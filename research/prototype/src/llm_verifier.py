"""
LLM-based statutory claim verifier using Qwen2.5-7B-Instruct.
An alternative to DeBERTa NLI designed specifically for legal domain claims
where attribution prefixes ("According to Section X...") and complex statutory
paraphrasing cause small NLI models to falsely predict NOT_ENOUGH_INFORMATION.
"""
from __future__ import annotations

import re
from typing import Optional, List, Tuple
from .verifier import VerificationResult, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION

VERIFIER_SYSTEM_PROMPT = (
    "You are an expert legal natural language inference (NLI) verifier.\n"
    "Your job is to compare a CANONICAL STATUTE EVIDENCE text against a CLAIM STATEMENT.\n\n"
    "Categorization Rules:\n"
    "1. ENTAILED: The claim's legal assertion is supported by or is a faithful paraphrase/application of the statute text. "
    "Attribution phrases such as 'According to Section X of IPC...' do NOT prevent entailment if the legal assertion matches.\n"
    "2. CONTRADICTED: The claim directly contradicts, negates, reverses, or misstates the statutory rule, duty, or penalty.\n"
    "3. NOT_ENOUGH_INFORMATION: The claim includes specific extraneous factual assertions, procedural timelines, or non-statutory conditions that cannot be derived from the statute text alone.\n\n"
    "Output MUST begin with EXACTLY ONE of these three words: ENTAILED, CONTRADICTED, or NOT_ENOUGH_INFORMATION."
)

VERIFIER_USER_TEMPLATE = (
    "STATUTE EVIDENCE:\n{premise}\n\n"
    "CLAIM STATEMENT:\n{hypothesis}\n\n"
    "VERDICT (ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION):"
)


class QwenLLMVerifier:
    def __init__(self, generator):
        """
        Wraps an existing StatuteGroundingGenerator instance to reuse the loaded Qwen GPU model.
        """
        self.generator = generator
        self.model_id = getattr(generator, "model_id", "Qwen/Qwen2.5-7B-Instruct")

    def is_loaded(self) -> bool:
        return self.generator.is_loaded()

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        return self.verify_batch([(premise, hypothesis)])[0]

    def verify_batch(self, pairs: List[Tuple[str, str]], batch_size: int = 16) -> List[VerificationResult]:
        if not self.is_loaded():
            raise RuntimeError("Underlying generator model is not loaded. Call generator.load() first.")

        import torch
        from transformers import GenerationConfig

        tokenizer = self.generator._tokenizer
        model = self.generator._model

        # Ensure padding side is left for decoder-only generation
        orig_padding_side = tokenizer.padding_side
        tokenizer.padding_side = "left"
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        results = []

        for i in range(0, len(pairs), batch_size):
            batch_pairs = pairs[i : i + batch_size]
            prompt_strs = []
            for premise, hypothesis in batch_pairs:
                user_content = VERIFIER_USER_TEMPLATE.format(premise=premise, hypothesis=hypothesis)
                messages = [
                    {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ]
                p_str = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                prompt_strs.append(p_str)

            inputs = tokenizer(prompt_strs, return_tensors="pt", padding=True)
            input_ids = inputs["input_ids"].to("cuda")
            attention_mask = inputs["attention_mask"].to("cuda")

            gen_config = GenerationConfig(
                do_sample=False,
                max_new_tokens=15,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

            with torch.no_grad():
                outputs = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    generation_config=gen_config,
                )

            for b_idx in range(len(batch_pairs)):
                new_tokens = outputs[b_idx][input_ids.shape[1]:]
                response_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

                verdict = NOT_ENOUGH_INFORMATION
                if "ENTAILED" in response_text.upper():
                    verdict = ENTAILED
                elif "CONTRADICTED" in response_text.upper():
                    verdict = CONTRADICTED
                elif "NOT_ENOUGH_INFORMATION" in response_text.upper() or "NEI" in response_text.upper():
                    verdict = NOT_ENOUGH_INFORMATION

                results.append(VerificationResult(
                    label=verdict,
                    confidence=1.0,
                    sub_reason=None,
                    raw_scores={"llm_response": response_text},
                    verifier_model=f"Qwen-LLMVerifier({self.model_id})",
                    disclaimer="Qwen2.5-7B LLM-based verification result.",
                ))

        tokenizer.padding_side = orig_padding_side
        return results
