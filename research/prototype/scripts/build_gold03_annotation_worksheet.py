#!/usr/bin/env python3
"""Build a GOLD-03 annotation worksheet from exact-audited evidence only.

This creates candidate rows and metadata-control fields, NOT gold labels.
It is read-only with respect to source evidence and all GOLD-01 artifacts.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "data" / "evidence"
OUT = ROOT / "research" / "prototype" / "outputs"
VERDICT = "VERIFIED_EXACT"
FIELDS = [
    "item_id", "source_key", "source_act", "source_provision_type",
    "source_provision_number", "source_subsection", "source_text",
    "source_url", "source_audit_verdict", "source_historical_status",
    "correct_identifier", "mismatched_identifier",
    "candidate_claim_without_citation",
    "reviewer1_label", "reviewer1_rationale",
    "reviewer2_label", "reviewer2_rationale",
    "adjudicated_label", "adjudication_rationale",
    "paraphrase_candidate", "paraphrase_review_decision",
    "contradiction_candidate", "contradiction_review_decision",
    "nei_candidate", "nei_review_decision",
    "reviewer_notes",
]


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def merged_records() -> list[dict]:
    """Mirror config's v0 + v1 merge-by-key, but retain raw provenance fields."""
    pairs = [
        (DATA / "canonical_statutes.jsonl", DATA / "evidence_audit.jsonl"),
        (DATA / "canonical_statutes_v1.jsonl", DATA / "evidence_audit_v1.jsonl"),
    ]
    merged: dict[str, dict] = {}
    for canonical_path, audit_path in pairs:
        audits = {r["dataset_citation_key"]: r for r in read_jsonl(audit_path)}
        for row in read_jsonl(canonical_path):
            key = row["dataset_citation_key"]
            audit = audits.get(key)
            if audit and audit.get("audit_verdict") in {"VERIFIED_EXACT", "VERIFIED_CONTENT"}:
                merged[key] = {**row, **{
                    "audit_verdict": audit.get("audit_verdict"),
                    "audit_note": audit.get("audit_note", ""),
                    "audit_date": audit.get("audit_date", ""),
                    "audit_method": audit.get("audit_method", ""),
                }}
    # Apply exact-only selection AFTER v1 replaces same-key v0 records.
    exact = [row for row in merged.values() if row["audit_verdict"] == VERDICT]
    return sorted(exact, key=lambda r: r["dataset_citation_key"])


def main() -> int:
    records = merged_records()
    if len(records) < 2:
        raise SystemExit("Need at least two VERIFIED_EXACT records across v0/v1 evidence files.")

    rows = []
    for i, source in enumerate(records):
        other = records[(i + 1) % len(records)]
        sub = f"({source['subsection']})" if source.get("subsection") else ""
        correct = (f"{source['provision_type']} {source['provision_number']}{sub} "
                   f"of {source['act']}")
        wrong_sub = f"({other['subsection']})" if other.get("subsection") else ""
        wrong = (f"{other['provision_type']} {other['provision_number']}{wrong_sub} "
                 f"of {other['act']}")
        rows.append({
            "item_id": f"G03_{i + 1:04d}",
            "source_key": source["dataset_citation_key"],
            "source_act": source["act"],
            "source_provision_type": source["provision_type"],
            "source_provision_number": source["provision_number"],
            "source_subsection": source.get("subsection") or "",
            "source_text": source["canonical_text"],
            "source_url": source.get("source_url", ""),
            "source_audit_verdict": source["audit_verdict"],
            "source_historical_status": source.get("historical_status", ""),
            "correct_identifier": correct,
            "mismatched_identifier": wrong,
            # Reserved for an independently drafted, citation-free claim.
            "candidate_claim_without_citation": "",
            **{field: "" for field in FIELDS if field not in {
                "item_id", "source_key", "source_act", "source_provision_type",
                "source_provision_number", "source_subsection", "source_text",
                "source_url", "source_audit_verdict", "source_historical_status",
                "correct_identifier", "mismatched_identifier",
                "candidate_claim_without_citation",
            }},
        })

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "GOLD03_ANNOTATION_WORKSHEET.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "output": str(path.relative_to(ROOT)),
        "candidate_rows": len(rows),
        "source_filter": "VERIFIED_EXACT only",
        "source_files": ["canonical_statutes.jsonl", "canonical_statutes_v1.jsonl"],
        "labels_created": False,
        "mismatched_identifiers": "deterministic next-record pairing; diagnostic only",
        "warning": (
            "No claims or gold labels are generated. The citation-free claim field "
            "is intentionally blank for independent drafting. The deterministic "
            "mismatch pairing may be substantively related and must be reviewed."
        ),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
