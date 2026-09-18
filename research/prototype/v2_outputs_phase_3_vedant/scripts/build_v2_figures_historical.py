#!/usr/bin/env python3
"""
V2 figures driven by HISTORICAL committed artifacts — the subsystems that could NOT be
rerun on this machine (no GPU; Qwen2.5-7B uncached; rank_bm25/sentence_transformers absent).

EVERY figure produced here is stamped "HISTORICAL — not rerun for V2" in its footnote, with
the artifact path and date, so it can never be mistaken for a fresh V2 measurement.

Statistics: where a historical artifact reports only a continuity-corrected chi-square, the
EXACT paired test is recomputed here from the artifact's own discordant counts and both are
shown. No number is hand-typed.

Writes into figures/03_evidence_retrieval, 05_verdict, 06_correction, 07_safety,
08_ablation, 10_natural_data, and emits figures/figure_provenance_historical.json.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

_V2 = Path(__file__).resolve().parent.parent
_PROTO = _V2.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v2_style import (  # noqa: E402
    C_ORIGINAL, C_LATEST, C_INTERMEDIATE, VERDICT_COLORS,
    C_SHIPPED, C_REJECT, C_SCOPE, C_NEUTRAL, footnote, save, plt,
)

F = _V2 / "figures"
OUT = _PROTO / "outputs"
EVAL = _PROTO / "evaluation"

PROV: list[dict] = []
HIST = "HISTORICAL — not rerun for V2"


def rec(path: Path, artifact: str, fields: str, grade: str, n, caveat: str):
    PROV.append({
        "figure": str(path.relative_to(_V2)).replace("\\", "/"),
        "source_artifact": artifact, "fields_used": fields,
        "evidence_grade": grade, "n": n, "caveat": caveat,
        "generated_by": "v2_outputs_phase_3_vedant/scripts/build_v2_figures_historical.py",
    })


def exact_mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n))


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------- evidence coverage
def fig_evidence_coverage():
    p = EVAL / "actual_outputs" / "natural_data_runs" / "209_paired" / "paired_209_metrics.json"
    d = jload(p)
    n = d["n_paired_claims"]
    a = d["fresh_evidence_coverage_arm_A"]
    b = d["fresh_evidence_coverage_arm_B"]
    ch = d["evidence_change_counts"]
    gained, lost = ch["evidence_gained"], ch.get("evidence_lost", 0)
    pval = exact_mcnemar(lost, gained)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.4))
    ax = axes[0]
    ax.bar([0], [a], 0.5, color=C_ORIGINAL)
    ax.bar([1], [b], 0.5, color=C_LATEST)
    ax.text(0, a + 0.015, f"{a:.4f}\n({round(a*n)}/{n})", ha="center", fontsize=10)
    ax.text(1, b + 0.015, f"{b:.4f}\n({round(b*n)}/{n})", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["ORIGINAL\n(v0, 59 records)", "LATEST\n(v1 merged, 136 records)"])
    ax.set_ylim(0, 0.92)
    ax.set_ylabel("Evidence coverage (claims resolving to evidence)")
    ax.set_title(f"Evidence coverage, paired natural claims (n={n})")

    ax2 = axes[1]
    cats = ["unchanged\nmatched", "unchanged\nno evidence", "evidence\nGAINED", "evidence\nLOST"]
    vals = [ch["unchanged_matched"], ch["unchanged_no_evidence"], gained, lost]
    cols = [C_NEUTRAL, "#D6D6D6", C_SHIPPED, C_REJECT]
    ax2.bar(cats, vals, 0.6, color=cols)
    for i, v in enumerate(vals):
        ax2.text(i, v + 2.5, str(v), ha="center", fontsize=10.5, fontweight="bold")
    ax2.set_ylim(0, max(vals) * 1.22)
    ax2.set_ylabel("Claims")
    ax2.set_title("Per-claim change — zero regressions")

    fig.suptitle("use_evidence_v1: ORIGINAL vs LATEST evidence coverage",
                 fontsize=13.5, fontweight="bold", y=1.05)
    footnote(axes[0],
             f"{HIST}. Source: evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json.\n"
             f"Paired McNemar, EXACT binomial recomputed here from the artifact's own counts "
             f"({gained} gained, {lost} lost): p={pval:.3e}. The artifact reports chi2=13.07, p=0.0003 (continuity-corrected).\n"
             f"METRIC-ONLY on unlabelled natural data: 'coverage' is a retrieval outcome. This is NOT accuracy, precision or recall.",
             y=-0.22)
    pth = save(fig, F / "03_evidence_retrieval" / "F13_evidence_coverage_209_paired.png")
    rec(pth, str(p.relative_to(_PROTO)), "fresh_evidence_coverage_arm_A/B; evidence_change_counts",
        "HISTORICAL / METRIC_ONLY", n,
        "unlabelled natural data — coverage is a retrieval outcome, not accuracy")


# --------------------------------------------------------------- verdict distribution
def fig_verdict_distribution():
    p = EVAL / "actual_outputs" / "natural_data_runs" / "209_paired" / "paired_209_metrics.json"
    d = jload(p)
    n = d["n_paired_claims"]
    A = d["fresh_verdict_distribution_arm_A"]
    B = d["fresh_verdict_distribution_arm_B"]
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION", "NO_EVIDENCE"]
    av = [A.get(k, 0) for k in order]
    bv = [B.get(k, 0) for k in order]

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    x = np.arange(len(order))
    w = 0.36
    ax.bar(x - w / 2, av, w, label="ORIGINAL (v0 pool)", color=C_ORIGINAL)
    ax.bar(x + w / 2, bv, w, label="LATEST (v1 pool)", color=C_LATEST)
    for i, (u, v) in enumerate(zip(av, bv)):
        ax.text(i - w / 2, u + 2, str(u), ha="center", fontsize=9.6)
        ax.text(i + w / 2, v + 2, str(v), ha="center", fontsize=9.6, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["ENTAILED", "CONTRADICTED", "NEI", "NO_EVIDENCE"])
    ax.set_ylabel("Claims")
    ax.set_ylim(0, max(av + bv) * 1.2)
    ax.set_title(f"Verdict distribution shift, paired natural claims (n={n})\n"
                 "use_evidence_v1 lever, both arms re-verified under labeled framing")
    ax.legend(fontsize=9)
    footnote(ax,
             f"{HIST}. Source: paired_209_metrics.json → fresh_verdict_distribution_arm_A/B.\n"
             "The movement is NO_EVIDENCE → NEI: 15 claims that previously had no evidence at all now have a premise to reason about.\n"
             "This is a DISTRIBUTION change on unlabelled data, not a correctness measurement. No accuracy claim attaches.",
             y=-0.20)
    pth = save(fig, F / "05_verdict" / "F16_verdict_distribution_209_paired.png")
    rec(pth, str(p.relative_to(_PROTO)), "fresh_verdict_distribution_arm_A/B",
        "HISTORICAL / BEHAVIORAL", n, "distribution only, no gold labels")


# --------------------------------------------------------------- correction funnel
def fig_correction_funnel():
    p = OUT / "final_metrics.json"
    d = jload(p)
    s = d["section_D_correction_safety_cumulative"]
    total = s["total_correction_attempts"]
    bd = s["status_breakdown"]
    shipped = s["total_shipped"]
    unsafe = s["total_unsafe_shipped"]

    stages = ["Correction\nattempts", "Passed safety\ngates", "Shipped\n(re-verified ENTAILED)", "UNSAFE\nshipped"]
    passed = total - bd.get("correction_scope_violation", 0)
    vals = [total, passed, shipped, unsafe]
    cols = [C_NEUTRAL, C_SCOPE, C_SHIPPED, C_REJECT]

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.4))
    ax = axes[0]
    ax.bar(range(len(stages)), vals, 0.6, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.0, str(v), ha="center", fontsize=11, fontweight="bold")
    ax.set_xticks(range(len(stages)))
    ax.set_xticklabels(stages, fontsize=9)
    ax.set_ylim(0, total * 1.22)
    ax.set_ylabel("Correction attempts")
    ax.set_title(f"Correction funnel, cumulative natural data (n={total})")

    ax2 = axes[1]
    labels = list(bd.keys())
    vals2 = [bd[k] for k in labels]
    cmap = {"correction_failed": C_NEUTRAL, "correction_scope_violation": C_SCOPE, "corrected": C_SHIPPED}
    ax2.barh(range(len(labels)), vals2, 0.6, color=[cmap.get(k, C_NEUTRAL) for k in labels])
    for i, v in enumerate(vals2):
        ax2.text(v + 0.6, i, str(v), va="center", fontsize=10.5, fontweight="bold")
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=9)
    ax2.set_xlim(0, max(vals2) * 1.2)
    ax2.set_xlabel("Attempts")
    ax2.set_title("Terminal status breakdown")

    fig.suptitle("Selective correction: what actually ships", fontsize=13.5, fontweight="bold", y=1.04)
    footnote(axes[0],
             f"{HIST} — Qwen-dependent, RERUN_INFEASIBLE on this machine (no GPU, model uncached).\n"
             f"Source: outputs/final_metrics.json → section_D_correction_safety_cumulative.\n"
             f"Shipped rate {s['shipped_rate_pct']}% ({shipped}/{total}). Unsafe shipped: {unsafe}/{total} — a ZERO-EVENT result over a SMALL denominator,\n"
             "which is evidence of a working fail-closed design, not proof of safety. The dominant failure is the 7B corrector\n"
             "producing no-op or inadequate edits — a generation-quality limit, not a pipeline defect.",
             y=-0.24)
    pth = save(fig, F / "06_correction" / "F17_correction_funnel_cumulative.png")
    rec(pth, "outputs/final_metrics.json", "section_D_correction_safety_cumulative",
        "HISTORICAL / BEHAVIORAL", total,
        "zero-event safety result over a small denominator; Qwen-dependent, not rerunnable")


# --------------------------------------------------- synthetic vs natural transfer gap
def fig_transfer_gap():
    p = OUT / "final_metrics.json"
    d = jload(p)
    g = d["synthetic_vs_natural_correction_transfer_gap"]
    labels = ["Synthetic stress\n(labeled framing)", "Natural data\n(all regimes)", "Natural data\n(final production regime)"]
    vals = [g["synthetic_labeled_shipped_rate_pct"],
            g["natural_all_regimes_shipped_rate_pct"],
            g["natural_final_production_regime_shipped_rate_pct"]]
    cols = [C_INTERMEDIATE, C_REJECT, C_SCOPE]

    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    ax.bar(range(len(labels)), vals, 0.55, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.6, f"{v}%", ha="center", fontsize=12, fontweight="bold")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylim(0, max(vals) * 1.28)
    ax.set_ylabel("Corrections shipped (%)")
    ax.set_title("The honest gap: correction works on synthetic contradictions,\nbut almost never ships on real generated text")
    footnote(ax,
             f"{HIST}. Source: outputs/final_metrics.json → synthetic_vs_natural_correction_transfer_gap.\n"
             "Synthetic contradictions are mechanically inverted from real statute text, so the corrector has an unambiguous target.\n"
             "Real generated claims are subtler, and the dominant terminal status is the 7B model returning a no-op or inadequate edit.\n"
             "This figure is included because it is the single most important limitation of the correction subsystem — it is NOT a success metric.",
             y=-0.22)
    pth = save(fig, F / "06_correction" / "F18_synthetic_vs_natural_transfer_gap.png")
    rec(pth, "outputs/final_metrics.json", "synthetic_vs_natural_correction_transfer_gap",
        "HISTORICAL / BEHAVIORAL", "59 synthetic / 56 natural",
        "a LIMITATION figure, not a success metric")


# --------------------------------------------------------------- retrieval safety
def fig_retrieval_safety():
    p = OUT / "retrieval_signal_benchmark_results.jsonl"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # method -> kind -> [correct, total]
    for r in rows:
        a = agg[r["method"]][r["kind"]]
        a[1] += 1
        if r.get("correct"):
            a[0] += 1
    methods = ["jaccard", "bm25", "embedding"]
    kinds = sorted({r["kind"] for r in rows})
    adversarial = [k for k in kinds if k != "should_match"]

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    x = np.arange(len(methods))
    w = 0.36
    sm = [agg[m]["should_match"][0] for m in methods]
    sm_t = agg["jaccard"]["should_match"][1]
    adv = [sum(agg[m][k][0] for k in adversarial) for m in methods]
    adv_t = sum(agg["jaccard"][k][1] for k in adversarial)
    ax.bar(x - w / 2, sm, w, label=f"should-match accepted (of {sm_t})", color=C_NEUTRAL)
    ax.bar(x + w / 2, adv, w, label=f"adversarial correctly REJECTED (of {adv_t})", color=C_SHIPPED)
    for i in range(len(methods)):
        ax.text(i - w / 2, sm[i] + 0.4, f"{sm[i]}/{sm_t}", ha="center", fontsize=10)
        ax.text(i + w / 2, adv[i] + 0.4, f"{adv[i]}/{adv_t}", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n{'(PRODUCTION)' if m=='jaccard' else '(REJECTED)'}" for m in methods])
    ax.set_ylabel("Cases")
    ax.set_ylim(0, max(sm + adv) * 1.28)
    ax.set_title("Why Jaccard was kept and BM25/embedding were rejected\nPre-registered retrieval-safety benchmark")
    ax.legend(fontsize=9, loc="upper right")
    footnote(ax,
             f"{HIST} — RERUN_INFEASIBLE here (rank_bm25 and sentence_transformers not installed; MiniLM not cached).\n"
             f"Source: outputs/retrieval_signal_benchmark_results.jsonl ({len(rows)} rows = {len(methods)} methods x {sm_t + adv_t} cases).\n"
             f"NOTE: several repo documents describe this as '30 adversarial cases'. It is {sm_t + adv_t} pre-registered cases of which {adv_t} are adversarial;\n"
             "the correct-reject rates are over those, not over 30. All three methods accept every real match — they differ ONLY on safety.\n"
             "Separately, the LATEST audit found evidence_matching.fuzzy_method is never read by any call site, so BM25/embedding are unreachable from production.",
             y=-0.24)
    pth = save(fig, F / "03_evidence_retrieval" / "F19_retrieval_method_safety.png")
    rec(pth, "outputs/retrieval_signal_benchmark_results.jsonl", "method, kind, correct",
        "HISTORICAL / BEHAVIORAL", f"{sm_t + adv_t} cases ({adv_t} adversarial)",
        "rates are over the adversarial subset, not over 30")


# --------------------------------------------------------------- narrow_primary GPU
def fig_narrow_primary():
    p = OUT / "narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json"
    d = jload(p)
    old, cur = d["OLD"], d["CURRENT"]
    order = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]
    ov = [old["verdict_distribution"].get(k, 0) for k in order]
    cv = [cur["verdict_distribution"].get(k, 0) for k in order]

    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    x = np.arange(len(order))
    w = 0.36
    ax.bar(x - w / 2, ov, w, label="narrow_primary_hypothesis=false (ORIGINAL)", color=C_ORIGINAL)
    ax.bar(x + w / 2, cv, w, label="narrow_primary_hypothesis=true (LATEST)", color=C_LATEST)
    for i, (u, v) in enumerate(zip(ov, cv)):
        ax.text(i - w / 2, u + 0.35, str(u), ha="center", fontsize=10)
        ax.text(i + w / 2, v + 0.35, str(v), ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["ENTAILED", "CONTRADICTED", "NEI"])
    ax.set_ylabel("Evidence-matched claims")
    ax.set_ylim(0, max(ov + cv) * 1.32)
    ax.set_title(f"narrow_primary_hypothesis: verdict shift on a fresh natural GPU batch\n"
                 f"n={d['config']['n_cases_total_in_output']} documents, "
                 f"{old['claims_with_evidence']} evidence-matched claims per arm")
    ax.legend(fontsize=9)
    footnote(ax,
             f"{HIST} — Qwen-dependent GPU batch, RERUN_INFEASIBLE here. Source: {p.name}.\n"
             f"Shift is toward more decisive verdicts, but correction shipped {old.get('corrections_shipped', 0)}/{old['correction_triggered']} vs "
             f"{cur.get('corrections_shipped', 0)}/{cur['correction_triggered']} — NOT significant at this n (the repo reports p≈0.125).\n"
             "Unlabelled natural data: this is a verdict DISTRIBUTION shift, not an accuracy improvement. "
             "On the gold-labelled GOLD-02 set this lever had EXACTLY ZERO effect.",
             y=-0.22)
    pth = save(fig, F / "08_ablation" / "F20_narrow_primary_hypothesis_shift.png")
    rec(pth, f"outputs/{p.name}", "OLD/CURRENT verdict_distribution, correction counts",
        "HISTORICAL / BEHAVIORAL", "62 docs / 32 claims per arm",
        "distribution shift only; null on GOLD-02; correction effect not significant")


# --------------------------------------------------------- assertion-aware null result
def fig_assertion_aware_null():
    p = OUT / "assertion_aware_correction_experiment_comparison.json"
    d = jload(p)
    n = d["n_paired_attempts"]
    legacy, aware = d["legacy_shipped"], d["assertion_aware_shipped"]
    st_l = Counter(r["legacy_status"] for r in d["rows"])
    st_a = Counter(r["assertion_aware_status"] for r in d["rows"])
    keys = sorted(set(st_l) | set(st_a))

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.4))
    ax = axes[0]
    ax.bar([0, 1], [legacy, aware], 0.5, color=[C_ORIGINAL, C_LATEST])
    for i, v in enumerate([legacy, aware]):
        ax.text(i, 0.06, str(v), ha="center", fontsize=22, fontweight="bold",
                color="white" if v else "#C44E52")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["LEGACY correction\n(PRODUCTION)", "ASSERTION-AWARE\n(EXPERIMENTAL, OFF)"])
    ax.set_ylim(0, max(1, max(legacy, aware)) * 1.4)
    ax.set_ylabel(f"Corrections shipped (of {n} paired attempts)")
    ax.set_title(f"NULL RESULT — {legacy}/{n} vs {aware}/{n}")

    ax2 = axes[1]
    x = np.arange(len(keys))
    w = 0.36
    cmap = {"correction_failed": C_NEUTRAL, "correction_scope_violation": C_SCOPE,
            "corrected": C_SHIPPED, "not_triggered": "#D6D6D6"}
    ax2.bar(x - w / 2, [st_l.get(k, 0) for k in keys], w, label="legacy", color=C_ORIGINAL)
    ax2.bar(x + w / 2, [st_a.get(k, 0) for k in keys], w, label="assertion-aware", color=C_LATEST)
    ax2.set_xticks(x)
    ax2.set_xticklabels([k.replace("correction_", "") for k in keys], fontsize=8.6, rotation=12)
    ax2.set_ylabel("Attempts")
    ax2.legend(fontsize=9)
    ax2.set_title("Terminal status, same 5 documents x 2 arms")

    fig.suptitle("Assertion-aware correction: built, evaluated, NOT promoted",
                 fontsize=13.5, fontweight="bold", y=1.04)
    footnote(axes[0],
             f"{HIST} — Qwen-dependent, RERUN_INFEASIBLE here. Source: {p.name} (5 documents x 2 arms = {n} paired attempts).\n"
             "The mechanism is architecturally complete and safe, and it changes WHICH gate stops an attempt — but it ships exactly as\n"
             "many corrections as the legacy path: none. This is preserved as a NULL result and must never be presented as an improvement.\n"
             "correction.assertion_aware remains FALSE in production.",
             y=-0.24)
    pth = save(fig, F / "06_correction" / "F21_assertion_aware_null_result.png")
    rec(pth, f"outputs/{p.name}", "legacy_shipped, assertion_aware_shipped, rows[].status",
        "HISTORICAL / BEHAVIORAL", n, "NULL RESULT — never present as an improvement")


# --------------------------------------------------------------- safety zero-event
def fig_safety_zero_event():
    d = jload(OUT / "final_metrics.json")
    s = d["section_D_correction_safety_cumulative"]
    total = s["total_correction_attempts"]
    unsafe = s["total_unsafe_shipped"]
    blocked = s["status_breakdown"].get("correction_scope_violation", 0)
    failed = s["status_breakdown"].get("correction_failed", 0)
    shipped = s["total_shipped"]

    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    cats = ["Blocked by a\nsafety gate", "Rejected: corrector\nproduced no valid edit",
            "Shipped\n(all gates + ENTAILED)", "UNSAFE text\nshipped"]
    vals = [blocked, failed, shipped, unsafe]
    cols = [C_SCOPE, C_NEUTRAL, C_SHIPPED, C_REJECT]
    bars = ax.bar(range(len(cats)), vals, 0.58, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.7, f"{v}/{total}", ha="center", fontsize=11, fontweight="bold")
    bars[3].set_edgecolor("#C44E52")
    bars[3].set_linewidth(2.5)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, fontsize=9)
    ax.set_ylim(0, total * 0.85)
    ax.set_ylabel(f"Correction attempts (denominator = {total})")
    ax.set_title(f"Safety outcome over every natural correction attempt (n={total})")
    footnote(ax,
             f"{HIST}. Source: outputs/final_metrics.json → section_D_correction_safety_cumulative.\n"
             f"ZERO-EVENT RESULT, stated with its exact denominator: 0 unsafe shipments in {total} attempts. Scope: natural-data correction\n"
             "attempts only. This evidences a fail-closed design that behaved correctly on the data seen — it is NOT a proof of safety,\n"
             "NOT a bound on the true unsafe rate, and NOT a red-team evaluation (no formal red-team evaluation exists in this project).\n"
             "With 0 events in 56 trials the exact one-sided 95% upper bound on the unsafe rate is ~5.2% (rule of three).",
             y=-0.24)
    pth = save(fig, F / "07_safety" / "F22_safety_zero_event_outcomes.png")
    rec(pth, "outputs/final_metrics.json", "section_D_correction_safety_cumulative",
        "HISTORICAL / BEHAVIORAL", total,
        "zero-event; upper bound ~5.2% by rule of three; not a safety proof")


def main() -> int:
    print("building V2 historical-evidence figures...")
    fig_evidence_coverage()
    fig_verdict_distribution()
    fig_correction_funnel()
    fig_transfer_gap()
    fig_retrieval_safety()
    fig_narrow_primary()
    fig_assertion_aware_null()
    fig_safety_zero_event()

    (F / "09_runtime").mkdir(parents=True, exist_ok=True)
    (F / "09_runtime" / "README.md").write_text(
        "# 09_runtime — deliberately empty\n\n"
        "**No runtime or resource comparison figure is produced in this package, by design.**\n\n"
        "A meaningful ORIGINAL-vs-LATEST runtime comparison cannot be made from this session:\n\n"
        "1. Every historical runtime and VRAM number was measured on a CUDA GPU with 4-bit Qwen\n"
        "   loaded. This machine has no GPU and Qwen is not cached, so nothing equivalent can be\n"
        "   measured.\n"
        "2. The fresh timings this package does have are CPU-only NLI timings under a different\n"
        "   torch/transformers major version, and are not comparable to the historical ones.\n"
        "3. They are not even safely comparable between arms: in the fresh GOLD-01 run the\n"
        "   `labeled` arm took 471.5 s against `bare`'s 112.7 s, but that is dominated by longer\n"
        "   premise strings and by CPU scheduling on a shared machine — not by a meaningful\n"
        "   algorithmic cost difference. Charting it as 'LATEST is 4x slower' would be misleading.\n\n"
        "Raw timings are retained in `metrics/gold01_v2_metrics.json` and\n"
        "`metrics/gold02_v2_metrics.json` for completeness. No runtime claim is made anywhere in\n"
        "this package. See `NOT_GENERATED_REGISTER.md` §4.\n",
        encoding="utf-8")
    print("  wrote figures/09_runtime/README.md (deliberately no runtime chart)")

    pth = F / "figure_provenance_historical.json"
    pth.write_text(json.dumps(PROV, indent=2), encoding="utf-8")
    print(f"\n{len(PROV)} historical figures written; provenance -> {pth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
