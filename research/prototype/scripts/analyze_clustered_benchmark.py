#!/usr/bin/env python3
"""Cluster-aware paired analysis for GOLD-01.

The benchmark has repeated items derived from the same source provision. Treat
'evidence_key' (source provision) as the independent resampling/randomization
unit, not each JSONL row. Inputs are the per-item result files emitted by
scripts/run_controlled_benchmark.py, one for bare and one for labeled framing.

Example:
  python scripts/analyze_clustered_benchmark.py \
    --bare outputs/gold01_bare_results.jsonl \
    --labeled outputs/gold01_labeled_results.jsonl

No model inference is performed. Bootstrap and sign-flip calculations use a
fixed seed and are reproducible.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

LABELS = ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION")


def read_results(path: Path) -> dict[str, dict[str, dict]]:
    rows: dict[str, dict[str, dict]] = defaultdict(dict)
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            key, item_id = row.get("evidence_key"), row.get("benchmark_id")
            if not key or not item_id:
                raise ValueError(f"{path}:{line_no}: missing evidence_key/benchmark_id")
            if item_id in rows[key]:
                raise ValueError(f"{path}:{line_no}: duplicate benchmark_id {item_id}")
            if row.get("expected_label") not in LABELS or row.get("predicted_label") not in LABELS:
                raise ValueError(f"{path}:{line_no}: unknown label")
            rows[key][item_id] = row
    return dict(rows)


def align(bare, labeled):
    if set(bare) != set(labeled):
        raise ValueError("Bare/labeled evidence_key sets differ")
    aligned = {}
    for key in sorted(bare):
        if set(bare[key]) != set(labeled[key]):
            raise ValueError(f"Item IDs differ for evidence_key={key}")
        for item_id in bare[key]:
            a, b = bare[key][item_id], labeled[key][item_id]
            if a["expected_label"] != b["expected_label"]:
                raise ValueError(f"Gold label differs for {item_id}")
        aligned[key] = (bare[key], labeled[key])
    return aligned


def macro_f1(rows):
    scores = []
    for label in LABELS:
        tp = sum(r["predicted_label"] == label and r["expected_label"] == label
                 for r in rows)
        fp = sum(r["predicted_label"] == label and r["expected_label"] != label
                 for r in rows)
        fn = sum(r["predicted_label"] != label and r["expected_label"] == label
                 for r in rows)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall)
                      if precision + recall else 0.0)
    return sum(scores) / len(scores)


def percentile(values, p):
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bare", required=True, type=Path)
    ap.add_argument("--labeled", required=True, type=Path)
    ap.add_argument("--bootstrap", type=int, default=20000)
    ap.add_argument("--permutations", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    if args.bootstrap < 1000 or args.permutations < 1000:
        ap.error("Use at least 1,000 bootstrap replicates and permutations")

    bare = read_results(args.bare)
    labeled = read_results(args.labeled)
    paired = align(bare, labeled)
    keys = list(paired)
    if len(keys) < 2:
        raise ValueError("Need at least two independent evidence clusters")

    cluster_deltas = []
    bare_cluster_acc, labeled_cluster_acc = [], []
    bare_all, labeled_all = [], []
    for key in keys:
        a, b = paired[key]
        ar, br = list(a.values()), list(b.values())
        aa = sum(r["correct"] for r in ar) / len(ar)
        ba = sum(r["correct"] for r in br) / len(br)
        bare_cluster_acc.append(aa)
        labeled_cluster_acc.append(ba)
        cluster_deltas.append(ba - aa)
        bare_all.extend(ar)
        labeled_all.extend(br)

    observed = sum(cluster_deltas) / len(cluster_deltas)
    rng = random.Random(args.seed)
    boot_acc, boot_f1 = [], []
    n = len(keys)
    for _ in range(args.bootstrap):
        sampled = [rng.randrange(n) for _ in range(n)]
        boot_acc.append(sum(cluster_deltas[i] for i in sampled) / n)
        arows, brows = [], []
        for i in sampled:
            arows.extend(paired[keys[i]][0].values())
            brows.extend(paired[keys[i]][1].values())
        boot_f1.append(macro_f1(brows) - macro_f1(arows))

    # Paired cluster sign-flip randomization test. The unit being flipped is
    # one source provision's complete within-provision difference.
    extreme = 0
    for _ in range(args.permutations):
        permuted = sum(d if rng.getrandbits(1) else -d for d in cluster_deltas) / n
        if abs(permuted) >= abs(observed) - 1e-15:
            extreme += 1
    p_value = (extreme + 1) / (args.permutations + 1)

    def acc(rows):
        return sum(r["correct"] for r in rows) / len(rows)

    result = {
        "analysis": "paired cluster bootstrap and sign-flip randomization",
        "cluster_unit": "evidence_key (source provision)",
        "n_clusters": n,
        "n_items_per_arm": len(bare_all),
        "bare_item_accuracy": acc(bare_all),
        "labeled_item_accuracy": acc(labeled_all),
        "item_accuracy_difference": acc(labeled_all) - acc(bare_all),
        "bare_equal_cluster_accuracy": sum(bare_cluster_acc) / n,
        "labeled_equal_cluster_accuracy": sum(labeled_cluster_acc) / n,
        "equal_cluster_accuracy_difference": observed,
        "equal_cluster_accuracy_difference_95pct_bootstrap_ci": [
            percentile(boot_acc, 0.025), percentile(boot_acc, 0.975)
        ],
        "paired_cluster_sign_flip_p_two_sided": p_value,
        "permutations": args.permutations,
        "bootstrap_replicates": args.bootstrap,
        "macro_f1_bare_item_pooled": macro_f1(bare_all),
        "macro_f1_labeled_item_pooled": macro_f1(labeled_all),
        "macro_f1_difference_95pct_cluster_bootstrap_ci": [
            percentile(boot_f1, 0.025), percentile(boot_f1, 0.975)
        ],
        "seed": args.seed,
        "interpretation": (
            "Descriptive benchmark performance remains conditional on this "
            "deterministically constructed corpus. Cluster-aware inference "
            "addresses repeated items per provision; it does not establish "
            "human-annotated or natural-case legal correctness."
        ),
    }
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
