"""Synthetic tests for the publication evidence integrity audit.

These tests exercise structural rules only; they do not validate statutory content.
"""
import importlib.util
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audit_evidence_integrity.py"
)
SPEC = importlib.util.spec_from_file_location("audit_evidence_integrity", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDIT)


def record(key="Section 1 in Test Act, 2000"):
    return {
        "dataset_citation_key": key,
        "act": "Test Act, 2000",
        "provision_type": "Section",
        "provision_number": "1",
        "canonical_text": "Synthetic text for structural testing only.",
        "source_url": "https://example.org/section-1",
        "historical_status": "in_force",
    }


def test_valid_canonical_audit_pair_has_no_structural_errors():
    errors, warnings = [], []
    canonical = [record()]
    audit = [{"dataset_citation_key": canonical[0]["dataset_citation_key"],
              "audit_verdict": "VERIFIED_EXACT"}]
    result = AUDIT.inspect_pair("fixture", canonical, audit, errors, warnings)
    assert result["canonical_records"] == 1
    assert result["usable_records"] == 1
    assert result["canonical_audit_key_sets_match"] is True
    assert errors == []


def test_missing_audit_row_is_reported():
    errors, warnings = [], []
    AUDIT.inspect_pair("fixture", [record()], [], errors, warnings)
    assert any(item["code"] == "MISSING_AUDIT_ROW" for item in errors)


def test_orphan_audit_row_is_reported():
    errors, warnings = [], []
    AUDIT.inspect_pair(
        "fixture", [],
        [{"dataset_citation_key": "orphan", "audit_verdict": "VERIFIED_EXACT"}],
        errors, warnings,
    )
    assert any(item["code"] == "ORPHAN_AUDIT_ROW" for item in errors)


def test_duplicate_canonical_key_is_reported():
    errors, warnings = [], []
    row = record()
    AUDIT.inspect_pair("fixture", [row, dict(row)], [], errors, warnings)
    assert any(item["code"] == "CANONICAL_DUPLICATE_OR_EMPTY_KEY" for item in errors)


def test_unusable_verdict_is_not_added_to_usable_pool():
    errors, warnings = [], []
    row = record()
    audit = [{"dataset_citation_key": row["dataset_citation_key"],
              "audit_verdict": "SOURCE_ONLY"}]
    result = AUDIT.inspect_pair("fixture", [row], audit, errors, warnings)
    assert result["usable_records"] == 0
    assert errors == []


def test_missing_required_field_is_reported():
    errors, warnings = [], []
    row = record()
    del row["historical_status"]
    AUDIT.inspect_pair(
        "fixture", [row],
        [{"dataset_citation_key": row["dataset_citation_key"],
          "audit_verdict": "VERIFIED_EXACT"}],
        errors, warnings,
    )
    assert any(item["code"] == "MISSING_REQUIRED_FIELDS" for item in errors)


def test_legacy_act_marked_in_force_is_a_warning_not_a_pass_claim():
    errors, warnings = [], []
    row = record()
    row["act"] = "The Indian Penal Code, 1860"
    AUDIT.inspect_pair(
        "fixture", [row],
        [{"dataset_citation_key": row["dataset_citation_key"],
          "audit_verdict": "VERIFIED_EXACT"}],
        errors, warnings,
    )
    assert any(item["code"] == "REVIEW_HISTORICAL_STATUS" for item in warnings)
    assert errors == []


def test_conflicting_audit_source_url_is_reported():
    errors, warnings = [], []
    row = record()
    audit = [{
        "dataset_citation_key": row["dataset_citation_key"],
        "audit_verdict": "VERIFIED_EXACT",
        "source_url": "https://example.org/different-source",
    }]
    AUDIT.inspect_pair("fixture", [row], audit, errors, warnings)
    assert any(
        item["code"] == "CANONICAL_AUDIT_METADATA_MISMATCH"
        and item["field"] == "source_url"
        for item in errors
    )


def test_sparse_audit_metadata_remains_supported():
    errors, warnings = [], []
    row = record()
    audit = [{
        "dataset_citation_key": row["dataset_citation_key"],
        "audit_verdict": "VERIFIED_EXACT",
    }]
    AUDIT.inspect_pair("fixture", [row], audit, errors, warnings)
    assert errors == []
