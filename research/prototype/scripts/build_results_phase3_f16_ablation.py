#!/usr/bin/env python3
"""
Regenerates ONLY F16 (ablation evidence-strength figure) for
research/prototype/results_phase3/, from the CANONICAL ablation table
(results_phase3/tables/ablation/ablation_results.csv) -- the one table
this whole package treats as authoritative for ablation results (built by
scripts/build_results_phase3_tables.py, which extends the archived
Output_phase_3_vedant package's original 8-row table with 5 more rows for
every lever evaluated since 2026-09-06).

The archived package's own F16 (8 rows) predates those 5 additions and no
longer represents the canonical table. This script produces the ONLY
change requested: a 13-row version, in the same visual language (same
"evidence-strength grade, NOT effect size" x-axis, same GRADE_COLORS
palette) as the original, sized and laid out for 13 rows instead of 8.

Reads ONLY the canonical CSV -- no number is hand-typed. Does not touch
any other figure, any source data, or any production code.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results_phase3"
CANONICAL_TABLE = RESULTS / "tables" / "ablation" / "ablation_results.csv"
OUT_PATH = RESULTS / "figures" / "07_ablation" / "F16_ablation_evidence_strength.png"

DPI = 200
plt.rcParams.update({
    "figure.dpi": DPI, "savefig.dpi": DPI,
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

GRADE_COLORS = {"A": "#2A6F2A", "B": "#7FB37F", "C": "#D9A441", "D": "#B0B0B0", "E": "#808080"}
GRADE_WIDTH = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}

# Friendly, multi-line y-axis labels for every one of the 13 canonical
# factor names -- the first 8 are copied verbatim from the archived
# package's own script (archive/2026-09-06_output_phase_3_vedant/
# Output_phase_3_vedant/scripts/generate_figures.py) so the reused rows
# read identically; the 5 new ones follow the same naming convention.
FRIENDLY_NAMES = {
    "evidence_v1": "Evidence corpus v1\n(use_evidence_v1)",
    "premise_framing": "Premise framing\n(bare -> labeled)",
    "claim_parser_fix": "Claim-parser fix\n(commit 223eb9d)",
    "atomic_scope_check_assertion_spans": "Scope check mode\n(assertion_spans)",
    "narrow_reverification_hypothesis": "Narrow re-verification\nhypothesis",
    "confidence_threshold": "Confidence threshold\n(sensitivity sweep)",
    "correction_levers_combined (premise_framing isolated within an otherwise-fixed config)":
        "Correction levers combined\n(framing isolated)",
    "joint_four_lever_isolation": "Joint four-lever isolation\n(experiment absent)",
    "narrow_primary_hypothesis": "Narrow PRIMARY\nverification hypothesis",
    "assertion_span_primary_hypothesis": "Assertion-span\nprimary hypothesis",
    "retrieval_fuzzy_method_bm25": "Retrieval fuzzy method:\nBM25 vs Jaccard",
    "retrieval_fuzzy_method_embedding": "Retrieval fuzzy method:\nembedding vs Jaccard",
    "correction_assertion_aware": "Assertion-aware\ncorrection (splice-based)",
}

# Shortened classification text for the chart only (the full text stays in
# the canonical CSV/table -- this is a display-length concession for 5
# rows whose full Classification string is a full sentence, not a change
# to the underlying classification).
SHORT_CLASSIFICATION = {
    "SUPPORTED (adopted in production)": "SUPPORTED (in production)",
    "EVALUATED, NOT PROMOTED (n too small)": "EVALUATED, NOT PROMOTED",
    "EVALUATED, REJECTED for production (materially less safe)": "EVALUATED, REJECTED",
    "EXPERIMENTAL, NOT PROMOTED (architecturally complete, no demonstrated shipping improvement)":
        "EXPERIMENTAL, NOT PROMOTED",
}


def load_rows() -> list[dict]:
    with CANONICAL_TABLE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    rows = load_rows()
    assert len(rows) == 13, f"Canonical ablation table has {len(rows)} rows, expected 13"

    n = len(rows)
    fig_h = 1.05 * n + 2.2  # scales cleanly with row count, unlike a fixed 6.6in for 8 rows
    fig, ax = plt.subplots(figsize=(14.5, fig_h))

    y = np.arange(n)
    grades = [r["Evidence grade"].strip() for r in rows]
    vals = [GRADE_WIDTH.get(g, 0) for g in grades]
    cols = [GRADE_COLORS.get(g, "#999999") for g in grades]
    bars = ax.barh(y, vals, 0.6, color=cols, edgecolor="black", linewidth=0.6, zorder=2)

    for b, r in zip(bars, rows):
        grade = r["Evidence grade"].strip()
        classification = r["Classification"].strip()
        classification = SHORT_CLASSIFICATION.get(classification, classification)
        p_raw = r["p-value"].strip()
        n_raw = r["n"].strip()
        bits = [f"grade {grade}", classification]
        if p_raw and p_raw not in ("n/a", "—", "-"):
            try:
                bits.append(f"p={float(p_raw):.2e}")
            except ValueError:
                pass
        if n_raw and n_raw not in ("n/a", "—", "-"):
            bits.append(f"n={n_raw}")
        ax.text(b.get_width() + 0.09, b.get_y() + b.get_height() / 2, "   ".join(bits),
                va="center", fontsize=9.5, zorder=3)

    labels = [FRIENDLY_NAMES.get(r["Factor"].strip(), r["Factor"].strip()) for r in rows]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 9.6)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["E\nnot isolable", "D", "C\ndiagnostic", "B\nsupported",
                         "A\nstrongly supported"], fontsize=10)
    ax.set_xlabel("Evidence-strength grade (isolation + sample size + statistical support) "
                  "-- NOT effect size", fontsize=11)
    ax.set_ylabel("Ablation factor (13 levers)", fontsize=11)
    ax.xaxis.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    fig.suptitle("Ablation evidence strength for all 13 evaluated levers",
                  fontsize=16, fontweight="bold", y=0.995)
    ax.set_title(
        "Grades are about how well a factor is evidenced, not how large its effect is;\n"
        "Grade E means the isolating experiment does not exist anywhere in the project",
        fontsize=10.5, fontweight="normal", pad=14,
    )

    fig.text(
        0.01, 0.01,
        "Source: results_phase3/tables/ablation/ablation_results.csv (the canonical, authoritative ablation table for this package;\n"
        "extends the archived Output_phase_3_vedant package's original 8 rows with 5 more evaluated since 2026-09-06).\n"
        "13 named ablation factors | n = varies per factor (3-420) | Status: mixed FRESH/HISTORICAL, see the table for each row's exact freshness.\n"
        "Caveat: no additive or interaction effect between the production levers may be inferred -- no experiment in this project varies "
        "all of them from one common baseline in a single run.",
        fontsize=7.8, color="#333333",
    )

    # Margins as an absolute inch budget, not a fixed fraction -- a fixed
    # fraction (e.g. top=0.86) leaves a growing, wasted gap as fig_h grows
    # with row count, since the title/footer blocks have a roughly FIXED
    # height regardless of how many rows are plotted.
    top_frac = 1 - 1.15 / fig_h
    bottom_frac = 1.55 / fig_h
    fig.subplots_adjust(top=top_frac, bottom=bottom_frac, left=0.22, right=0.97)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {OUT_PATH} ({n} rows)")


if __name__ == "__main__":
    main()
