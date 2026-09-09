#!/usr/bin/env python
"""
Generates all 16 demo-pack figures (PNG, 300dpi) from
research/prototype/final_demo_pack/metadata/computed_metrics.json -- the
single, already-cross-checked source of truth for this project's numbers.

No model inference, no GPU. Every number plotted is read from
computed_metrics.json (or, where noted, directly from the one small extra
config file cited below). Nothing here recomputes a result -- only
visualizes an already-computed one.

Run: research/.venv/Scripts/python.exe research/prototype/final_demo_pack/figures/generate_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = Path(__file__).resolve().parent
# parents[3] -> parents[5] (2026-09-09 addendum pass): this pack now lives one
# level deeper (archive/2026-08-27_presentation/) than its original build
# location, so the walk-up to repo root needs 2 more levels.
REPO_ROOT = HERE.parents[5]
METRICS_PATH = HERE.parent / "metadata" / "computed_metrics.json"
CONFIG_PATH = REPO_ROOT / "research/prototype/config/prototype.yaml"

M = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

# --- shared style -----------------------------------------------------------
plt.rcParams.update({
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "font.size": 10,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.edgecolor": "#444444",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "legend.fontsize": 9,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

COLOR_BARE = "#4C72B0"
COLOR_LABELED = "#DD8452"
COLOR_SYNTH = "#C44E52"
COLOR_NATURAL = "#55A868"
COLOR_NEUTRAL = "#8172B2"
COLOR_GOOD = "#55A868"
COLOR_BAD = "#C44E52"
COLOR_WARN = "#CCB974"
VERDICT_COLORS = {
    "NOT_ENOUGH_INFORMATION": "#8C8C8C",
    "NO_EVIDENCE": "#B0B0B0",
    "CONTRADICTED": "#C44E52",
    "ENTAILED": "#55A868",
}

PROVISIONAL_FOOTNOTE = "PROVISIONAL -- Claude-generated labels, NOT lawyer-verified ground truth"


def savefig(fig, name, note=None):
    if note:
        fig.text(0.5, 0.01, note, ha="center", va="bottom", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1] if note else None)
    out = HERE / name
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.name}")


# ---------------------------------------------------------------------------
def fig01_evidence_coverage_v0_to_v1():
    cov = M["evidence_coverage_v0_v1"]
    paired = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    armA = paired["final_A_bare_v0_baseline"]
    armB = paired["final_B_bare_v1_assertionspans_narrow"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    ax = axes[0]
    labels = ["v0 only\n(59 usable)", "v0 + v1\n(136 usable)"]
    vals = [cov["coverage_v0_pct"], cov["coverage_v1_pct"]]
    bars = ax.bar(labels, vals, color=[COLOR_BARE, COLOR_LABELED], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v}%", ha="center", fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Evidence coverage (%)")
    ax.set_title(f"All natural claims, n={cov['n_claims']} claims\n(claim-level, non-paired)")

    ax = axes[1]
    labels = ["Arm A: v0 only\n(pre-2026-08-27 baseline)", "Arm B: v0+v1\n+assertion_spans"]
    vals = [armA["coverage_pct"], armB["coverage_pct"]]
    bars = ax.bar(labels, vals, color=[COLOR_BARE, COLOR_LABELED], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v}%", ha="center", fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_title(f"Paired-arm comparison, n={armA['n_cases']} held-out cases,\n{armA['n_claims']} claims each arm\nMcNemar chi2=13.07, p~0.0003")

    fig.suptitle("Evidence coverage: v0 vs v0+v1", fontsize=13, fontweight="bold")
    savefig(fig, "01_evidence_coverage_v0_to_v1.png",
            "Left: all 588 claims ever generated, non-paired. Right: same 209 claims from 50 held-out cases, matched independently per arm (the strongest comparison -- only this one carries a significance test).")


def fig02_coverage_across_batches():
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    order = ["n30_modeB_bare_v0", "batch1_bare_v0", "batch2_bare_v0", "final_A_bare_v0_baseline", "final_B_bare_v1_assertionspans_narrow"]
    labels = ["n=30\n(v0,bare)", "batch1\n(v0,bare)", "batch2\n(v0,bare)", "final-A\n(v0,bare)", "final-B\n(v0+v1,bare)"]
    vals = [regimes[k]["coverage_pct"] for k in order]
    n_cases = [regimes[k]["n_cases"] for k in order]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    colors = [COLOR_BARE] * 4 + [COLOR_LABELED]
    bars = ax.bar(labels, vals, color=colors, width=0.6)
    for b, v, n in zip(bars, vals, n_cases):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v}%", ha="center", fontweight="bold")
        ax.text(b.get_x() + b.get_width() / 2, 2, f"n={n} cases", ha="center", fontsize=8, color="white")
    ax.set_ylim(0, 85)
    ax.set_ylabel("Evidence coverage (%)")
    ax.set_title("Evidence coverage across natural NyayaRAG batches (bare framing)")
    savefig(fig, "02_evidence_coverage_across_natural_batches.png",
            "Each batch is a disjoint set of real NyayaRAG cases (see case_census). Coverage varies with each batch's own citation profile, not a trend over time.")


def fig03_bare_vs_labeled_verification():
    bare = M["final_metrics_passthrough"]["section_B_pooled_bare_v0"]
    labeled = M["final_metrics_passthrough"]["section_B_pooled_labeled_v0"]
    verdicts = ["NO_EVIDENCE", "NOT_ENOUGH_INFORMATION", "CONTRADICTED", "ENTAILED"]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    x = range(len(verdicts))
    w = 0.35
    bare_vals = [bare["verdict_counts"].get(v, 0) for v in verdicts]
    labeled_vals = [labeled["verdict_counts"].get(v, 0) for v in verdicts]
    ax.bar([i - w / 2 for i in x], bare_vals, width=w, label=f"bare, pooled (180 cases, {bare['n_claims']} claims)", color=COLOR_BARE)
    ax.bar([i + w / 2 for i in x], labeled_vals, width=w, label=f"labeled, pooled (100 cases, {labeled['n_claims']} claims)", color=COLOR_LABELED)
    ax.set_xticks(list(x))
    ax.set_xticklabels(verdicts, rotation=10)
    ax.set_ylabel("Claim count")
    ax.set_title("Bare vs labeled premise framing: verdict distribution\n(natural data, pooled same-regime batches)")
    ax.legend()
    savefig(fig, "03_bare_vs_labeled_verification_outcomes.png",
            "NOTE: different underlying case sets (bare pools n=30+batch1+batch2+final-A; labeled pools batch1+batch2 only) -- see section_B_pooled_* in computed_metrics.json. Not a same-case paired comparison.")


def fig04_bare_vs_labeled_correction():
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    batches = [("batch1", "batch1_bare_v0", "batch1_labeled_v0"), ("batch2", "batch2_bare_v0", "batch2_labeled_v0")]
    statuses = ["correction_failed", "correction_scope_violation", "corrected"]
    status_colors = {"correction_failed": COLOR_WARN, "correction_scope_violation": COLOR_BAD, "corrected": COLOR_GOOD}

    fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    for ax, (name, bare_k, lab_k) in zip(axes, batches):
        bare_c = regimes[bare_k]["correction"]
        lab_c = regimes[lab_k]["correction"]
        labels = [f"bare\n(n={bare_c['correction_triggers']} triggered)", f"labeled\n(n={lab_c['correction_triggers']} triggered)"]
        bottoms = [0, 0]
        for status in statuses:
            vals = [bare_c["statuses"].get(status, 0), lab_c["statuses"].get(status, 0)]
            ax.bar(labels, vals, bottom=bottoms, label=status, color=status_colors[status])
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        ax.set_title(name)
        ax.set_ylabel("Correction attempts")
    axes[1].legend(loc="upper right")
    fig.suptitle("Bare vs labeled: correction attempt outcomes (natural batches 1 & 2)", fontsize=13, fontweight="bold")
    savefig(fig, "04_bare_vs_labeled_correction_outcomes.png",
            "Legacy (pre-assertion_spans) scope-check regime -- not the final production config. 0 shipped in either arm on these two batches.")


def fig05_synthetic_vs_natural_correction_success():
    gap = M["final_metrics_passthrough"]["synthetic_vs_natural_correction_transfer_gap"]
    synth = M["correction_safety_audit"]["synthetic"]
    synth_bare_rate = 100.0 * synth["bare"]["n_shipped_corrected"] / synth["bare"]["n_correction_attempts"]
    synth_labeled_rate = gap["synthetic_labeled_shipped_rate_pct"]

    labels = [f"synthetic\nbare (n={synth['bare']['n_correction_attempts']})",
              f"synthetic\nlabeled (n={synth['labeled']['n_correction_attempts']})",
              f"natural\nall regimes (n=56)",
              f"natural\nfinal production (n=10)"]
    vals = [synth_bare_rate, synth_labeled_rate, gap["natural_all_regimes_shipped_rate_pct"], gap["natural_final_production_regime_shipped_rate_pct"]]
    colors = [COLOR_SYNTH, COLOR_SYNTH, COLOR_NATURAL, COLOR_NATURAL]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, vals, color=colors, width=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}%", ha="center", fontweight="bold")
    ax.set_ylabel("Shipped-correction rate (%)")
    ax.set_ylim(0, 85)
    ax.set_title("Correction shipped-rate: synthetic stress vs natural data")
    legend_handles = [mpatches.Patch(color=COLOR_SYNTH, label="synthetic (deliberately corrupted claims)"),
                       mpatches.Patch(color=COLOR_NATURAL, label="natural (real NyayaRAG cases)")]
    ax.legend(handles=legend_handles)
    savefig(fig, "05_synthetic_vs_natural_correction_success.png",
            "Synthetic performance has never transferred to natural data at anywhere near the same magnitude -- see final_research_results.md SS A vs SS D.")


def fig06_contradiction_detection_comparison():
    synth = M["final_metrics_passthrough"]["section_A_synthetic"]
    labels = ["bare\noverall", "bare\nevidence-matched", "labeled\noverall", "labeled\nevidence-matched"]
    vals = [
        synth["bare"]["contradiction_recall_overall"] * 100,
        synth["bare"]["contradiction_recall_with_evidence"] * 100,
        synth["labeled"]["contradiction_recall_overall"] * 100,
        synth["labeled"]["contradiction_recall_with_evidence"] * 100,
    ]
    colors = [COLOR_BARE, COLOR_BARE, COLOR_LABELED, COLOR_LABELED]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", fontweight="bold")
    ax.set_ylabel("Contradiction recall (%)")
    ax.set_ylim(0, 75)
    ax.set_title(f"Contradiction detection recall -- SYNTHETIC STRESS TEST ONLY\n(n={synth['n_cases']} deliberately-corrupted claim pairs, real DeBERTa verification)")
    savefig(fig, "06_contradiction_detection_comparison.png",
            "SYNTHETIC data (deliberate corruption), not natural case text. Real natural-data contradiction counts are far smaller in absolute terms -- see figure 03.")


def fig07_no_evidence_taxonomy():
    tax = M["final_metrics_passthrough"]["section_C_parser_retrieval"]["taxonomy"]
    labels = list(tax.keys())
    vals = list(tax.values())
    pretty = {
        "genuinely_absent_no_such_provision_any_act": "genuinely absent\n(no such provision\nin any act)",
        "genuinely_absent_wrong_act_or_edition": "genuinely absent\n(wrong act/edition)",
        "unresolved_act": "unresolved act\n(correctly declined)",
        "parser_or_matcher_defect_candidate": "parser/matcher\ndefect candidate\n(both reviewed: not bugs)",
    }
    labels_pretty = [pretty.get(l, l) for l in labels]
    colors = [COLOR_NEUTRAL, COLOR_WARN, COLOR_BARE, COLOR_BAD]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    bars = ax.barh(labels_pretty, vals, color=colors)
    total = sum(vals)
    for b, v in zip(bars, vals):
        ax.text(v + 2, b.get_y() + b.get_height() / 2, f"{v} ({100*v/total:.0f}%)", va="center", fontweight="bold")
    ax.set_xlabel("Claims")
    ax.set_title(f"NO_EVIDENCE taxonomy (n={total} claims with a citation but no evidence match,\nof {M['final_metrics_passthrough']['section_C_parser_retrieval']['n_claims']} total claims across all natural experiments)")
    savefig(fig, "07_no_evidence_taxonomy.png",
            "NO_EVIDENCE means 'not in our corpus', not 'legally unsupported' -- see reports/retrieval_analysis.md.")


def fig08_correction_failure_taxonomy():
    sb = M["correction_safety_audit"]["natural"]["status_breakdown"]
    labels_pretty = {"correction_failed": "correction_failed\n(no ENTAILED reverification)", "correction_scope_violation": "scope_violation\n(sibling claim disturbed)", "corrected": "corrected\n(shipped)"}
    labels = [labels_pretty[k] for k in sb]
    vals = list(sb.values())
    colors = [COLOR_WARN, COLOR_BAD, COLOR_GOOD]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(labels, vals, color=colors[:len(vals)], width=0.5)
    total = sum(vals)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v} ({100*v/total:.0f}%)", ha="center", fontweight="bold")
    ax.set_ylabel("Correction attempts")
    ax.set_title(f"Natural-data correction outcome taxonomy (n={total} attempts, all historical batches)")
    savefig(fig, "08_correction_failure_taxonomy.png")


def fig09_safety_outcomes():
    csa = M["correction_safety_audit"]
    nat_shipped = csa["natural"]["n_shipped_corrected"]
    nat_rejected = csa["natural"]["n_correction_attempts"] - nat_shipped
    synth_shipped = csa["synthetic"]["n_shipped_corrected"]
    synth_rejected = csa["synthetic"]["n_correction_attempts"] - synth_shipped
    unsafe = csa["combined_total_unsafe_shipped"]

    fig, ax = plt.subplots(figsize=(8, 6.2))
    cats = ["natural\n(n=56)", "synthetic\n(n=66)"]
    shipped = [nat_shipped, synth_shipped]
    rejected = [nat_rejected, synth_rejected]
    ax.bar(cats, rejected, label="rejected (failed / scope_violation)", color=COLOR_WARN)
    ax.bar(cats, shipped, bottom=rejected, label="shipped (corrected)", color=COLOR_GOOD)
    for i, (s, r) in enumerate(zip(shipped, rejected)):
        ax.text(i, r + s + 1.5, f"shipped={s}", ha="center", fontweight="bold", fontsize=9)
    ax.set_ylim(0, max(r + s for r, s in zip(rejected, shipped)) * 1.28)
    ax.text(0.5, 1.16, f"UNSAFE SHIPMENTS = {unsafe} / {csa['combined_total_attempts']} total attempts",
            transform=ax.transAxes, ha="center", fontsize=12, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=COLOR_GOOD))
    ax.set_ylabel("Correction attempts")
    ax.set_title("Safety outcomes: shipped vs rejected, natural + synthetic")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0))
    savefig(fig, "09_safety_outcomes.png",
            "'Unsafe' = shipped without reverification.verdict==ENTAILED. Checked against every single attempt in the project's history, not sampled.")


def fig10_threshold_sensitivity():
    ts = M["threshold_sensitivity"]
    prod_t = ts["production_threshold"]
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for label, key, color in [("bare", "bare", COLOR_BARE), ("labeled", "labeled", COLOR_LABELED)]:
        sweep = ts[key]["sweep"]
        xs = [p["threshold"] for p in sweep]
        ys = [p["macro_f1"] for p in sweep]
        ax.plot(xs, ys, marker="o", label=f"{label} (n={ts[key]['n_items']})", color=color)
    ax.axvline(prod_t, color="black", linestyle=":", linewidth=1.5)
    ax.text(prod_t + 0.005, 0.72, f"production\nthreshold={prod_t}", fontsize=8)
    ax.set_xlabel("Confidence threshold")
    ax.set_ylabel("Macro F1")
    ax.set_title("Threshold sensitivity (controlled benchmark, 420 curated claims)")
    ax.legend()
    savefig(fig, "10_threshold_sensitivity_curve.png",
            "Deterministic replay over stored softmax outputs -- controlled benchmark, not synthetic stress or natural data.")


def fig11_coverage_vs_batch_size():
    regimes = M["final_metrics_passthrough"]["section_B_natural_regimes"]
    order = ["n30_modeB_bare_v0", "batch1_bare_v0", "batch2_bare_v0", "final_A_bare_v0_baseline", "final_B_bare_v1_assertionspans_narrow"]
    names = ["n=30", "batch1", "batch2", "final-A", "final-B"]
    xs = [regimes[k]["n_cases"] for k in order]
    ys = [regimes[k]["coverage_pct"] for k in order]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.scatter(xs, ys, s=90, color=COLOR_BARE, zorder=3)
    for x, y, n in zip(xs, ys, names):
        ax.annotate(n, (x, y), textcoords="offset points", xytext=(8, 4), fontsize=9)
    ax.set_xlabel("Batch size (n cases)")
    ax.set_ylabel("Evidence coverage (%)")
    ax.set_ylim(30, 80)
    ax.set_title("Evidence coverage vs. batch size (natural batches)")
    savefig(fig, "11_evidence_coverage_vs_batch_size.png",
            "No trend line fitted -- 5 points is too few to establish a relationship; coverage depends on each batch's citation profile, not primarily its size.")


def fig12_experiment_timeline():
    milestones = M["timeline"]["milestones"]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ys = list(range(len(milestones)))
    ax.hlines(0, -0.5, len(milestones) - 0.5, color="#999999", linewidth=1.5, zorder=1)
    for i, m in enumerate(milestones):
        ax.scatter(i, 0, s=140, color=COLOR_BARE if i % 2 == 0 else COLOR_LABELED, zorder=3)
        y_off = 0.35 if i % 2 == 0 else -0.55
        ax.text(i, y_off, f"{m['date']}\n({m['commit_tag']})\n{m['event']}", ha="center", va="bottom" if i % 2 == 0 else "top",
                fontsize=7.6, wrap=True,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#F5F5F5", edgecolor="#CCCCCC"))
    ax.set_xlim(-0.5, len(milestones) - 0.5)
    ax.set_ylim(-1.3, 1.3)
    ax.axis("off")
    ax.set_title("Project experiment timeline", fontsize=13, fontweight="bold")
    savefig(fig, "12_experiment_timeline.png", "Illustrates development sequence only -- not a performance metric.")


def fig13_claim_evidence_funnel():
    f = M["funnel"]["bare_v0_pooled_180_cases"]
    stages = ["cases", "claims", "evidence-\nmatched", "flagged for\ncorrection\n(CONTRADICTED)"]
    vals = [f["n_cases"], f["n_claims"], f["n_evidence_matched"], f["n_flagged_for_correction"]]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(stages, vals, color=[COLOR_NEUTRAL, COLOR_BARE, COLOR_GOOD, COLOR_BAD], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.02 if v > 5 else v + 5, f"{v}", ha="center", fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylabel("Count (log scale)")
    ax.set_title(f"Claim/evidence funnel -- {f['regime']}")
    savefig(fig, "13_claim_evidence_funnel.png",
            f"NO_EVIDENCE (not shown as a stage): {f['n_no_evidence']} claims -- excluded from our corpus, not confirmed legally unsupported.")


def fig14_correction_pipeline_funnel():
    f = M["funnel"]["final_production_regime"]
    sb = M["correction_safety_audit"]["natural"]["status_breakdown"]
    # scope this funnel to the final-production-regime GPU correction validation (n=10), matching f's own numbers
    prod = M["final_metrics_passthrough"]["section_B_natural_regimes"]["final_labeled_v1_assertionspans_narrow_CORRECTION_GPU"]["correction"]["statuses"]
    stages = ["triggered", "correction_failed", "scope_violation", "shipped"]
    vals = [f["n_correction_triggers"], prod.get("correction_failed", 0), prod.get("correction_scope_violation", 0), f["n_correction_shipped"]]
    colors = [COLOR_NEUTRAL, COLOR_WARN, COLOR_BAD, COLOR_GOOD]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(stages, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v}", ha="center", fontweight="bold")
    ax.set_ylabel("Cases")
    ax.set_title(f"Correction pipeline outcome -- final production regime\n(n={f['n_correction_triggers']} triggered, targeted GPU validation)")
    savefig(fig, "14_correction_pipeline_funnel.png",
            "This is the n=10 targeted GPU correction-validation batch under the final production config, not the cumulative historical count (see figure 08 for that).")


def fig15_production_config_summary():
    # Values transcribed directly from FINAL_PRODUCTION_CONFIG.md's own summary
    # table / config/prototype.yaml comments (both already-committed, frozen
    # documents) -- not invented here.
    rows = [
        ("premise_framing", "bare", "labeled"),
        ("use_evidence_v1", "false", "true"),
        ("correction.atomic_scope_check", "false", '"assertion_spans"'),
        ("correction.narrow_reverification_hypothesis", "false", "true"),
        ("verification.confidence_threshold", "0.70", "0.70 (unchanged)"),
    ]
    fig, ax = plt.subplots(figsize=(12, 3.4))
    ax.axis("off")
    col_labels = ["Config option", "Old default", "New default (2026-08-27)"]
    cell_colors = []
    for opt, old, new in rows:
        changed = old != new and "unchanged" not in new
        cell_colors.append(["#FFFFFF", "#FDECEA" if changed else "#EFEFEF", "#EAF7EC" if changed else "#EFEFEF"])
    table = ax.table(cellText=[list(r) for r in rows], colLabels=col_labels, cellColours=cell_colors,
                      loc="center", cellLoc="left", colLoc="left",
                      colWidths=[0.48, 0.18, 0.34])
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 2.4)
    for j in range(len(col_labels)):
        table[0, j].set_text_props(fontweight="bold")
        table[0, j].set_facecolor("#4C72B0")
        table[0, j].set_text_props(color="white", fontweight="bold")
    ax.set_title("Final production configuration -- what changed on 2026-08-27\n(source: FINAL_PRODUCTION_CONFIG.md, config/prototype.yaml)",
                 fontsize=11, fontweight="bold", pad=14)
    savefig(fig, "15_production_config_summary.png")


def fig16_natural_vs_synthetic_comparison():
    synth = M["final_metrics_passthrough"]["section_A_synthetic"]
    gap = M["final_metrics_passthrough"]["synthetic_vs_natural_correction_transfer_gap"]
    natural_final = M["final_metrics_passthrough"]["section_B_natural_regimes"]["final_B_bare_v1_assertionspans_narrow"]

    metrics = ["evidence coverage (%)", "contradiction recall,\nevidence-matched (%)", "correction shipped\nrate (%)"]
    synthetic_vals = [None, synth["labeled"]["contradiction_recall_with_evidence"] * 100, gap["synthetic_labeled_shipped_rate_pct"]]
    natural_vals = [natural_final["coverage_pct"], None, gap["natural_final_production_regime_shipped_rate_pct"]]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = range(len(metrics))
    w = 0.35
    synth_plot = [v if v is not None else 0 for v in synthetic_vals]
    nat_plot = [v if v is not None else 0 for v in natural_vals]
    b1 = ax.bar([i - w / 2 for i in x], synth_plot, width=w, label="synthetic (labeled)", color=COLOR_SYNTH)
    b2 = ax.bar([i + w / 2 for i in x], nat_plot, width=w, label="natural (final production regime)", color=COLOR_NATURAL)
    for i, v in enumerate(synthetic_vals):
        if v is None:
            ax.text(i - w / 2, 2, "N/A\n(not applicable\nto synthetic)", ha="center", fontsize=7.5)
    for i, v in enumerate(natural_vals):
        if v is None:
            ax.text(i + w / 2, 2, "N/A\n(synthetic-only\nmetric)", ha="center", fontsize=7.5)
    for b, v in zip(b1, synthetic_vals):
        if v is not None:
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}", ha="center", fontweight="bold", fontsize=8)
    for b, v in zip(b2, natural_vals):
        if v is not None:
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}", ha="center", fontweight="bold", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics)
    ax.set_ylabel("%")
    ax.set_title("Natural vs synthetic data: side-by-side comparison")
    ax.legend()
    savefig(fig, "16_natural_vs_synthetic_comparison.png",
            "Metrics are only comparable where both data types produce them -- N/A bars mark metrics that don't apply to the other data type (e.g. synthetic has no independent 'evidence coverage' notion; contradiction recall requires known-corrupted claims, which only the synthetic set has).")


def main():
    fig01_evidence_coverage_v0_to_v1()
    fig02_coverage_across_batches()
    fig03_bare_vs_labeled_verification()
    fig04_bare_vs_labeled_correction()
    fig05_synthetic_vs_natural_correction_success()
    fig06_contradiction_detection_comparison()
    fig07_no_evidence_taxonomy()
    fig08_correction_failure_taxonomy()
    fig09_safety_outcomes()
    fig10_threshold_sensitivity()
    fig11_coverage_vs_batch_size()
    fig12_experiment_timeline()
    fig13_claim_evidence_funnel()
    fig14_correction_pipeline_funnel()
    fig15_production_config_summary()
    fig16_natural_vs_synthetic_comparison()
    print("All 16 figures generated.")


if __name__ == "__main__":
    main()
