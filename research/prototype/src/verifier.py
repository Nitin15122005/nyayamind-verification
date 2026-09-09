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
    # Measurement instrumentation, not live behavior — never changes the
    # verdict/confidence/sub_reason above. True when premise+hypothesis
    # together exceed max_sequence_length, meaning HF's pair-truncation
    # silently cut content from the END of the premise (verified empirically
    # against this project's cached tokenizer: the premise, not the
    # hypothesis, is trimmed first) before this verdict was computed —
    # exactly where a real statute's trailing exception/proviso clause would
    # sit. Confirmed inert against the current 136-record evidence corpus
    # (the longest real record + a realistic claim sentence total ~354/512
    # tokens), but previously had zero detection: a future longer record
    # could silently produce a verdict from truncated evidence with no
    # trace in the output record. Same shape as the (separately fixed)
    # evidence-matcher year-blindness gap — real, checked, currently-safe,
    # worth closing before it can bite.
    input_truncated: bool = False
    disclaimer: str = (
        "NLI statistical confidence, not a legal-correctness determination."
    )


class NLIVerifier:
    def __init__(self, model_id: str, confidence_threshold: float, max_sequence_length: int = 512,
                 device: str = "cuda"):
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
        self.model_id = model_id
        self.confidence_threshold = confidence_threshold
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

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        # fp16 on CUDA: this model is loaded concurrently with the 4-bit 7B
        # generator on a 6GB card (RTX 4050) — the default fp32 load nearly
        # doubles this model's VRAM footprint for no accuracy benefit at
        # inference time, so halve it instead of copying full fp32 weights
        # to the GPU only to be squeezed for headroom later.
        # On CPU, fp16 is kept OFF: several CPU kernels have no half
        # implementation and the ones that do are slower than fp32, so the
        # halving that pays for itself on the GPU costs on CPU.
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id, torch_dtype=dtype
        )
        self._model.eval()
        self._model = self._model.to(self.device)
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

        # Detect (never prevent) truncation: tokenize the SAME pair without
        # truncation first, purely to measure its true combined length —
        # this is a cheap, CPU-only tokenizer call (no model forward pass),
        # not a second inference. HF's default pair-truncation trims the
        # FIRST sequence (the premise, here) from its end when the pair
        # exceeds max_length (verified empirically against this project's
        # cached tokenizer) — exactly where a real statute's trailing
        # exception/proviso clause would sit. Detection only; the actual
        # model call below is unchanged (still truncates exactly as before)
        # — this never alters what verdict is computed, only whether the
        # caller can tell afterward that the input was cut.
        untruncated_length = len(self._tokenizer(premise, hypothesis)["input_ids"])
        input_truncated = untruncated_length > self.max_sequence_length

        inputs = self._tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=self.max_sequence_length,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

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
            input_truncated=input_truncated,
        )
