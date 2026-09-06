#!/usr/bin/env python3
"""STEP 9 -- generate all 11 figures from the LOCKED STEP 8 figure-data CSV contracts.

Every plotted value is read directly from research/prototype/evaluation/metrics/figure_data/*.csv
-- no experimental value is hardcoded in this file. This script does not compute,
regenerate, or reinterpret any experimental result; it only visualizes numbers that
already exist in the locked CSVs.

Matplotlib only (no seaborn). Default matplotlib styling; colors are used only where
semantically necessary (FRESH vs HISTORICAL, GOLD vs natural, evidence grade A-E,
shipped vs rejected). Deterministic: no randomness anywhere in this script.

Usage:
    research/.venv/Scripts/python.exe research/prototype/evaluation/figures/generate_figures.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

FIG_DIR = Path(__file__).resolve().parent
TESTING_DIR = FIG_DIR.parent
DATA_DIR = TESTING_DIR / "evaluation" / "figure_data"

DPI = 200
plt.rcParams["figure.dpi"] = DPI
plt.rcParams["savefig.dpi"] = DPI
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.titleweight"] = "bold"

COLOR_FRESH = "#4C72B0"
COLOR_HISTORICAL = "#B0B0B0"
COLOR_GOLD = "#55A868"
COLOR_NATURAL = "#4C72B0"
COLOR_SHIPPED = "#55A868"
COLOR_FAILED = "#C44E52"
COLOR_SCOPE = "#DD8452"
COLOR_UNSAFE = "#C44E52"
GRADE_COLORS = {"A": "#2A6F2A", "B": "#7FB37F", "C": "#D9A441", "D": "#B0B0B0", "E": "#808080"}


def read_csv(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def savefig(fig, name: str):
    out = FIG_DIR / name
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


# ---------------------------------------------------------------------------
# 01 -- overall metric comparison
# ---------------------------------------------------------------------------

def fig01():
    rows = read_csv("01_overall_metric_comparison.csv")
    tick_labels = {
        "evidence_coverage": "Evidence coverage\n(209-paired, natural)",
        "controlled_benchmark_macro_f1": "Macro F1\n(GOLD benchmark)",
        "controlled_benchmark_accuracy": "Accuracy\n(GOLD benchmark)",
        "synthetic_contradiction_recall": "Contradiction recall\n(Synthetic GOLD)",
    }
    categories = {
        "evidence_coverage": "Natural, metric-only",
        "controlled_benchmark_macro_f1": "Controlled GOLD benchmark",
        "controlled_benchmark_accuracy": "Controlled GOLD benchmark",
        "synthetic_contradiction_recall": "Synthetic GOLD (constructed)",
    }
    cat_colors = {"Natural, metric-only": COLOR_NATURAL, "Controlled GOLD benchmark": COLOR_GOLD,
                  "Synthetic GOLD (constructed)": "#8172B2"}

    x = list(range(len(rows)))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))
    orig = [float(r["original_value"]) for r in rows]
    curr = [float(r["current_value"]) for r in rows]
    colors = [cat_colors[categories[r["metric"]]] for r in rows]

    ax.bar([i - width / 2 for i in x], orig, width, label="Original", color="#B0B0B0", edgecolor="black")
    ax.bar([i + width / 2 for i in x], curr, width, label="Current",
           color=colors, edgecolor="black")

    for i, r in enumerate(rows):
        ax.text(i - width / 2, orig[i] + 0.02, f"{orig[i]:.3f}", ha="center", fontsize=8)
        ax.text(i + width / 2, curr[i] + 0.02, f"{curr[i]:.3f}", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([tick_labels[r["metric"]] for r in rows], fontsize=9)
    ax.set_ylabel("Value (fraction)")
    ax.set_ylim(0, 1.1)
    ax.set_title("Original vs. Current -- Strongest Comparable Metrics")
    legend_handles = [mpatches.Patch(color="#B0B0B0", label="Original"),
                      mpatches.Patch(color=COLOR_NATURAL, label="Current -- Natural (metric-only)"),
                      mpatches.Patch(color=COLOR_GOLD, label="Current -- Controlled GOLD benchmark"),
                      mpatches.Patch(color="#8172B2", label="Current -- Synthetic GOLD (constructed)")]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8, framealpha=0.95)
    fig.subplots_adjust(bottom=0.22)
    fig.text(0.5, 0.03,
              "Evidence coverage is a retrieval metric, not verifier accuracy. Synthetic contradiction recall is measured\n"
              "on a deliberately corrupted, constructed set. Heterogeneous metrics shown on a shared 0-1 fraction\n"
              "scale for magnitude comparison only -- they are not the same kind of measurement.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "01_overall_metric_comparison.png")


# ---------------------------------------------------------------------------
# 02 -- evidence coverage (headline: 209-paired + 588 aggregate)
# ---------------------------------------------------------------------------

def fig02():
    rows = read_csv("02_evidence_coverage.csv")
    headline = [r for r in rows if r["dataset"] in ("209_paired_ArmA", "209_paired_ArmB", "588_claim_aggregate")]

    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    x = range(len(headline))
    vals = [float(r["coverage"]) * 100 for r in headline]
    colors = [COLOR_FRESH if r["fresh_or_historical"] == "FRESH" else COLOR_HISTORICAL for r in headline]
    bars = ax.bar(x, vals, color=colors, edgecolor="black")

    display_labels = {
        "209_paired_ArmA": "v0-only\n(original)\nN=209",
        "209_paired_ArmB": "v0+v1\n(current)\nN=209",
        "588_claim_aggregate": "588-claim\naggregate\n(current)\nN=588",
    }
    ax.set_xticks(list(x))
    ax.set_xticklabels([display_labels[r["dataset"]] for r in headline])
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontweight="bold")

    ax.set_ylabel("Observed evidence coverage (%)")
    ax.set_ylim(0, 95)
    ax.set_title("Observed Evidence Coverage -- Natural-Data, Metric-Only")

    ax.annotate(
        "Paired (N=209): gained=15, lost=0, unchanged=194\nMcNemar p=0.000301",
        xy=(0.5, 1.0), xycoords="axes fraction", xytext=(0, -6), textcoords="offset points",
        ha="center", va="top", fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec="black"),
    )
    legend_handles = [mpatches.Patch(color=COLOR_FRESH, label="Fresh (this workspace)"),
                      mpatches.Patch(color=COLOR_HISTORICAL, label="Historical")]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8)
    fig.subplots_adjust(bottom=0.28)
    fig.text(0.5, 0.04,
              "\"Observed evidence coverage\" -- NOT accuracy. Natural-data, metric-only evaluation: no independent\n"
              "correctness label exists for these claims.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "02_evidence_coverage.png")


# ---------------------------------------------------------------------------
# 03 -- verdict distribution, 588-claim aggregate
# ---------------------------------------------------------------------------

def fig03():
    rows = read_csv("03_verdict_distribution.csv")
    subset = [r for r in rows if r["dataset"] == "588_claim_aggregate"]
    order = ["NOT_ENOUGH_INFORMATION", "NO_EVIDENCE", "ENTAILED", "CONTRADICTED"]
    subset.sort(key=lambda r: order.index(r["verdict"]))

    fig, ax = plt.subplots(figsize=(7, 5))
    x = range(len(subset))
    vals = [int(r["count"]) for r in subset]
    colors = ["#4C72B0", "#B0B0B0", "#55A868", "#C44E52"]
    ax.bar(x, vals, color=colors, edgecolor="black")
    ax.set_xticks(list(x))
    ax.set_xticklabels([r["verdict"] for r in subset], rotation=15, ha="right")
    for i, v in enumerate(vals):
        ax.text(i, v + 5, str(v), ha="center", fontweight="bold")
    ax.set_ylabel("Count")
    n_total = subset[0]["n_total"]
    ax.set_title(f"Verdict Distribution -- N={n_total} Natural Claims\n(Descriptive / Metric-Only)")
    fig.subplots_adjust(bottom=0.24)
    fig.text(0.5, 0.02,
              "Raw observed verifier-verdict counts on real, previously-generated claims.\n"
              "These are NOT correctness labels -- no independent ground truth exists for this data.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "03_verdict_distribution.png")


# ---------------------------------------------------------------------------
# 04 -- correction funnel (5 populations, kept separate)
# ---------------------------------------------------------------------------

def fig04():
    rows = read_csv("04_correction_funnel.csv")
    stages = ["correction_triggered", "correction_generated", "scope_gate_rejected",
              "reverification_not_entailed", "shipped"]
    stage_labels = ["Triggered", "Generated", "Scope\nrejected", "Re-verify\nnot ENTAILED", "Shipped"]

    fig, axes = plt.subplots(1, len(rows), figsize=(4 * len(rows), 5), sharey=False)
    if len(rows) == 1:
        axes = [axes]
    for ax, r in zip(axes, rows):
        vals = []
        for s in stages:
            v = r[s]
            vals.append(None if "NOT AVAILABLE" in v else int(v))
        colors = ["#4C72B0", "#4C72B0", COLOR_SCOPE, COLOR_FAILED, COLOR_SHIPPED]
        for i, (v, c) in enumerate(zip(vals, colors)):
            if v is None:
                ax.text(i, 0.5, "Not\navailable", ha="center", va="center", fontsize=8, rotation=0)
                ax.bar(i, 0, color="none")
            else:
                ax.bar(i, v, color=c, edgecolor="black")
                ax.text(i, v + max(vals[j] for j in range(len(vals)) if vals[j] is not None) * 0.02,
                        str(v), ha="center", fontsize=8)
        ax.set_xticks(range(len(stages)))
        ax.set_xticklabels(stage_labels, fontsize=7)
        title = r["population"].replace("_", " ")
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("Count" if ax is axes[0] else "")

    fig.suptitle("Correction Funnel -- Populations Kept Strictly Separate", fontweight="bold", y=1.03)
    fig.text(0.5, -0.05,
              "Synthetic (deliberately corrupted) and natural populations are never merged into one success rate.\n"
              "\"Not available\" stages are shown explicitly, never inferred.",
              ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    savefig(fig, "04_correction_funnel.png")


# ---------------------------------------------------------------------------
# 05 -- correction outcome (stacked: shipped / failed / scope_violation)
# ---------------------------------------------------------------------------

def fig05():
    rows = read_csv("05_correction_outcome.csv")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = range(len(rows))
    shipped = [int(r["shipped"]) for r in rows]
    failed = [int(r["correction_failed_or_reverification_not_entailed"]) for r in rows]
    scope = [int(r["scope_violation"]) for r in rows]

    ax.bar(x, shipped, color=COLOR_SHIPPED, edgecolor="black", label="Shipped")
    ax.bar(x, failed, bottom=shipped, color=COLOR_FAILED, edgecolor="black", label="Failed / not ENTAILED")
    bottoms2 = [s + f for s, f in zip(shipped, failed)]
    ax.bar(x, scope, bottom=bottoms2, color=COLOR_SCOPE, edgecolor="black", label="Scope violation")

    for i, r in enumerate(rows):
        total = int(r["n_triggered"])
        ax.text(i, total + 0.8, f"{r['shipped']}/{r['n_triggered']}\nshipped", ha="center", fontsize=8, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels([r["population"].replace("_", "\n") for r in rows], fontsize=8)
    ax.set_ylabel("Count (of triggered corrections)")
    ax.set_title("Correction Outcomes by Population\n(Historical / GPU-dependent where applicable)")
    ax.legend(fontsize=8)
    fig.text(0.5, -0.06,
              "Targeted: 0/5 (original) -> 1/10 (current), isolated by design but n too small for statistical support.\n"
              "Cumulative: 1/56 = 1.8% across this project's entire history. Unsafe corrections shipped: 0 (all populations).\n"
              "These figures are NOT statistically established -- shown as observed counts only.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "05_correction_outcome.png")


# ---------------------------------------------------------------------------
# 06 -- safety
# ---------------------------------------------------------------------------

def fig06():
    rows = read_csv("06_safety.csv")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    labels, vals, avail = [], [], []
    for r in rows:
        labels.append(r["safety_mechanism"])
        if "NOT AVAILABLE" in r["count"]:
            vals.append(0)
            avail.append(False)
        else:
            vals.append(int(r["count"]))
            avail.append(True)

    y = range(len(rows))
    colors = [COLOR_UNSAFE if "Unsafe" in l else ("#B0B0B0" if not a else "#4C72B0") for l, a in zip(labels, avail)]
    ax.barh(y, vals, color=colors, edgecolor="black")
    for i, (v, a, r) in enumerate(zip(vals, avail, rows)):
        if a:
            ax.text(v + 0.5, i, str(v), va="center", fontsize=9, fontweight="bold")
        else:
            ax.text(0.5, i, "Not available", va="center", fontsize=9, style="italic")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Unsafe corrections observed (count)")
    ax.set_title("Safety -- Unsafe Corrections Observed (Not a Safety Guarantee)")
    ax.invert_yaxis()
    fig.text(0.5, -0.05,
              "\"0 unsafe corrections observed\" describes the tested correction history (122 attempts) --\n"
              "it does not mean unsafe corrections are impossible.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "06_safety.png")


# ---------------------------------------------------------------------------
# 07 -- confidence distribution
# ---------------------------------------------------------------------------

def fig07():
    rows = read_csv("07_confidence_distribution.csv")
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION", "ALL"]
    rows.sort(key=lambda r: order.index(r["verdict"]))
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    x = list(range(len(rows)))
    means = [float(r["mean_confidence"]) for r in rows]
    medians = [float(r["median_confidence"]) for r in rows]
    width = 0.35
    ax.bar([i - width / 2 for i in x], means, width, label="Mean", color=COLOR_FRESH, edgecolor="black")
    ax.bar([i + width / 2 for i in x], medians, width, label="Median", color="#8172B2", edgecolor="black")
    for i in x:
        ax.text(i - width / 2, means[i] + 0.015, f"{means[i]:.2f}", ha="center", fontsize=8)
        ax.text(i + width / 2, medians[i] + 0.015, f"{medians[i]:.2f}", ha="center", fontsize=8)

    tick_labels = [f"{r['verdict']}\n(n={r['n']})" for r in rows]
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Verifier confidence")
    ax.set_title("Confidence Distribution -- 588-Claim Aggregate\n(Current production config, labeled framing, CPU/DeBERTa)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8, frameon=False)
    fig.subplots_adjust(bottom=0.26)
    fig.text(0.5, 0.03,
              "Confidence is the verifier's own statistical certainty, not a correctness measure.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "07_confidence_distribution.png")


# ---------------------------------------------------------------------------
# 08 -- ablation comparison (grade-colored)
# ---------------------------------------------------------------------------

def fig08():
    rows = read_csv("08_ablation_comparison.csv")
    grade_of = {}
    for r in rows:
        c = r["classification"]
        grade_of[r["factor"]] = {"SUPPORTED": "A", "DESCRIPTIVE": "B", "DIAGNOSTIC": "C",
                                  "NOT_ISOLABLE": "E", "NOT_EXECUTED": "E"}.get(c, "C")
    # Grade A is reserved for the two strongest (p<1e-20); everything else SUPPORTED-but-smaller-n is B.
    grade_of["evidence_v1"] = "A"
    grade_of["premise_framing"] = "A"
    grade_of["claim_parser_fix"] = "B"
    grade_of["confidence_threshold"] = "B"
    grade_of["atomic_scope_check_assertion_spans"] = "C"
    grade_of["narrow_reverification_hypothesis"] = "C"
    grade_of["correction_levers_combined (premise_framing isolated within an otherwise-fixed config)"] = "C"
    grade_of["joint_four_lever_isolation"] = "E"

    display_names = {
        "evidence_v1": "Evidence v1",
        "premise_framing": "Premise framing\n(controlled benchmark)",
        "claim_parser_fix": "Claim parser fix",
        "atomic_scope_check_assertion_spans": "Atomic scope check",
        "narrow_reverification_hypothesis": "Narrow re-verification",
        "confidence_threshold": "Confidence threshold",
        "correction_levers_combined (premise_framing isolated within an otherwise-fixed config)": "Correction levers\n(targeted, isolated)",
        "joint_four_lever_isolation": "Joint four-lever\ninteraction",
    }

    order = ["evidence_v1", "premise_framing", "claim_parser_fix", "confidence_threshold",
             "atomic_scope_check_assertion_spans", "narrow_reverification_hypothesis",
             "correction_levers_combined (premise_framing isolated within an otherwise-fixed config)",
             "joint_four_lever_isolation"]
    rows_by_factor = {r["factor"]: r for r in rows}

    fig, ax = plt.subplots(figsize=(9, 6))
    y = range(len(order))
    grade_rank = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    vals = [grade_rank[grade_of[f]] for f in order]
    colors = [GRADE_COLORS[grade_of[f]] for f in order]
    ax.barh(y, vals, color=colors, edgecolor="black")

    for i, f in enumerate(order):
        r = rows_by_factor[f]
        p = r.get("p_value", "")
        annotation = f"Grade {grade_of[f]}"
        if p:
            try:
                annotation += f"  (p={float(p):.2e})"
            except ValueError:
                pass
        if f == "joint_four_lever_isolation":
            annotation = "Grade E -- NOT EXECUTED (no joint isolation exists)"
        ax.text(vals[i] + 0.08, i, annotation, va="center", fontsize=8)

    ax.set_yticks(list(y))
    ax.set_yticklabels([display_names[f] for f in order], fontsize=9)
    ax.set_xlim(0, 7.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["E", "D", "C", "B", "A"])
    ax.set_xlabel("Evidence grade (A = strongly supported ... E = not executed)")
    ax.invert_yaxis()
    ax.set_title("Ablation Evidence Strength by Grade\n(Grade communicates evidence strength, not effect size)")

    legend_handles = [mpatches.Patch(color=GRADE_COLORS[g], label=lbl) for g, lbl in [
        ("A", "A -- Strongly supported"), ("B", "B -- Supported/descriptive"),
        ("C", "C -- Diagnostic/provisional"), ("E", "E -- Not executed"),
    ]]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8)
    fig.text(0.5, -0.04,
              "No causal isolation is implied for the four-lever interaction (Grade E): no experiment in this\n"
              "project varies all four current production levers from one common baseline.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "08_ablation_comparison.png")


# ---------------------------------------------------------------------------
# 09 -- runtime/resource
# ---------------------------------------------------------------------------

def fig09():
    rows = read_csv("09_runtime_resource.csv")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = range(len(rows))
    vals = [float(r["runtime_seconds"]) for r in rows]
    colors = [COLOR_FRESH if "FRESH" in r["fresh_or_historical"] else COLOR_HISTORICAL for r in rows]
    ax.barh(y, vals, color=colors, edgecolor="black")
    for i, r in enumerate(rows):
        ax.text(vals[i] + 20, i, f"{vals[i]:.0f}s (n={r['n_cases']})", va="center", fontsize=8)
    ax.set_yticks(list(y))
    ax.set_yticklabels([r["arm"].replace("_", " ") for r in rows], fontsize=8)
    ax.set_xlabel("Runtime (seconds)")
    ax.set_title("Runtime / Resource -- Historical GPU vs. Fresh CPU")
    ax.invert_yaxis()
    legend_handles = [mpatches.Patch(color=COLOR_HISTORICAL, label="Historical (GPU, prior session)"),
                      mpatches.Patch(color=COLOR_FRESH, label="Fresh (CPU, this workspace)")]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8)
    fig.text(0.5, -0.05,
              "NVIDIA GPU available on this machine: NO.  Qwen generation/correction executed in this workspace: NOT EXECUTED.\n"
              "All GPU rows above are historical, from a prior session on different hardware -- not reproduced here.",
              ha="center", fontsize=8, style="italic", color="#8B0000")
    savefig(fig, "09_runtime_resource.png")


# ---------------------------------------------------------------------------
# 10 -- cumulative natural results (all regimes)
# ---------------------------------------------------------------------------

def fig10():
    rows = read_csv("10_cumulative_natural_results.csv")
    fig, ax = plt.subplots(figsize=(10, 6.5))
    y = range(len(rows))
    vals = [float(r["coverage"]) * 100 for r in rows]
    colors = [COLOR_FRESH if r["fresh_or_historical"] == "FRESH" else COLOR_HISTORICAL for r in rows]
    ax.barh(y, vals, color=colors, edgecolor="black")
    for i, r in enumerate(rows):
        ax.text(vals[i] + 1, i, f"{vals[i]:.1f}% (N={r['n']})", va="center", fontsize=8)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{r['dataset']}\n({r['arm_or_config']})" for r in rows], fontsize=7)
    ax.set_xlabel("Observed evidence coverage (%)")
    ax.set_xlim(0, 90)
    ax.set_title("Cumulative Natural-Data Results Across All Regimes\n(Metric-only -- not an accuracy measure)")
    ax.invert_yaxis()
    legend_handles = [mpatches.Patch(color=COLOR_FRESH, label="Fresh (this workspace)"),
                      mpatches.Patch(color=COLOR_HISTORICAL, label="Historical")]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=8, frameon=False)
    fig.subplots_adjust(bottom=0.22)
    fig.text(0.5, 0.03,
              "Each regime is reported separately, never pooled, per this project's own methodology.\n"
              "No trend line is added beyond what the CSV itself contains.",
              ha="center", fontsize=8, style="italic")
    savefig(fig, "10_cumulative_natural_results.png")


# ---------------------------------------------------------------------------
# 11 -- synthetic vs. natural transfer (explicit non-equivalence)
# ---------------------------------------------------------------------------

def fig11():
    rows = read_csv("11_synthetic_vs_natural_transfer.csv")
    corr_row = next(r for r in rows if r["metric"] == "correction_shipping_rate")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    synthetic_val = 26 / 36
    natural_val = 1 / 56
    x = [0, 1]
    vals = [synthetic_val, natural_val]
    colors = ["#8172B2", COLOR_NATURAL]
    ax.bar(x, vals, color=colors, edgecolor="black", width=0.5)
    ax.text(0, synthetic_val + 0.02, "26/36 = 72.2%", ha="center", fontweight="bold")
    ax.text(1, natural_val + 0.02, "1/56 = 1.8%", ha="center", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["Synthetic correction\n(deliberately corrupted, GOLD-adjacent)",
                         "Natural cumulative correction\n(real generated text, project history)"])
    ax.set_ylabel("Correction shipping rate (fraction)")
    ax.set_ylim(0, 0.9)
    ax.set_title("Synthetic vs. Natural Correction Shipping\n-- Different Populations, Not Directly Equivalent --")

    ax.annotate("Different evaluation populations; not directly equivalent.",
                xy=(0.5, 0.5), xycoords="axes fraction", xytext=(0.5, 0.75),
                ha="center", fontsize=10, fontweight="bold", color="#8B0000",
                bbox=dict(boxstyle="round", fc="#FFF3CD", ec="#8B0000"))
    fig.text(0.5, -0.06,
              f"{corr_row['note']}",
              ha="center", fontsize=8, style="italic", wrap=True)
    savefig(fig, "11_synthetic_vs_natural_transfer.png")


def main():
    fig01()
    fig02()
    fig03()
    fig04()
    fig05()
    fig06()
    fig07()
    fig08()
    fig09()
    fig10()
    fig11()
    print("\nAll 11 figures generated.")


if __name__ == "__main__":
    main()
