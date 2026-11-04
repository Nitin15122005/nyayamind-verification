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


def _validated_nli_label_map(id2label: dict) -> dict[int, str]:
    """Validate a complete, unambiguous three-class NLI label mapping."""
    if not isinstance(id2label, dict):
        raise ValueError("NLI model config.id2label must be a dictionary.")
    normalized: dict[int, str] = {}
    try:
        for index, label in id2label.items():
            normalized_index = int(index)
            if normalized_index in normalized:
                raise ValueError(
                    f"Duplicate NLI class index after normalization: {normalized_index}."
                )
            normalized[normalized_index] = str(label).strip().lower()
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "NLI model config.id2label contains an invalid or duplicate class index."
        ) from exc
    expected_indices = {0, 1, 2}
    expected_labels = set(_RAW_LABEL_TO_VERDICT)
    if set(normalized) != expected_indices or set(normalized.values()) != expected_labels:
        raise ValueError(
            "NLI model must expose exactly one each of entailment, contradiction, "
            f"and neutral at class indices 0, 1, 2; received {normalized!r}. "
            "Refusing to guess label semantics."
        )
    return normalized


PREMISE_FRAMING_BARE = "bare"
PREMISE_FRAMING_LABELED = "labeled"
PREMISE_FRAMINGS = (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED)


def format_premise(
    evidence_text: str,
    framing: str = PREMISE_FRAMING_BARE,
    provision_type: Optional[str] = None,
    provision_number: Optional[str] = None,
    act: Optional[str] = None,
) -> str:
    """Build the NLI premise from a canonical evidence record.

    "bare" is the original behaviour: the premise is the statute text alone.
    That framing has a structural problem this project measured on the
    controlled benchmark. Generated legal claims are almost always *attributed*
    ("According to Section 302 of the IPC, whoever commits murder..."), so the
    hypothesis asserts two things: the legal rule, and the fact that this rule
    is what Section 302 says. A bare premise contains the rule but never
    mentions Section 302, so the second proposition is genuinely unsupported by
    the premise and a well-behaved NLI model must answer "neutral". The NEI
    verdicts were the model being right about a premise that had been stripped
    of the very identifier the claim was about.

    "labeled" restores that identifier, so an attributed claim can actually be
    entailed. It only ever ADDS the provision label already carried on the
    audited evidence record — no legal content is invented, and the statute
    text itself is passed through untouched.

    Falls back to the bare text when the label parts are missing, so a record
    with incomplete metadata degrades to current behaviour rather than emitting
    a malformed premise like ": Whoever commits murder...".
    """
    if framing not in PREMISE_FRAMINGS:
        raise ValueError(f"framing must be one of {PREMISE_FRAMINGS}, got {framing!r}")
    if framing == PREMISE_FRAMING_BARE:
        return evidence_text
    if not (provision_type and provision_number and act):
        return evidence_text
    return f"{provision_type} {provision_number} of {act}: {evidence_text}"


@dataclass
class VerificationResult:
    label: str                 # ENTAILED | CONTRADICTED | NOT_ENOUGH_INFORMATION
    confidence: float          # softmax probability of the argmax raw NLI class
    sub_reason: Optional[str]  # None | "low_confidence" (only set when downgraded)
    raw_scores: dict           # {"entailment": p, "neutral": p, "contradiction": p}
    verifier_model: str
    # Kept for output-schema compatibility. Successful results are never
    # truncated; overlength pairs raise before model inference.
    input_truncated: bool = False
    disclaimer: str = (
        "NLI statistical confidence, not a legal-correctness determination."
    )


class NLIVerifier:
    def __init__(self, model_id: str, confidence_threshold: float, max_sequence_length: int = 512,
                 device: str = "cuda", model_revision: str | None = None):
        """`device` defaults to "cuda" and that path is unchanged: it still
        refuses to run if CUDA is missing, because in the pipeline this model
        shares a 6GB card with a 4-bit 7B generator and a silent CPU fallback
        would turn a misconfigured run into an inexplicably slow one.

        Passing device="cpu" is an explicit opt-in used by the offline
        controlled-verifier benchmark, which is pure NLI scoring with no
        generator co-resident and therefore runs fine (if slower) on CPU. It
        must be requested deliberately — never inferred from availability.
        """
        if device not in ("cuda", "cpu"):
            raise ValueError(f"device must be 'cuda' or 'cpu', got {device!r}")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must be a non-empty string.")
        if (
            not isinstance(confidence_threshold, (int, float))
            or isinstance(confidence_threshold, bool)
            or not 0.0 <= float(confidence_threshold) <= 1.0
        ):
            raise ValueError("confidence_threshold must be a number between 0 and 1.")
        if (
            not isinstance(max_sequence_length, int)
            or isinstance(max_sequence_length, bool)
            or max_sequence_length < 1
        ):
            raise ValueError("max_sequence_length must be a positive integer.")
        self.model_id = model_id
        self.model_revision = model_revision
        self.confidence_threshold = float(confidence_threshold)
        self.max_sequence_length = max_sequence_length
        self.device = device
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

        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. This verifier is loaded alongside a "
                "4-bit 7B generator on a VRAM-constrained GPU and must not "
                "silently fall back to CPU. Pass device='cpu' explicitly if "
                "you intend a CPU-only run (e.g. the offline benchmark)."
            )

        tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.model_revision)
        # fp16 on CUDA: this model is loaded concurrently with the 4-bit 7B
        # generator on a 6GB card (RTX 4050) — the default fp32 load nearly
        # doubles this model's VRAM footprint for no accuracy benefit at
        # inference time, so halve it instead of copying full fp32 weights
        # to the GPU only to be squeezed for headroom later.
        # On CPU, fp16 is kept OFF: several CPU kernels have no half
        # implementation and the ones that do are slower than fp32, so the
        # halving that pays for itself on the GPU costs on CPU.
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id, torch_dtype=dtype, revision=self.model_revision
        )
        model.eval()
        model = model.to(self.device)
        # Validate all three classes and their indices before exposing the
        # model as loaded. Partial/duplicate mappings can otherwise yield a
        # confident but semantically invalid verdict.
        id2label = _validated_nli_label_map(model.config.id2label)
        if int(getattr(model.config, "num_labels", len(id2label))) != 3:
            raise ValueError(
                f"NLI model {self.model_id} must have exactly 3 output labels."
            )
        self._tokenizer = tokenizer
        self._model = model
        self._id2label_lower = id2label

    def is_loaded(self) -> bool:
        return self._model is not None

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        if not self.is_loaded():
            raise RuntimeError("NLIVerifier.load() must be called before verify().")
        if not isinstance(premise, str) or not premise.strip():
            raise ValueError("premise must be a non-empty string.")
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("hypothesis must be a non-empty string.")

        # Never score a silently truncated premise/hypothesis pair. In
        # particular, truncating the premise can remove a trailing statutory
        # exception or proviso and produce a confident but incomplete verdict.
        # Refuse the pair before model inference; callers must treat this as
        # an explicit verification failure, not as a legal verdict.
        untruncated = self._tokenizer(premise, hypothesis, truncation=False)
        untruncated_length = len(untruncated["input_ids"])
        if untruncated_length > self.max_sequence_length:
            raise ValueError(
                "NLI input exceeds max_sequence_length "
                f"({untruncated_length} > {self.max_sequence_length}); "
                "refusing to verify truncated statutory evidence."
            )
        input_truncated = False

        inputs = self._tokenizer(
            premise,
            hypothesis,
            truncation=False,
            max_length=self.max_sequence_length,
            return_tensors="pt",
        )
        import torch
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.inference_mode():
            logits = self._model(**inputs).logits
            probs = torch.softmax(logits, dim=-1).squeeze(0).tolist()
        if len(probs) != 3 or len(self._id2label_lower) != 3:
            raise RuntimeError(
                f"NLI model returned {len(probs)} class probabilities; expected exactly 3."
            )

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
            input_truncated=input_truncated,
        )
