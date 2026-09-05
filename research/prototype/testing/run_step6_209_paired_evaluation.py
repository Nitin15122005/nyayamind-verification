#!/usr/bin/env python3
"""STEP 6 Phase 5/7 -- 209-claim paired natural evaluation, fresh CPU-safe analysis.

Loads outputs/final_gpu_validation_A.jsonl (Arm A = ORIGINAL config: v0-only evidence,
bare framing, legacy scope check) and _B.jsonl (Arm B = v0+v1 evidence pool; its
ORIGINALLY-STORED verdicts used bare framing too -- premise_framing=labeled was decided
AFTER this data was generated). Both arms share identical generation (confirmed:
identical document_id order, identical claim_text per position) -- evidence was matched
independently per arm at generation time.

This script performs TWO clearly-separated things:
  1. Reads each arm's ORIGINALLY-STORED evidence/verdict fields directly -- labeled
     "HISTORICAL RESULT" throughout.
  2. Freshly re-derives, THIS RUN, evidence matching for Arm A against the v0-only pool
     (its own original, explicitly-recorded configuration) and for Arm B against the
     CURRENT production merged pool (v0+v1, 136 records) -- then freshly re-verifies
     every matched claim in both arms under the CURRENT production premise_framing
     (labeled), using the real, unmodified DeBERTa verifier, CPU-only. Labeled
     "FRESH TESTING RESULT" throughout.

No Qwen generation or correction is invoked. No natural-data accuracy/F1/correctness is
calculated anywhere -- every metric here is a paired, mechanical description of what
changed, per evaluation/METRIC_DEFINITIONS.md.

Writes only under research/prototype/testing/.

Usage:
    research/.venv/Scripts/python.exe research/prototype/testing/run_step6_209_paired_evaluation.py
"""
from __future__ import annotations

import copy
import csv
import datetime
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"

sys.path.insert(0, str(PROTOTYPE_DIR))

import yaml  # noqa: E402
from src.data_loader import load_usable_evidence_from_config  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402
from src.verifier import NLIVerifier, format_premise  # noqa: E402

OUT_DIR = TESTING_DIR / "actual_outputs" / "step6_natural_data" / "209_paired"
OUT_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR = TESTING_DIR / "evaluation"


def load_jsonl(path: Path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    except Exception as e:
        return f"UNKNOWN ({e!r})"


def mcnemar(b: int, c: int) -> tuple[float, float]:
    """Continuity-corrected McNemar chi-square + p-value (chi2 df=1), no scipy dependency."""
    if b + c == 0:
        return 0.0, 1.0
    chi2 = ((abs(b - c) - 1) ** 2) / (b + c)
    # chi2 df=1 survival function via a standard series approximation (erfc-based),
    # avoiding a scipy dependency not pinned in requirements.txt.
    import math
    p = math.erfc(math.sqrt(chi2 / 2))
    return chi2, p


def main() -> int:
    log_lines = []

    def log(msg):
        print(msg, flush=True)
        log_lines.append(msg)

    log("=" * 70)
    log("STEP 6 Phase 5/7 -- 209-claim paired natural evaluation")
    log("=" * 70)

    path_a = OUTPUTS / "final_gpu_validation_A.jsonl"
    path_b = OUTPUTS / "final_gpu_validation_B.jsonl"
    cases_a = load_jsonl(path_a)
    cases_b = load_jsonl(path_b)

    if len(cases_a) != 50 or len(cases_b) != 50:
        log(f"BLOCKER: expected 50 cases per arm, found A={len(cases_a)} B={len(cases_b)}")
        return 2
    if [c["document_id"] for c in cases_a] != [c["document_id"] for c in cases_b]:
        log("BLOCKER: document_id order differs between arms -- alignment assumption violated")
        return 2

    config = yaml.safe_load((PROTOTYPE_DIR / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root_for_loader = PROTOTYPE_DIR.parent.parent
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]
    production_framing = config["verification"]["premise_framing"]  # "labeled"

    config_v0 = copy.deepcopy(config)
    config_v0["use_evidence_v1"] = False
    exact_index_v0, pool_v0 = load_usable_evidence_from_config(config_v0, repo_root_for_loader)
    exact_index_current, pool_current = load_usable_evidence_from_config(config, repo_root_for_loader)
    log(f"Arm A fresh re-match pool (v0-only, its ORIGINAL config): {len(pool_v0)} records")
    log(f"Arm B fresh re-match pool (CURRENT production, v0+v1): {len(pool_current)} records")
    log(f"Fresh re-verification premise_framing (CURRENT production): {production_framing}")

    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except Exception:
        cuda_available = False
    log(f"NVIDIA GPU available = {'YES' if cuda_available else 'NO'}")

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device="cpu",
    )
    log("Loading real DeBERTa verifier on device=cpu ...")
    verifier.load()

    rows = []
    t0 = time.time()
    for case_a, case_b in zip(cases_a, cases_b):
        doc_id = case_a["document_id"]
        for pos, (ca, cb) in enumerate(zip(case_a["claims"], case_b["claims"])):
            if ca["claim_text"] != cb["claim_text"]:
                log(f"BLOCKER: claim_text mismatch at {doc_id} position {pos} -- alignment broken")
                return 2

            cit_a = ca.get("citation_extracted")
            cit_b = cb.get("citation_extracted")
            from src.claim_parser import ExtractedCitation
            ext_a = ExtractedCitation(**cit_a) if cit_a else None
            ext_b = ExtractedCitation(**cit_b) if cit_b else None

            match_a = match_evidence(ext_a, exact_index_v0, pool_v0, fuzzy_threshold) if ext_a else None
            match_b = match_evidence(ext_b, exact_index_current, pool_current, fuzzy_threshold) if ext_b else None

            row = {
                "claim_position_id": f"{doc_id}::{ca['claim_id']}",
                "document_id": doc_id,
                "claim_id": ca["claim_id"],
                "claim_text": ca["claim_text"],
                "historical_evidence_A": ca.get("evidence_id"),
                "historical_verdict_A": ca.get("verdict"),
                "historical_confidence_A": ca.get("confidence"),
                "historical_evidence_B": cb.get("evidence_id"),
                "historical_verdict_B": cb.get("verdict"),
                "historical_confidence_B": cb.get("confidence"),
                "fresh_evidence_matched_A": bool(match_a and match_a.matched),
                "fresh_evidence_matched_B": bool(match_b and match_b.matched),
                "fresh_evidence_id_A": match_a.evidence.dataset_citation_key if match_a and match_a.matched else None,
                "fresh_evidence_id_B": match_b.evidence.dataset_citation_key if match_b and match_b.matched else None,
                "fresh_verdict_A": None, "fresh_confidence_A": None,
                "fresh_verdict_B": None, "fresh_confidence_B": None,
            }

            for arm, match, matcher_key in (("A", match_a, "fresh_evidence_matched_A"), ("B", match_b, "fresh_evidence_matched_B")):
                if match and match.matched:
                    premise = format_premise(
                        match.evidence.canonical_text, framing=production_framing,
                        provision_type=match.evidence.provision_type,
                        provision_number=match.evidence.provision_number,
                        act=match.evidence.act,
                    )
                    r = verifier.verify(premise, ca["claim_text"] if arm == "A" else cb["claim_text"])
                    row[f"fresh_verdict_{arm}"] = r.label
                    row[f"fresh_confidence_{arm}"] = r.confidence

            # Paired mechanical change categories (evidence)
            ma, mb = row["fresh_evidence_matched_A"], row["fresh_evidence_matched_B"]
            if ma and mb:
                row["evidence_change"] = "unchanged_matched"
            elif not ma and not mb:
                row["evidence_change"] = "unchanged_no_evidence"
            elif not ma and mb:
                row["evidence_change"] = "evidence_gained"
            else:
                row["evidence_change"] = "evidence_lost"

            va, vb = row["fresh_verdict_A"], row["fresh_verdict_B"]
            if va is None and vb is None:
                row["verdict_change"] = "both_no_evidence"
            elif va == vb:
                row["verdict_change"] = "unchanged"
            else:
                row["verdict_change"] = f"changed_{va}_to_{vb}"

            rows.append(row)
    elapsed = time.time() - t0
    log(f"\nProcessed {len(rows)} paired claim positions in {elapsed:.1f}s")

    if len(rows) != 209:
        log(f"WARNING: expected 209 paired claims, got {len(rows)}")

    # ---- write per-claim CSV ----
    csv_path = EVAL_DIR / "paired_209_analysis.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"Wrote {csv_path}")

    # also save full JSONL under actual_outputs
    jsonl_path = OUT_DIR / "paired_209_full_records.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"Wrote {jsonl_path}")

    # ---- aggregate paired change counts ----
    evidence_change_counts = Counter(r["evidence_change"] for r in rows)
    verdict_change_counts = Counter(r["verdict_change"] for r in rows)
    historical_verdict_a = Counter(r["historical_verdict_A"] for r in rows)
    historical_verdict_b = Counter(r["historical_verdict_B"] for r in rows)
    fresh_verdict_a = Counter(r["fresh_verdict_A"] or "NO_EVIDENCE" for r in rows)
    fresh_verdict_b = Counter(r["fresh_verdict_B"] or "NO_EVIDENCE" for r in rows)

    # ---- McNemar's test on the evidence-coverage binary event (fresh-matched) ----
    b_count = sum(1 for r in rows if not r["fresh_evidence_matched_A"] and r["fresh_evidence_matched_B"])  # gained
    c_count = sum(1 for r in rows if r["fresh_evidence_matched_A"] and not r["fresh_evidence_matched_B"])  # lost
    chi2, p_value = mcnemar(b_count, c_count)
    n_matched_a = sum(1 for r in rows if r["fresh_evidence_matched_A"])
    n_matched_b = sum(1 for r in rows if r["fresh_evidence_matched_B"])

    log(f"\nFresh evidence coverage: Arm A (v0-only) {n_matched_a}/{len(rows)} = {n_matched_a/len(rows):.4f}, "
        f"Arm B (v0+v1) {n_matched_b}/{len(rows)} = {n_matched_b/len(rows):.4f}")
    log(f"McNemar (binary event: usable evidence found y/n): b(gained)={b_count} c(lost)={c_count} "
        f"chi2={chi2:.4f} p={p_value:.6f}")

    metrics = {
        "dataset_tag": "209_claim_paired_natural_evaluation",
        "classification": "METRIC-ONLY -- paired comparative data, not ground truth",
        "n_paired_claims": len(rows),
        "arm_A_config": {"use_evidence_v1": False, "evidence_pool_size": len(pool_v0), "note": "Arm A's ORIGINAL, explicitly-recorded configuration"},
        "arm_B_config": {"use_evidence_v1": True, "evidence_pool_size": len(pool_current), "note": "CURRENT production evidence pool"},
        "fresh_reverification_premise_framing": production_framing,
        "fresh_evidence_coverage_arm_A": n_matched_a / len(rows),
        "fresh_evidence_coverage_arm_B": n_matched_b / len(rows),
        "evidence_change_counts": dict(evidence_change_counts),
        "verdict_change_counts": dict(verdict_change_counts),
        "historical_verdict_distribution_arm_A": dict(historical_verdict_a),
        "historical_verdict_distribution_arm_B": dict(historical_verdict_b),
        "fresh_verdict_distribution_arm_A": dict(fresh_verdict_a),
        "fresh_verdict_distribution_arm_B": dict(fresh_verdict_b),
        "mcnemar_evidence_coverage": {
            "binary_event": "claim received usable evidence (yes/no)",
            "b_gained": b_count, "c_lost": c_count, "chi2": chi2, "p_value": p_value,
            "note": "Reproduces this project's existing methodology (outputs/final_gpu_validation.md) for this exact binary event -- not a new hypothesis.",
        },
        "elapsed_seconds": elapsed,
        "gpu_execution_claimed": False,
        "qwen_generation_or_correction_invoked": False,
        "device": "cpu",
        "cuda_available": cuda_available,
        "result_classification_note": "historical_* fields = HISTORICAL RESULT (as originally stored, Arm B under bare framing). fresh_* fields = FRESH TESTING RESULT (evidence re-matched and verdicts re-verified this run, both arms under current production labeled framing).",
    }
    (OUT_DIR / "paired_209_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"Wrote {OUT_DIR / 'paired_209_metrics.json'}")

    run_meta = {
        "produced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repo_commit": git_commit(),
        "python_version": platform.python_version(),
        "command_executed": "research/.venv/Scripts/python.exe research/prototype/testing/run_step6_209_paired_evaluation.py",
        "source_files": ["outputs/final_gpu_validation_A.jsonl", "outputs/final_gpu_validation_B.jsonl"],
        "nvidia_gpu_available": False,
        "cuda_available_per_torch": cuda_available,
        "qwen_generation_or_correction_invoked": False,
        "model_identifier": config["verification"]["model_id"],
    }
    (OUT_DIR / "run_metadata.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Wrote {OUT_DIR / 'run_metadata.json'}")

    (OUT_DIR / "execution_log.txt").write_text("\n".join(log_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
