#!/usr/bin/env python3
"""Score three-class predictions against lawyer annotations on two separate targets.

Prediction CSV columns: annotation_id, predicted_statement_correctness,
predicted_reference_correctness. No automatic mapping from NLI labels is made.
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


def _metrics(truth: list[str], predicted: list[str]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, predicted, labels=LABELS, zero_division=0
    )
    return {
        "n": len(truth),
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1_score(truth, predicted, labels=LABELS, average="macro", zero_division=0)),
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
    }


def evaluate(annotations: list[dict[str, Any]], predictions: pd.DataFrame) -> dict[str, Any]:
    gold = pd.DataFrame(annotations)
    if not {"annotation_id", "case_reference", *TARGETS}.issubset(gold.columns):
        raise ValueError("Normalized annotations are missing required fields")
    _unique(gold["annotation_id"], "annotation_id")
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

    result: dict[str, Any] = {
        "dataset": "NyayaMind Lawyer-Reviewed Statutory Claim Dataset",
        "n_rows": int(len(merged)),
        "n_unique_cases": int(merged["case_reference"].nunique()),
        "label_order": LABELS,
        "targets": {},
        "warning": (
            "Scores measure agreement with supplied annotations, not universal legal truth. "
            "Rows are clustered by case and are not independent observations."
        ),
    }
    for target, prediction_column in TARGETS.items():
        truth = merged[target].astype(str).tolist()
        predicted = merged[prediction_column].astype(str).tolist()
        invalid = sorted((set(truth) | set(predicted)) - set(LABELS))
        if invalid:
            raise ValueError(f"{target}: labels outside {LABELS}: {invalid}")
        result["targets"][target] = _metrics(truth, predicted)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(load_jsonl(args.annotations), pd.read_csv(args.predictions))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: evaluation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "ok", "n_rows": result["n_rows"],
        "n_unique_cases": result["n_unique_cases"],
        "targets": {k: {"accuracy": v["accuracy"], "macro_f1": v["macro_f1"]}
                    for k, v in result["targets"].items()},
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
