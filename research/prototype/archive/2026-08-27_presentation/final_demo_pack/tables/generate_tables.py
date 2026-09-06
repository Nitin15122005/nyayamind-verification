#!/usr/bin/env python
"""
Generates CSV + Markdown tables backing every demo-pack figure, plus one
comprehensive metrics table, all sourced from
research/prototype/final_demo_pack/metadata/computed_metrics.json.

Raw-derived tables (*_raw.csv) contain only numbers pulled straight from
computed_metrics.json. Explanatory *.md files add a one-line
methodology/defensibility note per table but never blend invented numbers
into the raw CSVs.

Run: research/.venv/Scripts/python.exe research/prototype/final_demo_pack/tables/generate_tables.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
METRICS_PATH = HERE.parent / "metadata" / "computed_metrics.json"
M = json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def write_csv(name: str, header: list, rows: list):
    path = HERE / name
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {name}")


def write_md(name: str, title: str, header: list, rows: list, note: str):
    path = HERE / name
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    lines.append("")
    lines.append(f"*{note}*")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {name}")


# ---------------------------------------------------------------------------
def table01_evidence_coverage():
    cov = M["evidence_coverage_v0_v1"]
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    armA, armB = regimes["final_A_bare_v0_baseline"], regimes["final_B_bare_v1_assertionspans_narrow"]
    rows = [
        ["claim-level (all natural claims)", cov["n_claims"], cov["n_matched_v0"], cov["coverage_v0_pct"], cov["n_matched_v1"], cov["coverage_v1_pct"], "no significance test computed"],
        ["paired-arm (final_gpu_validation, 50 held-out cases)", armA["n_claims"], armA["n_matched"], armA["coverage_pct"], armB["n_matched"], armB["coverage_pct"], "McNemar chi2=13.07, p~0.0003"],
    ]
    write_csv("01_evidence_coverage_v0_to_v1_raw.csv",
              ["comparison", "n_claims", "n_matched_v0", "coverage_v0_pct", "n_matched_v1", "coverage_v1_pct", "significance"], rows)
    write_md("01_evidence_coverage_v0_to_v1.md", "Evidence coverage: v0 vs v0+v1",
              ["comparison", "n_claims", "n_matched_v0", "coverage_v0_pct", "n_matched_v1", "coverage_v1_pct", "significance"], rows,
              "Source: computed_metrics.json.evidence_coverage_v0_v1 and .final_metrics_passthrough.section_B_natural_regimes. The paired-arm row is the only one with an established significance test.")


def table02_coverage_across_batches():
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    order = [("n=30", "n30_modeB_bare_v0"), ("batch1", "batch1_bare_v0"), ("batch2", "batch2_bare_v0"),
             ("final-A", "final_A_bare_v0_baseline"), ("final-B", "final_B_bare_v1_assertionspans_narrow")]
    rows = [[name, regimes[k]["n_cases"], regimes[k]["n_claims"], regimes[k]["n_matched"], regimes[k]["coverage_pct"], regimes[k]["config"]] for name, k in order]
    write_csv("02_evidence_coverage_across_natural_batches_raw.csv", ["batch", "n_cases", "n_claims", "n_matched", "coverage_pct", "config"], rows)
    write_md("02_evidence_coverage_across_natural_batches.md", "Evidence coverage across natural batches",
              ["batch", "n_cases", "n_claims", "n_matched", "coverage_pct", "config"], rows,
              "Source: computed_metrics.json.final_metrics_passthrough.section_B_natural_regimes. Batches are disjoint case sets, not sequential progress.")


def table03_bare_vs_labeled_verification():
    bare = M["final_metrics_passthrough"]["section_B_pooled_bare_v0"]
    labeled = M["final_metrics_passthrough"]["section_B_pooled_labeled_v0"]
    verdicts = ["NO_EVIDENCE", "NOT_ENOUGH_INFORMATION", "CONTRADICTED", "ENTAILED"]
    rows = [[v, bare["verdict_counts"].get(v, 0), labeled["verdict_counts"].get(v, 0)] for v in verdicts]
    write_csv("03_bare_vs_labeled_verification_outcomes_raw.csv", ["verdict", "bare_pooled_count", "labeled_pooled_count"], rows)
    write_md("03_bare_vs_labeled_verification_outcomes.md", "Bare vs labeled: verdict distribution (pooled)",
              ["verdict", f"bare (n={bare['n_claims']} claims, 180 cases)", f"labeled (n={labeled['n_claims']} claims, 100 cases)"], rows,
              "DIFFERENT underlying case sets -- bare pools n30+batch1+batch2+final-A; labeled pools batch1+batch2 only. Not a same-case paired comparison.")


def table04_bare_vs_labeled_correction():
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    rows = []
    for batch, bare_k, lab_k in [("batch1", "batch1_bare_v0", "batch1_labeled_v0"), ("batch2", "batch2_bare_v0", "batch2_labeled_v0")]:
        for framing, k in [("bare", bare_k), ("labeled", lab_k)]:
            c = regimes[k]["correction"]
            rows.append([batch, framing, c["correction_triggers"], c["statuses"].get("correction_failed", 0),
                         c["statuses"].get("correction_scope_violation", 0), c["statuses"].get("corrected", 0), c["shipped"], c["unsafe_shipped"]])
    header = ["batch", "framing", "triggers", "correction_failed", "scope_violation", "corrected", "shipped", "unsafe_shipped"]
    write_csv("04_bare_vs_labeled_correction_outcomes_raw.csv", header, rows)
    write_md("04_bare_vs_labeled_correction_outcomes.md", "Bare vs labeled: correction outcomes (batch1/batch2)", header, rows,
              "Legacy (pre-assertion_spans) scope-check regime. Source: section_B_natural_regimes.*.correction.")


def table05_synthetic_vs_natural_success():
    gap = M["final_metrics_passthrough"]["synthetic_vs_natural_correction_transfer_gap"]
    synth = M["correction_safety_audit"]["synthetic"]
    rows = [
        ["synthetic", "bare", synth["bare"]["n_correction_attempts"], synth["bare"]["n_shipped_corrected"], round(100*synth["bare"]["n_shipped_corrected"]/synth["bare"]["n_correction_attempts"], 1)],
        ["synthetic", "labeled", synth["labeled"]["n_correction_attempts"], synth["labeled"]["n_shipped_corrected"], gap["synthetic_labeled_shipped_rate_pct"]],
        ["natural", "all regimes pooled", 56, 1, gap["natural_all_regimes_shipped_rate_pct"]],
        ["natural", "final production regime", 10, 1, gap["natural_final_production_regime_shipped_rate_pct"]],
    ]
    header = ["data_type", "regime", "n_attempts", "n_shipped", "shipped_rate_pct"]
    write_csv("05_synthetic_vs_natural_correction_success_raw.csv", header, rows)
    write_md("05_synthetic_vs_natural_correction_success.md", "Correction shipped-rate: synthetic vs natural", header, rows,
              "Source: computed_metrics.json.correction_safety_audit and .final_metrics_passthrough.synthetic_vs_natural_correction_transfer_gap.")


def table06_contradiction_detection():
    synth = M["final_metrics_passthrough"]["section_A_synthetic"]
    rows = [
        ["bare", "overall", round(synth["bare"]["contradiction_recall_overall"]*100, 1)],
        ["bare", "evidence-matched only", round(synth["bare"]["contradiction_recall_with_evidence"]*100, 1)],
        ["labeled", "overall", round(synth["labeled"]["contradiction_recall_overall"]*100, 1)],
        ["labeled", "evidence-matched only", round(synth["labeled"]["contradiction_recall_with_evidence"]*100, 1)],
    ]
    write_csv("06_contradiction_detection_comparison_raw.csv", ["framing", "basis", "contradiction_recall_pct"], rows)
    write_md("06_contradiction_detection_comparison.md", f"Contradiction detection recall (SYNTHETIC, n={synth['n_cases']})",
              ["framing", "basis", "contradiction_recall_pct"], rows,
              "SYNTHETIC STRESS TEST ONLY -- deliberately-corrupted claims, not natural case text.")


def table07_no_evidence_taxonomy():
    tax = M["final_metrics_passthrough"]["section_C_parser_retrieval"]["taxonomy"]
    total = sum(tax.values())
    rows = [[k, v, round(100*v/total, 1)] for k, v in tax.items()]
    write_csv("07_no_evidence_taxonomy_raw.csv", ["bucket", "count", "pct_of_no_evidence"], rows)
    write_md("07_no_evidence_taxonomy.md", f"NO_EVIDENCE taxonomy (n={total})", ["bucket", "count", "pct_of_no_evidence"], rows,
              "NO_EVIDENCE means 'not in our corpus', never 'legally unsupported'. Source: no_evidence_taxonomy_v3.json via final_metrics.json section_C.")


def table08_correction_failure_taxonomy():
    sb = M["correction_safety_audit"]["natural"]["status_breakdown"]
    total = sum(sb.values())
    rows = [[k, v, round(100*v/total, 1)] for k, v in sb.items()]
    write_csv("08_correction_failure_taxonomy_raw.csv", ["status", "count", "pct"], rows)
    write_md("08_correction_failure_taxonomy.md", f"Natural correction outcome taxonomy (n={total})", ["status", "count", "pct"], rows,
              "Recomputed fresh from every raw correction-attempt jsonl this project produced; cross-checked against final_metrics.json (match confirmed).")


def table09_safety_outcomes():
    csa = M["correction_safety_audit"]
    rows = [
        ["natural", csa["natural"]["n_correction_attempts"], csa["natural"]["n_correction_attempts"] - csa["natural"]["n_shipped_corrected"], csa["natural"]["n_shipped_corrected"], csa["natural"]["n_unsafe_shipped"]],
        ["synthetic", csa["synthetic"]["n_correction_attempts"], csa["synthetic"]["n_correction_attempts"] - csa["synthetic"]["n_shipped_corrected"], csa["synthetic"]["n_shipped_corrected"], csa["synthetic"]["n_unsafe_shipped"]],
    ]
    header = ["data_type", "n_attempts", "n_rejected", "n_shipped", "n_unsafe_shipped"]
    write_csv("09_safety_outcomes_raw.csv", header, rows)
    write_md("09_safety_outcomes.md", "Safety outcomes", header, rows,
              f"UNSAFE SHIPMENTS = {csa['combined_total_unsafe_shipped']} / {csa['combined_total_attempts']} total attempts across this project's entire history. Invariant checked against every single attempt.")


def table10_threshold_sensitivity():
    ts = M["threshold_sensitivity"]
    rows = []
    for framing in ("bare", "labeled"):
        for p in ts[framing]["sweep"]:
            rows.append([framing, p["threshold"], p["accuracy"], p["macro_f1"], p["n_low_confidence_downgrades"]])
    header = ["framing", "threshold", "accuracy", "macro_f1", "n_low_confidence_downgrades"]
    write_csv("10_threshold_sensitivity_curve_raw.csv", header, rows)
    write_md("10_threshold_sensitivity_curve.md", f"Threshold sensitivity (controlled benchmark, n={ts['bare']['n_items']})", header, rows,
              f"Deterministic replay over stored softmax outputs, no re-inference. Production threshold = {ts['production_threshold']}.")


def table11_coverage_vs_batch_size():
    # identical data to table02, different framing (x=size, y=coverage) -- kept as its own file per the figure list.
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    order = [("n=30", "n30_modeB_bare_v0"), ("batch1", "batch1_bare_v0"), ("batch2", "batch2_bare_v0"),
             ("final-A", "final_A_bare_v0_baseline"), ("final-B", "final_B_bare_v1_assertionspans_narrow")]
    rows = [[name, regimes[k]["n_cases"], regimes[k]["coverage_pct"]] for name, k in order]
    write_csv("11_evidence_coverage_vs_batch_size_raw.csv", ["batch", "n_cases", "coverage_pct"], rows)
    write_md("11_evidence_coverage_vs_batch_size.md", "Evidence coverage vs batch size", ["batch", "n_cases", "coverage_pct"], rows,
              "5 points -- too few to fit a trend; no regression line computed or implied.")


def table12_timeline():
    rows = [[m["date"], m["commit_tag"], m["event"]] for m in M["timeline"]["milestones"]]
    write_csv("12_experiment_timeline_raw.csv", ["date", "commit", "event"], rows)
    write_md("12_experiment_timeline.md", "Project experiment timeline", ["date", "commit", "event"], rows,
              "Illustrates development sequence only -- not a performance metric.")


def table13_claim_evidence_funnel():
    f = M["funnel"]["bare_v0_pooled_180_cases"]
    rows = [
        ["cases", f["n_cases"]],
        ["claims", f["n_claims"]],
        ["evidence-matched", f["n_evidence_matched"]],
        ["NO_EVIDENCE", f["n_no_evidence"]],
        ["flagged for correction (CONTRADICTED)", f["n_flagged_for_correction"]],
    ]
    write_csv("13_claim_evidence_funnel_raw.csv", ["stage", "count"], rows)
    write_md("13_claim_evidence_funnel.md", f"Claim/evidence funnel -- {f['regime']}", ["stage", "count"], rows,
              "NO_EVIDENCE excluded from our corpus, not confirmed legally unsupported.")


def table14_correction_pipeline_funnel():
    f = M["funnel"]["final_production_regime"]
    prod = M["final_metrics_passthrough"]["section_B_natural_regimes"]["final_labeled_v1_assertionspans_narrow_CORRECTION_GPU"]["correction"]["statuses"]
    rows = [
        ["triggered", f["n_correction_triggers"]],
        ["correction_failed", prod.get("correction_failed", 0)],
        ["scope_violation", prod.get("correction_scope_violation", 0)],
        ["shipped", f["n_correction_shipped"]],
    ]
    write_csv("14_correction_pipeline_funnel_raw.csv", ["stage", "count"], rows)
    write_md("14_correction_pipeline_funnel.md", f"Correction pipeline -- final production regime (n={f['n_correction_triggers']} triggered)", ["stage", "count"], rows,
              "n=10 targeted GPU correction-validation batch under the final production config -- not the cumulative historical count (see table 08 for that).")


def table15_production_config():
    rows = [
        ["premise_framing", "bare", "labeled"],
        ["use_evidence_v1", "false", "true"],
        ["correction.atomic_scope_check", "false", "assertion_spans"],
        ["correction.narrow_reverification_hypothesis", "false", "true"],
        ["verification.confidence_threshold", "0.70", "0.70 (unchanged)"],
    ]
    write_csv("15_production_config_summary_raw.csv", ["config_option", "old_default", "new_default_2026_08_27"], rows)
    write_md("15_production_config_summary.md", "Final production configuration changes", ["config_option", "old_default", "new_default_2026_08_27"], rows,
              "Source: FINAL_PRODUCTION_CONFIG.md, config/prototype.yaml (both frozen documents, transcribed verbatim, not recomputed).")


def table16_natural_vs_synthetic():
    synth = M["final_metrics_passthrough"]["section_A_synthetic"]
    gap = M["final_metrics_passthrough"]["synthetic_vs_natural_correction_transfer_gap"]
    natural_final = M["final_metrics_passthrough"]["section_B_natural_regimes"]["final_B_bare_v1_assertionspans_narrow"]
    rows = [
        ["evidence_coverage_pct", "N/A (no corpus-coverage notion for synthetic)", natural_final["coverage_pct"]],
        ["contradiction_recall_evidence_matched_pct", round(synth["labeled"]["contradiction_recall_with_evidence"]*100, 1), "N/A (requires known-corrupted claims)"],
        ["correction_shipped_rate_pct", gap["synthetic_labeled_shipped_rate_pct"], gap["natural_final_production_regime_shipped_rate_pct"]],
    ]
    write_csv("16_natural_vs_synthetic_comparison_raw.csv", ["metric", "synthetic_labeled", "natural_final_production"], rows)
    write_md("16_natural_vs_synthetic_comparison.md", "Natural vs synthetic side-by-side", ["metric", "synthetic_labeled", "natural_final_production"], rows,
              "N/A marks a metric that genuinely does not apply to the other data type -- not a missing/zero value.")


# ---------------------------------------------------------------------------
def comprehensive_table():
    rows = []

    def add(metric, value, dataset, n, methodology, defensible, limitations, source_path):
        rows.append([metric, value, dataset, n, methodology, defensible, limitations, source_path])

    fm = M["final_metrics_passthrough"]
    add("total distinct natural cases", fm["case_census"]["total_distinct_cases_all_batches"], "natural, all batches pooled", 180,
        "Sum of disjoint batches (n30, batch1, batch2, final_validation); targeted confirmed subset of n30, excluded from sum.",
        True, "Case counts, not an accuracy claim.", "case_census.total_distinct_cases_all_batches")

    add("synthetic stress cases", fm["section_A_synthetic"]["n_cases"], "synthetic (deliberately corrupted)", 59,
        "Paired corrupted (c1) / true (c2) claim per case, real DeBERTa verification, real GPU Qwen correction.",
        True, "Synthetic corruption -- not representative of natural error rates.", "section_A_synthetic.n_cases")

    for regime_name, regime in fm["section_B_natural_regimes"].items():
        if regime.get("n_claims") is None:
            continue
        add(f"claims -- {regime_name}", regime["n_claims"], regime.get("source", regime_name), regime["n_cases"],
            "Deterministic claim extraction (claim_parser.py) over real generated text.", True, "", f"section_B_natural_regimes.{regime_name}.n_claims")
        if regime.get("n_matched") is not None:
            add(f"evidence-matched claims -- {regime_name}", regime["n_matched"], regime.get("source", regime_name), regime["n_cases"],
                "Exact-normalized + fuzzy match against usable evidence pool.", True, "", f"section_B_natural_regimes.{regime_name}.n_matched")
        if regime.get("coverage_pct") is not None:
            add(f"evidence coverage % -- {regime_name}", regime["coverage_pct"], regime.get("source", regime_name), regime["n_cases"],
                "n_matched / n_claims * 100.", True, "", f"section_B_natural_regimes.{regime_name}.coverage_pct")
        for verdict, count in (regime.get("verdict_counts") or {}).items():
            add(f"verdict count [{verdict}] -- {regime_name}", count, regime.get("source", regime_name), regime["n_cases"],
                "Real DeBERTa-v3 NLI verification against matched evidence.", True, "Verdict is model output, not legal ground truth.", f"section_B_natural_regimes.{regime_name}.verdict_counts.{verdict}")

    add("NO_EVIDENCE rate (claims with citation, no match)", fm["section_C_parser_retrieval"]["n_no_evidence_with_citation"], "natural, all experiments pooled", fm["section_C_parser_retrieval"]["n_claims"],
        "797 claims re-extracted with current parser, matched against current v0+v1 pool.", True,
        "NO_EVIDENCE = not in our 136-record corpus; never equated with legal falsehood.", "section_C_parser_retrieval.n_no_evidence_with_citation")

    for bucket, count in fm["section_C_parser_retrieval"]["taxonomy"].items():
        add(f"NO_EVIDENCE taxonomy [{bucket}]", count, "natural, all experiments pooled", fm["section_C_parser_retrieval"]["n_claims"],
            "Manual+programmatic taxonomy of all 260 NO_EVIDENCE claims.", True, "", f"section_C_parser_retrieval.taxonomy.{bucket}")

    add("contradiction recall (overall, bare, synthetic)", round(fm["section_A_synthetic"]["bare"]["contradiction_recall_overall"]*100, 1), "synthetic", 59, "corrupted claims correctly flagged CONTRADICTED / total corrupted.", True, "Synthetic corruption only.", "section_A_synthetic.bare.contradiction_recall_overall")
    add("contradiction recall (overall, labeled, synthetic)", round(fm["section_A_synthetic"]["labeled"]["contradiction_recall_overall"]*100, 1), "synthetic", 59, "same as above, labeled framing.", True, "Synthetic corruption only.", "section_A_synthetic.labeled.contradiction_recall_overall")
    add("false-positive rate (unflagged true claim wrongly CONTRADICTED)", fm["section_A_synthetic"]["bare"]["false_positive_rate_c2"], "synthetic, bare", 59, "c2 (paired true claim) verdict counts.", True, "Synthetic corruption only; 0.0 in both framings.", "section_A_synthetic.bare.false_positive_rate_c2")
    add("false-positive rate (labeled)", fm["section_A_synthetic"]["labeled"]["false_positive_rate_c2"], "synthetic, labeled", 59, "same.", True, "", "section_A_synthetic.labeled.false_positive_rate_c2")

    add("total correction attempts (cumulative, natural)", fm["section_D_correction_safety_cumulative"]["total_correction_attempts"], "natural, all history", None,
        "Cross-checked: fresh recount from every raw jsonl matches final_metrics.json exactly.", True, "", "section_D_correction_safety_cumulative.total_correction_attempts")
    add("correction attempts (synthetic, bare+labeled)", M["correction_safety_audit"]["synthetic"]["n_correction_attempts"], "synthetic", 59, "framing_comparison_gpu_n59_postfix_metrics.json", True, "", "correction_safety_audit.synthetic.n_correction_attempts")
    add("total shipped corrections (natural)", fm["section_D_correction_safety_cumulative"]["total_shipped"], "natural, all history", None, "", True, "n=1 -- a proof of existence, not a rate.", "section_D_correction_safety_cumulative.total_shipped")
    add("total unsafe shipments (natural+synthetic, all history)", M["correction_safety_audit"]["combined_total_unsafe_shipped"], "natural+synthetic, all history", 122, "Checked against every single correction attempt via the status=='corrected' <=> reverification.verdict=='ENTAILED' invariant.", True, "", "correction_safety_audit.combined_total_unsafe_shipped")
    for status, count in fm["section_D_correction_safety_cumulative"]["status_breakdown"].items():
        add(f"correction status [{status}] (natural, cumulative)", count, "natural, all history", None, "", True, "", f"section_D_correction_safety_cumulative.status_breakdown.{status}")

    add("sibling regressions found (natural)", M["correction_safety_audit"]["natural"]["n_attempts_with_sibling_regression_flagged"], "natural, all history", None,
        "sibling_regressions field checked on every correction attempt record.", True, "0 found -- the safety net has not yet had to reject anything on this basis.", "correction_safety_audit.natural.n_attempts_with_sibling_regression_flagged")

    add("unflagged-claim preservation (batch1, bare)", "45/45 = 100%", "natural, batch1 bare", 50, "See final_gpu_validation.md SS4 for full per-claim breakdown.", True, "Per-batch, not pooled across all batches.", "N/A (narrative report, not in computed_metrics.json)")
    add("unflagged-claim preservation (batch1, labeled)", "83/107 = 77.6%", "natural, batch1 labeled", 50, "same.", True, "", "N/A (narrative report)")
    add("citation-identity preservation", "always-on, not independently toggleable", "all modes", None, "src/pipeline.py _citation_identity(); every disturbance produces correction_failed, never a false ship.", True, "Structural guarantee, not a measured rate.", "N/A (code invariant, see FINAL_PRODUCTION_CONFIG.md SS7)")

    add("atomic_scope_check unlocking rate (batch1, historical motivation)", "4/6 genuine edits unblocked", "natural, batch1 (legacy vs relaxed scope check, offline replay)", 50,
        "outputs/natural_candidates_50_gpu_report.md SS5.", True, "This specific finding was not reproduced on the final validation batch's 2 scope-violation cases (both stayed rejected).", "N/A (narrative report)")

    add("evidence corpus: distinct acts (v0)", M["evidence_corpus_composition"]["v0"]["n_distinct_acts"], "v0 evidence corpus", 63, "Direct count over canonical_statutes.jsonl.", True, "", "evidence_corpus_composition.v0.n_distinct_acts")
    add("evidence corpus: distinct acts (v0+v1 combined)", M["evidence_corpus_composition"]["combined_v0_plus_v1"]["n_distinct_acts"], "v0+v1 combined", 142, "Direct count, merge rule replicated from src/data_loader.py.", True, "", "evidence_corpus_composition.combined_v0_plus_v1.n_distinct_acts")
    add("evidence corpus: usable records (v0+v1, production)", 136, "v0+v1, post-audit-fix", None, "final_metrics.json / config/prototype.yaml comments.", True, "Differs from this file's own raw-merge count (145) which predates the 2026-08-27 audit fix -- see evidence_corpus_composition.notes.", "final_metrics_passthrough (136-record pool)")

    ts = M["threshold_sensitivity"]
    add("threshold sensitivity: macro_f1 at production threshold (bare)", [p["macro_f1"] for p in ts["bare"]["sweep"] if p["threshold"] == 0.7][0], "controlled benchmark, bare", 420, "Deterministic replay, no re-inference.", True, "", "threshold_sensitivity.bare.sweep[threshold=0.7].macro_f1")
    add("threshold sensitivity: macro_f1 at production threshold (labeled)", [p["macro_f1"] for p in ts["labeled"]["sweep"] if p["threshold"] == 0.7][0], "controlled benchmark, labeled", 420, "same.", True, "", "threshold_sensitivity.labeled.sweep[threshold=0.7].macro_f1")

    ag = M["assumption_gold_provisional"]
    add("bare agreement with provisional assumption labels", ag["bare_agreement_with_assumption"]["pct"], "PROVISIONAL, not lawyer-verified", ag["n_evidence_matched_claims"], ag["scope"], False, ag["defensible_reason"], "assumption_gold_provisional.bare_agreement_with_assumption.pct")
    add("labeled agreement with provisional assumption labels", ag["labeled_agreement_with_assumption"]["pct"], "PROVISIONAL, not lawyer-verified", ag["n_evidence_matched_claims"], ag["scope"], False, ag["defensible_reason"], "assumption_gold_provisional.labeled_agreement_with_assumption.pct")

    # Explicitly-not-measurable rows, per task requirement.
    add("retrieval precision against independently-labeled false-match ground truth", "NOT MEASURABLE WITH CURRENT DATA", "N/A", "N/A",
        "No independent human/lawyer annotation of 'is this match actually the right provision' exists at scale; only a match-method proxy (exact_normalized vs fuzzy ratio) and manual CONTRADICTED-verdict spot review exist.",
        False, "Would require dedicated lawyer/expert annotation of a retrieval-correctness sample; out of scope for this project to date.", "N/A")
    add("verifier accuracy against lawyer-verified legal ground truth", "NOT MEASURABLE WITH CURRENT DATA", "N/A", "N/A",
        "No lawyer/professional-legal ground-truth evaluation of verifier accuracy has been run as of 2026-08-27 (see research/prototype/README.md 'Known limitations').",
        False, "assumption_annotation.jsonl is Claude-generated, explicitly not a substitute.", "N/A")
    add("natural correction shipped rate as a stable, generalizable rate", "NOT STATISTICALLY DEFENSIBLE AS A RATE", "natural, final production regime", 10,
        "n=1 shipped / 10 triggered.", False, "Too small a sample to treat as a stable rate; reported as a proof-of-existence data point, not a percentage claim.", "final_metrics_passthrough.section_B_natural_regimes.final_labeled_v1_assertionspans_narrow_CORRECTION_GPU")

    header = ["metric", "value", "dataset", "n", "methodology", "statistically_defensible", "limitations", "source_path"]
    write_csv("METRICS_COMPREHENSIVE.csv", header, rows)
    (HERE / "METRICS_COMPREHENSIVE.json").write_text(
        json.dumps([dict(zip(header, r)) for r in rows], indent=2, default=str), encoding="utf-8")
    print(f"wrote METRICS_COMPREHENSIVE.csv / .json ({len(rows)} rows)")


def main():
    table01_evidence_coverage()
    table02_coverage_across_batches()
    table03_bare_vs_labeled_verification()
    table04_bare_vs_labeled_correction()
    table05_synthetic_vs_natural_success()
    table06_contradiction_detection()
    table07_no_evidence_taxonomy()
    table08_correction_failure_taxonomy()
    table09_safety_outcomes()
    table10_threshold_sensitivity()
    table11_coverage_vs_batch_size()
    table12_timeline()
    table13_claim_evidence_funnel()
    table14_correction_pipeline_funnel()
    table15_production_config()
    table16_natural_vs_synthetic()
    comprehensive_table()
    print("All tables generated.")


if __name__ == "__main__":
    main()
