#!/usr/bin/env python3
"""Evaluate structured verifier signals against lawyer labels using case-grouped CV.

Only uniquely aligned claim/provision rows are eligible. The model uses structured
retrieval/verifier metadata, never lawyer correction text, supporting authorities,
case IDs, legal statement text, or annotation-derived audit conclusions.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

LABELS = ["Yes", "No", "Partially"]
TARGETS = ["statement_correctness", "reference_correctness"]
CATEGORICAL = [
    "provision_type", "act_match", "evidence_match_method", "verdict",
    "verifier_model", "evidence_present", "provision_identifier_match", "reference_text_match",
]
NUMERIC = ["confidence", "candidate_count"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def build_feature_frame(annotations: list[dict[str, Any]], audit: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    audit_rows = {str(row.get("annotation_id")): row for row in audit.get("rows", [])}
    if len(audit_rows) != len(audit.get("rows", [])):
        raise ValueError("Alignment audit contains duplicate or missing annotation IDs")
    records = []
    exclusions = Counter()
    for annotation in annotations:
        aid = str(annotation["annotation_id"])
        row = audit_rows.get(aid)
        if row is None:
            exclusions["missing_audit_row"] += 1
            continue
        if not row.get("exact_statement_match"):
            exclusions["no_exact_statement_match"] += 1
            continue
        if int(row.get("num_reference_aligned_matches", 0)) != 1:
            exclusions["reference_alignment_not_unique"] += 1
            continue
        candidates = row.get("matched_model_claims") or []
        aligned = [c for c in candidates if
                   c.get("provision_identifier_match")
                   and c.get("act_match") != "mismatch"]
        if len(aligned) != 1:
            exclusions["candidate_alignment_not_unique"] += 1
            continue
        claim = aligned[0]
        confidence = claim.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else np.nan
        except (TypeError, ValueError):
            confidence = np.nan
        records.append({
            "annotation_id": aid,
            "case_reference": str(annotation["case_reference"]),
            "statement_correctness": annotation["statement_correctness"],
            "reference_correctness": annotation["reference_correctness"],
            "provision_type": claim.get("provision_type") or "MISSING",
            "act_match": claim.get("act_match") or "MISSING",
            "evidence_match_method": claim.get("evidence_match_method") or "MISSING",
            "verdict": claim.get("verdict") or "MISSING",
            "verifier_model": claim.get("verifier_model") or "MISSING",
            "evidence_present": "yes" if claim.get("evidence_id") or claim.get("evidence_text") else "no",
            "provision_identifier_match": str(bool(claim.get("provision_identifier_match"))),
            "reference_text_match": str(bool(claim.get("reference_text_match"))),
            "confidence": confidence,
            "candidate_count": float(row.get("num_distinct_statement_matches", 0)),
        })
    frame = pd.DataFrame(records)
    if not frame.empty:
        for target in TARGETS:
            invalid = sorted(set(frame[target].astype(str)) - set(LABELS))
            if invalid:
                raise ValueError(f"{target}: unsupported labels {invalid}")
    diagnostics = {
        "n_annotations": len(annotations),
        "n_eligible_rows": len(frame),
        "n_eligible_cases": int(frame["case_reference"].nunique()) if not frame.empty else 0,
        "excluded_rows": dict(exclusions),
        "eligibility": "exact statement match and exactly one compatible provision/Act candidate",
        "feature_policy": "structured verifier/retrieval metadata only; no text, IDs, corrections, authorities, or annotation-derived fields",
    }
    return frame, diagnostics


def _pipeline(categorical: list[str] | None = None, numeric: list[str] | None = None) -> Pipeline:
    categorical = CATEGORICAL if categorical is None else categorical
    numeric = NUMERIC if numeric is None else numeric
    prep = ColumnTransformer([
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="constant", fill_value="MISSING")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
         ]), categorical),
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
         ]), numeric),
    ])
    return Pipeline([
        ("features", prep),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5)),
    ])


def _scores(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    return {
        "n": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "per_class": {
            label: {"precision": float(precision[i]), "recall": float(recall[i]),
                    "f1": float(f1[i]), "support": int(support[i])}
            for i, label in enumerate(LABELS)
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
    }


def _cluster_bootstrap(frame: pd.DataFrame, y_col: str, pred_col: str, *, reps: int, seed: int) -> dict[str, Any]:
    groups = {case: group for case, group in frame.groupby("case_reference", sort=True)}
    cases = list(groups)
    if len(cases) < 2:
        raise ValueError("At least two eligible cases are required for cluster bootstrap")
    rng = np.random.default_rng(seed)
    acc, mf1 = [], []
    for _ in range(reps):
        draw_cases = rng.choice(cases, size=len(cases), replace=True)
        draw = pd.concat([groups[c] for c in draw_cases], ignore_index=True)
        s = _scores(draw[y_col].astype(str).tolist(), draw[pred_col].astype(str).tolist())
        acc.append(s["accuracy"])
        mf1.append(s["macro_f1"])
    return {
        "method": "case_reference cluster percentile bootstrap",
        "replicates": reps, "seed": seed, "confidence_level": 0.95,
        "accuracy_interval": [float(x) for x in np.quantile(acc, [0.025, 0.975])],
        "macro_f1_interval": [float(x) for x in np.quantile(mf1, [0.025, 0.975])],
    }


def _paired_cluster_difference_bootstrap(
    frame: pd.DataFrame, y_col: str, model_col: str, baseline_col: str,
    *, reps: int, seed: int,
) -> dict[str, Any]:
    """Paired case-cluster bootstrap of model-minus-baseline OOF metrics."""
    groups = {case: group for case, group in frame.groupby("case_reference", sort=True)}
    cases = list(groups)
    if len(cases) < 2:
        raise ValueError("At least two eligible cases are required for paired bootstrap")
    rng = np.random.default_rng(seed)
    accuracy_diff, macro_f1_diff = [], []
    for _ in range(reps):
        sampled = rng.choice(cases, size=len(cases), replace=True)
        draw = pd.concat([groups[case] for case in sampled], ignore_index=True)
        gold = draw[y_col].astype(str).tolist()
        model = _scores(gold, draw[model_col].astype(str).tolist())
        baseline = _scores(gold, draw[baseline_col].astype(str).tolist())
        accuracy_diff.append(model["accuracy"] - baseline["accuracy"])
        macro_f1_diff.append(model["macro_f1"] - baseline["macro_f1"])
    return {
        "method": "paired case_reference cluster percentile bootstrap",
        "difference": "model minus same-fold majority baseline",
        "replicates": reps, "seed": seed, "confidence_level": 0.95,
        "accuracy_difference_interval": [float(x) for x in np.quantile(accuracy_diff, [0.025, 0.975])],
        "macro_f1_difference_interval": [float(x) for x in np.quantile(macro_f1_diff, [0.025, 0.975])],
    }


ABLATION_FEATURES = {
    "without_provision_identity": {
        "categorical": ["act_match", "provision_identifier_match"],
        "numeric": [],
        "remove": ["provision_type", "act_match", "provision_identifier_match"],
    },
    "without_retrieval_evidence": {
        "categorical": ["evidence_match_method", "evidence_present", "reference_text_match"],
        "numeric": [],
        "remove": ["evidence_match_method", "evidence_present", "reference_text_match"],
    },
    "without_nli_signal": {
        "categorical": ["verdict"],
        "numeric": ["confidence"],
        "remove": ["verdict", "confidence"],
    },
    "without_model_metadata": {
        "categorical": ["verifier_model"],
        "numeric": ["candidate_count"],
        "remove": ["verifier_model", "candidate_count"],
    },
}


def evaluate(frame: pd.DataFrame, *, folds: int = 5, seed: int = 20261109, bootstrap_reps: int = 2000) -> tuple[pd.DataFrame, dict[str, Any]]:
    if frame.empty:
        raise ValueError("No uniquely aligned rows are eligible")
    if frame["case_reference"].nunique() < folds:
        raise ValueError("Number of eligible cases must be at least the fold count")
    all_predictions = []
    results: dict[str, Any] = {}
    for target in TARGETS:
        y = frame[target].astype(str)
        splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
        model_pred = pd.Series(index=frame.index, dtype="object")
        majority_pred = pd.Series(index=frame.index, dtype="object")
        fold_info = []
        for fold, (train_idx, test_idx) in enumerate(
            splitter.split(frame, y, groups=frame["case_reference"]), start=1
        ):
            train_cases = set(frame.iloc[train_idx]["case_reference"])
            test_cases = set(frame.iloc[test_idx]["case_reference"])
            if train_cases & test_cases:
                raise RuntimeError(f"Case leakage in {target} fold {fold}")
            train = frame.iloc[train_idx]
            test = frame.iloc[test_idx]
            train_majority = Counter(train[target]).most_common(1)[0][0]
            majority_pred.iloc[test_idx] = train_majority
            model = _pipeline()
            model.fit(train[CATEGORICAL + NUMERIC], train[target])
            model_pred.iloc[test_idx] = model.predict(test[CATEGORICAL + NUMERIC])
            fold_info.append({
                "fold": fold, "train_cases": len(train_cases), "test_cases": len(test_cases),
                "train_rows": len(train_idx), "test_rows": len(test_idx),
                "train_majority": train_majority,
            })
        if model_pred.isna().any() or majority_pred.isna().any():
            raise RuntimeError(f"{target}: missing out-of-fold predictions")
        result_frame = frame[["annotation_id", "case_reference", target]].copy()
        result_frame[f"predicted_{target}_model"] = model_pred
        result_frame[f"predicted_{target}_majority"] = majority_pred
        all_predictions.append(result_frame)
        ablation_results = {}
        for ablation_name, spec in ABLATION_FEATURES.items():
            cat_cols = [col for col in CATEGORICAL if col not in spec["remove"]]
            num_cols = [col for col in NUMERIC if col not in spec["remove"]]
            ablation_pred = pd.Series(index=frame.index, dtype="object")
            for fold, (train_idx, test_idx) in enumerate(
                splitter.split(frame, y, groups=frame["case_reference"]), start=1
            ):
                train = frame.iloc[train_idx]
                test = frame.iloc[test_idx]
                ablation_model = _pipeline(cat_cols, num_cols)
                ablation_model.fit(train[cat_cols + num_cols], train[target])
                ablation_pred.iloc[test_idx] = ablation_model.predict(test[cat_cols + num_cols])
            if ablation_pred.isna().any():
                raise RuntimeError(f"{target}/{ablation_name}: missing OOF predictions")
            ablation_frame = frame[["case_reference", target]].copy()
            ablation_frame["prediction"] = ablation_pred
            ablation_results[ablation_name] = {
                "removed_features": spec["remove"],
                "remaining_features": cat_cols + num_cols,
                "scores": _scores(y.tolist(), ablation_pred.tolist()),
                "case_cluster_bootstrap": _cluster_bootstrap(
                    ablation_frame.rename(columns={target: "gold"}),
                    "gold", "prediction", reps=bootstrap_reps, seed=seed
                ),
            }
        model_scores = _scores(y.tolist(), model_pred.tolist())
        majority_scores = _scores(y.tolist(), majority_pred.tolist())
        model_for_boot = result_frame.rename(columns={
            target: "gold", f"predicted_{target}_model": "prediction"
        })
        majority_for_boot = result_frame.rename(columns={
            target: "gold", f"predicted_{target}_majority": "prediction"
        })
        results[target] = {
            "n": len(frame), "n_unique_cases": int(frame["case_reference"].nunique()),
            "model": model_scores,
            "model_case_cluster_bootstrap": _cluster_bootstrap(
                model_for_boot, "gold", "prediction", reps=bootstrap_reps, seed=seed
            ),
            "majority_baseline": majority_scores,
            "majority_case_cluster_bootstrap": _cluster_bootstrap(
                majority_for_boot, "gold", "prediction", reps=bootstrap_reps, seed=seed
            ),
            "paired_model_minus_majority_bootstrap": _paired_cluster_difference_bootstrap(
                result_frame, target, f"predicted_{target}_model",
                f"predicted_{target}_majority", reps=bootstrap_reps, seed=seed
            ),
            "folds": fold_info,
            "feature_ablations": ablation_results,
        }
    predictions = all_predictions[0][["annotation_id", "case_reference"]].copy()
    for result_frame in all_predictions:
        target = next(t for t in TARGETS if f"predicted_{t}_model" in result_frame.columns)
        predictions[f"gold_{target}"] = result_frame[target]
        predictions[f"predicted_{target}_model"] = result_frame[f"predicted_{target}_model"]
        predictions[f"predicted_{target}_majority"] = result_frame[f"predicted_{target}_majority"]
    return predictions, {
        "experiment": "structured_verifier_signal_logistic_regression",
        "split": "StratifiedGroupKFold grouped by case_reference",
        "folds": folds, "seed": seed, "labels": LABELS,
        "targets": results,
        "interpretation": "Scores are agreement with supplied lawyer annotations on the uniquely aligned subset, not legal accuracy. Targets are independent. The majority comparator is generated on the same eligible rows and folds.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    args = parser.parse_args()
    annotations = read_jsonl(args.annotations)
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    frame, diagnostics = build_feature_frame(annotations, audit)
    predictions, metrics = evaluate(
        frame, folds=args.folds, seed=args.seed, bootstrap_reps=args.bootstrap_replicates
    )
    metrics["data_diagnostics"] = diagnostics
    args.predictions.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.predictions, index=False)
    args.metrics.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "data_diagnostics": diagnostics,
        "targets": metrics["targets"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
