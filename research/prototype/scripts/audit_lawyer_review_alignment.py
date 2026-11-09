#!/usr/bin/env python3
"""Audit whether lawyer-reviewed workbook rows align with committed model outputs.

Identity/alignment only. It does not infer lawyer labels, map NLI labels to
Yes/No/Partially, or compute model accuracy.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def norm_reference(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_text(value))


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
                    "document_id": str(case_id),
                    "source_file": path.name,
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text") or "",
                    "assertion_text": claim.get("assertion_text") or "",
                    "provision_type": citation.get("provision_type"),
                    "provision_number": citation.get("provision_number"),
                    "act_raw": citation.get("act_raw"),
                    "act_norm": citation.get("act_norm"),
                    "evidence_id": claim.get("evidence_id"),
                    "evidence_match_method": claim.get("evidence_match_method"),
                    "verdict": claim.get("verdict"),
                    "confidence": claim.get("confidence"),
                })
    return by_case


def audit(annotations: list[dict[str, Any]], by_case: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = []
    for annotation in annotations:
        case_id = str(annotation.get("case_reference") or "")
        statement = norm_text(annotation.get("legal_statement"))
        reference = norm_reference(annotation.get("legal_reference"))
        candidates = by_case.get(case_id, [])
        statement_matches = [
            candidate for candidate in candidates
            if statement and statement in {
                norm_text(candidate.get("claim_text")),
                norm_text(candidate.get("assertion_text")),
            }
        ]
        pair_matches = [
            candidate for candidate in statement_matches
            if not reference or reference in {
                norm_reference(candidate.get("act_raw")),
                norm_reference(candidate.get("evidence_id")),
                norm_reference(
                    f"{candidate.get('provision_type') or ''} "
                    f"{candidate.get('provision_number') or ''} "
                    f"{candidate.get('act_raw') or ''}"
                ),
            }
        ]
        unique = {}
        for candidate in statement_matches:
            key = (
                candidate.get("claim_text"), candidate.get("provision_type"),
                candidate.get("provision_number"), candidate.get("act_raw"),
                candidate.get("verdict"), candidate.get("evidence_id"),
            )
            if key not in unique:
                unique[key] = dict(candidate, source_files=[candidate["source_file"]])
            elif candidate["source_file"] not in unique[key]["source_files"]:
                unique[key]["source_files"].append(candidate["source_file"])
        matches = list(unique.values())
        rows.append({
            "annotation_id": annotation.get("annotation_id"),
            "case_reference": case_id,
            "case_found_in_model_outputs": bool(candidates),
            "num_candidate_claims_for_case": len(candidates),
            "exact_statement_match": bool(matches),
            "exact_statement_and_reference_match": bool(pair_matches),
            "num_distinct_statement_matches": len(matches),
            "matched_model_claims": matches,
        })

    n = len(rows)
    cases = {row["case_reference"] for row in rows}
    cases_found = {row["case_reference"] for row in rows if row["case_found_in_model_outputs"]}
    n_case = sum(row["case_found_in_model_outputs"] for row in rows)
    n_statement = sum(row["exact_statement_match"] for row in rows)
    n_pair = sum(row["exact_statement_and_reference_match"] for row in rows)
    return {
        "audit_type": "identity_alignment_only_not_model_evaluation",
        "n_lawyer_rows": n,
        "n_unique_lawyer_cases": len(cases),
        "n_unique_cases_present_in_model_outputs": len(cases_found),
        "rows_with_case_found": n_case,
        "rows_with_exact_statement_match": n_statement,
        "rows_with_exact_statement_and_reference_match": n_pair,
        "rows_with_ambiguous_multiple_statement_matches": sum(
            row["num_distinct_statement_matches"] > 1 for row in rows
        ),
        "row_coverage": {
            "case_found": n_case / n if n else 0.0,
            "exact_statement_match": n_statement / n if n else 0.0,
            "exact_statement_and_reference_match": n_pair / n if n else 0.0,
        },
        "rows": rows,
        "interpretation": (
            "Only exact text identity is counted. A missing match does not mean a legal "
            "statement is wrong. This script does not map NLI verdicts to lawyer labels."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path(
        "research/data/lawyer-review/processed/lawyer_review.normalized.jsonl"))
    parser.add_argument("--outputs-dir", type=Path, default=Path("research/prototype/outputs"))
    parser.add_argument("--output", type=Path, default=Path(
        "research/data/lawyer-review/processed/alignment_audit.json"))
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
