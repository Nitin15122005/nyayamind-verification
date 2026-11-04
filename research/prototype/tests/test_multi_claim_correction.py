from copy import deepcopy
from types import SimpleNamespace

import pytest

from src import pipeline


def _claim(claim_id, text, verdict=pipeline.CONTRADICTED):
    return {
        "claim_id": claim_id,
        "claim_text": text,
        "verdict": verdict,
        "sub_reason": None,
        "negation_contradiction_caveat": False,
    }


def _baseline():
    return {
        "generated_field": {"text": "Original field."},
        "claims": [_claim("c1", "First claim."), _claim("c2", "Second claim.")],
    }


def _config(limit=2):
    return {"correction": {"max_claim_corrections": limit}}


def test_multi_claim_correction_rebuilds_between_edits_and_ships_only_when_all_clear(monkeypatch):
    baseline = _baseline()
    calls = []
    rebuilds = []

    def fake_single(current, case, corrector, config, on_event=None):
        calls.append(current["generated_field"]["text"])
        target = next(c for c in current["claims"] if pipeline._should_trigger_correction(c))
        new_text = current["generated_field"]["text"] + f" Edit-{len(calls)}."
        return {
            "status": "corrected",
            "attempts": 1,
            "regenerated_text": new_text,
            "triggered_for_claim_id": target["claim_id"],
            "trigger_reason": "contradicted",
            "reverification": {"verdict": pipeline.ENTAILED},
            "corr_meta": {"model": "test"},
        }

    def fake_rebuild(current, text, config):
        refreshed = deepcopy(current)
        refreshed["generated_field"]["text"] = text
        rebuilds.append(text)
        if len(rebuilds) == 1:
            refreshed["claims"] = [_claim("new-1", "First claim.", pipeline.ENTAILED),
                                   _claim("new-2", "Second claim.")]
        else:
            refreshed["claims"] = [_claim("new-1", "First claim.", pipeline.ENTAILED),
                                   _claim("new-2", "Second claim.", pipeline.ENTAILED)]
        return refreshed

    monkeypatch.setattr(pipeline, "apply_selective_correction", fake_single)
    monkeypatch.setattr(pipeline, "_rebuild_verified_baseline", fake_rebuild)

    result = pipeline.apply_multi_claim_correction(
        baseline, SimpleNamespace(), object(), _config()
    )

    assert result["status"] == "corrected"
    assert result["attempts"] == 2
    assert len(calls) == 2
    assert calls[1].endswith("Edit-1.")
    assert result["regenerated_text"].endswith("Edit-2.")
    assert result["remaining_flagged_claims"] == 0
    assert result["atomic_batch"] is True


def test_multi_claim_correction_rolls_back_entire_batch_if_later_attempt_fails(monkeypatch):
    baseline = _baseline()
    calls = []

    def fake_single(current, case, corrector, config, on_event=None):
        calls.append(current["generated_field"]["text"])
        if len(calls) == 1:
            return {
                "status": "corrected", "attempts": 1,
                "regenerated_text": "First edit.", "triggered_for_claim_id": "c1",
                "trigger_reason": "contradicted", "reverification": {"verdict": pipeline.ENTAILED},
            }
        return {
            "status": "correction_scope_violation", "attempts": 1,
            "regenerated_text": "Unsafe second edit.", "triggered_for_claim_id": "c2",
        }

    def fake_rebuild(current, text, config):
        refreshed = deepcopy(current)
        refreshed["generated_field"]["text"] = text
        refreshed["claims"] = [_claim("c1", "First claim.", pipeline.ENTAILED),
                               _claim("c2", "Second claim.")]
        return refreshed

    monkeypatch.setattr(pipeline, "apply_selective_correction", fake_single)
    monkeypatch.setattr(pipeline, "_rebuild_verified_baseline", fake_rebuild)

    result = pipeline.apply_multi_claim_correction(
        baseline, SimpleNamespace(), object(), _config()
    )

    assert result["status"] == "multi_claim_batch_rolled_back"
    assert result["regenerated_text"] == "Original field."
    assert result["attempts"] == 2
    assert len(calls) == 2
    assert result["failed_attempt"]["status"] == "correction_scope_violation"


def test_multi_claim_limit_is_validated():
    with pytest.raises(ValueError, match="positive integer"):
        pipeline.apply_multi_claim_correction(
            _baseline(), SimpleNamespace(), object(), _config(0)
        )


def test_multi_claim_limit_does_not_silently_ship_partial_batch(monkeypatch):
    baseline = _baseline()

    def fake_single(current, case, corrector, config, on_event=None):
        target = next(c for c in current["claims"] if pipeline._should_trigger_correction(c))
        return {
            "status": "corrected", "attempts": 1,
            "regenerated_text": current["generated_field"]["text"] + " Edit.",
            "triggered_for_claim_id": target["claim_id"],
            "trigger_reason": "contradicted",
            "reverification": {"verdict": pipeline.ENTAILED},
        }

    def fake_rebuild(current, text, config):
        refreshed = deepcopy(current)
        refreshed["generated_field"]["text"] = text
        refreshed["claims"] = [_claim("c1", "First claim.", pipeline.ENTAILED),
                               _claim("c2", "Second claim.")]
        return refreshed

    monkeypatch.setattr(pipeline, "apply_selective_correction", fake_single)
    monkeypatch.setattr(pipeline, "_rebuild_verified_baseline", fake_rebuild)

    result = pipeline.apply_multi_claim_correction(
        baseline, SimpleNamespace(), object(), _config(1)
    )

    assert result["status"] == "multi_claim_limit_reached"
    assert result["regenerated_text"] == "Original field."
    assert result["remaining_flagged_claims"] == 1


def test_rebuild_verified_baseline_uses_fresh_parse_and_evidence(monkeypatch):
    fresh_claim = SimpleNamespace(
        claim_id="fresh-id", claim_text="Corrected claim.",
        assertion_text="Corrected claim.", assertion_spans=["Corrected claim."],
        citation_extracted=SimpleNamespace(as_dict=lambda: {"provision_number": "302"}),
    )
    baseline = {
        "generated_field": {"text": "Original field."},
        "claims": [{"claim_id": "old-id"}],
        "_exact_index": {}, "_all_usable": ["evidence"],
        "_verifier": object(),
    }
    parsed = []
    matched = []
    verified = []

    def extract(text):
        parsed.append(text)
        return [fresh_claim]

    def match(citation, exact_index, all_usable, threshold, **kwargs):
        matched.append((exact_index, all_usable, threshold))
        evidence = SimpleNamespace(
            dataset_citation_key="evidence-302", canonical_text="Evidence text",
            provision_type="Section", provision_number="302", act="IPC",
        )
        return SimpleNamespace(matched=True, evidence=evidence, match_method="exact")

    def verify(refreshed, verifier, framing, narrow, span):
        verified.append((refreshed, verifier))
        refreshed["claims"][0]["verdict"] = pipeline.ENTAILED

    monkeypatch.setattr(pipeline.claim_parser, "extract_claims", extract)
    monkeypatch.setattr(pipeline, "match_evidence", match)
    monkeypatch.setattr(pipeline, "apply_verification", verify)

    refreshed = pipeline._rebuild_verified_baseline(
        baseline, "Corrected claim.",
        {"evidence_matching": {"fuzzy_token_overlap_threshold": 0.8},
         "verification": {"premise_framing": "bare"}},
    )

    assert parsed == ["Corrected claim."]
    assert matched == [(baseline["_exact_index"], baseline["_all_usable"], 0.8)]
    assert refreshed["claims"][0]["claim_id"] == "fresh-id"
    assert refreshed["claims"][0]["evidence_id"] == "evidence-302"
    assert refreshed["claims"][0]["verdict"] == pipeline.ENTAILED
    assert verified == [(refreshed, baseline["_verifier"])]
    assert baseline["generated_field"]["text"] == "Original field."
    assert baseline["claims"][0]["claim_id"] == "old-id"
