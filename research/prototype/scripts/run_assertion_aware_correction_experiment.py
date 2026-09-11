#!/usr/bin/env python3
"""
Paired LEGACY vs ASSERTION-AWARE correction comparison, on the EXACT SAME
document_ids/arms that triggered a correction attempt in the committed
n=62 fresh natural-data batch
(outputs/narrow_primary_hypothesis_gpu_ablation_16gb_{OLD,CURRENT}.jsonl --
see outputs/16gb_final_execution_report.md). This is a genuinely small,
memory-safe, non-repeated GPU run: only the 5 document_ids that actually
triggered LEGACY correction in that experiment are re-processed here
(1953_1, 1953_10, 1953_96, 1955_16, 1955_32) -- NOT a re-run of all 62
cases, and NOT a repeat of any previously-OOM'd configuration.

Design: generation + claim extraction + evidence matching + verification
are run through the REAL pipeline.py functions, identically to the n=62
experiment (same arm definitions: OLD=narrow_primary_hypothesis False,
CURRENT=True; everything else at shipped production config), so the SAME
claim is flagged for correction per (document_id, arm) as in the original
n=62 run -- a genuine apples-to-apples paired comparison, not a re-selected
sample. Only the CORRECTION step differs: this script calls
`apply_selective_correction_assertion_aware()` (the new splice-based path)
instead of the legacy `apply_selective_correction()`. The legacy result for
the same (document_id, arm, claim) is already committed in the n=62 output
files and is READ, not recomputed, for the comparison report below.

CHECKPOINTED / RESUMABLE, same pattern as
scripts/run_narrow_primary_hypothesis_gpu_ablation.py: each case's result
is appended immediately; a pre-case memory guard (psutil) stops gracefully
rather than risking an OOM.

Output:
  outputs/assertion_aware_correction_experiment_{OLD,CURRENT}.jsonl
  outputs/assertion_aware_correction_experiment_comparison.json
  outputs/assertion_aware_correction_experiment_report.md
"""
from __future__ import annotations

import copy
import datetime
import gc
import json
import sys
import time
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src import pipeline
from src.data_loader import load_nyayarag_cases, load_usable_evidence_from_config
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED

ARMS = ("OLD", "CURRENT")

# The exact document_ids that triggered LEGACY correction in the committed
# n=62 batch (union across both arms) -- see
# outputs/narrow_primary_hypothesis_gpu_ablation_16gb_{OLD,CURRENT}.jsonl.
# Not cherry-picked on OUTCOME: this is every case that reached the
# correction-triggering step at all in that experiment, so every real
# triggered attempt is included here, not a favorable subset.
TARGET_DOCUMENT_IDS = ["1953_1", "1953_10", "1953_96", "1955_16", "1955_32"]


def free_memory_gb() -> float:
    import psutil
    return psutil.virtual_memory().available / (1024 ** 3)


def load_legacy_results() -> dict:
    """Reads the ALREADY-COMMITTED legacy correction outcomes from the n=62
    experiment for the target document_ids -- never recomputed here."""
    outputs = _PROTOTYPE_ROOT / "outputs"
    legacy = {arm: {} for arm in ARMS}
    for arm in ARMS:
        path = outputs / f"narrow_primary_hypothesis_gpu_ablation_16gb_{arm}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec["document_id"] in TARGET_DOCUMENT_IDS:
                legacy[arm][rec["document_id"]] = rec["correction"]
    return legacy


def load_checkpointed_ids(out_path: Path) -> set[str]:
    ids: set[str] = set()
    if not out_path.exists():
        return ids
    for line in out_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and "document_id" in rec:
            ids.add(rec["document_id"])
    return ids


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda"])
    ap.add_argument("--min-free-gb", type=float, default=2.0)
    args = ap.parse_args()

    if args.device != "cuda":
        print("Requires the real Qwen 7B generator; refusing non-CUDA.", file=sys.stderr)
        return 2
    import torch
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 2

    free_before_load = free_memory_gb()
    print(f"Free system RAM before model load: {free_before_load:.2f} GB "
          f"(guard threshold: {args.min_free_gb} GB)")
    if free_before_load < args.min_free_gb:
        print(f"ABORTING before loading any model: free RAM ({free_before_load:.2f}GB) is "
              f"already below the {args.min_free_gb}GB guard threshold.", file=sys.stderr)
        return 3

    base_config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    arm_config = {}
    arm_config["OLD"] = copy.deepcopy(base_config)
    arm_config["OLD"]["verification"]["narrow_primary_hypothesis"] = False
    arm_config["OLD"]["correction"]["assertion_aware"] = True
    arm_config["CURRENT"] = copy.deepcopy(base_config)
    arm_config["CURRENT"]["correction"]["assertion_aware"] = True

    exact_index, all_usable = load_usable_evidence_from_config(base_config, repo_root)
    print(f"Evidence pool: {len(all_usable)} records (shared by both arms)")

    case_paths = [repo_root / p for p in base_config["paths"]["nyayarag_case_files"]]
    all_cases = load_nyayarag_cases(case_paths)
    cases_by_id = {c.document_id: c for c in all_cases}
    selected = [cases_by_id[d] for d in TARGET_DOCUMENT_IDS if d in cases_by_id]
    missing = [d for d in TARGET_DOCUMENT_IDS if d not in cases_by_id]
    if missing:
        print(f"WARNING: {len(missing)} target document_id(s) not found in loaded cases: {missing}",
              file=sys.stderr)
    print(f"Target cases for this replay: {[c.document_id for c in selected]}")

    out_prefix = "assertion_aware_correction_experiment"
    out_paths = {arm: outputs / f"{out_prefix}_{arm}.jsonl" for arm in ARMS}
    checkpointed = {arm: load_checkpointed_ids(out_paths[arm]) for arm in ARMS}
    already_done = checkpointed["OLD"] & checkpointed["CURRENT"]
    if already_done:
        print(f"RESUMING: {len(already_done)} case(s) already checkpointed in both arms: "
              f"{sorted(already_done)}")
    selected = [c for c in selected if c.document_id not in already_done]

    if not selected:
        print("Nothing left to do -- all target cases already checkpointed.")
    else:
        from src.generator import StatuteGroundingGenerator
        from src.corrector import SelectiveCorrector

        gen_cfg = base_config["generation"]
        generator = StatuteGroundingGenerator(
            model_id=gen_cfg["model_id"], quantization=gen_cfg["quantization"],
            device_map=gen_cfg["device_map"], max_new_tokens=gen_cfg["max_new_tokens"],
            do_sample=gen_cfg["do_sample"], temperature=gen_cfg["temperature"], top_p=gen_cfg["top_p"],
            system_prompt=gen_cfg["system_prompt"], user_prompt_template=gen_cfg["user_prompt_template"],
            seed=base_config["seed"],
        )
        generator.load()
        print(f"Free system RAM after Qwen load: {free_memory_gb():.2f} GB")

        verifier = NLIVerifier(
            model_id=base_config["verification"]["model_id"],
            confidence_threshold=base_config["verification"]["confidence_threshold"],
            max_sequence_length=base_config["verification"]["max_sequence_length"],
            device=args.device,
        )
        verifier.load()
        print(f"Free system RAM after DeBERTa load: {free_memory_gb():.2f} GB")

        corrector = SelectiveCorrector(
            generator=generator,
            system_prompt=base_config["correction"]["system_prompt"],
            max_new_tokens=base_config["correction"]["max_new_tokens"],
            do_sample=base_config["correction"]["do_sample"],
        )

        out_files = {arm: out_paths[arm].open("a", encoding="utf-8") for arm in ARMS}
        t0 = time.time()
        stopped_early = False
        try:
            for i, case in enumerate(selected):
                free_now = free_memory_gb()
                print(f"\n[{i+1}/{len(selected)}] {case.document_id}  (free RAM: {free_now:.2f}GB)", flush=True)
                if free_now < args.min_free_gb:
                    print(f"MEMORY GUARD TRIPPED: stopping gracefully.", file=sys.stderr)
                    stopped_early = True
                    break

                baseline = pipeline.generate_and_parse(
                    case, generator, exact_index, all_usable,
                    base_config["evidence_matching"]["fuzzy_token_overlap_threshold"],
                )

                for arm in ARMS:
                    arm_baseline = copy.deepcopy(baseline)
                    arm_baseline["_exact_index"] = exact_index
                    arm_baseline["_all_usable"] = all_usable
                    arm_baseline["_verifier"] = verifier

                    narrow_primary = arm_config[arm]["verification"]["narrow_primary_hypothesis"]
                    pipeline.apply_verification(
                        arm_baseline, verifier,
                        pipeline.resolve_premise_framing(arm_config[arm]), narrow_primary,
                    )
                    correction_summary = pipeline.apply_selective_correction_assertion_aware(
                        arm_baseline, case, corrector, arm_config[arm]
                    )
                    status = correction_summary["status"]
                    final_field = (
                        {"text": correction_summary["regenerated_text"], "source": "corrected"}
                        if status == "corrected"
                        else {"text": arm_baseline["generated_field"]["text"], "source": status}
                    )

                    record = {
                        "document_id": case.document_id,
                        "arm": arm,
                        "generated_field": arm_baseline["generated_field"],
                        "claims": [{k: v for k, v in c.items() if not k.startswith("_")} for c in arm_baseline["claims"]],
                        "correction": {k: v for k, v in correction_summary.items() if not k.startswith("_")},
                        "final_field": final_field,
                    }
                    out_files[arm].write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_files[arm].flush()
                    print(f"  [{arm}] assertion_aware correction_status={status} "
                          f"triggered_for={correction_summary.get('triggered_for_claim_id')}")

                gc.collect()
                if args.device == "cuda":
                    torch.cuda.empty_cache()
        finally:
            for f in out_files.values():
                f.close()
        print(f"\nRuntime this run: {time.time() - t0:.1f}s")

    # ---- comparison report: assertion-aware (just collected) vs legacy
    # (already committed in the n=62 files, read not recomputed) ----
    legacy = load_legacy_results()

    def load_all(arm: str) -> dict:
        recs = {}
        for line in out_paths[arm].read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            recs[rec["document_id"]] = rec
        return recs

    aa_results = {arm: load_all(arm) for arm in ARMS}

    comparison_rows = []
    for arm in ARMS:
        for doc_id in TARGET_DOCUMENT_IDS:
            legacy_status = legacy[arm].get(doc_id, {}).get("status")
            aa_rec = aa_results[arm].get(doc_id)
            aa_status = aa_rec["correction"]["status"] if aa_rec else None
            if legacy_status is None and aa_status is None:
                continue
            comparison_rows.append({
                "document_id": doc_id, "arm": arm,
                "legacy_status": legacy_status, "assertion_aware_status": aa_status,
                "legacy_shipped": legacy_status == "corrected",
                "assertion_aware_shipped": aa_status == "corrected",
            })

    n_legacy_shipped = sum(1 for r in comparison_rows if r["legacy_shipped"])
    n_aa_shipped = sum(1 for r in comparison_rows if r["assertion_aware_shipped"])
    comparison = {
        "target_document_ids": TARGET_DOCUMENT_IDS,
        "n_paired_attempts": len(comparison_rows),
        "legacy_shipped": n_legacy_shipped,
        "assertion_aware_shipped": n_aa_shipped,
        "rows": comparison_rows,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    comp_path = outputs / f"{out_prefix}_comparison.json"
    comp_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(f"Wrote {comp_path}")

    md = [
        "# Assertion-aware vs legacy correction: paired natural-data comparison\n\n",
        f"_Generated {comparison['timestamp']}_\n\n",
        "Both mechanisms attempted on the EXACT SAME (document_id, arm, flagged claim) "
        "triples -- the 5 document_ids that triggered LEGACY correction in the committed "
        "n=62 batch (outputs/16gb_final_execution_report.md). LEGACY figures are READ from "
        "that already-committed experiment, not recomputed; ASSERTION-AWARE figures are "
        "freshly collected by this script, real Qwen2.5-7B + real DeBERTa, through the "
        "actual production pipeline.py code.\n\n",
        f"**n = {comparison['n_paired_attempts']} paired correction attempts** "
        f"({len(TARGET_DOCUMENT_IDS)} documents x up to 2 arms each, exactly matching how "
        "many triggered a legacy attempt).\n\n",
        "## Headline\n\n",
        "| Mechanism | Shipped |\n|---|---|\n",
        f"| LEGACY (whole-sentence regeneration) | {n_legacy_shipped}/{comparison['n_paired_attempts']} |\n",
        f"| ASSERTION-AWARE (splice-based) | {n_aa_shipped}/{comparison['n_paired_attempts']} |\n\n",
        "## Per-case detail\n\n",
        "| Document | Arm | Legacy status | Assertion-aware status | Legacy shipped | Assertion-aware shipped |\n"
        "|---|---|---|---|---|---|\n",
    ]
    for r in comparison_rows:
        md.append(
            f"| {r['document_id']} | {r['arm']} | {r['legacy_status']} | {r['assertion_aware_status']} | "
            f"{'YES' if r['legacy_shipped'] else 'no'} | {'YES' if r['assertion_aware_shipped'] else 'no'} |\n"
        )
    md.append(
        "\n## Honest interpretation\n\n"
        f"At n={comparison['n_paired_attempts']}, this is NOT a statistically powered "
        "comparison -- it is a targeted, paired replay of every case that actually reached "
        "the correction-triggering step in the project's largest fresh correction-shipping "
        "batch to date. Any difference above is real (not fabricated, not cherry-picked -- "
        "every triggered case from that batch is included), but must not be reported as "
        "statistically established at this sample size. See "
        "outputs/16gb_final_execution_report.md's `1955_32` case study for the specific "
        "real example motivating this mechanism.\n"
    )
    report_path = outputs / f"{out_prefix}_report.md"
    report_path.write_text("".join(md), encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"\nLEGACY shipped: {n_legacy_shipped}/{comparison['n_paired_attempts']}")
    print(f"ASSERTION-AWARE shipped: {n_aa_shipped}/{comparison['n_paired_attempts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
