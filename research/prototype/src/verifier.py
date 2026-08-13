"""
NLI-based statutory-claim verifier.

premise = matched canonical statute text (from canonical_statutes.jsonl,
          never NyayaRAG's own noisy `sections` text)
hypothesis = the extracted claim sentence from generated model output

Labels: ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION.

IMPORTANT — what this verifier does and does not measure: it reports the
NLI model's statistical confidence that the premise text entails/
contradicts/is neutral toward the hypothesis. That is NOT the same thing as
legal correctness. A high-confidence ENTAILED verdict means "this small
public NLI model thinks the statute text supports this sentence", not "a
lawyer confirmed this is legally accurate". See research/prototype/README.md
for why this distinction matters and is repeated in the output schema.

No model is loaded at import time — only inside NLIVerifier.load(), so this
module can be imported for tests/checks without touching the GPU or
downloading anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ENTAILED = "ENTAILED"
CONTRADICTED = "CONTRADICTED"
NOT_ENOUGH_INFORMATION = "NOT_ENOUGH_INFORMATION"

_RAW_LABEL_TO_VERDICT = {
    "entailment": ENTAILED,
    "contradiction": CONTRADICTED,
    "neutral": NOT_ENOUGH_INFORMATION,
}


@dataclass
class VerificationResult:
    label: str                 # ENTAILED | CONTRADICTED | NOT_ENOUGH_INFORMATION
    confidence: float          # softmax probability of the argmax raw NLI class
    sub_reason: Optional[str]  # None | "low_confidence" (only set when downgraded)
    raw_scores: dict           # {"entailment": p, "neutral": p, "contradiction": p}
    verifier_model: str
    disclaimer: str = (
        "NLI statistical confidence, not a legal-correctness determination."
    )


class NLIVerifier:
    def __init__(self, model_id: str, confidence_threshold: float, max_sequence_length: int = 512):
        self.model_id = model_id
        self.confidence_threshold = confidence_threshold
        self.max_sequence_length = max_sequence_length
        self._tokenizer = None
        self._model = None
        self._id2label_lower = None

    def load(self) -> None:
        """Loads the tokenizer/model. Deferred out of __init__ so that
        constructing an NLIVerifier (e.g. in tests, or before deciding
        whether a real run is even needed) never touches the GPU or
        downloads anything until this is explicitly called."""
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. This verifier is loaded alongside a "
                "4-bit 7B generator on a VRAM-constrained GPU and must not "
                "silently fall back to CPU."
            )

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        # fp16 on CUDA: this model is loaded concurrently with the 4-bit 7B
        # generator on a 6GB card (RTX 4050) — the default fp32 load nearly
        # doubles this model's VRAM footprint for no accuracy benefit at
        # inference time, so halve it instead of copying full fp32 weights
        # to the GPU only to be squeezed for headroom later.
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id, torch_dtype=torch.float16
        )
        self._model.eval()
        self._model = self._model.to("cuda")
        # Read the label order from the model's own config rather than
        # hardcoding indices — different NLI checkpoints do not all use the
        # same id2label ordering.
        self._id2label_lower = {
            i: label.lower() for i, label in self._model.config.id2label.items()
        }
        for lbl in self._id2label_lower.values():
            if lbl not in _RAW_LABEL_TO_VERDICT:
                raise ValueError(
                    f"Unexpected NLI label '{lbl}' in {self.model_id} config.id2label "
                    f"— expected entailment/neutral/contradiction. Refusing to guess."
                )

    def is_loaded(self) -> bool:
        return self._model is not None

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        if not self.is_loaded():
            raise RuntimeError("NLIVerifier.load() must be called before verify().")

        import torch

        inputs = self._tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=self.max_sequence_length,
            return_tensors="pt",
        )
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits
            probs = torch.softmax(logits, dim=-1).squeeze(0).tolist()

        raw_scores = {
            self._id2label_lower[i]: probs[i] for i in range(len(probs))
        }
        argmax_idx = max(range(len(probs)), key=lambda i: probs[i])
        argmax_label_raw = self._id2label_lower[argmax_idx]
        argmax_confidence = probs[argmax_idx]

        verdict = _RAW_LABEL_TO_VERDICT[argmax_label_raw]
        sub_reason = None
        if argmax_confidence < self.confidence_threshold:
            verdict = NOT_ENOUGH_INFORMATION
            sub_reason = "low_confidence"

        return VerificationResult(
            label=verdict,
            confidence=argmax_confidence,
            sub_reason=sub_reason,
            raw_scores=raw_scores,
            verifier_model=self.model_id,
        )
