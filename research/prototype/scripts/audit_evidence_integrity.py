#!/usr/bin/env python3
"""Structural integrity audit for NyayaMind's read-only statutory evidence corpus.

This script checks file/schema/join/merge invariants. It does NOT certify that
statutory text is legally correct; that requires authoritative-source and
qualified legal review. It writes a machine-readable JSON report and exits
non-zero only for structural errors.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "research" / "prototype"))
from src.claim_parser import normalize_act  # noqa: E402

USABLE = {"VERIFIED_EXACT", "VERIFIED_CONTENT"}
ALLOWED_VERDICTS = USABLE | {"SOURCE_ONLY", "INVALID", "UNRESOLVED"}
REQUIRED = {
    "dataset_citation_key", "act", "provision_type", "provision_number",
    "canonical_text", "source_url", "historical_status",
}


def read_jsonl(path: Path, errors: list[dict]) -> list[dict]:
    rows = []
    if not path.is_file():
        errors.append({"code": "MISSING_FILE", "path": str(path)})
        return rows
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                errors.append({"code": "BLANK_LINE", "path": str(path), "line": line_no})
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append({"code": "INVALID_JSON", "path": str(path), "line": line_no, "detail": str(exc)})
                continue
            if not isinstance(value, dict):
                errors.append({"code": "NON_OBJECT_RECORD", "path": str(path), "line": line_no})
                continue
            value["_audit_line"] = line_no
            rows.append(value)
    return rows


def inspect_pair(label: str, canonical: list[dict], audit: list[dict], errors: list[dict], warnings: list[dict]) -> dict:
    ckeys = [r.get("dataset_citation_key") for r in canonical]
    akeys = [r.get("dataset_citation_key") for r in audit]
    ccounts, acounts = Counter(ckeys), Counter(akeys)
    for key, count in ccounts.items():
        if not key or count > 1:
            errors.append({"code": "CANONICAL_DUPLICATE_OR_EMPTY_KEY", "pool": label, "key": key, "count": count})
    for key, count in acounts.items():
        if not key or count > 1:
            errors.append({"code": "AUDIT_DUPLICATE_OR_EMPTY_KEY", "pool": label, "key": key, "count": count})
    cset, aset = set(ckeys), set(akeys)
    for key in sorted(cset - aset, key=lambda value: str(value)):
        errors.append({"code": "MISSING_AUDIT_ROW", "pool": label, "key": key})
    for key in sorted(aset - cset, key=lambda value: str(value)):
        errors.append({"code": "ORPHAN_AUDIT_ROW", "pool": label, "key": key})
    audit_by_key = {r.get("dataset_citation_key"): r for r in audit}
    verdict_counts = Counter()
    usable = []
    for row in canonical:
        key = row.get("dataset_citation_key")
        audit_row = audit_by_key.get(key, {})
        verdict = audit_row.get("audit_verdict")
        verdict_counts[verdict or "MISSING"] += 1
        for field_name in ("source_url", "act", "provision_type", "provision_number"):
            audited_value = audit_row.get(field_name)
            if audited_value is not None and str(audited_value) != str(row.get(field_name)):
                errors.append({
                    "code": "CANONICAL_AUDIT_METADATA_MISMATCH",
                    "pool": label,
                    "key": key,
                    "field": field_name,
                })
        missing = sorted(field for field in REQUIRED if not str(row.get(field, "")).strip())
        if missing:
            errors.append({"code": "MISSING_REQUIRED_FIELDS", "pool": label, "key": key, "fields": missing})
        url = row.get("source_url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append({"code": "INVALID_SOURCE_URL", "pool": label, "key": key, "url": url})
        if verdict not in ALLOWED_VERDICTS:
            errors.append({"code": "UNKNOWN_OR_MISSING_VERDICT", "pool": label, "key": key, "verdict": verdict})
        if verdict in USABLE and isinstance(key, str) and key.strip():
            usable.append(row)
        act = row.get("act", "")
        if act and row.get("act_norm") and row["act_norm"] != normalize_act(act):
            errors.append({"code": "ACT_NORMALIZATION_MISMATCH", "pool": label, "key": key})
        if row.get("historical_status") == "in_force" and any(
            token in act.lower() for token in ("indian penal code", "code of criminal procedure", "indian evidence act")
        ):
            warnings.append({
                "code": "REVIEW_HISTORICAL_STATUS",
                "pool": label,
                "key": key,
                "detail": "Legacy enactment marked in_force; confirm applicable date/version and statutory transition.",
            })
    return {
        "pool": label,
        "canonical_records": len(canonical),
        "audit_records": len(audit),
        "usable_records": len(usable),
        "verdict_counts": dict(verdict_counts),
        "canonical_audit_key_sets_match": cset == aset,
        "canonical_audit_key_order_matches": ckeys == akeys,
        "usable_records_by_key": {r["dataset_citation_key"]: r for r in usable},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    errors: list[dict] = []
    warnings: list[dict] = []
    base = root / "research/data/evidence"
    specs = [
        ("v0", base / "canonical_statutes.jsonl", base / "evidence_audit.jsonl"),
        ("v1", base / "canonical_statutes_v1.jsonl", base / "evidence_audit_v1.jsonl"),
    ]
    pools = []
    for label, cp, ap in specs:
        c = read_jsonl(cp, errors)
        a = read_jsonl(ap, errors)
        pools.append(inspect_pair(label, c, a, errors, warnings))

    merged = {}
    for pool in pools:
        for key, record in pool["usable_records_by_key"].items():
            if key in merged and pool["pool"] == "v1" and not record.get("v1_supersedes_v0_record"):
                errors.append({"code": "UNDECLARED_V1_KEY_COLLISION", "key": key})
            merged[key] = record

    index = defaultdict(list)
    for key, row in merged.items():
        norm = normalize_act(row["act"])
        index[(row["provision_type"], str(row["provision_number"]), row.get("subsection"), norm)].append(key)
    collisions = [
        {"index_key": list(index_key), "citation_keys": keys}
        for index_key, keys in index.items() if len(keys) > 1
    ]
    for item in collisions:
        errors.append({"code": "MERGED_EXACT_INDEX_COLLISION", **item})

    report = {
        "audit_scope": "structural integrity only; not legal validation",
        "repo_root": str(root),
        "pools": [{k: v for k, v in p.items() if k != "usable_records_by_key"} for p in pools],
        "merged_usable_record_count": len(merged),
        "merged_exact_index_collision_count": len(collisions),
        "errors": errors,
        "warnings": warnings,
        "status": "PASS_WITH_WARNINGS" if not errors and warnings else "PASS" if not errors else "FAIL",
    }
    output = args.output or (root / "research/prototype/outputs/publication_evidence_integrity_audit.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"errors", "warnings"}}, indent=2))
    print(f"Errors: {len(errors)} | Warnings: {len(warnings)} | Report: {output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
