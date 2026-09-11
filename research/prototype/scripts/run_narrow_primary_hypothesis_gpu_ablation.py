#!/usr/bin/env python3
"""
Fresh end-to-end GPU ablation, isolating EXACTLY the
verification.narrow_primary_hypothesis lever (Stage 4), on a genuinely
fresh natural-data batch never used in any prior experiment in this repo.

Unlike scripts/run_final_gpu_validation.py (which varies FOUR levers
together, including the evidence pool itself), this script holds
EVERYTHING else at the current shipped production config
(config/prototype.yaml, unmodified) and only flips
verification.narrow_primary_hypothesis: false (Arm OLD, i.e. the config as
it stood at commit c250a0e, immediately before Stage 4) vs true (Arm
CURRENT, i.e. exactly what ships today). Both arms use the SAME 136-record
evidence pool, SAME premise framing, SAME scope-check mode -- so any
difference measured is attributable to this one lever alone.

Generation is called EXACTLY ONCE per case (do_sample=False, fixed seed --
deterministic, so a second call would reproduce identical text, just waste
GPU time); claim parsing and evidence matching are also shared (both
depend only on the generated text + the SAME evidence pool). Only
apply_verification() and apply_selective_correction() are run
independently per arm, via the REAL pipeline.py functions -- not
reimplemented.

Case selection: every document_id already used in ANY committed
outputs/*.jsonl file in this repo (scanned generically, not
hand-maintained) is excluded. Of the remaining NyayaRAG cases with nonzero
evidence overlap under the current (v1) pool, the first N by document_id
sort order are selected -- deterministic, no cherry-picking on outcome.

CHECKPOINTED / RESUMABLE (added 2026-09-11 for the 16GB-laptop memory
constraint, outputs/16gb_memory_architecture_audit.md): each case's result
for both arms is appended to the output JSONL files immediately after that
case completes, not held in memory until the end. On startup, any
document_ids already present in BOTH arms' output files (for this exact
--out-prefix) are treated as already-done and skipped -- so a killed/
resumed run never recomputes or duplicates a completed case. A MEMORY GUARD
checks free system RAM before each case (via psutil) and, if it falls below
--min-free-gb, stops gracefully (writes final metrics from whatever
completed, does not crash the machine, does not lose any already-computed
case).

Output (outputs/, new prefix by default, nothing overwritten; existing
per-arm JSONL files are APPENDED to on resume, never truncated):
  narrow_primary_hypothesis_gpu_ablation_OLD.jsonl
  narrow_primary_hypothesis_gpu_ablation_CURRENT.jsonl
  narrow_primary_hypothesis_gpu_ablation_metrics.json
  narrow_primary_hypothesis_gpu_ablation_report.md
"""
from __future__ import annotations

import argparse
import copy
import datetime
import gc
import json
import sys
import time
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src import pipeline
from src.data_loader import load_nyayarag_cases, load_usable_evidence_from_config, select_cases_with_evidence_overlap
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.evidence_matcher import NO_EVIDENCE

ARMS = ("OLD", "CURRENT")


def find_previously_used_ids(outputs: Path) -> set[str]:
    used: set[str] = set()
    for fp in outputs.glob("*.jsonl"):
        try:
            for line in fp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and "document_id" in rec:
                    used.add(rec["document_id"])
        except Exception:
            continue
    return used


def load_checkpointed_ids(out_path: Path) -> set[str]:
    """document_ids already present in one arm's output file -- used to
    determine what's safe to skip on a resumed run. Malformed/partial last
    lines (e.g. from a kill mid-write) are tolerated, not fatal."""
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
            continue  # last line may be a partial write from a kill; skip it, don't crash
        if isinstance(rec, dict) and "document_id" in rec:
            ids.add(rec["document_id"])
    return ids


def free_memory_gb() -> float:
    import psutil
    return psutil.virtual_memory().available / (1024 ** 3)


def build_final_field(baseline: dict, correction_summary: dict) -> dict:
    status = correction_summary["status"]
    if status == "corrected":
        return {"text": correction_summary["regenerated_text"], "source": "corrected"}
    return {"text": baseline["generated_field"]["text"], "source": status}


def triggers_correction(rec: dict) -> bool:
    return rec["verdict"] == CONTRADICTED or rec.get("sub_reason") == "low_confidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda"])
    ap.add_argument("--n-cases", type=int, default=15)
    ap.add_argument("--out-prefix", default="narrow_primary_hypothesis_gpu_ablation")
    ap.add_argument("--min-free-gb", type=float, default=2.0,
                     help="Stop gracefully (do not crash) if free system RAM falls below this "
                          "before starting a case. Default 2.0GB -- chosen with headroom above "
                          "the ~1.2-1.6GB margin observed to be too tight during model loading "
                          "on this project's 16GB reference machine.")
    args = ap.parse_args()

    if args.device != "cuda":
        print("This experiment requires the real Qwen 7B generator; refusing non-CUDA "
              "by policy (use --device cuda).", file=sys.stderr)
        return 2
    import torch
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 2

    import psutil
    free_before_load = free_memory_gb()
    print(f"Free system RAM before model load: {free_before_load:.2f} GB "
          f"(guard threshold: {args.min_free_gb} GB)")
    if free_before_load < args.min_free_gb:
        print(f"ABORTING before loading any model: free RAM ({free_before_load:.2f}GB) is "
              f"already below the {args.min_free_gb}GB guard threshold. Not attempting to load "
              f"a 7B model into an already-insufficient memory budget.", file=sys.stderr)
        return 3

    base_config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    assert base_config["verification"]["narrow_primary_hypothesis"] is True, (
        "config/prototype.yaml must ship with narrow_primary_hypothesis: true "
        "(current production) -- refusing to run against an unexpected base config."
    )

    arm_config = {}
    arm_config["OLD"] = copy.deepcopy(base_config)
    arm_config["OLD"]["verification"]["narrow_primary_hypothesis"] = False
    arm_config["CURRENT"] = copy.deepcopy(base_config)  # exactly as shipped

    exact_index, all_usable = load_usable_evidence_from_config(base_config, repo_root)
    print(f"Evidence pool: {len(all_usable)} records (shared by both arms)")

    case_paths = [repo_root / p for p in base_config["paths"]["nyayarag_case_files"]]
    all_cases = load_nyayarag_cases(case_paths)
    overlapping = select_cases_with_evidence_overlap(all_cases, exact_index, min_overlap=1)
    print(f"NyayaRAG cases with >=1 evidence-overlapping citation: {len(overlapping)}")

    previously_used = find_previously_used_ids(outputs)
    print(f"document_ids already used in some prior experiment: {len(previously_used)}")

    out_paths = {arm: outputs / f"{args.out_prefix}_{arm}.jsonl" for arm in ARMS}
    checkpointed = {arm: load_checkpointed_ids(out_paths[arm]) for arm in ARMS}
    already_done = checkpointed["OLD"] & checkpointed["CURRENT"]  # complete in BOTH arms
    if already_done:
        print(f"RESUMING: {len(already_done)} case(s) already checkpointed in both arms' "
              f"output files for prefix {args.out_prefix!r}, will be skipped: "
              f"{sorted(already_done)}")

    fresh = sorted(
        {c.document_id: c for c in overlapping
         if c.document_id not in previously_used and c.document_id not in already_done}.items()
    )
    selected = [c for _, c in fresh[: args.n_cases]]
    print(f"Selected {len(selected)} genuinely fresh, not-yet-checkpointed cases "
          f"(deterministic, sorted by document_id): {[c.document_id for c in selected]}")
    if len(selected) < args.n_cases:
        print(f"WARNING: only {len(selected)} fresh cases available, requested {args.n_cases}", file=sys.stderr)

    from src.generator import StatuteGroundingGenerator
    from src.corrector import SelectiveCorrector

    gen_cfg = base_config["generation"]
    generator = StatuteGroundingGenerator(
        model_id=gen_cfg["model_id"],
        quantization=gen_cfg["quantization"],
        device_map=gen_cfg["device_map"],
        max_new_tokens=gen_cfg["max_new_tokens"],
        do_sample=gen_cfg["do_sample"],
        temperature=gen_cfg["temperature"],
        top_p=gen_cfg["top_p"],
        system_prompt=gen_cfg["system_prompt"],
        user_prompt_template=gen_cfg["user_prompt_template"],
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
    n_completed_this_run = 0
    stopped_early = False
    try:
        for i, case in enumerate(selected):
            free_now = free_memory_gb()
            print(f"\n[{i+1}/{len(selected)}] {case.document_id}  (free RAM: {free_now:.2f}GB)", flush=True)
            if free_now < args.min_free_gb:
                print(f"MEMORY GUARD TRIPPED: free RAM ({free_now:.2f}GB) < threshold "
                      f"({args.min_free_gb}GB) before starting this case. Stopping gracefully -- "
                      f"{n_completed_this_run} case(s) already safely checkpointed this run "
                      f"(plus {len(already_done)} resumed from a prior run) are NOT lost.",
                      file=sys.stderr)
                stopped_early = True
                break

            t_gen0 = time.time()
            baseline = pipeline.generate_and_parse(
                case, generator, exact_index, all_usable,
                base_config["evidence_matching"]["fuzzy_token_overlap_threshold"],
            )
            gen_time = time.time() - t_gen0
            print(f"  generated + parsed in {gen_time:.1f}s, {len(baseline['claims'])} claims, "
                  f"{sum(1 for c in baseline['claims'] if c['evidence_text'])} with evidence")

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
                correction_summary = pipeline.apply_selective_correction(
                    arm_baseline, case, corrector, arm_config[arm]
                )
                final_field = build_final_field(arm_baseline, correction_summary)

                record = {
                    "document_id": case.document_id,
                    "arm": arm,
                    "generated_field": arm_baseline["generated_field"],
                    "claims": [{k: v for k, v in c.items() if not k.startswith("_")} for c in arm_baseline["claims"]],
                    "correction": {k: v for k, v in correction_summary.items() if not k.startswith("_")},
                    "final_field": final_field,
                }
                # CHECKPOINT: write + flush immediately, not held until the
                # end -- a kill after this point never loses this case.
                out_files[arm].write(json.dumps(record, ensure_ascii=False) + "\n")
                out_files[arm].flush()

                n_ev = sum(1 for c in record["claims"] if c["evidence_text"])
                n_ent = sum(1 for c in record["claims"] if c["verdict"] == ENTAILED)
                n_con = sum(1 for c in record["claims"] if c["verdict"] == CONTRADICTED)
                print(f"  [{arm}] evidence={n_ev} ENTAILED={n_ent} CONTRADICTED={n_con} "
                      f"correction_status={correction_summary['status']}")

            n_completed_this_run += 1
            gc.collect()
            if args.device == "cuda":
                torch.cuda.empty_cache()
    finally:
        for f in out_files.values():
            f.close()

    total_runtime = time.time() - t0

    # ---- metrics: read back the FULL checkpointed files (resumed + this
    # run's own cases), not just what happened in this process's memory ----
    def load_all_records(arm: str) -> list[dict]:
        recs = []
        for line in out_paths[arm].read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return recs

    def summarize(arm: str) -> dict:
        recs = load_all_records(arm)
        all_claims = [c for r in recs for c in r["claims"]]
        matched = [c for c in all_claims if c["evidence_text"]]
        verdicts = Counter(c["verdict"] for c in matched)
        corr_status = Counter(r["correction"]["status"] for r in recs)
        triggered = sum(1 for r in recs if r["correction"]["status"] != "not_triggered")
        shipped = sum(1 for r in recs if r["correction"]["status"] == "corrected")
        return {
            "n_cases": len(recs),
            "total_claims": len(all_claims),
            "claims_with_evidence": len(matched),
            "evidence_coverage": len(matched) / len(all_claims) if all_claims else None,
            "verdict_distribution": dict(verdicts),
            "correction_status_distribution": dict(corr_status),
            "correction_triggered": triggered,
            "correction_shipped": shipped,
            "correction_shipping_rate_of_triggered": shipped / triggered if triggered else None,
        }

    old_m, cur_m = summarize("OLD"), summarize("CURRENT")
    metrics = {
        "config": {
            "n_cases_requested_this_run": args.n_cases,
            "n_cases_completed_this_run": n_completed_this_run,
            "n_cases_resumed_from_checkpoint": len(already_done),
            "n_cases_total_in_output": old_m["n_cases"],
            "stopped_early_by_memory_guard": stopped_early,
            "min_free_gb_threshold": args.min_free_gb,
            "evidence_pool_size": len(all_usable),
            "premise_framing": base_config["verification"]["premise_framing"],
            "generation_model": base_config["generation"]["model_id"],
            "verification_model": base_config["verification"]["model_id"],
        },
        "OLD": old_m,
        "CURRENT": cur_m,
        "runtime_seconds_this_run": total_runtime,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    metrics_path = outputs / f"{args.out_prefix}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nWrote {out_paths['OLD']}")
    print(f"Wrote {out_paths['CURRENT']}")
    print(f"Wrote {metrics_path}")

    # ---- report ----
    md = [
        "# narrow_primary_hypothesis: fresh end-to-end GPU ablation (checkpointed)\n\n",
        f"_Generated {metrics['timestamp']}_\n\n",
        f"Real Qwen2.5-7B generation + real DeBERTa verification + real selective correction, "
        f"run through the ACTUAL production `pipeline.py` code (mode C). "
        f"**{old_m['n_cases']} total cases in output** "
        f"({len(already_done)} resumed from a prior checkpointed run + {n_completed_this_run} "
        f"completed this run"
        + (", STOPPED EARLY by the memory guard" if stopped_early else "") + ").\n\n",
        f"Generation is shared between arms (called once per case, deterministic greedy "
        f"decoding); only `verification.narrow_primary_hypothesis` differs "
        f"(OLD=false, matching the config immediately before Stage 4; CURRENT=true, exactly "
        f"as shipped today) -- everything else (evidence pool, premise framing, scope-check "
        f"mode, confidence threshold) is held identical between arms.\n\n",
        f"> Verdicts are a small public NLI model's output against a {len(all_usable)}-record "
        f"corpus. They are not legal-correctness determinations, and no lawyer ground truth "
        f"exists.\n\n",
        "## Headline\n\n",
        "| Metric | OLD (pre-Stage-4) | CURRENT (shipped) |\n|---|---|---|\n",
        f"| Total claims | {old_m['total_claims']} | {cur_m['total_claims']} |\n",
        f"| Claims with evidence | {old_m['claims_with_evidence']} | {cur_m['claims_with_evidence']} |\n",
        f"| ENTAILED | {old_m['verdict_distribution'].get('ENTAILED', 0)} | "
        f"{cur_m['verdict_distribution'].get('ENTAILED', 0)} |\n",
        f"| CONTRADICTED | {old_m['verdict_distribution'].get('CONTRADICTED', 0)} | "
        f"{cur_m['verdict_distribution'].get('CONTRADICTED', 0)} |\n",
        f"| NOT_ENOUGH_INFORMATION | {old_m['verdict_distribution'].get('NOT_ENOUGH_INFORMATION', 0)} | "
        f"{cur_m['verdict_distribution'].get('NOT_ENOUGH_INFORMATION', 0)} |\n",
        f"| Correction triggered | {old_m['correction_triggered']}/{old_m['n_cases']} | "
        f"{cur_m['correction_triggered']}/{cur_m['n_cases']} |\n",
        f"| **Correction SHIPPED** | **{old_m['correction_shipped']}/{old_m['n_cases']}** | "
        f"**{cur_m['correction_shipped']}/{cur_m['n_cases']}** |\n\n",
        "## Correction status breakdown\n\n",
        "| Status | OLD | CURRENT |\n|---|---|---|\n",
    ]
    all_statuses = sorted(set(old_m["correction_status_distribution"]) | set(cur_m["correction_status_distribution"]))
    for s in all_statuses:
        md.append(f"| {s} | {old_m['correction_status_distribution'].get(s, 0)} | "
                   f"{cur_m['correction_status_distribution'].get(s, 0)} |\n")
    if stopped_early:
        md.append(
            f"\n**This run was stopped early by the memory guard** (free RAM fell below "
            f"{args.min_free_gb}GB). To continue, re-run the exact same command -- already-"
            f"checkpointed cases are automatically skipped, no data is lost or duplicated.\n"
        )
    md.append(
        f"\nRuntime this run: {total_runtime:.1f}s for {n_completed_this_run} newly-completed "
        f"case(s) x 2 arms (generation shared, so this is NOT double the single-arm cost).\n\n"
        "## Interpretation\n\n"
        "This distinguishes VERIFICATION recovery (NEI -> ENTAILED/CONTRADICTED verdict "
        "changes) from actual CORRECTION SHIPPING (a rewritten field passing every safety "
        "gate). A verdict change does not automatically produce a shipped correction -- "
        "shipping additionally requires the flagged claim to be the one selected for "
        "correction (max_attempts=1, first-flagged-claim-only), Qwen's rewrite to pass "
        "re-verification as ENTAILED, and the sibling-regression/scope/injection/ordinal "
        "safety gates to all pass. See the correction status breakdown above for exactly "
        "which gate stopped each non-shipped attempt.\n"
    )

    report_path = outputs / f"{args.out_prefix}_report.md"
    report_path.write_text("".join(md), encoding="utf-8")
    print(f"Wrote {report_path}")

    print(f"\nOLD:     shipped {old_m['correction_shipped']}/{old_m['n_cases']} "
          f"(triggered {old_m['correction_triggered']})")
    print(f"CURRENT: shipped {cur_m['correction_shipped']}/{cur_m['n_cases']} "
          f"(triggered {cur_m['correction_triggered']})")
    print(f"Runtime this run: {total_runtime:.1f}s")
    if stopped_early:
        print("Stopped early by memory guard -- re-run the same command to continue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
