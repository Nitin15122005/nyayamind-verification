"""Independent Qwen3 generation/correction adapter for research_v2."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import random
import os
import time
from typing import Any, Optional

MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"

def _local_revision(path: str | None) -> str | None:
    if not path:
        return None
    metadata = __import__("pathlib").Path(path) / ".cache" / "huggingface" / "download" / "config.json.metadata"
    try:
        value = metadata.read_text(encoding="utf-8").splitlines()[0].strip()
        return value or None
    except (OSError, IndexError):
        return None

@dataclass(frozen=True)
class Qwen3Config:
    model_id: str = MODEL_ID
    device: str = "cuda"  # Explicitly set to cpu to use the CPU fallback.
    allow_cpu_fallback: bool = False
    quantization: str = "4bit_nf4"  # none | 4bit_nf4
    dtype: str = "bfloat16"
    max_input_length: int = 8192
    max_new_tokens: int = 200
    temperature: float = 1.0
    top_p: float = 1.0
    do_sample: bool = False
    seed: int = 42
    trust_remote_code: bool = False
    model_path: Optional[str] = None

    def __post_init__(self):
        if self.model_id != MODEL_ID:
            raise ValueError(f"This adapter is pinned to {MODEL_ID}")
        if self.quantization not in {"none", "4bit_nf4"}:
            raise ValueError("quantization must be none or 4bit_nf4")
        if self.max_input_length < 1 or self.max_new_tokens < 1:
            raise ValueError("token limits must be positive")

class Qwen3Adapter:
    def __init__(self, config: Qwen3Config = Qwen3Config(), model=None, tokenizer=None):
        self.config = config
        self.model, self.tokenizer = model, tokenizer
        self.device = config.device
        self._load_s = 0.0
        self.model_revision = None
        self.model_source = config.model_path or os.environ.get("NYAYAMIND_QWEN3_PATH") or config.model_id
        if model is None or tokenizer is None:
            self._load()

    def _load(self):
        started = time.perf_counter()
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            if self.config.device.startswith("cuda") and not torch.cuda.is_available():
                if self.config.allow_cpu_fallback:
                    self.device = "cpu"
                else:
                    raise RuntimeError("CUDA requested but unavailable; set allow_cpu_fallback=True explicitly")
            dtype = getattr(torch, self.config.dtype, None)
            if dtype is None:
                raise ValueError(f"Unsupported torch dtype: {self.config.dtype}")
            source = self.config.model_path or os.environ.get("NYAYAMIND_QWEN3_PATH") or self.config.model_id
            self.model_source = source
            local_only = source != self.config.model_id
            self.tokenizer = AutoTokenizer.from_pretrained(source, trust_remote_code=self.config.trust_remote_code, local_files_only=local_only)
            kwargs: dict[str, Any] = {"dtype": dtype, "trust_remote_code": self.config.trust_remote_code, "local_files_only": local_only}
            if self.device.startswith("cuda"):
                kwargs["device_map"] = {"": int(self.device.split(":")[1]) if ":" in self.device else 0}
            else:
                kwargs["device_map"] = {"": "cpu"}
            if self.config.quantization == "4bit_nf4":
                from transformers import BitsAndBytesConfig
                kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype)
            self.model = AutoModelForCausalLM.from_pretrained(source, **kwargs)
            self.model.eval()
            self.model_revision = getattr(getattr(self.model, "config", None), "_commit_hash", None) or _local_revision(source if local_only else None)
        except Exception:
            self.model = self.tokenizer = None
            raise
        finally:
            self._load_s = time.perf_counter() - started

    def _memory(self):
        try:
            import torch
            if self.device.startswith("cuda") and torch.cuda.is_available():
                return int(torch.cuda.max_memory_allocated(torch.device(self.device)))
        except Exception:
            pass
        return None

    def generate(self, prompt: str, *, system_prompt: Optional[str] = None, max_new_tokens: Optional[int] = None) -> dict[str, Any]:
        """Generate one completion; returns text plus reproducibility/timing metadata."""
        import torch
        random.seed(self.config.seed); torch.manual_seed(self.config.seed)
        if self.device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.config.seed); torch.cuda.reset_peak_memory_stats(torch.device(self.device))
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": prompt}]
        # This exact 2507 Instruct checkpoint is the non-thinking variant;
        # its model card says the thinking flag is no longer required.
        formatted = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        # The production Qwen path does not truncate case prompts. Match that
        # behavior: fail explicitly if the configured memory-safe ceiling is
        # exceeded rather than cutting potentially relevant facts silently.
        measured = self.tokenizer(formatted, add_special_tokens=True, truncation=False)
        input_length = len(measured["input_ids"])
        if input_length > self.config.max_input_length:
            raise ValueError(f"Prompt is {input_length} tokens, above configured max_input_length={self.config.max_input_length}; refusing silent truncation")
        encoded = self.tokenizer(formatted, return_tensors="pt", truncation=False)
        model_device = getattr(self.model, "device", self.device)
        encoded = {k: v.to(model_device) for k, v in encoded.items()}
        start = time.perf_counter()
        with torch.inference_mode():
            output = self.model.generate(**encoded, max_new_tokens=max_new_tokens or self.config.max_new_tokens,
                do_sample=self.config.do_sample, temperature=self.config.temperature,
                top_p=self.config.top_p, pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id)
        elapsed = time.perf_counter() - start
        completion = output[0, encoded["input_ids"].shape[1]:]
        config_record=asdict(self.config);config_record["model_path"]=self.model_source if self.model_source != self.config.model_id else None
        return {"text": self.tokenizer.decode(completion, skip_special_tokens=True).strip(),
                "latency_seconds": elapsed, "input_tokens": input_length,
                "input_truncated": False,
                "output_tokens": int(completion.shape[0]), "peak_gpu_memory_bytes": self._memory(),
                "model_id": self.config.model_id, "model_revision": getattr(getattr(self.model,"config",None), "_commit_hash", None) or self.model_revision,
                "transformers_version": __import__("transformers").__version__,
                "torch_version": torch.__version__,"device": self.device, "config": config_record}

    def correct(self, prompt: str, **kwargs) -> dict[str, Any]:
        """Correction uses the same deterministic generation contract as ordinary drafting."""
        return self.generate(prompt, **kwargs)
