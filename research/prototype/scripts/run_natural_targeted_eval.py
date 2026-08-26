#!/usr/bin/env python
"""
Run natural NyayaRAG evaluation over targeted cases overlapping the 59 canonical statutes.
Runs Modes A, B, and C with the real Qwen2.5-7B generator and real DeBERTa-v3-large verifier on GPU.
Outputs: outputs/run_natural_targeted.jsonl
"""
from __future__ import annotations

import copy
import datetime
import json
import random
import sys
import time
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml
from src.data_loader import load_usable_evidence, load_nyayarag_cases, select_cases_with_evidence_overlap
from src.generator import StatuteGroundingGenerator
from src.verifier import NLIVerifier
from src.corrector import SelectiveCorrector
from src import pipeline

N_TARGETED_CASES = 30
SELECTION_SEED = 42


def select_eval_cases(cases, exact_index):
    eligible = select_cases_with_evidence_overlap(cases, exact_index, min_overlap=1)
    rng = random.Random(SELECTION_SEED)
    if len(eligible) <= N_TARGETED_CASES:
        return eligible
    return rng.sample(eligible, N_TARGETED_CASES)


def run_one_case_all_modes(case, generator, verifier, corrector, exact_index, all_usable, config):
    t_gen_start = time.time()
    baseline = pipeline.generate_and_parse(
        case, generator, exact_index, all_usable,
        config["evidence_matching"]["fuzzy_token_overlap_threshold"],
    )
    generation_seconds = time.time() - t_gen_start

    records = {}
    timings = {}

    for mode in ("A", "B", "C"):
        t_mode_start = time.time()
        mb = copy.deepcopy(baseline)
        mb["_exact_index"] = exact_index
        mb["_all_usable"] = all_usable
        mb["_verifier"] = verifier

        verification_seconds = 0.0
        correction_seconds = 0.0

        if mode in ("B", "C"):
            t0 = time.time()
            pipeline.apply_verification(mb, verifier, pipeline.resolve_premise_framing(config))
            verification_seconds = time.time() - t0

        correction_summary = {
            "triggered_for_claim_id": None,
            "attempts": 0,
            "status": "not_applicable_mode_" + mode,
            "regenerated_text": None,
            "original_field_text": mb["generated_field"]["text"],
            "reverification": None,
        }
        final_field = {"text": mb["generated_field"]["text"], "source": "original"}

        if mode == "C":
            t0 = time.time()
            correction_summary = pipeline.apply_selective_correction(mb, case, corrector, config)
            correction_seconds = time.time() - t0
            if correction_summary["status"] == "corrected":
                final_field = {"text": correction_summary["regenerated_text"], "source": "corrected"}
            elif correction_summary["status"] == "correction_failed":
                final_field = {"text": mb["generated_field"]["text"], "source": "correction_failed"}
            elif correction_summary["status"] == "correction_scope_violation":
                final_field = {"text": mb["generated_field"]["text"], "source": "correction_scope_violation"}

        verifier_model_id = getattr(verifier, "model_id", None) if verifier is not None else None
        record = {
            "document_id": mb["document_id"],
            "case_text": mb["case_text"],
            "generated_field": mb["generated_field"],
            "claims": [
                {k: v for k, v in c.items() if not k.startswith("_")}
                for c in mb["claims"]
            ],
            "evidence": pipeline._summarize_evidence(mb["claims"], len(all_usable)),
            "verification": pipeline._summarize_verification(
                mb["claims"], mode, verifier_model_id, config["verification"]["confidence_threshold"],
            ),
            "correction": {k: v for k, v in correction_summary.items() if not k.startswith("_")},
            "final_field": final_field,
            "reproducibility": {
                "mode": mode,
                "seed": config["seed"],
                "generation_model": config["generation"]["model_id"],
                "verification_model": config["verification"]["model_id"] if mode in ("B", "C") else None,
                "quantization": config["generation"]["quantization"],
                "confidence_threshold": config["verification"]["confidence_threshold"],
                "premise_framing": pipeline.resolve_premise_framing(config) if mode in ("B", "C") else None,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "software_versions": pipeline._software_versions(),
            },
        }
        mode_total = generation_seconds + (time.time() - t_mode_start)
        records[mode] = record
        timings[mode] = {
            "generation_seconds": round(generation_seconds, 3),
            "verification_seconds": round(verification_seconds, 3),
            "correction_seconds": round(correction_seconds, 3),
            "total_seconds": round(mode_total, 3),
        }

    return records, timings


def main() -> int:
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    exact_index, all_usable = load_usable_evidence(
        canonical_path, audit_path, set(config["usable_evidence_verdicts"])
    )
    print(f"Loaded {len(all_usable)} usable evidence records.")

    nyayarag_paths = [repo_root / p for p in config["paths"]["nyayarag_case_files"]]
    cases = load_nyayarag_cases(nyayarag_paths)
    print(f"Loaded {len(cases)} raw NyayaRAG cases.")

    eval_cases = select_eval_cases(cases, exact_index)
    print(f"Selected {len(eval_cases)} targeted cases overlapping 59 canonical statutes.")

    print(f"Loading generator ({config['generation']['model_id']}, 4-bit, CUDA)...")
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

    print(f"Loading verifier ({config['verification']['model_id']})...")
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    verifier.load()

    corrector = SelectiveCorrector(
        generator=gen,
        max_new_tokens=config["correction"]["max_new_tokens"],
        do_sample=config["correction"]["do_sample"],
        system_prompt=config["correction"]["system_prompt"],
    )

    output_dir = _PROTOTYPE_ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "run_natural_targeted.jsonl"
    
    with output_path.open("w", encoding="utf-8") as f_out:
        for i, case in enumerate(eval_cases, start=1):
            print(f"[{i}/{len(eval_cases)}] Natural eval case {case.document_id}...")
            t0 = time.time()
            records, timings = run_one_case_all_modes(
                case, gen, verifier, corrector, exact_index, all_usable, config
            )
            elapsed = time.time() - t0
            # Write a single combined record containing all 3 modes for easy analysis
            rec_entry = {
                "document_id": case.document_id,
                "case_text": case.case_text,
                "mode_A": records["A"],
                "mode_B": records["B"],
                "mode_C": records["C"],
                "timing": timings,
            }
            f_out.write(json.dumps(rec_entry, ensure_ascii=False) + "\n")
            f_out.flush()
            print(f"  Done in {elapsed:.1f}s (claims={len(records['C']['claims'])}, correction={records['C']['correction']['status']})")

    print(f"\nWrote natural evaluation to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
