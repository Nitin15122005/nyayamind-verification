#!/usr/bin/env python3
"""Audit lawyer-review rows against frozen model outputs; never infer legal labels."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PROVISION_RE = re.compile(
    r"\b(section|sections|article|articles|rule|rules|regulation|regulations)\s+"
    r"([0-9]+[A-Za-z]?(?:\([^)]+\))*(?:\s*(?:,|and|&)\s*[0-9]+[A-Za-z]?(?:\([^)]+\))*)*)",
    re.IGNORECASE,
)


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def norm_reference(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_text(value))


def provision_keys(value: Any) -> set[tuple[str, str]]:
    """Extract typed provision identifiers without guessing an Act or legal meaning."""
    result: set[tuple[str, str]] = set()
    text = norm_text(value)
    for match in PROVISION_RE.finditer(text):
        kind = match.group(1).rstrip("s")
        for number in re.findall(r"[0-9]+[a-z]?(?:\([^)]+\))*", match.group(2)):
            result.add((kind, re.sub(r"\s+", "", number)))
    return result


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc


def collect_model_claims(outputs_dir: Path) -> dict[str, list[dict[str, Any]]]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(outputs_dir.glob("*.jsonl")):
        if "annotation" in path.name.casefold():
            continue
        for record in read_jsonl(path):
            case_id = record.get("document_id") or record.get("case_reference")
            claims = record.get("claims")
            if not case_id or not isinstance(claims, list):
                continue
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                citation = claim.get("citation_extracted") or claim.get("extracted_citation") or {}
                by_case[str(case_id)].append({
                    "document_id": str(case_id), "source_file": path.name,
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text") or "",
                    "assertion_text": claim.get("assertion_text") or "",
                    "provision_type": citation.get("provision_type"),
                    "provision_number": citation.get("provision_number"),
                    "act_raw": citation.get("act_raw"), "act_norm": citation.get("act_norm"),
                    "evidence_id": claim.get("evidence_id"),
                    "evidence_match_method": claim.get("evidence_match_method"),
                    "verdict": claim.get("verdict"), "confidence": claim.get("confidence"),
                })
    return by_case


def audit(annotations: list[dict[str, Any]], by_case: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = []
    for annotation in annotations:
        case_id = str(annotation.get("case_reference") or "")
        statement = norm_text(annotation.get("legal_statement"))
        reference = norm_text(annotation.get("legal_reference"))
        keys = provision_keys(annotation.get("legal_reference"))
        candidates = by_case.get(case_id, [])
        statement_matches = [
            candidate for candidate in candidates
            if statement and statement in {
                norm_text(candidate.get("claim_text")), norm_text(candidate.get("assertion_text"))
            }
        ]
        unique = {}
        for candidate in statement_matches:
            key = (candidate.get("claim_text"), candidate.get("provision_type"),
                   candidate.get("provision_number"), candidate.get("act_raw"),
                   candidate.get("verdict"), candidate.get("evidence_id"))
            if key not in unique:
                item = dict(candidate, source_files=[candidate["source_file"]])
                ctype = norm_text(candidate.get("provision_type")).rstrip("s")
                cnum = re.sub(r"\s+", "", norm_text(candidate.get("provision_number")))
                item["provision_identifier_match"] = bool(keys and (ctype, cnum) in keys)
                item["reference_text_match"] = bool(reference and reference in {
                    norm_text(candidate.get("act_raw")), norm_text(candidate.get("evidence_id")),
                    norm_text(f"{candidate.get('provision_type') or ''} {candidate.get('provision_number') or ''} {candidate.get('act_raw') or ''}")
                })
                unique[key] = item
            elif candidate["source_file"] not in unique[key]["source_files"]:
                unique[key]["source_files"].append(candidate["source_file"])
        matches = list(unique.values())
        reference_matches = [m for m in matches if m["provision_identifier_match"] or m["reference_text_match"]]
        rows.append({
            "annotation_id": annotation.get("annotation_id"),
            "case_reference": case_id,
            "legal_statement": annotation.get("legal_statement"),
            "legal_reference": annotation.get("legal_reference"),
            "statement_correctness": annotation.get("statement_correctness"),
            "reference_correctness": annotation.get("reference_correctness"),
            "correction_or_clarification": annotation.get("correction_or_clarification"),
            "supporting_legal_authority": annotation.get("supporting_legal_authority"),
            "case_found_in_model_outputs": bool(candidates),
            "num_candidate_claims_for_case": len(candidates),
            "exact_statement_match": bool(matches),
            "exact_statement_and_reference_match": bool(reference_matches),
            "num_distinct_statement_matches": len(matches),
            "num_reference_aligned_matches": len(reference_matches),
            "matched_model_claims": matches,
        })

    n = len(rows)
    cases = {r["case_reference"] for r in rows}
    cases_found = {r["case_reference"] for r in rows if r["case_found_in_model_outputs"]}
    return {
        "audit_type": "identity_and_provision_alignment_only_not_model_evaluation",
        "n_lawyer_rows": n,
        "n_unique_lawyer_cases": len(cases),
        "n_unique_cases_present_in_model_outputs": len(cases_found),
        "rows_with_case_found": sum(r["case_found_in_model_outputs"] for r in rows),
        "rows_with_exact_statement_match": sum(r["exact_statement_match"] for r in rows),
        "rows_with_exact_statement_and_reference_match": sum(r["exact_statement_and_reference_match"] for r in rows),
        "rows_with_ambiguous_multiple_statement_matches": sum(r["num_distinct_statement_matches"] > 1 for r in rows),
        "row_coverage": {
            "case_found": sum(r["case_found_in_model_outputs"] for r in rows) / n if n else 0.0,
            "exact_statement_match": sum(r["exact_statement_match"] for r in rows) / n if n else 0.0,
            "statement_and_reference_candidate_match": sum(r["exact_statement_and_reference_match"] for r in rows) / n if n else 0.0,
        },
        "rows": rows,
        "interpretation": (
            "Provision alignment is based only on typed provision identifiers parsed from the lawyer's "
            "reference field or exact normalized reference text. Multiple matching claims remain ambiguous. "
            "No NLI verdict is mapped to Yes/No/Partially and no model accuracy is computed."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path("research/data/lawyer-review/processed/lawyer_review.normalized.jsonl"))
    parser.add_argument("--outputs-dir", type=Path, default=Path("research/prototype/outputs"))
    parser.add_argument("--output", type=Path, default=Path("research/data/lawyer-review/processed/alignment_audit.json"))
    args = parser.parse_args(argv)
    if not args.annotations.is_file():
        print(f"ERROR: normalized annotations not found: {args.annotations}", file=sys.stderr)
        return 2
    if not args.outputs_dir.is_dir():
        print(f"ERROR: model outputs directory not found: {args.outputs_dir}", file=sys.stderr)
        return 2
    try:
        annotations = list(read_jsonl(args.annotations))
        if not annotations:
            raise ValueError("normalized annotation file contains no rows")
        result = audit(annotations, collect_model_claims(args.outputs_dir))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: alignment audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
