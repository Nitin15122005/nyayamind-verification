#!/usr/bin/env python3
"""
Generates the ONE new diagram needed for research/prototype/results_phase3/
that the archived Output_phase_3_vedant package does not have: the
ASSERTION-AWARE (splice-based) correction flow, added 2026-09-12 and not
present when that package was generated (2026-09-06). D09 in the archived
package documents only the LEGACY whole-paragraph-regeneration flow.

Visual convention matched to D09 (box-and-arrow flowchart, same palette,
same title/subtitle/source-footer layout) for one consistent visual
language across old + new diagrams. Every box/label is confirmed against
actual source code (src/pipeline.py's apply_selective_correction_assertion_aware,
src/corrector.py's correct_assertion_span) -- no invented stage.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results_phase3"

DPI = 200
plt.rcParams.update({"figure.dpi": DPI, "savefig.dpi": DPI, "font.size": 11})

COLORS = {
    "input": "#E4D9F0",
    "llm": "#F3D9BE",
    "splice": "#D4E6D0",
    "gate": "#F6D3D9",
    "reverify": "#FCEBB5",
    "decision": "#FFFFFF",
    "ship": "#D4E6D0",
    "reject": "#F9DEE2",
}
EDGE = "#333333"


def box(ax, xy, w, h, text, color, edgecolor=EDGE, fontsize=10.5, fontweight="normal", lw=1.4):
    x, y = xy
    rect = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=lw, edgecolor=edgecolor, facecolor=color, zorder=2,
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
             fontweight=fontweight, zorder=3, linespacing=1.35)
    return (x, y, w, h)


def arrow(ax, start, end, color=EDGE, label=None, label_color=None, style="-|>", label_dy=0.0):
    a = FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=16,
                         linewidth=1.6, color=color, zorder=1)
    ax.add_patch(a)
    if label:
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + label_dy
        ax.text(mx, my, label, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color=label_color or color, zorder=4,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none"))


def right_center(b):
    x, y, w, h = b
    return (x + w, y + h / 2)


def left_center(b):
    x, y, w, h = b
    return (x, y + h / 2)


def bottom_center(b):
    x, y, w, h = b
    return (x + w / 2, y)


def top_center(b):
    x, y, w, h = b
    return (x + w / 2, y + h)


def build_assertion_aware_flow_diagram():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis("off")

    fig.text(0.5, 0.975, "Assertion-span-aware correction — deterministic splice flow",
              ha="center", fontsize=18, fontweight="bold")
    fig.text(0.5, 0.945,
              "correction.assertion_aware=true (EXPERIMENTAL, not production default) — targets only the flagged\n"
              "claim's own content fragment; everything outside it is byte-identical to the original by construction",
              ha="center", fontsize=11, color="#333333")

    row1_y, row2_y, row3_y, row4_y = 8.4, 6.1, 3.8, 1.3
    bh = 1.4

    b_flagged = box(ax, (0.3, row1_y), 3.0, bh,
                     "Flagged claim\n+ its own assertion_spans\n(e.g. ['302', 'theft'])", COLORS["input"])
    b_target = box(ax, (3.9, row1_y), 3.0, bh,
                    "_correction_target_spans()\ncontent fragment = spans[-1]\n(fail closed if malformed)", COLORS["input"])
    b_llm = box(ax, (7.5, row1_y), 3.2, bh,
                "SelectiveCorrector\n.correct_assertion_span()\nQwen2.5-7B, ONE fragment only", COLORS["llm"])
    b_fragment = box(ax, (11.3, row1_y), 3.2, bh,
                      "Corrected fragment\n(e.g. 'murder')\nno paragraph regeneration", COLORS["llm"])

    arrow(ax, right_center(b_flagged), left_center(b_target))
    arrow(ax, right_center(b_target), left_center(b_llm))
    arrow(ax, right_center(b_llm), left_center(b_fragment))

    b_splice = box(ax, (11.3, row2_y), 3.2, bh,
                    "_splice_assertion_correction()\ndeterministic string replace\nfails closed if ambiguous", COLORS["splice"])
    arrow(ax, bottom_center(b_fragment), top_center(b_splice))

    b_structural = box(ax, (7.5, row2_y), 3.2, bh,
                        "Structural-span check\n(NEW) — e.g. the bare\nnumber survives the edit", COLORS["gate"])
    arrow(ax, left_center(b_splice), right_center(b_structural))

    b_scope = box(ax, (3.9, row2_y), 3.0, bh,
                   "Scope + unauthorized-citation\n+ ordinal-integrity gates\n(same as legacy path)", COLORS["gate"])
    arrow(ax, left_center(b_structural), right_center(b_scope))

    b_reparse = box(ax, (0.3, row2_y), 3.0, bh,
                     "Re-parse corrected text\nordinal-position match\n-> replacement claim", COLORS["splice"])
    arrow(ax, left_center(b_scope), right_center(b_reparse))

    b_reverify = box(ax, (0.3, row3_y), 3.0, bh,
                      "Re-verify target\n(real DeBERTa call)\nsame premise framing", COLORS["reverify"])
    arrow(ax, bottom_center(b_reparse), top_center(b_reverify))

    b_decision = box(ax, (3.9, row3_y), 3.0, bh, "verdict == ENTAILED ?", COLORS["decision"])
    arrow(ax, right_center(b_reverify), left_center(b_decision))

    b_failed = box(ax, (7.5, row3_y), 3.0, bh,
                    'status = "correction_failed"\nORIGINAL text ships', COLORS["reject"])
    arrow(ax, right_center(b_decision), left_center(b_failed), label="no", label_color="#B22222")

    b_sibling = box(ax, (3.9, row4_y), 3.4, bh,
                     "Sibling-regression check\n(NEW — runs unconditionally\nfor this mechanism)", COLORS["reverify"])
    arrow(ax, bottom_center(b_decision), top_center(b_sibling), label="yes", label_color="#2A6F2A")

    b_shipped = box(ax, (0.3, row4_y), 3.0, bh,
                     'status = "corrected"\nfinal_field.source = "corrected"', COLORS["ship"])
    arrow(ax, left_center(b_sibling), right_center(b_shipped), label="clean", label_color="#2A6F2A")

    b_regressed = box(ax, (7.9, row4_y), 3.6, bh,
                       'status = "correction_sibling_regression"\nORIGINAL text ships\n(untouched sibling independently wrong)', COLORS["reject"])
    arrow(ax, right_center(b_sibling), left_center(b_regressed), label="regression\nfound", label_color="#B22222", label_dy=0.95)

    fig.text(0.02, 0.035,
              "Source: research/prototype/src/pipeline.py (apply_selective_correction_assertion_aware, "
              "_correction_target_spans, _splice_assertion_correction), research/prototype/src/corrector.py "
              "(correct_assertion_span).\n"
              "Real n=10 result: 0/10 shipped (outputs/assertion_aware_correction_experiment_report.md) — "
              "EXPERIMENTAL, correction.assertion_aware stays false in production.",
              fontsize=8.5, color="#555555")

    out = RESULTS / "diagrams" / "04_correction" / "assertion_aware_correction_splice_flow.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build_assertion_aware_flow_diagram()
