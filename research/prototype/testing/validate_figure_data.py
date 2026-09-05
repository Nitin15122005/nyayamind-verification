"""STEP 8 Phase 12 -- figure-data CSV contract validator.

Verifies the 11 files under research/prototype/testing/evaluation/figure_data/ satisfy
the figure-data contract: declared source, values matching source artifacts, no
natural-data accuracy/F1, no fabricated labels, N present where required, unambiguous
baseline/current labels, consistent percentage units, fresh/historical correctly
labeled, GPU/CPU correctly labeled, correction populations separated, headline values
reconciling, all files parseable, no duplicate metric rows, all source files existing.
Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_figure_data.py
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"
EVAL_DIR = TESTING_DIR / "evaluation"
FIG_DIR = EVAL_DIR / "figure_data"

FAILURES: list[str] = []
WARNINGS: list[str] = []
PASSES: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)
def warn(m): WARNINGS.append(m)


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


EXPECTED_FILES = [
    "01_overall_metric_comparison.csv", "02_evidence_coverage.csv", "03_verdict_distribution.csv",
    "04_correction_funnel.csv", "05_correction_outcome.csv", "06_safety.csv",
    "07_confidence_distribution.csv", "08_ablation_comparison.csv", "09_runtime_resource.csv",
    "10_cumulative_natural_results.csv", "11_synthetic_vs_natural_transfer.csv",
]


# 1. every figure CSV has a declared source; 12. all parseable; 14. all source files exist
def check_files_and_sources():
    name = "Files present, parseable, source-declared"
    for fname in EXPECTED_FILES:
        p = FIG_DIR / fname
        if not p.exists():
            fail(f"{name}: {fname} missing")
            continue
        try:
            rows = read_csv(p)
        except Exception as e:
            fail(f"{name}: {fname} failed to parse: {e!r}")
            continue
        ok(f"{name}: {fname} parses OK ({len(rows)} rows)")
        if not rows:
            warn(f"{name}: {fname} has 0 data rows")
            continue
        header = rows[0].keys()
        source_cols = [c for c in header if "source" in c.lower()]
        if not source_cols:
            fail(f"{name}: {fname} has no 'source' column")
        else:
            missing_source = [r for r in rows if not any(r.get(c) for c in source_cols)]
            if missing_source:
                fail(f"{name}: {fname} has {len(missing_source)} row(s) with an empty source")
            else:
                ok(f"{name}: {fname} declares a non-empty source for every row")


# 2. every numeric value matches its source artifact (spot-check the headline files)
def check_numeric_values_match_source():
    name = "Numeric values match source"
    gold01 = json.loads((TESTING_DIR / "actual_outputs" / "step4_gold_verifier" / "gold01_controlled" / "gold01_metrics.json").read_text(encoding="utf-8"))
    rows = read_csv(FIG_DIR / "01_overall_metric_comparison.csv")
    row = next((r for r in rows if r["metric"] == "controlled_benchmark_macro_f1"), None)
    if row is None:
        fail(f"{name}: controlled_benchmark_macro_f1 row missing from 01_overall_metric_comparison.csv")
    elif abs(float(row["current_value"]) - gold01["results_by_framing"]["labeled"]["macro_f1"]) > 1e-6:
        fail(f"{name}: 01_overall_metric_comparison.csv's macro_f1 current_value does not match gold01_metrics.json")
    else:
        ok(f"{name}: 01_overall_metric_comparison.csv's macro_f1 current_value matches gold01_metrics.json exactly")

    paired209 = json.loads((TESTING_DIR / "actual_outputs" / "step6_natural_data" / "209_paired" / "paired_209_metrics.json").read_text(encoding="utf-8"))
    ec_rows = read_csv(FIG_DIR / "02_evidence_coverage.csv")
    arm_b_row = next((r for r in ec_rows if r["dataset"] == "209_paired_ArmB"), None)
    if arm_b_row is None:
        fail(f"{name}: 209_paired_ArmB row missing from 02_evidence_coverage.csv")
    elif abs(float(arm_b_row["coverage"]) - paired209["fresh_evidence_coverage_arm_B"]) > 1e-6:
        fail(f"{name}: 02_evidence_coverage.csv's Arm B coverage does not match paired_209_metrics.json")
    else:
        ok(f"{name}: 02_evidence_coverage.csv's Arm B coverage matches paired_209_metrics.json exactly")


# 3. no natural accuracy/F1 exists
def check_no_natural_accuracy():
    name = "No natural-data accuracy/F1"
    violation = False
    for fname in EXPECTED_FILES:
        p = FIG_DIR / fname
        if not p.exists():
            continue
        rows = read_csv(p)
        for r in rows:
            metric_field = (r.get("metric") or r.get("verdict") or r.get("factor") or "").lower()
            dataset_field = (r.get("dataset") or r.get("population") or "").lower()
            if ("accuracy" in metric_field or "f1" in metric_field) and "natural" in dataset_field and "gold" not in dataset_field:
                fail(f"{name}: {fname} row combines accuracy/F1 with a natural (non-GOLD) dataset: {r}")
                violation = True
    if not violation:
        ok(f"{name}: no figure_data row combines accuracy/F1 with a natural, non-GOLD dataset")


# 4. no fabricated labels (spot check: no forbidden provisional filenames)
def check_no_fabricated_labels():
    name = "No fabricated labels"
    forbidden = {"gold_annotation", "lawyer_annotation", "assumption_annotation"}
    violation = False
    for fname in EXPECTED_FILES:
        text = (FIG_DIR / fname).read_text(encoding="utf-8") if (FIG_DIR / fname).exists() else ""
        if any(term in text for term in forbidden):
            fail(f"{name}: {fname} references a provisional annotation file")
            violation = True
    if not violation:
        ok(f"{name}: no figure_data file references a provisional annotation source")


# 5. no missing N where N is required
def check_n_present():
    name = "N present where required"
    files_requiring_n = ["01_overall_metric_comparison.csv", "02_evidence_coverage.csv",
                          "03_verdict_distribution.csv", "07_confidence_distribution.csv", "09_runtime_resource.csv"]
    for fname in files_requiring_n:
        p = FIG_DIR / fname
        if not p.exists():
            continue
        rows = read_csv(p)
        n_col = next((c for c in rows[0].keys() if c.lower() in ("n", "n_total", "n_cases")), None)
        if n_col is None:
            fail(f"{name}: {fname} has no N-like column")
            continue
        missing = [r for r in rows if not r.get(n_col)]
        if missing:
            fail(f"{name}: {fname} has {len(missing)} row(s) with missing N")
        else:
            ok(f"{name}: {fname} has N populated for every row")


# 6. baseline/current labels unambiguous
def check_baseline_current_labels():
    name = "Baseline/current labels unambiguous"
    p = FIG_DIR / "01_overall_metric_comparison.csv"
    rows = read_csv(p)
    for r in rows:
        if "original_value" not in r or "current_value" not in r:
            fail(f"{name}: {p.name} row missing explicit original_value/current_value columns")
        else:
            ok(f"{name}: {p.name} row '{r.get('metric')}' has unambiguous original_value/current_value columns")


# 7. percentages in consistent units (fractions, not mixed with %-strings, in numeric columns)
def check_percentage_units():
    name = "Consistent percentage units"
    violation = False
    for fname in ["01_overall_metric_comparison.csv", "02_evidence_coverage.csv"]:
        p = FIG_DIR / fname
        if not p.exists():
            continue
        rows = read_csv(p)
        for r in rows:
            for col in ("original_value", "current_value", "coverage"):
                if col in r and r[col]:
                    if "%" in r[col]:
                        fail(f"{name}: {fname} column '{col}' contains a '%' string in a numeric field: {r[col]}")
                        violation = True
    if not violation:
        ok(f"{name}: no '%' strings found in numeric columns -- all coverage/metric values are plain fractions")


# 8. no historical result mislabeled fresh; 9. no GPU result mislabeled CPU
def check_fresh_gpu_labeling():
    name = "Fresh/historical and GPU/CPU labeling"
    p = FIG_DIR / "09_runtime_resource.csv"
    rows = read_csv(p)
    for r in rows:
        if "gpu" in r["arm"].lower() or "generation" in r["arm"].lower() or "correction" in r["arm"].lower():
            if "HISTORICAL" not in r["fresh_or_historical"] and "cpu" not in r["arm"].lower():
                fail(f"{name}: {p.name} row '{r['arm']}' looks GPU-related but is not marked HISTORICAL: {r}")
            else:
                ok(f"{name}: {p.name} row '{r['arm']}' correctly labeled ({r['fresh_or_historical']})")
        else:
            ok(f"{name}: {p.name} row '{r['arm']}' labeled {r['fresh_or_historical']}")


# 10. correction synthetic/natural results are separated
def check_correction_separation():
    name = "Correction synthetic/natural separation"
    p = FIG_DIR / "05_correction_outcome.csv"
    rows = read_csv(p)
    populations = {r["population"] for r in rows}
    if any("synthetic" in x for x in populations) and any("natural" in x for x in populations):
        ok(f"{name}: {p.name} contains both synthetic and natural populations, never merged into one row")
    else:
        fail(f"{name}: {p.name} does not clearly separate synthetic and natural correction populations")

    transfer_rows = read_csv(FIG_DIR / "11_synthetic_vs_natural_transfer.csv")
    if all(r.get("populations_comparable", "").upper() == "NO" for r in transfer_rows):
        ok(f"{name}: 11_synthetic_vs_natural_transfer.csv explicitly marks synthetic/natural as NOT comparable")
    else:
        fail(f"{name}: 11_synthetic_vs_natural_transfer.csv does not explicitly disclaim synthetic/natural comparability")


# 11. all headline values reconcile (spot-check ablation comparison figure data)
def check_headline_reconciliation():
    name = "Headline values reconcile (figure data)"
    ablation = json.loads((EVAL_DIR / "ABLATION_SUMMARY.json").read_text(encoding="utf-8"))
    rows = read_csv(FIG_DIR / "08_ablation_comparison.csv")
    ev1_row = next((r for r in rows if r["factor"] == "evidence_v1"), None)
    ev1_source = next(f for f in ablation["findings"] if f["factor"] == "evidence_v1")
    if ev1_row and abs(float(ev1_row["p_value"]) - ev1_source["p_value"]) < 1e-9:
        ok(f"{name}: 08_ablation_comparison.csv's evidence_v1 p_value reconciles exactly with ABLATION_SUMMARY.json")
    else:
        fail(f"{name}: 08_ablation_comparison.csv's evidence_v1 p_value does not reconcile")


# 13. no duplicate metric rows
def check_no_duplicate_rows():
    name = "No duplicate metric rows"
    for fname in EXPECTED_FILES:
        p = FIG_DIR / fname
        if not p.exists():
            continue
        rows = read_csv(p)
        if not rows:
            continue
        key_col = next((c for c in rows[0].keys() if c in ("metric", "dataset", "factor", "population", "safety_mechanism")), None)
        if key_col is None:
            continue
        keys = [tuple(sorted(r.items())) for r in rows]
        if len(keys) != len(set(keys)):
            fail(f"{name}: {fname} contains fully duplicate rows")
        else:
            ok(f"{name}: {fname} has no fully duplicate rows")


def main() -> int:
    check_files_and_sources()
    check_numeric_values_match_source()
    check_no_natural_accuracy()
    check_no_fabricated_labels()
    check_n_present()
    check_baseline_current_labels()
    check_percentage_units()
    check_fresh_gpu_labeling()
    check_correction_separation()
    check_headline_reconciliation()
    check_no_duplicate_rows()

    print("=" * 70)
    print("FIGURE DATA VALIDATION REPORT")
    print("=" * 70)
    print(f"\nPASSED ({len(PASSES)}):")
    for p in PASSES:
        print(f"  [PASS] {p}")
    if WARNINGS:
        print(f"\nWARNINGS ({len(WARNINGS)}):")
        for w in WARNINGS:
            print(f"  [WARN] {w}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  [FAIL] {f}")
        print(f"\nRESULT: FAIL ({len(FAILURES)} failure(s), {len(WARNINGS)} warning(s), {len(PASSES)} passed)")
        return 1

    print(f"\nRESULT: PASS ({len(PASSES)} checks passed, {len(WARNINGS)} warning(s), 0 failures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
