#!/usr/bin/env python3
"""STEP 10B — fresh reproduction of the historical 209-claim GPU generation
experiment (`research/prototype/scripts/run_final_gpu_validation.py`,
originally run 2026-08-27, `outputs/final_gpu_validation_metrics.json`).

This is a copy of that unmodified production script with exactly two
changes, both purely about where things are written/recorded, never about
pipeline behavior:

  1. Fresh outputs are written under
     research/prototype/testing/actual_outputs/step10b_gpu_experiments/
     instead of research/prototype/outputs/ -- so nothing historical is
     touched or overwritten. Inputs (candidate file, config, NyayaRAG
     source files, evidence files) are still READ from their original,
     unmodified locations.
  2. A reproducibility_metadata block (git commit, torch/CUDA/driver
     versions, GPU name, dataset file hashes, exact command, wall-clock
     start/end) is captured and written alongside the metrics.

Every line of actual experiment logic (arm configs, generation, evidence
matching, verification, correction, metric computation) is copied verbatim
from scripts/run_final_gpu_validation.py -- see that file for the full
design rationale. Do not edit that production script; this is a standalone
copy for STEP 10B only.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

_TESTING_DIR = Path(__file__).resolve().parent
_PROTOTYPE_ROOT = _TESTING_DIR.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))
sys.path.insert(0, str(_PROTOTYPE_ROOT / "scripts"))

import yaml

from src import claim_parser, pipeline
from src.data_loader import load_nyayarag_cases, load_usable_evidence_from_config
from src.evidence_matcher import match_evidence, NO_EVIDENCE
from src.verifier import ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, PREMISE_FRAMING_BARE
from select_natural_candidates import score_case  # exact same scoring/tie-break used for selection

ARMS = ("A", "B")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_selected_cases(read_outputs: Path, repo_root: Path, config: dict, exact_index, all_usable,
                         candidate_file: str):
    selected_path = read_outputs / candidate_file
    selected_ids = json.loads(selected_path.read_text(encoding="utf-8"))["document_ids"]
    selected_set = set(selected_ids)

    case_paths = [repo_root / p for p in config["paths"]["nyayarag_case_files"]]
    all_cases = load_nyayarag_cases(case_paths)
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    variants_by_id: dict[str, list] = {}
    for case in all_cases:
        if case.document_id in selected_set:
            variants_by_id.setdefault(case.document_id, []).append(case)

    chosen = {}
    for doc_id, variants in variants_by_id.items():
        scored = [(score_case(c, exact_index, all_usable, fuzzy_threshold), c) for c in variants]
        best = sorted(scored, key=lambda pair: (-pair[0]["score"], pair[0]["n_raw_citation_keys"], doc_id))[0]
        chosen[doc_id] = best[1]

    missing = selected_set - set(chosen)
    if missing:
        raise RuntimeError(f"{len(missing)} selected document_ids not found in NyayaRAG source files: {missing}")

    return [chosen[doc_id] for doc_id in selected_ids], case_paths


def triggers_correction(rec: dict) -> bool:
    return rec["verdict"] == CONTRADICTED or rec.get("sub_reason") == "low_confidence"


def build_arm_claim_records(claims, exact_index, all_usable, fuzzy_threshold: float) -> list[dict]:
    claim_records = []
    for claim in claims:
        match = match_evidence(claim.citation_extracted, exact_index, all_usable, fuzzy_threshold)
        claim_records.append({
            "claim_id": claim.claim_id,
            "claim_text": claim.claim_text,
            "assertion_text": claim.assertion_text,
            "assertion_spans": list(claim.assertion_spans),
            "citation_extracted": claim.citation_extracted.as_dict() if claim.citation_extracted else None,
            "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
            "evidence_text": match.evidence.canonical_text if match.matched else None,
            "_evidence_provision": {
                "provision_type": match.evidence.provision_type,
                "provision_number": match.evidence.provision_number,
                "act": match.evidence.act,
            } if match.matched else None,
            "evidence_match_method": match.match_method,
            "verdict": None, "confidence": None, "sub_reason": None, "verifier_model": None,
        })
        if not match.matched:
            claim_records[-1]["verdict"] = NO_EVIDENCE
    return claim_records


def classify_failure(status: str, reverification: dict | None) -> str | None:
    if status == "correction_failed":
        if reverification is None:
            return "citation_identity_lost"
        if reverification.get("verdict") == NO_EVIDENCE:
            return "evidence_lost_after_edit"
        return "reverification_not_entailed"
    if status in ("correction_scope_violation", "correction_sibling_regression", "not_triggered"):
        return status
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda"])
    ap.add_argument("--out-prefix", default="step10b_final_gpu_validation")
    ap.add_argument("--candidate-file", default="natural_candidate_selected_ids_50_final_validation.json")
    args = ap.parse_args()
    exact_command = "research/.venv/Scripts/python.exe research/prototype/testing/run_step10b_209_gpu_generation.py " + " ".join(sys.argv[1:])

    if args.device != "cuda":
        print("This experiment requires the real Qwen 7B generator; refusing non-CUDA "
              "by policy for this script (use --device cuda).", file=sys.stderr)
        return 2
    import torch
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 2

    base_config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    read_outputs = _PROTOTYPE_ROOT / "outputs"  # READ-ONLY: candidate file lives here, never written here
    write_outputs = _TESTING_DIR / "actual_outputs" / "step10b_gpu_experiments"
    write_outputs.mkdir(parents=True, exist_ok=True)

    wall_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_commit = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True).stdout.strip()
    nvidia_smi_out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True
    ).stdout.strip()

    arm_config: dict[str, dict] = {}
    arm_config["A"] = copy.deepcopy(base_config)
    arm_config["A"]["use_evidence_v1"] = False
    arm_config["A"]["verification"]["premise_framing"] = "bare"
    arm_config["A"]["verification"]["confidence_threshold"] = 0.70
    arm_config["A"]["correction"]["atomic_scope_check"] = False
    arm_config["A"]["correction"]["narrow_reverification_hypothesis"] = False

    arm_config["B"] = copy.deepcopy(base_config)
    arm_config["B"]["use_evidence_v1"] = True
    arm_config["B"]["verification"]["premise_framing"] = "bare"
    arm_config["B"]["verification"]["confidence_threshold"] = 0.70
    arm_config["B"]["correction"]["atomic_scope_check"] = "assertion_spans"
    arm_config["B"]["correction"]["narrow_reverification_hypothesis"] = True

    print("On-disk config/prototype.yaml is not modified; both arms are in-memory deep "
          "copies. Arm A = unmodified production defaults. Arm B = use_evidence_v1=true, "
          "atomic_scope_check=assertion_spans, narrow_reverification_hypothesis=true, "
          "premise_framing=bare, confidence_threshold=0.70.", flush=True)

    exact_index: dict[str, dict] = {}
    all_usable: dict[str, list] = {}
    for arm in ARMS:
        exact_index[arm], all_usable[arm] = load_usable_evidence_from_config(arm_config[arm], repo_root)
        print(f"Arm {arm} evidence pool: {len(all_usable[arm])} usable records "
              f"(use_evidence_v1={arm_config[arm]['use_evidence_v1']}).", flush=True)

    fuzzy_threshold = base_config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    candidate_path = read_outputs / args.candidate_file
    cases, nyayarag_case_paths = load_selected_cases(read_outputs, repo_root, base_config,
                                                       exact_index["A"], all_usable["A"], args.candidate_file)
    print(f"Loaded {len(cases)} selected cases (from {args.candidate_file}).", flush=True)

    dataset_hashes = {
        "candidate_file": {"path": str(candidate_path.relative_to(repo_root)), "sha256": sha256_file(candidate_path)},
        "nyayarag_case_files": [
            {"path": str(p.relative_to(repo_root)), "sha256": sha256_file(p)} for p in nyayarag_case_paths
        ],
        "evidence_files": [
            {"path": str((repo_root / base_config["paths"][k]).relative_to(repo_root)),
             "sha256": sha256_file(repo_root / base_config["paths"][k])}
            for k in ("canonical_statutes", "evidence_audit", "canonical_statutes_v1", "evidence_audit_v1")
            if (repo_root / base_config["paths"][k]).exists()
        ],
    }

    torch.cuda.reset_peak_memory_stats()
    from src.generator import StatuteGroundingGenerator
    from src.corrector import SelectiveCorrector
    from src.verifier import NLIVerifier

    gen_cfg = base_config["generation"]
    print(f"Loading generator {gen_cfg['model_id']} (4-bit, CUDA)...", flush=True)
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
    corr_cfg = base_config["correction"]
    corrector = SelectiveCorrector(
        generator=generator,
        max_new_tokens=corr_cfg["max_new_tokens"],
        do_sample=corr_cfg["do_sample"],
        system_prompt=corr_cfg["system_prompt"],
    )

    ver_cfg = base_config["verification"]
    print(f"Loading verifier {ver_cfg['model_id']} (CUDA)...", flush=True)
    verifier = NLIVerifier(
        model_id=ver_cfg["model_id"],
        confidence_threshold=0.70,
        max_sequence_length=ver_cfg["max_sequence_length"],
        device="cuda",
    )
    verifier.load()

    per_arm_rows: dict[str, list] = {"A": [], "B": []}
    correction_rows: list[dict] = []
    generation_seconds_total = 0.0
    arm_seconds: dict[str, float] = {"A": 0.0, "B": 0.0}
    n_claims_total = 0

    run_t0 = time.time()
    for i, case in enumerate(cases, start=1):
        t_gen0 = time.time()
        generated_text, gen_meta = generator.generate(case.case_text)
        claims = claim_parser.extract_claims(generated_text)
        gen_elapsed = time.time() - t_gen0
        generation_seconds_total += gen_elapsed
        n_claims_total += len(claims)

        generated_field = {
            "text": generated_text, "model": gen_meta.model_id, "quantization": gen_meta.quantization,
            "generation_params": {
                "max_new_tokens": gen_meta.max_new_tokens, "do_sample": gen_meta.do_sample,
                "temperature": gen_meta.temperature, "top_p": gen_meta.top_p, "seed": gen_meta.seed,
            },
            "generated_at": gen_meta.generated_at,
        }

        arm_stats = {}
        for arm in ARMS:
            t_arm0 = time.time()
            cfg = arm_config[arm]
            baseline = {
                "document_id": case.document_id, "case_text": case.case_text,
                "generated_field": generated_field,
                "claims": build_arm_claim_records(claims, exact_index[arm], all_usable[arm], fuzzy_threshold),
            }
            baseline["_exact_index"] = exact_index[arm]
            baseline["_all_usable"] = all_usable[arm]
            baseline["_verifier"] = verifier

            pipeline.apply_verification(baseline, verifier, pipeline.resolve_premise_framing(cfg))

            doc_triggered = any(
                rec["evidence_text"] is not None and triggers_correction(rec) for rec in baseline["claims"]
            )
            correction_summary = None
            if doc_triggered:
                correction_summary = pipeline.apply_selective_correction(baseline, case, corrector, cfg)
                rv = correction_summary.get("reverification") or {}
                target_id = correction_summary["triggered_for_claim_id"]
                unflagged_checked = unflagged_claimtext_preserved = unflagged_assertion_preserved = 0
                if correction_summary.get("regenerated_text") is not None:
                    for rec in baseline["claims"]:
                        if rec["claim_id"] == target_id:
                            continue
                        unflagged_checked += 1
                        rt = correction_summary["regenerated_text"]
                        if rec["claim_text"] in rt:
                            unflagged_claimtext_preserved += 1
                        fragments = rec.get("assertion_spans") or [rec.get("assertion_text") or rec["claim_text"]]
                        if all(f and f in rt for f in fragments):
                            unflagged_assertion_preserved += 1
                correction_rows.append({
                    "arm": arm, "document_id": case.document_id,
                    "triggered_for_claim_id": target_id, "status": correction_summary["status"],
                    "failure_category": classify_failure(correction_summary["status"], rv or None),
                    "original_field_text": correction_summary["original_field_text"],
                    "regenerated_text": correction_summary["regenerated_text"],
                    "reverification": rv or None,
                    "sibling_regressions": correction_summary.get("sibling_regressions") or [],
                    "corr_meta": correction_summary.get("corr_meta"),
                    "unflagged_checked": unflagged_checked,
                    "unflagged_claimtext_preserved": unflagged_claimtext_preserved,
                    "unflagged_assertion_preserved": unflagged_assertion_preserved,
                })

            record = {
                "document_id": case.document_id, "case_text": case.case_text,
                "generated_field": generated_field,
                "claims": [{k: v for k, v in c.items() if not k.startswith("_")} for c in baseline["claims"]],
                "correction": (
                    {k: v for k, v in correction_summary.items() if not k.startswith("_")}
                    if correction_summary is not None
                    else {"triggered_for_claim_id": None, "attempts": 0, "status": "not_triggered",
                          "regenerated_text": None, "original_field_text": generated_field["text"],
                          "reverification": None}
                ),
                "reproducibility": {
                    "arm": arm, "seed": base_config["seed"],
                    "generation_model": gen_cfg["model_id"], "verification_model": ver_cfg["model_id"],
                    "confidence_threshold": 0.70, "use_evidence_v1": cfg["use_evidence_v1"],
                    "premise_framing": cfg["verification"]["premise_framing"],
                    "atomic_scope_check": cfg["correction"]["atomic_scope_check"],
                    "narrow_reverification_hypothesis": cfg["correction"]["narrow_reverification_hypothesis"],
                    "evidence_pool_size": len(all_usable[arm]),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            }
            per_arm_rows[arm].append(record)
            arm_elapsed = time.time() - t_arm0
            arm_seconds[arm] += arm_elapsed
            arm_stats[arm] = (len(baseline["claims"]), sum(1 for c in baseline["claims"] if c["evidence_text"]))

        print(f"[{i}/{len(cases)}] {case.document_id}: gen={gen_elapsed:.1f}s, claims={len(claims)}, "
              f"A_matched={arm_stats['A'][1]}, B_matched={arm_stats['B'][1]}", flush=True)

    run_elapsed = time.time() - run_t0
    torch.cuda.synchronize()
    peak_vram_mib = torch.cuda.max_memory_allocated() // (1024 * 1024)
    peak_vram_reserved_mib = torch.cuda.max_memory_reserved() // (1024 * 1024)
    wall_end = datetime.datetime.now(datetime.timezone.utc).isoformat()

    per_arm_metrics = {}
    for arm in ARMS:
        rows = per_arm_rows[arm]
        verdicts = Counter()
        confidences = []
        for rec in rows:
            for c in rec["claims"]:
                verdicts[c["verdict"]] += 1
                if c["confidence"] is not None:
                    confidences.append(c["confidence"])
        match_methods = Counter(c["evidence_match_method"] for rec in rows for c in rec["claims"])
        corr_status = Counter(rec["correction"]["status"] for rec in rows)
        triggers = sum(1 for rec in rows if rec["correction"]["status"] != "not_triggered")
        c_rows = [r for r in correction_rows if r["arm"] == arm]
        unsafe = sum(
            1 for r in c_rows
            if r["status"] == "corrected" and (r["reverification"] or {}).get("verdict") != ENTAILED
        )
        failure_categories = Counter(r["failure_category"] for r in c_rows if r["failure_category"])
        confidences.sort()
        n_conf = len(confidences)
        per_arm_metrics[arm] = {
            "n_cases": len(rows),
            "n_claims": sum(len(rec["claims"]) for rec in rows),
            "n_claims_evidence_matched": sum(1 for rec in rows for c in rec["claims"] if c["evidence_text"]),
            "evidence_match_method_counts": dict(match_methods),
            "verdict_counts": dict(verdicts),
            "confidence_summary": {
                "n": n_conf,
                "mean": (sum(confidences) / n_conf) if n_conf else None,
                "median": (confidences[n_conf // 2] if n_conf else None),
                "min": (confidences[0] if n_conf else None),
                "max": (confidences[-1] if n_conf else None),
            },
            "correction_triggers": triggers,
            "correction_attempts": sum(v for k, v in corr_status.items() if k != "not_triggered"),
            "correction_statuses": {k: v for k, v in corr_status.items() if k != "not_triggered"},
            "corrections_shipped_success": corr_status.get("corrected", 0),
            "correction_failed": corr_status.get("correction_failed", 0),
            "correction_scope_violation": corr_status.get("correction_scope_violation", 0),
            "correction_sibling_regression": corr_status.get("correction_sibling_regression", 0),
            "failure_categories": dict(failure_categories),
            "unsafe_corrections_shipped": unsafe,
            "unflagged_claimtext_preserved": sum(r["unflagged_claimtext_preserved"] for r in c_rows),
            "unflagged_assertion_preserved": sum(r["unflagged_assertion_preserved"] for r in c_rows),
            "unflagged_claim_checked": sum(r["unflagged_checked"] for r in c_rows),
            "runtime_seconds_arm_only": round(arm_seconds[arm], 2),
        }

    result = {
        "experiment": "step10b_fresh_reproduction_of_final_gpu_validation_A_vs_B",
        "fresh_reproduction_of": "research/prototype/outputs/final_gpu_validation_metrics.json (2026-08-27)",
        "step": "STEP 10B",
        "data": "50 deterministically-selected, NEVER-before-evaluated NyayaRAG cases "
                "(outputs/natural_candidate_selected_ids_50_final_validation.json), disjoint "
                "from all 130 document_ids used in run_A_n30/run_natural_targeted/"
                "natural_candidates_50_gpu/natural_candidates_batch2_gpu. Genuine fresh Qwen "
                "generation (once per case, shared across arms); genuine DeBERTa verification "
                "and Qwen correction, run independently per arm against that arm's own "
                "evidence pool.",
        "n_cases": len(cases), "seed": base_config["seed"],
        "generation_model": gen_cfg["model_id"], "verification_model": ver_cfg["model_id"],
        "arm_definitions": {
            "A": {"label": "baseline (production defaults, unmodified)",
                  "use_evidence_v1": False, "premise_framing": "bare",
                  "atomic_scope_check": False, "narrow_reverification_hypothesis": False,
                  "confidence_threshold": 0.70, "evidence_pool_size": len(all_usable["A"])},
            "B": {"label": "improved (all validated improvements enabled)",
                  "use_evidence_v1": True, "premise_framing": "bare",
                  "atomic_scope_check": "assertion_spans", "narrow_reverification_hypothesis": True,
                  "confidence_threshold": 0.70, "evidence_pool_size": len(all_usable["B"])},
        },
        "per_arm": per_arm_metrics,
        "n_claims_shared_generation": n_claims_total,
        "runtime_seconds_total": run_elapsed,
        "runtime_seconds_generation": generation_seconds_total,
        "peak_vram_mib": peak_vram_mib,
        "peak_vram_reserved_mib": peak_vram_reserved_mib,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reproducibility_metadata": {
            "git_commit": git_commit,
            "exact_command": exact_command,
            "wall_clock_start_utc": wall_start,
            "wall_clock_end_utc": wall_end,
            "python_version": sys.version,
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "gpu_device_name": torch.cuda.get_device_name(0),
            "nvidia_smi_query": nvidia_smi_out,
            "dataset_hashes": dataset_hashes,
        },
    }

    (write_outputs / f"{args.out_prefix}_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for arm in ARMS:
        with (write_outputs / f"{args.out_prefix}_{arm}.jsonl").open("w", encoding="utf-8") as f:
            for rec in per_arm_rows[arm]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with (write_outputs / f"{args.out_prefix}_corrections_detail.jsonl").open("w", encoding="utf-8") as f:
        for r in correction_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    a, b = per_arm_metrics["A"], per_arm_metrics["B"]
    print("\n" + "=" * 72)
    print(f"{'metric':<42}{'A (baseline)':>14}{'B (improved)':>16}")
    print("-" * 72)
    print(f"{'claims / evidence-matched':<42}{str(a['n_claims'])+'/'+str(a['n_claims_evidence_matched']):>14}"
          f"{str(b['n_claims'])+'/'+str(b['n_claims_evidence_matched']):>16}")
    print(f"{'verdict counts':<42}{str(a['verdict_counts']):>14}{str(b['verdict_counts']):>16}")
    print(f"{'correction triggers':<42}{a['correction_triggers']:>14}{b['correction_triggers']:>16}")
    print(f"{'corrections shipped':<42}{a['corrections_shipped_success']:>14}{b['corrections_shipped_success']:>16}")
    print(f"{'correction_failed':<42}{a['correction_failed']:>14}{b['correction_failed']:>16}")
    print(f"{'scope_violation':<42}{a['correction_scope_violation']:>14}{b['correction_scope_violation']:>16}")
    print(f"{'sibling_regression':<42}{a['correction_sibling_regression']:>14}{b['correction_sibling_regression']:>16}")
    print(f"{'unsafe shipped':<42}{a['unsafe_corrections_shipped']:>14}{b['unsafe_corrections_shipped']:>16}")
    print("=" * 72)
    print(f"\nTotal runtime: {run_elapsed:.1f}s (generation: {generation_seconds_total:.1f}s), "
          f"peak VRAM: {peak_vram_mib} MiB (reserved: {peak_vram_reserved_mib} MiB)")
    print(f"\nWrote {write_outputs / (args.out_prefix + '_metrics.json')}")
    print(f"Wrote {write_outputs / (args.out_prefix + '_A.jsonl')}")
    print(f"Wrote {write_outputs / (args.out_prefix + '_B.jsonl')}")
    print(f"Wrote {write_outputs / (args.out_prefix + '_corrections_detail.jsonl')}")
    print("\nSTEP10B_RUN_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
