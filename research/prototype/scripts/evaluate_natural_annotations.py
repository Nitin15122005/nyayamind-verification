#!/usr/bin/env python3
"""Evaluate frozen natural-case annotations against archived pipeline predictions.

NO_EVIDENCE is reported as evidence coverage/abstention, not silently relabelled
as NOT_ENOUGH_INFORMATION. Bootstrap resampling is clustered by document_id.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

LABELS = ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def read_annotations(path: Path) -> dict[tuple[str, str], dict]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row.get("document_id", "").strip(), row.get("claim_id", "").strip())
            if not all(key):
                raise ValueError("Annotation rows require document_id and claim_id")
            if key in result:
                raise ValueError(f"Duplicate annotation key: {key}")
            label = row.get("adjudicated_label", "").strip().upper()
            if label not in LABELS:
                raise ValueError(f"{key}: missing or invalid adjudicated_label {label!r}")
            result[key] = row
    if not result:
        raise ValueError("No adjudicated annotations found")
    return result


def prediction_map(path: Path) -> dict[tuple[str, str], str]:
    result = {}
    for record in read_jsonl(path):
        doc = str(record.get("document_id") or "")
        for claim in record.get("claims") or []:
            key = (doc, str(claim.get("claim_id") or ""))
            if not all(key):
                continue
            if key in result:
                raise ValueError(f"Duplicate prediction key: {key}")
            result[key] = str(claim.get("verdict") or "").upper()
    return result


def metrics(rows: list[tuple[str, str, str]]) -> dict:
    """Rows are (document_id, gold, prediction), all prediction labels in LABELS."""
    matrix = {g: {p: 0 for p in LABELS} for g in LABELS}
    for _, gold, pred in rows:
        matrix[gold][pred] += 1
    per_class = {}
    f1s = []
    for label in LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[g][label] for g in LABELS if g != label)
        fn = sum(matrix[label][p] for p in LABELS if p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1,
                            "support": sum(matrix[label].values())}
        f1s.append(f1)
    return {
        "n": len(rows),
        "accuracy": sum(matrix[x][x] for x in LABELS) / len(rows) if rows else None,
        "macro_f1": sum(f1s) / len(f1s) if rows else None,
        "per_class": per_class,
        "confusion_matrix_gold_rows_predicted_columns": matrix,
    }


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def evaluate(annotations: dict, predictions: dict, bootstrap: int, seed: int) -> dict:
    matched, no_evidence, missing = [], [], []
    for key, ann in annotations.items():
        pred = predictions.get(key)
        if pred is None:
            missing.append(key)
        elif pred in LABELS:
            matched.append((key[0], ann["adjudicated_label"].strip().upper(), pred))
        elif pred in {"NO_EVIDENCE", "NO_EVIDENCE_TEMPORAL", "TEMPORAL_UNVERIFIED"}:
            no_evidence.append(key)
        else:
            missing.append(key)
    base = metrics(matched)
    groups: dict[str, list[tuple[str, str, str]]] = {}
    for row in matched:
        groups.setdefault(row[0], []).append(row)
    cluster_ids = sorted(groups)
    ci = None
    if cluster_ids and bootstrap > 0:
        rng = random.Random(seed)
        accs, f1s = [], []
        for _ in range(bootstrap):
            sampled = [cluster_ids[rng.randrange(len(cluster_ids))] for _ in cluster_ids]
            sample = [row for doc in sampled for row in groups[doc]]
            m = metrics(sample)
            accs.append(m["accuracy"])
            f1s.append(m["macro_f1"])
        ci = {
            "cluster_bootstrap_replicates": bootstrap,
            "seed": seed,
            "accuracy_95pct_ci": [percentile(accs, .025), percentile(accs, .975)],
            "macro_f1_95pct_ci": [percentile(f1s, .025), percentile(f1s, .975)],
        }
    return {
        "evaluation": "natural case claim-level; independently adjudicated labels only",
        "n_annotated": len(annotations),
        "n_prediction_labelled": len(matched),
        "n_no_evidence": len(no_evidence),
        "n_missing_prediction": len(missing),
        "evidence_coverage_on_annotated_claims": len(matched) / len(annotations),
        "selective_metrics_on_evidence_labelled_subset": base,
        "cluster_bootstrap": ci,
        "cluster_unit": "document_id",
        "excluded_no_evidence_keys": [list(k) for k in no_evidence],
        "missing_prediction_keys": [list(k) for k in missing],
        "interpretation": (
            "Metrics are conditional on the annotated sample and evidence-labelled subset. "
            "NO_EVIDENCE is reported separately and is not treated as an NLI class. "
            "The cluster bootstrap does not correct sampling bias or label error."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261104)
    args = parser.parse_args()
    if args.bootstrap < 0:
        parser.error("--bootstrap must be non-negative")
    result = evaluate(read_annotations(args.annotations), prediction_map(args.predictions),
                      args.bootstrap, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
