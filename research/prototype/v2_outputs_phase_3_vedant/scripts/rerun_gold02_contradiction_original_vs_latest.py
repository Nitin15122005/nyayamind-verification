#!/usr/bin/env python3
"""
V2 FRESH RERUN — GOLD-02 synthetic contradiction stress set, 2x2 factorial.

WHAT THIS MEASURES
------------------
Contradiction detection on the 59-item deterministic synthetic stress set,
under a full 2x2 crossing of the two VERIFICATION levers that differ between
ORIGINAL and LATEST NyayaMind:

    premise_framing        : bare (ORIGINAL)  vs labeled (LATEST)
    narrow_primary_hypothesis : False (ORIGINAL) vs True (LATEST)

The four cells are:
    ORIGINAL_config : bare    + narrow=False   <- the original verification config
    LATEST_config   : labeled + narrow=True    <- the production verification config
    plus the two single-lever cells, which give the main effect of each lever
    in isolation.

Reporting the 2x2 means the headline ORIGINAL->LATEST number is a genuine
config-to-config comparison, while each lever's individual contribution stays
separately visible. Nothing is attributed to a lever that was not varied alone.

GOLD LABELS
-----------
Every record in this set is CONTRADICTED-by-construction: `synthetic_stress.py`
deterministically inverts a phrase actually present in the matched record's real
canonical statute text. There is no `expected_label` field in the fixture, so —
following the existing GOLD-02 runner's stronger integrity check — this script
RE-DERIVES all 59 synthetic claims from the v0 evidence pool with the same
`build_synthetic_stress_claims()` that produced the frozen fixture, and confirms
each re-derived claim matches the fixture's stored text/transform_rule/evidence
identity before treating CONTRADICTED as the gold label.

Because the single gold class is CONTRADICTED, the only well-defined metric is
CONTRADICTED **recall** over the 59 items. Macro F1 / accuracy over a
single-class set are degenerate and are NOT reported as headline numbers.

SCOPE / HONESTY
---------------
- Evidence pool is held at v0 in all four cells (the synthetic claims are built
  FROM the v0 pool, so using v1 would change the item set, not just the arm).
- NO_EVIDENCE claims are reported separately: the verifier is never called for
  them by design, so they are neither detections nor misses of the verifier —
  they are retrieval outcomes. Recall is reported BOTH over all 59 items and
  over only the evidence-matched subset, with both denominators printed.
- CPU only. No Qwen. No generation. No correction. Deterministic (greedy argmax).

OUTPUT
------
metrics/gold02_v2_metrics.json
metrics/gold02_v2_predictions.jsonl
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
_PROTOTYPE_ROOT = _V2_ROOT.parent
_REPO_ROOT = _PROTOTYPE_ROOT.parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))
sys.path.insert(0, str(_PROTOTYPE_ROOT / "scripts"))

import yaml  # noqa: E402

from src import claim_parser, pipeline  # noqa: E402
from src.data_loader import load_usable_evidence  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402
from src.synthetic_stress import build_synthetic_stress_claims  # noqa: E402
from src.verifier import NLIVerifier, CONTRADICTED, NOT_ENOUGH_INFORMATION  # noqa: E402

NO_EVIDENCE = "NO_EVIDENCE"
# Same unflagged filler sentence the original synthetic runner appends, so the
# parsed paragraph shape matches the frozen fixture exactly.
from compare_premise_framing_synthetic import (  # noqa: E402
    build_baseline, triggers_correction, UNFLAGGED_SENTENCE,
)

FIXTURE = _PROTOTYPE_ROOT / "outputs" / "run_synthetic_stress.jsonl"
CONFIG_PATH = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
METRICS_DIR = _V2_ROOT / "metrics"

CELLS = [
    ("ORIGINAL_config", "bare", False),
    ("framing_only", "labeled", False),
    ("narrow_only", "bare", True),
    ("LATEST_config", "labeled", True),
]


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson_ci(successes: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(correct_a, correct_b):
    b = sum(1 for x, y in zip(correct_a, correct_b) if x and not y)
    c = sum(1 for x, y in zip(correct_a, correct_b) if (not x) and y)
    n = b + c
    if n == 0:
        return {"b_only_A": 0, "c_only_B": 0, "n_discordant": 0, "p_value": 1.0,
                "test": "McNemar exact binomial (two-sided)", "note": "no discordant pairs"}
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return {"b_only_A": b, "c_only_B": c, "n_discordant": n,
            "p_value": min(1.0, 2.0 * tail),
            "test": "McNemar exact binomial (two-sided)"}


def main() -> int:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    usable_verdicts = set(cfg["usable_evidence_verdicts"])
    vcfg = cfg["verification"]

    c0 = _REPO_ROOT / paths["canonical_statutes"]
    a0 = _REPO_ROOT / paths["evidence_audit"]
    exact_index, all_usable = load_usable_evidence(c0, a0, usable_verdicts)
    print(f"v0 evidence pool: {len(all_usable)} usable records")

    # ---- integrity: re-derive the synthetic claims and check against fixture ----
    synth_claims = build_synthetic_stress_claims(all_usable)
    fixture_rows = [json.loads(l) for l in FIXTURE.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_id = {r["synthetic_claim_id"]: r for r in fixture_rows}

    integrity = {"n_rederived": len(synth_claims), "n_fixture": len(fixture_rows),
                 "mismatches": [], "verified": False}
    for sc in synth_claims:
        row = by_id.get(sc.claim_id)
        if row is None:
            integrity["mismatches"].append({"claim_id": sc.claim_id, "issue": "absent from fixture"})
            continue
        if row.get("original_synthetic_text") != sc.claim_text:
            integrity["mismatches"].append({"claim_id": sc.claim_id, "issue": "claim_text differs"})
        if row.get("transform_rule") != sc.transform_rule:
            integrity["mismatches"].append({"claim_id": sc.claim_id, "issue": "transform_rule differs"})
    integrity["verified"] = (
        not integrity["mismatches"] and len(synth_claims) == len(fixture_rows)
    )
    print(f"fixture integrity: rederived={len(synth_claims)} fixture={len(fixture_rows)} "
          f"verified={integrity['verified']} mismatches={len(integrity['mismatches'])}")
    if not integrity["verified"]:
        print("ABORT: cannot treat CONTRADICTED as gold without a clean re-derivation.")
        (METRICS_DIR / "gold02_v2_metrics.json").write_text(
            json.dumps({"artifact_id": "GOLD02-V2-FRESH", "status": "ABORTED_INTEGRITY",
                        "integrity": integrity}, indent=2), encoding="utf-8")
        return 1

    # ---- build the baselines once; verification is what varies across cells ----
    baselines = [build_baseline(sc, exact_index, all_usable, cfg) for sc in synth_claims]

    verifier = NLIVerifier(
        model_id=vcfg["model_id"],
        confidence_threshold=vcfg["confidence_threshold"],
        max_sequence_length=vcfg["max_sequence_length"],
        device="cpu",
    )
    t0 = time.time()
    verifier.load()
    print(f"verifier loaded on cpu in {time.time()-t0:.1f}s")

    import copy
    results = {}
    detected_flags = {}
    pred_rows = []

    for cell_name, framing, narrow in CELLS:
        recs = copy.deepcopy(baselines)
        t = time.time()
        for rec in recs:
            pipeline.apply_verification(
                rec, verifier,
                premise_framing=framing,
                narrow_primary_hypothesis=narrow,
            )
        elapsed = time.time() - t

        # The synthetic claim is the FIRST claim of each paragraph (the filler
        # sentence carries no citation). Score only the synthetic claim.
        verdicts, matched_flags, detected = [], [], []
        for sc, rec in zip(synth_claims, recs):
            target = None
            for cr in rec["claims"]:
                cit = cr.get("citation_extracted") or {}
                if (cit.get("provision_number") == sc.provision_number):
                    target = cr
                    break
            if target is None and rec["claims"]:
                target = rec["claims"][0]
            v = target["verdict"] if target else NO_EVIDENCE
            has_ev = v != NO_EVIDENCE
            verdicts.append(v)
            matched_flags.append(has_ev)
            detected.append(v == CONTRADICTED)
            pred_rows.append({
                "cell": cell_name, "premise_framing": framing,
                "narrow_primary_hypothesis": narrow,
                "synthetic_claim_id": sc.claim_id,
                "evidence_id": target.get("evidence_id") if target else None,
                "evidence_matched": has_ev,
                "verdict": v,
                "confidence": target.get("confidence") if target else None,
                "sub_reason": target.get("sub_reason") if target else None,
                "triggers_correction": triggers_correction(target) if target else False,
            })

        n_total = len(verdicts)
        n_matched = sum(matched_flags)
        n_detected = sum(detected)
        n_detected_matched = sum(1 for d, m in zip(detected, matched_flags) if m)

        results[cell_name] = {
            "premise_framing": framing,
            "narrow_primary_hypothesis": narrow,
            "n_items": n_total,
            "n_evidence_matched": n_matched,
            "n_no_evidence": n_total - n_matched,
            "n_detected_contradicted": n_detected,
            "contradiction_recall_all_items": n_detected / n_total,
            "contradiction_recall_all_items_ci95": list(wilson_ci(n_detected, n_total)),
            "contradiction_recall_evidence_matched_only": (
                n_detected_matched / n_matched if n_matched else 0.0),
            "contradiction_recall_evidence_matched_only_ci95": list(
                wilson_ci(n_detected_matched, n_matched)),
            "verdict_distribution": dict(Counter(verdicts)),
            "n_triggers_correction": sum(
                1 for r in pred_rows if r["cell"] == cell_name and r["triggers_correction"]),
            "elapsed_seconds": elapsed,
        }
        detected_flags[cell_name] = detected
        print(f"  {cell_name:16} framing={framing:8} narrow={str(narrow):5} "
              f"recall(all)={results[cell_name]['contradiction_recall_all_items']:.4f} "
              f"detected={n_detected}/{n_total} no_evidence={n_total-n_matched}")

    headline = mcnemar_exact(detected_flags["ORIGINAL_config"], detected_flags["LATEST_config"])
    framing_effect = mcnemar_exact(detected_flags["ORIGINAL_config"], detected_flags["framing_only"])
    narrow_effect = mcnemar_exact(detected_flags["ORIGINAL_config"], detected_flags["narrow_only"])

    out = {
        "artifact_id": "GOLD02-V2-FRESH",
        "benchmark_tag": "GOLD-02_synthetic_stress_set",
        "design": "2x2 factorial: premise_framing x narrow_primary_hypothesis",
        "comparison": "ORIGINAL verification config (bare, narrow=False) vs LATEST (labeled, narrow=True)",
        "evidence_grade": "DETERMINISTIC_SYNTHETIC",
        "grade_note": (
            "Gold class is CONTRADICTED-by-construction for all 59 items, re-derived and "
            "integrity-checked against the frozen fixture this run. Synthetic, not natural "
            "data: it probes whether contradiction is DETECTED, and says nothing about "
            "real-world legal accuracy. Single-class set, so only recall is well-defined — "
            "accuracy and macro F1 would be degenerate and are deliberately not reported."
        ),
        "n_items": len(synth_claims),
        "fixture_path": str(FIXTURE.relative_to(_PROTOTYPE_ROOT)),
        "fixture_sha256": sha256_of(FIXTURE),
        "fixture_integrity_check": integrity,
        "evidence_pool": {
            "canonical": str(c0.relative_to(_REPO_ROOT)),
            "usable_records": len(all_usable),
            "held_constant_across_cells": True,
            "why": "synthetic claims are constructed FROM this pool; changing it changes the item set",
        },
        "verifier_model": vcfg["model_id"],
        "confidence_threshold": vcfg["confidence_threshold"],
        "max_sequence_length": vcfg["max_sequence_length"],
        "device": "cpu",
        "deterministic": True,
        "seed_required": False,
        "cells": results,
        "headline_delta": {
            "metric": "contradiction_recall_all_items",
            "original": results["ORIGINAL_config"]["contradiction_recall_all_items"],
            "latest": results["LATEST_config"]["contradiction_recall_all_items"],
            "absolute_delta": (results["LATEST_config"]["contradiction_recall_all_items"]
                               - results["ORIGINAL_config"]["contradiction_recall_all_items"]),
        },
        "statistics": {
            "original_vs_latest_mcnemar": headline,
            "main_effect_premise_framing_mcnemar": framing_effect,
            "main_effect_narrow_primary_mcnemar": narrow_effect,
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "torch": __import__("torch").__version__,
            "transformers": __import__("transformers").__version__,
            "cuda_available": __import__("torch").cuda.is_available(),
        },
        "historical_comparison_reference": (
            "research/prototype/evaluation/actual_outputs/gold_benchmark_runs/"
            "gold02_synthetic/gold02_metrics.json"
        ),
        "generated_by": "v2_outputs_phase_3_vedant/scripts/rerun_gold02_contradiction_original_vs_latest.py",
    }

    (METRICS_DIR / "gold02_v2_metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (METRICS_DIR / "gold02_v2_predictions.jsonl").open("w", encoding="utf-8") as fh:
        for r in pred_rows:
            fh.write(json.dumps(r) + "\n")

    print("\n=== GOLD-02 RESULT ===")
    print(f"  ORIGINAL config recall : {out['headline_delta']['original']:.4f}")
    print(f"  LATEST   config recall : {out['headline_delta']['latest']:.4f}")
    print(f"  delta                  : {out['headline_delta']['absolute_delta']:+.4f}")
    print(f"  McNemar p (orig->latest): {headline['p_value']:.4f} (discordant={headline['n_discordant']})")
    print(f"  wrote {METRICS_DIR / 'gold02_v2_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
