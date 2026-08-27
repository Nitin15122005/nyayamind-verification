#!/usr/bin/env python3
"""
GENUINE end-to-end natural-data GPU experiment on the deterministic 50-case
candidate pool selected by scripts/select_natural_candidates.py
(outputs/natural_candidate_selected_ids_50.json).

Unlike compare_premise_framing_natural.py / _reparsed.py (which reused
ALREADY-GENERATED text from run_B_n30.jsonl / run_natural_targeted.jsonl),
these 50 cases have NEVER been run through the generator before — this
script performs REAL Qwen generation for every one of them, once per case
(generation does not depend on premise_framing, so it is shared across the
bare/labeled arms exactly as pipeline.py's module docstring specifies for
modes A/B/C — generating twice would be redundant, not more rigorous).
Both premise-framing arms then run genuine DeBERTa verification and, where
triggered, genuine Qwen correction + re-verification — nothing is re-scored
from a prior run; every "corrected"/"correction_failed" status here reflects
an actual new model call.

Nothing previously committed is read for its CONTENT here except the
selected-ID list itself (read-only) and the two NyayaRAG source JSON files
(read-only, never written). No prior output file is overwritten — this
script's outputs are new, distinctly-prefixed files.

config/prototype.yaml's default (bare) is not changed. No threshold is
changed. The safety gate (src/pipeline.py) is not modified.
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
sys.path.insert(0, str(_PROTOTYPE_ROOT / "scripts"))

import yaml

from src import pipeline
from src.data_loader import load_nyayarag_cases, load_usable_evidence
from src.verifier import ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED
from select_natural_candidates import score_case  # reuse the exact same scoring/tie-break used for selection


def load_selected_cases(outputs: Path, repo_root: Path, config: dict, exact_index, all_usable,
                         candidate_file: str):
    """Loads the selected document_ids' Case objects, picking the SAME
    multi/single variant the selection script would have picked (highest
    score_case() score; tie-break: fewer raw citation keys; then
    document_id) — so this run is reproducibly the exact pool the selection
    report describes, not an arbitrary re-pick."""
    selected_path = outputs / candidate_file
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

    # Preserve the selection's own order (already diversity/score-ranked).
    return [chosen[doc_id] for doc_id in selected_ids]


def triggers_correction(rec: dict) -> bool:
    return rec["verdict"] == CONTRADICTED or rec.get("sub_reason") == "low_confidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda"])
    ap.add_argument("--out-prefix", default="natural_candidates_50_gpu")
    ap.add_argument("--candidate-file", default="natural_candidate_selected_ids_50.json",
                     help="outputs/<this file> — the deterministic candidate-selection "
                          "output to source document_ids from.")
    ap.add_argument("--atomic-scope-check", default=None, choices=[None, "true", "false", "assertion_spans"],
                     help="Override config.correction.atomic_scope_check for this run only "
                          "(config/prototype.yaml's own default, false, is never changed). "
                          "Applied identically to both framing arms.")
    args = ap.parse_args()

    if args.device != "cuda":
        print("This experiment requires the real Qwen 7B generator; refusing non-CUDA "
              "by policy for this script (use --device cuda).", file=sys.stderr)
        return 2
    import torch
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 2

    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    exact_index, all_usable = load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )
    print(f"Evidence pool: {len(all_usable)} records.", flush=True)

    if args.atomic_scope_check is not None:
        override = {"true": True, "false": False, "assertion_spans": "assertion_spans"}[args.atomic_scope_check]
        config.setdefault("correction", {})["atomic_scope_check"] = override
        print(f"NOTE: config.correction.atomic_scope_check overridden to {override!r} for this "
              f"run only (config/prototype.yaml's own file on disk is untouched).", flush=True)

    cases = load_selected_cases(outputs, repo_root, config, exact_index, all_usable, args.candidate_file)
    print(f"Loaded {len(cases)} selected cases (from {args.candidate_file}).", flush=True)

    torch.cuda.reset_peak_memory_stats()
    from src.generator import StatuteGroundingGenerator
    from src.corrector import SelectiveCorrector
    from src.verifier import NLIVerifier

    print(f"Loading generator {config['generation']['model_id']} (4-bit, CUDA)...", flush=True)
    generator = StatuteGroundingGenerator(
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
    generator.load()
    corrector = SelectiveCorrector(
        generator=generator,
        max_new_tokens=config["correction"]["max_new_tokens"],
        do_sample=config["correction"]["do_sample"],
        system_prompt=config["correction"]["system_prompt"],
    )

    print(f"Loading verifier {config['verification']['model_id']} (CUDA)...", flush=True)
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device="cuda",
    )
    verifier.load()

    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    per_framing_rows: dict[str, list] = {PREMISE_FRAMING_BARE: [], PREMISE_FRAMING_LABELED: []}
    correction_rows: list[dict] = []
    generation_seconds_total = 0.0
    n_claims_total = 0
    n_matched_total = 0

    run_t0 = time.time()
    for i, case in enumerate(cases, start=1):
        t_gen0 = time.time()
        baseline_shared = pipeline.generate_and_parse(case, generator, exact_index, all_usable, fuzzy_threshold)
        gen_elapsed = time.time() - t_gen0
        generation_seconds_total += gen_elapsed

        n_claims_total += len(baseline_shared["claims"])
        n_matched_total += sum(1 for c in baseline_shared["claims"] if c["evidence_text"])

        case_summary = {"document_id": case.document_id, "generation_seconds": round(gen_elapsed, 2)}
        for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
            arm_config = copy.deepcopy(config)
            arm_config["verification"]["premise_framing"] = framing

            baseline = copy.deepcopy(baseline_shared)
            baseline["_exact_index"] = exact_index
            baseline["_all_usable"] = all_usable
            baseline["_verifier"] = verifier

            pipeline.apply_verification(baseline, verifier, framing)

            doc_triggered = any(
                rec["evidence_text"] is not None and triggers_correction(rec) for rec in baseline["claims"]
            )

            correction_summary = None
            if doc_triggered:
                correction_summary = pipeline.apply_selective_correction(baseline, case, corrector, arm_config)
                rv = correction_summary.get("reverification") or {}
                target_id = correction_summary["triggered_for_claim_id"]
                unflagged_checked = unflagged_preserved = 0
                if correction_summary.get("regenerated_text") is not None:
                    for rec in baseline["claims"]:
                        if rec["claim_id"] == target_id:
                            continue
                        unflagged_checked += 1
                        if rec["claim_text"] in correction_summary["regenerated_text"]:
                            unflagged_preserved += 1
                correction_rows.append({
                    "framing": framing, "document_id": case.document_id,
                    "triggered_for_claim_id": target_id, "status": correction_summary["status"],
                    "original_field_text": correction_summary["original_field_text"],
                    "regenerated_text": correction_summary["regenerated_text"],
                    "reverification": rv,
                    "unflagged_checked": unflagged_checked, "unflagged_preserved": unflagged_preserved,
                })

            record = {
                "document_id": case.document_id, "case_text": case.case_text,
                "generated_field": baseline["generated_field"],
                "claims": [{k: v for k, v in c.items() if not k.startswith("_")} for c in baseline["claims"]],
                "correction": (
                    {k: v for k, v in correction_summary.items() if not k.startswith("_")}
                    if correction_summary is not None
                    else {"triggered_for_claim_id": None, "attempts": 0, "status": "not_triggered",
                          "regenerated_text": None, "original_field_text": baseline["generated_field"]["text"],
                          "reverification": None}
                ),
                "reproducibility": {
                    "seed": config["seed"], "generation_model": config["generation"]["model_id"],
                    "verification_model": config["verification"]["model_id"],
                    "confidence_threshold": config["verification"]["confidence_threshold"],
                    "premise_framing": framing,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            }
            per_framing_rows[framing].append(record)

        print(f"[{i}/{len(cases)}] {case.document_id}: gen={gen_elapsed:.1f}s, "
              f"claims={len(baseline_shared['claims'])}, "
              f"matched={sum(1 for c in baseline_shared['claims'] if c['evidence_text'])}", flush=True)

    run_elapsed = time.time() - run_t0
    torch.cuda.synchronize()
    peak_vram_mib = torch.cuda.max_memory_allocated() // (1024 * 1024)

    # ---- Aggregate metrics per arm -----------------------------------------
    per_framing_metrics = {}
    for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
        rows = per_framing_rows[framing]
        verdicts = Counter()
        for rec in rows:
            for c in rec["claims"]:
                verdicts[c["verdict"]] += 1
        corr_status = Counter(rec["correction"]["status"] for rec in rows)
        triggers = sum(1 for rec in rows if rec["correction"]["status"] != "not_triggered")
        c_rows = [r for r in correction_rows if r["framing"] == framing]
        unsafe = sum(
            1 for r in c_rows
            if r["status"] == "corrected" and (r["reverification"] or {}).get("verdict") != ENTAILED
        )
        unflagged_checked = sum(r["unflagged_checked"] for r in c_rows)
        unflagged_preserved = sum(r["unflagged_preserved"] for r in c_rows)
        per_framing_metrics[framing] = {
            "n_cases": len(rows),
            "n_claims": sum(len(rec["claims"]) for rec in rows),
            "n_claims_evidence_matched": sum(1 for rec in rows for c in rec["claims"] if c["evidence_text"]),
            "verdict_counts": dict(verdicts),
            "correction_triggers": triggers,
            "correction_attempts": sum(v for k, v in corr_status.items() if k != "not_triggered"),
            "correction_statuses": {k: v for k, v in corr_status.items() if k != "not_triggered"},
            "corrections_shipped_success": corr_status.get("corrected", 0),
            "correction_failed": corr_status.get("correction_failed", 0),
            "correction_scope_violation": corr_status.get("correction_scope_violation", 0),
            "unsafe_corrections_shipped": unsafe,
            "unflagged_claim_checked": unflagged_checked,
            "unflagged_claim_preserved": unflagged_preserved,
        }

    result = {
        "experiment": "natural_candidates_50_gpu_bare_vs_labeled",
        "data": "50 deterministically-selected, NEVER-before-evaluated NyayaRAG cases "
                "(outputs/natural_candidate_selected_ids_50.json) — genuine fresh Qwen "
                "generation, once per case, shared across both framing arms; genuine "
                "DeBERTa verification and Qwen correction per arm.",
        "n_cases": len(cases), "seed": config["seed"],
        "generation_model": config["generation"]["model_id"],
        "verification_model": config["verification"]["model_id"],
        "confidence_threshold": config["verification"]["confidence_threshold"],
        "per_framing": per_framing_metrics,
        "n_claims_shared_generation": n_claims_total,
        "n_claims_evidence_matched_shared_generation": n_matched_total,
        "runtime_seconds_total": run_elapsed,
        "runtime_seconds_generation": generation_seconds_total,
        "peak_vram_mib": peak_vram_mib,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    (outputs / f"{args.out_prefix}_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
        with (outputs / f"{args.out_prefix}_{framing}.jsonl").open("w", encoding="utf-8") as f:
            for rec in per_framing_rows[framing]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with (outputs / f"{args.out_prefix}_corrections_detail.jsonl").open("w", encoding="utf-8") as f:
        for r in correction_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    b, l = per_framing_metrics[PREMISE_FRAMING_BARE], per_framing_metrics[PREMISE_FRAMING_LABELED]
    print("\n" + "=" * 68)
    print(f"{'metric':<40}{'bare':>12}{'labeled':>14}")
    print("-" * 68)
    print(f"{'claims / evidence-matched':<40}{str(b['n_claims'])+'/'+str(b['n_claims_evidence_matched']):>12}"
          f"{str(l['n_claims'])+'/'+str(l['n_claims_evidence_matched']):>14}")
    print(f"{'verdict counts':<40}{str(b['verdict_counts']):>12}{str(l['verdict_counts']):>14}")
    print(f"{'correction triggers':<40}{b['correction_triggers']:>12}{l['correction_triggers']:>14}")
    print(f"{'correction attempts':<40}{b['correction_attempts']:>12}{l['correction_attempts']:>14}")
    print(f"{'corrections shipped':<40}{b['corrections_shipped_success']:>12}{l['corrections_shipped_success']:>14}")
    print(f"{'correction_failed':<40}{b['correction_failed']:>12}{l['correction_failed']:>14}")
    print(f"{'correction_scope_violation':<40}{b['correction_scope_violation']:>12}{l['correction_scope_violation']:>14}")
    print(f"{'unsafe shipped':<40}{b['unsafe_corrections_shipped']:>12}{l['unsafe_corrections_shipped']:>14}")
    print(f"{'unflagged preserved/checked':<40}"
          f"{str(b['unflagged_claim_preserved'])+'/'+str(b['unflagged_claim_checked']):>12}"
          f"{str(l['unflagged_claim_preserved'])+'/'+str(l['unflagged_claim_checked']):>14}")
    print("=" * 68)
    print(f"\nTotal runtime: {run_elapsed:.1f}s (generation: {generation_seconds_total:.1f}s), "
          f"peak VRAM: {peak_vram_mib} MiB")
    print(f"\nWrote {outputs / (args.out_prefix + '_metrics.json')}")
    print(f"Wrote {outputs / (args.out_prefix + '_bare.jsonl')}")
    print(f"Wrote {outputs / (args.out_prefix + '_labeled.jsonl')}")
    print(f"Wrote {outputs / (args.out_prefix + '_corrections_detail.jsonl')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
