#!/usr/bin/env python3
"""
V2 FRESH — confidence-threshold sensitivity, ORIGINAL (bare) vs LATEST (labeled).

WHAT THIS MEASURES
------------------
How macro F1 on GOLD-01 (n=420) moves as `verification.confidence_threshold`
sweeps 0.34 -> 0.99, for BOTH premise framings. It answers: is the production
threshold of 0.70 a tuned value carrying hidden credit for the labeled-framing
result, or is it sitting on a flat plateau where the framing effect dominates?

NO NEW INFERENCE IS RUN. This recomputes verdicts from the per-item softmax
distributions already stored by the fresh GOLD-01 rerun
(`metrics/gold01_v2_predictions_{bare,labeled}.jsonl`), replaying exactly the
verdict rule in `src/verifier.py`:

    verdict = map(argmax(raw_scores))
    if argmax_confidence < threshold: verdict = NOT_ENOUGH_INFORMATION

Because the argmax over three classes is always > 1/3, thresholds at or below
0.3333 can never downgrade anything; the sweep therefore starts just above that
floor. Everything here is deterministic arithmetic over stored numbers.

OUTPUT
------
metrics/threshold_sensitivity_v2.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
_PROTOTYPE_ROOT = _V2_ROOT.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))

METRICS_DIR = _V2_ROOT / "metrics"

ENTAILED = "ENTAILED"
CONTRADICTED = "CONTRADICTED"
NEI = "NOT_ENOUGH_INFORMATION"
LABELS = (ENTAILED, CONTRADICTED, NEI)

RAW_TO_VERDICT = {"entailment": ENTAILED, "contradiction": CONTRADICTED, "neutral": NEI}

PRODUCTION_THRESHOLD = 0.70


def macro_f1_and_acc(expected, predicted):
    cm = {e: {p: 0 for p in LABELS} for e in LABELS}
    for e, p in zip(expected, predicted):
        cm[e][p] += 1
    f1s = []
    for lbl in LABELS:
        tp = cm[lbl][lbl]
        fp = sum(cm[o][lbl] for o in LABELS if o != lbl)
        fn = sum(cm[lbl][o] for o in LABELS if o != lbl)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    acc = sum(1 for e, p in zip(expected, predicted) if e == p) / len(expected)
    return sum(f1s) / len(f1s), acc


def load(framing: str):
    path = METRICS_DIR / f"gold01_v2_predictions_{framing}.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows, path


def main() -> int:
    thresholds = [round(0.34 + 0.01 * i, 2) for i in range(0, 66)]  # 0.34 .. 0.99
    out_by_framing = {}
    sanity = {}

    for framing in ("bare", "labeled"):
        rows, path = load(framing)
        expected = [r["expected_label"] for r in rows]
        raws = [r["raw_scores"] for r in rows]
        stored = [r["predicted_label"] for r in rows]

        sweep = []
        for th in thresholds:
            preds = []
            for raw in raws:
                best_lbl = max(raw, key=raw.get)
                conf = raw[best_lbl]
                v = RAW_TO_VERDICT[best_lbl]
                if conf < th:
                    v = NEI
                preds.append(v)
            f1, acc = macro_f1_and_acc(expected, preds)
            sweep.append({"threshold": th, "macro_f1": f1, "accuracy": acc})

        # Sanity: replaying at the production threshold must reproduce the
        # verdicts actually stored by the rerun. If it does not, the replay
        # rule has drifted from src/verifier.py and nothing below is valid.
        replay_prod = []
        for raw in raws:
            best_lbl = max(raw, key=raw.get)
            v = RAW_TO_VERDICT[best_lbl]
            if raw[best_lbl] < PRODUCTION_THRESHOLD:
                v = NEI
            replay_prod.append(v)
        matches = sum(1 for a, b in zip(replay_prod, stored) if a == b)
        sanity[framing] = {
            "n": len(stored),
            "replay_matches_stored_verdicts": matches,
            "exact": matches == len(stored),
            "source_file": str(path.relative_to(_V2_ROOT)),
        }

        best = max(sweep, key=lambda d: d["macro_f1"])
        at_prod = next(d for d in sweep if d["threshold"] == PRODUCTION_THRESHOLD)
        plateau = [d["threshold"] for d in sweep if best["macro_f1"] - d["macro_f1"] <= 0.005]
        out_by_framing[framing] = {
            "sweep": sweep,
            "best": best,
            "at_production_threshold": at_prod,
            "gap_to_optimum_macro_f1": best["macro_f1"] - at_prod["macro_f1"],
            "plateau_within_0.005_macro_f1": {
                "min_threshold": min(plateau), "max_threshold": max(plateau),
                "n_thresholds": len(plateau),
            },
        }

    if not all(s["exact"] for s in sanity.values()):
        print("ABORT: threshold replay does not reproduce the stored verdicts.")
        print(json.dumps(sanity, indent=2))
        return 1

    # Minimum framing gap across the whole sweep: if the labeled arm beats the
    # bare arm at EVERY threshold, the effect cannot be a threshold artifact.
    gaps = [
        out_by_framing["labeled"]["sweep"][i]["macro_f1"] - out_by_framing["bare"]["sweep"][i]["macro_f1"]
        for i in range(len(thresholds))
    ]
    min_gap_idx = min(range(len(gaps)), key=lambda i: gaps[i])

    out = {
        "artifact_id": "THRESHOLD-SENS-V2",
        "measurement": "macro F1 vs confidence_threshold, ORIGINAL (bare) vs LATEST (labeled), GOLD-01 n=420",
        "evidence_grade": "GOLD",
        "grade_note": (
            "Derived deterministically from the fresh GOLD-01 gold-labelled run's stored "
            "softmax distributions. No new inference; no model reloaded. Descriptive "
            "sensitivity analysis — no significance test is attached to a threshold sweep."
        ),
        "no_new_inference": True,
        "source_artifacts": [
            "metrics/gold01_v2_predictions_bare.jsonl",
            "metrics/gold01_v2_predictions_labeled.jsonl",
        ],
        "verdict_rule_replayed": (
            "verdict = map(argmax(raw_scores)); if argmax_confidence < threshold -> "
            "NOT_ENOUGH_INFORMATION (src/verifier.py:218-222)"
        ),
        "sweep_range": {"min": thresholds[0], "max": thresholds[-1], "step": 0.01,
                        "floor_note": "argmax of 3 classes always exceeds 1/3, so thresholds <= 0.3333 are inert"},
        "production_threshold": PRODUCTION_THRESHOLD,
        "replay_sanity_check": sanity,
        "by_framing": out_by_framing,
        "framing_gap": {
            "description": "labeled macro F1 minus bare macro F1, at every threshold in the sweep",
            "min_gap": gaps[min_gap_idx],
            "min_gap_at_threshold": thresholds[min_gap_idx],
            "max_gap": max(gaps),
            "labeled_beats_bare_at_every_threshold": all(g > 0 for g in gaps),
            "interpretation": (
                "If the labeled arm leads at every threshold, the ORIGINAL->LATEST verifier "
                "result is not an artifact of the chosen threshold."
            ),
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "v2_outputs_phase_3_vedant/scripts/compute_threshold_sensitivity_v2.py",
    }

    p = METRICS_DIR / "threshold_sensitivity_v2.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")

    for f in ("bare", "labeled"):
        d = out_by_framing[f]
        print(f"  {f:8} best macro F1 {d['best']['macro_f1']:.4f} @ {d['best']['threshold']:.2f} | "
              f"@0.70 {d['at_production_threshold']['macro_f1']:.4f} | "
              f"gap {d['gap_to_optimum_macro_f1']:.4f} | "
              f"plateau {d['plateau_within_0.005_macro_f1']['min_threshold']:.2f}-"
              f"{d['plateau_within_0.005_macro_f1']['max_threshold']:.2f}")
    print(f"  labeled leads at every threshold: {out['framing_gap']['labeled_beats_bare_at_every_threshold']}")
    print(f"  smallest gap {out['framing_gap']['min_gap']:.4f} at threshold {out['framing_gap']['min_gap_at_threshold']}")
    print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
