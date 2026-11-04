"""
LLM-based statutory claim verifier using the already-loaded Qwen model.

This is an experimental alternative to the production DeBERTa NLI verifier.
Its verdict is categorical and uncalibrated: it must never be presented as a
probability or treated as confidence-equivalent to the NLI model.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .verifier import (
    VerificationResult,
    ENTAILED,
    CONTRADICTED,
    NOT_ENOUGH_INFORMATION,
)

VERIFIER_SYSTEM_PROMPT = (
    "You compare CANONICAL STATUTE EVIDENCE against a CLAIM STATEMENT.\n"
    "Return exactly one label as the first token.\n"
    "ENTAILED: the legal assertion is supported by the evidence.\n"
    "CONTRADICTED: the legal assertion conflicts with the evidence.\n"
    "NOT_ENOUGH_INFORMATION: the evidence does not establish either conclusion.\n"
    "Do not infer legal facts absent from the evidence."
)

VERIFIER_USER_TEMPLATE = (
    "STATUTE EVIDENCE:\n{premise}\n\n"
    "CLAIM STATEMENT:\n{hypothesis}\n\n"
    "VERDICT:"
)

_VERDICT_PREFIX = re.compile(
    r"^\s*(ENTAILED|CONTRADICTED|NOT_ENOUGH_INFORMATION)\b",
    re.IGNORECASE,
)


def _parse_verdict(response_text: str) -> str:
    """Accept only an unambiguous label at the beginning of the response.

    Any malformed, explanatory-first, or conflicting response fails closed
    to NOT_ENOUGH_INFORMATION. Substring matching is unsafe because a model
    can mention a label while actually returning a different conclusion.
    """
    match = _VERDICT_PREFIX.match(response_text or "")
    if not match:
        return NOT_ENOUGH_INFORMATION
    return match.group(1).upper()


class QwenLLMVerifier:
    def __init__(self, generator):
        """Reuse the generator's loaded model; no second model is loaded."""
        self.generator = generator
        self.model_id = getattr(generator, "model_id", "Qwen/Qwen2.5-7B-Instruct")

    def is_loaded(self) -> bool:
        return self.generator.is_loaded()

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        return self.verify_batch([(premise, hypothesis)])[0]

    def verify_batch(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: int = 16,
    ) -> List[VerificationResult]:
        if not self.is_loaded():
            raise RuntimeError(
                "Underlying generator model is not loaded. Call generator.load() first."
            )
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer.")
        if not pairs:
            return []
        for index, pair in enumerate(pairs):
            if (
                not isinstance(pair, (tuple, list))
                or len(pair) != 2
                or not all(isinstance(value, str) and value.strip() for value in pair)
            ):
                raise ValueError(
                    f"Each verification pair must contain non-empty premise and hypothesis strings; "
                    f"invalid pair at index {index}."
                )

        import torch
        from transformers import GenerationConfig

        tokenizer = self.generator._tokenizer
        model = self.generator._model
        original_padding_side = tokenizer.padding_side
        original_pad_token = tokenizer.pad_token
        results: list[VerificationResult] = []

        try:
            # Decoder-only batched generation requires left padding.
            tokenizer.padding_side = "left"
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            device = model.device

            for start in range(0, len(pairs), batch_size):
                batch_pairs = pairs[start : start + batch_size]
                prompts = []
                for premise, hypothesis in batch_pairs:
                    messages = [
                        {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": VERIFIER_USER_TEMPLATE.format(
                                premise=premise, hypothesis=hypothesis
                            ),
                        },
                    ]
                    prompts.append(
                        tokenizer.apply_chat_template(
                            messages,
                            tokenize=False,
                            add_generation_prompt=True,
                        )
                    )

                inputs = tokenizer(prompts, return_tensors="pt", padding=True)
                input_ids = inputs["input_ids"].to(device)
                attention_mask = inputs["attention_mask"].to(device)
                generation_config = GenerationConfig(
                    do_sample=False,
                    max_new_tokens=15,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )

                with torch.inference_mode():
                    outputs = model.generate(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        generation_config=generation_config,
                    )

                for batch_index in range(len(batch_pairs)):
                    generated_tokens = outputs[batch_index][input_ids.shape[1] :]
                    response_text = tokenizer.decode(
                        generated_tokens, skip_special_tokens=True
                    ).strip()
                    verdict = _parse_verdict(response_text)
                    results.append(
                        VerificationResult(
                            label=verdict,
                            # The generative verifier exposes no calibrated
                            # class probabilities. Zero means unavailable,
                            # not a measured 0% probability.
                            confidence=0.0,
                            sub_reason="unscored_llm_verdict",
                            raw_scores={
                                "llm_response": response_text,
                                "confidence_semantics": "uncalibrated; no probability available",
                            },
                            verifier_model=f"Qwen-LLMVerifier({self.model_id})",
                            disclaimer=(
                                "Experimental generative verdict; confidence is unscored "
                                "and is not a calibrated probability."
                            ),
                        )
                    )
        finally:
            tokenizer.padding_side = original_padding_side
            tokenizer.pad_token = original_pad_token

        return results
