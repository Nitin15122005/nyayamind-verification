"""Dependency-light metrics for the frozen NyayaMind NLI benchmarks."""
from __future__ import annotations

LABELS = ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION")


def classification_metrics(expected, predicted):
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have equal length")
    columns = list(LABELS)
    columns.extend(sorted({p for p in predicted if p not in columns and p is not None}))
    if any(p is None for p in predicted):
        columns.append("INFERENCE_FAILURE")
    cm = {gold: {pred: 0 for pred in columns} for gold in LABELS}
    for gold, pred in zip(expected, predicted):
        if gold not in LABELS:
            raise ValueError(f"unsupported gold label: {gold!r}")
        cm[gold][pred if pred is not None else "INFERENCE_FAILURE"] += 1
    per_class = {}
    for label in LABELS:
        tp = cm[label].get(label, 0)
        fp = sum(cm[g].get(label, 0) for g in LABELS if g != label)
        fn = sum(cm[label].values()) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1,
                            "support": sum(cm[label].values()), "tp": tp, "fp": fp, "fn": fn}
    n = len(expected)
    return {"n": n, "accuracy": sum(g == p for g, p in zip(expected, predicted)) / n if n else None,
            "macro_f1": sum(x["f1"] for x in per_class.values()) / len(LABELS),
            "weighted_f1": sum(x["f1"] * x["support"] for x in per_class.values()) / n if n else None,
            "per_class": per_class, "confusion_matrix": cm}


def mean(values):
    xs = [float(x) for x in values if x is not None]
    return sum(xs) / len(xs) if xs else None
