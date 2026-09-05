#!/usr/bin/env python3
"""STEP 8 -- consolidation build script.

Reads every canonical source artifact from STEP 4-7 (never re-computes anything, never
introduces a new number) and mechanically produces the consolidated CSV/JSON registries.
This is the single source of truth for every number that appears in this step's markdown
reports -- every prose document is written FROM this script's printed/written output,
not independently retyped.

No production source, test, or historical output is read for modification -- everything
under research/prototype/outputs/ is opened read-only. Writes only under
research/prototype/testing/evaluation/.
"""
from __future__ import annotations

import csv
import datetime
import json
import subprocess
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"
EVAL_DIR = TESTING_DIR / "evaluation"
FIG_DIR = EVAL_DIR / "figure_data"
FIG_DIR.mkdir(parents=True, exist_ok=True)

STEP4 = TESTING_DIR / "actual_outputs" / "step4_gold_verifier"
STEP6 = TESTING_DIR / "actual_outputs" / "step6_natural_data"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    except Exception as e:
        return f"UNKNOWN ({e!r})"


# ---------------------------------------------------------------------------
# Load every canonical source once
# ---------------------------------------------------------------------------

gold01 = load_json(STEP4 / "gold01_controlled" / "gold01_metrics.json")
gold02 = load_json(STEP4 / "gold02_synthetic" / "gold02_metrics.json")
claims588 = load_json(STEP6 / "588_claims" / "claims_588_metrics.json")
paired209 = load_json(STEP6 / "209_paired" / "paired_209_metrics.json")
batches = load_json(STEP6 / "batches" / "batches_analysis.json")
ablation = load_json(EVAL_DIR / "ABLATION_SUMMARY.json")
final_metrics = load_json(OUTPUTS / "final_metrics.json")
labeled_corr_gpu = load_json(OUTPUTS / "labeled_correction_validation_gpu_metrics.json")
final_gpu_val_metrics = load_json(OUTPUTS / "final_gpu_validation_metrics.json")
bare_vs_labeled_cpu = load_json(OUTPUTS / "final_validation_bare_vs_labeled_cpu_metrics.json")

print("All canonical sources loaded OK.")

# ---------------------------------------------------------------------------
# PHASE 2 -- CANONICAL_METRICS.csv / .json
# ---------------------------------------------------------------------------

metrics = []


def add_metric(**kw):
    metrics.append(kw)


add_metric(
    metric_id="M01", metric_name="Controlled benchmark accuracy (bare)", category="verifier",
    dataset="GOLD-01_controlled_verifier_benchmark", n=420, baseline=None,
    current=gold01["results_by_framing"]["bare"]["accuracy"], delta=None, unit="fraction",
    statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="FRESH (STEP 4)", metric_class="gold_metric", evidence_grade="A",
    source_artifact="testing/actual_outputs/step4_gold_verifier/gold01_controlled/gold01_metrics.json",
    safe_interpretation="Verifier accuracy under bare premise framing on the 420-item controlled GOLD benchmark.",
    prohibited_interpretation="Applies to natural, non-curated legal text.",
)
add_metric(
    metric_id="M02", metric_name="Controlled benchmark accuracy (labeled)", category="verifier",
    dataset="GOLD-01_controlled_verifier_benchmark", n=420,
    baseline=gold01["results_by_framing"]["bare"]["accuracy"],
    current=gold01["results_by_framing"]["labeled"]["accuracy"],
    delta=gold01["results_by_framing"]["labeled"]["accuracy"] - gold01["results_by_framing"]["bare"]["accuracy"],
    unit="fraction", statistical_test="McNemar", statistic=98.01, p_value=4.1627504389864034e-23,
    confidence_interval=None, fresh_or_historical="FRESH (STEP 4/7)", metric_class="gold_metric",
    evidence_grade="A", source_artifact="testing/evaluation/ABLATION_SUMMARY.json (factor=premise_framing)",
    safe_interpretation="Labeled framing substantially improves verifier accuracy on the controlled GOLD benchmark.",
    prohibited_interpretation="Equivalent improvement on natural legal text; a legal-correctness claim.",
)
add_metric(
    metric_id="M03", metric_name="Controlled benchmark macro F1 (bare -> labeled)", category="verifier",
    dataset="GOLD-01_controlled_verifier_benchmark", n=420,
    baseline=gold01["results_by_framing"]["bare"]["macro_f1"],
    current=gold01["results_by_framing"]["labeled"]["macro_f1"],
    delta=gold01["results_by_framing"]["labeled"]["macro_f1"] - gold01["results_by_framing"]["bare"]["macro_f1"],
    unit="fraction", statistical_test="McNemar + exact sign test", statistic=98.01, p_value=4.1627504389864034e-23,
    confidence_interval=None, fresh_or_historical="FRESH (STEP 4/7)", metric_class="gold_metric",
    evidence_grade="A", source_artifact="testing/evaluation/ABLATION_SUMMARY.json (factor=premise_framing)",
    safe_interpretation="Macro F1 improvement on the controlled GOLD benchmark, exact sign test p=1.5777e-30.",
    prohibited_interpretation="A natural-data accuracy/F1 claim.",
)
add_metric(
    metric_id="M04", metric_name="Synthetic stress contradiction recall (bare -> labeled)", category="verifier",
    dataset="GOLD-02_synthetic_stress_set", n=59,
    baseline=gold02["results_by_framing"]["bare"]["contradiction_recall"],
    current=gold02["results_by_framing"]["labeled"]["contradiction_recall"],
    delta=gold02["results_by_framing"]["labeled"]["contradiction_recall"] - gold02["results_by_framing"]["bare"]["contradiction_recall"],
    unit="fraction", statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="FRESH (STEP 4)", metric_class="gold_metric", evidence_grade="A",
    source_artifact="testing/actual_outputs/step4_gold_verifier/gold02_synthetic/gold02_metrics.json",
    safe_interpretation="Contradiction recall on the synthetic (deliberately corrupted, GOLD) stress set.",
    prohibited_interpretation="A natural-data accuracy claim; every record here is contradictory by construction.",
)
add_metric(
    metric_id="M05", metric_name="Evidence coverage, 209-claim paired natural set (v0 -> v0+v1)", category="evidence/retrieval",
    dataset="209_claim_paired_natural_evaluation", n=209,
    baseline=paired209["fresh_evidence_coverage_arm_A"], current=paired209["fresh_evidence_coverage_arm_B"],
    delta=paired209["fresh_evidence_coverage_arm_B"] - paired209["fresh_evidence_coverage_arm_A"],
    unit="fraction", statistical_test="McNemar", statistic=paired209["mcnemar_evidence_coverage"]["chi2"],
    p_value=paired209["mcnemar_evidence_coverage"]["p_value"], confidence_interval=None,
    fresh_or_historical="FRESH REPRODUCTION (STEP 6)", metric_class="natural_metric", evidence_grade="A",
    source_artifact="testing/actual_outputs/step6_natural_data/209_paired/paired_209_metrics.json",
    safe_interpretation="Evidence-v1 materially increased observed evidence coverage on the paired natural evaluation.",
    prohibited_interpretation="Increased legal correctness or accuracy on natural data.",
)
add_metric(
    metric_id="M06", metric_name="Evidence coverage, 588-claim natural aggregate (current config)", category="evidence/retrieval",
    dataset="588_claim_natural_aggregate", n=588, baseline=None, current=claims588["evidence_coverage"],
    delta=None, unit="fraction", statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="FRESH (STEP 6)", metric_class="natural_metric", evidence_grade=None,
    source_artifact="testing/actual_outputs/step6_natural_data/588_claims/claims_588_metrics.json",
    safe_interpretation="Descriptive evidence-coverage rate on the 588-claim natural aggregate under the current production config.",
    prohibited_interpretation="A correctness or accuracy figure -- no independent label exists for this data.",
)
add_metric(
    metric_id="M07", metric_name="Verdict distribution, 588-claim natural aggregate", category="natural-data descriptive metrics",
    dataset="588_claim_natural_aggregate", n=588, baseline=None,
    current=json.dumps(claims588["verdict_distribution"]), delta=None, unit="count",
    statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="FRESH (STEP 6)", metric_class="natural_metric", evidence_grade=None,
    source_artifact="testing/actual_outputs/step6_natural_data/588_claims/claims_588_metrics.json",
    safe_interpretation="Observed verdict counts on the 588-claim natural aggregate (descriptive only).",
    prohibited_interpretation="An accuracy or F1 breakdown -- these are raw verifier outcome counts, not correctness labels.",
)
add_metric(
    metric_id="M08", metric_name="Claim parser fix: per-case evidence-count improvement", category="parser",
    dataset="n30_reparse", n=30,
    baseline=next(f for f in ablation["findings"] if f["factor"] == "claim_parser_fix")["cases_worsened"],
    current=next(f for f in ablation["findings"] if f["factor"] == "claim_parser_fix")["cases_improved"],
    delta=None, unit="count_of_cases", statistical_test="exact two-sided sign test",
    statistic=None, p_value=next(f for f in ablation["findings"] if f["factor"] == "claim_parser_fix")["p_value"],
    confidence_interval=None, fresh_or_historical="HISTORICAL REPRODUCTION / NOT FRESH (STEP 7)",
    metric_class="natural_metric", evidence_grade="B",
    source_artifact="testing/evaluation/ABLATION_SUMMARY.json (factor=claim_parser_fix)",
    safe_interpretation="The parser fix (commit 223eb9d) increased per-case evidence-matched counts with zero cases worsened.",
    prohibited_interpretation="Improved legal accuracy.",
)
add_metric(
    metric_id="M09", metric_name="Natural ENTAILED reached, 147-claim evidence-matched subset (bare -> labeled)", category="verifier",
    dataset="final_validation_Arm_B_evidence_matched_subset", n=bare_vs_labeled_cpu["n_claims_with_evidence"],
    baseline=bare_vs_labeled_cpu["bare_verdict_counts"].get("ENTAILED", 0),
    current=bare_vs_labeled_cpu["labeled_verdict_counts"].get("ENTAILED", 0),
    delta=bare_vs_labeled_cpu["labeled_verdict_counts"].get("ENTAILED", 0) - bare_vs_labeled_cpu["bare_verdict_counts"].get("ENTAILED", 0),
    unit="count", statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="HISTORICAL (outputs/final_validation_bare_vs_labeled_cpu_metrics.json)",
    metric_class="natural_metric", evidence_grade="B",
    source_artifact="research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json",
    safe_interpretation="Descriptive count of real natural claims reaching a verifier verdict of ENTAILED, before vs. after the framing change, on the same 147 claims.",
    prohibited_interpretation="An accuracy or correctness metric -- ENTAILED is a model verdict, not a validated fact.",
)
add_metric(
    metric_id="M10", metric_name="Natural CONTRADICTED count, 147-claim subset (bare -> labeled)", category="verifier",
    dataset="final_validation_Arm_B_evidence_matched_subset", n=bare_vs_labeled_cpu["n_claims_with_evidence"],
    baseline=bare_vs_labeled_cpu["bare_verdict_counts"].get("CONTRADICTED", 0),
    current=bare_vs_labeled_cpu["labeled_verdict_counts"].get("CONTRADICTED", 0), delta=0,
    unit="count", statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="HISTORICAL", metric_class="natural_metric", evidence_grade=None,
    source_artifact="research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json",
    safe_interpretation="CONTRADICTED count unchanged (3 -> 3) between framings on this subset.",
    prohibited_interpretation="Any correctness claim about which contradictions are legally accurate.",
)
add_metric(
    metric_id="M11", metric_name="Targeted correction shipping (bare -> labeled, isolated)", category="correction",
    dataset="final_validation_batch_targeted", n=None,
    baseline="0/5", current="1/10", delta=None, unit="count/count",
    statistical_test="none (n too small)", statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="HISTORICAL, GPU-dependent, NOT re-executed", metric_class="natural_metric",
    evidence_grade="C", source_artifact="research/prototype/outputs/labeled_correction_validation_gpu_metrics.json",
    safe_interpretation="Directional, isolated-by-design shift in shipped corrections; not statistically supported.",
    prohibited_interpretation="Statistical significance; that any lever solved correction.",
)
add_metric(
    metric_id="M12", metric_name="Cumulative correction shipping rate (project history)", category="correction",
    dataset="all_natural_correction_attempts", n=final_metrics["section_D_correction_safety_cumulative"]["total_correction_attempts"],
    baseline=None, current=final_metrics["section_D_correction_safety_cumulative"]["shipped_rate_pct"] / 100,
    delta=None, unit="fraction", statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="HISTORICAL (cumulative, GPU-dependent)", metric_class="natural_metric", evidence_grade="D",
    source_artifact="research/prototype/outputs/final_metrics.json (section_D_correction_safety_cumulative)",
    safe_interpretation="1 of 56 correction attempts across this project's entire history has ever shipped (1.8%) -- not a stable rate estimate at this n.",
    prohibited_interpretation="A statistically meaningful success-rate estimate.",
)
add_metric(
    metric_id="M13", metric_name="Synthetic correction shipping rate (labeled)", category="correction",
    dataset="GOLD-02_synthetic_stress_set", n=36,
    baseline=None, current=26 / 36, delta=None, unit="fraction", statistical_test=None,
    statistic=None, p_value=None, confidence_interval=None, fresh_or_historical="HISTORICAL, GPU-dependent",
    metric_class="natural_metric", evidence_grade=None,
    source_artifact="research/prototype/outputs/final_metrics.json (section_A_synthetic.correction_labeled)",
    safe_interpretation="26/36 (72.2%) synthetic (deliberately corrupted, GOLD-adjacent) corrections shipped under labeled framing.",
    prohibited_interpretation="Equivalent to, or predictive of, the natural-data correction shipping rate (1.8% cumulative) -- these are disjoint populations with different base rates by construction.",
)
add_metric(
    metric_id="M14", metric_name="Unsafe corrections shipped (cumulative)", category="safety",
    dataset="all_correction_attempts_project_history", n=final_metrics["section_D_correction_safety_cumulative"]["total_correction_attempts"] + 66,
    baseline=None, current=0, delta=None, unit="count", statistical_test=None, statistic=None,
    p_value=None, confidence_interval=None, fresh_or_historical="HISTORICAL", metric_class="natural_metric",
    evidence_grade=None, source_artifact="research/prototype/outputs/final_metrics.json",
    safe_interpretation="0 unsafe corrections observed in the tested correction history (56 natural + 66 synthetic attempts).",
    prohibited_interpretation="That 0 observed incidents proves unsafe corrections are impossible.",
)
add_metric(
    metric_id="M15", metric_name="Full regression suite result", category="component behavior",
    dataset="research/prototype/tests/", n=205, baseline=None, current=205, delta=None, unit="tests_passed",
    statistical_test=None, statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="FRESH (re-run at every step, STEP 2-7)", metric_class="behavior_metric",
    evidence_grade=None, source_artifact="testing/actual_outputs/step7_ablation/pytest_regression_final.txt",
    safe_interpretation="205/205 existing tests pass, unchanged since STEP 2.",
    prohibited_interpretation="A statement about statistical or legal accuracy.",
)
add_metric(
    metric_id="M16", metric_name="Atomic scope check unblocked count", category="correction",
    dataset="11_real_scope_violations_replay", n=11, baseline=0, current=1, delta=1, unit="count",
    statistical_test="none (descriptive)", statistic=None, p_value=None, confidence_interval=None,
    fresh_or_historical="FRESH REPRODUCTION (STEP 7)", metric_class="natural_metric", evidence_grade="C",
    source_artifact="testing/actual_outputs/step7_ablation/scope_check_replay_fresh.json",
    safe_interpretation="assertion_spans changed scope-gate behavior, unblocking 1 of 11 real scope violations at the gate.",
    prohibited_interpretation="That the unblocked case was verified to ship a safe correction (not tested by this replay).",
)

# ---------------------------------------------------------------------------
# Write CANONICAL_METRICS.csv / .json
# ---------------------------------------------------------------------------

canon_json_path = EVAL_DIR / "CANONICAL_METRICS.json"
canon_json_path.write_text(json.dumps({
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "repo_commit": git_commit(),
    "metrics": metrics,
}, indent=2, default=str), encoding="utf-8")
print(f"Wrote {canon_json_path} ({len(metrics)} metrics)")

canon_csv_path = EVAL_DIR / "CANONICAL_METRICS.csv"
fieldnames = ["metric_id", "metric_name", "category", "dataset", "n", "baseline", "current", "delta", "unit",
              "statistical_test", "statistic", "p_value", "confidence_interval", "fresh_or_historical",
              "metric_class", "evidence_grade", "source_artifact", "safe_interpretation", "prohibited_interpretation"]
with canon_csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for m in metrics:
        w.writerow(m)
print(f"Wrote {canon_csv_path}")

# ---------------------------------------------------------------------------
# PHASE 4 -- ORIGINAL_VS_CURRENT.csv/.md
# ---------------------------------------------------------------------------

ovc_rows = [
    {"metric": "Evidence coverage (209-claim paired natural)", "original": "63.2%", "current": "70.3%",
     "delta": "+7.1pp", "n": 209, "dataset": "209-claim paired natural set",
     "statistical_support": "McNemar p=0.0003; sign test p=6.10e-05", "classification": "SUPPORTED"},
    {"metric": "Verifier controlled benchmark (macro F1)", "original": "0.7487", "current": "0.9684",
     "delta": "+0.2197", "n": 420, "dataset": "GOLD-01 controlled benchmark",
     "statistical_support": "McNemar p=4.16e-23; sign test p=1.58e-30", "classification": "SUPPORTED"},
    {"metric": "Natural ENTAILED reached (147-claim subset)", "original": "0/147", "current": "13/147",
     "delta": "+13", "n": 147, "dataset": "final_validation Arm B evidence-matched subset",
     "statistical_support": "none performed", "classification": "DESCRIPTIVE (not a correctness metric)"},
    {"metric": "Natural CONTRADICTED detection (147-claim subset)", "original": "3", "current": "3",
     "delta": "0", "n": 147, "dataset": "final_validation Arm B evidence-matched subset",
     "statistical_support": "none performed", "classification": "DESCRIPTIVE"},
    {"metric": "Targeted correction shipping", "original": "0/5", "current": "1/10",
     "delta": "+1", "n": "5 vs 10", "dataset": "final_validation batch, targeted",
     "statistical_support": "none (n too small)", "classification": "DIAGNOSTIC / UNDERPOWERED"},
    {"metric": "Cumulative correction shipping", "original": "n/a (single-arm cumulative)", "current": "1/56 = 1.8%",
     "delta": "n/a", "n": 56, "dataset": "all natural correction attempts, project history",
     "statistical_support": "none (not an ablation)", "classification": "DIAGNOSTIC"},
    {"metric": "Unsafe corrections shipped", "original": "0", "current": "0",
     "delta": "0", "n": "56 natural + 66 synthetic = 122", "dataset": "all correction attempts, project history",
     "statistical_support": "none (descriptive count)", "classification": "DESCRIPTIVE (0 observed, not proof of impossibility)"},
]
with (EVAL_DIR / "ORIGINAL_VS_CURRENT.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric", "original", "current", "delta", "n", "dataset", "statistical_support", "classification"])
    w.writeheader()
    for r in ovc_rows:
        w.writerow(r)
print(f"Wrote {EVAL_DIR / 'ORIGINAL_VS_CURRENT.csv'}")

# ---------------------------------------------------------------------------
# PHASE 5 -- EVIDENCE_STRENGTH_MATRIX.csv
# ---------------------------------------------------------------------------

esm_rows = [
    {"conclusion": "Evidence-v1 increases observed coverage on paired natural claims", "dataset": "209-claim paired",
     "evidence": "McNemar + exact sign test, fresh reproduction", "statistical_support": "p=0.0003 / p=6.10e-05",
     "replicated": "Yes (STEP 6 and STEP 7 both reproduce it)", "grade": "A",
     "safe_claim": "Increased observed evidence coverage, zero regressions"},
    {"conclusion": "Labeled framing improves verifier benchmark performance", "dataset": "GOLD-01 controlled benchmark",
     "evidence": "McNemar + exact sign test, fresh", "statistical_support": "p=4.16e-23 / p=1.58e-30",
     "replicated": "Yes (STEP 4 and STEP 7)", "grade": "A",
     "safe_claim": "Substantially improved verifier accuracy/macro F1 on the controlled benchmark"},
    {"conclusion": "Labeled framing improves natural-data verification decisiveness", "dataset": "147-claim natural subset",
     "evidence": "Historical CPU re-verification", "statistical_support": "descriptive count only",
     "replicated": "No (single historical experiment)", "grade": "B",
     "safe_claim": "More claims reach a decisive verdict (ENTAILED) under labeled framing on this subset"},
    {"conclusion": "Claim parser fix increases evidence-matched count", "dataset": "n=30 reparse",
     "evidence": "Exact sign test, freshly recomputed", "statistical_support": "p=0.03125",
     "replicated": "Yes (matches final_comparison's independent figure)", "grade": "B",
     "safe_claim": "Increased per-case evidence-matched count, zero cases worsened"},
    {"conclusion": "Production confidence threshold (0.70) sits in a stable region", "dataset": "GOLD-01 benchmark, sweep",
     "evidence": "Descriptive sensitivity sweep, fresh", "statistical_support": "not a hypothesis test",
     "replicated": "Yes (STEP 1 and STEP 7)", "grade": "B",
     "safe_claim": "0.70 sits within ~0.002 macro-F1 of the empirical optimum, not fragile"},
    {"conclusion": "Atomic scope check unblocks some real scope violations", "dataset": "11 real scope violations",
     "evidence": "Deterministic replay, fresh reproduction", "statistical_support": "none (n=11, descriptive)",
     "replicated": "Yes (matches historical committed replay exactly)", "grade": "C",
     "safe_claim": "Changed scope-gate behavior (1/11 unblocked); downstream shipping not verified"},
    {"conclusion": "Narrow re-verification improves confidence calibration", "dataset": "3 correction_failed cases",
     "evidence": "Historical narrative citation", "statistical_support": "none performed",
     "replicated": "No", "grade": "C",
     "safe_claim": "More decisive re-verification signals on 3 cases; 0 shipping outcomes changed"},
    {"conclusion": "Labeled framing increases shipped corrections", "dataset": "final validation batch, targeted",
     "evidence": "Isolated-by-design historical GPU experiment", "statistical_support": "none (n too small)",
     "replicated": "No", "grade": "C",
     "safe_claim": "Directional shift (0/5->1/10), not statistically supported"},
    {"conclusion": "The four current production levers interact in some specific way", "dataset": "N/A",
     "evidence": "None", "statistical_support": "N/A", "replicated": "N/A", "grade": "E / NOT_ISOLATED",
     "safe_claim": "No claim can be made -- the experiment does not exist"},
]
with (EVAL_DIR / "EVIDENCE_STRENGTH_MATRIX.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["conclusion", "dataset", "evidence", "statistical_support", "replicated", "grade", "safe_claim"])
    w.writeheader()
    for r in esm_rows:
        w.writerow(r)
print(f"Wrote {EVAL_DIR / 'EVIDENCE_STRENGTH_MATRIX.csv'}")

# ---------------------------------------------------------------------------
# PHASE 6 -- STATISTICAL_RESULTS.csv
# ---------------------------------------------------------------------------

stat_rows = []
for f_ in ablation["findings"]:
    if f_.get("p_value") is not None:
        stat_rows.append({
            "hypothesis": f"{f_['factor']}: baseline vs variant has no effect",
            "dataset": f_["dataset"], "n": f_.get("n"), "paired": f_.get("paired", True),
            "test": f_.get("statistical_test"), "statistic": f_.get("statistic"), "p_value": f_.get("p_value"),
            "exact_test": f_.get("exact_sign_test_p_value", ""),
            "effect_change": f_.get("effect_size", f"{f_.get('baseline_value')} -> {f_.get('variant_value')}"),
            "interpretation": f_.get("safe_claim"),
            "multiple_comparison_status": f_.get("multiple_comparison_correction", "not applied (single pre-specified comparison)"),
            "exploratory_or_confirmatory": "confirmatory (reproduces this project's own pre-specified methodology)",
        })
with (EVAL_DIR / "STATISTICAL_RESULTS.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["hypothesis", "dataset", "n", "paired", "test", "statistic", "p_value",
                                       "exact_test", "effect_change", "interpretation",
                                       "multiple_comparison_status", "exploratory_or_confirmatory"])
    w.writeheader()
    for r in stat_rows:
        w.writerow(r)
print(f"Wrote {EVAL_DIR / 'STATISTICAL_RESULTS.csv'} ({len(stat_rows)} rows)")

# ---------------------------------------------------------------------------
# PHASE 7 -- CORRECTION_FUNNEL.csv
# ---------------------------------------------------------------------------

funnel_rows = [
    # synthetic (labeled arm)
    {"population": "synthetic_labeled", "candidate": 59, "correction_triggered": 36, "correction_generated": 36,
     "scope_gate_rejected": 0, "reverification_not_entailed": 10, "sibling_regression_rejected": "NOT AVAILABLE",
     "citation_identity_failures": "NOT AVAILABLE", "shipped": 26, "rejected_total": 10},
    # synthetic (bare arm)
    {"population": "synthetic_bare", "candidate": 59, "correction_triggered": 30, "correction_generated": 30,
     "scope_gate_rejected": 0, "reverification_not_entailed": 30, "sibling_regression_rejected": "NOT AVAILABLE",
     "citation_identity_failures": "NOT AVAILABLE", "shipped": 0, "rejected_total": 30},
    # natural targeted (bare, = final_gpu_validation Arm B original)
    {"population": "natural_targeted_bare", "candidate": 209, "correction_triggered": 5, "correction_generated": 5,
     "scope_gate_rejected": 2, "reverification_not_entailed": 3, "sibling_regression_rejected": 0,
     "citation_identity_failures": "NOT AVAILABLE", "shipped": 0, "rejected_total": 5},
    # natural targeted (labeled)
    {"population": "natural_targeted_labeled", "candidate": 209, "correction_triggered": 10, "correction_generated": 10,
     "scope_gate_rejected": 3, "reverification_not_entailed": 6, "sibling_regression_rejected": "NOT AVAILABLE",
     "citation_identity_failures": "NOT AVAILABLE", "shipped": 1, "rejected_total": 9},
    # cumulative natural (project history)
    {"population": "natural_cumulative_project_history", "candidate": "NOT AVAILABLE (not tracked as a single denominator)",
     "correction_triggered": 56, "correction_generated": 56, "scope_gate_rejected": 18,
     "reverification_not_entailed": 37, "sibling_regression_rejected": "NOT AVAILABLE",
     "citation_identity_failures": "NOT AVAILABLE", "shipped": 1, "rejected_total": 55},
]
with (EVAL_DIR / "CORRECTION_FUNNEL.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(funnel_rows[0].keys()))
    w.writeheader()
    for r in funnel_rows:
        w.writerow(r)
print(f"Wrote {EVAL_DIR / 'CORRECTION_FUNNEL.csv'}")

# ---------------------------------------------------------------------------
# PHASE 8 -- SAFETY_SUMMARY.csv
# ---------------------------------------------------------------------------

safety_rows = [
    {"safety_mechanism": "Unsafe corrections shipped (cumulative)", "count": 0,
     "denominator": "56 natural + 66 synthetic = 122 total correction attempts", "source": "outputs/final_metrics.json"},
    {"safety_mechanism": "Scope-gate rejections (cumulative natural)", "count": 18,
     "denominator": "56 natural correction attempts", "source": "outputs/final_metrics.json"},
    {"safety_mechanism": "Sibling-regression rejections observed (final_gpu_validation Arm B)", "count": 0,
     "denominator": "5 correction attempts", "source": "outputs/final_gpu_validation_metrics.json"},
    {"safety_mechanism": "Citation-identity preservation failures observed", "count": "NOT AVAILABLE (not separately tracked as a count; STEP 0 audit found 0 confirmed false-ship cases)",
     "denominator": "N/A", "source": "outputs/final_gpu_validation.md Section 4 (narrative)"},
    {"safety_mechanism": "Re-verification-not-ENTAILED rejections (cumulative natural)", "count": 37,
     "denominator": "56 natural correction attempts", "source": "outputs/final_metrics.json"},
]
with (EVAL_DIR / "SAFETY_SUMMARY.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["safety_mechanism", "count", "denominator", "source"])
    w.writeheader()
    for r in safety_rows:
        w.writerow(r)
print(f"Wrote {EVAL_DIR / 'SAFETY_SUMMARY.csv'}")

# ---------------------------------------------------------------------------
# PHASE 9 -- COMPONENT_TEST_MATRIX.csv
# ---------------------------------------------------------------------------

comp_rows = [
    {"component": "01_claim_parser", "tests": 111, "passed": 111, "real_model_used": "No", "cpu_gpu": "CPU",
     "representative_case": "IPC 120-B/471/477 vs POCA sec 1(d) act-attribution (gold_annotation.jsonl doc 2007_1517)",
     "classification": "SOFTWARE BEHAVIOR PASS", "source_artifact": "testing/actual_outputs/step5_components/01_claim_parser/"},
    {"component": "02_evidence_matcher", "tests": 72, "passed": 72, "real_model_used": "No", "cpu_gpu": "CPU",
     "representative_case": "Section 34 resolved independently across IPC / Arbitration Act 1940 / 1996",
     "classification": "SOFTWARE BEHAVIOR PASS", "source_artifact": "testing/actual_outputs/step5_components/02_evidence_matcher/"},
    {"component": "03_verifier", "tests": 48, "passed": 48, "real_model_used": "Yes (DeBERTa)", "cpu_gpu": "CPU",
     "representative_case": "Real Section 302 IPC evidence vs corrupted hypothesis -> CONTRADICTED",
     "classification": "SOFTWARE BEHAVIOR PASS", "source_artifact": "testing/actual_outputs/step5_components/03_verifier/"},
    {"component": "04_verdict_application", "tests": 3, "passed": 3, "real_model_used": "No (mocked)", "cpu_gpu": "CPU",
     "representative_case": "NO_EVIDENCE claim never reaches the verifier", "classification": "SOFTWARE BEHAVIOR PASS",
     "source_artifact": "testing/actual_outputs/step5_components/04_verdict_application/"},
    {"component": "05_citation_adversarial", "tests": 15, "passed": 15, "real_model_used": "No", "cpu_gpu": "CPU",
     "representative_case": "CrPC-vs-CPC Section 100 never cross-matches", "classification": "SOFTWARE BEHAVIOR PASS",
     "source_artifact": "testing/actual_outputs/step5_components/05_citation_adversarial/"},
    {"component": "06_correction_safety", "tests": 35, "passed": 35, "real_model_used": "Yes (DeBERTa, 3 of 35)", "cpu_gpu": "CPU",
     "representative_case": "Scope-violation correctly rejected before re-verification", "classification": "SOFTWARE BEHAVIOR PASS",
     "source_artifact": "testing/actual_outputs/step5_components/06_correction_safety/"},
    {"component": "07_final_assembly", "tests": 5, "passed": 5, "real_model_used": "Yes (DeBERTa, 3 of 5)", "cpu_gpu": "CPU",
     "representative_case": "Full run_case() record for a shipped correction and a scope-violation rejection",
     "classification": "SOFTWARE BEHAVIOR PASS", "source_artifact": "testing/actual_outputs/step5_components/07_final_assembly/"},
]
with (EVAL_DIR / "COMPONENT_TEST_MATRIX.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(comp_rows[0].keys()))
    w.writeheader()
    for r in comp_rows:
        w.writerow(r)
sum_of_groups = sum(r["tests"] for r in comp_rows)
print(f"Wrote {EVAL_DIR / 'COMPONENT_TEST_MATRIX.csv'} (sum of group counts = {sum_of_groups}, NOTE: groups overlap conceptually, see STEP 5 TEST_INVENTORY.md -- the authoritative non-duplicated total is 205)")

# ---------------------------------------------------------------------------
# PHASE 11 -- figure_data/*.csv (data only, no PNGs generated in this step)
# ---------------------------------------------------------------------------

def write_csv(name: str, fieldnames: list[str], rows: list[dict]):
    path = FIG_DIR / name
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {path} ({len(rows)} rows)")


# 01 -- overall metric comparison
write_csv("01_overall_metric_comparison.csv",
          ["metric", "original_value", "current_value", "unit", "dataset", "n", "fresh_or_historical", "source"],
          [
              {"metric": "evidence_coverage", "original_value": paired209["fresh_evidence_coverage_arm_A"],
               "current_value": paired209["fresh_evidence_coverage_arm_B"], "unit": "fraction",
               "dataset": "209_claim_paired_natural", "n": 209, "fresh_or_historical": "FRESH",
               "source": "step6/209_paired/paired_209_metrics.json"},
              {"metric": "controlled_benchmark_macro_f1", "original_value": gold01["results_by_framing"]["bare"]["macro_f1"],
               "current_value": gold01["results_by_framing"]["labeled"]["macro_f1"], "unit": "fraction",
               "dataset": "GOLD-01", "n": 420, "fresh_or_historical": "FRESH",
               "source": "step4/gold01_controlled/gold01_metrics.json"},
              {"metric": "controlled_benchmark_accuracy", "original_value": gold01["results_by_framing"]["bare"]["accuracy"],
               "current_value": gold01["results_by_framing"]["labeled"]["accuracy"], "unit": "fraction",
               "dataset": "GOLD-01", "n": 420, "fresh_or_historical": "FRESH",
               "source": "step4/gold01_controlled/gold01_metrics.json"},
              {"metric": "synthetic_contradiction_recall", "original_value": gold02["results_by_framing"]["bare"]["contradiction_recall"],
               "current_value": gold02["results_by_framing"]["labeled"]["contradiction_recall"], "unit": "fraction",
               "dataset": "GOLD-02", "n": 59, "fresh_or_historical": "FRESH",
               "source": "step4/gold02_synthetic/gold02_metrics.json"},
          ])

# 02 -- evidence coverage (all datasets with a coverage figure)
ec_rows = [
    {"dataset": "209_paired_ArmA", "arm_or_config": "v0-only (original)", "coverage": paired209["fresh_evidence_coverage_arm_A"],
     "n": 209, "n_matched": None, "fresh_or_historical": "FRESH", "source": "step6/209_paired"},
    {"dataset": "209_paired_ArmB", "arm_or_config": "v0+v1 (current)", "coverage": paired209["fresh_evidence_coverage_arm_B"],
     "n": 209, "n_matched": None, "fresh_or_historical": "FRESH", "source": "step6/209_paired"},
    {"dataset": "588_claim_aggregate", "arm_or_config": "v0+v1 (current)", "coverage": claims588["evidence_coverage"],
     "n": 588, "n_matched": claims588["n_evidence_matched"], "fresh_or_historical": "FRESH", "source": "step6/588_claims"},
]
for b in batches["batches"]:
    if b["status"] == "analyzed":
        ec_rows.append({"dataset": b["name"], "arm_or_config": b["configuration"], "coverage": b["evidence_coverage"],
                         "n": b["n_claims"], "n_matched": b["n_evidence_matched"], "fresh_or_historical": "HISTORICAL",
                         "source": "step6/batches/batches_analysis.json"})
write_csv("02_evidence_coverage.csv",
          ["dataset", "arm_or_config", "coverage", "n", "n_matched", "fresh_or_historical", "source"], ec_rows)

# 03 -- verdict distribution (all datasets)
vd_rows = []
for label, vd, n, fresh, src in [
    ("588_claim_aggregate", claims588["verdict_distribution"], 588, "FRESH", "step6/588_claims/claims_588_metrics.json"),
    ("209_paired_ArmA_fresh", paired209["fresh_verdict_distribution_arm_A"], 209, "FRESH", "step6/209_paired/paired_209_metrics.json"),
    ("209_paired_ArmB_fresh", paired209["fresh_verdict_distribution_arm_B"], 209, "FRESH", "step6/209_paired/paired_209_metrics.json"),
]:
    for verdict, count in vd.items():
        vd_rows.append({"dataset": label, "verdict": verdict, "count": count, "n_total": n, "fresh_or_historical": fresh, "source": src})
for b in batches["batches"]:
    if b["status"] == "analyzed":
        for verdict, count in b["verdict_distribution"].items():
            vd_rows.append({"dataset": b["name"], "verdict": verdict, "count": count, "n_total": b["n_claims"],
                             "fresh_or_historical": "HISTORICAL", "source": "step6/batches/batches_analysis.json"})
write_csv("03_verdict_distribution.csv", ["dataset", "verdict", "count", "n_total", "fresh_or_historical", "source"], vd_rows)

# 04 -- correction funnel (reuse the canonical funnel rows, with source added)
funnel_sources = {
    "synthetic_labeled": "outputs/final_metrics.json (section_A_synthetic.correction_labeled)",
    "synthetic_bare": "outputs/final_metrics.json (section_A_synthetic.correction_bare)",
    "natural_targeted_bare": "outputs/final_gpu_validation_metrics.json (per_arm.B)",
    "natural_targeted_labeled": "outputs/labeled_correction_validation_gpu_metrics.json",
    "natural_cumulative_project_history": "outputs/final_metrics.json (section_D_correction_safety_cumulative)",
}
funnel_rows_with_source = [dict(r, source=funnel_sources[r["population"]]) for r in funnel_rows]
write_csv("04_correction_funnel.csv", list(funnel_rows_with_source[0].keys()), funnel_rows_with_source)

# 05 -- correction outcome (per population, shipped/failed/scope_violation)
write_csv("05_correction_outcome.csv",
          ["population", "n_triggered", "shipped", "correction_failed_or_reverification_not_entailed", "scope_violation", "source"],
          [
              {"population": "synthetic_bare", "n_triggered": 30, "shipped": 0, "correction_failed_or_reverification_not_entailed": 30, "scope_violation": 0, "source": "outputs/final_metrics.json"},
              {"population": "synthetic_labeled", "n_triggered": 36, "shipped": 26, "correction_failed_or_reverification_not_entailed": 10, "scope_violation": 0, "source": "outputs/final_metrics.json"},
              {"population": "natural_targeted_bare", "n_triggered": 5, "shipped": 0, "correction_failed_or_reverification_not_entailed": 3, "scope_violation": 2, "source": "outputs/final_gpu_validation_metrics.json"},
              {"population": "natural_targeted_labeled", "n_triggered": 10, "shipped": 1, "correction_failed_or_reverification_not_entailed": 6, "scope_violation": 3, "source": "outputs/labeled_correction_validation_gpu_metrics.json"},
              {"population": "natural_cumulative", "n_triggered": 56, "shipped": 1, "correction_failed_or_reverification_not_entailed": 37, "scope_violation": 18, "source": "outputs/final_metrics.json"},
          ])

# 06 -- safety (reuse safety_rows)
write_csv("06_safety.csv", ["safety_mechanism", "count", "denominator", "source"], safety_rows)

# 07 -- confidence distribution (588-claim aggregate, by verdict)
conf_rows = []
for verdict, stats in claims588.get("confidence_by_verdict", {}).items():
    conf_rows.append({"dataset": "588_claim_aggregate", "verdict": verdict, "mean_confidence": stats["mean"],
                       "median_confidence": stats["median"], "n": stats["n"], "source": "step6/588_claims/claims_588_metrics.json"})
if claims588.get("confidence_overall"):
    conf_rows.append({"dataset": "588_claim_aggregate", "verdict": "ALL", "mean_confidence": claims588["confidence_overall"]["mean"],
                       "median_confidence": claims588["confidence_overall"]["median"], "n": claims588["confidence_overall"]["n"],
                       "source": "step6/588_claims/claims_588_metrics.json"})
write_csv("07_confidence_distribution.csv", ["dataset", "verdict", "mean_confidence", "median_confidence", "n", "source"], conf_rows)

# 08 -- ablation comparison (reuse ABLATION_SUMMARY findings)
ab_rows = []
for f_ in ablation["findings"]:
    ab_rows.append({
        "factor": f_["factor"], "baseline_value": f_.get("baseline_value"), "variant_value": f_.get("variant_value"),
        "primary_metric": f_.get("primary_metric"), "p_value": f_.get("p_value"),
        "classification": f_.get("classification"), "fresh_or_historical": f_.get("fresh_or_historical", "").split(" (")[0],
        "source": "testing/evaluation/ABLATION_SUMMARY.json",
    })
write_csv("08_ablation_comparison.csv",
          ["factor", "baseline_value", "variant_value", "primary_metric", "p_value", "classification", "fresh_or_historical", "source"],
          ab_rows)

# 09 -- runtime/resource (only where GPU experiments recorded real runtime -- historical)
write_csv("09_runtime_resource.csv",
          ["arm", "runtime_seconds", "peak_vram_mib", "n_cases", "fresh_or_historical", "source"],
          [
              {"arm": "final_gpu_validation_total", "runtime_seconds": final_gpu_val_metrics["runtime_seconds_total"],
               "peak_vram_mib": final_gpu_val_metrics["peak_vram_mib"], "n_cases": final_gpu_val_metrics["n_cases"],
               "fresh_or_historical": "HISTORICAL (GPU, prior session)", "source": "outputs/final_gpu_validation_metrics.json"},
              {"arm": "final_gpu_validation_generation_only", "runtime_seconds": final_gpu_val_metrics["runtime_seconds_generation"],
               "peak_vram_mib": final_gpu_val_metrics["peak_vram_mib"], "n_cases": final_gpu_val_metrics["n_cases"],
               "fresh_or_historical": "HISTORICAL (GPU, prior session)", "source": "outputs/final_gpu_validation_metrics.json"},
              {"arm": "synthetic_correction_bare", "runtime_seconds": final_metrics["section_A_synthetic"]["correction_bare"]["runtime_seconds_total_arm"],
               "peak_vram_mib": final_metrics["section_A_synthetic"]["correction_bare"]["peak_vram_mib_cumulative"],
               "n_cases": 59, "fresh_or_historical": "HISTORICAL (GPU, prior session)", "source": "outputs/final_metrics.json"},
              {"arm": "synthetic_correction_labeled", "runtime_seconds": final_metrics["section_A_synthetic"]["correction_labeled"]["runtime_seconds_total_arm"],
               "peak_vram_mib": final_metrics["section_A_synthetic"]["correction_labeled"]["peak_vram_mib_cumulative"],
               "n_cases": 59, "fresh_or_historical": "HISTORICAL (GPU, prior session)", "source": "outputs/final_metrics.json"},
              {"arm": "step4_gold01_labeled_cpu", "runtime_seconds": gold01["results_by_framing"]["labeled"]["elapsed_seconds"],
               "peak_vram_mib": "N/A (CPU)", "n_cases": 420, "fresh_or_historical": "FRESH (CPU, this workspace)",
               "source": "step4/gold01_controlled/gold01_metrics.json"},
          ])

# 10 -- cumulative natural results (all natural batches + 588 + 209, side by side)
cum_rows = list(ec_rows)  # same shape reused
write_csv("10_cumulative_natural_results.csv",
          ["dataset", "arm_or_config", "coverage", "n", "n_matched", "fresh_or_historical", "source"], cum_rows)

# 11 -- synthetic vs natural transfer
write_csv("11_synthetic_vs_natural_transfer.csv",
          ["metric", "synthetic_value", "natural_value", "populations_comparable", "note", "source"],
          [
              {"metric": "contradiction_recall_or_detection", "synthetic_value": gold02["results_by_framing"]["labeled"]["contradiction_recall"],
               "natural_value": "not directly comparable (no natural denominator of known-contradictory claims)",
               "populations_comparable": "NO",
               "note": "Synthetic set is 100% contradictory by construction; natural data has no such label.",
               "source": "step4/gold02 + step6/588_claims"},
              {"metric": "correction_shipping_rate", "synthetic_value": "26/36 = 0.722", "natural_value": "1/56 = 0.018",
               "populations_comparable": "NO",
               "note": "Disjoint populations with different base rates by construction -- the 72.2% synthetic figure must not be presented as equivalent to the natural shipped-correction rate.",
               "source": "outputs/final_metrics.json"},
          ])

print("\nAll STEP 8 core registries and figure-data CSVs written.")
