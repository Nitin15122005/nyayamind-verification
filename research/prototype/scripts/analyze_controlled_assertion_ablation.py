#!/usr/bin/env python3
"""Paired, CPU-only analysis of controlled assertion-aware correction runs.

This script consumes the metrics and correction-detail artifacts written by
run_controlled_assertion_ablation_gpu.py. It verifies paired case coverage,
arm-setting parity, token-budget parity, and the metrics/detail join before
reporting an exact two-sided McNemar/binomial test for the discordant
correction outcomes. It does not assess legal correctness.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected a JSON object")
        rows.append(row)
    return rows


def exact_binomial_two_sided_p(successes_a: int, successes_b: int) -> float:
    """Exact two-sided binomial p-value for discordant paired outcomes."""
    discordant = successes_a + successes_b
    if discordant == 0:
        return 1.0
    tail = min(successes_a, successes_b)
    probability = sum(math.comb(discordant, k) for k in range(tail + 1)) / (2 ** discordant)
    return min(1.0, 2.0 * probability)


def analyze(metrics: dict, details: list[dict]) -> dict:
    errors: list[str] = []
    arms = ("A", "B")
    by_arm: dict[str, dict[str, dict]] = {arm: {} for arm in arms}

    for row in details:
        arm = row.get("arm")
        doc_id = row.get("document_id")
        if arm not in arms:
            errors.append(f"Unexpected arm in details: {arm!r}")
            continue
        if not doc_id:
            errors.append(f"Missing document_id in arm {arm} detail row")
            continue
        if doc_id in by_arm[arm]:
            errors.append(f"Duplicate correction detail for arm {arm}, document {doc_id}")
            continue
        by_arm[arm][doc_id] = row

    if set(by_arm["A"]) != set(by_arm["B"]):
        errors.append(
            "Correction-triggered document sets differ: "
            f"A-only={sorted(set(by_arm['A']) - set(by_arm['B']))}, "
            f"B-only={sorted(set(by_arm['B']) - set(by_arm['A']))}"
        )

    arm_metrics = metrics.get("per_arm", {})
    for arm in arms:
        expected = arm_metrics.get(arm, {})
        observed_statuses = Counter(row.get("status") for row in by_arm[arm].values())
        if dict(observed_statuses) != expected.get("correction_statuses", {}):
            errors.append(f"Arm {arm} status counts disagree with metrics")
        if len(by_arm[arm]) != expected.get("correction_attempts"):
            errors.append(f"Arm {arm} attempt count disagrees with metrics")
        shipped = sum(row.get("status") == "corrected" for row in by_arm[arm].values())
        if shipped != expected.get("corrections_shipped_success"):
            errors.append(f"Arm {arm} shipped count disagrees with metrics")

    # The two arms must share all recorded settings except the treatment flag.
    defs = metrics.get("arm_definitions", {})
    a_def, b_def = defs.get("A", {}), defs.get("B", {})
    comparable_keys = (
        "use_evidence_v1", "premise_framing", "atomic_scope_check",
        "narrow_reverification_hypothesis", "confidence_threshold",
        "narrow_primary_hypothesis", "assertion_span_primary_hypothesis",
        "correction_max_new_tokens", "evidence_pool_size",
    )
    for key in comparable_keys:
        if a_def.get(key) != b_def.get(key):
            errors.append(f"Arm configuration mismatch for {key}: A={a_def.get(key)!r}, B={b_def.get(key)!r}")
    if a_def.get("assertion_aware_correction") is not False:
        errors.append("Arm A must declare assertion_aware_correction=false")
    if b_def.get("assertion_aware_correction") is not True:
        errors.append("Arm B must declare assertion_aware_correction=true")

    budgets = {
        arm: {(row.get("corr_meta") or {}).get("max_new_tokens") for row in by_arm[arm].values()}
        for arm in arms
    }
    if budgets["A"] != budgets["B"]:
        errors.append(f"Correction token budgets differ: A={budgets['A']}, B={budgets['B']}")
    if None in budgets["A"] or None in budgets["B"]:
        errors.append("At least one correction detail row has no recorded token budget")

    paired_docs = sorted(set(by_arm["A"]) & set(by_arm["B"]))
    both = a_only = b_only = neither = 0
    pair_rows = []
    for doc_id in paired_docs:
        a_ok = by_arm["A"][doc_id].get("status") == "corrected"
        b_ok = by_arm["B"][doc_id].get("status") == "corrected"
        if a_ok and b_ok:
            both += 1
        elif a_ok:
            a_only += 1
        elif b_ok:
            b_only += 1
        else:
            neither += 1
        pair_rows.append({
            "document_id": doc_id,
            "arm_a_status": by_arm["A"][doc_id].get("status"),
            "arm_b_status": by_arm["B"][doc_id].get("status"),
            "arm_a_shipped": a_ok,
            "arm_b_shipped": b_ok,
        })

    p_value = exact_binomial_two_sided_p(a_only, b_only)
    return {
        "experiment": metrics.get("experiment"),
        "n_paired_correction_attempts": len(paired_docs),
        "paired_outcomes": {
            "both_shipped": both,
            "arm_a_only_shipped": a_only,
            "arm_b_only_shipped": b_only,
            "neither_shipped": neither,
        },
        "exact_mcnemar_two_sided_p": p_value,
        "correction_token_budgets": {arm: sorted(budgets[arm], key=str) for arm in arms},
        "paired_cases": pair_rows,
        "integrity_errors": errors,
        "interpretation": (
            "Descriptive pilot result only. This exact paired test does not establish legal correctness "
            "or generalization; correction-triggered sample size and external adjudication remain limiting."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--details", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    result = analyze(metrics, load_jsonl(args.details))
    print(json.dumps(result, indent=2))
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    if result["integrity_errors"]:
        return 1
    print(
        "NOTE: Exact paired test is descriptive; p="
        f"{result['exact_mcnemar_two_sided_p']:.6g}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
