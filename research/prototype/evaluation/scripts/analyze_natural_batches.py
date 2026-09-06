#!/usr/bin/env python3
"""STEP 6 Phase 6 -- per-batch descriptive tabulation of existing natural batches.

Reads each batch's ALREADY-COMPUTED, historical verdict/evidence data directly from
research/prototype/outputs/ (read-only) and tabulates it per batch, separately (never
merged across batches unless the source methodology already treats them as one
aggregate -- it does not, per outputs/final_research_results.md's own "10 distinct
regimes, never pooled" statement). This is HISTORICAL RESULT tabulation, not fresh
re-computation -- the fresh, re-derived layer for the batches folded into the 588/209
analyses already exists in run_step6_588_evaluation.py / run_step6_209_paired_evaluation.py.

No Qwen generation or correction is invoked. No natural-data accuracy/F1 is calculated.

Writes only under research/prototype/evaluation/.
"""
from __future__ import annotations

import datetime
import json
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"

OUT_DIR = TESTING_DIR / "actual_outputs" / "natural_data_runs" / "batches"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BATCHES = [
    {"name": "n30_mode_B", "file": "run_B_n30.jsonl", "config": "bare, v0-only, legacy scope (pre-2026-08-27 default)", "sub": None},
    {"name": "targeted_mode_B", "file": "run_natural_targeted.jsonl", "config": "bare, v0-only, legacy scope", "sub": "mode_B"},
    {"name": "batch1_bare", "file": "natural_candidates_50_gpu_bare.jsonl", "config": "bare, v0-only", "sub": None},
    {"name": "batch1_labeled", "file": "natural_candidates_50_gpu_labeled.jsonl", "config": "labeled, v0-only", "sub": None},
    {"name": "batch2_bare", "file": "natural_candidates_batch2_gpu_bare.jsonl", "config": "bare, v0-only", "sub": None},
    {"name": "batch2_labeled", "file": "natural_candidates_batch2_gpu_labeled.jsonl", "config": "labeled, v0-only", "sub": None},
    {"name": "final_validation_arm_A", "file": "final_gpu_validation_A.jsonl", "config": "bare, v0-only, legacy scope (ORIGINAL)", "sub": None},
    {"name": "final_validation_arm_B", "file": "final_gpu_validation_B.jsonl", "config": "bare (as stored), v0+v1, assertion_spans (pre-labeled-decision)", "sub": None},
]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    except Exception as e:
        return f"UNKNOWN ({e!r})"


def analyze_batch(spec: dict) -> dict:
    path = OUTPUTS / spec["file"]
    if not path.exists():
        return {"name": spec["name"], "file": spec["file"], "status": "MISSING"}

    cases = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    all_claims = []
    for case in cases:
        block = case[spec["sub"]] if spec["sub"] else case
        for c in block.get("claims", []):
            all_claims.append(c)

    n_claims = len(all_claims)
    n_matched = sum(1 for c in all_claims if c.get("evidence_text"))
    verdicts = Counter(c.get("verdict") for c in all_claims)
    confidences = [c["confidence"] for c in all_claims if c.get("confidence") is not None]
    n_contradicted = verdicts.get("CONTRADICTED", 0)

    correction_status = None
    corr_counter = Counter()
    for case in cases:
        block = case[spec["sub"]] if spec["sub"] else case
        corr = block.get("correction")
        if corr and corr.get("status"):
            corr_counter[corr["status"]] += 1
    if corr_counter:
        correction_status = dict(corr_counter)

    return {
        "name": spec["name"],
        "file": spec["file"],
        "configuration": spec["config"],
        "n_cases": len(cases),
        "n_claims": n_claims,
        "n_evidence_matched": n_matched,
        "evidence_coverage": n_matched / n_claims if n_claims else None,
        "no_evidence_rate": 1 - (n_matched / n_claims) if n_claims else None,
        "verdict_distribution": dict(verdicts),
        "n_contradicted_raw_count": n_contradicted,
        "confidence_stats": {
            "n": len(confidences),
            "mean": statistics.mean(confidences) if confidences else None,
            "median": statistics.median(confidences) if confidences else None,
        } if confidences else None,
        "correction_status_counts_historical": correction_status,
        "result_classification": "HISTORICAL RESULT (verdicts as originally computed at generation time, tabulated fresh this run -- not re-verified)",
        "gpu_execution_claimed": False,
        "status": "analyzed",
    }


def main() -> int:
    results = [analyze_batch(spec) for spec in BATCHES]

    for r in results:
        if r["status"] == "MISSING":
            print(f"[MISSING] {r['name']} -- {r['file']}")
        else:
            print(f"[OK] {r['name']}: n_cases={r['n_cases']} n_claims={r['n_claims']} "
                  f"coverage={r['evidence_coverage']:.4f} verdicts={r['verdict_distribution']}")

    out = {
        "batches": results,
        "note": "Batches are reported SEPARATELY, never merged, per outputs/final_research_results.md's own '10 distinct regimes, never pooled' methodology.",
        "produced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repo_commit": git_commit(),
    }
    (OUT_DIR / "batches_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'batches_analysis.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
