"""NLI sequence-length safety: never produce a verdict from truncated statute text."""
from unittest.mock import MagicMock

import pytest

from src.verifier import NLIVerifier


def test_overlength_pair_is_rejected_before_model_inference():
    verifier = NLIVerifier(
        model_id="test-model",
        confidence_threshold=0.7,
        max_sequence_length=8,
        device="cpu",
    )
    tokenizer = MagicMock()
    tokenizer.return_value = {"input_ids": list(range(9))}
    model = MagicMock()
    verifier._tokenizer = tokenizer
    verifier._model = model
    verifier._id2label_lower = {
        0: "entailment",
        1: "neutral",
        2: "contradiction",
    }

    with pytest.raises(ValueError, match="refusing to verify truncated statutory evidence"):
        verifier.verify("long canonical statute text", "claim")

    model.assert_not_called()
    assert tokenizer.call_count == 1
    assert tokenizer.call_args.kwargs["truncation"] is False


def test_input_within_limit_is_tokenized_without_truncation():
    verifier = NLIVerifier(
        model_id="test-model",
        confidence_threshold=0.7,
        max_sequence_length=8,
        device="cpu",
    )
    tokenizer = MagicMock()
    tokenizer.return_value = {"input_ids": list(range(8))}
    verifier._tokenizer = tokenizer

    # The length guard must accept exactly max_sequence_length tokens.
    untruncated = verifier._tokenizer("premise", "claim", truncation=False)
    assert len(untruncated["input_ids"]) == verifier.max_sequence_length
    assert tokenizer.call_args.kwargs["truncation"] is False
