#!/usr/bin/env python3
"""Score model predictions against lawyer annotations without collapsing targets.

Prediction CSV must contain annotation_id plus:
  predicted_statement_correctness
  predicted_reference_correctness

Both prediction columns must use the same Yes/No/Partially label space as the
lawyer annotations. No automatic mapping from NLI labels is performed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

LABELS = ["Yes", "No", "Partially"]
TARGETS = {
    "statement_correctness": "predicted_statement_correctness",
    "reference_correctness": "predicted_reference_correctness",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return records


def _validate_unique(values: pd.Series, name: str) -> None:
    if values.isna().any():
        raise ValueError(f"{name} contains missing values")
    if values.duplicated().any():
        duplicates = values[values.duplicated()].astype(str).tolist()[:5]
        raise ValueError(f"{name} contains duplicate IDs: {duplicates}")


def _target_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_recall_fscore_support(
            y_true, y_pred, labels=LABELS, average="macro", zero_division=0
        )[0]),
        "macro_recall": float(precision_recall_fscore_support(
            y_true, y_pred, labels=LABELS, average="macro", zero_division=0
        )[1]),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "per_class": {
            label: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate(LABELS)
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        "confusion_matrix_label_order": LABELS,
        "n": len(y_true),
    }


def evaluate(annotation_records: list[dict[str, Any]], predictions: pd.DataFrame) -> dict[str, Any]:
    annotations = pd.DataFrame(annotation_records)
    if "annotation_id" not in annotations or "case_reference" not in annotations:
        raise ValueError("Annotations must contain annotation_id and case_reference")
    if "annotation" in annotations:
        raise ValueError("Unexpected nested annotation schema; import normalized JSONL first")
    _validate_unique(annotations["annotation_id"], "annotation_id")
    _validate_unique(predictions.get("annotation_id", pd.Series(dtype=object)), "prediction annotation_id")

    required = {"annotation_id", *TARGETS.values()}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError("Prediction CSV is missing columns: " + ", ".join(missing))

    merged = annotations.merge(
        predictions[list(required)],
        on="annotation_id",
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    unmatched = merged.loc[merged["_merge"] != "both", ["annotation_id", "_merge"]]
    if not unmatched.empty:
        sample = unmatched.head(10).to_dict(orient="records")
        raise ValueError(f"Annotation/prediction IDs do not match exactly: {sample}")

    output: dict[str, Any] = {
        "dataset": "NyayaMind Lawyer-Reviewed Statutory Claim Dataset",
        "n_rows": int(len(merged)),
        "n_unique_cases": int(merged["case_reference"].nunique()),
        "label_order": LABELS,
        "targets": {},
        "warning": (
            "Metrics measure agreement with supplied annotations, not universal legal truth. "
            "Rows are clustered by case and must not be treated as independent observations."
        ),
    }
    for target, prediction_column in TARGETS.items():
        truth = merged[target].astype(str).tolist()
        predicted = merged[prediction_column].astype(str).tolist()
        invalid = sorted((set(truth) | set(predicted)) - set(LABELS))
        if invalid:
            raise ValueError(f"{target}: labels outside {LABELS}: {invalid}")
        output["targets"][target] = _target_metrics(truth, predicted)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        records = _load_jsonl(args.annotations)
        predictions = pd.read_csv(args.predictions)
        result = evaluate(records, predictions)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: evaluation failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "status": "ok",
        "n_rows": result["n_rows"],
        "n_unique_cases": result["n_unique_cases"],
        "targets": {
            name: {"accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"]}
            for name, metrics in result["targets"].items()
        },
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
