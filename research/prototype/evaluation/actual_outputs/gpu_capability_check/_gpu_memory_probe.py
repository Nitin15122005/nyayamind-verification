"""
STEP 10 instrumentation only — not a production module, not imported by
src/ or tests/. Wraps the real production classes (StatuteGroundingGenerator,
NLIVerifier from src/generator.py and src/verifier.py) with GPU memory
sampling around load() and one real generate() call, using the exact
repository config (research/prototype/config/prototype.yaml). No production
source is modified; this only observes it.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parents[3]  # research/prototype/
_REPO_ROOT = _PROTOTYPE_ROOT.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import torch
import yaml

from src.data_loader import load_usable_evidence_from_config, load_nyayarag_cases, select_cases_with_evidence_overlap
from src.generator import StatuteGroundingGenerator
from src.verifier import NLIVerifier


def mib(nbytes: int) -> float:
    return round(nbytes / (1024 ** 2), 1)


def snapshot(label: str) -> dict:
    torch.cuda.synchronize()
    return {
        "label": label,
        "allocated_mib": mib(torch.cuda.memory_allocated(0)),
        "reserved_mib": mib(torch.cuda.memory_reserved(0)),
        "max_allocated_mib": mib(torch.cuda.max_memory_allocated(0)),
    }


def main() -> int:
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    result = {"gpu_name": torch.cuda.get_device_name(0), "torch": torch.__version__,
              "torch_cuda": torch.version.cuda, "snapshots": []}

    torch.cuda.reset_peak_memory_stats(0)
    result["snapshots"].append(snapshot("before_any_load"))

    t0 = time.time()
    gen = StatuteGroundingGenerator(
        model_id=config["generation"]["model_id"],
        quantization=config["generation"]["quantization"],
        device_map=config["generation"]["device_map"],
        max_new_tokens=config["generation"]["max_new_tokens"],
        do_sample=config["generation"]["do_sample"],
        temperature=config["generation"]["temperature"],
        top_p=config["generation"]["top_p"],
        system_prompt=config["generation"]["system_prompt"],
        user_prompt_template=config["generation"]["user_prompt_template"],
        seed=config["seed"],
    )
    gen.load()
    result["generator_load_seconds"] = round(time.time() - t0, 2)
    result["generator_device"] = str(gen._model.device)
    result["generator_dtype_of_first_param"] = str(next(gen._model.parameters()).dtype)
    result["snapshots"].append(snapshot("after_generator_load"))

    exact_index, all_usable = load_usable_evidence_from_config(config, _REPO_ROOT)
    nyayarag_paths = [_REPO_ROOT / p for p in config["paths"]["nyayarag_case_files"]]
    cases = load_nyayarag_cases(nyayarag_paths)
    selected = select_cases_with_evidence_overlap(cases, exact_index, min_overlap=1)
    case = selected[0]
    result["probe_case_id"] = case.document_id

    t0 = time.time()
    text, meta = gen.generate(case.case_text)
    result["single_generation_seconds"] = round(time.time() - t0, 2)
    result["snapshots"].append(snapshot("after_one_generation"))
    result["generation_output_chars"] = len(text)
    result["generation_metadata"] = {
        "model_id": meta.model_id, "quantization": meta.quantization,
        "max_new_tokens": meta.max_new_tokens, "do_sample": meta.do_sample, "seed": meta.seed,
    }

    t0 = time.time()
    ver = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    ver.load()
    result["verifier_load_seconds"] = round(time.time() - t0, 2)
    result["snapshots"].append(snapshot("after_verifier_load_alongside_generator"))

    out_path = Path(__file__).parent / "gpu_memory_probe_result.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
