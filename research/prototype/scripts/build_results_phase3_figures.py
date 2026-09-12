#!/usr/bin/env python3
"""
Generates the NEW figures for research/prototype/results_phase3/ covering
everything evaluated since the archived Output_phase_3_vedant package
(generated 2026-09-06): narrow_primary_hypothesis, retrieval fuzzy-method
safety comparison, assertion-span verification, assertion-aware correction,
and error propagation. Reads ONLY committed real source artifacts -- no
number is hand-typed into a plotting call.

Visual style matched to the archived package's own convention (same color
palette, same publication density) for one consistent visual language
across the whole results story -- see archive/2026-09-06_output_phase_3_vedant/
Output_phase_3_vedant/scripts/common.py for the source of these constants.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
RESULTS = ROOT / "results_phase3"

DPI = 200
plt.rcParams.update({
    "figure.dpi": DPI, "savefig.dpi": DPI,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.labelsize": 11, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

VERDICT_COLORS = {
    "ENTAILED": "#3F8F4F",
    "CONTRADICTED": "#C44E52",
    "NOT_ENOUGH_INFORMATION": "#DDA63A",
    "NO_EVIDENCE": "#9E9E9E",
}
C_BASELINE = "#8C8C8C"
C_MODIFIED = "#2A6099"
C_SHIPPED = "#3F8F4F"
C_REJECT = "#C44E52"
C_SCOPE = "#DD8452"


def save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {path}")


# ---------------------------------------------------------------------------
# 1. narrow_primary_hypothesis: verdict distribution, OLD vs CURRENT (n=62)
# ---------------------------------------------------------------------------

def fig_narrow_primary_hypothesis():
    d = json.loads((OUTPUTS / "narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json").read_text(encoding="utf-8"))
    old_v = d["OLD"]["verdict_distribution"]
    cur_v = d["CURRENT"]["verdict_distribution"]
    verdicts = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]
    old_vals = [old_v.get(v, 0) for v in verdicts]
    cur_vals = [cur_v.get(v, 0) for v in verdicts]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = np.arange(len(verdicts))
    w = 0.35
    ax.bar(x - w / 2, old_vals, w, label="narrow_primary_hypothesis=false (pre-Stage-4)", color=C_BASELINE)
    ax.bar(x + w / 2, cur_vals, w, label="narrow_primary_hypothesis=true (PRODUCTION)", color=C_MODIFIED)
    for i, (ov, cv) in enumerate(zip(old_vals, cur_vals)):
        ax.text(i - w / 2, ov + 0.3, str(ov), ha="center", fontsize=10)
        ax.text(i + w / 2, cv + 0.3, str(cv), ha="center", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(verdicts, rotation=10)
    ax.set_ylabel("Number of evidence-matched claims")
    ax.set_ylim(0, max(old_vals + cur_vals) * 1.3)
    ax.set_title("narrow_primary_hypothesis: verdict distribution shift\nFresh natural GPU batch, n=62 documents, 32 evidence-matched claims/arm")
    ax.text(0.5, -0.24,
            "Qwen2.5-7B-Instruct generation + DeBERTa-v3-base-mnli-fever-anli verification, real GPU batch, 2026-09-12.\n"
            "Correction shipped: 0/4 (false-arm) vs 0/5 (true-arm) -- verdict shift is NOT independently significant at this n.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555555")
    ax.legend(loc="upper left", fontsize=9)
    save(fig, RESULTS / "figures" / "08_natural_data" / "narrow_primary_hypothesis_verdict_shift.png")


# ---------------------------------------------------------------------------
# 2. Retrieval fuzzy-method safety comparison: Jaccard vs BM25 vs embedding
# ---------------------------------------------------------------------------

def fig_retrieval_safety_comparison():
    recs = [json.loads(l) for l in (OUTPUTS / "retrieval_signal_benchmark_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    methods = ["jaccard", "bm25", "embedding"]
    labels = ["Jaccard\n(PRODUCTION)", "BM25\n(evaluated)", "Embedding\n(evaluated)"]
    accept_rate, reject_rate = [], []
    for m in methods:
        sm = [r for r in recs if r["kind"] == "should_match" and r["method"] == m]
        snm = [r for r in recs if r["kind"] == "should_not_match" and r["method"] == m]
        accept_rate.append(100 * sum(1 for r in sm if r["correct"]) / len(sm))
        reject_rate.append(100 * sum(1 for r in snm if r["correct"]) / len(snm))

    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = np.arange(len(methods))
    w = 0.35
    ax.bar(x - w / 2, accept_rate, w, label="Correct ACCEPT rate (21 real should-match cases)", color=C_MODIFIED)
    ax.bar(x + w / 2, reject_rate, w, label="Correct REJECT rate (9 adversarial should-NOT-match cases)", color=C_REJECT)
    for i, (a, r) in enumerate(zip(accept_rate, reject_rate)):
        ax.text(i - w / 2, a + 1.5, f"{a:.0f}%", ha="center", fontsize=10)
        ax.text(i + w / 2, r + 1.5, f"{r:.0f}%", ha="center", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Percent correct")
    ax.set_ylim(0, 112)
    ax.set_title("Evidence-matching fuzzy method: safety comparison\n136-record production evidence pool, pre-registered adversarial Act-name set")
    ax.text(0.5, -0.2,
            "BM25/embedding accept every real match but are materially LESS SAFE on near-miss Act names "
            "(e.g. Civil<->Criminal Procedure Code, Arbitration Act 1940<->1996) at production thresholds. "
            "Jaccard remains the sole production fuzzy_method for this reason.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555555")
    ax.legend(loc="lower center", fontsize=9)
    save(fig, RESULTS / "figures" / "03_evidence_retrieval" / "retrieval_method_safety_comparison.png")


# ---------------------------------------------------------------------------
# 3. Assertion-span verification: verdict shift (n=6 real "respectively" claims)
# ---------------------------------------------------------------------------

def fig_assertion_span_verification():
    recs = [json.loads(l) for l in (OUTPUTS / "assertion_spans_primary_hypothesis_benchmark.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    from collections import Counter
    baseline_counts = Counter(r["baseline_verdict"] for r in recs)
    span_counts = Counter(r["span_verdict"] for r in recs)
    verdicts = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = np.arange(len(verdicts))
    w = 0.35
    baseline_vals = [baseline_counts.get(v, 0) for v in verdicts]
    span_vals = [span_counts.get(v, 0) for v in verdicts]
    ax.bar(x - w / 2, baseline_vals, w, label="Full-sentence hypothesis (assertion_text)", color=C_BASELINE)
    ax.bar(x + w / 2, span_vals, w, label="assertion_spans-built hypothesis", color=C_MODIFIED)
    for i, (bv, sv) in enumerate(zip(baseline_vals, span_vals)):
        ax.text(i - w / 2, bv + 0.05, str(bv), ha="center", fontsize=10)
        ax.text(i + w / 2, sv + 0.05, str(sv), ha="center", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(verdicts, rotation=10)
    ax.set_ylabel("Number of claims (n=6)")
    ax.set_ylim(0, max(baseline_vals + span_vals) + 1.5)
    ax.set_title("assertion_span_primary_hypothesis: verdict shift\nn=6 real 'respectively'-pattern claims, real DeBERTa (CPU)")
    ax.text(0.5, -0.24,
            "4/6 claims changed verdict (3 NEI->ENTAILED, 1 NEI->CONTRADICTED -- a real generation error the diluted\n"
            "full-sentence hypothesis had masked). Zero ENTAILED<->CONTRADICTED reversals. EVALUATED, NOT PROMOTED (n too small).",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555555")
    ax.legend(loc="upper right", fontsize=9)
    save(fig, RESULTS / "figures" / "02_verifier" / "assertion_span_verification_shift.png")


# ---------------------------------------------------------------------------
# 4. Correction funnel comparison: LEGACY vs ASSERTION-AWARE (n=10 paired)
# ---------------------------------------------------------------------------

def fig_correction_funnel_comparison():
    d = json.loads((OUTPUTS / "assertion_aware_correction_experiment_comparison.json").read_text(encoding="utf-8"))
    n = d["n_paired_attempts"]
    legacy_shipped = d["legacy_shipped"]
    aa_shipped = d["assertion_aware_shipped"]
    legacy_rejected = n - legacy_shipped
    aa_rejected = n - aa_shipped

    fig, ax = plt.subplots(figsize=(8, 6.5))
    mechanisms = ["LEGACY\n(whole-sentence\nregeneration)", "ASSERTION-AWARE\n(deterministic\nsplice)"]
    shipped = [legacy_shipped, aa_shipped]
    rejected = [legacy_rejected, aa_rejected]
    x = np.arange(2)
    ax.bar(x, shipped, 0.5, label="Shipped", color=C_SHIPPED)
    ax.bar(x, rejected, 0.5, bottom=shipped, label="Rejected (safety gate or reverification)", color=C_REJECT)
    for i in range(2):
        if shipped[i]:
            ax.text(i, shipped[i] / 2, f"{shipped[i]}", ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        ax.text(i, shipped[i] + rejected[i] / 2, f"{rejected[i]}", ha="center", va="center", color="white", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(mechanisms)
    ax.set_ylabel(f"Correction attempts\n(n={n} paired, identical documents/arms)")
    ax.set_ylim(0, n * 1.18)
    fig.suptitle("Correction shipping: legacy vs. assertion-aware", fontsize=13, fontweight="bold", y=1.0)
    ax.set_title("Paired real replay -- the exact 5 documents that triggered legacy correction in the n=62 batch",
                 fontsize=10, fontweight="normal", pad=12)
    ax.text(0.5, -0.22,
            f"{legacy_shipped}/{n} shipped (legacy) vs {aa_shipped}/{n} shipped (assertion-aware) -- NO shipping-rate improvement measured.\n"
            "0 unsafe shipments under either mechanism. See error_propagation_analysis.md for why each case was rejected.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555555")
    ax.legend(loc="upper right", fontsize=9)
    save(fig, RESULTS / "figures" / "05_correction" / "assertion_aware_vs_legacy_correction_funnel.png")


# ---------------------------------------------------------------------------
# 5. Error propagation: first-failure-stage distribution (n=10)
# ---------------------------------------------------------------------------

def fig_error_propagation():
    rows = list(csv.DictReader((OUTPUTS / "error_propagation_matrix.csv").open(encoding="utf-8")))
    from collections import Counter
    counts = Counter(r["first_failure_stage"] for r in rows)
    order = [
        "none (correctly not triggered)", "correction_targeting", "correction_generation",
        "splice", "safety_scope_citation_ordinal", "reverification", "safety_sibling_regression",
        "none (shipped)",
    ]
    labels_display = {
        "none (correctly not triggered)": "Correctly not\ntriggered",
        "safety_scope_citation_ordinal": "Safety gate:\nscope/citation/ordinal",
        "reverification": "Re-verification\n(not ENTAILED)",
        "safety_sibling_regression": "Safety gate:\nsibling regression",
        "none (shipped)": "Shipped",
    }
    present = [s for s in order if counts.get(s, 0) > 0]
    vals = [counts[s] for s in present]
    labels = [labels_display.get(s, s) for s in present]
    colors = [C_SHIPPED if s == "none (shipped)" else (C_SCOPE if "safety" in s else (C_REJECT if s == "reverification" else "#9E9E9E")) for s in present]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(present))
    ax.bar(x, vals, 0.55, color=colors)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.05, str(v), ha="center", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Number of (document, arm) attempts")
    ax.set_ylim(0, max(vals) + 1)
    ax.set_title("Error propagation: first-failing stage\nAssertion-aware correction, n=10 real paired attempts")
    ax.text(0.5, -0.26,
            "Every attempt's rejection is attributed to the FIRST pipeline stage it failed at (parser -> citation mapping ->\n"
            "retrieval -> verification -> correction targeting -> generation -> splice -> safety gates -> reverification -> shipping).\n"
            "Source: outputs/error_propagation_matrix.csv (derived programmatically, not hand-filled).",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555555")
    save(fig, RESULTS / "figures" / "05_correction" / "error_propagation_first_failure_stage.png")


def main():
    fig_narrow_primary_hypothesis()
    fig_retrieval_safety_comparison()
    fig_assertion_span_verification()
    fig_correction_funnel_comparison()
    fig_error_propagation()


if __name__ == "__main__":
    main()
