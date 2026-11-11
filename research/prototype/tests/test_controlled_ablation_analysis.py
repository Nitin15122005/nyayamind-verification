from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPT_DIR))

from analyze_controlled_assertion_ablation import analyze, exact_binomial_two_sided_p


def _metrics():
    common = {
        "use_evidence_v1": True,
        "premise_framing": "labeled",
        "atomic_scope_check": "assertion_spans",
        "narrow_reverification_hypothesis": True,
        "confidence_threshold": 0.70,
        "narrow_primary_hypothesis": True,
        "assertion_span_primary_hypothesis": False,
        "correction_max_new_tokens": 220,
        "evidence_pool_size": 136,
    }
    return {
        "experiment": "test",
        "arm_definitions": {
            "A": {**common, "assertion_aware_correction": False},
            "B": {**common, "assertion_aware_correction": True},
        },
        "per_arm": {
            "A": {"correction_statuses": {"corrected": 1, "correction_failed": 1},
                  "correction_attempts": 2, "corrections_shipped_success": 1},
            "B": {"correction_statuses": {"corrected": 2},
                  "correction_attempts": 2, "corrections_shipped_success": 2},
        },
    }


def test_exact_binomial_two_sided_p_for_one_discordant_pair_is_one():
    assert exact_binomial_two_sided_p(0, 1) == 1.0


def test_paired_analysis_reports_both_arm_discordance_and_validates_parity():
    details = [
        {"arm": "A", "document_id": "doc1", "status": "corrected", "corr_meta": {"max_new_tokens": 220}},
        {"arm": "B", "document_id": "doc1", "status": "corrected", "corr_meta": {"max_new_tokens": 220}},
        {"arm": "A", "document_id": "doc2", "status": "correction_failed", "corr_meta": {"max_new_tokens": 220}},
        {"arm": "B", "document_id": "doc2", "status": "corrected", "corr_meta": {"max_new_tokens": 220}},
    ]
    result = analyze(_metrics(), details)
    assert result["integrity_errors"] == []
    assert result["paired_outcomes"] == {
        "both_shipped": 1,
        "arm_a_only_shipped": 0,
        "arm_b_only_shipped": 1,
        "neither_shipped": 0,
    }
    assert result["exact_mcnemar_two_sided_p"] == 1.0


def test_paired_analysis_rejects_unequal_arm_settings():
    metrics = _metrics()
    metrics["arm_definitions"]["B"]["evidence_pool_size"] = 137
    details = [
        {"arm": "A", "document_id": "doc1", "status": "corrected", "corr_meta": {"max_new_tokens": 220}},
        {"arm": "B", "document_id": "doc1", "status": "corrected", "corr_meta": {"max_new_tokens": 220}},
    ]
    result = analyze(metrics, details)
    assert any("evidence_pool_size" in error for error in result["integrity_errors"])
