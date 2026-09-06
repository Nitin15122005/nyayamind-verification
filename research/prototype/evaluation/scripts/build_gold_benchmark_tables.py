#!/usr/bin/env python3
"""STEP 4 Phase 6/7 -- build expected-vs-actual CSV tables and the aggregate summary,
mechanically, directly from the per-record prediction files written by
run_gold01_evaluation.py and run_gold02_evaluation.py. Nothing here re-computes a
number by any means other than reading those files' own ID/EXPECTED/ACTUAL columns --
per Phase 7's requirement that the comparison be mechanically reproducible from them.

Primary rows use premise_framing="labeled" (the actual production config value).
Secondary "bare" framing results are included in gold_verifier_summary.csv for
completeness/cross-check but are not the primary per-record comparison.

Usage:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/build_gold_benchmark_tables.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
RUN_DIR = TESTING_DIR / "actual_outputs" / "gold_benchmark_runs"
OUT_DIR = TESTING_DIR / "comparisons" / "expected_vs_actual"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_expected_vs_actual_csv(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ID", "EXPECTED", "ACTUAL", "MATCH", "CONFIDENCE"])
        for r in records:
            w.writerow([
                r["id"],
                r["expected_label"],
                r["predicted_label"],
                "MATCH" if r["match"] else "MISMATCH",
                f"{r['confidence']:.6f}" if r.get("confidence") is not None else "",
            ])


def summarize(records: list[dict], dataset: str, framing: str) -> dict:
    n = len(records)
    correct = sum(1 for r in records if r["match"])
    incorrect = n - correct
    accuracy = correct / n if n else 0.0

    labels = sorted({r["expected_label"] for r in records})
    per_class = {}
    for lbl in labels:
        tp = sum(1 for r in records if r["expected_label"] == lbl and r["predicted_label"] == lbl)
        fp = sum(1 for r in records if r["expected_label"] != lbl and r["predicted_label"] == lbl)
        fn = sum(1 for r in records if r["expected_label"] == lbl and r["predicted_label"] != lbl)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[lbl] = (prec, rec, f1)

    macro_p = sum(v[0] for v in per_class.values()) / len(per_class) if per_class else 0.0
    macro_r = sum(v[1] for v in per_class.values()) / len(per_class) if per_class else 0.0
    macro_f1 = sum(v[2] for v in per_class.values()) / len(per_class) if per_class else 0.0

    return {
        "dataset": dataset, "framing": framing, "n": n, "correct": correct,
        "incorrect": incorrect, "accuracy": accuracy,
        "macro_precision": macro_p, "macro_recall": macro_r, "macro_f1": macro_f1,
    }


def main() -> int:
    gold01_labeled = load_jsonl(RUN_DIR / "gold01_controlled" / "gold01_predictions_labeled.jsonl")
    gold01_bare = load_jsonl(RUN_DIR / "gold01_controlled" / "gold01_predictions_bare.jsonl")
    gold02_labeled = load_jsonl(RUN_DIR / "gold02_synthetic" / "gold02_predictions_labeled.jsonl")
    gold02_bare = load_jsonl(RUN_DIR / "gold02_synthetic" / "gold02_predictions_bare.jsonl")

    # Phase 6: primary per-record tables use the production (labeled) framing.
    write_expected_vs_actual_csv(gold01_labeled, OUT_DIR / "gold01_expected_vs_actual.csv")
    write_expected_vs_actual_csv(gold02_labeled, OUT_DIR / "gold02_expected_vs_actual.csv")
    print(f"Wrote {OUT_DIR / 'gold01_expected_vs_actual.csv'} ({len(gold01_labeled)} rows)")
    print(f"Wrote {OUT_DIR / 'gold02_expected_vs_actual.csv'} ({len(gold02_labeled)} rows)")

    # Phase 7: aggregate summary, computed fresh from the same per-record data, both framings.
    summaries = [
        summarize(gold01_labeled, "GOLD-01", "labeled"),
        summarize(gold01_bare, "GOLD-01", "bare"),
        summarize(gold02_labeled, "GOLD-02", "labeled"),
        summarize(gold02_bare, "GOLD-02", "bare"),
    ]
    summary_path = OUT_DIR / "gold_verifier_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dataset", "framing", "n", "correct", "incorrect", "accuracy",
                    "macro_precision", "macro_recall", "macro_f1"])
        for s in summaries:
            w.writerow([s["dataset"], s["framing"], s["n"], s["correct"], s["incorrect"],
                        f"{s['accuracy']:.6f}", f"{s['macro_precision']:.6f}",
                        f"{s['macro_recall']:.6f}", f"{s['macro_f1']:.6f}"])
    print(f"Wrote {summary_path}")

    # Sanity: mechanical consistency check -- the CSV's own MATCH column must agree
    # with a fresh count of EXPECTED==ACTUAL, and with the aggregate table's counts.
    for name, records, summ in [
        ("GOLD-01 labeled", gold01_labeled, summaries[0]),
        ("GOLD-02 labeled", gold02_labeled, summaries[2]),
    ]:
        recomputed_correct = sum(1 for r in records if r["expected_label"] == r["predicted_label"])
        assert recomputed_correct == summ["correct"], f"{name}: MATCH column disagrees with a fresh EXPECTED==ACTUAL count"
        print(f"Consistency check OK for {name}: {recomputed_correct}/{summ['n']} correct, MATCH column agrees")

    for s in summaries:
        print(s)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
