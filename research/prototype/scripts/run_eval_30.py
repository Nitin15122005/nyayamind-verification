#!/usr/bin/env python
"""
MVP research evaluation: runs modes A, B, and C on the SAME deterministic
30-case sample and writes three separate JSONL outputs.

Does NOT modify src/claim_parser.py, src/evidence_matcher.py,
src/verifier.py, src/corrector.py, src/pipeline.py, src/generator.py, or
config/prototype.yaml — every record is produced by calling those modules'
existing, unmodified functions exactly as scripts/run_mvp.py does. This
script only adds new orchestration on top: (1) a deterministic 30-case
sample (scripts/run_mvp.py has no case-count/selection controls beyond
"first N, hard-capped at 5" — this is intentionally a separate, explicit
evaluation entry point, not a change to that guardrail), and (2) sharing
one generate_and_parse() call per case across all three modes so A/B/C are
a true paired comparison against an identical generated baseline (see
pipeline.py's own module docstring) instead of 3x redundant generation —
this is what "reuse loaded models ... to reduce runtime" calls for.

Usage:
  research/.venv/Scripts/python.exe research/prototype/scripts/run_eval_30.py
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

N_CASES = 30
SELECTION_SEED = 42

import yaml

from src.data_loader import load_usable_evidence, load_nyayarag_cases, select_cases_with_evidence_overlap
from src.generator import StatuteGroundingGenerator
from src.verifier import NLIVerifier
from src.corrector import SelectiveCorrector
from src import pipeline


def select_eval_cases(cases, exact_index):
    """Deterministic (seed=42) sample of N_CASES from every case with
    >=1 citation overlapping the usable evidence pool. select_cases_
    with_evidence_overlap()'s output is itself already deterministic
    (file order, no randomness), so random.Random(SELECTION_SEED).sample()
    over it is fully reproducible run to run."""
    eligible = select_cases_with_evidence_overlap(cases, exact_index, min_overlap=1)
    rng = random.Random(SELECTION_SEED)
    return rng.sample(eligible, N_CASES)


def run_one_case_all_modes(case, generator, verifier, corrector, exact_index, all_usable, config):
    """Mirrors pipeline.run_case()'s exact per-mode logic (same functions,
    same branching), but calls generate_and_parse() ONCE and reuses that
    baseline for all three modes, instead of run_case()'s one-baseline-
    per-call behavior. Returns (records_by_mode, timing_by_mode)."""
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
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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
    print(f"Loaded {len(cases)} raw NyayaRAG cases from scratch space.")

    eval_cases = select_eval_cases(cases, exact_index)
    print(f"Selected {len(eval_cases)} cases deterministically (seed={SELECTION_SEED}): "
          f"{[c.document_id for c in eval_cases]}")

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

    output_dir = repo_root / config["paths"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {mode: output_dir / f"run_{mode}_n30.jsonl" for mode in ("A", "B", "C")}
    files = {mode: paths[mode].open("w", encoding="utf-8") for mode in ("A", "B", "C")}

    run_start = time.time()
    try:
        for i, case in enumerate(eval_cases, start=1):
            print(f"[{i}/{len(eval_cases)}] Running case {case.document_id}...")
            t0 = time.time()
            records, timings = run_one_case_all_modes(
                case, gen, verifier, corrector, exact_index, all_usable, config
            )
            elapsed = time.time() - t0
            for mode in ("A", "B", "C"):
                rec = records[mode]
                rec["_timing"] = timings[mode]
                files[mode].write(json.dumps(rec, ensure_ascii=False) + "\n")
                files[mode].flush()
            print(f"  case {case.document_id} done in {elapsed:.1f}s "
                  f"(claims={len(records['C']['claims'])}, "
                  f"correction_status={records['C']['correction']['status']})")
    finally:
        for f in files.values():
            f.close()

    total_elapsed = time.time() - run_start
    print(f"\nWrote {len(eval_cases)} record(s) each to:")
    for mode in ("A", "B", "C"):
        print(f"  {paths[mode]}")
    print(f"Total wall time: {total_elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
