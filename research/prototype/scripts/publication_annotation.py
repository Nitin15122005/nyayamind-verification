#!/usr/bin/env python3
"""Blind annotation workflow for publication evaluation.

This utility prepares reviewer-separated packets, merges independent labels,
validates adjudication, and reports agreement. It never creates labels.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Iterable

LABELS = {"ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"}
GOLD03_REVIEW_FIELDS = [
    "item_id", "source_text", "source_url", "claim_text",
    "label", "rationale", "reviewer_id",
]
NATURAL_FIELDS = [
    "annotation_id", "document_id", "claim_id", "case_date",
    "case_context", "claim_text", "assertion_text", "citation",
    "evidence_text", "evidence_source_url",
    "reviewer_label", "reviewer_rationale", "citation_correctness",
    "temporal_applicability", "reviewer_id",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            yield value


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def command_split_gold03(args: argparse.Namespace) -> int:
    rows = read_csv(args.worksheet)
    required = {"item_id", "source_text", "source_url", "candidate_claim_without_citation"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Worksheet must contain columns: {sorted(required)}")
    blank_claims = [r.get("item_id", "") for r in rows if not r.get("candidate_claim_without_citation", "").strip()]
    if blank_claims:
        raise ValueError(f"Draft citation-free claims before blind annotation; blank items: {blank_claims[:10]}")
    ids = [r["item_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate item_id in source worksheet")
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    out = Path(args.outdir)
    for reviewer in ("R1", "R2"):
        packet = []
        for row in rows:
            packet.append({
                "item_id": row["item_id"],
                "source_text": row["source_text"],
                "source_url": row["source_url"],
                "claim_text": row["candidate_claim_without_citation"],
                "label": "",
                "rationale": "",
                "reviewer_id": reviewer,
            })
        write_csv(out / f"GOLD03_{reviewer}_BLIND.csv", packet, GOLD03_REVIEW_FIELDS)
    manifest = {
        "dataset": "GOLD-03 candidate annotation",
        "source_file": str(args.worksheet),
        "source_sha256": digest(args.worksheet),
        "n_items": len(rows),
        "seed": args.seed,
        "reviewer_packets": ["GOLD03_R1_BLIND.csv", "GOLD03_R2_BLIND.csv"],
        "labels_created": False,
        "blinding": "reviewer packets contain no model predictions or other reviewer's fields",
        "warning": "Claims must be independently authored and non-empty before annotation.",
    }
    (out / "GOLD03_ANNOTATION_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


def _validate_review_packet(path: Path) -> dict[str, dict]:
    rows = read_csv(path)
    result = {}
    for row in rows:
        item = row.get("item_id", "").strip()
        label = row.get("label", "").strip().upper()
        if not item:
            raise ValueError(f"{path}: blank item_id")
        if item in result:
            raise ValueError(f"{path}: duplicate item_id {item}")
        if label not in LABELS:
            raise ValueError(f"{path}: {item}: invalid label {label!r}")
        if not row.get("claim_text", "").strip():
            raise ValueError(f"{path}: {item}: blank claim_text")
        if not row.get("rationale", "").strip():
            raise ValueError(f"{path}: {item}: rationale is required")
        result[item] = {**row, "label": label}
    return result


def command_merge_gold03(args: argparse.Namespace) -> int:
    a = _validate_review_packet(args.reviewer1)
    b = _validate_review_packet(args.reviewer2)
    if set(a) != set(b):
        raise ValueError("Reviewer item sets differ; refusing positional or partial merge")
    ids_a = {row.get("reviewer_id", "").strip() for row in a.values()}
    ids_b = {row.get("reviewer_id", "").strip() for row in b.values()}
    if len(ids_a) != 1 or len(ids_b) != 1 or "" in ids_a or "" in ids_b or ids_a == ids_b:
        raise ValueError("Reviewer packets must have distinct, non-empty reviewer identities")
    rows = []
    for item in sorted(a):
        x, y = a[item], b[item]
        for field in ("claim_text", "source_text"):
            if x.get(field) != y.get(field):
                raise ValueError(f"{item}: reviewers saw different {field}")
        rows.append({
            "item_id": item,
            "claim_text": x["claim_text"],
            "source_text": x["source_text"],
            "source_url": x.get("source_url", ""),
            "reviewer1_id": x.get("reviewer_id", ""),
            "reviewer1_label": x["label"],
            "reviewer1_rationale": x["rationale"],
            "reviewer2_id": y.get("reviewer_id", ""),
            "reviewer2_label": y["label"],
            "reviewer2_rationale": y["rationale"],
            "adjudicated_label": "",
            "adjudication_rationale": "",
            "adjudicator_id": "",
        })
    write_csv(args.output, rows, list(rows[0]) if rows else [
        "item_id", "claim_text", "source_text", "source_url", "reviewer1_id",
        "reviewer1_label", "reviewer1_rationale", "reviewer2_id",
        "reviewer2_label", "reviewer2_rationale", "adjudicated_label",
        "adjudication_rationale", "adjudicator_id",
    ])
    print(json.dumps({
        "output": str(args.output), "items": len(rows),
        "agreement_count": sum(r["reviewer1_label"] == r["reviewer2_label"] for r in rows),
        "disagreement_count": sum(r["reviewer1_label"] != r["reviewer2_label"] for r in rows),
        "adjudication_required": sum(r["reviewer1_label"] != r["reviewer2_label"] for r in rows),
        "gold_labels_created": False,
    }, indent=2))
    return 0


def command_validate_gold03(args: argparse.Namespace) -> int:
    rows = read_csv(args.input)
    errors = []
    seen = set()
    for i, row in enumerate(rows, 2):
        item = row.get("item_id", "").strip()
        if not item or item in seen:
            errors.append(f"line {i}: blank or duplicate item_id")
        seen.add(item)
        for field in ("reviewer1_label", "reviewer2_label"):
            value = row.get(field, "").strip().upper()
            if value not in LABELS:
                errors.append(f"line {i}: missing or invalid {field}={value}")
        value = row.get("adjudicated_label", "").strip().upper()
        if value and value not in LABELS:
            errors.append(f"line {i}: invalid adjudicated_label={value}")
        for field in ("reviewer1_id", "reviewer2_id", "reviewer1_rationale", "reviewer2_rationale"):
            if not row.get(field, "").strip():
                errors.append(f"line {i}: {field} missing")
        if row.get("reviewer1_id") == row.get("reviewer2_id"):
            errors.append(f"line {i}: reviewer identities must be independent")
        if row.get("adjudicated_label", "").strip():
            if not row.get("adjudication_rationale", "").strip():
                errors.append(f"line {i}: adjudication rationale missing")
            if not row.get("adjudicator_id", "").strip():
                errors.append(f"line {i}: adjudicator_id missing")
    incomplete = sum(not r.get("adjudicated_label", "").strip() for r in rows)
    result = {"n_items": len(rows), "n_incomplete_adjudications": incomplete,
              "errors": errors, "release_ready": bool(rows) and not errors and incomplete == 0}
    print(json.dumps(result, indent=2))
    return 0 if result["release_ready"] else 2


def kappa(rows: list[dict]) -> float | None:
    n = len(rows)
    if not n:
        return None
    observed = sum(r["reviewer1_label"] == r["reviewer2_label"] for r in rows) / n
    labels = sorted(LABELS)
    c1, c2 = Counter(r["reviewer1_label"] for r in rows), Counter(r["reviewer2_label"] for r in rows)
    expected = sum(c1[x] * c2[x] for x in labels) / (n * n)
    return (observed - expected) / (1 - expected) if expected != 1 else 1.0


def command_summarize_gold03(args: argparse.Namespace) -> int:
    rows = read_csv(args.input)
    paired = [r for r in rows if r.get("reviewer1_label") in LABELS and r.get("reviewer2_label") in LABELS]
    adjudicated = [r for r in rows if r.get("adjudicated_label") in LABELS]
    result = {
        "n_items": len(rows),
        "n_double_annotated": len(paired),
        "raw_agreement": (sum(r["reviewer1_label"] == r["reviewer2_label"] for r in paired) / len(paired)) if paired else None,
        "cohens_kappa": kappa(paired),
        "adjudicated_class_counts": dict(Counter(r["adjudicated_label"] for r in adjudicated)),
        "n_adjudicated": len(adjudicated),
        "n_unadjudicated": len(rows) - len(adjudicated),
        "warning": "Agreement is descriptive; it does not establish label correctness or legal validity.",
    }
    print(json.dumps(result, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


def command_export_natural(args: argparse.Namespace) -> int:
    records = list(read_jsonl(args.input))
    rows = []
    for record in records:
        document_id = str(record.get("document_id") or "")
        case_text = str(record.get("case_text") or "")
        generated = record.get("generated_field") or {}
        claims = record.get("claims") or []
        if not isinstance(claims, list):
            continue
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            citation = claim.get("citation_extracted") or {}
            evidence_url = claim.get("evidence_source_url") or record.get("evidence_source_url") or ""
            rows.append({
                "annotation_id": f"{document_id}:{claim.get('claim_id', '')}",
                "document_id": document_id,
                "claim_id": str(claim.get("claim_id") or ""),
                "case_date": str(record.get("judgment_date") or record.get("case_date") or ""),
                "case_context": case_text,
                "claim_text": str(claim.get("assertion_text") or claim.get("claim_text") or generated.get("text") or ""),
                "assertion_text": str(claim.get("assertion_text") or ""),
                "citation": json.dumps(citation, ensure_ascii=False, sort_keys=True),
                "evidence_text": str(claim.get("evidence_text") or ""),
                "evidence_source_url": str(evidence_url),
                "reviewer_label": "",
                "reviewer_rationale": "",
                "citation_correctness": "",
                "temporal_applicability": "",
                "reviewer_id": args.reviewer,
            })
    if not rows:
        raise ValueError("No claim rows found; expected records with document_id and claims[]")
    # No automated verdict, confidence, or model identity is exported to reviewers.
    rows.sort(key=lambda r: (r["document_id"], r["claim_id"]))
    write_csv(args.output, rows, NATURAL_FIELDS)
    print(json.dumps({
        "output": str(args.output), "n_documents": len({r["document_id"] for r in rows}),
        "n_claims": len(rows), "labels_created": False,
        "blinding": "automated verdicts and confidence scores are excluded from reviewer packet",
        "case_grouping": "document_id is the mandatory split/cluster unit",
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("split-gold03")
    p.add_argument("--worksheet", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20261104)
    p.set_defaults(func=command_split_gold03)
    p = sub.add_parser("merge-gold03")
    p.add_argument("--reviewer1", type=Path, required=True)
    p.add_argument("--reviewer2", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(func=command_merge_gold03)
    p = sub.add_parser("validate-gold03")
    p.add_argument("--input", type=Path, required=True)
    p.set_defaults(func=command_validate_gold03)
    p = sub.add_parser("summarize-gold03")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.set_defaults(func=command_summarize_gold03)
    p = sub.add_parser("export-natural")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--reviewer", default="")
    p.set_defaults(func=command_export_natural)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
