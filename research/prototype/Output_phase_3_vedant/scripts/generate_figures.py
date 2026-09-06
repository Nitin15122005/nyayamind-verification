#!/usr/bin/env python3
"""Phase 3 (Vedant) — STEP 2: render every metric figure from the locked CSVs in
Output_phase_3_vedant/metrics/.

This script NEVER opens a source experiment artifact. It reads only the CSVs
produced by build_metric_tables.py, so every plotted number is already traced.

Each figure is rendered twice:
  * figures/<name>.png            — publication density (200 dpi)
  * ppt_assets/figures/<name>.png — 16:9 landscape, presentation type sizes

Matplotlib only, no seaborn, no randomness.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import numpy as np  # noqa: E402

PPT = False           # set by the runner
MANIFEST: list[dict] = []

DPI = 200
PPT_SIZE = (13.333, 7.5)


# --------------------------------------------------------------------------
# style helpers
# --------------------------------------------------------------------------
def S(pub: float, ppt: float) -> float:
    return ppt if PPT else pub


def new_fig(w: float, h: float, nrows: int = 1, ncols: int = 1, **kw):
    size = PPT_SIZE if PPT else (w, h)
    fig, ax = plt.subplots(nrows, ncols, figsize=size, **kw)
    return fig, ax


def adjust(fig, top=None, bottom=None, left=None, right=None, **kw):
    """subplots_adjust with extra breathing room in PPT mode, where type is ~1.4x larger."""
    if PPT:
        if bottom is not None:
            bottom = min(0.44, bottom + 0.085)
        if top is not None:
            top = max(0.62, top - 0.035)
        if left is not None:
            left = min(0.32, left + 0.05)
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right, **kw)


def T(long_text: str, short_text: str) -> str:
    """Use the compact wording on PPT slides, the full wording in the print figure."""
    return short_text if PPT else long_text


def apply_rc():
    base = 13.5 if PPT else 9.5
    plt.rcParams.update({
        "figure.dpi": DPI, "savefig.dpi": DPI,
        "font.size": base,
        "axes.titlesize": base + (3 if PPT else 2.5),
        "axes.titleweight": "bold",
        "axes.labelsize": base + (1 if PPT else 0.5),
        "xtick.labelsize": base - (0 if PPT else 0.5),
        "ytick.labelsize": base - (0 if PPT else 0.5),
        "legend.fontsize": base - (1 if PPT else 0.5),
        "axes.grid": False,
        "figure.autolayout": False,
    })


def titleblock(fig, title: str, subtitle: str) -> None:
    fig.suptitle(title, fontsize=S(13, 20), fontweight="bold", y=0.985)
    fig.text(0.5, 0.925 if not PPT else 0.930, subtitle, ha="center",
             va="top", fontsize=S(8.5, 13), color="#333333")


def footer(fig, source: str, dataset: str, n: str, status: str, caveat: str) -> None:
    """Provenance strip on every figure: source artifact, dataset, n, freshness, caveat."""
    line1 = f"Source: {source}"
    line2 = f"Dataset: {dataset}   |   n = {n}   |   Status: {status}"
    line3 = f"Caveat: {caveat}"
    width = 150 if PPT else 175
    txt = "\n".join(
        "\n".join(textwrap.wrap(s, width)) for s in (line1, line2, line3)
    )
    fig.text(0.012, 0.012, txt, ha="left", va="bottom",
             fontsize=S(6.6, 9.5), color="#444444", family="DejaVu Sans")


def save(fig, name: str) -> Path:
    out = (C.OUT_PPT_FIG if PPT else C.OUT_FIGURES) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def register(fig_id, name, title, purpose, metric_csvs, source, dataset, n,
             system_designation, status, grade, caveat):
    if PPT:
        return
    MANIFEST.append({
        "artifact_id": fig_id,
        "artifact_type": "figure",
        "filename": f"figures/{name}",
        "ppt_variant": f"ppt_assets/figures/{name}",
        "title": title,
        "purpose": purpose,
        "metric_contract_csv": " ; ".join(metric_csvs),
        "source_artifact": source,
        "dataset": dataset,
        "n": n,
        "system_model_names": system_designation,
        "baseline_or_modified": "baseline vs modified" if "vs" in system_designation.lower()
                                else system_designation,
        "fresh_or_historical": status,
        "evidence_grade": grade,
        "caveat": caveat,
        "generation_script": "Output_phase_3_vedant/scripts/generate_figures.py",
    })


def bar_labels(ax, bars, fmt="{:.3f}", fs=None, offset=0.012):
    fs = fs or S(8, 12)
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + offset, fmt.format(h),
                ha="center", va="bottom", fontsize=fs, fontweight="bold")


def stack_label(ax, xi, bottom, value, total, colour, dark_text=False,
                side_offset=0.34, min_frac=0.10, y_nudge=0.0):
    """Label one segment of a stacked bar.

    Segments large enough to hold their own label get it centred inside; thin
    segments get an offset label with a connector line, so small but important
    counts (ENTAILED, CONTRADICTED) are never overplotted onto each other.
    """
    if value <= 0:
        return
    centre = bottom + value / 2
    if value / total >= min_frac:
        ax.text(xi, centre, f"{int(value)}", ha="center", va="center",
                fontsize=S(8.5, 12.5), fontweight="bold",
                color="#222222" if dark_text else "white")
        return
    ax.annotate(f"{int(value)}", xy=(xi + 0.24, centre),
                xytext=(xi + side_offset, centre + y_nudge), ha="left", va="center",
                fontsize=S(7.8, 11.5), fontweight="bold", color=colour,
                arrowprops=dict(arrowstyle="-", color=colour, lw=1.0,
                                shrinkA=0, shrinkB=1))


SHORT_POP = {
    "Synthetic stress — baseline (bare premise)": "Synthetic stress\nbaseline (bare)",
    "Synthetic stress — modified (labeled premise)": "Synthetic stress\nmodified (labeled)",
    "Natural targeted — baseline framing (Arm B, bare)": "Natural targeted\nbaseline (bare)",
    "Natural targeted — modified framing (labeled)": "Natural targeted\nmodified (labeled)",
    "Natural cumulative — all correction attempts, project history":
        "Natural cumulative\n(project history)",
}

NUDGE = {"ENTAILED": -0.035, "CONTRADICTED": 0.045}

SYSTEMS_LINE = (f"Baseline: NyayaMind v0 (pre-2026-08-27) vs Modified: NyayaMind "
                f"2026-08-27 production  |  {C.SHARED_STACK}")


# ==========================================================================
# F01 — headline comparison
# ==========================================================================
def f01():
    rows = C.read_csv(C.OUT_METRICS / "M01_headline_baseline_vs_modified.csv")
    labels = [r["metric_label"] for r in rows]
    base = [float(r["baseline_value"]) for r in rows]
    mod = [float(r["modified_value"]) for r in rows]
    x = np.arange(len(rows))
    w = 0.36
    fig, ax = new_fig(11.5, 6.6)
    b1 = ax.bar(x - w / 2, base, w, color=C.C_BASELINE, edgecolor="black", linewidth=0.6,
                label=C.BASELINE_LABEL_1L)
    b2 = ax.bar(x + w / 2, mod, w, color=C.C_MODIFIED, edgecolor="black", linewidth=0.6,
                label=C.MODIFIED_LABEL_1L)
    bar_labels(ax, b1)
    bar_labels(ax, b2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{lab}\nn = {r['n']}  ·  {r['metric_class'].split(' (')[0]}"
                        for lab, r in zip(labels, rows)], fontsize=S(8.5, 12))
    ax.set_ylim(0, 1.12)
    ax.set_ylabel(T("Metric value (0–1 scale; each bar's own unit — see x-axis)",
                    "Metric value (0–1)"))
    ax.set_xlabel(T("Metric (heterogeneous types — bar heights are NOT interchangeable across groups)",
                    "Metric (heterogeneous types — not interchangeable)"),
                  labelpad=12)
    fig.legend(handles=[b1, b2], loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, 0.115), frameon=True)
    ax.yaxis.grid(True, linestyle=":", alpha=0.45)
    ax.set_axisbelow(True)
    titleblock(fig, "Headline comparison: baseline NyayaMind v0 vs modified NyayaMind production",
               SYSTEMS_LINE)
    footer(fig,
           "gold01_metrics.json; gold02_metrics.json; paired_209_metrics.json; ABLATION_SUMMARY.json "
           "(via metrics/M01_headline_baseline_vs_modified.csv)",
           "GOLD-01 controlled benchmark; GOLD-02 synthetic stress; 209-claim paired natural",
           "420 / 420 / 59 / 209", "FRESH (all four arms, CPU)",
           "Four different kinds of measurement plotted on one axis for scale only. Evidence "
           "coverage is a retrieval metric on unlabelled natural data and is NOT accuracy; "
           "GOLD-01/GOLD-02 are labelled benchmarks and do not transfer to natural text.")
    adjust(fig, top=0.855, bottom=0.335, left=0.075, right=0.985)
    save(fig, "F01_headline_baseline_vs_modified.png")
    register("F01", "F01_headline_baseline_vs_modified.png",
             "Headline comparison: baseline NyayaMind v0 vs modified NyayaMind production",
             "Show the four strongest supported baseline/modified comparisons at a glance",
             ["M01_headline_baseline_vs_modified.csv"],
             "gold01_metrics.json; gold02_metrics.json; paired_209_metrics.json",
             "GOLD-01; GOLD-02; 209-claim paired natural", "420 / 59 / 209",
             "Baseline vs Modified", "FRESH", "A",
             "Heterogeneous metrics on one axis; not interchangeable.")


# ==========================================================================
# F02 — GOLD-01 accuracy / macro F1
# ==========================================================================
def f02():
    rows = C.read_csv(C.OUT_METRICS / "M02_gold01_overall.csv")
    names = {"accuracy": "Accuracy", "macro_f1": "Macro F1"}
    labels = [names[r["metric"]] for r in rows]
    base = [float(r["baseline_bare"]) for r in rows]
    mod = [float(r["modified_labeled"]) for r in rows]
    x = np.arange(len(rows))
    w = 0.34
    fig, ax = new_fig(9.5, 6.3)
    b1 = ax.bar(x - w / 2, base, w, color=C.C_BASELINE, edgecolor="black", linewidth=0.6,
                label="Baseline: bare premise (statute text only)")
    b2 = ax.bar(x + w / 2, mod, w, color=C.C_MODIFIED, edgecolor="black", linewidth=0.6,
                label="Modified: labeled premise (\"Section N of Act: <statute text>\")")
    bar_labels(ax, b1, "{:.4f}")
    bar_labels(ax, b2, "{:.4f}")
    for i, r in enumerate(rows):
        ax.annotate(f"+{float(r['delta']):.4f}", xy=(i, max(base[i], mod[i]) + 0.075),
                    ha="center", fontsize=S(9, 13), fontweight="bold", color=C.C_MODIFIED)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.16)
    ax.set_ylabel("Score against GOLD labels (fraction, 0–1)")
    ax.set_xlabel("Verifier metric")
    ax.legend(loc="lower right", frameon=True)
    ax.yaxis.grid(True, linestyle=":", alpha=0.45)
    ax.set_axisbelow(True)
    r0 = rows[0]
    titleblock(fig,
               "Verifier accuracy and macro F1 on the GOLD-01 controlled benchmark (n = 420)",
               f"Verifier {r0['verifier_model']} · threshold {r0['confidence_threshold']} · "
               f"device {r0['device']} · McNemar χ²={float(r0['mcnemar_statistic']):.2f}, "
               f"p={float(r0['mcnemar_p_value']):.2e} (exact sign test "
               f"p={float(r0['exact_sign_test_p_value']):.2e})")
    footer(fig, "evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json "
                "(via metrics/M02_gold01_overall.csv)",
           "GOLD-01_controlled_verifier_benchmark", "420", "FRESH (CPU, no GPU used)",
           "GOLD-01 items are curated, mechanically constructed hypotheses. This is verifier "
           "benchmark performance, NOT legal correctness and NOT a natural-text accuracy claim.")
    adjust(fig, top=0.845, bottom=0.185, left=0.095, right=0.975)
    save(fig, "F02_gold01_accuracy_macro_f1.png")
    register("F02", "F02_gold01_accuracy_macro_f1.png",
             "Verifier accuracy and macro F1 on the GOLD-01 controlled benchmark",
             "Quantify the premise-framing lever on labelled ground truth",
             ["M02_gold01_overall.csv"],
             "evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json",
             "GOLD-01_controlled_verifier_benchmark", "420", "Baseline vs Modified",
             "FRESH (CPU)", "A", "Benchmark performance, not legal correctness.")


# ==========================================================================
# F03 — GOLD-01 per-class precision / recall / F1
# ==========================================================================
def f03():
    rows = C.read_csv(C.OUT_METRICS / "M03_gold01_per_class.csv")
    classes = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]
    metrics = ["precision", "recall", "f1"]
    fig, axes = new_fig(12.5, 5.6, 1, 3, sharey=True)
    for ax, m in zip(axes, metrics):
        base = [float(next(r for r in rows if r["system"] == "baseline" and r["class"] == c)[m])
                for c in classes]
        mod = [float(next(r for r in rows if r["system"] == "modified" and r["class"] == c)[m])
               for c in classes]
        x = np.arange(len(classes))
        w = 0.36
        b1 = ax.bar(x - w / 2, base, w, color=C.C_BASELINE, edgecolor="black", linewidth=0.5)
        b2 = ax.bar(x + w / 2, mod, w, color=C.C_MODIFIED, edgecolor="black", linewidth=0.5)
        bar_labels(ax, b1, "{:.2f}", fs=S(7, 10.5))
        bar_labels(ax, b2, "{:.2f}", fs=S(7, 10.5))
        ax.set_title(m.replace("f1", "F1").capitalize() if m != "f1" else "F1",
                     fontsize=S(10.5, 15))
        ax.set_xticks(x)
        ax.set_xticklabels(["ENTAILED", "CONTRA-\nDICTED", "NOT_ENOUGH_\nINFORMATION"],
                           fontsize=S(7.5, 11))
        ax.set_ylim(0, 1.16)
        ax.yaxis.grid(True, linestyle=":", alpha=0.45)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Score against GOLD labels (0–1)")
    axes[1].set_xlabel("Verifier verdict class (support: ENTAILED 184, CONTRADICTED 118, NEI 118)", labelpad=12)
    fig.legend(handles=[mpatches.Patch(facecolor=C.C_BASELINE, edgecolor="black",
                                       label="Baseline: bare premise framing"),
                        mpatches.Patch(facecolor=C.C_MODIFIED, edgecolor="black",
                                       label="Modified: labeled premise framing")],
               loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.105), frameon=True)
    titleblock(fig, "Per-class precision, recall and F1 — GOLD-01 controlled benchmark (n = 420)",
               f"Verifier {C.VERIFICATION_MODEL} · confidence threshold {C.CONF_THRESHOLD} · CPU · "
               "identical model and threshold in both systems; only the premise framing differs")
    footer(fig, "evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json "
                "(via metrics/M03_gold01_per_class.csv)",
           "GOLD-01_controlled_verifier_benchmark", "420 (184 / 118 / 118 per class)",
           "FRESH (CPU)",
           "Precision and recall are computed here ONLY because GOLD-01 carries real per-item "
           "labels. No natural-data figure in this package reports precision or recall.")
    adjust(fig, top=0.815, bottom=0.30, left=0.07, right=0.985, wspace=0.12)
    save(fig, "F03_gold01_per_class_precision_recall_f1.png")
    register("F03", "F03_gold01_per_class_precision_recall_f1.png",
             "Per-class precision, recall and F1 — GOLD-01 controlled benchmark",
             "Show where the premise-framing gain actually lands (ENTAILED recall 0.50 → 1.00)",
             ["M03_gold01_per_class.csv"],
             "evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json",
             "GOLD-01_controlled_verifier_benchmark", "420", "Baseline vs Modified",
             "FRESH (CPU)", "A", "Legitimate only because GOLD-01 has per-item labels.")


# ==========================================================================
# F04 — GOLD-01 confusion matrices
# ==========================================================================
def f04():
    rows = C.read_csv(C.OUT_METRICS / "M04_gold01_confusion.csv")
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]
    short = ["ENTAILED", "CONTRADICTED", "NEI"]
    fig, axes = new_fig(11.5, 5.8, 1, 2)
    panels = [("baseline", "Baseline: NyayaMind v0 — bare premise framing", C.C_BASELINE),
              ("modified", "Modified: NyayaMind production — labeled premise framing", C.C_MODIFIED)]
    for ax, (sysname, title, colour) in zip(axes, panels):
        mat = np.zeros((3, 3), dtype=int)
        for r in rows:
            if r["system"] != sysname:
                continue
            mat[order.index(r["true_label"]), order.index(r["predicted_label"])] = int(r["count"])
        ax.imshow(mat, cmap="Blues", vmin=0, vmax=200)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, str(mat[i, j]), ha="center", va="center",
                        fontsize=S(11, 16), fontweight="bold",
                        color="white" if mat[i, j] > 110 else "#111111")
        ax.set_xticks(range(3)); ax.set_xticklabels(short, fontsize=S(8.5, 12))
        ax.set_yticks(range(3)); ax.set_yticklabels(short, fontsize=S(8.5, 12))
        ax.set_xlabel("Predicted verdict (verifier output)")
        ax.set_ylabel("True verdict (GOLD label)")
        correct = int(np.trace(mat))
        ax.set_title(f"{title}\nCorrect on diagonal: {correct} / {mat.sum()} items",
                     fontsize=S(9.5, 13.5), pad=10, color=colour)
    titleblock(fig, "Verifier confusion matrices — GOLD-01 controlled benchmark (n = 420)",
               f"Verifier {C.VERIFICATION_MODEL} · threshold {C.CONF_THRESHOLD} · CPU · "
               "NEI = NOT_ENOUGH_INFORMATION")
    footer(fig, "evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json "
                "(via metrics/M04_gold01_confusion.csv)",
           "GOLD-01_controlled_verifier_benchmark", "420", "FRESH (CPU)",
           "Confusion counts are verifier decisions against GOLD-01's own labels. The dominant "
           "baseline failure is 92 true-ENTAILED items answered NEI, because a bare premise never "
           "names the provision the claim attributes the rule to.")
    adjust(fig, top=0.80, bottom=0.235, left=0.085, right=0.98, wspace=0.32)
    save(fig, "F04_gold01_confusion_matrices.png")
    register("F04", "F04_gold01_confusion_matrices.png",
             "Verifier confusion matrices — GOLD-01 controlled benchmark",
             "Expose the exact error structure behind the accuracy difference",
             ["M04_gold01_confusion.csv"],
             "evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json",
             "GOLD-01_controlled_verifier_benchmark", "420", "Baseline vs Modified",
             "FRESH (CPU)", "A", "Benchmark labels, not legal ground truth.")


# ==========================================================================
# F05 — GOLD-02 synthetic stress
# ==========================================================================
def f05():
    rows = C.read_csv(C.OUT_METRICS / "M05_gold02_synthetic_stress.csv")
    base = next(r for r in rows if r["system"] == "baseline")
    mod = next(r for r in rows if r["system"] == "modified")
    fig, axes = new_fig(12.0, 5.9, 1, 2)

    ax = axes[0]
    vals = [float(base["contradiction_recall"]), float(mod["contradiction_recall"])]
    bars = ax.bar(["Baseline\n(bare premise)", "Modified\n(labeled premise)"], vals,
                  color=[C.C_BASELINE, C.C_MODIFIED], edgecolor="black", linewidth=0.6, width=0.5)
    bar_labels(ax, bars, "{:.4f}")
    ax.set_ylim(0, 0.62)
    ax.set_ylabel("Contradiction recall (detected / 59 corrupted claims)")
    ax.set_xlabel("System configuration")
    ax.set_title("Contradiction recall", fontsize=S(10.5, 15))
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)

    ax = axes[1]
    cats = ["Detected\nCONTRADICTED", "Missed as\nNEI", "Unreachable\n(NO_EVIDENCE)"]
    b = [int(base["detected_contradicted"]), int(base["missed_as_nei"]), int(base["no_evidence"])]
    m = [int(mod["detected_contradicted"]), int(mod["missed_as_nei"]), int(mod["no_evidence"])]
    x = np.arange(3); w = 0.36
    r1 = ax.bar(x - w / 2, b, w, color=C.C_BASELINE, edgecolor="black", linewidth=0.5,
                label="Baseline (bare premise)")
    r2 = ax.bar(x + w / 2, m, w, color=C.C_MODIFIED, edgecolor="black", linewidth=0.5,
                label="Modified (labeled premise)")
    bar_labels(ax, r1, "{:.0f}", offset=0.4)
    bar_labels(ax, r2, "{:.0f}", offset=0.4)
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=S(8, 11.5))
    ax.set_ylabel("Claims (count of 59)")
    ax.set_xlabel("Outcome for a claim that is contradictory by construction")
    ax.set_title("Outcome split for all 59 corrupted claims", fontsize=S(10.5, 15))
    ax.set_ylim(0, 34)
    ax.legend(frameon=True, loc="upper right")
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)

    titleblock(fig, "Contradiction detection on the GOLD-02 synthetic stress set (n = 59)",
               f"Verifier {C.VERIFICATION_MODEL} · CPU · every record is CONTRADICTED by "
               "construction (src/synthetic_stress.py) · CONTRADICTED precision = 1.00 in both systems")
    footer(fig, "evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json "
                "(via metrics/M05_gold02_synthetic_stress.csv)",
           "GOLD-02_synthetic_stress_set", "59 (15 unreachable — no evidence record)",
           "FRESH (CPU)",
           "Deliberately corrupted claims. This measures detection sensitivity on adversarial "
           "input; it is NOT an accuracy figure for natural legal text, where no comparable "
           "contradiction base rate exists.")
    adjust(fig, top=0.825, bottom=0.235, left=0.075, right=0.985, wspace=0.28)
    save(fig, "F05_gold02_synthetic_contradiction_detection.png")
    register("F05", "F05_gold02_synthetic_contradiction_detection.png",
             "Contradiction detection on the GOLD-02 synthetic stress set",
             "Show adversarial detection sensitivity and its residual failure mode",
             ["M05_gold02_synthetic_stress.csv"],
             "evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json",
             "GOLD-02_synthetic_stress_set", "59", "Baseline vs Modified", "FRESH (CPU)", "A",
             "Contradictory by construction; not a natural-data accuracy claim.")


# ==========================================================================
# F06 — evidence coverage, 209 paired
# ==========================================================================
def f06():
    rows = C.read_csv(C.OUT_METRICS / "M06_evidence_coverage_209_paired.csv")
    disc = C.read_csv(C.OUT_METRICS / "M06b_evidence_209_discordance.csv")[0]
    base = next(r for r in rows if r["system"] == "baseline")
    mod = next(r for r in rows if r["system"] == "modified")
    fig, axes = new_fig(12.0, 6.0, 1, 2, gridspec_kw={"width_ratios": [1, 1.25]})

    ax = axes[0]
    vals = [float(base["evidence_coverage"]), float(mod["evidence_coverage"])]
    labels = [f"Baseline\nevidence pool v0\n({base['evidence_pool_size']} usable records)",
              f"Modified\nevidence pool v0+v1\n({mod['evidence_pool_size']} usable records)"]
    bars = ax.bar(labels, vals, color=[C.C_BASELINE, C.C_MODIFIED],
                  edgecolor="black", linewidth=0.6, width=0.52)
    for bar, r in zip(bars, (base, mod)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{bar.get_height() * 100:.1f}%\n({r['n_matched']} / {r['n_claims']} claims)",
                ha="center", va="bottom", fontsize=S(8.5, 12.5), fontweight="bold")
    ax.set_ylim(0, 0.88)
    ax.set_ylabel(T("Evidence coverage (fraction of claims matched to a usable record)",
                    "Evidence coverage (fraction)"))
    ax.set_xlabel("Canonical evidence pool")
    ax.set_title("Observed evidence coverage", fontsize=S(10.5, 15))
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.text(0.5, max(vals) + 0.115, f"+{(vals[1] - vals[0]) * 100:.1f} pp", ha="center",
            fontsize=S(9.5, 14), fontweight="bold", color=C.C_MODIFIED,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#EDF2F8",
                      edgecolor=C.C_MODIFIED))

    ax = axes[1]
    cats = ["Gained evidence\n(baseline miss →\nmodified match)",
            "Lost evidence\n(baseline match →\nmodified miss)",
            "Unchanged:\nmatched in both",
            "Unchanged:\nno evidence in both"]
    counts = [int(disc["gained_evidence_b"]), int(disc["lost_evidence_c"]),
              int(disc["unchanged_matched"]), int(disc["unchanged_no_evidence"])]
    cols = [C.C_SHIPPED, C.C_REJECT, "#9FB6CC", "#CFCFCF"]
    bars = ax.bar(cats, counts, color=cols, edgecolor="black", linewidth=0.5, width=0.62)
    bar_labels(ax, bars, "{:.0f}", offset=2)
    ax.set_ylabel("Claims (count of 209 paired claims)")
    ax.set_xlabel("Per-claim paired outcome")
    ax.set_ylim(0, max(counts) * 1.18)
    ax.tick_params(axis="x", labelsize=S(7.5, 11))
    ax.set_title(f"Paired discordance — McNemar χ² = {float(disc['mcnemar_chi2']):.2f}, "
                 f"p = {float(disc['mcnemar_p_value']):.2e}", fontsize=S(10.5, 15))
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)

    titleblock(fig, "Evidence retrieval coverage on 209 paired natural claims "
                    "(evidence corpus v0 vs v0+v1)",
               "Same 50 NyayaRAG cases, same Qwen2.5-7B-Instruct generation pass, evidence matched "
               "independently per arm; zero claims lost evidence")
    footer(fig, "evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json "
                "(via metrics/M06_evidence_coverage_209_paired.csv, M06b_evidence_209_discordance.csv)",
           "209_claim_paired_natural_evaluation", "209 claims from 50 cases",
           "FRESH REPRODUCTION (CPU re-matching and re-verification)",
           "METRIC-ONLY. Coverage measures whether retrieval surfaced a record — it does NOT "
           "measure whether the record is legally right for the claim, and NO_EVIDENCE does not "
           "mean the citation was wrong.")
    adjust(fig, top=0.835, bottom=0.245, left=0.075, right=0.985, wspace=0.28)
    save(fig, "F06_evidence_coverage_209_paired.png")
    register("F06", "F06_evidence_coverage_209_paired.png",
             "Evidence retrieval coverage on 209 paired natural claims",
             "The strongest natural-data baseline/modified result in the project",
             ["M06_evidence_coverage_209_paired.csv", "M06b_evidence_209_discordance.csv"],
             "evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json",
             "209_claim_paired_natural_evaluation", "209", "Baseline vs Modified",
             "FRESH REPRODUCTION (CPU)", "A", "Retrieval coverage, never accuracy.")


# ==========================================================================
# F07 — corpus-level evidence coverage over 588 claims
# ==========================================================================
def f07():
    rows = C.read_csv(C.OUT_METRICS / "M07_evidence_coverage_588_corpus.csv")
    base = next(r for r in rows if r["system"] == "baseline")
    mod = next(r for r in rows if r["system"] == "modified")
    fig, ax = new_fig(9.5, 6.1)
    labels = ["Baseline: evidence pool v0\n(59 usable records)",
              "Modified: evidence pool v0+v1\n(136 usable records)"]
    matched = [int(base["n_matched"]), int(mod["n_matched"])]
    total = int(base["n_claims"])
    unmatched = [total - matched[0], total - matched[1]]
    b1 = ax.bar(labels, matched, 0.5, color=[C.C_BASELINE, C.C_MODIFIED],
                edgecolor="black", linewidth=0.6, label="Claim matched to a usable evidence record")
    ax.bar(labels, unmatched, 0.5, bottom=matched, color="#E4E4E4", edgecolor="black",
           linewidth=0.6, label="Claim resolved to NO_EVIDENCE")
    for i, (mv, r) in enumerate(zip(matched, (base, mod))):
        ax.text(i, mv / 2, f"{mv} matched\n({float(r['coverage_pct']):.1f}%)", ha="center",
                va="center", fontsize=S(9.5, 14), fontweight="bold", color="white")
        ax.text(i, mv + unmatched[i] / 2, f"{unmatched[i]}\nNO_EVIDENCE", ha="center",
                va="center", fontsize=S(8.5, 12.5), color="#333333")
    ax.text(1, total + 14, f"+{int(mod['newly_covered'])} claims newly covered by evidence v1",
            ha="center", fontsize=S(9, 13), fontweight="bold", color=C.C_MODIFIED)
    ax.set_ylim(0, total * 1.14)
    ax.set_ylabel(T("Claims (count of 588 pooled natural claims)", "Claims (count of 588)"))
    ax.set_xlabel("Canonical evidence pool")
    ax.legend(loc="lower right", frameon=True)
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    titleblock(fig, "Corpus-level evidence coverage over all 588 pooled natural claims",
               "Every claim extracted by the deterministic parser across every natural experiment "
               "in the project, re-matched against each evidence pool")
    footer(fig, "research/prototype/outputs/evidence_coverage_v0_vs_v1.json "
                "(via metrics/M07_evidence_coverage_588_corpus.csv)",
           "588 pooled natural claims (all experiments)", "588",
           "HISTORICAL (corpus-level replay, CPU)",
           "Corpus-level replay, not a paired-arm experiment — it complements, and does not "
           "replace, the paired 209-claim result. Coverage is not accuracy.")
    adjust(fig, top=0.845, bottom=0.20, left=0.11, right=0.975)
    save(fig, "F07_evidence_coverage_588_corpus.png")
    register("F07", "F07_evidence_coverage_588_corpus.png",
             "Corpus-level evidence coverage over all 588 pooled natural claims",
             "Show the evidence-pool change at the largest available claim scale",
             ["M07_evidence_coverage_588_corpus.csv"],
             "research/prototype/outputs/evidence_coverage_v0_vs_v1.json",
             "588 pooled natural claims", "588", "Baseline vs Modified",
             "HISTORICAL (CPU replay)", "B", "Corpus-level, not paired-arm.")


# ==========================================================================
# F08 — verdict distributions
# ==========================================================================
def f08():
    rows = C.read_csv(C.OUT_METRICS / "M08_verdict_distribution.csv")
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION", "NO_EVIDENCE"]
    groups = [("209_claim_paired_natural_evaluation", "baseline",
               "Baseline evidence pool v0\n(209 paired claims)"),
              ("209_claim_paired_natural_evaluation", "modified",
               "Modified evidence pool v0+v1\n(209 paired claims)"),
              ("588_claim_natural_aggregate", "modified",
               "Modified production config\n(588-claim aggregate)")]
    fig, ax = new_fig(11.0, 6.2)
    x = np.arange(len(groups))
    bottoms = np.zeros(len(groups))
    totals = np.array([sum(int(r["count"]) for r in rows
                           if r["dataset"] == ds and r["system"] == sysname)
                       for ds, sysname, _ in groups], dtype=float)
    for v in order:
        vals = []
        for ds, sysname, _ in groups:
            vals.append(int(next(r for r in rows if r["dataset"] == ds and r["system"] == sysname
                                 and r["verdict"] == v)["count"]))
        vals = np.array(vals, dtype=float)
        ax.bar(x, vals, 0.55, bottom=bottoms, color=C.VERDICT_COLORS[v],
               edgecolor="black", linewidth=0.5, label=v)
        for xi, (val, bt) in enumerate(zip(vals, bottoms)):
            stack_label(ax, xi, bt, val, totals[xi], C.VERDICT_COLORS[v],
                        dark_text=(v == "NOT_ENOUGH_INFORMATION"),
                        y_nudge=NUDGE.get(v, 0.0) * totals[xi])
        bottoms += vals
    ax.set_xticks(x)
    ax.set_xticklabels([g[2] for g in groups], fontsize=S(8.5, 12))
    ax.set_ylabel("Claims (count)")
    ax.set_xlabel("Natural-data evaluation set and configuration")
    ax.set_ylim(0, max(bottoms) * 1.20)
    ax.legend(title="Verifier verdict", frameon=True, loc="upper left", ncol=2)
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    titleblock(fig, "Verifier verdict distribution on natural NyayaRAG claims",
               f"Verifier {C.VERIFICATION_MODEL} · labeled premise framing · threshold "
               f"{C.CONF_THRESHOLD} · CPU · NO_EVIDENCE means retrieval found no record, "
               "so the verifier was never called")
    footer(fig, "paired_209_metrics.json; claims_588_metrics.json "
                "(via metrics/M08_verdict_distribution.csv)",
           "209-claim paired natural; 588-claim natural aggregate", "209 / 209 / 588",
           "FRESH (CPU)",
           "METRIC-ONLY and strictly descriptive. These are the NLI model's own verdicts; no "
           "independent correctness label exists for any natural claim in this project, so this "
           "figure must never be read as accuracy.")
    adjust(fig, top=0.835, bottom=0.235, left=0.09, right=0.98)
    save(fig, "F08_verdict_distribution_natural.png")
    register("F08", "F08_verdict_distribution_natural.png",
             "Verifier verdict distribution on natural NyayaRAG claims",
             "Describe what the verifier actually outputs on real generated text",
             ["M08_verdict_distribution.csv"],
             "paired_209_metrics.json; claims_588_metrics.json",
             "209-claim paired; 588-claim aggregate", "209 / 588",
             "Baseline vs Modified (209) plus Modified-only (588)", "FRESH (CPU)",
             "n/a (descriptive)", "Verdict counts are not correctness labels.")


# ==========================================================================
# F09 — premise framing on natural batches
# ==========================================================================
def f09():
    rows = C.read_csv(C.OUT_METRICS / "M09_premise_framing_natural_batches.csv")
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION", "NO_EVIDENCE"]
    fig, axes = new_fig(12.2, 6.0, 1, 2)
    for ax, batch in zip(axes, ("batch1", "batch2")):
        sub = [r for r in rows if r["batch"] == batch]
        n_claims = int(sub[0]["n_claims"])
        cov = float(sub[0]["evidence_coverage"])
        x = np.arange(2)
        bottoms = np.zeros(2)
        for v in order:
            vals = np.array([
                int(next(r for r in sub if r["system"] == s and r["verdict"] == v)["count"])
                for s in ("baseline", "modified")], dtype=float)
            ax.bar(x, vals, 0.5, bottom=bottoms, color=C.VERDICT_COLORS[v],
                   edgecolor="black", linewidth=0.5, label=v if batch == "batch1" else None)
            for xi, (val, bt) in enumerate(zip(vals, bottoms)):
                stack_label(ax, xi, bt, val, float(n_claims), C.VERDICT_COLORS[v],
                            dark_text=(v == "NOT_ENOUGH_INFORMATION"), side_offset=0.31,
                            y_nudge=NUDGE.get(v, 0.0) * n_claims)
            bottoms += vals
        ax.set_xticks(x)
        ax.set_xticklabels(["Baseline\nbare premise", "Modified\nlabeled premise"],
                           fontsize=S(8.5, 12))
        ax.set_xlim(-0.55, 1.75)
        ax.set_ylim(0, n_claims * 1.1)
        ax.set_ylabel("Claims (count)")
        ax.set_xlabel("Premise framing")
        ax.set_title(f"natural_candidates {batch} — {n_claims} claims from 50 cases\n"
                     f"identical claims and identical evidence pool v0 "
                     f"(coverage {cov * 100:.1f}% in both arms)", fontsize=S(9.5, 13.5))
        ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    fig.legend(loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.108), frameon=True,
               title="Verifier verdict")
    titleblock(fig, "Premise framing on real natural data — verdict decisiveness at fixed retrieval",
               "Evidence coverage is identical within each pair, so every difference below is "
               "attributable to the premise-framing lever alone")
    footer(fig, "evaluation/actual_outputs/natural_data_runs/batches/batches_analysis.json "
                "(via metrics/M09_premise_framing_natural_batches.csv)",
           "natural_candidates batch1 and batch2 (GPU-generated, historical)",
           "251 (batch1) / 236 (batch2)", "HISTORICAL (generation on GPU; tabulated fresh)",
           "METRIC-ONLY. More ENTAILED verdicts means the verifier reached a decisive answer more "
           "often — NOT that more claims were shown to be legally correct.")
    adjust(fig, top=0.815, bottom=0.31, left=0.075, right=0.985, wspace=0.24)
    save(fig, "F09_premise_framing_natural_batches.png")
    register("F09", "F09_premise_framing_natural_batches.png",
             "Premise framing on real natural data — verdict decisiveness at fixed retrieval",
             "Isolate the framing lever on natural text with retrieval held constant",
             ["M09_premise_framing_natural_batches.csv"],
             "evaluation/actual_outputs/natural_data_runs/batches/batches_analysis.json",
             "natural_candidates batch1 / batch2", "251 / 236", "Baseline vs Modified",
             "HISTORICAL", "B", "Decisiveness, not measured correctness.")


# ==========================================================================
# F10 — 147-claim framing shift
# ==========================================================================
def f10():
    rows = C.read_csv(C.OUT_METRICS / "M10_natural_147_framing_shift.csv")
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]
    fig, ax = new_fig(9.8, 6.1)
    x = np.arange(3); w = 0.36
    base = [int(next(r for r in rows if r["system"] == "baseline" and r["verdict"] == v)["count"])
            for v in order]
    mod = [int(next(r for r in rows if r["system"] == "modified" and r["verdict"] == v)["count"])
           for v in order]
    b1 = ax.bar(x - w / 2, base, w, color=C.C_BASELINE, edgecolor="black", linewidth=0.6,
                label="Baseline: bare premise framing")
    b2 = ax.bar(x + w / 2, mod, w, color=C.C_MODIFIED, edgecolor="black", linewidth=0.6,
                label="Modified: labeled premise framing")
    bar_labels(ax, b1, "{:.0f}", offset=2)
    bar_labels(ax, b2, "{:.0f}", offset=2)
    ax.set_xticks(x)
    ax.set_xticklabels(["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_\nINFORMATION"], fontsize=S(9, 13))
    ax.set_ylabel(T("Claims (count of the same 147 evidence-matched claims)",
                    "Claims (count of 147)"))
    ax.set_xlabel("Verifier verdict")
    ax.set_ylim(0, 168)
    ax.legend(frameon=True, loc="upper left")
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    flips = rows[0]["n_verdict_flips"]
    ax.text(0.98, 0.72, f"{flips} of 147 verdicts changed\nCONTRADICTED count unchanged (3 → 3)",
            transform=ax.transAxes, ha="right", va="top", fontsize=S(8.5, 12.5),
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#F4F4F4", edgecolor="#999999"))
    titleblock(fig, "Premise framing on the same 147 evidence-matched natural claims",
               "Verification-only re-run: identical generated text, identical matched evidence "
               "records, identical threshold — only the premise framing differs")
    footer(fig, "research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json "
                "(via metrics/M10_natural_147_framing_shift.csv)",
           "final_validation Arm B evidence-matched subset", "147", "HISTORICAL (CPU re-run)",
           "METRIC-ONLY. ENTAILED 0 → 13 counts verdicts reached, not claims proven correct; the "
           "project's own counter-signal on an older provisional-label set is recorded in "
           "FINAL_PRODUCTION_CONFIG.md §1 and is not suppressed here.")
    adjust(fig, top=0.845, bottom=0.20, left=0.10, right=0.975)
    save(fig, "F10_natural_147_framing_shift.png")
    register("F10", "F10_natural_147_framing_shift.png",
             "Premise framing on the same 147 evidence-matched natural claims",
             "Paired natural-data evidence for the framing lever",
             ["M10_natural_147_framing_shift.csv"],
             "research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json",
             "final_validation Arm B evidence-matched subset", "147", "Baseline vs Modified",
             "HISTORICAL (CPU)", "B", "Verdicts reached, not correctness.")


# ==========================================================================
# F11 — confidence distribution
# ==========================================================================
def f11():
    rows = C.read_csv(C.OUT_METRICS / "M11_confidence_by_verdict_588.csv")
    rows = [r for r in rows if r["verdict"] != "ALL evidence-matched"] + \
           [r for r in rows if r["verdict"] == "ALL evidence-matched"]
    fig, ax = new_fig(10.2, 6.1)
    y = np.arange(len(rows))
    for i, r in enumerate(rows):
        colour = C.VERDICT_COLORS.get(r["verdict"], "#6B6B6B")
        if r["min_confidence"]:
            lo, hi = float(r["min_confidence"]), float(r["max_confidence"])
            ax.plot([lo, hi], [i, i], color=colour, lw=S(3.5, 5), alpha=0.35,
                    solid_capstyle="round")
            ax.plot([lo, lo], [i - 0.12, i + 0.12], color=colour, lw=1.4)
            ax.plot([hi, hi], [i - 0.12, i + 0.12], color=colour, lw=1.4)
        ax.plot(float(r["mean_confidence"]), i, "o", color=colour, markersize=S(9, 13),
                markeredgecolor="black", markeredgewidth=0.7, zorder=3)
        ax.plot(float(r["median_confidence"]), i, "D", color="white", markersize=S(6, 9),
                markeredgecolor=colour, markeredgewidth=1.6, zorder=4)
        ax.text(1.012, i, f"mean {float(r['mean_confidence']):.3f}   "
                          f"median {float(r['median_confidence']):.3f}   n={r['n']}",
                va="center", fontsize=S(8, 11.5))
    thr = float(rows[0]["confidence_threshold"])
    ax.axvline(thr, color=C.C_REJECT, linestyle="--", lw=1.5)
    ax.annotate(f"production confidence\nthreshold = {thr}", xy=(thr, -0.62),
                xytext=(thr - 0.30, -0.80), ha="center", va="top",
                fontsize=S(7.5, 11), color=C.C_REJECT,
                annotation_clip=False,
                arrowprops=dict(arrowstyle="->", color=C.C_REJECT, lw=1.1))
    ax.set_yticks(y)
    ax.set_yticklabels([r["verdict"].replace("NOT_ENOUGH_INFORMATION", "NOT_ENOUGH_\nINFORMATION")
                        for r in rows], fontsize=S(8.5, 12))
    ax.set_xlim(0.3, 1.02)
    ax.set_xlabel(T("Verifier confidence — softmax probability of the argmax NLI class (0–1)",
                    "Verifier confidence (softmax probability, 0–1)"))
    ax.set_ylabel("Verifier verdict")
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.legend(handles=[
        plt.Line2D([], [], marker="o", color="#555555", linestyle="", markersize=S(8, 11),
                   label="Mean confidence"),
        plt.Line2D([], [], marker="D", color="white", markeredgecolor="#555555", linestyle="",
                   markersize=S(6, 9), label="Median confidence"),
        plt.Line2D([], [], color="#999999", lw=S(3.5, 5), alpha=0.4, label="Observed min–max range"),
    ], loc="lower left", frameon=True)
    titleblock(fig, "Verifier confidence distribution by verdict — 588-claim natural aggregate",
               f"Modified NyayaMind production configuration · verifier {C.VERIFICATION_MODEL} · "
               "labeled premise framing · CPU · 390 of 588 claims were evidence-matched and scored")
    footer(fig, "evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json "
                "(via metrics/M11_confidence_by_verdict_588.csv)",
           "588_claim_natural_aggregate", "390 evidence-matched claims of 588", "FRESH (CPU)",
           "Confidence is the model's own statistical certainty. High confidence does NOT mean the "
           "verdict is legally correct — src/verifier.py stamps this disclaimer on every result.")
    adjust(fig, top=0.845, bottom=0.235, left=0.155, right=0.72)
    save(fig, "F11_confidence_distribution_588.png")
    register("F11", "F11_confidence_distribution_588.png",
             "Verifier confidence distribution by verdict — 588-claim natural aggregate",
             "Show how decisively the verifier reaches each verdict on real claims",
             ["M11_confidence_by_verdict_588.csv"],
             "evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json",
             "588_claim_natural_aggregate", "390 of 588", "Modified only (no baseline arm exists)",
             "FRESH (CPU)", "n/a (descriptive)", "Confidence is not correctness.")


# ==========================================================================
# F12 — threshold sweep
# ==========================================================================
def f12():
    rows = C.read_csv(C.OUT_METRICS / "M12_confidence_threshold_sweep.csv")
    fig, ax = new_fig(10.0, 6.1)
    for sysname, colour, label, marker in (
        ("baseline", C.C_BASELINE, "Baseline: bare premise framing", "s"),
        ("modified", C.C_MODIFIED, "Modified: labeled premise framing", "o")):
        sub = sorted((r for r in rows if r["system"] == sysname),
                     key=lambda r: float(r["threshold"]))
        ax.plot([float(r["threshold"]) for r in sub], [float(r["macro_f1"]) for r in sub],
                marker=marker, color=colour, lw=2.0, markersize=S(6, 9), label=label)
    prod = float(rows[0]["production_threshold"])
    ax.axvline(prod, color=C.C_ACCENT, linestyle="--", lw=1.6)
    ax.text(prod + 0.006, 0.53, f"production threshold = {prod}\n(unchanged in both systems)",
            fontsize=S(8, 11.5), color=C.C_ACCENT, va="bottom")
    ax.set_xlabel("Confidence threshold for the low-confidence downgrade rule")
    ax.set_ylabel("Macro F1 on GOLD-01 (0–1)")
    ax.set_ylim(0.5, 1.02)
    ax.set_xlim(0.47, 0.98)
    ax.legend(frameon=True, loc="center left")
    ax.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    titleblock(fig, "Confidence-threshold sensitivity on GOLD-01 (n = 420), both premise framings",
               "Deterministic replay of the already-computed softmax distributions at each cutoff — "
               "no model re-inference, so this isolates the decision rule exactly")
    footer(fig, "research/prototype/outputs/threshold_sensitivity_analysis.json "
                "(via metrics/M12_confidence_threshold_sweep.csv)",
           "GOLD-01_controlled_verifier_benchmark (stored softmax replay)", "420",
           "FRESH (deterministic replay, CPU)",
           "A sensitivity description, not a threshold search. The production threshold was "
           "deliberately NOT moved to chase a metric; under labeled framing 0.70 already sits "
           "inside the optimal plateau.")
    adjust(fig, top=0.845, bottom=0.20, left=0.095, right=0.975)
    save(fig, "F12_confidence_threshold_sensitivity.png")
    register("F12", "F12_confidence_threshold_sensitivity.png",
             "Confidence-threshold sensitivity on GOLD-01, both premise framings",
             "Show the production threshold is in a flat, non-fragile region",
             ["M12_confidence_threshold_sweep.csv"],
             "research/prototype/outputs/threshold_sensitivity_analysis.json",
             "GOLD-01_controlled_verifier_benchmark", "420", "Baseline vs Modified",
             "FRESH (replay)", "B", "Sensitivity description, not a tuning result.")


# ==========================================================================
# F13 — correction funnel
# ==========================================================================
def f13():
    rows = C.read_csv(C.OUT_METRICS / "M13_correction_funnel.csv")
    fig, axes = new_fig(13.0, 6.2, 1, len(rows), sharey=False)
    stages = [("correction_triggered", "Triggered", "#6E9BC5"),
              ("scope_gate_rejected", "Scope-gate reject", C.C_SCOPE),
              ("reverification_not_entailed", "Re-verify reject", C.C_REJECT),
              ("shipped", "Shipped", C.C_SHIPPED)]
    for ax, r in zip(axes, rows):
        vals = [int(r[k]) for k, _, _ in stages]
        cols = [c for _, _, c in stages]
        bars = ax.bar(range(4), vals, color=cols, edgecolor="black", linewidth=0.5, width=0.68)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.03, str(v), ha="center",
                    va="bottom", fontsize=S(8.5, 12), fontweight="bold")
        ax.set_xticks(range(4))
        ax.set_xticklabels([lbl for _, lbl, _ in stages], fontsize=S(7, 8.5),
                           rotation=34, ha="right", rotation_mode="anchor")
        ax.set_ylim(0, max(vals) * 1.28 if max(vals) else 1)
        ax.set_title(SHORT_POP[r["population"]], fontsize=S(8, 9.5))
        ax.yaxis.grid(True, linestyle=":", alpha=0.4); ax.set_axisbelow(True)
        ax.text(0.5, -0.40, f"unsafe shipped: {r['unsafe_shipped']}", transform=ax.transAxes,
                ha="center", fontsize=S(7.5, 11), color=C.C_UNSAFE, fontweight="bold")
    axes[0].set_ylabel("Correction attempts (count)")
    titleblock(fig, "Selective-correction funnel — five populations kept strictly separate",
               f"Corrector {C.CORRECTION_MODEL} (reuses the loaded generator, 4-bit {C.QUANT}) · a correction "
               "ships only if re-verification returns ENTAILED · each panel has its own y-scale")
    footer(fig, "final_metrics.json; final_gpu_validation_metrics.json; "
                "labeled_correction_validation_gpu_metrics.json "
                "(via metrics/M13_correction_funnel.csv)",
           "synthetic stress; natural targeted; natural cumulative project history",
           "59 / 209 / 56", "HISTORICAL (GPU-dependent); two arms exactly reproduced in STEP 10/10B",
           "Populations must NEVER be pooled into one shipping rate — synthetic claims are "
           "contradictory by construction. The cumulative column is a project-history rollup with "
           "no single reproducible protocol.")
    adjust(fig, top=0.80, bottom=0.34, left=0.062, right=0.99, wspace=0.58)
    save(fig, "F13_correction_funnel.png")
    register("F13", "F13_correction_funnel.png",
             "Selective-correction funnel — five populations kept strictly separate",
             "Show where correction attempts are stopped, per population",
             ["M13_correction_funnel.csv"],
             "final_metrics.json; final_gpu_validation_metrics.json; labeled_correction_validation_gpu_metrics.json",
             "synthetic + natural targeted + natural cumulative", "59 / 209 / 56",
             "Baseline vs Modified (within each population)", "HISTORICAL (GPU)", "C",
             "Never pool populations into one rate.")


# ==========================================================================
# F14 — correction outcomes
# ==========================================================================
def f14():
    rows = C.read_csv(C.OUT_METRICS / "M14_correction_outcomes.csv")
    fig, ax = new_fig(11.5, 6.2)
    labels = [r["population"].replace(" — ", "\n") for r in rows]
    y = np.arange(len(rows))
    shipped = np.array([int(r["shipped"]) for r in rows], dtype=float)
    reverif = np.array([int(r["reverification_not_entailed"]) for r in rows], dtype=float)
    scope = np.array([int(r["scope_gate_rejected"]) for r in rows], dtype=float)
    ax.barh(y, shipped, 0.55, color=C.C_SHIPPED, edgecolor="black", linewidth=0.5,
            label="Shipped (re-verification returned ENTAILED)")
    ax.barh(y, reverif, 0.55, left=shipped, color=C.C_REJECT, edgecolor="black", linewidth=0.5,
            label="Rejected: re-verification not ENTAILED")
    ax.barh(y, scope, 0.55, left=shipped + reverif, color=C.C_SCOPE, edgecolor="black",
            linewidth=0.5, label="Rejected: scope-violation gate")
    for i, r in enumerate(rows):
        total = int(r["n_triggered"])
        rate = f"{float(r['shipped_rate']) * 100:.1f}%" if r["shipped_rate"] else "n/a"
        ax.text(total + max(shipped + reverif + scope) * 0.02, i,
                f"{r['shipped']} shipped of {total} triggered  ({rate})",
                va="center", fontsize=S(8.5, 12), fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=S(8, 11.5))
    ax.invert_yaxis()
    ax.set_xlabel("Correction attempts (count)")
    ax.set_ylabel("Evaluation population")
    ax.set_xlim(0, 84)
    ax.legend(loc="center right", frameon=True, bbox_to_anchor=(1.0, 0.45))
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    titleblock(fig, "Correction outcomes by population — shipped vs each rejection reason",
               "Every rejection path is a programmatic gate in src/pipeline.py; 0 unsafe "
               "corrections were shipped in any population")
    footer(fig, "final_metrics.json; final_gpu_validation_metrics.json; "
                "labeled_correction_validation_gpu_metrics.json "
                "(via metrics/M14_correction_outcomes.csv)",
           "synthetic stress; natural targeted; natural cumulative", "59 / 209 / 56",
           "HISTORICAL (GPU-dependent)",
           "The 0/5 → 1/10 natural shift is directional and isolated by design, but far too small "
           "for statistical support; 1/56 cumulative is not a stable rate estimate.")
    adjust(fig, top=0.845, bottom=0.205, left=0.235, right=0.985)
    save(fig, "F14_correction_outcomes.png")
    register("F14", "F14_correction_outcomes.png",
             "Correction outcomes by population — shipped vs each rejection reason",
             "Show that almost every correction attempt is stopped by a safety gate",
             ["M14_correction_outcomes.csv"],
             "final_metrics.json; final_gpu_validation_metrics.json; labeled_correction_validation_gpu_metrics.json",
             "synthetic + natural targeted + natural cumulative", "59 / 209 / 56",
             "Baseline vs Modified (within each population)", "HISTORICAL (GPU)", "C",
             "n too small for a statistical shipping-rate claim.")


# ==========================================================================
# F15 — safety observations
# ==========================================================================
def f15():
    rows = C.read_csv(C.OUT_METRICS / "M15_safety_observations.csv")
    fig, ax = new_fig(11.0, 5.9)
    labels = [textwrap.fill(r["safety_observation"], 34) for r in rows]
    vals = [int(r["count"]) for r in rows]
    cols = [C.C_UNSAFE if "Unsafe" in r["safety_observation"] else
            (C.C_SHIPPED if "shipped" in r["safety_observation"] else C.C_SCOPE) for r in rows]
    y = np.arange(len(rows))
    bars = ax.barh(y, vals, 0.55, color=cols, edgecolor="black", linewidth=0.6)
    for b, r in zip(bars, rows):
        ax.text(b.get_width() + 0.7, b.get_y() + b.get_height() / 2,
                f"{r['count']}   (of {r['denominator']})", va="center", fontsize=S(8, 11.5))
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=S(8, 11.5))
    ax.invert_yaxis()
    ax.set_xlabel("Observed count across the tested correction history")
    ax.set_ylabel("Safety mechanism / outcome")
    ax.set_xlim(0, 62)
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.text(0.985, 0.06, "0 unsafe corrections shipped\nin 122 tested correction attempts",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=S(9.5, 14),
            fontweight="bold", color=C.C_UNSAFE,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF3F3", edgecolor=C.C_UNSAFE))
    titleblock(fig, "Observed safety-gate behaviour across the full tested correction history",
               "Gates in src/pipeline.py: scope-violation check, sibling-regression re-verification, "
               "citation-identity preservation, and the ENTAILED-only shipping gate")
    footer(fig, "final_metrics.json; final_gpu_validation_metrics.json "
                "(via metrics/M15_safety_observations.csv)",
           "all tested correction attempts (56 natural + 66 synthetic)", "122",
           "HISTORICAL; STEP 10/10B reproductions added 0 further unsafe shipments",
           "0 observed unsafe shipments is an observation on a finite tested history — it is NOT "
           "a proof that unsafe shipments are impossible, and no safety probability is claimed.")
    adjust(fig, top=0.845, bottom=0.185, left=0.26, right=0.985)
    save(fig, "F15_safety_observations.png")
    register("F15", "F15_safety_observations.png",
             "Observed safety-gate behaviour across the full tested correction history",
             "Evidence the safety layer is the binding constraint, and that nothing unsafe shipped",
             ["M15_safety_observations.csv"],
             "final_metrics.json; final_gpu_validation_metrics.json",
             "all tested correction attempts", "122", "Modified system's gates (cumulative)",
             "HISTORICAL", "n/a (observed counts)",
             "Observed counts, not a safety guarantee.")


# ==========================================================================
# F16 — ablation matrix
# ==========================================================================
def f16():
    rows = C.read_csv(C.OUT_METRICS / "M16_ablation_matrix.csv")
    fig, ax = new_fig(12.0, 6.6)
    y = np.arange(len(rows))
    grades = [r["evidence_grade"] for r in rows]
    widths = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    vals = [widths.get(g, 0) for g in grades]
    cols = [C.GRADE_COLORS.get(g, "#999999") for g in grades]
    bars = ax.barh(y, vals, 0.6, color=cols, edgecolor="black", linewidth=0.6)
    for b, r in zip(bars, rows):
        bits = [f"grade {r['evidence_grade']}", r["classification"]]
        if r["p_value"]:
            bits.append(f"p={float(r['p_value']):.2e}")
        if r["n"]:
            bits.append(f"n={r['n']}")
        ax.text(b.get_width() + 0.09, b.get_y() + b.get_height() / 2, "   ".join(bits),
                va="center", fontsize=S(7.8, 11))
    friendly = {
        "evidence_v1": "Evidence corpus v1\n(use_evidence_v1)",
        "premise_framing": "Premise framing\n(bare → labeled)",
        "claim_parser_fix": "Claim-parser fix\n(commit 223eb9d)",
        "atomic_scope_check_assertion_spans": "Scope check mode\n(assertion_spans)",
        "narrow_reverification_hypothesis": "Narrow re-verification\nhypothesis",
        "confidence_threshold": "Confidence threshold\n(sensitivity sweep)",
        "correction_levers_combined (premise_framing isolated within an otherwise-fixed config)":
            "Correction levers combined\n(framing isolated)",
        "joint_four_lever_isolation": "Joint four-lever isolation\n(experiment absent)",
    }
    labels = [friendly.get(r["factor"], r["factor"]) for r in rows]
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=S(8, 11.5))
    ax.invert_yaxis()
    ax.set_xlim(0, 8.4)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["E\nnot isolable", "D", "C\ndiagnostic", "B\nsupported",
                        "A\nstrongly supported"], fontsize=S(7.5, 11))
    ax.set_xlabel("Evidence-strength grade (isolation + sample size + statistical support) — "
                  "NOT effect size")
    ax.set_ylabel("Ablation factor")
    ax.xaxis.grid(True, linestyle=":", alpha=0.4); ax.set_axisbelow(True)
    titleblock(fig, "Ablation evidence strength for all eight studied factors",
               "Grades are about how well a factor is evidenced, not how large its effect is; "
               "Grade E means the isolating experiment does not exist anywhere in the project")
    footer(fig, "evaluation/ablation/ABLATION_SUMMARY.json; evaluation/metrics/"
                "EVIDENCE_STRENGTH_MATRIX.csv (via metrics/M16_ablation_matrix.csv)",
           "8 named ablation factors", "varies per factor (3–420)",
           "MIXED — 2 FRESH, 1 FRESH REPRODUCTION, 1 HISTORICAL REPRODUCTION, 3 HISTORICAL, "
           "1 NOT EXECUTED",
           "No additive or interaction effect between the four production levers may be inferred: "
           "no experiment in this project varies all four from one common baseline in a single run.")
    adjust(fig, top=0.83, bottom=0.20, left=0.235, right=0.985)
    save(fig, "F16_ablation_evidence_strength.png")
    register("F16", "F16_ablation_evidence_strength.png",
             "Ablation evidence strength for all eight studied factors",
             "Communicate honestly how well each design decision is evidenced",
             ["M16_ablation_matrix.csv"],
             "evaluation/ablation/ABLATION_SUMMARY.json",
             "8 named ablation factors", "3–420 per factor", "Baseline vs Modified per factor",
             "MIXED", "A–E", "Grade is evidence strength, not effect size.")


# ==========================================================================
# F17 — runtime / resource
# ==========================================================================
def f17():
    rows = C.read_csv(C.OUT_METRICS / "M17_runtime_resource.csv")
    rows = [r for r in rows if r["runtime_seconds"]]
    fig, ax = new_fig(12.0, 6.3)
    y = np.arange(len(rows))
    vals = [float(r["runtime_seconds"]) for r in rows]
    cols = []
    for r in rows:
        if "CPU" in r["hardware"]:
            cols.append("#7FB37F")
        elif r["fresh_or_historical"].startswith("FRESH"):
            cols.append(C.C_FRESH)
        else:
            cols.append(C.C_HISTORICAL)
    bars = ax.barh(y, vals, 0.6, color=cols, edgecolor="black", linewidth=0.6)
    for b, r in zip(bars, rows):
        extra = f", peak VRAM {r['peak_vram_mib']} MiB" if str(r["peak_vram_mib"]).isdigit() else ""
        ax.text(b.get_width() + 22, b.get_y() + b.get_height() / 2,
                f"{float(r['runtime_seconds']):.1f} s (n={r['n_cases']}{extra})",
                va="center", fontsize=S(7.8, 11))
    ax.set_yticks(y)
    ax.set_yticklabels([textwrap.fill(r["arm"], 42) for r in rows], fontsize=S(7.5, 10.5))
    ax.invert_yaxis()
    ax.set_xlabel("Wall-clock runtime (seconds)")
    ax.set_ylabel("Experiment arm")
    ax.set_xlim(0, max(vals) * 1.42)
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.legend(handles=[
        mpatches.Patch(facecolor=C.C_HISTORICAL, edgecolor="black", label="Historical GPU run"),
        mpatches.Patch(facecolor=C.C_FRESH, edgecolor="black",
                       label="Fresh GPU reproduction (STEP 10 / 10B)"),
        mpatches.Patch(facecolor="#7FB37F", edgecolor="black", label="Fresh CPU-only run"),
    ], loc="lower right", frameon=True)
    titleblock(fig, "Runtime and peak VRAM per experiment arm — GPU and CPU rows kept separate",
               f"Generator {C.GENERATION_MODEL} 4-bit {C.QUANT} on a 6 GB NVIDIA RTX 4050 Laptop "
               f"class GPU; verifier {C.VERIFICATION_MODEL} runs on CPU or GPU")
    footer(fig, "final_gpu_validation_metrics.json; final_metrics.json; gold01_metrics.json; "
                "step10b_final_gpu_validation_metrics.json; "
                "labeled_correction_validation_gpu_metrics.fresh.json "
                "(via metrics/M17_runtime_resource.csv)",
           "mixed experiment arms", "10 / 50 / 59 / 420",
           "MIXED — historical GPU, fresh GPU reproduction, and fresh CPU arms all labelled",
           "Wall-clock time is a hardware, thermal and background-load measure, not a correctness "
           "measure. GPU and CPU arms are never compared against each other as if equivalent.")
    adjust(fig, top=0.845, bottom=0.185, left=0.26, right=0.985)
    save(fig, "F17_runtime_resource.png")
    register("F17", "F17_runtime_resource.png",
             "Runtime and peak VRAM per experiment arm",
             "Give the mentor a realistic cost picture for each stage",
             ["M17_runtime_resource.csv"],
             "final_gpu_validation_metrics.json; final_metrics.json; gold01_metrics.json",
             "mixed experiment arms", "10–420", "Baseline vs Modified within paired arms",
             "MIXED", "n/a (resource)", "Runtime is not a correctness measure.")


# ==========================================================================
# F18 — natural regimes coverage
# ==========================================================================
def f18():
    rows = C.read_csv(C.OUT_METRICS / "M18_natural_regimes_coverage.csv")
    rows = sorted(rows, key=lambda r: float(r["evidence_coverage"]))
    fig, ax = new_fig(11.5, 6.4)
    y = np.arange(len(rows))
    vals = [float(r["evidence_coverage"]) for r in rows]
    cols = [C.C_FRESH if r["fresh_or_historical"] == "FRESH" else C.C_HISTORICAL for r in rows]
    bars = ax.barh(y, vals, 0.62, color=cols, edgecolor="black", linewidth=0.5)
    for b, r in zip(bars, rows):
        ax.text(b.get_width() + 0.008, b.get_y() + b.get_height() / 2,
                f"{b.get_width() * 100:.1f}%  ({r['n_evidence_matched']}/{r['n_claims']} claims, "
                f"{r['n_cases']} cases)", va="center", fontsize=S(7.6, 11))
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['regime']}\n{textwrap.fill(r['configuration'], 46)}" for r in rows],
                       fontsize=S(7, 10))
    ax.set_xlim(0, 1.02)
    ax.set_xlabel(T("Evidence coverage (fraction of extracted claims matched to a usable record)",
                    "Evidence coverage (fraction of claims)"))
    ax.set_ylabel("Natural-data evaluation regime")
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.legend(handles=[
        mpatches.Patch(facecolor=C.C_FRESH, edgecolor="black", label="Fresh (this evaluation workspace)"),
        mpatches.Patch(facecolor=C.C_HISTORICAL, edgecolor="black", label="Historical (prior session)"),
    ], loc="lower right", frameon=True)
    titleblock(fig, "Evidence coverage across every natural-data regime in the project",
               "Regimes differ in case selection, evidence pool and premise framing and are "
               "reported separately — this project never pools them into a single headline number")
    footer(fig, "batches_analysis.json; paired_209_metrics.json; claims_588_metrics.json "
                "(via metrics/M18_natural_regimes_coverage.csv)",
           "11 natural-data regimes", "29–588 claims per regime",
           "MIXED — 3 FRESH, 8 HISTORICAL (each row labelled)",
           "The spread across regimes reflects different case samples, not a trend over time, and "
           "coverage is never an accuracy measure.")
    adjust(fig, top=0.845, bottom=0.185, left=0.30, right=0.985)
    save(fig, "F18_natural_regimes_coverage.png")
    register("F18", "F18_natural_regimes_coverage.png",
             "Evidence coverage across every natural-data regime in the project",
             "Give the honest spread rather than a single flattering number",
             ["M18_natural_regimes_coverage.csv"],
             "batches_analysis.json; paired_209_metrics.json; claims_588_metrics.json",
             "11 natural-data regimes", "29–588", "Mixed baseline and modified regimes",
             "MIXED", "n/a (descriptive)", "Not a trend; regimes are not comparable samples.")


# ==========================================================================
# F19 — synthetic vs natural transfer
# ==========================================================================
def f19():
    rows = C.read_csv(C.OUT_METRICS / "M19_synthetic_vs_natural_transfer.csv")
    fig, ax = new_fig(10.0, 6.1)
    labels = [textwrap.fill(r["population"], 26) for r in rows]
    vals = [float(r["shipped_rate_pct"]) for r in rows]
    cols = [C.C_GOLD, C.C_NATURAL, C.C_NATURAL]
    bars = ax.bar(labels, vals, 0.52, color=cols, edgecolor="black", linewidth=0.6)
    for b, r in zip(bars, rows):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.6,
                f"{b.get_height():.1f}%\n({r['shipped']} / {r['triggered']} attempts)",
                ha="center", va="bottom", fontsize=S(8.5, 12.5), fontweight="bold")
    ax.set_ylim(0, 95)
    ax.set_ylabel(T("Corrections shipped as a percentage of corrections triggered (%)",
                    "Corrections shipped (% of triggered)"))
    ax.set_xlabel("Evaluation population")
    ax.tick_params(axis="x", labelsize=S(8, 11.5))
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.text(0.5, 0.62, "DISJOINT POPULATIONS — NOT DIRECTLY COMPARABLE\n"
                       "Synthetic claims are contradictory by construction;\n"
                       "natural claims have no comparable base rate",
            transform=ax.transAxes, ha="center", va="center", fontsize=S(9, 13),
            fontweight="bold", color=C.C_UNSAFE,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#FFF3F3", edgecolor=C.C_UNSAFE))
    titleblock(fig, "Correction shipping rate: synthetic stress set vs natural data",
               "Presented specifically to show the transfer gap — these bars measure different "
               "things and must not be read as one trend")
    footer(fig, "research/prototype/outputs/final_metrics.json "
                "(via metrics/M19_synthetic_vs_natural_transfer.csv)",
           "GOLD-02-derived synthetic corrections vs natural correction attempts",
           "36 / 56 / 10", "HISTORICAL (GPU-dependent)",
           "72.2% and 1.8% do NOT measure the same capability. Neither rate predicts the other, "
           "and the natural n is far too small for a rate estimate.")
    adjust(fig, top=0.845, bottom=0.215, left=0.10, right=0.975)
    save(fig, "F19_synthetic_vs_natural_transfer.png")
    register("F19", "F19_synthetic_vs_natural_transfer.png",
             "Correction shipping rate: synthetic stress set vs natural data",
             "State the synthetic-to-natural transfer gap explicitly rather than hiding it",
             ["M19_synthetic_vs_natural_transfer.csv"],
             "research/prototype/outputs/final_metrics.json",
             "synthetic vs natural correction attempts", "36 / 56 / 10",
             "Modified system across two populations", "HISTORICAL (GPU)", "D",
             "Disjoint populations; never plot as a single trend.")


# ==========================================================================
# F20 — NO_EVIDENCE taxonomy
# ==========================================================================
def f20():
    rows = C.read_csv(C.OUT_METRICS / "M20_no_evidence_taxonomy.csv")
    rows = sorted(rows, key=lambda r: -int(r["count"]))
    fig, ax = new_fig(11.0, 6.0)
    y = np.arange(len(rows))
    vals = [int(r["count"]) for r in rows]
    cols = ["#8FA9C4", "#A9BFD4", "#C7D4E0", C.C_REJECT]
    bars = ax.barh(y, vals, 0.58, color=cols[:len(rows)], edgecolor="black", linewidth=0.6)
    total = int(rows[0]["n_no_evidence_with_citation"])
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 2, b.get_y() + b.get_height() / 2,
                f"{v}  ({v / total * 100:.1f}% of {total} NO_EVIDENCE claims)",
                va="center", fontsize=S(8, 11.5))
    ax.set_yticks(y)
    ax.set_yticklabels([textwrap.fill(r["bucket_label"], 36) for r in rows], fontsize=S(7.8, 11))
    ax.invert_yaxis()
    ax.set_xlim(0, total * 0.92)
    ax.set_xlabel("Claims (count)")
    ax.set_ylabel("Reason retrieval returned NO_EVIDENCE")
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    r0 = rows[0]
    ax.text(0.985, 0.06,
            f"{r0['n_matched_total']} of {r0['n_claims_total']} claims matched evidence; "
            f"{total} did not\n0 confirmed parser or matcher defects across all "
            f"{r0['n_claims_total']} claims",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=S(8.5, 12),
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F4F4F4", edgecolor="#999999"))
    titleblock(fig, "Why claims resolve to NO_EVIDENCE — audit over all 797 claims in the project",
               "Deterministic evidence matcher (exact normalised key, then fuzzy act-name fallback) "
               "against the 136-record canonical corpus")
    footer(fig, "research/prototype/outputs/no_evidence_taxonomy_v3.json "
                "(via metrics/M20_no_evidence_taxonomy.csv)",
           "797 pooled claims from every natural experiment", "797 (260 NO_EVIDENCE)",
           "HISTORICAL (audit re-run, CPU)",
           "A NO_EVIDENCE claim is NOT shown to be wrong. The corpus holds ~140 provisions, so "
           "most unmatched citations simply fall outside it — a documented corpus limitation, "
           "not a detected error.")
    adjust(fig, top=0.845, bottom=0.185, left=0.26, right=0.985)
    save(fig, "F20_no_evidence_taxonomy.png")
    register("F20", "F20_no_evidence_taxonomy.png",
             "Why claims resolve to NO_EVIDENCE — audit over all 797 claims",
             "Explain the dominant natural-data outcome honestly",
             ["M20_no_evidence_taxonomy.csv"],
             "research/prototype/outputs/no_evidence_taxonomy_v3.json",
             "797 pooled claims", "797 (260 NO_EVIDENCE)", "Modified system's retrieval stage",
             "HISTORICAL", "B", "NO_EVIDENCE is a corpus limit, not a detected error.")


# ==========================================================================
# F21 — parser fix
# ==========================================================================
def f21():
    rows = C.read_csv(C.OUT_METRICS / "M21_parser_fix_n30.csv")
    numeric = [r for r in rows if str(r["baseline_pre_fix_parser"]).isdigit()]
    outcome = next(r for r in rows if not str(r["baseline_pre_fix_parser"]).isdigit())
    fig, ax = new_fig(10.0, 6.1)
    x = np.arange(len(numeric)); w = 0.36
    base = [int(r["baseline_pre_fix_parser"]) for r in numeric]
    mod = [int(r["modified_post_fix_parser"]) for r in numeric]
    b1 = ax.bar(x - w / 2, base, w, color=C.C_BASELINE, edgecolor="black", linewidth=0.6,
                label="Baseline: pre-fix claim parser")
    b2 = ax.bar(x + w / 2, mod, w, color=C.C_MODIFIED, edgecolor="black", linewidth=0.6,
                label="Modified: post-fix claim parser (commit 223eb9d)")
    bar_labels(ax, b1, "{:.0f}", offset=1.2)
    bar_labels(ax, b2, "{:.0f}", offset=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels([textwrap.fill(r["measure"], 20) for r in numeric], fontsize=S(8.5, 12))
    ax.set_ylabel("Claims (count, across the same 30 generated texts)")
    ax.set_xlabel("Parser output measure")
    ax.set_ylim(0, 112)
    ax.legend(frameon=True, loc="upper right")
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.text(0.035, 0.40,
            f"Per-case outcome:\n{outcome['modified_post_fix_parser']},\n"
            f"{outcome['baseline_pre_fix_parser']}\n\n"
            f"{outcome['statistical_test']},\np = {outcome['p_value']}",
            transform=ax.transAxes, ha="left", va="center", fontsize=S(8.5, 12),
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F4F4F4", edgecolor="#999999"))
    titleblock(fig, "Claim-parser fix (commit 223eb9d) — re-parse of the same 30 generated texts",
               "A code-version ablation, measured separately from the four configuration levers; "
               "same texts, same evidence-pool snapshot, only the parser differs")
    footer(fig, "research/prototype/outputs/parser_fix_before_after_n30.json; "
                "evaluation/ablation/ABLATION_SUMMARY.json (via metrics/M21_parser_fix_n30.csv)",
           "n30_reparse", "30 cases (88 vs 93 extracted claims)",
           "HISTORICAL REPRODUCTION — the pre-fix code was NOT re-executed; the sign test was "
           "recomputed fresh from the stored per-case artifact",
           "Claim segmentation itself changes with the fix (88 → 93 claims), so this is not a "
           "strict 1:1 paired-claim comparison, and it says nothing about legal accuracy.")
    adjust(fig, top=0.845, bottom=0.20, left=0.10, right=0.975)
    save(fig, "F21_claim_parser_fix_n30.png")
    register("F21", "F21_claim_parser_fix_n30.png",
             "Claim-parser fix (commit 223eb9d) — re-parse of the same 30 generated texts",
             "Show the one code-level (not configuration-level) improvement measured in the project",
             ["M21_parser_fix_n30.csv"],
             "research/prototype/outputs/parser_fix_before_after_n30.json",
             "n30_reparse", "30 cases", "Baseline vs Modified (parser code version)",
             "HISTORICAL REPRODUCTION", "B", "Not a 1:1 paired-claim comparison.")


# ==========================================================================
# F22 — GPU reproduction crosscheck
# ==========================================================================
def f22():
    rows = C.read_csv(C.OUT_METRICS / "M22_gpu_reproduction_crosscheck.csv")
    fig, ax = new_fig(11.5, 6.3)
    y = np.arange(len(rows)); w = 0.36
    hist = [float(r["historical_value"]) for r in rows]
    fresh = [float(r["fresh_value"]) for r in rows]
    ax.barh(y - w / 2, hist, w, color=C.C_HISTORICAL, edgecolor="black", linewidth=0.5,
            label="Historical run (2026-08-27)")
    ax.barh(y + w / 2, fresh, w, color=C.C_FRESH, edgecolor="black", linewidth=0.5,
            label="Fresh GPU reproduction (STEP 10 / 10B, second machine)")
    for i, r in enumerate(rows):
        mark = "MATCH" if r["match"] == "True" else "DIFFERS"
        ax.text(max(hist[i], fresh[i]) + 3.2, i,
                f"{r['historical_value']} vs {r['fresh_value']}   {mark}", va="center",
                fontsize=S(7.8, 11), fontweight="bold",
                color=C.C_SHIPPED if r["match"] == "True" else C.C_REJECT)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['experiment'].replace('209-claim paired generation, ', '209-claim, ')}\n"
                        f"{r['quantity']}" for r in rows], fontsize=S(7, 10))
    ax.invert_yaxis()
    ax.set_xlabel("Value (count — units differ per row, see labels)")
    ax.set_ylabel("Experiment and quantity")
    ax.set_xlim(0, 235)
    ax.legend(loc="lower right", frameon=True, bbox_to_anchor=(1.0, 0.0))
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    n_match = sum(1 for r in rows if r["match"] == "True")
    ax.text(0.985, 0.24, f"{n_match} of {len(rows)} compared quantities match exactly\n"
                         "50/50 generated texts and 10/10 corrected texts byte-identical",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=S(8.5, 12),
            fontweight="bold", color=C.C_SHIPPED,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F1F8F1", edgecolor=C.C_SHIPPED))
    titleblock(fig, "GPU reproducibility crosscheck — historical run vs fresh re-execution",
               f"Generator {C.GENERATION_MODEL} 4-bit {C.QUANT}, greedy decoding (do_sample=false), "
               "seed 42; unmodified production code path on a second GPU machine")
    footer(fig, "final_gpu_validation_metrics.json; step10b_final_gpu_validation_metrics.json; "
                "labeled_correction_validation_gpu_metrics.json (+ .fresh.json) "
                "(via metrics/M22_gpu_reproduction_crosscheck.csv)",
           "209-claim paired generation experiment; 10-case targeted correction validation",
           "209 claims / 10 correction attempts",
           "FRESH GPU REPRODUCTION compared against HISTORICAL",
           "Exact reproduction evidences pipeline determinism across machines. It adds no new "
           "statistical evidence and says nothing about legal correctness.")
    adjust(fig, top=0.845, bottom=0.185, left=0.245, right=0.985)
    save(fig, "F22_gpu_reproduction_crosscheck.png")
    register("F22", "F22_gpu_reproduction_crosscheck.png",
             "GPU reproducibility crosscheck — historical run vs fresh re-execution",
             "Demonstrate the reported GPU results are independently reproducible",
             ["M22_gpu_reproduction_crosscheck.csv"],
             "final_gpu_validation_metrics.json; step10b_final_gpu_validation_metrics.json",
             "209-claim paired + 10-case targeted correction", "209 / 10",
             "Modified system, two machines", "FRESH vs HISTORICAL", "A (reproducibility only)",
             "Determinism evidence, not accuracy evidence.")


# ==========================================================================
# F23 — component test matrix
# ==========================================================================
def f23():
    rows = C.read_csv(C.OUT_METRICS / "M23_component_test_matrix.csv")
    fig, ax = new_fig(10.8, 6.1)
    y = np.arange(len(rows))
    vals = [int(r["tests"]) for r in rows]
    bars = ax.barh(y, vals, 0.6, color=C.C_MODIFIED, edgecolor="black", linewidth=0.6)
    for b, r in zip(bars, rows):
        ax.text(b.get_width() + 1.5, b.get_y() + b.get_height() / 2,
                f"{r['passed']}/{r['tests']} passed  ·  {r['cpu_gpu']}  ·  "
                f"real model: {r['real_model_used']}", va="center", fontsize=S(7.6, 11))
    ax.set_yticks(y)
    ax.set_yticklabels([r["component"].replace("_", " ") for r in rows], fontsize=S(8, 11.5))
    ax.invert_yaxis()
    ax.set_xlim(0, 175)
    ax.set_xlabel("Tests in this component group (count)")
    ax.set_ylabel("Pipeline component")
    ax.xaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.text(0.985, 0.08, "Authoritative suite total: 205 / 205 passed\n"
                         "(component rows overlap — never sum them)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=S(9, 13),
            fontweight="bold", color=C.C_SHIPPED,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F1F8F1", edgecolor=C.C_SHIPPED))
    titleblock(fig, "Component regression coverage — research/prototype/tests/",
               "Software-behaviour results only: each test asserts a documented pipeline invariant, "
               "not a statistical or legal outcome")
    footer(fig, "evaluation/metrics/COMPONENT_TEST_MATRIX.csv "
                "(via metrics/M23_component_test_matrix.csv)",
           "research/prototype/tests/", "205 authoritative total (289 across overlapping groups)",
           "FRESH — the full suite was re-run for this package: 205 passed",
           "SOFTWARE BEHAVIOUR PASS only. Passing tests say the code does what it was designed to "
           "do; they say nothing about verifier accuracy or legal correctness.")
    adjust(fig, top=0.845, bottom=0.185, left=0.235, right=0.985)
    save(fig, "F23_component_test_coverage.png")
    register("F23", "F23_component_test_coverage.png",
             "Component regression coverage — research/prototype/tests/",
             "Show the behavioural test surface behind each pipeline stage",
             ["M23_component_test_matrix.csv"],
             "evaluation/metrics/COMPONENT_TEST_MATRIX.csv", "research/prototype/tests/", "205",
             "Modified system (current code)", "FRESH", "n/a (software behaviour)",
             "Software behaviour, not accuracy.")


# ==========================================================================
# F24 — evidence pool composition
# ==========================================================================
def f24():
    rows = C.read_csv(C.OUT_METRICS / "M24_evidence_pool_composition.csv")
    base = next(r for r in rows if r["system"] == "baseline")
    mod = next(r for r in rows if r["system"] == "modified")
    fig, ax = new_fig(9.6, 6.1)
    labels = ["Baseline\nuse_evidence_v1 = false", "Modified\nuse_evidence_v1 = true"]
    usable = [int(base["usable_records_loaded"]), int(mod["usable_records_loaded"])]
    onfile = [int(base["records_in_v0_file"]) + int(base["records_in_v1_file"]),
              int(mod["records_in_v0_file"]) + int(mod["records_in_v1_file"])]
    x = np.arange(2); w = 0.34
    b1 = ax.bar(x - w / 2, onfile, w, color="#D7D7D7", edgecolor="black", linewidth=0.6,
                label="Records available in the loaded corpus files")
    b2 = ax.bar(x + w / 2, usable, w, color=[C.C_BASELINE, C.C_MODIFIED], edgecolor="black",
                linewidth=0.6, label="Usable premises (VERIFIED_EXACT / VERIFIED_CONTENT only)")
    bar_labels(ax, b1, "{:.0f}", offset=2)
    bar_labels(ax, b2, "{:.0f}", offset=2)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=S(9, 13))
    ax.set_ylabel("Canonical statute records (count)")
    ax.set_xlabel("Evidence-pool configuration")
    ax.set_ylim(0, 178)
    ax.legend(frameon=True, loc="upper left")
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    ax.annotate(f"+{usable[1] - usable[0]} usable premises",
                xy=(1 + w / 2, usable[1] + 8), ha="center", fontsize=S(9, 13),
                fontweight="bold", color=C.C_MODIFIED)
    titleblock(fig, "Canonical evidence pool available to the verifier in each system",
               "Loaded live through the unmodified production loader "
               "src/data_loader.load_usable_evidence_from_config(); v1 is merged on top of v0, "
               "never replacing it")
    footer(fig, "research/prototype/config/prototype.yaml + research/data/evidence/*.jsonl, "
                "loaded via src/data_loader.py (via metrics/M24_evidence_pool_composition.csv)",
           "research/data/evidence/ (canonical_statutes.jsonl + canonical_statutes_v1.jsonl)",
           "63 + 82 records on file; 59 vs 136 usable",
           "FRESH (computed live for this package)",
           "SOURCE_ONLY / INVALID / UNRESOLVED audit verdicts are excluded by design and are never "
           "used as verifier premises. The corpus is not a substitute for professional legal review.")
    adjust(fig, top=0.835, bottom=0.20, left=0.10, right=0.975)
    save(fig, "F24_evidence_pool_composition.png")
    register("F24", "F24_evidence_pool_composition.png",
             "Canonical evidence pool available to the verifier in each system",
             "Make the single largest structural difference between the systems concrete",
             ["M24_evidence_pool_composition.csv"],
             "config/prototype.yaml; research/data/evidence/*.jsonl via src/data_loader.py",
             "research/data/evidence/", "59 vs 136 usable records", "Baseline vs Modified",
             "FRESH", "A", "Audit-excluded records are never used as premises.")


# ==========================================================================
# F25 — scope gate replay
# ==========================================================================
def f25():
    rows = C.read_csv(C.OUT_METRICS / "M25_scope_gate_replay.csv")
    fig, ax = new_fig(9.6, 6.0)
    labels = ["Baseline\natomic_scope_check = false\n(full-sentence byte-for-byte rule)",
              "Modified\natomic_scope_check = \"assertion_spans\"\n(per-citation verbatim fragments)"]
    blocked = [int(r["n_blocked"]) for r in rows]
    unblocked = [int(r["n_unblocked"]) for r in rows]
    ax.bar(labels, blocked, 0.5, color=C.C_SCOPE, edgecolor="black", linewidth=0.6,
           label="Still rejected at the scope gate")
    ax.bar(labels, unblocked, 0.5, bottom=blocked, color=C.C_SHIPPED, edgecolor="black",
           linewidth=0.6, label="No longer rejected on scope grounds")
    for i, (b, u) in enumerate(zip(blocked, unblocked)):
        ax.text(i, b / 2, f"{b} rejected", ha="center", va="center", fontsize=S(9.5, 14),
                fontweight="bold", color="white")
        if u:
            ax.text(i, b + u / 2, f"{u} unblocked", ha="center", va="center",
                    fontsize=S(9, 13), fontweight="bold", color="white")
    ax.set_ylim(0, 14)
    ax.set_ylabel(T("Real historical scope-violation correction attempts (count of 11)",
                    "Scope-violation attempts (count of 11)"))
    ax.set_xlabel("Scope-violation check mode")
    ax.tick_params(axis="x", labelsize=S(8, 11.5))
    ax.legend(frameon=True, loc="upper right")
    ax.yaxis.grid(True, linestyle=":", alpha=0.45); ax.set_axisbelow(True)
    titleblock(fig, "Scope-gate behaviour replay on 11 real historical scope violations",
               "Deterministic replay of pipeline._scope_violation() against the same already-"
               "generated correction text under both check modes — no model call")
    footer(fig, "evaluation/ablation/scope_check_replay_fresh.json "
                "(via metrics/M25_scope_gate_replay.csv)",
           "11 real historical scope-violation correction attempts (batch1 + batch2)", "11",
           "FRESH REPRODUCTION (CPU); matches the historical committed replay exactly",
           "The replay stops AT the scope gate. It does NOT show that the one unblocked case "
           "would ship — re-verification and the sibling-regression net still apply, and "
           "downstream shipping was not tested by this artifact.")
    adjust(fig, top=0.835, bottom=0.215, left=0.11, right=0.975)
    save(fig, "F25_scope_gate_replay.png")
    register("F25", "F25_scope_gate_replay.png",
             "Scope-gate behaviour replay on 11 real historical scope violations",
             "Show precisely what the relaxed scope check did and did not change",
             ["M25_scope_gate_replay.csv"],
             "evaluation/ablation/scope_check_replay_fresh.json",
             "11 real scope violations", "11", "Baseline vs Modified", "FRESH REPRODUCTION", "C",
             "Stops at the gate; downstream shipping not verified.")


FIGURES = [f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, f12, f13,
           f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, f25]


def main() -> None:
    global PPT
    for mode in (False, True):
        PPT = mode
        apply_rc()
        print(f"\nRendering {'PPT (16:9)' if mode else 'publication'} variants ...")
        for fn in FIGURES:
            fn()
            print(f"  {fn.__name__} ok")
    C.write_csv(C.BUILD_STATE / "figures.csv", list(MANIFEST[0].keys()), MANIFEST)
    print(f"\n{len(MANIFEST)} figures rendered in both variants.")


if __name__ == "__main__":
    main()
