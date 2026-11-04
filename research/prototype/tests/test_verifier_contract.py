"""Contract tests for fail-closed NLI model configuration."""
import pytest

from src.verifier import (
    ENTAILED,
    CONTRADICTED,
    NOT_ENOUGH_INFORMATION,
    NLIVerifier,
    _validated_nli_label_map,
)


def test_nli_label_map_accepts_all_three_classes_independent_of_order():
    mapping = _validated_nli_label_map({
        0: "CONTRADICTION",
        1: "NEUTRAL",
        2: "ENTAILMENT",
    })
    assert mapping == {
        0: "contradiction",
        1: "neutral",
        2: "entailment",
    }


@pytest.mark.parametrize("mapping", [
    {0: "entailment", 1: "neutral"},
    {0: "entailment", 1: "neutral", 2: "neutral"},
    {0: "entailment", 1: "neutral", 2: "unknown"},
    {1: "entailment", 2: "neutral", 3: "contradiction"},
    {"zero": "entailment", 1: "neutral", 2: "contradiction"},
    None,
])
def test_nli_label_map_rejects_incomplete_or_ambiguous_classes(mapping):
    with pytest.raises(ValueError):
        _validated_nli_label_map(mapping)


@pytest.mark.parametrize("kwargs", [
    {"model_id": ""},
    {"confidence_threshold": -0.01},
    {"confidence_threshold": 1.01},
    {"confidence_threshold": True},
    {"max_sequence_length": 0},
    {"max_sequence_length": 1.5},
    {"device": "auto"},
])
def test_nli_verifier_rejects_invalid_configuration(kwargs):
    defaults = {
        "model_id": "test/model",
        "confidence_threshold": 0.7,
        "max_sequence_length": 512,
        "device": "cpu",
    }
    defaults.update(kwargs)
    with pytest.raises(ValueError):
        NLIVerifier(**defaults)
