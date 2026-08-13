#!/usr/bin/env python
"""
CLI entry point for Prototype v0.

Usage:
  # Import/syntax check only — loads NO model, downloads nothing:
  research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check

  # Real run (loads Qwen2.5-7B-Instruct in 4-bit + the NLI verifier onto the
  # GPU, generates+verifies+[corrects] N real cases). NOT executed as part
  # of building this prototype — see README "How to run the first real
  # case" for the exact command and what to expect.
  research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py \\
      --mode C --num-cases 1 --output research/prototype/outputs/run_C_n1.jsonl

Hard-capped at MAX_ALLOWED_CASES per invocation — this script will refuse to
run more than that, by design, until a deliberate, separate decision is made
to scale up. This is not a performance limit, it's a "don't run the full
dataset yet" guardrail requested for this prototype.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as a plain script (python scripts/run_mvp.py) as well as
# `python -m research.prototype.scripts.run_mvp` by making the package root
# importable either way.
_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))  # repo root, for `research.*`
sys.path.insert(0, str(_PROTOTYPE_ROOT))                 # prototype root, for `src.*`

MAX_ALLOWED_CASES = 5


def cmd_check() -> int:
    """Import every src module and confirm the config parses. No model
    loading, no GPU use, no network access."""
    print("Checking imports (no models loaded)...")
    from src import claim_parser, data_loader, evidence_matcher, verifier, generator, corrector, pipeline  # noqa: F401

    print("  OK: src.claim_parser")
    print("  OK: src.data_loader")
    print("  OK: src.evidence_matcher")
    print("  OK: src.verifier (module only — NLIVerifier not instantiated/loaded)")
    print("  OK: src.generator (module only — StatuteGroundingGenerator not instantiated/loaded)")
    print("  OK: src.corrector")
    print("  OK: src.pipeline")

    import yaml

    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    required_top_keys = {
        "seed", "paths", "usable_evidence_verdicts", "generation",
        "claim_parsing", "evidence_matching", "verification", "correction", "modes",
    }
    missing = required_top_keys - set(config.keys())
    if missing:
        print(f"  FAIL: config missing keys: {missing}")
        return 1
    print(f"  OK: {config_path} parses and has all required top-level keys")

    # Config paths are repo-root-relative.
    repo_root = _PROTOTYPE_ROOT.parent.parent
    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    if not canonical_path.exists():
        print(f"  FAIL: canonical evidence file not found at {canonical_path}")
        return 1
    if not audit_path.exists():
        print(f"  FAIL: evidence audit file not found at {audit_path}")
        return 1
    print(f"  OK: found {canonical_path}")
    print(f"  OK: found {audit_path}")

    from src.data_loader import load_usable_evidence

    exact_index, all_usable = load_usable_evidence(
        canonical_path, audit_path, set(config["usable_evidence_verdicts"])
    )
    print(f"  OK: loaded {len(all_usable)} usable evidence records "
          f"(VERIFIED_EXACT + VERIFIED_CONTENT only, per config)")

    print("\nAll checks passed. No model was loaded, nothing was downloaded.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.num_cases > MAX_ALLOWED_CASES:
        print(
            f"Refusing to run {args.num_cases} cases: this prototype is "
            f"hard-capped at {MAX_ALLOWED_CASES} cases per invocation until "
            f"a deliberate decision is made to scale up. Re-run with "
            f"--num-cases <= {MAX_ALLOWED_CASES}."
        )
        return 1

    import yaml

    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = Path(args.config) if args.config else _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    from src.data_loader import load_usable_evidence, load_nyayarag_cases, select_cases_with_evidence_overlap
    from src.generator import StatuteGroundingGenerator
    from src.verifier import NLIVerifier
    from src.corrector import SelectiveCorrector
    from src.pipeline import run_case

    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    exact_index, all_usable = load_usable_evidence(
        canonical_path, audit_path, set(config["usable_evidence_verdicts"])
    )
    print(f"Loaded {len(all_usable)} usable evidence records.")

    nyayarag_paths = [repo_root / p for p in config["paths"]["nyayarag_case_files"]]
    cases = load_nyayarag_cases(nyayarag_paths)
    print(f"Loaded {len(cases)} raw NyayaRAG cases from scratch space.")
    selected = select_cases_with_evidence_overlap(cases, exact_index, min_overlap=1)
    print(f"{len(selected)} cases have >=1 citation overlapping the usable evidence pool.")
    if not selected:
        print("No eligible cases found. Nothing to run.")
        return 1

    run_cases = selected[: args.num_cases]
    print(f"Running mode {args.mode} on {len(run_cases)} case(s): "
          f"{[c.document_id for c in run_cases]}")

    print(f"Loading generator ({config['generation']['model_id']}, 4-bit, CUDA)... "
          f"this downloads/loads a 7B model and will take a while.")
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

    verifier = None
    corrector = None
    if args.mode in ("B", "C"):
        print(f"Loading verifier ({config['verification']['model_id']})...")
        verifier = NLIVerifier(
            model_id=config["verification"]["model_id"],
            confidence_threshold=config["verification"]["confidence_threshold"],
            max_sequence_length=config["verification"]["max_sequence_length"],
        )
        verifier.load()
    if args.mode == "C":
        corrector = SelectiveCorrector(
            generator=gen,
            max_new_tokens=config["correction"]["max_new_tokens"],
            do_sample=config["correction"]["do_sample"],
            system_prompt=config["correction"]["system_prompt"],
        )

    output_path = Path(args.output) if args.output else (
        repo_root / config["paths"]["output_dir"] / f"run_mode{args.mode}_n{len(run_cases)}.jsonl"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for case in run_cases:
            print(f"  Running case {case.document_id}...")
            record = run_case(
                case, args.mode, gen, verifier, corrector, exact_index, all_usable, config
            )
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(run_cases)} record(s) to {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Import/config check only. No model loading.")
    parser.add_argument("--mode", choices=["A", "B", "C"], default="A")
    parser.add_argument("--num-cases", type=int, default=1)
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    if args.check:
        return cmd_check()
    return cmd_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
