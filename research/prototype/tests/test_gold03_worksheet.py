"""Synthetic tests for GOLD-03 candidate worksheet construction."""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_gold03_annotation_worksheet.py"
SPEC = importlib.util.spec_from_file_location("build_gold03_annotation_worksheet", SCRIPT)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def canonical(key, number, text):
    return {
        "dataset_citation_key": key,
        "act": "Synthetic Act, 2000",
        "provision_type": "Section",
        "provision_number": number,
        "subsection": None,
        "canonical_text": text,
        "source_url": "https://example.org/" + number,
        "historical_status": "in_force",
    }


def audit(key, verdict):
    return {"dataset_citation_key": key, "audit_verdict": verdict}


def test_merge_applies_v1_replacement_before_exact_only_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(BUILDER, "DATA", tmp_path)
    write_jsonl(tmp_path / "canonical_statutes.jsonl", [
        canonical("A", "1", "Old v0 text."),
        canonical("B", "2", "Retained v0 text."),
    ])
    write_jsonl(tmp_path / "evidence_audit.jsonl", [
        audit("A", "VERIFIED_EXACT"), audit("B", "VERIFIED_EXACT"),
    ])
    write_jsonl(tmp_path / "canonical_statutes_v1.jsonl", [
        canonical("A", "1", "Updated v1 text."),
        canonical("C", "3", "New v1 text."),
    ])
    write_jsonl(tmp_path / "evidence_audit_v1.jsonl", [
        audit("A", "VERIFIED_CONTENT"), audit("C", "VERIFIED_EXACT"),
    ])

    rows = BUILDER.merged_records()
    assert [r["dataset_citation_key"] for r in rows] == ["B", "C"]
    assert [r["canonical_text"] for r in rows] == ["Retained v0 text.", "New v1 text."]


def test_builder_leaves_claim_and_gold_label_fields_blank():
    records = [
        {**canonical("A", "1", "First exact provision."), "audit_verdict": "VERIFIED_EXACT"},
        {**canonical("B", "2", "Second exact provision."), "audit_verdict": "VERIFIED_EXACT"},
    ]
    rows = BUILDER.build_rows(records)
    assert len(rows) == 2
    assert all(row["candidate_claim_without_citation"] == "" for row in rows)
    assert all(row["reviewer1_label"] == "" and row["reviewer2_label"] == ""
               and row["adjudicated_label"] == "" for row in rows)
    assert all(row["correct_identifier"] != row["mismatched_identifier"] for row in rows)
    assert [row["item_id"] for row in rows] == ["G03_0001", "G03_0002"]
