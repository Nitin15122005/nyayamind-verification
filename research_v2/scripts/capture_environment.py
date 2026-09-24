#!/usr/bin/env python3
"""Capture experiment environment without loading any model weights."""
from __future__ import annotations
import datetime, json, platform, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import torch, transformers

def revision(path):
    metadata = Path(path) / ".cache" / "huggingface" / "download" / "config.json.metadata"
    try: return metadata.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError): return None

def package(name):
    try: return __import__(name).__version__
    except Exception: return None

environment = {
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None,
    "python": platform.python_version(), "torch": torch.__version__,
    "transformers": transformers.__version__, "cuda_runtime": torch.version.cuda,
    "accelerate": package("accelerate"), "bitsandbytes": package("bitsandbytes"),
    "cuda_available": torch.cuda.is_available(),
    "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "gpu_total_memory_bytes": torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None,
    "models": {"baseline_generator": "Qwen/Qwen2.5-7B-Instruct",
               "baseline_verifier": "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
               "v2_generator": "Qwen/Qwen3-4B-Instruct-2507",
               "v2_verifier": "tasksource/ModernBERT-large-nli"},
    "local_checkpoint_paths": {"v2_generator": str((ROOT / "research_v2/models/Qwen3-4B-Instruct-2507").resolve()),
                                "v2_verifier": str((ROOT / "research_v2/models/ModernBERT-large-nli").resolve())},
    "model_revisions": {"v2_generator": revision(ROOT / "research_v2/models/Qwen3-4B-Instruct-2507"),
                        "v2_verifier": revision(ROOT / "research_v2/models/ModernBERT-large-nli")},
    "qwen3_generation": {"quantization": "4bit_nf4", "double_quant": True, "compute_dtype": "bfloat16", "max_input_tokens": 8192, "max_output_tokens": 200, "temperature": 1.0, "top_p": 1.0, "do_sample": False, "seed": 42},
    "modernbert_verification": {"max_position_length": 2048, "confidence_threshold": 0.70, "long_input_policy": "ordered evidence chunks, complete claim repeated, equal-weight mean probabilities; never drops evidence"},
    "seed": 42, "note": "Environment capture; v2 models were not loaded."
}
out = ROOT / "research_v2" / "results" / "reports" / "environment.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(environment, indent=2), encoding="utf-8")
print(out)
