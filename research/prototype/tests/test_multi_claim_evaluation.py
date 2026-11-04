from types import SimpleNamespace

from src import pipeline
from scripts import evaluate_multi_claim_correction as evaluation


def _claim(claim_id):
    return {
        "claim_id": claim_id,
        "claim_text": f"Claim {claim_id}",
        "verdict": pipeline.CONTRADICTED,
        "sub_reason": None,
        "negation_contradiction_caveat": False,
    }


def test_fork_baseline_copies_mutable_state_but_preserves_model_references():
    verifier = object()
    baseline = {
        "generated_field": {"text": "Original"},
        "claims": [_claim("c1")],
        "_verifier": verifier,
        "_exact_index": {"x": ["y"]},
    }
    fork = evaluation._fork_baseline(baseline)
    fork["generated_field"]["text"] = "Changed"
    fork["claims"][0]["verdict"] = pipeline.ENTAILED
    assert baseline["generated_field"]["text"] == "Original"
    assert baseline["claims"][0]["verdict"] == pipeline.CONTRADICTED
    assert fork["_verifier"] is verifier
    assert fork["_exact_index"] is baseline["_exact_index"]


def test_paired_evaluation_generates_once_and_uses_identical_initial_baseline(monkeypatch):
    calls = {"generate": 0, "verify": 0, "legacy": 0, "multi": 0, "rebuild": 0}
    template = {
        "document_id": "case-1", "case_text": "Case facts",
        "generated_field": {"text": "Same original text"},
        "claims": [_claim("c1"), _claim("c2")],
    }

    def fake_generate(*args):
        calls["generate"] += 1
        return evaluation._fork_baseline(template)

    def fake_verify(*args):
        calls["verify"] += 1

    def fake_legacy(baseline, *args, **kwargs):
        calls["legacy"] += 1
        assert baseline["generated_field"]["text"] == "Same original text"
        return {"status": "corrected", "attempts": 1, "regenerated_text": "Legacy candidate"}

    def fake_multi(baseline, case, corrector, config, **kwargs):
        calls["multi"] += 1
        assert baseline["generated_field"]["text"] == "Same original text"
        assert config["correction"]["max_claim_corrections"] == 2
        return {"status": "corrected", "attempts": 2, "regenerated_text": "Multi candidate"}

    def fake_rebuild(baseline, text, config):
        calls["rebuild"] += 1
        refreshed = evaluation._fork_baseline(baseline)
        refreshed["generated_field"]["text"] = text
        refreshed["claims"] = [
            dict(claim, verdict=pipeline.ENTAILED) for claim in baseline["claims"]
        ]
        return refreshed

    monkeypatch.setattr(pipeline, "generate_and_parse", fake_generate)
    monkeypatch.setattr(pipeline, "apply_verification", fake_verify)
    monkeypatch.setattr(pipeline, "resolve_premise_framing", lambda config: "bare")
    monkeypatch.setattr(pipeline, "apply_selective_correction", fake_legacy)
    monkeypatch.setattr(pipeline, "apply_multi_claim_correction", fake_multi)
    monkeypatch.setattr(pipeline, "_rebuild_verified_baseline", fake_rebuild)

    config = {
        "seed": 42,
        "evidence_matching": {"fuzzy_token_overlap_threshold": 0.8},
        "verification": {"confidence_threshold": 0.8},
        "correction": {"max_claim_corrections": 3, "assertion_aware": False},
    }
    result = evaluation.evaluate_case(
        SimpleNamespace(document_id="case-1"),
        object(), object(), object(), {}, [], config,
    )
    assert result is not None
    assert result["pairing"]["same_initial_text"] is True
    assert result["pairing"]["same_initial_claims"] is True
    assert result["legacy"]["shipped_text"] == "Legacy candidate"
    assert result["multi_claim"]["shipped_text"] == "Multi candidate"
    assert result["legacy"]["candidate_audit"]["remaining_flagged_claims"] == 0
    assert result["multi_claim"]["candidate_audit"]["remaining_flagged_claims"] == 0
    assert calls == {"generate": 1, "verify": 1, "legacy": 1, "multi": 1, "rebuild": 2}
