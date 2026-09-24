from research_v2.src.evaluation.metrics import classification_metrics
from research_v2.src.comparison.paired import pair_predictions, mcnemar_exact
from research_v2.src.verification.modernbert_verifier import ModernBertVerifier


def test_metrics_with_extra_outcome_and_failure():
    got = classification_metrics(["CONTRADICTED", "ENTAILED", "NOT_ENOUGH_INFORMATION"],
                                 ["NO_EVIDENCE", "ENTAILED", None])
    assert got["n"] == 3
    assert got["accuracy"] == 1 / 3
    assert got["confusion_matrix"]["CONTRADICTED"]["NO_EVIDENCE"] == 1
    assert got["confusion_matrix"]["NOT_ENOUGH_INFORMATION"]["INFERENCE_FAILURE"] == 1


def test_pairing_and_exact_mcnemar():
    base = [{"id": "a", "predicted_label": "ENTAILED"}, {"id": "b", "predicted_label": "ENTAILED"}]
    new = [{"id": "a", "predicted_label": "CONTRADICTED"}, {"id": "b", "predicted_label": "CONTRADICTED"}]
    gold = {"a": "CONTRADICTED", "b": "ENTAILED"}
    assert pair_predictions(base, new, gold)[0]["category"] == "v2_improves"
    result = mcnemar_exact(base, new, gold)
    assert result["baseline_only_correct"] == 1
    assert result["v2_only_correct"] == 1
    assert result["exact_two_sided_p"] == 1.0


def test_modernbert_pipeline_wrapper_matches_existing_correction_policy(monkeypatch):
    import research_v2.scripts.run_full_pipeline as runner
    from src.pipeline import _should_trigger_correction
    class FakeVerifier:
        model_id = "tasksource/ModernBERT-large-nli"
        def __init__(self, config): self.model = object(); self.config = config
        def verify(self, premise, hypothesis):
            return {"normalized_verdict":"NOT_ENOUGH_INFORMATION","confidence":0.55,
                    "sub_reason":"low_confidence","probability_distribution":{"entailment":0.25,"neutral":0.55,"contradiction":0.20},
                    "token_lengths":{"truncated":False}}
    monkeypatch.setattr("research_v2.src.verification.modernbert_verifier.ModernBertVerifier", FakeVerifier)
    wrapped=runner.ModernPipelineVerifier("cpu")
    result=wrapped.verify("evidence","claim")
    claim={"verdict":result.label,"sub_reason":result.sub_reason,"confidence":result.confidence}
    assert result.label=="NOT_ENOUGH_INFORMATION"
    assert _should_trigger_correction(claim) is True
    assert _should_trigger_correction({"verdict":"NOT_ENOUGH_INFORMATION","sub_reason":None}) is False
    assert _should_trigger_correction({"verdict":"NO_EVIDENCE","sub_reason":None}) is False
