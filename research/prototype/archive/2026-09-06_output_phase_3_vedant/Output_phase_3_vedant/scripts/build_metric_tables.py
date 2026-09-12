#!/usr/bin/env python3
"""Phase 3 (Vedant) — STEP 1: extract every plotted number from its source artifact
into locked figure-data CSVs under Output_phase_3_vedant/metrics/.

No experimental value is computed, re-run, or re-interpreted here. Every row is
read out of an existing committed artifact and carries its own `source_artifact`
provenance column. `generate_figures.py` reads ONLY these CSVs — it never opens a
source artifact directly, so no number can enter a figure without a traceable row.

Read-only against: config/, src/, outputs/, evaluation/, archive/, research/data/.
Writes only into Output_phase_3_vedant/metrics/.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

GOLD01 = C.EVAL_ACTUAL / "gold_benchmark_runs" / "gold01_controlled" / "gold01_metrics.json"
GOLD02 = C.EVAL_ACTUAL / "gold_benchmark_runs" / "gold02_synthetic" / "gold02_metrics.json"
PAIRED209 = C.EVAL_ACTUAL / "natural_data_runs" / "209_paired" / "paired_209_metrics.json"
CLAIMS588 = C.EVAL_ACTUAL / "natural_data_runs" / "588_claims" / "claims_588_metrics.json"
BATCHES = C.EVAL_ACTUAL / "natural_data_runs" / "batches" / "batches_analysis.json"
ABLATION = C.EVAL_ABLATION / "ABLATION_SUMMARY.json"
SCOPE_REPLAY = C.EVAL_ABLATION / "scope_check_replay_fresh.json"
FINAL_METRICS = C.OUTPUTS / "final_metrics.json"
FINAL_GPU = C.OUTPUTS / "final_gpu_validation_metrics.json"
LABELED_CORR = C.OUTPUTS / "labeled_correction_validation_gpu_metrics.json"
CPU_FRAMING_147 = C.OUTPUTS / "final_validation_bare_vs_labeled_cpu_metrics.json"
THRESHOLD = C.OUTPUTS / "threshold_sensitivity_analysis.json"
EVID_V0_V1_588 = C.OUTPUTS / "evidence_coverage_v0_vs_v1.json"
NOEV_TAXONOMY = C.OUTPUTS / "no_evidence_taxonomy_v3.json"
PARSER_FIX = C.OUTPUTS / "parser_fix_before_after_n30.json"
COMPONENT_MATRIX = C.EVAL_METRICS / "COMPONENT_TEST_MATRIX.csv"
GPU_209_FRESH = C.EVAL_ACTUAL / "gpu_209_reproduction" / "step10b_final_gpu_validation_metrics.json"
GPU_CORR_FRESH = (C.EVAL_ACTUAL / "gpu_correction_rerun"
                  / "labeled_correction_validation_gpu_metrics.fresh.json")

SOURCE_MAP: list[dict] = []


def emit(csv_name: str, fieldnames: list[str], rows: list[dict],
         purpose: str, sources: list[Path], dataset: str, n: str,
         status: str, grade: str, caveat: str) -> None:
    """Write one figure-data CSV and register it in METRIC_SOURCE_MAP.csv."""
    path = C.OUT_METRICS / csv_name
    C.write_csv(path, fieldnames, rows)
    SOURCE_MAP.append({
        "metric_csv": csv_name,
        "purpose": purpose,
        "source_artifact": " ; ".join(C.rel(s) for s in sources),
        "dataset": dataset,
        "n": n,
        "fresh_or_historical": status,
        "evidence_grade": grade,
        "caveat": caveat,
        "generation_script": "Output_phase_3_vedant/scripts/build_metric_tables.py",
    })
    print(f"  wrote metrics/{csv_name}  ({len(rows)} rows)")


# ==========================================================================
# M01 — headline baseline vs modified comparison (four strongest metrics)
# ==========================================================================
def m01_headline():
    g1 = C.load_json(GOLD01)["results_by_framing"]
    g2 = C.load_json(GOLD02)["results_by_framing"]
    p9 = C.load_json(PAIRED209)
    abl = {f["factor"]: f for f in C.load_json(ABLATION)["findings"]}

    rows = [
        {
            "metric_key": "evidence_coverage_209_paired",
            "metric_label": "Evidence coverage\n(209-claim paired natural)",
            "baseline_value": p9["fresh_evidence_coverage_arm_A"],
            "modified_value": p9["fresh_evidence_coverage_arm_B"],
            "unit": "fraction of claims",
            "dataset": "209_claim_paired_natural_evaluation",
            "n": 209,
            "metric_class": "METRIC-ONLY (natural, no correctness label)",
            "lever_changed": "use_evidence_v1: false -> true",
            "statistical_test": abl["evidence_v1"]["statistical_test"],
            "p_value": abl["evidence_v1"]["p_value"],
            "fresh_or_historical": "FRESH REPRODUCTION (CPU)",
            "evidence_grade": "A",
            "source_artifact": C.rel(PAIRED209),
        },
        {
            "metric_key": "gold01_macro_f1",
            "metric_label": "Verifier macro F1\n(GOLD-01 controlled benchmark)",
            "baseline_value": g1["bare"]["macro_f1"],
            "modified_value": g1["labeled"]["macro_f1"],
            "unit": "macro F1",
            "dataset": "GOLD-01_controlled_verifier_benchmark",
            "n": 420,
            "metric_class": "GOLD (labelled ground truth)",
            "lever_changed": "premise_framing: bare -> labeled",
            "statistical_test": abl["premise_framing"]["statistical_test"],
            "p_value": abl["premise_framing"]["p_value"],
            "fresh_or_historical": "FRESH (CPU)",
            "evidence_grade": "A",
            "source_artifact": C.rel(GOLD01),
        },
        {
            "metric_key": "gold01_accuracy",
            "metric_label": "Verifier accuracy\n(GOLD-01 controlled benchmark)",
            "baseline_value": g1["bare"]["accuracy"],
            "modified_value": g1["labeled"]["accuracy"],
            "unit": "fraction correct",
            "dataset": "GOLD-01_controlled_verifier_benchmark",
            "n": 420,
            "metric_class": "GOLD (labelled ground truth)",
            "lever_changed": "premise_framing: bare -> labeled",
            "statistical_test": abl["premise_framing"]["statistical_test"],
            "p_value": abl["premise_framing"]["p_value"],
            "fresh_or_historical": "FRESH (CPU)",
            "evidence_grade": "A",
            "source_artifact": C.rel(GOLD01),
        },
        {
            "metric_key": "gold02_contradiction_recall",
            "metric_label": "Contradiction recall\n(GOLD-02 synthetic stress set)",
            "baseline_value": g2["bare"]["contradiction_recall"],
            "modified_value": g2["labeled"]["contradiction_recall"],
            "unit": "recall",
            "dataset": "GOLD-02_synthetic_stress_set",
            "n": 59,
            "metric_class": "GOLD (contradictory by construction)",
            "lever_changed": "premise_framing: bare -> labeled",
            "statistical_test": "none performed",
            "p_value": "",
            "fresh_or_historical": "FRESH (CPU)",
            "evidence_grade": "A",
            "source_artifact": C.rel(GOLD02),
        },
    ]
    emit("M01_headline_baseline_vs_modified.csv", list(rows[0].keys()), rows,
         "Four strongest baseline-vs-modified comparisons on one 0-1 axis",
         [GOLD01, GOLD02, PAIRED209, ABLATION],
         "GOLD-01 / GOLD-02 / 209-claim paired natural", "420 / 59 / 209",
         "FRESH", "A",
         "Heterogeneous metric types on a shared axis; bar heights are NOT "
         "interchangeable across categories. Natural evidence coverage is not accuracy.")


# ==========================================================================
# M02 / M03 / M04 — GOLD-01 overall, per-class, confusion matrices
# ==========================================================================
def m02_m03_m04_gold01():
    g = C.load_json(GOLD01)
    byf = g["results_by_framing"]
    abl = {f["factor"]: f for f in C.load_json(ABLATION)["findings"]}["premise_framing"]

    rows = []
    for metric in ("accuracy", "macro_f1"):
        rows.append({
            "metric": metric,
            "baseline_bare": byf["bare"][metric],
            "modified_labeled": byf["labeled"][metric],
            "delta": byf["labeled"][metric] - byf["bare"][metric],
            "n_items": g["n_items"],
            "verifier_model": g["verifier_model"],
            "confidence_threshold": g["confidence_threshold"],
            "device": g["device"],
            "mcnemar_statistic": abl["statistic"],
            "mcnemar_p_value": abl["p_value"],
            "exact_sign_test_p_value": abl["exact_sign_test_p_value"],
            "source_artifact": C.rel(GOLD01),
        })
    emit("M02_gold01_overall.csv", list(rows[0].keys()), rows,
         "GOLD-01 accuracy and macro F1, baseline (bare) vs modified (labeled)",
         [GOLD01, ABLATION], "GOLD-01_controlled_verifier_benchmark", "420",
         "FRESH (CPU)", "A",
         "Curated controlled benchmark; hypotheses are mechanically constructed, "
         "not free-running generated claims.")

    pc_rows = []
    for framing, sysname in (("bare", "baseline"), ("labeled", "modified")):
        for cls, d in byf[framing]["per_class"].items():
            pc_rows.append({
                "system": sysname,
                "system_label": C.BASELINE_LABEL_1L if sysname == "baseline" else C.MODIFIED_LABEL_1L,
                "premise_framing": framing,
                "class": cls,
                "precision": d["precision"],
                "recall": d["recall"],
                "f1": d["f1"],
                "support": d["support"],
                "tp": d["tp"], "fp": d["fp"], "fn": d["fn"],
                "n_items": g["n_items"],
                "source_artifact": C.rel(GOLD01),
            })
    emit("M03_gold01_per_class.csv", list(pc_rows[0].keys()), pc_rows,
         "GOLD-01 per-class precision / recall / F1 for both systems",
         [GOLD01], "GOLD-01_controlled_verifier_benchmark", "420",
         "FRESH (CPU)", "A",
         "Precision/recall are legitimate here ONLY because GOLD-01 carries real "
         "per-item labels; no natural-data figure in this package uses them.")

    cm_rows = []
    for framing, sysname in (("bare", "baseline"), ("labeled", "modified")):
        for true_lbl, preds in byf[framing]["confusion_matrix"].items():
            for pred_lbl, count in preds.items():
                cm_rows.append({
                    "system": sysname,
                    "premise_framing": framing,
                    "true_label": true_lbl,
                    "predicted_label": pred_lbl,
                    "count": count,
                    "n_items": g["n_items"],
                    "source_artifact": C.rel(GOLD01),
                })
    emit("M04_gold01_confusion.csv", list(cm_rows[0].keys()), cm_rows,
         "GOLD-01 3x3 confusion matrices, baseline vs modified",
         [GOLD01], "GOLD-01_controlled_verifier_benchmark", "420",
         "FRESH (CPU)", "A", "Counts are per-item verifier decisions against GOLD labels.")


# ==========================================================================
# M05 — GOLD-02 synthetic stress
# ==========================================================================
def m05_gold02():
    g = C.load_json(GOLD02)
    byf = g["results_by_framing"]
    rows = []
    for framing, sysname in (("bare", "baseline"), ("labeled", "modified")):
        r = byf[framing]
        outcomes = r["confusion_matrix"]["CONTRADICTED"]
        rows.append({
            "system": sysname,
            "premise_framing": framing,
            "contradiction_recall": r["contradiction_recall"],
            "detected_contradicted": outcomes["CONTRADICTED"],
            "missed_as_nei": outcomes["NOT_ENOUGH_INFORMATION"],
            "missed_as_entailed": outcomes["ENTAILED"],
            "no_evidence": outcomes["NO_EVIDENCE"],
            "n_items": g["n_items"],
            "n_no_evidence": r["n_no_evidence"],
            "contradicted_precision": r["per_class"]["CONTRADICTED"]["precision"],
            "verifier_model": g["verifier_model"],
            "device": g["device"],
            "source_artifact": C.rel(GOLD02),
        })
    emit("M05_gold02_synthetic_stress.csv", list(rows[0].keys()), rows,
         "GOLD-02 synthetic stress-set contradiction recall and outcome split",
         [GOLD02], "GOLD-02_synthetic_stress_set", "59", "FRESH (CPU)", "A",
         "Every record is CONTRADICTED by construction, so recall here is a "
         "detection-sensitivity measure on deliberately corrupted claims — it is "
         "not a natural-data accuracy figure.")


# ==========================================================================
# M06 / M07 — evidence coverage
# ==========================================================================
def m06_m07_evidence():
    p = C.load_json(PAIRED209)
    ch = p["evidence_change_counts"]
    mc = p["mcnemar_evidence_coverage"]
    rows = [
        {"system": "baseline", "system_label": C.BASELINE_LABEL_1L,
         "arm": "Arm A", "evidence_pool": "v0 only",
         "evidence_pool_size": p["arm_A_config"]["evidence_pool_size"],
         "evidence_coverage": p["fresh_evidence_coverage_arm_A"],
         "n_claims": p["n_paired_claims"],
         "n_matched": ch["unchanged_matched"],
         "source_artifact": C.rel(PAIRED209)},
        {"system": "modified", "system_label": C.MODIFIED_LABEL_1L,
         "arm": "Arm B", "evidence_pool": "v0 + v1",
         "evidence_pool_size": p["arm_B_config"]["evidence_pool_size"],
         "evidence_coverage": p["fresh_evidence_coverage_arm_B"],
         "n_claims": p["n_paired_claims"],
         "n_matched": ch["unchanged_matched"] + ch["evidence_gained"],
         "source_artifact": C.rel(PAIRED209)},
    ]
    emit("M06_evidence_coverage_209_paired.csv", list(rows[0].keys()), rows,
         "Paired 209-claim evidence coverage, baseline v0 pool vs modified v0+v1 pool",
         [PAIRED209], "209_claim_paired_natural_evaluation", "209",
         "FRESH REPRODUCTION (CPU)", "A",
         "Coverage = retrieval found a usable record. NOT a correctness or accuracy measure.")

    disc = [{
        "gained_evidence_b": ch["evidence_gained"],
        "lost_evidence_c": mc["c_lost"],
        "unchanged_matched": ch["unchanged_matched"],
        "unchanged_no_evidence": ch["unchanged_no_evidence"],
        "mcnemar_chi2": mc["chi2"],
        "mcnemar_p_value": mc["p_value"],
        "n_claims": p["n_paired_claims"],
        "source_artifact": C.rel(PAIRED209),
    }]
    emit("M06b_evidence_209_discordance.csv", list(disc[0].keys()), disc,
         "McNemar discordant-pair counts behind the 209-claim coverage result",
         [PAIRED209], "209_claim_paired_natural_evaluation", "209",
         "FRESH REPRODUCTION (CPU)", "A", "Paired binary event: claim received usable evidence.")

    e = C.load_json(EVID_V0_V1_588)
    rows2 = [
        {"system": "baseline", "evidence_pool": "v0 only",
         "n_matched": e["n_matched_v0"], "n_claims": e["n_claims"],
         "coverage_pct": e["coverage_v0_pct"], "newly_covered": "",
         "source_artifact": C.rel(EVID_V0_V1_588)},
        {"system": "modified", "evidence_pool": "v0 + v1",
         "n_matched": e["n_matched_v1"], "n_claims": e["n_claims"],
         "coverage_pct": e["coverage_v1_pct"], "newly_covered": e["n_newly_covered_by_v1"],
         "source_artifact": C.rel(EVID_V0_V1_588)},
    ]
    emit("M07_evidence_coverage_588_corpus.csv", list(rows2[0].keys()), rows2,
         "Corpus-level evidence coverage over all 588 pooled natural claims, v0 vs v0+v1",
         [EVID_V0_V1_588], "588 pooled natural claims (all experiments)", "588",
         "HISTORICAL (corpus-level replay, CPU)", "B",
         "Corpus-level, not a paired-arm experiment; complements the paired 209 result.")


# ==========================================================================
# M08 / M09 / M10 — verdict distributions
# ==========================================================================
def m08_m09_m10_verdicts():
    p = C.load_json(PAIRED209)
    c588 = C.load_json(CLAIMS588)
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION", "NO_EVIDENCE"]

    rows = []
    for key, sysname, label, n, status in (
        ("fresh_verdict_distribution_arm_A", "baseline",
         "Baseline evidence pool v0 (Arm A)", p["n_paired_claims"], "FRESH"),
        ("fresh_verdict_distribution_arm_B", "modified",
         "Modified evidence pool v0+v1 (Arm B)", p["n_paired_claims"], "FRESH"),
    ):
        for v in order:
            rows.append({
                "dataset": "209_claim_paired_natural_evaluation", "system": sysname,
                "arm_label": label, "verdict": v,
                "count": p[key].get(v, 0), "n_total": n,
                "premise_framing": p["fresh_reverification_premise_framing"],
                "fresh_or_historical": status, "source_artifact": C.rel(PAIRED209),
            })
    for v in order:
        rows.append({
            "dataset": "588_claim_natural_aggregate", "system": "modified",
            "arm_label": "Modified production config (588-claim aggregate)", "verdict": v,
            "count": c588["verdict_distribution"].get(v, 0), "n_total": c588["n_claims"],
            "premise_framing": c588["config"]["premise_framing"],
            "fresh_or_historical": "FRESH", "source_artifact": C.rel(CLAIMS588),
        })
    emit("M08_verdict_distribution.csv", list(rows[0].keys()), rows,
         "Verifier verdict distributions on natural claims",
         [PAIRED209, CLAIMS588], "209-claim paired + 588-claim aggregate", "209 / 588",
         "FRESH (CPU)", "n/a (descriptive)",
         "Verdict counts are the NLI model's own outputs, NOT correctness labels.")

    b = C.load_json(BATCHES)["batches"]
    by_name = {x["name"]: x for x in b}
    rows2 = []
    for batch, pair in (("batch1", ("batch1_bare", "batch1_labeled")),
                        ("batch2", ("batch2_bare", "batch2_labeled"))):
        for name, sysname in zip(pair, ("baseline", "modified")):
            d = by_name[name]
            for v in order:
                rows2.append({
                    "batch": batch, "regime": name, "system": sysname,
                    "premise_framing": "bare" if sysname == "baseline" else "labeled",
                    "configuration": d["configuration"], "verdict": v,
                    "count": d["verdict_distribution"].get(v, 0),
                    "n_claims": d["n_claims"], "n_cases": d["n_cases"],
                    "evidence_coverage": d["evidence_coverage"],
                    "fresh_or_historical": "HISTORICAL",
                    "source_artifact": C.rel(BATCHES),
                })
    emit("M09_premise_framing_natural_batches.csv", list(rows2[0].keys()), rows2,
         "Premise-framing effect on natural-data verdicts (batch1 n=251, batch2 n=236)",
         [BATCHES], "natural_candidates batch1 / batch2", "251 / 236",
         "HISTORICAL", "B",
         "Same claims and same v0 evidence pool in each pair; only premise framing "
         "differs. Verdict shifts are decisiveness, not measured correctness.")

    f = C.load_json(CPU_FRAMING_147)
    rows3 = []
    for key, sysname, framing in (("bare_verdict_counts", "baseline", "bare"),
                                  ("labeled_verdict_counts", "modified", "labeled")):
        for v in order:
            rows3.append({
                "system": sysname, "premise_framing": framing, "verdict": v,
                "count": f[key].get(v, 0), "n_claims": f["n_claims_with_evidence"],
                "correction_triggers": f["bare_correction_triggers"] if framing == "bare"
                                       else f["labeled_correction_triggers"],
                "n_verdict_flips": f["n_verdict_flips"],
                "fresh_or_historical": "HISTORICAL",
                "source_artifact": C.rel(CPU_FRAMING_147),
            })
    emit("M10_natural_147_framing_shift.csv", list(rows3[0].keys()), rows3,
         "Premise-framing verdict shift on the same 147 evidence-matched natural claims",
         [CPU_FRAMING_147], "final_validation Arm B evidence-matched subset", "147",
         "HISTORICAL (CPU verification-only re-run)", "B",
         "ENTAILED 0 -> 13 is a count of model verdicts reached, NOT of claims proven correct.")


# ==========================================================================
# M11 / M12 — confidence distribution and threshold sensitivity
# ==========================================================================
def m11_m12_confidence():
    c = C.load_json(CLAIMS588)
    rows = []
    for verdict, d in c["confidence_by_verdict"].items():
        rows.append({
            "dataset": "588_claim_natural_aggregate", "verdict": verdict,
            "n": d["n"], "mean_confidence": d["mean"], "median_confidence": d["median"],
            "min_confidence": d["min"], "max_confidence": d["max"],
            "premise_framing": c["config"]["premise_framing"],
            "confidence_threshold": c["config"]["confidence_threshold"],
            "source_artifact": C.rel(CLAIMS588),
        })
    ov = c["confidence_overall"]
    rows.append({
        "dataset": "588_claim_natural_aggregate", "verdict": "ALL evidence-matched",
        "n": ov["n"], "mean_confidence": ov["mean"], "median_confidence": ov["median"],
        "min_confidence": "", "max_confidence": "",
        "premise_framing": c["config"]["premise_framing"],
        "confidence_threshold": c["config"]["confidence_threshold"],
        "source_artifact": C.rel(CLAIMS588),
    })
    emit("M11_confidence_by_verdict_588.csv", list(rows[0].keys()), rows,
         "Verifier confidence per verdict on the 588-claim natural aggregate",
         [CLAIMS588], "588_claim_natural_aggregate", "390 evidence-matched of 588",
         "FRESH (CPU)", "n/a (descriptive)",
         "Confidence is the NLI model's own softmax certainty, not correctness.")

    t = C.load_json(THRESHOLD)
    rows2 = []
    for framing, sysname in (("bare", "baseline"), ("labeled", "modified")):
        for pt in t["results"][framing]["sweep"]:
            rows2.append({
                "system": sysname, "premise_framing": framing,
                "threshold": pt["threshold"], "macro_f1": pt["macro_f1"],
                "accuracy": pt["accuracy"],
                "n_low_confidence_downgrades": pt["n_low_confidence_downgrades"],
                "n_items": t["results"][framing]["n_items"],
                "production_threshold": t["production_threshold"],
                "source_artifact": C.rel(THRESHOLD),
            })
    emit("M12_confidence_threshold_sweep.csv", list(rows2[0].keys()), rows2,
         "Deterministic threshold sweep (0.50-0.95) on GOLD-01 for both premise framings",
         [THRESHOLD], "GOLD-01_controlled_verifier_benchmark (stored softmax replay)", "420",
         "FRESH (deterministic replay, no re-inference)", "B",
         "A sensitivity description, not a threshold search; production threshold was "
         "not changed on the strength of this sweep.")


# ==========================================================================
# M13 / M14 / M15 — correction funnel, outcomes, safety
# ==========================================================================
def m13_m14_m15_correction():
    fm = C.load_json(FINAL_METRICS)
    gpu = C.load_json(FINAL_GPU)
    lab = C.load_json(LABELED_CORR)
    syn_b = fm["section_A_synthetic"]["correction_bare"]
    syn_l = fm["section_A_synthetic"]["correction_labeled"]
    cum = fm["section_D_correction_safety_cumulative"]

    rows = [
        {"population": "Synthetic stress — baseline (bare premise)",
         "system": "baseline", "population_type": "synthetic",
         "candidate_claims": syn_b["n_cases"], "correction_triggered": syn_b["correction_triggers"],
         "scope_gate_rejected": syn_b["correction_scope_violation"],
         "reverification_not_entailed": syn_b["correction_failed"],
         "shipped": syn_b["corrections_shipped_success"],
         "unsafe_shipped": syn_b["unsafe_corrections_shipped"],
         "fresh_or_historical": "HISTORICAL (GPU)", "source_artifact": C.rel(FINAL_METRICS)},
        {"population": "Synthetic stress — modified (labeled premise)",
         "system": "modified", "population_type": "synthetic",
         "candidate_claims": syn_l["n_cases"], "correction_triggered": syn_l["correction_triggers"],
         "scope_gate_rejected": syn_l["correction_scope_violation"],
         "reverification_not_entailed": syn_l["correction_failed"],
         "shipped": syn_l["corrections_shipped_success"],
         "unsafe_shipped": syn_l["unsafe_corrections_shipped"],
         "fresh_or_historical": "HISTORICAL (GPU)", "source_artifact": C.rel(FINAL_METRICS)},
        {"population": "Natural targeted — baseline framing (Arm B, bare)",
         "system": "baseline", "population_type": "natural",
         "candidate_claims": gpu["per_arm"]["B"]["n_claims"],
         "correction_triggered": gpu["per_arm"]["B"]["correction_triggers"],
         "scope_gate_rejected": gpu["per_arm"]["B"]["correction_scope_violation"],
         "reverification_not_entailed": gpu["per_arm"]["B"]["correction_failed"],
         "shipped": gpu["per_arm"]["B"]["corrections_shipped_success"],
         "unsafe_shipped": gpu["per_arm"]["B"]["unsafe_corrections_shipped"],
         "fresh_or_historical": "HISTORICAL (GPU); exactly reproduced STEP 10B",
         "source_artifact": C.rel(FINAL_GPU)},
        {"population": "Natural targeted — modified framing (labeled)",
         "system": "modified", "population_type": "natural",
         "candidate_claims": gpu["per_arm"]["B"]["n_claims"],
         "correction_triggered": lab["n_cases_triggered"],
         "scope_gate_rejected": lab["status_counts"].get("correction_scope_violation", 0),
         "reverification_not_entailed": lab["status_counts"].get("correction_failed", 0),
         "shipped": lab["corrections_shipped"], "unsafe_shipped": lab["unsafe_shipped"],
         "fresh_or_historical": "HISTORICAL (GPU); exactly reproduced STEP 10",
         "source_artifact": C.rel(LABELED_CORR)},
        {"population": "Natural cumulative — all correction attempts, project history",
         "system": "cumulative", "population_type": "natural",
         "candidate_claims": "NOT TRACKED as a single denominator",
         "correction_triggered": cum["total_correction_attempts"],
         "scope_gate_rejected": cum["status_breakdown"]["correction_scope_violation"],
         "reverification_not_entailed": cum["status_breakdown"]["correction_failed"],
         "shipped": cum["total_shipped"], "unsafe_shipped": cum["total_unsafe_shipped"],
         "fresh_or_historical": "HISTORICAL-ONLY (protocol insufficient to reproduce)",
         "source_artifact": C.rel(FINAL_METRICS)},
    ]
    emit("M13_correction_funnel.csv", list(rows[0].keys()), rows,
         "Correction funnel stage counts, five populations kept strictly separate",
         [FINAL_METRICS, FINAL_GPU, LABELED_CORR],
         "synthetic + natural targeted + natural cumulative", "59 / 209 / 56",
         "HISTORICAL (GPU-dependent)", "C",
         "Synthetic and natural populations must never be pooled into one rate. "
         "The natural cumulative denominator is a project-history rollup, not one experiment.")

    out_rows = []
    for r in rows:
        trig = r["correction_triggered"]
        out_rows.append({
            "population": r["population"], "system": r["system"],
            "n_triggered": trig, "shipped": r["shipped"],
            "reverification_not_entailed": r["reverification_not_entailed"],
            "scope_gate_rejected": r["scope_gate_rejected"],
            "shipped_rate": (r["shipped"] / trig) if trig else "",
            "fresh_or_historical": r["fresh_or_historical"],
            "source_artifact": r["source_artifact"],
        })
    emit("M14_correction_outcomes.csv", list(out_rows[0].keys()), out_rows,
         "Shipped / re-verification-failed / scope-rejected split per population",
         [FINAL_METRICS, FINAL_GPU, LABELED_CORR],
         "synthetic + natural targeted + natural cumulative", "59 / 209 / 56",
         "HISTORICAL (GPU-dependent)", "C",
         "0/5 -> 1/10 is a directional, isolated-by-design shift, not a statistically "
         "supported rate.")

    saf = [
        {"safety_observation": "Unsafe corrections shipped",
         "count": cum["total_unsafe_shipped"],
         "denominator": "122 correction attempts (56 natural + 66 synthetic)",
         "mechanism": "ENTAILED-only shipping gate + scope gate + sibling-regression net",
         "source_artifact": C.rel(FINAL_METRICS)},
        {"safety_observation": "Scope-gate rejections (natural, cumulative)",
         "count": cum["status_breakdown"]["correction_scope_violation"],
         "denominator": "56 natural correction attempts",
         "mechanism": "pipeline._scope_violation()",
         "source_artifact": C.rel(FINAL_METRICS)},
        {"safety_observation": "Re-verification-not-ENTAILED rejections (natural, cumulative)",
         "count": cum["status_breakdown"]["correction_failed"],
         "denominator": "56 natural correction attempts",
         "mechanism": "ENTAILED-only shipping gate",
         "source_artifact": C.rel(FINAL_METRICS)},
        {"safety_observation": "Sibling-regression rejections observed (209-claim paired, Arm B)",
         "count": gpu["per_arm"]["B"]["correction_sibling_regression"],
         "denominator": "5 correction attempts",
         "mechanism": "pipeline._reverify_sibling_regressions()",
         "source_artifact": C.rel(FINAL_GPU)},
        {"safety_observation": "Corrections shipped (natural, cumulative)",
         "count": cum["total_shipped"], "denominator": "56 natural correction attempts",
         "mechanism": "passed every gate",
         "source_artifact": C.rel(FINAL_METRICS)},
    ]
    emit("M15_safety_observations.csv", list(saf[0].keys()), saf,
         "Observed counts for each programmatic safety mechanism",
         [FINAL_METRICS, FINAL_GPU], "all tested correction attempts", "122",
         "HISTORICAL", "n/a (observed counts)",
         "0 observed unsafe shipments is an observation on a finite tested history, "
         "not a proof that unsafe shipments are impossible.")


# ==========================================================================
# M16 / M25 — ablation matrix and scope-gate replay
# ==========================================================================
def m16_ablation():
    findings = C.load_json(ABLATION)["findings"]
    grade_by_factor = {
        "evidence_v1": "A", "premise_framing": "A", "claim_parser_fix": "B",
        "confidence_threshold": "B", "atomic_scope_check_assertion_spans": "C",
        "narrow_reverification_hypothesis": "C",
        "correction_levers_combined (premise_framing isolated within an otherwise-fixed config)": "C",
        "joint_four_lever_isolation": "E",
    }
    rows = []
    for f in findings:
        rows.append({
            "factor": f["factor"],
            "baseline_setting": f.get("baseline"),
            "modified_setting": f.get("variant"),
            "dataset": f.get("dataset"),
            "n": f.get("n") if f.get("n") is not None else "",
            "primary_metric": f.get("primary_metric") or "",
            "baseline_value": f.get("baseline_value") if f.get("baseline_value") is not None else "",
            "variant_value": f.get("variant_value") if f.get("variant_value") is not None else "",
            "statistical_test": f.get("statistical_test") or "",
            "p_value": f.get("p_value") if f.get("p_value") is not None else "",
            "classification": f["classification"],
            "fresh_or_historical": f["fresh_or_historical"],
            "evidence_grade": grade_by_factor.get(f["factor"], ""),
            "safe_claim": f.get("safe_claim", ""),
            "prohibited_claim": f.get("prohibited_claim", ""),
            "source_artifact": C.rel(ABLATION),
        })
    emit("M16_ablation_matrix.csv", list(rows[0].keys()), rows,
         "All eight ablation factors with evidence grade, isolation status and statistics",
         [ABLATION, C.EVAL_METRICS / "EVIDENCE_STRENGTH_MATRIX.csv"],
         "8 named ablation factors", "varies (3-420)", "MIXED", "A-E",
         "Grade communicates evidence strength (isolation + n + statistical support), "
         "not effect size. Grade E = the experiment does not exist.")

    sr = C.load_json(SCOPE_REPLAY)
    rows2 = [
        {"scope_check_mode": "atomic_scope_check=false (baseline, full-sentence rule)",
         "system": "baseline", "n_replayed": sr["n_scope_violations_replayed"],
         "n_blocked": sr["n_scope_violations_replayed"], "n_unblocked": 0,
         "source_artifact": C.rel(SCOPE_REPLAY)},
        {"scope_check_mode": 'atomic_scope_check="assertion_spans" (modified)',
         "system": "modified", "n_replayed": sr["n_scope_violations_replayed"],
         "n_blocked": sr["n_scope_violations_replayed"] - sr["n_unblocked_final"],
         "n_unblocked": sr["n_unblocked_final"],
         "source_artifact": C.rel(SCOPE_REPLAY)},
    ]
    emit("M25_scope_gate_replay.csv", list(rows2[0].keys()), rows2,
         "Deterministic scope-gate replay over 11 real historical scope violations",
         [SCOPE_REPLAY], "11 real historical scope-violation correction attempts", "11",
         "FRESH REPRODUCTION (CPU)", "C",
         "The replay stops at the scope gate. Whether the one unblocked case would "
         "actually ship an ENTAILED correction is NOT answered by this artifact.")


# ==========================================================================
# M17 — runtime / resource
# ==========================================================================
def m17_runtime():
    fm = C.load_json(FINAL_METRICS)
    gpu = C.load_json(FINAL_GPU)
    g1 = C.load_json(GOLD01)
    fresh209 = C.load_json(GPU_209_FRESH)
    lab = C.load_json(LABELED_CORR)
    freshcorr = C.load_json(GPU_CORR_FRESH)
    syn = fm["section_A_synthetic"]
    rows = [
        {"arm": "209-claim paired generation experiment (total)",
         "runtime_seconds": gpu["runtime_seconds_total"],
         "peak_vram_mib": gpu.get("peak_vram_mib", ""), "n_cases": gpu["n_cases"],
         "hardware": "NVIDIA GPU (RTX 4050 Laptop class, 6GB)",
         "fresh_or_historical": "HISTORICAL (GPU)", "source_artifact": C.rel(FINAL_GPU)},
        {"arm": "209-claim paired generation experiment (total), STEP 10B reproduction",
         "runtime_seconds": fresh209.get("runtime_seconds_total", ""),
         "peak_vram_mib": fresh209.get("peak_vram_mib", ""), "n_cases": fresh209.get("n_cases", ""),
         "hardware": "NVIDIA GPU (second machine)",
         "fresh_or_historical": "FRESH GPU REPRODUCTION (STEP 10B)",
         "source_artifact": C.rel(GPU_209_FRESH)},
        {"arm": "Synthetic correction, baseline (bare premise)",
         "runtime_seconds": syn["correction_bare"]["runtime_seconds_total_arm"],
         "peak_vram_mib": syn["correction_bare"]["peak_vram_mib_cumulative"],
         "n_cases": syn["correction_bare"]["n_cases"],
         "hardware": "NVIDIA GPU", "fresh_or_historical": "HISTORICAL (GPU)",
         "source_artifact": C.rel(FINAL_METRICS)},
        {"arm": "Synthetic correction, modified (labeled premise)",
         "runtime_seconds": syn["correction_labeled"]["runtime_seconds_total_arm"],
         "peak_vram_mib": syn["correction_labeled"]["peak_vram_mib_cumulative"],
         "n_cases": syn["correction_labeled"]["n_cases"],
         "hardware": "NVIDIA GPU", "fresh_or_historical": "HISTORICAL (GPU)",
         "source_artifact": C.rel(FINAL_METRICS)},
        {"arm": "Targeted labeled-framing correction validation",
         "runtime_seconds": lab["runtime_seconds"], "peak_vram_mib": "",
         "n_cases": lab["n_cases_triggered"], "hardware": "NVIDIA GPU",
         "fresh_or_historical": "HISTORICAL (GPU)", "source_artifact": C.rel(LABELED_CORR)},
        {"arm": "Targeted labeled-framing correction validation, STEP 10 reproduction",
         "runtime_seconds": freshcorr.get("runtime_seconds", ""), "peak_vram_mib": "",
         "n_cases": freshcorr.get("n_cases_triggered", ""), "hardware": "NVIDIA GPU (second machine)",
         "fresh_or_historical": "FRESH GPU REPRODUCTION (STEP 10)",
         "source_artifact": C.rel(GPU_CORR_FRESH)},
        {"arm": "GOLD-01 verifier benchmark, modified framing (CPU)",
         "runtime_seconds": g1["results_by_framing"]["labeled"]["elapsed_seconds"],
         "peak_vram_mib": "N/A (CPU)", "n_cases": g1["n_items"],
         "hardware": "CPU only", "fresh_or_historical": "FRESH (CPU)",
         "source_artifact": C.rel(GOLD01)},
        {"arm": "GOLD-01 verifier benchmark, baseline framing (CPU)",
         "runtime_seconds": g1["results_by_framing"]["bare"]["elapsed_seconds"],
         "peak_vram_mib": "N/A (CPU)", "n_cases": g1["n_items"],
         "hardware": "CPU only", "fresh_or_historical": "FRESH (CPU)",
         "source_artifact": C.rel(GOLD01)},
    ]
    emit("M17_runtime_resource.csv", list(rows[0].keys()), rows,
         "Wall-clock runtime and peak VRAM per experiment arm, GPU and CPU rows separated",
         [FINAL_GPU, FINAL_METRICS, GOLD01, GPU_209_FRESH, GPU_CORR_FRESH],
         "mixed experiment arms", "50 / 59 / 10 / 420", "MIXED (GPU historical + fresh; CPU fresh)",
         "n/a (resource measure)",
         "Wall-clock time is a hardware/thermal/load measure, not a correctness measure. "
         "GPU and CPU arms are never compared as if equivalent.")


# ==========================================================================
# M18 / M19 / M20 / M21 — regimes, transfer, evidence gaps, parser fix
# ==========================================================================
def m18_m19_m20_m21():
    b = C.load_json(BATCHES)["batches"]
    p = C.load_json(PAIRED209)
    c588 = C.load_json(CLAIMS588)
    rows = []
    for d in b:
        rows.append({
            "regime": d["name"], "configuration": d["configuration"],
            "n_cases": d["n_cases"], "n_claims": d["n_claims"],
            "n_evidence_matched": d["n_evidence_matched"],
            "evidence_coverage": d["evidence_coverage"],
            "fresh_or_historical": "HISTORICAL", "source_artifact": C.rel(BATCHES),
        })
    rows.append({"regime": "209_paired_ArmA", "configuration": "evidence pool v0 (59), labeled re-verification",
                 "n_cases": 50, "n_claims": p["n_paired_claims"],
                 "n_evidence_matched": p["evidence_change_counts"]["unchanged_matched"],
                 "evidence_coverage": p["fresh_evidence_coverage_arm_A"],
                 "fresh_or_historical": "FRESH", "source_artifact": C.rel(PAIRED209)})
    rows.append({"regime": "209_paired_ArmB", "configuration": "evidence pool v0+v1 (136), labeled",
                 "n_cases": 50, "n_claims": p["n_paired_claims"],
                 "n_evidence_matched": p["evidence_change_counts"]["unchanged_matched"]
                                       + p["evidence_change_counts"]["evidence_gained"],
                 "evidence_coverage": p["fresh_evidence_coverage_arm_B"],
                 "fresh_or_historical": "FRESH", "source_artifact": C.rel(PAIRED209)})
    rows.append({"regime": "588_claim_aggregate", "configuration": "evidence pool v0+v1 (136), labeled",
                 "n_cases": c588["n_distinct_texts"], "n_claims": c588["n_claims"],
                 "n_evidence_matched": c588["n_evidence_matched"],
                 "evidence_coverage": c588["evidence_coverage"],
                 "fresh_or_historical": "FRESH", "source_artifact": C.rel(CLAIMS588)})
    emit("M18_natural_regimes_coverage.csv", list(rows[0].keys()), rows,
         "Observed evidence coverage across every natural-data regime, never pooled",
         [BATCHES, PAIRED209, CLAIMS588], "11 natural-data regimes", "29-588 per regime",
         "MIXED (3 FRESH, 8 HISTORICAL)", "n/a (descriptive)",
         "Regimes differ in case selection and configuration; the spread is not a trend.")

    fm = C.load_json(FINAL_METRICS)
    gap = fm["synthetic_vs_natural_correction_transfer_gap"]
    syn_l = fm["section_A_synthetic"]["correction_labeled"]
    cum = fm["section_D_correction_safety_cumulative"]
    rows2 = [
        {"population": "Synthetic stress set (labeled framing)",
         "population_type": "synthetic (contradictory by construction)",
         "shipped": syn_l["corrections_shipped_success"],
         "triggered": syn_l["correction_triggers"],
         "shipped_rate_pct": gap["synthetic_labeled_shipped_rate_pct"],
         "comparable_to_other_rows": "NO", "source_artifact": C.rel(FINAL_METRICS)},
        {"population": "Natural data, all regimes (project history)",
         "population_type": "natural (no correctness label)",
         "shipped": cum["total_shipped"], "triggered": cum["total_correction_attempts"],
         "shipped_rate_pct": gap["natural_all_regimes_shipped_rate_pct"],
         "comparable_to_other_rows": "NO", "source_artifact": C.rel(FINAL_METRICS)},
        {"population": "Natural data, modified production regime (targeted)",
         "population_type": "natural (no correctness label)",
         "shipped": 1, "triggered": 10,
         "shipped_rate_pct": gap["natural_final_production_regime_shipped_rate_pct"],
         "comparable_to_other_rows": "NO", "source_artifact": C.rel(FINAL_METRICS)},
    ]
    emit("M19_synthetic_vs_natural_transfer.csv", list(rows2[0].keys()), rows2,
         "Synthetic vs natural correction shipping rates, explicitly marked non-equivalent",
         [FINAL_METRICS], "synthetic stress vs natural corpus", "36 / 56 / 10",
         "HISTORICAL (GPU)", "D",
         "Disjoint populations with different base rates by construction. 72.2% and 1.8% "
         "do NOT measure the same capability and must never be plotted as a single trend.")

    tax = C.load_json(NOEV_TAXONOMY)
    labels = {
        "genuinely_absent_no_such_provision_any_act":
            "Provision genuinely absent from the evidence corpus",
        "genuinely_absent_wrong_act_or_edition":
            "Cited act/edition not in corpus (anaphora, superseded edition)",
        "unresolved_act": "Act name could not be resolved from the sentence",
        "parser_or_matcher_defect_candidate":
            "Parser/matcher defect candidate (both manually confirmed correct)",
    }
    rows3 = [{"bucket_key": k, "bucket_label": labels[k], "count": v,
              "n_no_evidence_with_citation": tax["n_no_evidence_with_citation"],
              "n_claims_total": tax["n_claims"], "n_matched_total": tax["n_matched"],
              "source_artifact": C.rel(NOEV_TAXONOMY)}
             for k, v in tax["taxonomy"].items()]
    emit("M20_no_evidence_taxonomy.csv", list(rows3[0].keys()), rows3,
         "Why claims resolve to NO_EVIDENCE, across all 797 claims in project history",
         [NOEV_TAXONOMY], "797 pooled claims from every natural experiment", "797 (260 NO_EVIDENCE)",
         "HISTORICAL (audit re-run)", "B",
         "A NO_EVIDENCE claim is not shown to be wrong — the corpus is ~140 provisions "
         "and most citations simply fall outside it.")

    pf = C.load_json(PARSER_FIX)
    abl = {f["factor"]: f for f in C.load_json(ABLATION)["findings"]}["claim_parser_fix"]
    t = pf["totals"]
    rows4 = [
        {"measure": "Claims extracted", "baseline_pre_fix_parser": t["old_claims"],
         "modified_post_fix_parser": t["new_claims"], "n_cases": abl["n"],
         "statistical_test": "", "p_value": "", "source_artifact": C.rel(PARSER_FIX)},
        {"measure": "Claims with usable evidence", "baseline_pre_fix_parser": t["old_with_evidence"],
         "modified_post_fix_parser": t["new_with_evidence"], "n_cases": abl["n"],
         "statistical_test": "", "p_value": "", "source_artifact": C.rel(PARSER_FIX)},
        {"measure": "Claims with unresolved act name", "baseline_pre_fix_parser": t["old_unresolved_act"],
         "modified_post_fix_parser": t["new_unresolved_act"], "n_cases": abl["n"],
         "statistical_test": "", "p_value": "", "source_artifact": C.rel(PARSER_FIX)},
        {"measure": "Per-case outcome (improved / worsened / unchanged)",
         "baseline_pre_fix_parser": f"{abl['cases_worsened']} cases worsened",
         "modified_post_fix_parser": f"{abl['cases_improved']} improved, {abl['cases_unchanged']} unchanged",
         "n_cases": abl["n"], "statistical_test": abl["statistical_test"],
         "p_value": abl["p_value"], "source_artifact": C.rel(ABLATION)},
    ]
    emit("M21_parser_fix_n30.csv", list(rows4[0].keys()), rows4,
         "Claim-parser fix (commit 223eb9d) re-parse of the same 30 generated texts",
         [PARSER_FIX, ABLATION], "n30_reparse", "30 cases / 88 vs 93 claims",
         "HISTORICAL REPRODUCTION (code change not re-executed; statistic recomputed fresh)",
         "B",
         "This is a code-version ablation, not a configuration ablation, and is measured "
         "separately from the four production levers.")


# ==========================================================================
# M22 / M23 / M24 — reproduction crosscheck, component tests, evidence pool
# ==========================================================================
def m22_m23_m24():
    hist = C.load_json(FINAL_GPU)
    fresh = C.load_json(GPU_209_FRESH)
    lh, lf = C.load_json(LABELED_CORR), C.load_json(GPU_CORR_FRESH)
    src209 = f"{C.rel(FINAL_GPU)} ; {C.rel(GPU_209_FRESH)}"
    srccorr = f"{C.rel(LABELED_CORR)} ; {C.rel(GPU_CORR_FRESH)}"
    rows = []
    for arm in ("A", "B"):
        for qty, key in (("claims evidence-matched", "n_claims_evidence_matched"),
                         ("correction triggers", "correction_triggers"),
                         ("corrections shipped", "corrections_shipped_success"),
                         ("unsafe corrections shipped", "unsafe_corrections_shipped")):
            hv = hist["per_arm"][arm][key]
            fv = fresh["per_arm"][arm][key]
            rows.append({
                "experiment": f"209-claim paired generation, Arm {arm}",
                "quantity": qty, "historical_value": hv, "fresh_value": fv,
                "match": hv == fv, "source_artifact": src209})
    rows.append({"experiment": "Targeted labeled-framing correction validation",
                 "quantity": "cases triggered",
                 "historical_value": lh["n_cases_triggered"],
                 "fresh_value": lf["n_cases_triggered"],
                 "match": lh["n_cases_triggered"] == lf["n_cases_triggered"],
                 "source_artifact": srccorr})
    rows.append({"experiment": "Targeted labeled-framing correction validation",
                 "quantity": "corrections shipped",
                 "historical_value": lh["corrections_shipped"],
                 "fresh_value": lf["corrections_shipped"],
                 "match": lh["corrections_shipped"] == lf["corrections_shipped"],
                 "source_artifact": srccorr})
    rows.append({"experiment": "Targeted labeled-framing correction validation",
                 "quantity": "unsafe corrections shipped",
                 "historical_value": lh["unsafe_shipped"],
                 "fresh_value": lf["unsafe_shipped"],
                 "match": lh["unsafe_shipped"] == lf["unsafe_shipped"],
                 "source_artifact": srccorr})
    emit("M22_gpu_reproduction_crosscheck.csv", list(rows[0].keys()), rows,
         "Historical vs freshly-reproduced GPU experiment values (STEP 10 / 10B)",
         [FINAL_GPU, GPU_209_FRESH, LABELED_CORR, GPU_CORR_FRESH],
         "209-claim paired + 10-case targeted correction", "209 / 10",
         "FRESH GPU REPRODUCTION vs HISTORICAL", "A (reproducibility only)",
         "Exact reproduction under greedy decoding evidences pipeline stability across "
         "machines. It adds no new statistical evidence about legal correctness.")

    comp = C.read_csv(COMPONENT_MATRIX)
    for r in comp:
        r["source_artifact"] = C.rel(COMPONENT_MATRIX)
    emit("M23_component_test_matrix.csv", list(comp[0].keys()), comp,
         "Per-component test counts and representative behaviour cases",
         [COMPONENT_MATRIX], "research/prototype/tests/", "205 authoritative total",
         "FRESH (re-run for this package: 205 passed)", "n/a (software behaviour)",
         "Per-component counts overlap where tests span stages; 205 is the only "
         "authoritative non-duplicated total — never sum the component rows.")

    sys.path.insert(0, str(C.PROTO_DIR))
    from src.data_loader import load_usable_evidence_from_config  # noqa: E402
    cfg_mod = C.load_current_config()
    cfg_base = copy.deepcopy(cfg_mod)
    cfg_base["use_evidence_v1"] = False
    _, all_mod = load_usable_evidence_from_config(cfg_mod, C.REPO_ROOT)
    _, all_base = load_usable_evidence_from_config(cfg_base, C.REPO_ROOT)
    v0_file = sum(1 for line in (C.REPO_ROOT / cfg_mod["paths"]["canonical_statutes"]).open(
        encoding="utf-8") if line.strip())
    v1_file = sum(1 for line in (C.REPO_ROOT / cfg_mod["paths"]["canonical_statutes_v1"]).open(
        encoding="utf-8") if line.strip())
    loader_src = (f"{C.rel(C.CONFIG_YAML)} ; "
                  "research/prototype/src/data_loader.py::load_usable_evidence_from_config")
    rows3 = [
        {"system": "baseline", "system_label": C.BASELINE_LABEL_1L,
         "use_evidence_v1": False, "records_in_v0_file": v0_file, "records_in_v1_file": 0,
         "usable_records_loaded": len(all_base),
         "usable_verdicts": "|".join(cfg_mod["usable_evidence_verdicts"]),
         "source_artifact": loader_src},
        {"system": "modified", "system_label": C.MODIFIED_LABEL_1L,
         "use_evidence_v1": True, "records_in_v0_file": v0_file, "records_in_v1_file": v1_file,
         "usable_records_loaded": len(all_mod),
         "usable_verdicts": "|".join(cfg_mod["usable_evidence_verdicts"]),
         "source_artifact": loader_src},
    ]
    emit("M24_evidence_pool_composition.csv", list(rows3[0].keys()), rows3,
         "Usable canonical-evidence pool size for each system, loaded live from source",
         [C.CONFIG_YAML], "research/data/evidence/", "59 vs 136 usable records",
         "FRESH (computed live via the unmodified production loader)", "A",
         "Only VERIFIED_EXACT / VERIFIED_CONTENT audit verdicts are usable; "
         "SOURCE_ONLY / INVALID / UNRESOLVED are excluded by design.")


def main() -> None:
    C.OUT_METRICS.mkdir(parents=True, exist_ok=True)
    print("Building locked figure-data CSVs ...")
    m01_headline()
    m02_m03_m04_gold01()
    m05_gold02()
    m06_m07_evidence()
    m08_m09_m10_verdicts()
    m11_m12_confidence()
    m13_m14_m15_correction()
    m16_ablation()
    m17_runtime()
    m18_m19_m20_m21()
    m22_m23_m24()
    C.write_csv(C.PKG_DIR / "METRIC_SOURCE_MAP.csv", list(SOURCE_MAP[0].keys()), SOURCE_MAP)
    print(f"\nWrote METRIC_SOURCE_MAP.csv ({len(SOURCE_MAP)} metric contracts)")


if __name__ == "__main__":
    main()
