#!/usr/bin/env python3
"""
Fast benchmark and ablation runner.
"""
import sys
import os
import json
import time
from pathlib import Path
from collections import Counter

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.generator import StatuteGroundingGenerator
from src.llm_verifier import QwenLLMVerifier

def main():
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    bench_path = _PROTOTYPE_ROOT / "outputs" / "verifier_benchmark.jsonl"
    records = []
    with bench_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} benchmark items.", flush=True)

    # 1. DeBERTa
    print("Evaluating DeBERTa...", flush=True)
    deberta = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    deberta.load()

    deberta_preds = []
    t0 = time.time()
    for r in records:
        res = deberta.verify(r["evidence_text"], r["hypothesis"])
        deberta_preds.append(res.label)
    print(f"DeBERTa completed in {time.time()-t0:.1f}s", flush=True)

    # DeBERTa metrics
    deb_counts = Counter(deberta_preds)
    print(f"DeBERTa predictions: {dict(deb_counts)}", flush=True)

    # 2. Qwen LLM Verifier
    print("\nLoading Qwen for LLM Verifier...", flush=True)
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

    qwen_v = QwenLLMVerifier(gen)
    print("Running Qwen LLM Verifier single-pair loop...", flush=True)
    qwen_preds = []
    t0 = time.time()
    # To be extremely fast, test 15 records per class (45 total) for instant precision/recall
    sample_records = [r for r in records if r["expected_label"] == "ENTAILED"][:15] + \
                     [r for r in records if r["expected_label"] == "CONTRADICTED"][:15] + \
                     [r for r in records if r["expected_label"] == "NOT_ENOUGH_INFORMATION"][:15]

    for idx, r in enumerate(sample_records, 1):
        res = qwen_v.verify(r["evidence_text"], r["hypothesis"])
        qwen_preds.append((r["expected_label"], res.label))
        print(f"  [{idx}/{len(sample_records)}] Expected: {r['expected_label']} -> Qwen: {res.label}", flush=True)

    print(f"\nQwen completed 45 benchmark items in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
