#!/usr/bin/env python3
"""Evaluate explicit three-class predictions against lawyer annotations.

Prediction CSV columns: annotation_id, predicted_statement_correctness,
predicted_reference_correctness. NLI labels are deliberately not mapped to
lawyer labels. Confidence intervals use a case-cluster bootstrap.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

LABELS = ["Yes", "No", "Partially"]
TARGETS = {
    "statement_correctness": "predicted_statement_correctness",
    "reference_correctness": "predicted_reference_correctness",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return records


def _unique(series: pd.Series, name: str) -> None:
    if series.isna().any() or series.duplicated().any():
        raise ValueError(f"{name} must contain non-null, unique IDs")


def _metric_pair(truth: list[str], predicted: list[str]) -> tuple[float, float]:
    return (
        float(accuracy_score(truth, predicted)),
        float(f1_score(truth, predicted, labels=LABELS, average="macro", zero_division=0)),
    )


def _case_bootstrap(
    frame: pd.DataFrame, target: str, prediction_column: str, *,
    n_bootstrap: int, seed: int, confidence_level: float,
) -> dict[str, Any]:
    """Percentile intervals from resampling whole cases, retaining all rows per draw."""
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")
    case_groups = {
        case: group for case, group in frame.groupby("case_reference", sort=True)
    }
    cases = list(case_groups)
    if len(cases) < 2:
        raise ValueError("At least two unique cases are required for case-cluster bootstrap")
    rng = np.random.default_rng(seed)
    accuracies: list[float] = []
    macro_f1s: list[float] = []
    for _ in range(n_bootstrap):
        sampled = rng.choice(cases, size=len(cases), replace=True)
        draw = pd.concat([case_groups[case] for case in sampled], ignore_index=True)
        accuracy, macro_f1 = _metric_pair(
            draw[target].astype(str).tolist(),
            draw[prediction_column].astype(str).tolist(),
        )
        accuracies.append(accuracy)
        macro_f1s.append(macro_f1)
    alpha = (1.0 - confidence_level) / 2.0
    def interval(values: list[float]) -> list[float]:
        return [float(x) for x in np.quantile(values, [alpha, 1.0 - alpha])]
    return {
        "method": "nonparametric percentile bootstrap resampling case_reference clusters",
        "replicates": n_bootstrap,
        "seed": seed,
        "confidence_level": confidence_level,
        "accuracy_interval": interval(accuracies),
        "macro_f1_interval": interval(macro_f1s),
        "unit_resampled": "case_reference",
    }


def _metrics(
    frame: pd.DataFrame, target: str, prediction_column: str, *,
    n_bootstrap: int, seed: int, confidence_level: float,
) -> dict[str, Any]:
    truth = frame[target].astype(str).tolist()
    predicted = frame[prediction_column].astype(str).tolist()
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, predicted, labels=LABELS, zero_division=0
    )
    accuracy, macro_f1 = _metric_pair(truth, predicted)
    return {
        "n": len(truth),
        "accuracy": accuracy,
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": macro_f1,
        "per_class": {
            label: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate(LABELS)
        },
        "confusion_matrix": confusion_matrix(truth, predicted, labels=LABELS).tolist(),
        "confusion_matrix_label_order": LABELS,
        "case_cluster_bootstrap": _case_bootstrap(
            frame, target, prediction_column, n_bootstrap=n_bootstrap,
            seed=seed, confidence_level=confidence_level,
        ),
    }


def evaluate(
    annotations: list[dict[str, Any]], predictions: pd.DataFrame, *,
    n_bootstrap: int = 2000, seed: int = 20261109,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    if not annotations:
        raise ValueError("Normalized annotations contain no rows")
    gold = pd.DataFrame(annotations)
    if not {"annotation_id", "case_reference", *TARGETS}.issubset(gold.columns):
        raise ValueError("Normalized annotations are missing required fields")
    _unique(gold["annotation_id"], "annotation_id")
    if gold["case_reference"].isna().any():
        raise ValueError("case_reference must be non-null for leakage-aware evaluation")
    required = {"annotation_id", *TARGETS.values()}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError("Prediction CSV missing columns: " + ", ".join(sorted(missing)))
    _unique(predictions["annotation_id"], "prediction annotation_id")
    merged = gold.merge(
        predictions[list(required)], on="annotation_id", how="outer",
        indicator=True, validate="one_to_one",
    )
    if (merged["_merge"] != "both").any():
        sample = merged.loc[merged["_merge"] != "both", ["annotation_id", "_merge"]].head(10)
        raise ValueError(f"Annotation/prediction IDs do not match exactly: {sample.to_dict('records')}")
    merged = merged.drop(columns="_merge")
    for target, prediction_column in TARGETS.items():
        invalid = sorted(
            (set(merged[target].astype(str)) | set(merged[prediction_column].astype(str))) - set(LABELS)
        )
        if invalid:
            raise ValueError(f"{target}: labels outside {LABELS}: {invalid}")

    result: dict[str, Any] = {
        "dataset": "NyayaMind Lawyer-Reviewed Statutory Claim Dataset",
        "n_rows": int(len(merged)),
        "n_unique_cases": int(merged["case_reference"].nunique()),
        "label_order": LABELS,
        "targets": {},
        "bootstrap_configuration": {
            "method": "case-cluster percentile bootstrap",
            "replicates": n_bootstrap,
            "seed": seed,
            "confidence_level": confidence_level,
        },
        "warning": (
            "Scores measure agreement with supplied annotations, not universal legal truth. "
            "Rows are clustered by case; confidence intervals therefore resample cases, not rows. "
            "Intervals quantify sampling variability under this bootstrap and do not account for "
            "annotator disagreement, dataset selection bias, or label validity."
        ),
    }
    for target, prediction_column in TARGETS.items():
        result["targets"][target] = _metrics(
            merged, target, prediction_column, n_bootstrap=n_bootstrap,
            seed=seed, confidence_level=confidence_level,
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    args = parser.parse_args(argv)
    try:
        result = evaluate(
            load_jsonl(args.annotations), pd.read_csv(args.predictions),
            n_bootstrap=args.bootstrap_replicates, seed=args.seed,
            confidence_level=args.confidence_level,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: evaluation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "ok", "n_rows": result["n_rows"],
        "n_unique_cases": result["n_unique_cases"],
        "targets": {k: {
            "accuracy": v["accuracy"], "macro_f1": v["macro_f1"],
            "accuracy_ci": v["case_cluster_bootstrap"]["accuracy_interval"],
            "macro_f1_ci": v["case_cluster_bootstrap"]["macro_f1_interval"],
        } for k, v in result["targets"].items()},
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
