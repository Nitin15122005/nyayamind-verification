#!/usr/bin/env python3
"""Generate leakage-aware out-of-fold majority-class baselines for lawyer labels.

This is a deliberately simple reference baseline, not a NyayaMind model score.
Each target is evaluated independently with StratifiedGroupKFold, grouping all
rows from a case_reference into the same fold.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

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


def majority_label(values: list[str]) -> str:
    counts = Counter(values)
    return max(LABELS, key=lambda label: counts[label])


def generate(annotations: list[dict[str, Any]], *, n_splits: int = 5, seed: int = 20261109):
    if not annotations:
        raise ValueError("No annotations supplied")
    frame = pd.DataFrame(annotations)
    required = {"annotation_id", "case_reference", *TARGETS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Annotations missing fields: " + ", ".join(sorted(missing)))
    if frame["annotation_id"].isna().any() or frame["annotation_id"].duplicated().any():
        raise ValueError("annotation_id must be non-null and unique")
    if frame["case_reference"].isna().any():
        raise ValueError("case_reference must be non-null")
    n_cases = frame["case_reference"].nunique()
    if n_splits < 2 or n_splits > n_cases:
        raise ValueError(f"n_splits must be between 2 and number of cases ({n_cases})")

    predictions = pd.DataFrame({"annotation_id": frame["annotation_id"]})
    metadata = {
        "baseline": "out_of_fold_training_majority_class",
        "n_rows": int(len(frame)),
        "n_unique_cases": int(n_cases),
        "n_splits": n_splits,
        "seed": seed,
        "grouping": "case_reference",
        "targets": {},
        "warning": (
            "This is a majority-class reference baseline, not a NyayaMind model. "
            "Predictions are out-of-fold and no case appears in both train and test "
            "within a fold. The two lawyer targets are evaluated independently."
        ),
    }

    for target, prediction_column in TARGETS.items():
        labels = frame[target].astype(str)
        invalid = sorted(set(labels) - set(LABELS))
        if invalid:
            raise ValueError(f"{target} contains labels outside {LABELS}: {invalid}")
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        output = pd.Series(index=frame.index, dtype="object")
        fold_details = []
        for fold, (train_idx, test_idx) in enumerate(
            splitter.split(frame, labels, groups=frame["case_reference"]), start=1
        ):
            train_groups = set(frame.iloc[train_idx]["case_reference"])
            test_groups = set(frame.iloc[test_idx]["case_reference"])
            overlap = train_groups & test_groups
            if overlap:
                raise RuntimeError(f"Case leakage in fold {fold}: {sorted(overlap)}")
            prediction = majority_label(labels.iloc[train_idx].tolist())
            output.iloc[test_idx] = prediction
            fold_details.append({
                "fold": fold,
                "train_cases": len(train_groups),
                "test_cases": len(test_groups),
                "train_rows": len(train_idx),
                "test_rows": len(test_idx),
                "training_majority_prediction": prediction,
                "training_label_counts": dict(Counter(labels.iloc[train_idx].tolist())),
                "test_label_counts": dict(Counter(labels.iloc[test_idx].tolist())),
            })
        if output.isna().any():
            raise RuntimeError(f"{target}: some rows did not receive an out-of-fold prediction")
        predictions[prediction_column] = output
        metadata["targets"][target] = {
            "label_counts": dict(Counter(labels.tolist())),
            "folds": fold_details,
        }
    return predictions, metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path(
        "research/data/lawyer-review/processed/lawyer_review.normalized.jsonl"
    ))
    parser.add_argument("--predictions", type=Path, default=Path(
        "research/data/lawyer-review/processed/majority_baseline.oof.csv"
    ))
    parser.add_argument("--metadata", type=Path, default=Path(
        "research/data/lawyer-review/processed/majority_baseline.oof.json"
    ))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261109)
    args = parser.parse_args(argv)
    try:
        predictions, metadata = generate(
            load_jsonl(args.annotations), n_splits=args.folds, seed=args.seed
        )
        args.predictions.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        predictions.to_csv(args.predictions, index=False)
        args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(json.dumps({
        "status": "ok",
        "n_rows": metadata["n_rows"],
        "n_unique_cases": metadata["n_unique_cases"],
        "folds": metadata["n_splits"],
        "predictions": str(args.predictions),
        "metadata": str(args.metadata),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
