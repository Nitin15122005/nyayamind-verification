"""
Statutory-grounding field generator.

Loads a small instruction-tuned LLM (default: Qwen/Qwen2.5-7B-Instruct) in
4-bit via bitsandbytes, following the exact BitsAndBytesConfig pattern and
accelerate/transformers version constraints already validated on this
RTX 4050 6GB machine for the RhetoricLLaMA baseline (see
research/baseline/BASELINE.md and research/requirements.txt for why
accelerate==0.29.3 specifically is required with transformers==4.40.2).

Produces ONLY the statutory_grounding field — no issue/argument/decision/
explanation. Every generation call records the exact model id, quantization
config, and generation parameters used, for the output record's
reproducibility block.

No model is loaded at import time — only inside StatuteGroundingGenerator.
load() — so this module can be imported for tests/checks without touching
the GPU or downloading anything.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class GenerationMetadata:
    model_id: str
    quantization: dict
    max_new_tokens: int
    do_sample: bool
    temperature: float
    top_p: float
    seed: int
    generated_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")


class StatuteGroundingGenerator:
    def __init__(
        self,
        model_id: str,
        quantization: dict,
        device_map: str,
        max_new_tokens: int,
        do_sample: bool,
        temperature: float,
        top_p: float,
        system_prompt: str,
        user_prompt_template: str,
        seed: int,
    ):
        self.model_id = model_id
        self.quantization = quantization
        self.device_map = device_map
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.temperature = temperature
        self.top_p = top_p
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.seed = seed
        self._tokenizer = None
        self._model = None

    def load(self) -> None:
        """Deferred model load — see module docstring. Not fine-tuning
        anything: from_pretrained only, no Trainer, no gradient updates.

        `low_cpu_mem_usage=True` and the `gc`/CUDA-cache clear immediately
        before `from_pretrained()` were added 2026-09-11 (16GB-laptop memory
        audit, outputs/16gb_memory_architecture_audit.md): `transformers`
        4.40.2 already defaults `low_cpu_mem_usage` to True whenever
        `device_map` is set (true here), so this makes an implicit default
        explicit rather than changing behavior; the gc/cache clear releases
        any allocator-cached memory left over from `import torch`/CUDA
        context init before the single largest transient allocation
        (~3.9GB per safetensors shard) that loading this model requires.
        Neither changes model identity, weights, quantization config, or
        output — purely loading-mechanics, safe to always run."""
        import gc
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. This generator loads a 7B model with a "
                "4-bit bitsandbytes CUDA quantization config and is not meant to "
                "run on CPU (silent CPU fallback would be impractically slow and "
                "is disallowed for this prototype)."
            )

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=self.quantization["load_in_4bit"],
            bnb_4bit_use_double_quant=self.quantization["bnb_4bit_use_double_quant"],
            bnb_4bit_quant_type=self.quantization["bnb_4bit_quant_type"],
            bnb_4bit_compute_dtype=getattr(torch, self.quantization["bnb_4bit_compute_dtype"]),
            llm_int8_skip_modules=[],
        )
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        gc.collect()
        torch.cuda.empty_cache()
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            quantization_config=bnb_config,
            device_map=self.device_map,
            low_cpu_mem_usage=True,
        )
        self._model.eval()

    def is_loaded(self) -> bool:
        return self._model is not None

    def _build_prompt(self, case_text: str) -> str:
        user_prompt = self.user_prompt_template.format(case_text=case_text)
        messages = [
            {"role": "system", "content": self.system_prompt.strip()},
            {"role": "user", "content": user_prompt},
        ]
        return self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    def generate(self, case_text: str) -> tuple[str, GenerationMetadata]:
        if not self.is_loaded():
            raise RuntimeError("StatuteGroundingGenerator.load() must be called before generate().")

        import torch

        torch.manual_seed(self.seed)

        prompt = self._build_prompt(case_text)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)

        gen_kwargs = dict(
            max_new_tokens=self.max_new_tokens,
            do_sample=self.do_sample,
        )
        if self.do_sample:
            gen_kwargs["temperature"] = self.temperature
            gen_kwargs["top_p"] = self.top_p

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, **gen_kwargs)

        generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        metadata = GenerationMetadata(
            model_id=self.model_id,
            quantization=self.quantization,
            max_new_tokens=self.max_new_tokens,
            do_sample=self.do_sample,
            temperature=self.temperature,
            top_p=self.top_p,
            seed=self.seed,
        )
        return text, metadata
