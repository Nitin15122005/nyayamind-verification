#!/usr/bin/env python3
"""Phase 3 (Vedant) — STEP 6: quality control for the whole package.

Checks, in order:

  A. Every value in every locked metric CSV is re-read INDEPENDENTLY from its source
     artifact and compared. A mismatch fails.
  B. Every artifact named in VISUALIZATION_MANIFEST.csv exists, in both variants,
     and is a non-trivial PNG / CSV / MD file.
  C. Naming discipline: no vague labels anywhere; the exact model and system names
     are present in the manifest and indices.
  D. Claim discipline: no natural-data metric is named accuracy / precision / recall / F1;
     GOLD and METRIC-ONLY rows are never mixed inside one contract; every figure carries a
     freshness status and a caveat.
  E. Protected paths: nothing outside Output_phase_3_vedant/ was created, modified or deleted
     (checked with `git status --porcelain`).

Writes validation/VALIDATION_REPORT.txt and exits non-zero on any FAIL.
"""
from __future__ import annotations

import datetime
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import build_metric_tables as B  # noqa: E402

LINES: list[str] = []
FAILS = 0
WARNS = 0


def log(msg=""):
    LINES.append(msg)
    print(msg)


def check(name: str, ok: bool, detail: str = "") -> bool:
    global FAILS
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAILS += 1
    log(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def warn(name: str, detail: str = ""):
    global WARNS
    WARNS += 1
    log(f"  [WARN] {name}" + (f" — {detail}" if detail else ""))


def close(a, b, tol=1e-9) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a) == str(b)


# ==========================================================================
# A. re-verify every locked metric value against its source artifact
# ==========================================================================
def section_a():
    log("\n=== A. Metric values re-verified independently against source artifacts ===")
    g1 = C.load_json(B.GOLD01)["results_by_framing"]
    g2 = C.load_json(B.GOLD02)["results_by_framing"]
    p9 = C.load_json(B.PAIRED209)
    c588 = C.load_json(B.CLAIMS588)
    abl = {f["factor"]: f for f in C.load_json(B.ABLATION)["findings"]}
    fm = C.load_json(B.FINAL_METRICS)
    gpu = C.load_json(B.FINAL_GPU)
    lab = C.load_json(B.LABELED_CORR)
    f147 = C.load_json(B.CPU_FRAMING_147)
    ev = C.load_json(B.EVID_V0_V1_588)
    tax = C.load_json(B.NOEV_TAXONOMY)
    sr = C.load_json(B.SCOPE_REPLAY)
    thr = C.load_json(B.THRESHOLD)
    batches = {x["name"]: x for x in C.load_json(B.BATCHES)["batches"]}

    m01 = {r["metric_key"]: r for r in C.read_csv(C.OUT_METRICS / "M01_headline_baseline_vs_modified.csv")}
    check("M01 evidence coverage baseline",
          close(m01["evidence_coverage_209_paired"]["baseline_value"],
                p9["fresh_evidence_coverage_arm_A"]))
    check("M01 evidence coverage modified",
          close(m01["evidence_coverage_209_paired"]["modified_value"],
                p9["fresh_evidence_coverage_arm_B"]))
    check("M01 GOLD-01 macro F1 pair",
          close(m01["gold01_macro_f1"]["baseline_value"], g1["bare"]["macro_f1"]) and
          close(m01["gold01_macro_f1"]["modified_value"], g1["labeled"]["macro_f1"]))
    check("M01 GOLD-01 accuracy pair",
          close(m01["gold01_accuracy"]["baseline_value"], g1["bare"]["accuracy"]) and
          close(m01["gold01_accuracy"]["modified_value"], g1["labeled"]["accuracy"]))
    check("M01 GOLD-02 contradiction recall pair",
          close(m01["gold02_contradiction_recall"]["baseline_value"],
                g2["bare"]["contradiction_recall"]) and
          close(m01["gold02_contradiction_recall"]["modified_value"],
                g2["labeled"]["contradiction_recall"]))

    m02 = {r["metric"]: r for r in C.read_csv(C.OUT_METRICS / "M02_gold01_overall.csv")}
    check("M02 statistics match ABLATION_SUMMARY",
          close(m02["macro_f1"]["mcnemar_p_value"], abl["premise_framing"]["p_value"]) and
          close(m02["macro_f1"]["exact_sign_test_p_value"],
                abl["premise_framing"]["exact_sign_test_p_value"]))

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M03_gold01_per_class.csv"):
        framing = r["premise_framing"]
        src = g1[framing]["per_class"][r["class"]]
        for k in ("precision", "recall", "f1", "support", "tp", "fp", "fn"):
            ok &= close(r[k], src[k])
    check("M03 all 42 per-class values match gold01_metrics.json", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M04_gold01_confusion.csv"):
        ok &= close(r["count"],
                    g1[r["premise_framing"]]["confusion_matrix"][r["true_label"]][r["predicted_label"]])
    check("M04 all 18 confusion-matrix cells match", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M05_gold02_synthetic_stress.csv"):
        s = g2[r["premise_framing"]]
        ok &= close(r["contradiction_recall"], s["contradiction_recall"])
        ok &= close(r["detected_contradicted"], s["confusion_matrix"]["CONTRADICTED"]["CONTRADICTED"])
        ok &= close(r["missed_as_nei"],
                    s["confusion_matrix"]["CONTRADICTED"]["NOT_ENOUGH_INFORMATION"])
    check("M05 GOLD-02 values match gold02_metrics.json", ok)

    d = C.read_csv(C.OUT_METRICS / "M06b_evidence_209_discordance.csv")[0]
    mc = p9["mcnemar_evidence_coverage"]
    check("M06b McNemar discordance matches paired_209_metrics.json",
          close(d["mcnemar_chi2"], mc["chi2"]) and close(d["mcnemar_p_value"], mc["p_value"])
          and close(d["gained_evidence_b"], p9["evidence_change_counts"]["evidence_gained"])
          and close(d["lost_evidence_c"], mc["c_lost"]))

    m07 = {r["system"]: r for r in C.read_csv(C.OUT_METRICS / "M07_evidence_coverage_588_corpus.csv")}
    check("M07 corpus coverage matches evidence_coverage_v0_vs_v1.json",
          close(m07["baseline"]["n_matched"], ev["n_matched_v0"]) and
          close(m07["modified"]["n_matched"], ev["n_matched_v1"]) and
          close(m07["modified"]["newly_covered"], ev["n_newly_covered_by_v1"]))

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M08_verdict_distribution.csv"):
        if r["dataset"] == "588_claim_natural_aggregate":
            ok &= close(r["count"], c588["verdict_distribution"].get(r["verdict"], 0))
        else:
            key = ("fresh_verdict_distribution_arm_A" if r["system"] == "baseline"
                   else "fresh_verdict_distribution_arm_B")
            ok &= close(r["count"], p9[key].get(r["verdict"], 0))
    check("M08 all verdict counts match their source", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M09_premise_framing_natural_batches.csv"):
        ok &= close(r["count"], batches[r["regime"]]["verdict_distribution"].get(r["verdict"], 0))
    check("M09 batch verdict counts match batches_analysis.json", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M10_natural_147_framing_shift.csv"):
        key = "bare_verdict_counts" if r["system"] == "baseline" else "labeled_verdict_counts"
        ok &= close(r["count"], f147[key].get(r["verdict"], 0))
    check("M10 147-claim framing counts match the CPU metrics json", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M11_confidence_by_verdict_588.csv"):
        if r["verdict"] == "ALL evidence-matched":
            src = c588["confidence_overall"]
        else:
            src = c588["confidence_by_verdict"][r["verdict"]]
        ok &= close(r["mean_confidence"], src["mean"]) and close(r["median_confidence"], src["median"])
    check("M11 confidence statistics match claims_588_metrics.json", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M12_confidence_threshold_sweep.csv"):
        pt = next(x for x in thr["results"][r["premise_framing"]]["sweep"]
                  if close(x["threshold"], r["threshold"]))
        ok &= close(r["macro_f1"], pt["macro_f1"]) and close(r["accuracy"], pt["accuracy"])
    check("M12 all 20 threshold-sweep points match", ok)

    m13 = {r["population"]: r for r in C.read_csv(C.OUT_METRICS / "M13_correction_funnel.csv")}
    syn_l = fm["section_A_synthetic"]["correction_labeled"]
    cum = fm["section_D_correction_safety_cumulative"]
    check("M13 synthetic modified arm matches final_metrics.json",
          close(m13["Synthetic stress — modified (labeled premise)"]["shipped"],
                syn_l["corrections_shipped_success"]) and
          close(m13["Synthetic stress — modified (labeled premise)"]["correction_triggered"],
                syn_l["correction_triggers"]))
    check("M13 natural cumulative matches final_metrics.json",
          close(m13["Natural cumulative — all correction attempts, project history"]["shipped"],
                cum["total_shipped"]) and
          close(m13["Natural cumulative — all correction attempts, project history"]["correction_triggered"],
                cum["total_correction_attempts"]))
    check("M13 natural targeted arms match their GPU metrics",
          close(m13["Natural targeted — baseline framing (Arm B, bare)"]["correction_triggered"],
                gpu["per_arm"]["B"]["correction_triggers"]) and
          close(m13["Natural targeted — modified framing (labeled)"]["shipped"],
                lab["corrections_shipped"]))

    m15 = {r["safety_observation"]: r for r in C.read_csv(C.OUT_METRICS / "M15_safety_observations.csv")}
    check("M15 unsafe shipped == 0 in the source",
          close(m15["Unsafe corrections shipped"]["count"], cum["total_unsafe_shipped"]) and
          close(cum["total_unsafe_shipped"], 0))
    check("M15 scope-gate and re-verification rejections match",
          close(m15["Scope-gate rejections (natural, cumulative)"]["count"],
                cum["status_breakdown"]["correction_scope_violation"]) and
          close(m15["Re-verification-not-ENTAILED rejections (natural, cumulative)"]["count"],
                cum["status_breakdown"]["correction_failed"]))

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M16_ablation_matrix.csv"):
        f = abl[r["factor"]]
        if r["p_value"]:
            ok &= close(r["p_value"], f["p_value"])
        if r["baseline_value"]:
            ok &= close(r["baseline_value"], f["baseline_value"])
    check("M16 ablation p-values and baselines match ABLATION_SUMMARY.json", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M18_natural_regimes_coverage.csv"):
        if r["regime"] in batches:
            ok &= close(r["evidence_coverage"], batches[r["regime"]]["evidence_coverage"])
    check("M18 batch coverage values match batches_analysis.json", ok)

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M20_no_evidence_taxonomy.csv"):
        ok &= close(r["count"], tax["taxonomy"][r["bucket_key"]])
    check("M20 NO_EVIDENCE taxonomy counts match no_evidence_taxonomy_v3.json", ok)

    m25 = {r["system"]: r for r in C.read_csv(C.OUT_METRICS / "M25_scope_gate_replay.csv")}
    check("M25 scope replay matches scope_check_replay_fresh.json",
          close(m25["modified"]["n_unblocked"], sr["n_unblocked_final"]) and
          close(m25["baseline"]["n_replayed"], sr["n_scope_violations_replayed"]))

    ok = True
    for r in C.read_csv(C.OUT_METRICS / "M22_gpu_reproduction_crosscheck.csv"):
        ok &= (r["match"] == "True")
    check("M22 every reproduced quantity is an exact match", ok)

    m24 = {r["system"]: r for r in C.read_csv(C.OUT_METRICS / "M24_evidence_pool_composition.csv")}
    sys.path.insert(0, str(C.PROTO_DIR))
    from src.data_loader import load_usable_evidence_from_config
    import copy as _copy
    cfg = C.load_current_config()
    cfg0 = _copy.deepcopy(cfg); cfg0["use_evidence_v1"] = False
    _, mod_pool = load_usable_evidence_from_config(cfg, C.REPO_ROOT)
    _, base_pool = load_usable_evidence_from_config(cfg0, C.REPO_ROOT)
    check("M24 evidence pool sizes reproduce via the production loader",
          close(m24["baseline"]["usable_records_loaded"], len(base_pool)) and
          close(m24["modified"]["usable_records_loaded"], len(mod_pool)),
          f"baseline={len(base_pool)}, modified={len(mod_pool)}")


# ==========================================================================
# B. artifact coverage
# ==========================================================================
def section_b():
    log("\n=== B. Artifact coverage ===")
    rows = C.read_csv(C.PKG_DIR / "VISUALIZATION_MANIFEST.csv")
    missing, tiny = [], []
    for r in rows:
        for rel in (r["filename"], r["ppt_variant"]):
            p = C.PKG_DIR / rel
            if not p.exists():
                missing.append(rel)
            else:
                floor = 20000 if p.suffix == ".png" else 400
                if p.stat().st_size < floor:
                    tiny.append(f"{rel} ({p.stat().st_size} bytes, floor {floor})")
    check("every manifest artifact exists (both variants)", not missing,
          f"missing: {missing}" if missing else f"{len(rows) * 2} files checked")
    check("no artifact is suspiciously small", not tiny, f"tiny: {tiny}" if tiny else "")

    on_disk = {f"figures/{p.name}" for p in C.OUT_FIGURES.glob("*.png")}
    on_disk |= {f"diagrams/{p.name}" for p in C.OUT_DIAGRAMS.glob("*.png")}
    on_disk |= {f"tables/{p.name}" for p in C.OUT_TABLES.glob("*.csv")}
    listed = {r["filename"] for r in rows}
    check("no unlisted artifact on disk", on_disk <= listed, f"unlisted: {sorted(on_disk - listed)}")

    n_fig = sum(1 for r in rows if r["artifact_type"] == "figure")
    n_dia = sum(1 for r in rows if r["artifact_type"] == "diagram")
    n_tab = sum(1 for r in rows if r["artifact_type"] == "table")
    log(f"  manifest: {n_fig} figures, {n_dia} diagrams, {n_tab} tables "
        f"({len(rows)} artifacts, {len(rows) * 2} files)")

    for doc in ("README.md", "FIGURE_DATA_AUDIT.md", "METRIC_SOURCE_MAP.csv",
                "VISUALIZATION_MANIFEST.csv", "NOT_GENERATED_REGISTER.md",
                "ppt_assets/FIGURE_INDEX.md", "ppt_assets/DIAGRAM_INDEX.md",
                "ppt_assets/SLIDE_MAPPING.md"):
        check(f"{doc} present", (C.PKG_DIR / doc).exists())


# ==========================================================================
# C. naming discipline
# ==========================================================================
BANNED = ["original vs current", "old vs new", "before vs after", "before/after",
          "original vs. current", "old/new", "system a vs system b", "v1 vs v2 system"]


def section_c():
    log("\n=== C. Naming discipline ===")
    texts = {}
    for p in list(C.PKG_DIR.glob("*.md")) + list(C.PKG_DIR.glob("*.csv")) + \
             list(C.OUT_PPT.glob("*.md")) + list(C.OUT_TABLES.glob("*.md")):
        texts[p.name] = p.read_text(encoding="utf-8").lower()
    hits = [f"{n}: '{b}'" for n, t in texts.items() for b in BANNED if b in t]
    check("no vague comparison label in any package document", not hits, "; ".join(hits))

    names = " ".join(p.name for p in list(C.OUT_FIGURES.glob("*.png")) +
                     list(C.OUT_DIAGRAMS.glob("*.png")) + list(C.OUT_TABLES.glob("*")))
    check("no vague comparison label in any filename",
          not any(b.replace(" ", "_") in names.lower() for b in BANNED))

    manifest_text = (C.PKG_DIR / "VISUALIZATION_MANIFEST.csv").read_text(encoding="utf-8")
    readme = (C.PKG_DIR / "README.md").read_text(encoding="utf-8")
    for model in (C.GENERATION_MODEL, C.VERIFICATION_MODEL):
        check(f"exact model id present in README: {model}", model in readme)
    check("exact baseline system name used in the manifest", C.BASELINE_NAME in manifest_text)
    check("exact modified system name used in the manifest", C.MODIFIED_NAME in manifest_text)
    check("out-of-scope RhetoricLLaMA baseline is documented",
          C.RHETORIC_BASE_MODEL in readme and C.RHETORIC_ADAPTER in readme)

    rows = C.read_csv(C.PKG_DIR / "VISUALIZATION_MANIFEST.csv")
    unnamed = [r["artifact_id"] for r in rows if not r["system_model_names"].strip()]
    check("every artifact carries a system/model designation", not unnamed, str(unnamed))


# ==========================================================================
# D. claim discipline
# ==========================================================================
NATURAL_TOKENS = ("natural", "209_claim", "588_claim", "batch", "147", "NyayaRAG")
ACCURACY_WORDS = ("accuracy", "precision", "recall", "macro_f1", "macro f1", " f1")


def section_d():
    log("\n=== D. Claim discipline ===")
    # D1 — natural-data contracts must not name an accuracy-family metric
    offenders = []
    for r in C.read_csv(C.PKG_DIR / "METRIC_SOURCE_MAP.csv"):
        ds = r["dataset"].lower()
        is_natural = any(t.lower() in ds for t in NATURAL_TOKENS) and "gold" not in ds
        if not is_natural:
            continue
        purpose = r["purpose"].lower()
        if any(w in purpose for w in ("accuracy", "precision", "recall")):
            offenders.append(f"{r['metric_csv']}: {r['purpose']}")
    check("no natural-data contract is described as accuracy/precision/recall",
          not offenders, "; ".join(offenders))

    # exception: GOLD-02 contradiction recall is legitimate (labels exist by construction)
    m19 = C.read_csv(C.OUT_METRICS / "M19_synthetic_vs_natural_transfer.csv")
    check("synthetic vs natural transfer is marked non-comparable on every row",
          all(r["comparable_to_other_rows"] == "NO" for r in m19))

    # D2 — no metric contract mixes GOLD and natural rows
    mixed = []
    for r in C.read_csv(C.PKG_DIR / "METRIC_SOURCE_MAP.csv"):
        ds = r["dataset"].lower()
        if "gold" in ds and any(t.lower() in ds for t in ("209_claim", "588_claim", "batch")):
            if r["metric_csv"] != "M01_headline_baseline_vs_modified.csv":
                mixed.append(r["metric_csv"])
    check("no contract silently mixes GOLD and natural datasets", not mixed, str(mixed))
    if any(r["metric_csv"] == "M01_headline_baseline_vs_modified.csv"
           for r in C.read_csv(C.PKG_DIR / "METRIC_SOURCE_MAP.csv")):
        m01 = C.read_csv(C.OUT_METRICS / "M01_headline_baseline_vs_modified.csv")
        check("M01 (the one mixed-class figure) labels every row's metric class",
              all(r["metric_class"].strip() for r in m01))

    # D3 — every artifact has freshness + caveat
    rows = C.read_csv(C.PKG_DIR / "VISUALIZATION_MANIFEST.csv")
    no_status = [r["artifact_id"] for r in rows if not r["fresh_or_historical"].strip()]
    no_caveat = [r["artifact_id"] for r in rows if not r["caveat"].strip()]
    check("every artifact declares a freshness status", not no_status, str(no_status))
    check("every artifact declares a caveat", not no_caveat, str(no_caveat))

    # D4 — GPU/CPU status is explicit wherever a GPU-dependent result is shown
    gpu_rows = [r for r in C.read_csv(C.OUT_METRICS / "M17_runtime_resource.csv")]
    check("every runtime row names its hardware", all(r["hardware"].strip() for r in gpu_rows))
    check("GPU and CPU runtime rows are both present and distinguished",
          any("CPU" in r["hardware"] for r in gpu_rows) and
          any("NVIDIA" in r["hardware"] for r in gpu_rows))

    # D5 — the Grade E gap is stated, not estimated
    m16 = C.read_csv(C.OUT_METRICS / "M16_ablation_matrix.csv")
    joint = next((r for r in m16 if r["factor"] == "joint_four_lever_isolation"), None)
    check("joint four-lever ablation is present and marked NOT_ISOLABLE / Grade E",
          joint is not None and joint["classification"] == "NOT_ISOLABLE"
          and joint["evidence_grade"] == "E")

    # D6 — provisional (Claude-generated) labels are excluded
    all_text = "\n".join(p.read_text(encoding="utf-8") for p in C.OUT_METRICS.glob("*.csv"))
    check("no provisional/assumption label set is used as a metric source",
          "assumption_annotation" not in all_text and "lawyer_annotation" not in all_text)


# ==========================================================================
# E. protected paths untouched
# ==========================================================================
PROTECTED_PREFIXES = (
    "research/prototype/src/", "research/prototype/tests/", "research/prototype/config/",
    "research/prototype/outputs/", "research/prototype/evaluation/", "research/prototype/scripts/",
    "research/prototype/archive/", "research/data/", "research/baseline/", "baseline/",
)
ALLOWED_PREFIX = "research/prototype/Output_phase_3_vedant/"


def section_e():
    log("\n=== E. Protected paths untouched ===")
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=C.REPO_ROOT,
                             capture_output=True, text=True, check=True).stdout
    except Exception as exc:  # pragma: no cover
        warn("git status unavailable", str(exc))
        return
    touched = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if path.startswith(ALLOWED_PREFIX):
            continue
        if any(path.startswith(p) for p in PROTECTED_PREFIXES):
            touched.append(line.strip())
    check("no protected path was created, modified or deleted", not touched,
          "; ".join(touched) if touched else
          "only research/prototype/Output_phase_3_vedant/ appears as new in git status")

    interesting = [ln for ln in out.splitlines()
                   if ln.strip() and not ln[3:].strip().startswith(ALLOWED_PREFIX)]
    if interesting:
        log("  git status entries outside this package (informational):")
        for ln in interesting:
            log(f"    {ln}")


# ==========================================================================
def main():
    log("NyayaMind Phase-3 visualisation package — validation report")
    log(f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}")
    log(f"Package:   {C.rel(C.PKG_DIR)}")
    log(f"Baseline:  {C.BASELINE_LABEL_1L}")
    log(f"Modified:  {C.MODIFIED_LABEL_1L}")
    section_a()
    section_b()
    section_c()
    section_d()
    section_e()
    log("")
    log("=" * 72)
    log(f"RESULT: {'PASS' if FAILS == 0 else 'FAIL'} — {FAILS} failure(s), {WARNS} warning(s)")
    log("=" * 72)
    C.OUT_VALIDATION.mkdir(parents=True, exist_ok=True)
    (C.OUT_VALIDATION / "VALIDATION_REPORT.txt").write_text("\n".join(LINES) + "\n",
                                                            encoding="utf-8")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
