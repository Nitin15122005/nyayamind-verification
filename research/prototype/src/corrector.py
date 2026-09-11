"""
Selective correction: regenerate ONLY the flagged sentence within a
statutory_grounding field, preserving every other sentence unchanged.

Reuses the already-loaded generation model/tokenizer from a
StatuteGroundingGenerator instance (via its ._model/._tokenizer) instead of
loading a second model — the design calls for one correction model, reused
from generation, not a separate one.

Triggering policy (CONTRADICTED, or NOT_ENOUGH_INFORMATION with
sub_reason == "low_confidence"; never NO_EVIDENCE) is decided by the caller
(pipeline.py) — this module only performs the regeneration once asked.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CorrectionMetadata:
    model_id: str
    max_new_tokens: int
    do_sample: bool
    seed: int
    corrected_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")


class SelectiveCorrector:
    def __init__(
        self,
        generator,  # a loaded generator.StatuteGroundingGenerator instance
        max_new_tokens: int,
        do_sample: bool,
        system_prompt: str,
    ):
        self._generator = generator
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.system_prompt = system_prompt

    def correct(
        self,
        case_text: str,
        original_field_text: str,
        flagged_claim_text: str,
        evidence_text: Optional[str],
    ) -> tuple[str, CorrectionMetadata]:
        if not self._generator.is_loaded():
            raise RuntimeError("The generator passed to SelectiveCorrector must already be loaded.")

        import torch

        tokenizer = self._generator._tokenizer
        model = self._generator._model

        evidence_block = (
            f"Actual statute text:\n{evidence_text}\n"
            if evidence_text
            else "No supporting statute text is available in the evidence corpus for this claim.\n"
        )
        user_prompt = (
            f"Case facts:\n{case_text}\n\n"
            f"Original Statutory Grounding paragraph:\n{original_field_text}\n\n"
            f"Flagged sentence (unsupported or contradicted):\n{flagged_claim_text}\n\n"
            f"{evidence_block}\n"
            "Rewrite the full paragraph, changing ONLY the flagged sentence."
        )
        messages = [
            {"role": "system", "content": self.system_prompt.strip()},
            {"role": "user", "content": user_prompt},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        # Reuses the generator's own seed (same config["seed"], since this
        # corrector always wraps an already-loaded generator instance) —
        # matches StatuteGroundingGenerator.generate()'s determinism pattern
        # rather than leaving correction unseeded.
        torch.manual_seed(self._generator.seed)

        gen_kwargs = dict(max_new_tokens=self.max_new_tokens, do_sample=self.do_sample)

        with torch.no_grad():
            output_ids = model.generate(**inputs, **gen_kwargs)

        generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
        corrected_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        metadata = CorrectionMetadata(
            model_id=self._generator.model_id,
            max_new_tokens=self.max_new_tokens,
            do_sample=self.do_sample,
            seed=self._generator.seed,
        )
        return corrected_text, metadata

    def correct_assertion_span(
        self,
        case_text: str,
        target_span: str,
        evidence_text: Optional[str],
        assertion_span_system_prompt: str,
        max_new_tokens: int,
    ) -> tuple[str, CorrectionMetadata]:
        """ASSERTION-AWARE correction (added 2026-09-12): rewrites ONLY
        `target_span` -- the flagged claim's own CONTENT fragment (its
        `assertion_text`, or the description item of a multi-element
        `assertion_spans` list for a "respectively" claim -- see
        claim_parser.py's `Claim` docstring; never the structural bare-
        number element of such a list, which the caller preserves
        separately) -- a verbatim, non-fabricated sub-span of the flagged
        sentence, never the full sentence or paragraph. The caller is
        responsible for splicing the returned fragment back into the
        original text via exact-substring replacement (see pipeline.py's
        `_splice_assertion_correction()`); this method never sees or
        touches sibling assertions at all, so they cannot be altered by
        this call by construction -- not merely checked afterward,
        structurally impossible here.

        Kept as a SEPARATE method from `correct()` (not a mode flag on it):
        the prompt shape, expected output shape (one fragment, not a full
        paragraph), and post-processing (splice vs. whole-text replacement)
        are different enough that sharing one method would need its own
        internal branching anyway, and this project's own convention
        (narrow_primary_hypothesis / assertion_span_primary_hypothesis
        alongside the pre-existing full-hypothesis path) is additive
        methods/flags, never in-place replacement of a still-relevant
        legacy path — see config/prototype.yaml's `correction.assertion_aware`
        for the production/legacy switch this feeds."""
        if not self._generator.is_loaded():
            raise RuntimeError("The generator passed to SelectiveCorrector must already be loaded.")

        import torch

        tokenizer = self._generator._tokenizer
        model = self._generator._model

        evidence_block = (
            f"Actual statute text:\n{evidence_text}\n"
            if evidence_text
            else "No supporting statute text is available in the evidence corpus for this claim.\n"
        )
        user_prompt = (
            f"Case facts:\n{case_text}\n\n"
            f"Flagged fragment (unsupported or contradicted by the statute text below):\n"
            f"{target_span}\n\n"
            f"{evidence_block}\n"
            "Rewrite ONLY this fragment so it is consistent with the statute text. "
            "Preserve its grammatical role, modality (e.g. \"shall\"/\"may\"/\"must not\"), "
            "any condition or exception it states, and who/what it is about -- change only "
            "the specific fact that is wrong. Do not introduce a new citation, section "
            "number, Act name, or any fact not needed to fix this fragment. "
            "Output ONLY the corrected fragment, nothing else -- no preamble, no quotation "
            "marks, no surrounding sentence, no explanation."
        )
        messages = [
            {"role": "system", "content": assertion_span_system_prompt.strip()},
            {"role": "user", "content": user_prompt},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        torch.manual_seed(self._generator.seed)
        gen_kwargs = dict(max_new_tokens=max_new_tokens, do_sample=self.do_sample)

        with torch.no_grad():
            output_ids = model.generate(**inputs, **gen_kwargs)

        generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
        corrected_fragment = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        # Defensive stripping of the most common LLM formatting tics for a
        # "just the fragment" instruction -- surrounding quote marks are
        # never legitimate content here (assertion_text itself never starts/
        # ends with a literal quote character in this corpus).
        corrected_fragment = corrected_fragment.strip('"').strip("'").strip()

        metadata = CorrectionMetadata(
            model_id=self._generator.model_id,
            max_new_tokens=max_new_tokens,
            do_sample=self.do_sample,
            seed=self._generator.seed,
        )
        return corrected_fragment, metadata
