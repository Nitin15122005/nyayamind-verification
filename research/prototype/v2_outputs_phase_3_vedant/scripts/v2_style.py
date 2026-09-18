#!/usr/bin/env python3
"""
Shared visual language for the V2 package.

The palette and density deliberately match this project's existing convention
(`archive/2026-09-06_output_phase_3_vedant/Output_phase_3_vedant/scripts/common.py`,
reused by `scripts/build_results_phase3_figures.py`) so that the V2 figures read
as one continuous visual system with the rest of the project's research output
rather than as a stylistic fork.

Conventions enforced here:
  - ORIGINAL is always the neutral grey; LATEST is always the project blue.
    The colour carries the arm identity on every figure, so a reader never has
    to re-learn which side is which.
  - Verdict colours are fixed per verdict, everywhere.
  - Every figure gets an explicit n and an explicit source/caveat footnote.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DPI = 200

plt.rcParams.update({
    "figure.dpi": DPI, "savefig.dpi": DPI,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "-",
    "axes.axisbelow": True,
    "legend.frameon": False,
})

# Arm identity — fixed across the whole package.
C_ORIGINAL = "#8C8C8C"   # project's C_BASELINE
C_LATEST = "#2A6099"     # project's C_MODIFIED
C_INTERMEDIATE = "#B8C7D6"

# Verdict identity — fixed across the whole package.
VERDICT_COLORS = {
    "ENTAILED": "#3F8F4F",
    "CONTRADICTED": "#C44E52",
    "NOT_ENOUGH_INFORMATION": "#DDA63A",
    "NO_EVIDENCE": "#9E9E9E",
}

C_SHIPPED = "#3F8F4F"
C_REJECT = "#C44E52"
C_SCOPE = "#DD8452"
C_NEUTRAL = "#9E9E9E"

ARM_LABEL_ORIGINAL = "ORIGINAL NyayaMind"
ARM_LABEL_LATEST = "LATEST NyayaMind"


def footnote(ax, text: str, y: float = -0.22):
    """Standard grey provenance/caveat line under an axes."""
    ax.text(0.5, y, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=8.2, color="#555555", linespacing=1.35)


def save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {path}")
    return path
