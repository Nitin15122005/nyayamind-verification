#!/usr/bin/env python3
"""CPU-only integrity audit for run_final_gpu_validation.py outputs.

This script does not load models or make legal judgments. It checks that the
metrics JSON agrees with the correction-detail JSONL and reports experimental
confounds visible in the recorded metadata.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--details", type=Path, required=True)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    details = load_jsonl(args.details)
    errors: list[str] = []
    print(f"Experiment: {metrics.get('experiment')}")
    print(f"Correction detail rows: {len(details)}")

    for arm in ("A", "B"):
        arm_rows = [row for row in details if row.get("arm") == arm]
        observed = Counter(row.get("status") for row in arm_rows)
        expected = metrics["per_arm"][arm]
        expected_statuses = expected.get("correction_statuses", {})
        observed_attempts = len(arm_rows)
        if dict(observed) != expected_statuses:
            errors.append(
                f"Arm {arm}: detail statuses {dict(observed)} != metrics {expected_statuses}"
            )
        if observed_attempts != expected.get("correction_attempts"):
            errors.append(
                f"Arm {arm}: {observed_attempts} detail rows != "
                f"{expected.get('correction_attempts')} correction attempts"
            )
        shipped = sum(row.get("status") == "corrected" for row in arm_rows)
        if shipped != expected.get("corrections_shipped_success"):
            errors.append(f"Arm {arm}: shipped count disagrees with detail rows")
        unsafe = sum(
            row.get("status") == "corrected"
            and (row.get("reverification") or {}).get("verdict") != "ENTAILED"
            for row in arm_rows
        )
        if unsafe != expected.get("unsafe_corrections_shipped"):
            errors.append(f"Arm {arm}: unsafe-shipped count disagrees with detail rows")

        budgets = sorted({
            (row.get("corr_meta") or {}).get("max_new_tokens")
            for row in arm_rows
        }, key=lambda value: (value is None, value or 0))
        print(
            f"Arm {arm}: attempts={observed_attempts}, statuses={dict(observed)}, "
            f"shipped={shipped}, correction_token_budgets={budgets}"
        )

    budgets_by_arm = {
        arm: {
            (row.get("corr_meta") or {}).get("max_new_tokens")
            for row in details if row.get("arm") == arm
        }
        for arm in ("A", "B")
    }
    if budgets_by_arm["A"] != budgets_by_arm["B"]:
        print(
            "CONFOUND: correction token budgets differ by arm: "
            f"A={sorted(budgets_by_arm['A'], key=str)}, "
            f"B={sorted(budgets_by_arm['B'], key=str)}"
        )

    for arm in ("A", "B"):
        for row in (r for r in details if r.get("arm") == arm):
            rv = row.get("reverification") or {}
            if row.get("status") == "correction_failed" and rv.get("verdict") == "NOT_ENOUGH_INFORMATION":
                print(
                    f"REVIEW: {arm}/{row.get('document_id')} failed re-verification "
                    f"with NEI confidence={rv.get('confidence')}; confidence is for "
                    "the NEI class, not support for the claim."
                )
            if row.get("status") == "correction_unauthorized_addition":
                print(f"REVIEW: {arm}/{row.get('document_id')} rejected for unauthorized addition.")
            if row.get("status") == "correction_scope_violation":
                print(f"REVIEW: {arm}/{row.get('document_id')} rejected for scope violation.")

    if errors:
        print("AUDIT FAILED:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("AUDIT PASSED: metrics and correction-detail counts are internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
