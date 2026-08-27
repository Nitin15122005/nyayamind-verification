#!/usr/bin/env python3
"""
Deterministic confidence-calibration / threshold-sensitivity analysis
(Priority 4 of the CPU pre-GPU optimization pass). NO model inference —
every number here is re-derived from the FULL 3-way softmax probability
distribution (`raw_scores`) already stored in the committed
controlled_benchmark_deberta_{,labeled_}results.jsonl files, replaying
the EXACT decision rule `src/verifier.py`'s `verify()` uses (argmax label;
downgrade to NOT_ENOUGH_INFORMATION with sub_reason="low_confidence" if
argmax confidence < threshold) at a sweep of candidate thresholds.

This does NOT change config/prototype.yaml's threshold (still 0.70) — it
only measures what WOULD happen at other thresholds, to inform (not
pre-empt) any future, separately-decided threshold change. Per the task
brief: "Do not change thresholds merely to improve metrics."

READ-ONLY: only reads existing committed outputs. Writes
outputs/threshold_sensitivity_analysis.{json,md}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

from src.verifier import ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION

_RAW_LABEL_TO_VERDICT = {
    "entailment": ENTAILED, "contradiction": CONTRADICTED, "neutral": NOT_ENOUGH_INFORMATION,
}

THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
PRODUCTION_THRESHOLD = 0.70


def apply_threshold(raw_scores: dict, threshold: float) -> tuple[str, float, str | None]:
    """Exact replica of NLIVerifier.verify()'s decision rule, operating on
    an already-computed raw_scores dict instead of a live model call."""
    argmax_label = max(raw_scores, key=lambda k: raw_scores[k])
    argmax_conf = raw_scores[argmax_label]
    verdict = _RAW_LABEL_TO_VERDICT[argmax_label]
    sub_reason = None
    if argmax_conf < threshold:
        verdict = NOT_ENOUGH_INFORMATION
        sub_reason = "low_confidence"
    return verdict, argmax_conf, sub_reason


def score_at_threshold(records: list[dict], threshold: float) -> dict:
    n = len(records)
    correct = 0
    per_label_tp = {ENTAILED: 0, CONTRADICTED: 0, NOT_ENOUGH_INFORMATION: 0}
    per_label_fp = {ENTAILED: 0, CONTRADICTED: 0, NOT_ENOUGH_INFORMATION: 0}
    per_label_fn = {ENTAILED: 0, CONTRADICTED: 0, NOT_ENOUGH_INFORMATION: 0}
    n_low_confidence_downgrades = 0

    for r in records:
        verdict, conf, sub_reason = apply_threshold(r["raw_scores"], threshold)
        expected = r["expected_label"]
        if sub_reason == "low_confidence":
            n_low_confidence_downgrades += 1
        if verdict == expected:
            correct += 1
            per_label_tp[expected] += 1
        else:
            per_label_fn[expected] += 1
            per_label_fp[verdict] += 1

    def f1(label):
        tp, fp, fn = per_label_tp[label], per_label_fp[label], per_label_fn[label]
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    macro_f1 = sum(f1(l) for l in per_label_tp) / 3
    return {
        "threshold": threshold, "accuracy": correct / n, "macro_f1": macro_f1,
        "n_low_confidence_downgrades": n_low_confidence_downgrades,
        "entailed_f1": f1(ENTAILED), "contradicted_f1": f1(CONTRADICTED), "nei_f1": f1(NOT_ENOUGH_INFORMATION),
    }


def main() -> int:
    outputs = _PROTOTYPE_ROOT / "outputs"
    results = {}
    for framing, fname in [("bare", "controlled_benchmark_deberta_results.jsonl"),
                            ("labeled", "controlled_benchmark_deberta_labeled_results.jsonl")]:
        path = outputs / fname
        if not path.exists():
            continue
        records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        sweep = [score_at_threshold(records, t) for t in THRESHOLDS]
        results[framing] = {"n_items": len(records), "sweep": sweep}
        print(f"[{framing}] {len(records)} items", flush=True)
        for row in sweep:
            marker = "  <- PRODUCTION DEFAULT" if abs(row["threshold"] - PRODUCTION_THRESHOLD) < 1e-9 else ""
            print(f"  t={row['threshold']:.2f}  acc={row['accuracy']:.3f}  "
                  f"macroF1={row['macro_f1']:.3f}  low_conf_downgrades={row['n_low_confidence_downgrades']}{marker}",
                  flush=True)

    (outputs / "threshold_sensitivity_analysis.json").write_text(
        json.dumps({"production_threshold": PRODUCTION_THRESHOLD, "results": results}, indent=2),
        encoding="utf-8",
    )

    md = [
        "# Confidence Calibration / Threshold Sensitivity (deterministic, no re-inference)",
        "",
        "_No GPU, no model call — every row replays the exact"
        " `NLIVerifier.verify()` decision rule against the already-computed"
        " full softmax distribution stored in the committed 420-item controlled"
        " benchmark. Threshold NOT changed in config/prototype.yaml (still 0.70)._",
        "",
    ]
    for framing, data in results.items():
        md += [f"## {framing} framing ({data['n_items']} items)", "",
               "| threshold | accuracy | macro F1 | ENTAILED F1 | CONTRADICTED F1 | NEI F1 | low_conf downgrades |",
               "|---:|---:|---:|---:|---:|---:|---:|"]
        for row in data["sweep"]:
            mark = " **(production)**" if abs(row["threshold"] - PRODUCTION_THRESHOLD) < 1e-9 else ""
            md.append(f"| {row['threshold']:.2f}{mark} | {row['accuracy']:.3f} | {row['macro_f1']:.3f} | "
                       f"{row['entailed_f1']:.3f} | {row['contradicted_f1']:.3f} | {row['nei_f1']:.3f} | "
                       f"{row['n_low_confidence_downgrades']} |")
        md.append("")
    (outputs / "threshold_sensitivity_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nWrote {outputs / 'threshold_sensitivity_analysis.json'}")
    print(f"Wrote {outputs / 'threshold_sensitivity_analysis.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
