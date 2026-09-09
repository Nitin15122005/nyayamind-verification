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
outputs/*.jsonl file in this repo (182 total, scanned generically, not
hand-maintained) is excluded. Of the remaining NyayaRAG cases with nonzero
evidence overlap under the current (v1) pool, the first N by document_id
sort order are selected -- deterministic, no cherry-picking on outcome.

Output (outputs/, new prefix, nothing overwritten):
  narrow_primary_hypothesis_gpu_ablation_OLD.jsonl
  narrow_primary_hypothesis_gpu_ablation_CURRENT.jsonl
  narrow_primary_hypothesis_gpu_ablation_metrics.json
  narrow_primary_hypothesis_gpu_ablation_report.md
"""
from __future__ import annotations

import argparse
import copy
import datetime
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
    args = ap.parse_args()

    if args.device != "cuda":
        print("This experiment requires the real Qwen 7B generator; refusing non-CUDA "
              "by policy (use --device cuda).", file=sys.stderr)
        return 2
    import torch
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 2

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

    fresh = sorted(
        {c.document_id: c for c in overlapping if c.document_id not in previously_used}.items()
    )
    selected = [c for _, c in fresh[: args.n_cases]]
    print(f"Selected {len(selected)} genuinely fresh cases (deterministic, sorted by document_id): "
          f"{[c.document_id for c in selected]}")
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

    verifier = NLIVerifier(
        model_id=base_config["verification"]["model_id"],
        confidence_threshold=base_config["verification"]["confidence_threshold"],
        max_sequence_length=base_config["verification"]["max_sequence_length"],
        device=args.device,
    )
    verifier.load()

    corrector = SelectiveCorrector(
        generator=generator,
        system_prompt=base_config["correction"]["system_prompt"],
        max_new_tokens=base_config["correction"]["max_new_tokens"],
        do_sample=base_config["correction"]["do_sample"],
    )

    records = {"OLD": [], "CURRENT": []}
    t0 = time.time()
    for i, case in enumerate(selected):
        print(f"\n[{i+1}/{len(selected)}] {case.document_id}", flush=True)
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
            records[arm].append(record)
            n_ev = sum(1 for c in record["claims"] if c["evidence_text"])
            n_ent = sum(1 for c in record["claims"] if c["verdict"] == ENTAILED)
            n_con = sum(1 for c in record["claims"] if c["verdict"] == CONTRADICTED)
            print(f"  [{arm}] evidence={n_ev} ENTAILED={n_ent} CONTRADICTED={n_con} "
                  f"correction_status={correction_summary['status']}")

    total_runtime = time.time() - t0

    # ---- metrics ----
    def summarize(arm: str) -> dict:
        recs = records[arm]
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

    metrics = {
        "config": {
            "n_cases_requested": args.n_cases, "n_cases_run": len(selected),
            "document_ids": [c.document_id for c in selected],
            "evidence_pool_size": len(all_usable),
            "premise_framing": base_config["verification"]["premise_framing"],
            "generation_model": base_config["generation"]["model_id"],
            "verification_model": base_config["verification"]["model_id"],
        },
        "OLD": summarize("OLD"),
        "CURRENT": summarize("CURRENT"),
        "runtime_seconds_total": total_runtime,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    for arm in ARMS:
        out_path = outputs / f"{args.out_prefix}_{arm}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for r in records[arm]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {out_path}")

    metrics_path = outputs / f"{args.out_prefix}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote {metrics_path}")

    # ---- report ----
    old_m, cur_m = metrics["OLD"], metrics["CURRENT"]
    md = [
        "# narrow_primary_hypothesis: fresh end-to-end GPU ablation\n\n",
        f"_Generated {metrics['timestamp']}_\n\n",
        f"Real Qwen2.5-7B generation + real DeBERTa verification + real selective correction, "
        f"run through the ACTUAL production `pipeline.py` code (mode C), on **{len(selected)} "
        f"genuinely fresh** NyayaRAG cases never used in any prior experiment in this repo "
        f"(182 document_ids excluded by scanning every committed outputs/*.jsonl file).\n\n",
        f"Generation is shared between arms (called once per case, deterministic greedy "
        f"decoding); only `verification.narrow_primary_hypothesis` differs "
        f"(OLD=false, matching the config immediately before Stage 4; CURRENT=true, exactly "
        f"as shipped today) -- everything else (evidence pool, premise framing, scope-check "
        f"mode, confidence threshold) is held identical between arms.\n\n",
        f"> Verdicts are a small public NLI model's output against a {len(all_usable)}-record "
        f"corpus. They are not legal-correctness determinations, and no lawyer ground truth "
        f"exists. This is a SMALL sample (n={len(selected)} cases) -- directional evidence, "
        f"not a statistically powered claim.\n\n",
        "## Headline\n\n",
        "| Metric | OLD (pre-Stage-4) | CURRENT (shipped) |\n|---|---|---|\n",
        f"| Total claims | {old_m['total_claims']} | {cur_m['total_claims']} |\n",
        f"| Claims with evidence | {old_m['claims_with_evidence']} | {cur_m['claims_with_evidence']} |\n",
        f"| Evidence coverage | "
        f"{old_m['evidence_coverage']*100:.1f}%" if old_m['evidence_coverage'] else "n/a",
        f" | {cur_m['evidence_coverage']*100:.1f}%" if cur_m['evidence_coverage'] else " | n/a",
        " |\n",
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
    md.append(
        f"\nRuntime: {total_runtime:.1f}s total for {len(selected)} cases x 2 arms "
        f"(generation shared, so this is NOT double the single-arm cost).\n\n"
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
    print(f"Total runtime: {total_runtime:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
