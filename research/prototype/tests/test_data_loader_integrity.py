"""Fail-closed tests for canonical evidence/audit loading.

These tests use synthetic records only; they do not validate statutory content.
"""
import json

import pytest

from src.data_loader import load_usable_evidence

USABLE = {"VERIFIED_EXACT", "VERIFIED_CONTENT"}


def write_pair(tmp_path, canonical_rows, audit_rows):
    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical = tmp_path / "canonical.jsonl"
    audit = tmp_path / "audit.jsonl"
    canonical.write_text(
        "".join(json.dumps(row) + "\n" for row in canonical_rows),
        encoding="utf-8",
    )
    audit.write_text(
        "".join(json.dumps(row) + "\n" for row in audit_rows),
        encoding="utf-8",
    )
    return canonical, audit


def canonical(key="Section 1 in Example Act, 2000", number="1", act="Example Act, 2000"):
    return {
        "dataset_citation_key": key,
        "act": act,
        "provision_type": "Section",
        "provision_number": number,
        "subsection": None,
        "canonical_text": "A synthetic statutory sentence.",
        "source_url": "https://example.invalid/source",
    }


def audit(key="Section 1 in Example Act, 2000", verdict="VERIFIED_EXACT"):
    return {"dataset_citation_key": key, "audit_verdict": verdict}


def test_valid_pair_loads_only_usable_records(tmp_path):
    rows = [canonical(), canonical("Section 2 in Example Act, 2000", "2")]
    audits = [audit(), audit("Section 2 in Example Act, 2000", "SOURCE_ONLY")]
    cpath, apath = write_pair(tmp_path, rows, audits)

    index, records = load_usable_evidence(cpath, apath, USABLE)

    assert len(index) == 1
    assert len(records) == 1
    assert records[0].audit_verdict == "VERIFIED_EXACT"


def test_duplicate_canonical_key_is_rejected(tmp_path):
    row = canonical()
    cpath, apath = write_pair(tmp_path, [row, row], [audit()])

    with pytest.raises(ValueError, match="Duplicate canonical citation key"):
        load_usable_evidence(cpath, apath, USABLE)


def test_duplicate_audit_key_is_rejected(tmp_path):
    row = canonical()
    cpath, apath = write_pair(tmp_path, [row], [audit(), audit()])

    with pytest.raises(ValueError, match="Duplicate audit citation key"):
        load_usable_evidence(cpath, apath, USABLE)


def test_missing_audit_row_is_rejected(tmp_path):
    cpath, apath = write_pair(tmp_path, [canonical()], [])

    with pytest.raises(ValueError, match="no audit row"):
        load_usable_evidence(cpath, apath, USABLE)


def test_orphan_audit_row_is_rejected(tmp_path):
    cpath, apath = write_pair(
        tmp_path, [canonical()], [audit(), audit("Section 99 in Example Act, 2000")]
    )

    with pytest.raises(ValueError, match="orphan record"):
        load_usable_evidence(cpath, apath, USABLE)


def test_unknown_audit_verdict_is_rejected(tmp_path):
    cpath, apath = write_pair(tmp_path, [canonical()], [audit(verdict="MAYBE_USABLE")])

    with pytest.raises(ValueError, match="Unknown audit verdict"):
        load_usable_evidence(cpath, apath, USABLE)


def test_incomplete_canonical_record_is_rejected(tmp_path):
    row = canonical()
    row["canonical_text"] = ""
    cpath, apath = write_pair(tmp_path, [row], [audit()])

    with pytest.raises(ValueError, match="missing/empty fields"):
        load_usable_evidence(cpath, apath, USABLE)


def test_malformed_jsonl_is_rejected_with_line_context(tmp_path):
    cpath = tmp_path / "canonical.jsonl"
    apath = tmp_path / "audit.jsonl"
    cpath.write_text('{"dataset_citation_key":\n', encoding="utf-8")
    apath.write_text(json.dumps(audit()) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_usable_evidence(cpath, apath, USABLE)


def test_exact_index_collision_is_rejected_across_merged_pools(tmp_path):
    base_key = "Section 1 in Example Act, 2000"
    extra_key = "Section 01 in Example Act, 2000"
    c0, a0 = write_pair(tmp_path / "base", [canonical(base_key)], [audit(base_key)])
    c1, a1 = write_pair(tmp_path / "extra", [canonical(extra_key, "1")], [audit(extra_key)])

    with pytest.raises(ValueError, match="Evidence index collision"):
        load_usable_evidence(c0, a0, USABLE, c1, a1)
