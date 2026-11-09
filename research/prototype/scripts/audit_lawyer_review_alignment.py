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
    r"([0-9]+(?:-[A-Za-z0-9]+)?[A-Za-z]?(?:\([^)]+\))*(?:\s*(?:,|and|&)\s*[0-9]+(?:-[A-Za-z0-9]+)?[A-Za-z]?(?:\([^)]+\))*)*)",
    re.IGNORECASE,
)


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def norm_reference(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_text(value))


def normalize_provision_number(value: Any) -> str:
    """Normalize typographic variants such as 295-A and 295A to one identifier."""
    return re.sub(r"[^a-z0-9()]", "", norm_text(value))


def provision_keys(value: Any) -> set[tuple[str, str]]:
    """Extract typed provision identifiers without guessing an Act or legal meaning."""
    result: set[tuple[str, str]] = set()
    for match in PROVISION_RE.finditer(norm_text(value)):
        kind = match.group(1).rstrip("s")
        for number in re.findall(r"[0-9]+(?:-[a-z0-9]+)?[a-z]?(?:\([^)]+\))*", match.group(2)):
            result.add((kind, normalize_provision_number(number)))
    return result


def extract_reference_act(value: Any) -> str:
    """Remove provision locators and subsection qualifiers from a lawyer reference."""
    text = PROVISION_RE.sub(" ", norm_text(value))
    text = re.sub(r"\b(?:sub[- ]?section|subsection|clause|paragraph)\s+[0-9]+[a-z]?(?:\([^)]+\))*", " ", text)
    text = re.sub(r"^\s*the\b", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(?:18|19|20)\d{2}\b", " ", text)
    normalized = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return "" if normalized in {"same act", "ibid"} else normalized


def act_name_match(reference_act: str, candidate_act: Any) -> str:
    """Return match/mismatch/unspecified; never infer an Act from a bare section number."""
    if not reference_act:
        return "unspecified"
    candidate = norm_text(candidate_act)
    if not candidate or candidate in {"same act", "ibid"}:
        return "unspecified"
    aliases = {
        "ipc": "indian penal code",
        "crpc": "code of criminal procedure",
        "pota": "prevention of terrorism act",
    }
    for alias, expansion in aliases.items():
        reference_act = re.sub(rf"\b{alias}\b", expansion, reference_act)
        candidate = re.sub(rf"\b{alias}\b", expansion, candidate)
    def core(value: str) -> str:
        value = re.sub(r"^the\s+", "", value.strip())
        value = re.sub(r"^part\s+[ivxlcdm]+\s+of\s+", "", value)
        return " ".join(
            token for token in value.split()
            if not re.fullmatch(r"(?:18|19|20)\d{2}", token)
        )
    reference_core = core(reference_act)
    candidate_core = core(candidate)
    if reference_core == candidate_core or reference_core in candidate_core or candidate_core in reference_core:
        return "match"
    return "mismatch"

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
        reference_act = extract_reference_act(annotation.get("legal_reference"))
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
                cnum = normalize_provision_number(candidate.get("provision_number"))
                item["provision_identifier_match"] = bool(keys and (ctype, cnum) in keys)
                item["act_match"] = act_name_match(reference_act, candidate.get("act_norm") or candidate.get("act_raw"))
                item["reference_text_match"] = bool(reference and reference in {
                    norm_text(candidate.get("act_raw")), norm_text(candidate.get("evidence_id")),
                    norm_text(f"{candidate.get('provision_type') or ''} {candidate.get('provision_number') or ''} {candidate.get('act_raw') or ''}")
                })
                unique[key] = item
            elif candidate["source_file"] not in unique[key]["source_files"]:
                unique[key]["source_files"].append(candidate["source_file"])
        matches = list(unique.values())
        reference_matches = [
            m for m in matches
            if (m["provision_identifier_match"] or m["reference_text_match"])
            and m.get("act_match") != "mismatch"
        ]
        # A same-Act, same-number Section/Rule disagreement is a confirmed citation
        # discrepancy, not a missing record. Preserve it as an explicit error state;
        # never coerce the provision type or count it as an exact reference match.
        typed_provision_mismatches = [
            m for m in matches
            if keys
            and any(number == normalize_provision_number(m.get("provision_number"))
                    and kind != norm_text(m.get("provision_type")).rstrip("s")
                    for kind, number in keys)
            and m.get("act_match") == "match"
        ]
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
            "num_typed_provision_mismatch_matches": len({
                (m.get("document_id"), m.get("claim_id"), m.get("provision_type"),
                 normalize_provision_number(m.get("provision_number")), norm_text(m.get("act_norm")))
                for m in typed_provision_mismatches
            }),
            "typed_provision_mismatch_claims": typed_provision_mismatches,
            "num_reference_aligned_matches": len({
                (m.get("document_id"), m.get("claim_id"), m.get("provision_type"),
                 normalize_provision_number(m.get("provision_number")), norm_text(m.get("act_norm")))
                for m in reference_matches
            }),
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
        "rows_with_ambiguous_reference_alignment": sum(r["num_reference_aligned_matches"] > 1 for r in rows),
        "rows_with_unique_reference_alignment": sum(r["num_reference_aligned_matches"] == 1 for r in rows),
        "rows_with_typed_provision_mismatch": sum(r["num_typed_provision_mismatch_matches"] > 0 for r in rows),
        "row_coverage": {
            "case_found": sum(r["case_found_in_model_outputs"] for r in rows) / n if n else 0.0,
            "exact_statement_match": sum(r["exact_statement_match"] for r in rows) / n if n else 0.0,
            "statement_and_reference_candidate_match": sum(r["exact_statement_and_reference_match"] for r in rows) / n if n else 0.0,
        },
        "rows": rows,
        "interpretation": (
            "Provision alignment requires a typed provision identifier and compatible Act name where supplied; "
            "unspecified Act names remain provisional. Multiple matching claims remain ambiguous. "
            "No NLI verdict is mapped to Yes/No/Partially and no model accuracy is computed."
        ),
    }


def compact_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Small alignment report suitable for CI artifacts and manual review."""
    rows = result["rows"]
    def ids(predicate):
        return [row["annotation_id"] for row in rows if predicate(row)]
    resolved_type_mismatches = [row for row in rows if row["num_typed_provision_mismatch_matches"] > 0]
    unmatched = [row for row in rows if row["num_reference_aligned_matches"] == 0
                 and row["num_typed_provision_mismatch_matches"] == 0]
    unmatched_diagnostics = []
    for row in unmatched:
        candidates = row["matched_model_claims"]
        if not candidates:
            reason = "no_exact_statement_match"
        elif not any(candidate["provision_identifier_match"] or candidate["reference_text_match"] for candidate in candidates):
            reason = "no_provision_identifier_or_reference_text_match"
        else:
            reason = "act_name_incompatible_or_unresolved"
        unmatched_diagnostics.append({
            "annotation_id": row["annotation_id"],
            "case_reference": row["case_reference"],
            "legal_reference": row["legal_reference"],
            "statement_correctness": row.get("statement_correctness"),
            "reference_correctness": row.get("reference_correctness"),
            "reason": reason,
            "statement_match_count": row["num_distinct_statement_matches"],
            "candidate_claims": [{
                "claim_id": candidate.get("claim_id"),
                "provision_type": candidate.get("provision_type"),
                "provision_number": candidate.get("provision_number"),
                "act_raw": candidate.get("act_raw"),
                "act_norm": candidate.get("act_norm"),
                "provision_identifier_match": candidate["provision_identifier_match"],
                "reference_text_match": candidate["reference_text_match"],
                "act_match": candidate["act_match"],
            } for candidate in candidates],
        })
    return {key: value for key, value in result.items() if key != "rows"} | {
        "row_counts": {
            "unique_reference_alignment": len(ids(lambda r: r["num_reference_aligned_matches"] == 1)),
            "ambiguous_reference_alignment": len(ids(lambda r: r["num_reference_aligned_matches"] > 1)),
            "resolved_typed_provision_mismatch": len(resolved_type_mismatches),
            "unmatched_reference_alignment": len(unmatched),
        },
        "annotation_ids": {
            "unique_reference_alignment": ids(lambda r: r["num_reference_aligned_matches"] == 1),
            "ambiguous_reference_alignment": ids(lambda r: r["num_reference_aligned_matches"] > 1),
            "resolved_typed_provision_mismatch": ids(lambda r: r["num_typed_provision_mismatch_matches"] > 0),
            "unmatched_reference_alignment": ids(lambda r: r["num_reference_aligned_matches"] == 0 and r["num_typed_provision_mismatch_matches"] == 0),
        },
        "resolved_typed_provision_mismatch_diagnostics": [{
            "annotation_id": row["annotation_id"],
            "legal_reference": row["legal_reference"],
            "candidate_claims": [{
                "claim_id": m.get("claim_id"), "provision_type": m.get("provision_type"),
                "provision_number": m.get("provision_number"), "act_raw": m.get("act_raw"),
            } for m in row["typed_provision_mismatch_claims"]],
        } for row in resolved_type_mismatches],
        "unmatched_diagnostics": unmatched_diagnostics,
        "interpretation": "Identity/provision alignment only; not model evaluation and no NLI-to-lawyer-label mapping.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path("research/data/lawyer-review/processed/lawyer_review.normalized.jsonl"))
    parser.add_argument("--outputs-dir", type=Path, default=Path("research/prototype/outputs"))
    parser.add_argument("--output", type=Path, default=Path("research/data/lawyer-review/processed/alignment_audit.json"))
    parser.add_argument("--summary-output", type=Path, default=Path("research/data/lawyer-review/processed/alignment_audit.summary.json"))
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
        summary = compact_summary(result)
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: alignment audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(compact_summary(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
