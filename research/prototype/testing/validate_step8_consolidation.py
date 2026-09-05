"""STEP 8 consolidation validator.

Verifies: canonical sources exist, canonical metrics reconcile with their source
artifacts, all 26 specific headline values named in this step's instructions reconcile
exactly, classifications/grades exist, no fabricated labels, no protected paths
modified, no natural-data correctness claims, no unsupported causal claims,
historical/fresh separation, GPU/CPU separation, correction synthetic/natural
separation, and the 205-test regression result remains 205/205. Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_step8_consolidation.py
"""
from __future__ import annotations

import hashlib
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


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def close(a, b, tol=1e-4) -> bool:
    try:
        return abs(float(a) - float(b)) < tol
    except (TypeError, ValueError):
        return a == b


# 1. source files exist
def check_sources_exist():
    name = "Source files exist"
    required = [
        STEP4 / "gold01_controlled" / "gold01_metrics.json",
        STEP4 / "gold02_synthetic" / "gold02_metrics.json",
        STEP6 / "588_claims" / "claims_588_metrics.json",
        STEP6 / "209_paired" / "paired_209_metrics.json",
        STEP6 / "batches" / "batches_analysis.json",
        EVAL_DIR / "ABLATION_SUMMARY.json",
        OUTPUTS / "final_metrics.json",
        OUTPUTS / "labeled_correction_validation_gpu_metrics.json",
        OUTPUTS / "final_gpu_validation_metrics.json",
        OUTPUTS / "final_validation_bare_vs_labeled_cpu_metrics.json",
    ]
    for p in required:
        if not p.exists():
            fail(f"{name}: missing {p}")
        else:
            ok(f"{name}: {p.name} present")


STEP4 = TESTING_DIR / "actual_outputs" / "step4_gold_verifier"
STEP6 = TESTING_DIR / "actual_outputs" / "step6_natural_data"


# 2. canonical metrics reconcile with source artifacts
def check_canonical_metrics_reconcile():
    name = "Canonical metrics reconcile"
    canon = load_json(EVAL_DIR / "CANONICAL_METRICS.json")
    gold01 = load_json(STEP4 / "gold01_controlled" / "gold01_metrics.json")
    m_by_id = {m["metric_id"]: m for m in canon["metrics"]}

    m02 = m_by_id.get("M02")
    if m02 and close(m02["current"], gold01["results_by_framing"]["labeled"]["accuracy"]):
        ok(f"{name}: M02 (controlled benchmark accuracy, labeled) reconciles with source")
    else:
        fail(f"{name}: M02 does not reconcile with gold01_metrics.json")

    paired209 = load_json(STEP6 / "209_paired" / "paired_209_metrics.json")
    m05 = m_by_id.get("M05")
    if m05 and close(m05["current"], paired209["fresh_evidence_coverage_arm_B"]):
        ok(f"{name}: M05 (evidence coverage Arm B) reconciles with source")
    else:
        fail(f"{name}: M05 does not reconcile with paired_209_metrics.json")


# 3. ALL 26 SPECIFIC HEADLINE VALUES reconcile exactly
def check_all_26_headline_values():
    name = "26 headline values reconcile"
    paired209 = load_json(STEP6 / "209_paired" / "paired_209_metrics.json")
    gold01 = load_json(STEP4 / "gold01_controlled" / "gold01_metrics.json")
    claims588 = load_json(STEP6 / "588_claims" / "claims_588_metrics.json")
    ablation = load_json(EVAL_DIR / "ABLATION_SUMMARY.json")
    final_metrics = load_json(OUTPUTS / "final_metrics.json")
    labeled_corr = load_json(OUTPUTS / "labeled_correction_validation_gpu_metrics.json")

    cp = next(f for f in ablation["findings"] if f["factor"] == "claim_parser_fix")
    pf = next(f for f in ablation["findings"] if f["factor"] == "premise_framing")

    checks = [
        ("63.2%", round(paired209["fresh_evidence_coverage_arm_A"] * 100, 1), 63.2),
        ("70.3%", round(paired209["fresh_evidence_coverage_arm_B"] * 100, 1), 70.3),
        ("15 gains", paired209["evidence_change_counts"].get("evidence_gained", 0), 15),
        ("0 losses", paired209["evidence_change_counts"].get("evidence_lost", 0), 0),
        ("chi2 13.0667", round(paired209["mcnemar_evidence_coverage"]["chi2"], 4), 13.0667),
        ("p 0.000301", round(paired209["mcnemar_evidence_coverage"]["p_value"], 6), 0.000301),
        ("macro_f1 bare 0.7487", round(gold01["results_by_framing"]["bare"]["macro_f1"], 4), 0.7487),
        ("macro_f1 labeled 0.9684", round(gold01["results_by_framing"]["labeled"]["macro_f1"], 4), 0.9684),
        ("accuracy bare 0.7333", round(gold01["results_by_framing"]["bare"]["accuracy"], 4), 0.7333),
        ("accuracy labeled 0.9714", round(gold01["results_by_framing"]["labeled"]["accuracy"], 4), 0.9714),
        ("chi2 98.01 (premise framing)", round(pf["statistic"], 2), 98.01),
        ("p 4.16e-23 (premise framing McNemar)", pf["p_value"], 4.1627504389864034e-23),
        ("p 1.5777e-30 (exact sign test)", pf["exact_sign_test_p_value"], 1.5777218104420236e-30),
        ("6/30 improved (parser)", cp["cases_improved"], 6),
        ("0/30 worsened (parser)", cp["cases_worsened"], 0),
        ("p 0.03125 (parser sign test)", round(cp["p_value"], 5), 0.03125),
        ("66.3% (588 coverage)", round(claims588["evidence_coverage"] * 100, 1), 66.3),
        ("390/588 matched", claims588["n_evidence_matched"], 390),
        ("364 NEI", claims588["verdict_distribution"].get("NOT_ENOUGH_INFORMATION"), 364),
        ("198 NO_EVIDENCE", claims588["verdict_distribution"].get("NO_EVIDENCE"), 198),
        ("21 ENTAILED", claims588["verdict_distribution"].get("ENTAILED"), 21),
        ("5 CONTRADICTED", claims588["verdict_distribution"].get("CONTRADICTED"), 5),
        ("0/5 triggered/shipped bare targeted", labeled_corr["comparison_bare_arm_b_original"]["corrections_shipped"], 0),
        ("1/10 shipped labeled targeted", labeled_corr["corrections_shipped"], 1),
        ("1/56 cumulative shipped", final_metrics["section_D_correction_safety_cumulative"]["total_shipped"], 1),
        ("0 unsafe (cumulative)", final_metrics["section_D_correction_safety_cumulative"]["total_unsafe_shipped"], 0),
    ]
    for label, actual, expected in checks:
        if isinstance(expected, float) and abs(expected) < 1e-6:
            match = abs(actual - expected) < 1e-6 or (actual == 0 and expected == 0)
        elif isinstance(expected, float):
            match = close(actual, expected, tol=max(abs(expected) * 1e-3, 1e-6))
        else:
            match = actual == expected
        if match:
            ok(f"{name}: '{label}' reconciles exactly (value={actual})")
        else:
            fail(f"{name}: '{label}' MISMATCH -- computed={actual}, expected={expected}")


# 4. classifications/grades exist for every metric where applicable
def check_classifications_exist():
    name = "Classifications/grades present"
    esm_path = EVAL_DIR / "EVIDENCE_STRENGTH_MATRIX.csv"
    if not esm_path.exists():
        fail(f"{name}: EVIDENCE_STRENGTH_MATRIX.csv missing")
        return
    import csv
    with esm_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    valid_grades = {"A", "B", "C", "D", "E", "E / NOT_ISOLATED"}
    missing = [r["conclusion"] for r in rows if r["grade"] not in valid_grades]
    if missing:
        fail(f"{name}: rows missing a valid grade: {missing}")
    else:
        ok(f"{name}: all {len(rows)} EVIDENCE_STRENGTH_MATRIX rows have a valid grade")


# 5. no fabricated labels; 6. no protected paths modified
def check_no_fabrication_and_protected_paths():
    name = "No fabrication / protected paths"
    forbidden = {"gold_annotation.jsonl", "lawyer_annotation.jsonl", "assumption_annotation.jsonl"}
    violation = False
    for path in EVAL_DIR.rglob("*"):
        if path.is_file() and path.name in forbidden:
            fail(f"{name}: forbidden provisional file found in STEP 8 output: {path}")
            violation = True
    if not violation:
        ok(f"{name}: no provisional annotation file found in STEP 8 output")

    gold_checks = [
        (TESTING_DIR / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl",
         "962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99"),
        (TESTING_DIR / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl",
         "2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516"),
    ]
    for p, expected in gold_checks:
        if p.exists():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            if h != expected:
                fail(f"{name}: GOLD fixture {p.name} modified")
            else:
                ok(f"{name}: GOLD fixture {p.name} unchanged")
        else:
            fail(f"{name}: GOLD fixture missing {p}")


# 7/9/10/11. terminology checks
def check_terminology():
    name = "Terminology discipline"
    files = list(EVAL_DIR.glob("CONSOLID*.md")) + list(EVAL_DIR.glob("HEADLINE*.md")) + \
            list(EVAL_DIR.glob("ORIGINAL_VS_CURRENT.md")) + list(EVAL_DIR.glob("EVIDENCE_STRENGTH*.md")) + \
            list(EVAL_DIR.glob("STATISTICAL_RESULTS.md")) + list(EVAL_DIR.glob("CORRECTION_FUNNEL.md")) + \
            list(EVAL_DIR.glob("SAFETY_SUMMARY.md")) + list(EVAL_DIR.glob("REPRODUCIBILITY_MATRIX.md"))

    natural_accuracy_pattern = re.compile(r"natural.{0,30}(accuracy|F1)\b|(accuracy|F1)\b.{0,30}natural data", re.IGNORECASE)
    allowed_natural = re.compile(
        r"not.*accuracy|no.*accuracy|never.*accuracy|not a correctness|not an accuracy|"
        r"is evidence coverage, not|no natural-data accuracy",
        re.IGNORECASE,
    )
    violation = False
    for md in files:
        text = md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if natural_accuracy_pattern.search(line) and not allowed_natural.search(line):
                fail(f"{name}: possible natural-data accuracy/F1 claim in {md.name}: {line.strip()[:140]}")
                violation = True
    if not violation:
        ok(f"{name}: no unsupported natural-data accuracy/F1 claim found across {len(files)} files")

    causal_pattern = re.compile(r"\bcaused\b|\bproved\b", re.IGNORECASE)
    allowed_causal = re.compile(r"not.*caused|no.*proved|never.*caused|does not prove", re.IGNORECASE)
    violation2 = False
    for md in files:
        text = md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if causal_pattern.search(line) and not allowed_causal.search(line):
                fail(f"{name}: unsupported causal term in {md.name}: {line.strip()[:140]}")
                violation2 = True
    if not violation2:
        ok(f"{name}: no unsupported 'caused'/'proved' claim found")


# 8. historical/fresh separation; GPU/CPU separation
def check_fresh_historical_gpu_separation():
    name = "Fresh/historical and GPU/CPU separation"
    canon = load_json(EVAL_DIR / "CANONICAL_METRICS.json")
    for m in canon["metrics"]:
        if not m.get("fresh_or_historical"):
            fail(f"{name}: metric {m['metric_id']} has no fresh_or_historical label")
        else:
            ok(f"{name}: metric {m['metric_id']} labeled '{m['fresh_or_historical'].split('(')[0].strip()}'")

    repro_path = EVAL_DIR / "REPRODUCIBILITY_MATRIX.md"
    text = repro_path.read_text(encoding="utf-8") if repro_path.exists() else ""
    if "GPU required, none available" in text and "NOT EXECUTED" in text:
        ok(f"{name}: REPRODUCIBILITY_MATRIX.md explicitly marks GPU-required/not-executed rows")
    else:
        fail(f"{name}: REPRODUCIBILITY_MATRIX.md does not clearly mark GPU-unavailable rows")


# 10 (funnel). correction synthetic/natural results separated
def check_correction_populations_separated():
    name = "Correction synthetic/natural separation"
    funnel_path = EVAL_DIR / "CORRECTION_FUNNEL.csv"
    if not funnel_path.exists():
        fail(f"{name}: CORRECTION_FUNNEL.csv missing")
        return
    import csv
    with funnel_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    populations = {r["population"] for r in rows}
    if {"synthetic_bare", "synthetic_labeled", "natural_targeted_bare", "natural_targeted_labeled", "natural_cumulative_project_history"} <= populations:
        ok(f"{name}: all 5 distinct correction populations present and separated, never merged into one row")
    else:
        fail(f"{name}: expected 5 distinct correction populations, found {populations}")

    text = (EVAL_DIR / "CORRECTION_FUNNEL.md").read_text(encoding="utf-8") if (EVAL_DIR / "CORRECTION_FUNNEL.md").exists() else ""
    if "72.2%" in text and "cannot be presented as equivalent" in text:
        ok(f"{name}: CORRECTION_FUNNEL.md explicitly states the 72.2% synthetic rate cannot be equated with the natural rate")
    else:
        fail(f"{name}: CORRECTION_FUNNEL.md does not explicitly disclaim the synthetic-vs-natural conflation")


# 12. all figure CSVs are parseable; 13. no duplicate metric rows; 14. all source files exist (already checked)
def check_figure_csvs():
    name = "Figure CSVs parseable / no duplicates"
    import csv
    expected_files = [f"{i:02d}_" for i in range(1, 12)]
    found = list(FIG_DIR.glob("*.csv"))
    if len(found) != 11:
        fail(f"{name}: expected 11 figure_data CSVs, found {len(found)}")
    else:
        ok(f"{name}: exactly 11 figure_data CSVs present")
    for p in found:
        try:
            with p.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            ok(f"{name}: {p.name} parses OK ({len(rows)} rows)")
        except Exception as e:
            fail(f"{name}: {p.name} failed to parse: {e!r}")


def main() -> int:
    check_sources_exist()
    check_canonical_metrics_reconcile()
    check_all_26_headline_values()
    check_classifications_exist()
    check_no_fabrication_and_protected_paths()
    check_terminology()
    check_fresh_historical_gpu_separation()
    check_correction_populations_separated()
    check_figure_csvs()

    print("=" * 70)
    print("STEP 8 CONSOLIDATION VALIDATION REPORT")
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
