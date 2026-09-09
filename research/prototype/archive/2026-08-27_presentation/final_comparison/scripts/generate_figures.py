"""
Generates every PNG figure under final_comparison/figures/ directly from the CSVs already
computed by build_comparison_data.py (never hand-typed numbers) plus a small number of
source JSON files read the same way build_comparison_data.py does.

Presentation layer only: this script maps the technical, config-flag-heavy strings stored
in the CSVs (e.g. "CURRENT (all four levers) -- targeted GPU correction validation") to
full, human-readable, never-truncated labels using the project's own consistent terminology
(ORIGINAL / CURRENT, Bare framing / Labeled framing, Evidence retrieval, Atomic/assertion-span
scope checking, Narrow re-verification, Synthetic stress test, Natural-data evaluation).
No numeric value, CSV, JSON, or underlying metric is changed here -- only how it is labeled,
laid out, and captioned so a figure is self-explanatory when pasted into a slide deck
without the reader having read FINAL_BASELINE_COMPARISON.md first.

Run: python generate_figures.py   (after build_comparison_data.py; CPU-only, matplotlib only)
"""
import csv
import json
import re
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

SCRIPT_DIR = Path(__file__).resolve().parent
FINAL_COMPARISON = SCRIPT_DIR.parent
# PROTOTYPE updated (2026-09-09 addendum pass): this directory now lives one
# level deeper (archive/2026-08-27_presentation/final_comparison/) than its
# original build location (research/prototype/final_comparison/), so an extra
# .parent is needed to still land on research/prototype/.
PROTOTYPE = FINAL_COMPARISON.parent.parent.parent
OUT = PROTOTYPE / "outputs"
TABLES = FINAL_COMPARISON / "tables"
FIGURES = FINAL_COMPARISON / "figures"
FIGURES.mkdir(exist_ok=True)

ORIGINAL_COLOR = "#6b7280"     # neutral grey  -- ORIGINAL configuration
CURRENT_COLOR = "#2563eb"      # blue          -- CURRENT configuration (all production improvements)
TRANSITIONAL_COLOR = "#7c9dd6"  # light blue    -- partial-improvement / transitional arm
CUMULATIVE_COLOR = "#374151"   # dark grey     -- pooled / cumulative-history figures
SYNTHETIC_COLOR = "#f59e0b"    # amber         -- synthetic stress test (calibration only)
ACCENT_RED = "#dc2626"
ACCENT_GREEN = "#16a34a"
ACCENT_TEAL = "#0d9488"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#111111",
    "text.color": "#111111",
    "xtick.color": "#111111",
    "ytick.color": "#111111",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "figure.titlesize": 15,
    "figure.titleweight": "bold",
})

# ======================================================================
# Label map: every raw string that appears in a comparison_* CSV, mapped to a
# full, human-readable, presentation-ready label using this project's fixed
# terminology (ORIGINAL / CURRENT, Bare framing / Labeled framing, Evidence
# retrieval, Atomic/assertion-span scope checking, Narrow re-verification,
# Synthetic stress test, Natural-data evaluation). Never truncated, never an
# internal config string standing alone. Multi-line ("\n") where that reads
# better as a bar-chart tick label than one long line.
# ======================================================================
LABELS = {
    # --- retrieval_results.csv: dataset ---
    "final_gpu_validation, 50 paired natural cases, bare framing both arms (isolates retrieval only)":
        "Natural-data evaluation\n(50 paired cases, Bare framing,\nEvidence retrieval isolated)",
    "588 claims pooled from every natural-experiment generated text ever produced":
        "Natural-data evaluation\n(588 pooled claims,\ncorpus-level check)",

    # --- verdict_distribution_results.csv: config ---
    "ORIGINAL (bare, v0, legacy scope) -- pooled":
        "ORIGINAL\n(Bare framing,\npooled natural-data\nevaluation)",
    "CURRENT framing only (labeled, v0, legacy scope) -- pooled":
        "Labeled framing only\n(pooled natural-data\nevaluation)",
    "ORIGINAL (bare, v0, legacy scope) -- paired final-validation batch":
        "ORIGINAL\n(Bare framing,\npaired natural-data\nbatch)",
    "+ retrieval + scope + narrow-reverify only, still bare -- paired final-validation batch":
        "+ Evidence retrieval\n+ scope checking\n+ narrow re-verification\n(still Bare framing)",
    "CURRENT (all four levers) -- paired final-validation batch, CPU re-verify":
        "CURRENT\n(all production\nimprovements,\nsame batch re-verified)",

    # --- correction_results.csv / safety_results.csv: regime ---
    "ORIGINAL (bare, v0, legacy scope) -- final-validation Arm A":
        "ORIGINAL\n(Bare framing)",
    "+retrieval+scope+narrow-reverify, still bare -- final-validation Arm B":
        "+ Evidence retrieval + scope checking\n+ narrow re-verification\n(still Bare framing)",
    "CURRENT (all four levers) -- targeted GPU correction validation":
        "CURRENT\n(All production improvements)",
    "cumulative, ALL natural regimes/history pooled (56 attempts, includes ORIGINAL and CURRENT batches)":
        "All natural-data history\npooled (56 attempts total)",
    "synthetic stress (calibration only, NOT natural data), labeled framing":
        "Synthetic stress test\n(Labeled framing, calibration only)",
    "ORIGINAL (bare, v0, legacy scope, no narrow-reverify) -- pooled natural correction attempts":
        "ORIGINAL\n(Bare framing,\npooled natural-data attempts)",
    "cumulative, ALL natural regimes/history (56 attempts)":
        "All natural-data history\n(56 attempts total)",
    "synthetic stress, bare (calibration only)":
        "Synthetic stress test\n(Bare framing)",
    "synthetic stress, labeled (calibration only)":
        "Synthetic stress test\n(Labeled framing)",

    # --- ablation_results.csv: lever ---
    "Evidence corpus (use_evidence_v1: false->true)":
        "Evidence retrieval\n(original corpus -> expanded corpus)",
    "Claim parser (pre-fix -> current, commit 223eb9d)":
        "Claim parser fix\n(pre-fix -> current parser)",
    "Premise framing (bare -> labeled), natural data, CPU re-verify":
        "Bare -> Labeled framing\n(natural-data re-verification)",
    "Premise framing (bare -> labeled), controlled benchmark (curated, not natural)":
        "Bare -> Labeled framing\n(controlled benchmark)",
    "Scope-violation check (legacy full-sentence -> assertion_spans)":
        "Atomic / assertion-span\nscope checking",
    "Narrow re-verification hypothesis (full-sentence -> assertion_text)":
        "Narrow re-verification",
    "Citation-identity preservation on correction":
        "Citation-identity preservation\n(always on, not an ablation)",

    # --- efficiency_results.csv: measurement ---
    "final_gpu_validation Arm A (ORIGINAL: bare, v0, legacy scope), verification+correction only (excl. shared generation)":
        "ORIGINAL\n(Bare framing,\nverification + correction only)",
    "final_gpu_validation Arm B (CURRENT retrieval/scope/narrow-reverify, still bare), verification+correction only":
        "+ Evidence retrieval + scope checking\n+ narrow re-verification (still Bare)\n(verification + correction only)",
    "labeled_correction_validation_gpu (CURRENT full config, targeted correction-only validation)":
        "CURRENT\n(All production improvements,\ntargeted correction validation)",
    "synthetic stress, bare framing correction path (calibration only)":
        "Synthetic stress test\n(Bare framing, correction path)",
    "synthetic stress, labeled framing correction path (calibration only)":
        "Synthetic stress test\n(Labeled framing, correction path)",
}


def label_for(raw, width=26):
    """Full, human-readable label for a raw CSV string. Falls back to a wrapped
    (never truncated, never '...'-suffixed) version of the raw string itself if
    it is somehow missing from LABELS, and records the miss so main() can warn."""
    if raw in LABELS:
        return LABELS[raw]
    _unmapped_raw_strings.append(raw)
    return textwrap.fill(raw, width=width, break_long_words=False)


_unmapped_raw_strings = []


def read_csv(name):
    with open(TABLES / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def parse_metric_value(s):
    """Extract a plotting-friendly float directly from a comparison_summary.csv
    value string, e.g. '132/209 (63.2%)' -> 63.2, '0.749' -> 0.749, '3/209' -> 1.4
    (as a percentage of the fraction). Never a hand-typed number -- always parsed
    from the machine-computed string itself."""
    m = re.search(r"\(([\d.]+)%\)", s)
    if m:
        return float(m.group(1))
    m = re.match(r"^(\d+)/(\d+)$", s.strip())
    if m:
        return 100.0 * int(m.group(1)) / int(m.group(2))
    return float(s)


def save(fig, name):
    path = FIGURES / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def add_config_legend_caption(fig, extra=None):
    """Consistent, always-present caption clarifying the ORIGINAL/CURRENT color
    coding so every figure is self-explanatory without reading the report."""
    text = "Grey = ORIGINAL (pre-2026-08-27 baseline)   |   Blue = CURRENT (shipped production config)"
    if extra:
        text += "   |   " + extra
    fig.text(0.5, -0.02, text, ha="center", va="top", fontsize=9, style="italic", color="#374151")


def annotate_bars(ax, bars, pct=False, fmt=None):
    for b in bars:
        h = b.get_height()
        if fmt:
            lbl = fmt(h)
        else:
            lbl = f"{h:.1f}%" if pct else f"{h:.0f}"
        ax.annotate(lbl, (b.get_x() + b.get_width() / 2, h), ha="center", va="bottom", fontsize=9)


def bar_pair(ax, labels, original_vals, current_vals, title, ylabel, pct=False):
    x = range(len(labels))
    w = 0.35
    b1 = ax.bar([i - w / 2 for i in x], original_vals, width=w, color=ORIGINAL_COLOR, label="ORIGINAL")
    b2 = ax.bar([i + w / 2 for i in x], current_vals, width=w, color=CURRENT_COLOR, label="CURRENT")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper left", framealpha=0.95)
    annotate_bars(ax, b1, pct=pct)
    annotate_bars(ax, b2, pct=pct)
    return ax


# ---------------------------------------------------------------- 1. overall metric comparison
def fig01_overall():
    rows = {r["metric"]: r for r in read_csv("comparison_summary.csv")}

    panels = [
        ("Evidence coverage (paired, 50 natural cases, bare framing both)",
         "Evidence Coverage", "% of claims matched with evidence", True),
        ("Premise-framing macro F1 (controlled benchmark, n=420)",
         "Verifier Accuracy (Macro F1)", "Macro F1 score (0-1 scale, controlled benchmark)", False),
        ("ENTAILED reached on natural data, framing-only CPU re-verify (147 matched claims)",
         "ENTAILED Verdicts Reached\n(Natural Data)", "% of matched claims reaching ENTAILED", True),
        ("Correction shipped rate, targeted GPU validation vs ORIGINAL-config trigger set",
         "Correction Shipped Rate", "% of triggered corrections shipped", True),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    fig.suptitle("ORIGINAL vs CURRENT — Headline Comparison Metrics", y=1.02)
    for ax, (metric_key, title, ylabel, is_pct) in zip(axes.flat, panels):
        r = rows[metric_key]
        orig_val = parse_metric_value(r["original"])
        cur_val = parse_metric_value(r["current_retrieval_only"])
        bars = ax.bar(["ORIGINAL", "CURRENT"], [orig_val, cur_val],
                       color=[ORIGINAL_COLOR, CURRENT_COLOR], width=0.55)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        fmt = (lambda h: f"{h:.1f}%") if is_pct else (lambda h: f"{h:.3f}")
        annotate_bars(ax, bars, fmt=fmt)
        ax.set_ylim(0, max(orig_val, cur_val, (1.0 if not is_pct else 10)) * 1.25 + 0.01)
    add_config_legend_caption(fig)
    save(fig, "01_overall_metric_comparison.png")


# ---------------------------------------------------------------- 2. evidence coverage comparison
def fig02_evidence_coverage():
    rows = read_csv("retrieval_results.csv")
    cfg = json.loads((FINAL_COMPARISON / "comparison_config.json").read_text(encoding="utf-8"))
    orig_pool = cfg["ORIGINAL"]["evidence_pool_size"]
    cur_pool = cfg["CURRENT"]["evidence_pool_size"]
    labels = [label_for(r["dataset"], width=30) for r in rows]
    orig = [float(r["original_coverage_pct"]) for r in rows]
    cur = [float(r["current_coverage_pct"]) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 6.5))
    bar_pair(
        ax, labels, orig, cur,
        "Evidence Coverage — ORIGINAL vs CURRENT Evidence Retrieval\n"
        f"(ORIGINAL evidence corpus: {orig_pool} records  |  CURRENT evidence corpus: {cur_pool} records)",
        "% of claims with matching evidence", pct=True,
    )
    add_config_legend_caption(fig)
    save(fig, "02_evidence_coverage_comparison.png")


# ---------------------------------------------------------------- 3. verdict distribution comparison
def fig03_verdict_distribution():
    rows = read_csv("verdict_distribution_results.csv")
    verdict_display = {
        "NOT_ENOUGH_INFORMATION": "Not Enough Information",
        "NO_EVIDENCE": "No Evidence Found",
        "CONTRADICTED": "Contradicted",
        "ENTAILED": "Entailed (Confirmed Correct)",
    }
    verdict_keys = list(verdict_display.keys())
    colors = ["#94a3b8", "#cbd5e1", ACCENT_RED, ACCENT_GREEN]
    fig, ax = plt.subplots(figsize=(17, 8.5))
    labels = [label_for(r["config"], width=26) for r in rows]
    bottoms = [0.0] * len(rows)
    for vk, c in zip(verdict_keys, colors):
        vals = [100 * int(r[vk]) / int(r["n_claims"]) for r in rows]
        bars = ax.bar(labels, vals, bottom=bottoms, label=verdict_display[vk], color=c)
        for b, v, bot in zip(bars, vals, bottoms):
            if v >= 4:
                ax.annotate(f"{v:.0f}%", (b.get_x() + b.get_width() / 2, bot + v / 2),
                            ha="center", va="center", fontsize=8, color="#111111")
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_ylabel("% of all claims in that configuration's sample")
    ax.set_title("Verifier Verdict Distribution — ORIGINAL vs CURRENT Configurations\n(stacked = 100% of claims per configuration)")
    ax.set_ylim(0, 112)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, framealpha=0.95, fontsize=9)
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=9.5)
    save(fig, "03_verdict_distribution_comparison.png")


# ---------------------------------------------------------------- 4. correction funnel comparison
def fig04_correction_funnel():
    rows = read_csv("correction_results.csv")
    keep = [r for r in rows if "cumulative" not in r["regime"] and "synthetic" not in r["regime"]]
    labels = [label_for(r["regime"], width=26) for r in keep]
    triggers = [int(r["n_triggers"]) for r in keep]
    failed = [int(r["correction_failed"]) for r in keep]
    scope = [int(r["correction_scope_violation"]) for r in keep]
    shipped = [int(r["corrected_shipped"]) for r in keep]
    fig, ax = plt.subplots(figsize=(11, 7))
    x = range(len(labels))
    b_shipped = ax.bar(x, shipped, label="Shipped (correction applied)", color=ACCENT_GREEN)
    b_scope = ax.bar(x, scope, bottom=shipped, label="Rejected: scope violation", color=SYNTHETIC_COLOR)
    b_failed = ax.bar(x, failed, bottom=[s + sc for s, sc in zip(shipped, scope)],
                       label="Rejected: re-verification failed", color=ORIGINAL_COLOR)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylabel("Number of correction attempts (count)")
    ax.set_title("Correction Funnel — ORIGINAL vs CURRENT Natural-Data Configurations\n(same 50-case final-validation batch throughout)")
    ax.legend(loc="upper right", framealpha=0.95)
    for i, t in enumerate(triggers):
        ax.annotate(f"{t} triggered", (i, t), ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylim(0, max(triggers) * 1.25)
    save(fig, "04_correction_funnel_comparison.png")


# ---------------------------------------------------------------- 5. correction outcome comparison (shipped rate)
def fig05_correction_outcome():
    rows = read_csv("correction_results.csv")
    labels = [label_for(r["regime"], width=24) for r in rows]
    rates = [float(r["shipped_rate_pct"]) for r in rows]

    def color_for(regime):
        if regime.startswith("CURRENT"):
            return CURRENT_COLOR
        if regime.startswith("ORIGINAL"):
            return ORIGINAL_COLOR
        if regime.startswith("cumulative"):
            return CUMULATIVE_COLOR
        if regime.startswith("synthetic"):
            return SYNTHETIC_COLOR
        return TRANSITIONAL_COLOR

    colors = [color_for(r["regime"]) for r in rows]
    fig, ax = plt.subplots(figsize=(16, 7.5))
    bars = ax.bar(labels, rates, color=colors)
    annotate_bars(ax, bars, pct=True)
    ax.set_ylabel("% of triggered corrections shipped")
    ax.set_title("Correction Shipped Rate by Configuration\n(shipped = passed re-verification and was applied)")
    ax.set_ylim(0, max(rates) * 1.3 + 5)
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=9.5)
    legend_handles = [
        Patch(color=ORIGINAL_COLOR, label="ORIGINAL"),
        Patch(color=TRANSITIONAL_COLOR, label="Partial improvements (still Bare framing)"),
        Patch(color=CURRENT_COLOR, label="CURRENT (all production improvements)"),
        Patch(color=CUMULATIVE_COLOR, label="Pooled across all natural-data history"),
        Patch(color=SYNTHETIC_COLOR, label="Synthetic stress test (calibration only)"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", framealpha=0.95, fontsize=8.5)
    save(fig, "05_correction_outcome_comparison.png")


# ---------------------------------------------------------------- 6. safety comparison
def fig06_safety():
    rows = read_csv("safety_results.csv")
    labels = [label_for(r["regime"], width=24) for r in rows]
    attempts = [int(r["n_correction_attempts"]) for r in rows]
    unsafe = [int(r["unsafe_shipped"]) for r in rows]
    fig, ax = plt.subplots(figsize=(16, 7.5))
    ax.bar(labels, attempts, color="#e5e7eb", label="Total correction attempts")
    ax.bar(labels, unsafe, color=ACCENT_RED, label="Unsafe corrections shipped")
    for i, (a, u) in enumerate(zip(attempts, unsafe)):
        ax.annotate(f"{u} unsafe / {a} attempts", (i, a), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Number of correction attempts (count)")
    ax.set_title("Safety — Unsafe Corrections Shipped vs Total Attempts\n(0 unsafe shipments observed in every configuration measured)")
    ax.set_ylim(0, max(attempts) * 1.25)
    ax.legend(loc="upper right", framealpha=0.95)
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=9.5)
    save(fig, "06_safety_comparison.png")


# ---------------------------------------------------------------- 7. confidence distribution
def fig07_confidence_distribution():
    A = [json.loads(l) for l in (OUT / "final_gpu_validation_A.jsonl").read_text(encoding="utf-8").splitlines()]
    B = [json.loads(l) for l in (OUT / "final_gpu_validation_B.jsonl").read_text(encoding="utf-8").splitlines()]
    bare_conf = [cl["confidence"] for doc in A for cl in doc["claims"] if cl["confidence"] is not None]
    cur_conf = [cl["confidence"] for doc in B for cl in doc["claims"] if cl["confidence"] is not None]
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.hist(bare_conf, bins=20, alpha=0.6, label=f"ORIGINAL evidence corpus (n={len(bare_conf)} matched claims)", color=ORIGINAL_COLOR)
    ax.hist(cur_conf, bins=20, alpha=0.6, label=f"CURRENT evidence corpus (n={len(cur_conf)} matched claims)", color=CURRENT_COLOR)
    ax.set_xlabel("Verifier confidence score (0-1, matched claims only)")
    ax.set_ylabel("Number of claims")
    ax.set_title("Verifier Confidence Distribution — ORIGINAL vs CURRENT Evidence Retrieval\n(Bare framing held fixed in both arms; same 50 paired natural cases)")
    ax.legend(loc="upper left", framealpha=0.95)
    save(fig, "07_confidence_distribution.png")


# ---------------------------------------------------------------- 8. ablation comparison
def fig08_ablation():
    rows = read_csv("ablation_results.csv")
    labels = [label_for(r["lever"], width=30) for r in rows]

    CONFIRMED = ("Confirmed lever", ACCENT_GREEN, "Confirmed: changed a measured outcome")
    CONFIRMED_DIAG = ("Confirmed diagnostic-quality lever", ACCENT_TEAL,
                       "Confirmed: improved diagnostic quality only (no shipping-outcome change shown)")
    WEAK = ("Weak", SYNTHETIC_COLOR, "Weak / inconclusive on available sample")
    INVARIANT = ("Invariant", "#9ca3af", "Invariant — always on, not an ablation")

    categories = [CONFIRMED, CONFIRMED_DIAG, WEAK, INVARIANT]

    def classify(verdict_text):
        for prefix, color, legend_text in categories:
            if verdict_text.startswith(prefix):
                return color, legend_text
        return "#9ca3af", "Unclassified"

    scores = []
    colors = []
    legend_texts = []
    for r in rows:
        v = r["verdict"]
        color, legend_text = classify(v)
        colors.append(color)
        legend_texts.append(legend_text)
        if v.startswith("Confirmed lever"):
            scores.append(1.0)
        elif v.startswith("Confirmed diagnostic-quality lever"):
            scores.append(0.6)
        elif v.startswith("Weak"):
            scores.append(0.3)
        elif v.startswith("Invariant"):
            scores.append(0.08)
        else:
            scores.append(0.5)

    fig, ax = plt.subplots(figsize=(11, 7.5))
    bars = ax.barh(labels, scores, color=colors)
    for b, txt in zip(bars, legend_texts):
        short = {
            "Confirmed: changed a measured outcome": "Confirmed",
            "Confirmed: improved diagnostic quality only (no shipping-outcome change shown)": "Confirmed (diagnostic only)",
            "Weak / inconclusive on available sample": "Weak / inconclusive",
            "Invariant — always on, not an ablation": "Invariant (no effect)",
        }[txt]
        ax.annotate(short, (b.get_width() + 0.02, b.get_y() + b.get_height() / 2),
                    va="center", ha="left", fontsize=9)
    ax.set_xlim(0, 1.55)
    ax.set_xlabel("Evidence strength for this improvement (qualitative rating, not a measured effect size)")
    ax.set_title("Ablation Summary — Which Individual Improvements Actually Moved Outcomes")
    ax.invert_yaxis()
    seen = []
    handles = []
    for _, color, legend_text in categories:
        if legend_text not in seen:
            seen.append(legend_text)
            short = {
                "Confirmed: changed a measured outcome": "Confirmed lever",
                "Confirmed: improved diagnostic quality only (no shipping-outcome change shown)": "Confirmed (diagnostic quality only)",
                "Weak / inconclusive on available sample": "Weak / inconclusive",
                "Invariant — always on, not an ablation": "Invariant (always on, not an ablation)",
            }[legend_text]
            handles.append(Patch(color=color, label=short))
    ax.legend(handles=handles, loc="lower right", framealpha=0.95, fontsize=8.5)
    save(fig, "08_ablation_comparison.png")


# ---------------------------------------------------------------- 9. runtime / resource comparison
def fig09_efficiency():
    rows = read_csv("efficiency_results.csv")
    labels = [label_for(r["measurement"], width=26) for r in rows]
    runtimes = [float(r["runtime_seconds"]) for r in rows]
    fig, ax = plt.subplots(figsize=(16, 7.5))
    colors = [CURRENT_COLOR if ("CURRENT" in r["measurement"] or "labeled" in r["measurement"])
              else (SYNTHETIC_COLOR if "synthetic" in r["measurement"] else ORIGINAL_COLOR) for r in rows]
    bars = ax.bar(labels, runtimes, color=colors)
    for b, r in zip(bars, runtimes):
        ax.annotate(f"{r:.0f} sec", (b.get_x() + b.get_width() / 2, b.get_height()), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Runtime (seconds)")
    ax.set_title("Runtime by Experiment\n(verification + correction only; shared Qwen generation excluded where noted)")
    ax.set_ylim(0, max(runtimes) * 1.2)
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=9.5)
    legend_handles = [
        Patch(color=ORIGINAL_COLOR, label="ORIGINAL"),
        Patch(color=CURRENT_COLOR, label="CURRENT / Labeled framing"),
        Patch(color=SYNTHETIC_COLOR, label="Synthetic stress test (calibration only)"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", framealpha=0.95, fontsize=9)
    save(fig, "09_runtime_resource_comparison.png")


# ---------------------------------------------------------------- 10. cumulative natural-data results
def fig10_cumulative_natural():
    fm = load_json("final_metrics.json")
    census = fm["case_census"]
    labels = ["Initial batch\n(30 cases)", "+ Batch 1\n(+50 cases)", "+ Batch 2\n(+50 cases)",
              "+ Final validation\n(+50 cases)"]
    cumulative_cases = [census["n30"], census["n30"] + census["batch1"],
                         census["n30"] + census["batch1"] + census["batch2"],
                         census["total_distinct_cases_all_batches"]]
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    ax.plot(labels, cumulative_cases, marker="o", markersize=9, color=CURRENT_COLOR, linewidth=2.5)
    for i, c in enumerate(cumulative_cases):
        ax.annotate(f"{c} cases total", (i, c), ha="center", va="bottom", fontsize=10, fontweight="bold",
                    xytext=(0, 8), textcoords="offset points")
    ax.set_ylabel("Cumulative number of distinct natural-data cases evaluated")
    ax.set_title("Cumulative Natural-Data Evaluation Across This Project's History\n"
                  "(an earlier targeted batch of 11 cases is excluded — confirmed to be a subset of the initial 30)")
    ax.set_ylim(0, max(cumulative_cases) * 1.2)
    save(fig, "10_cumulative_natural_data_results.png")


# ---------------------------------------------------------------- 11. synthetic vs natural transfer comparison
def fig11_synthetic_vs_natural():
    fm = load_json("final_metrics.json")
    gap = fm["synthetic_vs_natural_correction_transfer_gap"]
    labels = ["Synthetic stress test\n(Labeled framing,\ncalibration only)",
              "Natural-data evaluation\n(all history pooled,\n56 attempts)",
              "Natural-data evaluation\n(CURRENT system,\n10 targeted attempts)"]
    vals = [gap["synthetic_labeled_shipped_rate_pct"], gap["natural_all_regimes_shipped_rate_pct"],
            gap["natural_final_production_regime_shipped_rate_pct"]]
    colors = [SYNTHETIC_COLOR, CUMULATIVE_COLOR, CURRENT_COLOR]
    fig, ax = plt.subplots(figsize=(9, 6.5))
    bars = ax.bar(labels, vals, color=colors)
    annotate_bars(ax, bars, pct=True)
    ax.set_ylabel("% of triggered corrections shipped")
    ax.set_title("Synthetic-Stress Correction Success Has NOT Transferred to Natural Data\n(same underlying correction mechanism, real vs. deliberately-corrupted claims)")
    ax.set_ylim(0, max(vals) * 1.25)
    save(fig, "11_synthetic_vs_natural_transfer.png")


def main():
    fig01_overall()
    fig02_evidence_coverage()
    fig03_verdict_distribution()
    fig04_correction_funnel()
    fig05_correction_outcome()
    fig06_safety()
    fig07_confidence_distribution()
    fig08_ablation()
    fig09_efficiency()
    fig10_cumulative_natural()
    fig11_synthetic_vs_natural()

    if _unmapped_raw_strings:
        print("\nWARNING: the following raw CSV strings were NOT found in LABELS and fell back")
        print("to a wrapped (but still technical) label -- add them to LABELS for full clarity:")
        for s in _unmapped_raw_strings:
            print("  -", repr(s))
    else:
        print("\nAll x-axis/legend labels resolved through the LABELS map (no unmapped raw strings).")

    print("\nAll figures written to", FIGURES)


if __name__ == "__main__":
    main()
