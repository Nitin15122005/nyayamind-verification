"""Regression tests for the production correction-trigger policy.

These tests deliberately use a scripted verifier/corrector. They verify the
decision boundary without loading Qwen or DeBERTa.

The production policy is:
  CONTRADICTED -> trigger
  NOT_ENOUGH_INFORMATION + sub_reason=low_confidence -> trigger
  genuine high-confidence NOT_ENOUGH_INFORMATION -> no trigger
  ENTAILED -> no trigger
  NO_EVIDENCE -> no trigger
"""
from __future__ import annotations

from src import pipeline
from src.verifier import CONTRADICTED, ENTAILED, NOT_ENOUGH_INFORMATION
from src.evidence_matcher import NO_EVIDENCE


def _claim(verdict: str, sub_reason=None) -> dict:
    return {
        "claim_id": "c1",
        "claim_text": "Section 302 prescribes punishment for murder.",
        "verdict": verdict,
        "sub_reason": sub_reason,
    }


def test_high_confidence_nei_does_not_trigger():
    claim = _claim(NOT_ENOUGH_INFORMATION, None)
    assert pipeline._correction_trigger_reason(claim) is None
    assert pipeline._should_trigger_correction(claim) is False


def test_low_confidence_nei_triggers():
    claim = _claim(NOT_ENOUGH_INFORMATION, "low_confidence")
    assert pipeline._correction_trigger_reason(claim) == "low_confidence_nei"
    assert pipeline._should_trigger_correction(claim) is True


def test_contradicted_triggers():
    claim = _claim(CONTRADICTED, None)
    assert pipeline._correction_trigger_reason(claim) == "contradicted"
    assert pipeline._should_trigger_correction(claim) is True


def test_entailed_does_not_trigger():
    claim = _claim(ENTAILED, None)
    assert pipeline._correction_trigger_reason(claim) is None
    assert pipeline._should_trigger_correction(claim) is False


def test_no_evidence_does_not_trigger():
    claim = _claim(NO_EVIDENCE, None)
    assert pipeline._correction_trigger_reason(claim) is None
    assert pipeline._should_trigger_correction(claim) is False


def test_annotation_is_auditable_for_each_claim():
    claims = [
        _claim(NOT_ENOUGH_INFORMATION, None),
        {**_claim(NOT_ENOUGH_INFORMATION, "low_confidence"), "claim_id": "c2"},
        {**_claim(CONTRADICTED), "claim_id": "c3"},
        {**_claim(ENTAILED), "claim_id": "c4"},
    ]
    pipeline._annotate_correction_triggers(claims)

    assert claims[0]["correction_trigger"] is False
    assert claims[0]["correction_trigger_reason"] is None

    assert claims[1]["correction_trigger"] is True
    assert claims[1]["correction_trigger_reason"] == "low_confidence_nei"

    assert claims[2]["correction_trigger"] is True
    assert claims[2]["correction_trigger_reason"] == "contradicted"

    assert claims[3]["correction_trigger"] is False
    assert claims[3]["correction_trigger_reason"] is None


def test_trigger_policy_does_not_depend_on_confidence_for_contradiction():
    for confidence in (0.01, 0.50, 0.99, 1.0):
        claim = {**_claim(CONTRADICTED), "confidence": confidence}
        assert pipeline._should_trigger_correction(claim) is True


def test_unknown_verdict_fails_closed():
    claim = _claim("UNKNOWN", None)
    assert pipeline._correction_trigger_reason(claim) is None
    assert pipeline._should_trigger_correction(claim) is False


def test_legacy_sentence_splice_replaces_only_unique_target_sentence():
    original = (
        "Section 302 provides punishment for murder. "
        "Section 34 requires common intention."
    )
    corrected = pipeline._splice_flagged_sentence(
        original,
        "Section 302 provides punishment for murder.",
        "Section 302 provides punishment for murder with imprisonment for life.",
    )
    assert corrected == (
        "Section 302 provides punishment for murder with imprisonment for life. "
        "Section 34 requires common intention."
    )


def test_legacy_sentence_splice_fails_closed_on_duplicate_target():
    original = (
        "Section 302 provides punishment for murder. "
        "Section 34 requires common intention. "
        "Section 302 provides punishment for murder."
    )
    assert pipeline._splice_flagged_sentence(
        original,
        "Section 302 provides punishment for murder.",
        "Corrected Section 302 sentence.",
    ) is None


def test_legacy_sentence_splice_fails_closed_on_empty_correction():
    original = "Section 302 provides punishment for murder."
    assert pipeline._splice_flagged_sentence(
        original,
        "Section 302 provides punishment for murder.",
        "",
    ) is None
