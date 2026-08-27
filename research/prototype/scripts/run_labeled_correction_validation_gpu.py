#!/usr/bin/env python3
"""
Small, targeted GPU validation: does labeled framing + the full improved
config (use_evidence_v1, atomic_scope_check=assertion_spans,
narrow_reverification_hypothesis) actually SHIP more corrections on real
natural data than bare, once real Qwen correction calls are involved?

This is the one open question the CPU-only verification comparison
(compare_final_validation_labeled_cpu.py) could not answer: labeled framing
roughly doubled claim-level correction-trigger eligibility (9 -> 19 claims)
on the final_gpu_validation batch, but whether the corrector actually
produces a shippable fix is a real-Qwen-generation question, not a
verification-only one.

Scope, deliberately minimal to respect "small targeted run, not another
large GPU experiment":
  - NO new Qwen generation -- reuses final_gpu_validation_B.jsonl's already
    generated text (50 cases, shared with Arm A/B).
  - NO new bulk verification -- reuses the CPU-only labeled verdicts already
    computed in final_validation_bare_vs_labeled_cpu_claims.jsonl for every
    claim; only the FIRST-per-case triggering claim (pipeline.py's own
    "at most one correction attempt per case" contract) drives an actual
    genuine Qwen correction call.
  - The DeBERTa reverification step inside apply_selective_correction runs
    on CPU (fast, a handful of calls) -- only the corrector's Qwen calls
    need the GPU.

Config: use_evidence_v1=true, premise_framing=labeled,
atomic_scope_check="assertion_spans", narrow_reverification_hypothesis=true,
confidence_threshold=0.70 -- i.e. every validated improvement PLUS labeled
framing, the one combination no prior experiment in this project has run
through real correction.

Nothing overwritten; new, distinctly-named output files only.
"""
from __future__ import annotations

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
from src.data_loader import load_usable_evidence_from_config
from src.evidence_matcher import NO_EVIDENCE
from src.verifier import CONTRADICTED, NOT_ENOUGH_INFORMATION, ENTAILED


def triggers(verdict, sub_reason):
    return verdict == CONTRADICTED or (verdict == NOT_ENOUGH_INFORMATION and sub_reason == "low_confidence")


def main() -> int:
    import torch
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 2

    outputs = _PROTOTYPE_ROOT / "outputs"
    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent

    arm_config = dict(config)
    arm_config["use_evidence_v1"] = True
    arm_config["verification"] = dict(config["verification"])
    arm_config["verification"]["premise_framing"] = "labeled"
    arm_config["verification"]["confidence_threshold"] = 0.70
    arm_config["correction"] = dict(config["correction"])
    arm_config["correction"]["atomic_scope_check"] = "assertion_spans"
    arm_config["correction"]["narrow_reverification_hypothesis"] = True

    exact_index, all_usable = load_usable_evidence_from_config(arm_config, repo_root)
    by_key = {e.dataset_citation_key: e for e in all_usable}
    print(f"v0+v1 usable pool: {len(all_usable)} records.", flush=True)

    rows = [json.loads(l) for l in (outputs / "final_gpu_validation_B.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cpu_labeled = [json.loads(l) for l in (outputs / "final_validation_bare_vs_labeled_cpu_claims.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    labeled_by_key = {(r["document_id"], r["claim_id"]): r for r in cpu_labeled}
    print(f"Loaded {len(rows)} cases; {len(cpu_labeled)} claims with pre-computed labeled verdicts.", flush=True)

    # Determine, per case, the FIRST claim (document order) whose LABELED
    # verdict triggers correction -- matches pipeline.apply_selective_correction's
    # own "first flagged claim only" contract exactly.
    cases_to_correct = []
    for rec in rows:
        target = None
        for c in rec["claims"]:
            if c["evidence_text"] is None:
                continue
            lv = labeled_by_key.get((rec["document_id"], c["claim_id"]))
            if lv is None:
                continue
            if triggers(lv["labeled_verdict"], lv["labeled_sub_reason"]):
                target = c["claim_id"]
                break
        if target is not None:
            cases_to_correct.append((rec, target))

    print(f"{len(cases_to_correct)} cases have >=1 labeled-framing correction trigger "
          f"(vs 5 under bare in the original final_gpu_validation Arm B run).", flush=True)
    for rec, target in cases_to_correct:
        print(f"  {rec['document_id']} / {target}")

    from src.generator import StatuteGroundingGenerator
    from src.corrector import SelectiveCorrector
    from src.verifier import NLIVerifier

    gen_cfg = config["generation"]
    print(f"\nLoading generator {gen_cfg['model_id']} (4-bit, CUDA) -- correction calls only, no generation...", flush=True)
    generator = StatuteGroundingGenerator(
        model_id=gen_cfg["model_id"], quantization=gen_cfg["quantization"], device_map=gen_cfg["device_map"],
        max_new_tokens=gen_cfg["max_new_tokens"], do_sample=gen_cfg["do_sample"], temperature=gen_cfg["temperature"],
        top_p=gen_cfg["top_p"], system_prompt=gen_cfg["system_prompt"], user_prompt_template=gen_cfg["user_prompt_template"],
        seed=config["seed"],
    )
    generator.load()
    corr_cfg = config["correction"]
    corrector = SelectiveCorrector(
        generator=generator, max_new_tokens=corr_cfg["max_new_tokens"], do_sample=corr_cfg["do_sample"],
        system_prompt=corr_cfg["system_prompt"],
    )
    print("Loading DeBERTa verifier on CPU (reverification only, few calls)...", flush=True)
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"], confidence_threshold=0.70,
        max_sequence_length=config["verification"]["max_sequence_length"], device="cpu",
    )
    verifier.load()

    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]
    correction_rows = []
    t0 = time.time()

    for i, (rec, target_id) in enumerate(cases_to_correct, start=1):
        # Rebuild a pipeline-shaped baseline dict from the stored record,
        # substituting each claim's LABELED verdict/confidence/sub_reason
        # (the CPU pass's real output) for the stored bare ones.
        baseline_claims = []
        for c in rec["claims"]:
            c2 = dict(c)
            lv = labeled_by_key.get((rec["document_id"], c["claim_id"]))
            if lv is not None:
                c2["verdict"] = lv["labeled_verdict"]
                c2["confidence"] = lv["labeled_confidence"]
                c2["sub_reason"] = lv["labeled_sub_reason"]
            if c2["evidence_text"] is not None:
                ev = by_key.get(c2["evidence_id"])
                c2["_evidence_provision"] = {
                    "provision_type": ev.provision_type, "provision_number": ev.provision_number, "act": ev.act,
                } if ev else None
            baseline_claims.append(c2)

        class _Case:
            document_id = rec["document_id"]
            case_text = rec["case_text"]

        baseline = {
            "document_id": rec["document_id"], "case_text": rec["case_text"],
            "generated_field": rec["generated_field"], "claims": baseline_claims,
            "_exact_index": exact_index, "_all_usable": all_usable, "_verifier": verifier,
        }
        t_c0 = time.time()
        summary = pipeline.apply_selective_correction(baseline, _Case(), corrector, arm_config)
        elapsed = time.time() - t_c0
        rv = summary.get("reverification") or {}
        print(f"[{i}/{len(cases_to_correct)}] {rec['document_id']} claim={target_id} "
              f"status={summary['status']} ({elapsed:.1f}s)", flush=True)
        correction_rows.append({
            "document_id": rec["document_id"], "triggered_for_claim_id": summary["triggered_for_claim_id"],
            "status": summary["status"], "original_field_text": summary["original_field_text"],
            "regenerated_text": summary["regenerated_text"], "reverification": rv or None,
            "sibling_regressions": summary.get("sibling_regressions") or [],
        })

    run_elapsed = time.time() - t0
    status_counts = Counter(r["status"] for r in correction_rows)
    unsafe = sum(1 for r in correction_rows if r["status"] == "corrected"
                 and (r["reverification"] or {}).get("verdict") != ENTAILED)

    result = {
        "experiment": "labeled_framing_all_improvements_correction_validation_gpu",
        "scope": "Targeted: reuses Arm B's already-generated text + CPU-computed labeled verdicts; "
                 "only genuine NEW work is the Qwen correction call + CPU DeBERTa reverification for "
                 "each case with >=1 labeled-framing correction trigger.",
        "config": {"use_evidence_v1": True, "premise_framing": "labeled",
                   "atomic_scope_check": "assertion_spans", "narrow_reverification_hypothesis": True,
                   "confidence_threshold": 0.70},
        "n_cases_triggered": len(cases_to_correct),
        "status_counts": dict(status_counts),
        "corrections_shipped": status_counts.get("corrected", 0),
        "unsafe_shipped": unsafe,
        "runtime_seconds": run_elapsed,
        "comparison_bare_arm_b_original": {
            "n_cases_triggered": 5, "corrections_shipped": 0,
            "note": "from final_gpu_validation_metrics.json, per_arm.B (bare framing, same 50 cases, same improved config except framing)",
        },
    }
    (outputs / "labeled_correction_validation_gpu_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (outputs / "labeled_correction_validation_gpu_corrections_detail.jsonl").open("w", encoding="utf-8") as f:
        for r in correction_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"Cases triggered (labeled): {len(cases_to_correct)}  (bare, original run: 5)")
    print(f"Status counts: {dict(status_counts)}")
    print(f"Shipped: {status_counts.get('corrected', 0)}  Unsafe shipped: {unsafe}")
    print(f"Runtime: {run_elapsed:.1f}s")
    print(f"\nWrote {outputs / 'labeled_correction_validation_gpu_metrics.json'}")
    print(f"Wrote {outputs / 'labeled_correction_validation_gpu_corrections_detail.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
