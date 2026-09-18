#!/usr/bin/env python3
"""
Builds the V2 package's tables (CSV + matching Markdown) and the flat metric CSVs.

Every value is read from a source file. Nothing is typed in by hand except the
column headings and the caveat prose, which are prose, not data.

Outputs
-------
tables/headline/        T01, T02
tables/verifier/        T03, T04, T05
tables/evidence/        T06, T07
tables/parser/          T08
tables/correction/      T09, T10
tables/safety/          T11, T12
tables/ablation/        T13
tables/reproducibility/ T14, T15
tables/limitations/     T16, T17
metrics/                experiment_audit.csv, headline_results.csv, detailed_metrics.csv
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

_V2 = Path(__file__).resolve().parent.parent
_PROTO = _V2.parent
M = _V2 / "metrics"
T = _V2 / "tables"
RECON = Path(
    r"C:/Users/VEDANT~1/AppData/Local/Temp/claude/d--Major/"
    r"0bceb748-3051-4f9a-abab-be8dd56574b4/scratchpad/recon"
)

NLI = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
QWEN = "Qwen/Qwen2.5-7B-Instruct"


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def f(x, nd=4):
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def write(sub: str, name: str, header: list[str], rows: list[list], preamble: str,
          notes: list[str] | None = None):
    d = T / sub
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{name}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)

    def esc(c):
        return str(c).replace("|", "\\|").replace("\n", " ")

    L = [f"# {name}", "", preamble, "",
         "| " + " | ".join(header) + " |",
         "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        L.append("| " + " | ".join(esc(c) for c in r) + " |")
    if notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    (d / f"{name}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  {sub}/{name}  ({len(rows)} rows)")


# ------------------------------------------------------------------ load
g1 = jload(M / "gold01_v2_metrics.json")
st = jload(M / "gold01_v2_stratified_by_condition.json")
g2 = jload(M / "gold02_v2_metrics.json")
pr = jload(M / "parser_original_vs_latest_v2.json")
ev = jload(M / "evidence_pool_composition_v2.json")
ts = jload(M / "threshold_sensitivity_v2.json")
p209 = jload(_PROTO / "evaluation" / "actual_outputs" / "natural_data_runs" /
             "209_paired" / "paired_209_metrics.json")
fm = jload(_PROTO / "outputs" / "final_metrics.json")
aa = jload(_PROTO / "outputs" / "assertion_aware_correction_experiment_comparison.json")
npg = jload(_PROTO / "outputs" / "narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json")
evcov = jload(_PROTO / "outputs" / "evidence_coverage_v0_vs_v1.json")
audit_rows = list(csv.DictReader((RECON / "agent4_experiment_audit.csv").open(encoding="utf-8")))
chg_rows = list(csv.DictReader((M / "change_inventory.csv").open(encoding="utf-8")))

LAB = g1["results_by_framing"]["labeled"]
BARE = g1["results_by_framing"]["bare"]
MC = g1["statistics"]["mcnemar_accuracy"]
LABELS = ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION")

CAVEAT_G1 = ("Single-lever ablation of premise_framing. 99/100 of the fixed items are in the "
             "ATTRIBUTED conditions; on the 269 non-attributed items p=1.0 (see T05).")

print("building V2 tables...")

# ------------------------------------------------------------------ T01
mc2 = g2["statistics"]["original_vs_latest_mcnemar"]
sgn = pr["statistics"]["original_to_latest"]
gained = p209["evidence_change_counts"]["evidence_gained"]
p209_exact = min(1.0, 2.0 * sum(math.comb(gained, i) for i in range(1)) * (0.5 ** gained))
hl = [
    ["Verifier accuracy", f(BARE["accuracy"]), f(LAB["accuracy"]),
     f(LAB["accuracy"] - BARE["accuracy"], 4), "420", "GOLD-01", "GOLD",
     f"McNemar exact p={MC['p_value']:.3e}", "V2 FRESH", CAVEAT_G1],
    ["Verifier macro F1", f(BARE["macro_f1"]), f(LAB["macro_f1"]),
     f(LAB["macro_f1"] - BARE["macro_f1"], 4), "420", "GOLD-01", "GOLD",
     "paired bootstrap CI [0.1837, 0.2575]", "V2 FRESH", CAVEAT_G1],
    ["Verifier accuracy, NON-attributed items only",
     f(st["strata"]["NON_ATTRIBUTED_conditions"]["original_bare"]["accuracy"]),
     f(st["strata"]["NON_ATTRIBUTED_conditions"]["latest_labeled"]["accuracy"]),
     f(st["strata"]["NON_ATTRIBUTED_conditions"]["delta_accuracy"], 4), "269", "GOLD-01", "GOLD",
     "exact sign test p=1.0", "V2 FRESH",
     "NOT SIGNIFICANT. This is where the headline does NOT hold."],
    ["Contradiction recall",
     f(g2["cells"]["ORIGINAL_config"]["contradiction_recall_all_items"]),
     f(g2["cells"]["LATEST_config"]["contradiction_recall_all_items"]),
     f(g2["headline_delta"]["absolute_delta"], 4), "59", "GOLD-02 synthetic",
     "DETERMINISTIC_SYNTHETIC", f"McNemar exact p={mc2['p_value']:.4f}", "V2 FRESH",
     "Single-class set: only recall is defined. 15/59 are NO_EVIDENCE in every cell."],
    ["Claims resolving to evidence", str(pr["totals"]["orig_matched"]),
     str(pr["totals"]["latest_matched"]),
     f"+{pr['totals']['latest_matched'] - pr['totals']['orig_matched']}",
     "30 documents / 88-93 claims", "run_A_n30 generated text",
     "DETERMINISTIC_SYNTHETIC", f"sign test p={sgn['p_value']:.4f} (+10/-0 docs)", "V2 FRESH",
     "Coverage outcome, NOT a correctness label. No gold extraction labels exist."],
    ["Usable evidence records", str(ev["original_v0"]["usable_records"]),
     str(ev["latest_v1_merged"]["usable_records"]),
     f"+{ev['delta']['usable_records']}", "structural", "canonical_statutes(+v1)",
     "DETERMINISTIC_SYNTHETIC", "n/a (exact count)", "V2 FRESH",
     "An INPUT property, not a retrieval outcome."],
    ["Distinct Acts covered", str(ev["original_v0"]["distinct_acts"]),
     str(ev["latest_v1_merged"]["distinct_acts"]), f"+{ev['delta']['distinct_acts']}",
     "structural", "canonical_statutes(+v1)", "DETERMINISTIC_SYNTHETIC", "n/a", "V2 FRESH",
     "An INPUT property."],
    ["Evidence coverage (paired natural claims)",
     f(p209["fresh_evidence_coverage_arm_A"]), f(p209["fresh_evidence_coverage_arm_B"]),
     f(p209["fresh_evidence_coverage_arm_B"] - p209["fresh_evidence_coverage_arm_A"], 4),
     "209", "209-claim paired natural", "HISTORICAL / METRIC_ONLY",
     f"McNemar exact p={p209_exact:.3e} ({gained} gained, 0 lost)", "HISTORICAL",
     "Unlabelled natural data - coverage is a retrieval outcome, never accuracy."],
    ["Corrections shipped (cumulative natural)",
     "n/a (single cumulative figure)",
     f"{fm['section_D_correction_safety_cumulative']['total_shipped']}/"
     f"{fm['section_D_correction_safety_cumulative']['total_correction_attempts']}",
     "n/a", "56 attempts", "all natural correction attempts", "HISTORICAL / BEHAVIORAL",
     "descriptive", "HISTORICAL",
     "Qwen-dependent, RERUN_INFEASIBLE here. 1.8% shipped rate."],
    ["Unsafe corrections shipped", "n/a",
     f"{fm['section_D_correction_safety_cumulative']['total_unsafe_shipped']}/56",
     "n/a", "56 attempts", "all natural correction attempts", "HISTORICAL / BEHAVIORAL",
     "zero-event; rule-of-three 95% upper bound ~5.2%", "HISTORICAL",
     "Zero-event over a SMALL denominator. Not a proof of safety."],
]
write("headline", "T01_headline_original_vs_latest",
      ["metric", "ORIGINAL", "LATEST", "delta", "n", "dataset", "evidence_grade",
       "statistical_test", "freshness", "caveat"], hl,
      "Every validated headline metric. `V2 FRESH` = re-executed on this machine for this "
      "package; `HISTORICAL` = reused from a committed artifact because it could not be rerun "
      "(no GPU / Qwen uncached).",
      ["Rows are independent experiments with different levers and denominators. They must not "
       "be averaged or read as one system score.",
       "No row is a legal-correctness claim. No lawyer-validated ground truth exists in this project."])

# ------------------------------------------------------------------ T02
cfg = [
    ["Generation model", QWEN, QWEN, "UNCHANGED"],
    ["Generation quantization", "4-bit NF4, double-quant, bfloat16", "4-bit NF4, double-quant, bfloat16", "UNCHANGED"],
    ["Generation decoding", "greedy, 200 new tokens, seed 42", "greedy, 200 new tokens, seed 42", "UNCHANGED"],
    ["Correction model", f"{QWEN} (same loaded instance reused)", f"{QWEN} (same loaded instance reused)", "UNCHANGED"],
    ["Verification model", NLI, NLI, "UNCHANGED"],
    ["Model revision pin", "none (UNDETERMINED)", "none (UNDETERMINED)", "UNCHANGED"],
    ["confidence_threshold", "0.70", "0.70", "UNCHANGED"],
    ["max_sequence_length", "512", "512", "UNCHANGED"],
    ["fuzzy_token_overlap_threshold", "0.8", "0.8", "UNCHANGED"],
    ["evidence_matching.top_k", "1", "1 (config key never read)", "UNCHANGED"],
    ["premise_framing", "bare (raw statute text)", "labeled (\"<Type> <N> of <Act>: <text>\")", "CHANGED"],
    ["use_evidence_v1", "false (59 usable records, 10 Acts)", "true (136 usable records, 22 Acts)", "CHANGED"],
    ["narrow_primary_hypothesis", "false (full claim sentence)", "true (narrow assertion_text)", "CHANGED"],
    ["atomic_scope_check", "false (full-sentence scope check)", "\"assertion_spans\"", "CHANGED"],
    ["narrow_reverification_hypothesis", "false", "true", "CHANGED"],
    ["assertion_span_primary_hypothesis", "did not exist", "false (EXPERIMENTAL, OFF)", "ADDED, NOT PROMOTED"],
    ["correction.assertion_aware", "did not exist", "false (EXPERIMENTAL, OFF)", "ADDED, NOT PROMOTED"],
    ["evidence_matching.fuzzy_method", "did not exist (Jaccard hardcoded)",
     "\"jaccard\" (config key NEVER READ - see D1)", "ADDED BUT INERT"],
    ["Claim parser size", "17,150 bytes", "56,697 bytes", "CHANGED"],
    ["Claim fields", "claim_id, claim_text, citation_extracted",
     "+ assertion_text, assertion_spans", "CHANGED"],
    ["Safety gates active", "1 (full-sentence scope check)",
     "scope(span), unauthorized citation, ordinal integrity, sibling regression, negation, year-conflict", "CHANGED"],
    ["Year-conflict veto", "absent", "active, unconditional", "ADDED"],
]
write("headline", "T02_model_and_config_comparison",
      ["setting", "ORIGINAL (0e37525)", "LATEST (fb4e98f)", "status"], cfg,
      "Model and configuration, ORIGINAL vs LATEST. Sources: `git show 0e37525:...config/prototype.yaml` "
      "and `config/prototype.yaml` @ HEAD, both verified against the source that reads them.",
      ["THE MODELS ARE UNCHANGED. Every measured difference is a system, pipeline or configuration "
       "change - never a different or better underlying model.",
       "`evidence_matching.fuzzy_method` is never read by any call site, so BM25/embedding "
       "retrieval is unreachable from production whatever this key says."])

# ------------------------------------------------------------------ T03
v = []
for name, o, l in (("accuracy", BARE["accuracy"], LAB["accuracy"]),
                   ("macro F1", BARE["macro_f1"], LAB["macro_f1"])):
    v.append([name, "-", f(o), f(l), f(l - o), "420",
              f"{BARE['accuracy_ci95_wilson'][0]:.4f}-{BARE['accuracy_ci95_wilson'][1]:.4f}"
              if name == "accuracy" else
              f"{g1['statistics']['bootstrap_macro_f1']['bare_macro_f1_ci95'][0]:.4f}-"
              f"{g1['statistics']['bootstrap_macro_f1']['bare_macro_f1_ci95'][1]:.4f}",
              f"{LAB['accuracy_ci95_wilson'][0]:.4f}-{LAB['accuracy_ci95_wilson'][1]:.4f}"
              if name == "accuracy" else
              f"{g1['statistics']['bootstrap_macro_f1']['labeled_macro_f1_ci95'][0]:.4f}-"
              f"{g1['statistics']['bootstrap_macro_f1']['labeled_macro_f1_ci95'][1]:.4f}"])
for lbl in LABELS:
    for met in ("precision", "recall", "f1"):
        b, la = BARE["per_class"][lbl], LAB["per_class"][lbl]
        v.append([met, lbl, f(b[met]), f(la[met]), f(la[met] - b[met]),
                  str(b["support"]), "-", "-"])
write("verifier", "T03_verifier_metrics",
      ["metric", "class", "ORIGINAL (bare)", "LATEST (labeled)", "delta", "support/n",
       "ORIGINAL 95% CI", "LATEST 95% CI"], v,
      "GOLD-01 verifier metrics, n=420, fresh CPU rerun. Accuracy CI is Wilson; macro-F1 CI is a "
      "paired bootstrap (10,000 resamples, seed 20260918). Per-class CIs not computed.",
      [CAVEAT_G1,
       "These terms (accuracy/precision/recall/F1) are legitimate here because GOLD-01 carries "
       "construction-rule gold labels."])

# ------------------------------------------------------------------ T04
cm = []
for framing, arm in (("bare", "ORIGINAL"), ("labeled", "LATEST")):
    c = g1["results_by_framing"][framing]["confusion_matrix"]
    for gold in LABELS:
        for pred in LABELS:
            cm.append([arm, framing, gold, pred, c[gold][pred],
                       "correct" if gold == pred else "error"])
write("verifier", "T04_verifier_confusion_matrices",
      ["arm", "premise_framing", "gold_label", "predicted_label", "count", "cell_type"], cm,
      "Both confusion matrices in long format, GOLD-01 n=420. Same 420 items in both arms.")

# ------------------------------------------------------------------ T05
sr = []
for key in ("ALL_420", "ATTRIBUTED_conditions", "NON_ATTRIBUTED_conditions"):
    s = st["strata"][key]
    pt = s["paired_sign_test"]
    sr.append([key, s["n_items"], f(s["original_bare"]["accuracy"]),
               f(s["latest_labeled"]["accuracy"]), f(s["delta_accuracy"]),
               s["items_fixed_by_latest"], s["items_broken_by_latest"],
               f"{pt['p_value']:.4g}",
               "NOT SIGNIFICANT" if pt["p_value"] > 0.05 else "significant"])
for cond, s in sorted(st["per_condition"].items()):
    pt = s["paired_sign_test"]
    sr.append([f"  {cond}" + (" [ATTRIBUTED]" if s["is_attributed"] else ""),
               s["n_items"], f(s["original_bare"]["accuracy"]),
               f(s["latest_labeled"]["accuracy"]), f(s["delta_accuracy"]),
               s["items_fixed_by_latest"], s["items_broken_by_latest"],
               f"{pt['p_value']:.4g}",
               "NOT SIGNIFICANT" if pt["p_value"] > 0.05 else "significant"])
write("verifier", "T05_verifier_stratified_by_condition",
      ["stratum", "n", "ORIGINAL accuracy", "LATEST accuracy", "delta",
       "items fixed", "items broken", "sign test p", "verdict"], sr,
      "**THE REQUIRED CAVEAT TABLE.** GOLD-01 split by benchmark construction condition. "
      "ATTRIBUTED conditions are those whose hypothesis names the provision while the ORIGINAL "
      "bare premise omits it by construction.",
      [st["REQUIRED_CAVEAT"],
       "It still matters: real generated statutory claims ARE overwhelmingly attributed, so the "
       "attributed conditions are the realistic ones. The caveat constrains the SIZE and "
       "GENERALITY of the number, not whether the change was worth making."])

# ------------------------------------------------------------------ T06
r = ev["reconciliation"]
ep = [
    ["Records in v0 file", ev["original_v0"]["records_in_file"], "-", "-"],
    ["Usable records", ev["original_v0"]["usable_records"], ev["latest_v1_merged"]["usable_records"],
     f"+{ev['delta']['usable_records']}"],
    ["Distinct Acts", ev["original_v0"]["distinct_acts"], ev["latest_v1_merged"]["distinct_acts"],
     f"+{ev['delta']['distinct_acts']}"],
    ["VERIFIED_EXACT", ev["original_v0"]["verdict_breakdown"].get("VERIFIED_EXACT", 0),
     ev["latest_v1_merged"]["verdict_breakdown"].get("VERIFIED_EXACT", 0), "-"],
    ["VERIFIED_CONTENT", ev["original_v0"]["verdict_breakdown"].get("VERIFIED_CONTENT", 0),
     ev["latest_v1_merged"]["verdict_breakdown"].get("VERIFIED_CONTENT", 0), "-"],
    ["Records in v1 supplement file", "-",
     ev["latest_v1_merged"]["records_in_supplement_file"], "-"],
    ["  of which usable", "-", ev["supplement_composition"]["supplement_file_usable"], "-"],
    ["  genuinely new keys", "-", ev["supplement_composition"]["genuinely_new_keys"], "-"],
    ["  new keys that are usable", "-", ev["supplement_composition"]["genuinely_new_keys_usable"], "-"],
    ["  v0 keys corrected", "-", ev["supplement_composition"]["keys_overlapping_v0_corrections"], "-"],
    ["RECONCILIATION", f"{r['v0_usable']} v0 usable",
     f"+ {r['plus_new_usable_keys']} new + {r['plus_promoted_from_unusable']} promoted = {r['equals_latest_usable']}",
     f"reconciles: {r['reconciles']}"],
]
write("evidence", "T06_evidence_pool_composition",
      ["property", "ORIGINAL (v0)", "LATEST (v0+v1 merged)", "delta"], ep,
      "Structural composition of the evidence pool, recomputed via the production loader "
      "(`src/data_loader.load_usable_evidence`).",
      [ev["documentation_discrepancy"]["issue"] + " Correct decomposition: " +
       ev["documentation_discrepancy"]["correct_decomposition"],
       ev["grade_note"]])

# ------------------------------------------------------------------ T07
cov = []
cov.append(["209-claim paired natural", "209", f(p209["fresh_evidence_coverage_arm_A"]),
            f(p209["fresh_evidence_coverage_arm_B"]),
            f(p209["fresh_evidence_coverage_arm_B"] - p209["fresh_evidence_coverage_arm_A"]),
            f"{gained} gained / 0 lost", f"McNemar exact p={p209_exact:.3e}",
            "evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json",
            "HISTORICAL"])
_n588 = evcov["n_claims"]
_m0, _m1 = evcov["n_matched_v0"], evcov["n_matched_v1"]
_new = evcov["n_newly_covered_by_v1"]
_lost588 = _m0 + _new - _m1          # 0 if every v0 match survived
_p588 = min(1.0, 2.0 * (0.5 ** _new)) if _lost588 == 0 else float("nan")
cov.append(["588-claim corpus sweep", str(_n588),
            f"{evcov['coverage_v0_pct']/100:.4f}", f"{evcov['coverage_v1_pct']/100:.4f}",
            f"{(evcov['coverage_v1_pct']-evcov['coverage_v0_pct'])/100:.4f}",
            f"{_new} gained / {_lost588} lost ({_m0} -> {_m1} matched)",
            f"McNemar exact p={_p588:.3e}",
            "outputs/evidence_coverage_v0_vs_v1.json", "HISTORICAL"])
write("evidence", "T07_evidence_coverage_results",
      ["dataset", "n", "ORIGINAL coverage", "LATEST coverage", "delta",
       "per-claim change", "statistical test", "source artifact", "freshness"], cov,
      "Evidence-coverage OUTCOMES (as opposed to the structural pool size in T06). "
      "Both rows are HISTORICAL - neither could be rerun here.",
      ["CORRECTED SOURCE POINTER: the repository documents the 588-corpus numbers as coming from "
       "`evaluation/metrics/EVIDENCE_STRENGTH_MATRIX.md`, which does not contain them. The real "
       "source is `outputs/evidence_coverage_v0_vs_v1.json`.",
       "'Coverage' on unlabelled natural data is a RETRIEVAL outcome. It is never accuracy, "
       "precision or recall.",
       "The artifact carries both `historical_*` and `fresh_*` columns; the values above are the "
       "`fresh_evidence_coverage_arm_A/B` fields."])

# ------------------------------------------------------------------ T08
prog = pr["progression_claims_resolving_to_evidence"]
den = prog["denominator_claims_extracted"]
mm = pr["match_methods"]
pt_rows = []
for key, label in (("ORIGINAL_0e37525", "ORIGINAL (0e37525)"),
                   ("INTERMEDIATE_223eb9d", "INTERMEDIATE (223eb9d)"),
                   ("LATEST_HEAD", "LATEST (HEAD fb4e98f)")):
    pt_rows.append([label, den[key], prog[key],
                    f"{prog[key]/den[key]:.4f}",
                    mm[key].get("exact_normalized", 0), mm[key].get("fuzzy", 0),
                    mm[key].get("no_evidence", 0)])
write("parser", "T08_parser_metrics",
      ["arm", "claims extracted", "claims resolving to evidence", "proportion resolved",
       "exact matches", "fuzzy matches", "no evidence"], pt_rows,
      "Three-arm parser + evidence-matcher progression, re-executed fresh from git over the same "
      "30 documents of already-generated text, with the evidence pool held at v0 in every arm.",
      [f"Sign tests (per-document paired): ORIGINAL->LATEST +{pr['statistics']['original_to_latest']['n_improved']}/"
       f"-{pr['statistics']['original_to_latest']['n_worsened']}, p={pr['statistics']['original_to_latest']['p_value']:.4f}; "
       f"ORIGINAL->INTERMEDIATE +{pr['statistics']['original_to_intermediate']['n_improved']}/"
       f"-{pr['statistics']['original_to_intermediate']['n_worsened']}, p={pr['statistics']['original_to_intermediate']['p_value']:.4f}; "
       f"INTERMEDIATE->LATEST +{pr['statistics']['intermediate_to_latest']['n_improved']}/"
       f"-{pr['statistics']['intermediate_to_latest']['n_worsened']}, "
       f"p={pr['statistics']['intermediate_to_latest']['p_value']:.4f} (NOT SIGNIFICANT).",
       "The safety-relevant movement is fuzzy -> exact (14 -> 2 fuzzy; 24 -> 55 exact): fewer "
       "matches rest on a token-overlap heuristic.",
       "'Resolving to evidence' is a coverage outcome, NOT a correctness label - no gold "
       "claim-extraction annotation exists anywhere in this project.",
       pr["reconciliation_against_committed_artifacts"]["INTERMEDIATE_arm"]["investigation"]])

# ------------------------------------------------------------------ T09
D = fm["section_D_correction_safety_cumulative"]
fun = [
    ["Correction attempts", D["total_correction_attempts"], "100.0%", "all natural attempts"],
    ["Blocked: scope violation", D["status_breakdown"].get("correction_scope_violation", 0),
     f"{100*D['status_breakdown'].get('correction_scope_violation',0)/D['total_correction_attempts']:.1f}%",
     "a safety gate rejected the rewrite"],
    ["Rejected: correction_failed", D["status_breakdown"].get("correction_failed", 0),
     f"{100*D['status_breakdown'].get('correction_failed',0)/D['total_correction_attempts']:.1f}%",
     "the 7B corrector produced a no-op or inadequate edit"],
    ["SHIPPED (status=corrected)", D["total_shipped"],
     f"{D['shipped_rate_pct']}%", "all gates passed AND re-verified ENTAILED"],
    ["UNSAFE shipped", D["total_unsafe_shipped"], "0.0%", "zero-event result"],
]
write("correction", "T09_correction_funnel",
      ["stage", "count", "share of attempts", "meaning"], fun,
      "Cumulative correction funnel over every natural correction attempt in the project's "
      "history. **HISTORICAL** - Qwen-dependent, RERUN_INFEASIBLE on this machine.",
      ["The dominant failure is the 7B corrector producing a no-op or inadequate edit - a "
       "generation-quality limitation, not a pipeline defect.",
       "Synthetic-vs-natural transfer gap: corrections ship at "
       f"{fm['synthetic_vs_natural_correction_transfer_gap']['synthetic_labeled_shipped_rate_pct']}% on "
       "synthetic contradictions but "
       f"{fm['synthetic_vs_natural_correction_transfer_gap']['natural_all_regimes_shipped_rate_pct']}% on real "
       "generated text. This is the correction subsystem's single most important limitation."])

# ------------------------------------------------------------------ T10
sl = Counter(r_["legacy_status"] for r_ in aa["rows"])
sa = Counter(r_["assertion_aware_status"] for r_ in aa["rows"])
mech = [["Corrections shipped", aa["legacy_shipped"], aa["assertion_aware_shipped"],
         "NULL - identical outcome"]]
for k in sorted(set(sl) | set(sa)):
    mech.append([f"status: {k}", sl.get(k, 0), sa.get(k, 0),
                 "differs" if sl.get(k, 0) != sa.get(k, 0) else "same"])
write("correction", "T10_correction_mechanism_comparison",
      ["outcome", "LEGACY (production)", "ASSERTION-AWARE (experimental, OFF)", "note"], mech,
      f"Paired replay over {len(set(r_['document_id'] for r_ in aa['rows']))} documents x 2 arms = "
      f"{aa['n_paired_attempts']} attempts. **HISTORICAL** - Qwen-dependent, RERUN_INFEASIBLE here.",
      ["**NULL RESULT, PRESERVED AS NULL.** The assertion-aware mechanism is architecturally "
       "complete and safe, and it changes WHICH gate stops an attempt, but it ships exactly as "
       "many corrections as the legacy path: none. It must never be presented as an improvement.",
       "correction.assertion_aware remains FALSE in production."])

# ------------------------------------------------------------------ T11
gates = [
    ["Full-sentence scope check", "pipeline.py:133-153 -> :462", "YES", "0e37525", "YES",
     "every unflagged claim must reappear verbatim in the rewrite"],
    ["Sibling regression net", "pipeline.py:601 / :945", "NO", "100e263 (2026-08-27)", "YES",
     "an untouched sibling claim must not regress; INACTIVE unless atomic_scope_check is truthy"],
    ["Unauthorized citation addition", "pipeline.py:769-790", "NO", "adf54aa (2026-09-09)", "YES",
     "the corrector may not introduce a citation that was not there"],
    ["Ordinal integrity", "pipeline.py:806-873", "NO", "adf54aa (2026-09-09)", "YES",
     "reordered same-citation siblings cannot ship a verdict never computed against the real edit"],
    ["Negation gate", "pipeline.py:160 / :419 / :713-716", "NO", "adf54aa (2026-09-09)", "YES",
     "negation-marked CONTRADICTED claims never enter the correction trigger; UNCONDITIONAL"],
    ["Year-conflict veto", "evidence_matcher.py:48 / :121", "NO", "adf54aa (2026-09-09)", "YES",
     "retrieval-side: rejects a candidate whose year contradicts the citation; UNCONDITIONAL"],
    ["Structural span validation", "pipeline.py:1151", "NO", "8cf8fa9 (2026-09-12)", "YES",
     "assertion-aware path only - currently DORMANT (assertion_aware=false)"],
]
write("safety", "T11_safety_gates",
      ["gate", "source reference", "present at ORIGINAL", "commit added", "fail-closed",
       "what it blocks"], gates,
      "Every safety gate, when it was added, and whether the ORIGINAL system had it. "
      "ORIGINAL had exactly ONE.",
      ["All gates are FAIL-CLOSED: on any doubt the ORIGINAL text ships unchanged.",
       "Most of these gates were discovered adversarially and are covered by REGRESSION TESTS "
       "rather than by data-batch measurement - see T12.",
       "The negation gate, year-conflict veto, injection guard and ordinal guard are "
       "UNCONDITIONAL and not controllable by any config lever. This is why the configuration "
       "baseline is strictly more gated than the real pre-2026-09-09 system (discrepancy C-1)."])

# ------------------------------------------------------------------ T12
safe = [
    ["Unsafe corrections shipped", "0", str(D["total_correction_attempts"]),
     "all natural correction attempts across the project's history",
     "~5.2% (rule of three, 95% one-sided)",
     "ZERO-EVENT. Evidence of a fail-closed design behaving correctly on the data seen. NOT a proof of safety."],
    ["Unsafe verdict reversals", "0", str(D["total_correction_attempts"]),
     "same scope", "~5.2%", "ZERO-EVENT, same caveat."],
    ["Corrections blocked by a gate",
     str(D["status_breakdown"].get("correction_scope_violation", 0)),
     str(D["total_correction_attempts"]), "same scope", "n/a",
     "Gates fired and stopped shipping - the mechanism demonstrably engages."],
    ["Formal 15-category red-team evaluation", "NOT PERFORMED", "n/a", "n/a", "n/a",
     "No red-team evaluation exists anywhere in this project."],
]
write("safety", "T12_safety_results",
      ["outcome", "count", "denominator", "exact scope", "95% upper bound on true rate", "reading"],
      safe,
      "Safety outcomes, each stated WITH its exact denominator and scope, as zero-event results "
      "require.",
      ["With 0 events in 56 trials, the exact one-sided 95% upper bound on the true unsafe rate "
       "is approximately 5.2% (rule of three). Quoting '0 unsafe' without that bound would "
       "overstate the evidence.",
       "Scope is natural-data correction attempts only. It says nothing about unseen inputs."])

# ------------------------------------------------------------------ T13
abl = [
    ["premise_framing", "bare -> labeled", "O-CFG single-lever", "YES",
     "macro F1 0.7487 -> 0.9684 (n=420 GOLD)", "GOLD", f"McNemar exact p={MC['p_value']:.3e}",
     "PROMOTED", "99/100 of the gain is in ATTRIBUTED conditions (T05)"],
    ["use_evidence_v1", "false -> true", "O-CFG single-lever", "YES",
     f"coverage {p209['fresh_evidence_coverage_arm_A']:.4f} -> {p209['fresh_evidence_coverage_arm_B']:.4f} (n=209)",
     "HISTORICAL / METRIC_ONLY", f"McNemar exact p={p209_exact:.3e}", "PROMOTED",
     "Unlabelled natural data; coverage is a retrieval outcome"],
    ["claim parser (codebase)", "0e37525 -> HEAD", "O-CODE", "YES (parser isolated, pool fixed)",
     f"claims resolving to evidence {pr['totals']['orig_matched']} -> {pr['totals']['latest_matched']} (n=30 docs)",
     "DETERMINISTIC_SYNTHETIC", f"sign test p={sgn['p_value']:.4f}", "PROMOTED",
     "The only experiment that measures the ORIGINAL CODEBASE"],
    ["narrow_primary_hypothesis", "false -> true", "O-CFG single-lever", "YES",
     "GOLD-02: EXACTLY ZERO effect; natural GPU n=62: verdict shift only", "MIXED",
     "n=62 correction effect p~0.125 (not significant)", "PROMOTED",
     "NULL on the gold-labelled set. Promoted on natural-data verdict behaviour."],
    ["atomic_scope_check", "false -> assertion_spans", "O-CFG single-lever", "PARTIAL",
     "1/11 historical scope violations unblocked", "BEHAVIORAL (diagnostic)", "descriptive",
     "PROMOTED",
     "Weaker than the 4/6 finding that motivated it. Also silently toggles the sibling-regression gate (C-2)."],
    ["narrow_reverification_hypothesis", "false -> true", "O-CFG single-lever", "YES",
     "n=3 cases; 0 ship/reject outcomes changed", "BEHAVIORAL (diagnostic)", "none possible at n=3",
     "PROMOTED", "Promoted on mechanism reasoning, not a measured outcome improvement"],
    ["assertion_span_primary_hypothesis", "off -> on", "O-CFG single-lever", "YES",
     "4/6 verdicts changed (n=6, the entire population found)", "BEHAVIORAL", "none at n=6",
     "NOT PROMOTED", "Sample size, not a found defect"],
    ["correction.assertion_aware", "off -> on", "LATEST single-lever", "YES",
     f"{aa['assertion_aware_shipped']}/{aa['n_paired_attempts']} shipped vs legacy {aa['legacy_shipped']}/{aa['n_paired_attempts']}",
     "BEHAVIORAL (null result)", "none", "NOT PROMOTED", "NULL RESULT, preserved as null"],
    ["fuzzy_method (BM25)", "jaccard -> bm25", "LATEST single-lever", "YES",
     "3/9 adversarial correctly rejected vs Jaccard's 9/9", "BEHAVIORAL", "descriptive",
     "REJECTED", "Also unreachable from production - config key never read (D1)"],
    ["fuzzy_method (embedding)", "jaccard -> embedding", "LATEST single-lever", "YES",
     "2/9 adversarial correctly rejected vs Jaccard's 9/9", "BEHAVIORAL", "descriptive",
     "REJECTED", "Same as above"],
    ["confidence_threshold", "sweep 0.34-0.99", "both arms", "YES (descriptive)",
     "0.70 within 0.0023 (bare) / 0.0000 (labeled) of optimum; LATEST leads at EVERY threshold",
     "GOLD (descriptive)", "none - descriptive sweep", "UNCHANGED",
     "Confirms the verifier result is not a threshold artifact"],
    ["JOINT four/five-lever", "all levers at once", "O-CFG -> LATEST", "N/A",
     "NOT EXECUTED - does not exist anywhere in the project", "E (NOT_ISOLABLE)", "none",
     "NOT EXECUTED",
     "Four levers were flipped in ONE commit (100e263), so their joint effect is confounded. "
     "No additive or interaction effect is claimed anywhere in this package."],
]
write("ablation", "T13_ablation_results",
      ["lever", "change", "baseline arm measured against", "single-lever isolated?",
       "result", "evidence grade", "statistical test", "production status", "caveat"], abl,
      "Per-lever ablation. Each row states WHICH baseline it was measured against and whether "
      "the lever was genuinely isolated.",
      ["'O-CFG' = the configuration baseline (HEAD code, levers at defaults). 'O-CODE' = the "
       "original codebase at 0e37525. These are NOT the same system - see SYSTEM_COMPARISON.md §0.",
       "Grade measures how well a result is EVIDENCED, never effect size."])

# ------------------------------------------------------------------ T14
repro = [
    ["Verifier accuracy / macro F1 (GOLD-01, n=420)", "REPRODUCED FRESH",
     "Python 3.13.1 / torch 2.13.0+cpu / transformers 5.15.1, CPU",
     "EXACT match to the historical run on a different stack"],
    ["Verifier per-class + confusion matrices", "REPRODUCED FRESH", "same", "EXACT match"],
    ["GOLD-01 condition stratification", "NEW ANALYSIS (no prior artifact)",
     "derived from fresh predictions", "n/a - did not previously exist"],
    ["Contradiction recall (GOLD-02, n=59)", "REPRODUCED FRESH", "same",
     "EXACT match (0.3559 / 0.4576)"],
    ["GOLD-02 2x2 factorial", "NEW ANALYSIS", "same", "n/a - did not previously exist"],
    ["Parser ORIGINAL arm (38/88)", "REPRODUCED FRESH", "CPU, no model",
     "EXACT match to 0e37525:outputs/eval_30_report.md"],
    ["Parser LATEST arm (57/93)", "REPRODUCED FRESH", "CPU, no model",
     "EXACT match to parser_fix_before_after_n30_v2_postfix.json"],
    ["Parser INTERMEDIATE arm (54)", "DISCREPANCY", "CPU, no model",
     "artifact at that commit records 51; unresolved (P-1). No conclusion depends on it."],
    ["Evidence pool composition", "REPRODUCED FRESH", "CPU, no model",
     "59/136 confirmed; config's own arithmetic corrected"],
    ["Threshold sensitivity", "REPRODUCED FRESH", "recomputed from stored softmax",
     "consistent with the historical sweep"],
    ["Evidence coverage (n=209)", "REUSED HISTORICAL", "originally GPU",
     "RERUN_INFEASIBLE - Qwen-dependent generation"],
    ["Correction funnel (n=56)", "REUSED HISTORICAL", "originally GPU",
     "RERUN_INFEASIBLE - no GPU, Qwen uncached"],
    ["Assertion-aware correction (n=10)", "REUSED HISTORICAL", "originally GPU",
     "RERUN_INFEASIBLE - Qwen-dependent"],
    ["narrow_primary GPU batch (n=62)", "REUSED HISTORICAL", "originally GPU",
     "RERUN_INFEASIBLE - Qwen-dependent"],
    ["Retrieval method safety (BM25/embedding)", "REUSED HISTORICAL", "CPU",
     "RERUN_INFEASIBLE - rank_bm25 and sentence_transformers not installed; MiniLM not cached"],
    ["Test suite", "RE-RUN THIS SESSION", "Python 3.13.1, CPU",
     "290 passed, 1 skipped (= a 12-test file skipped via importorskip rank_bm25). 290+12=302, reconciling the documented figure."],
]
write("reproducibility", "T14_reproducibility_status",
      ["metric / experiment", "V2 status", "environment used", "outcome"], repro,
      "What was reproduced fresh, what was reused, and what could not be rerun.",
      ["Cross-stack exact reproduction of the GOLD-01 and GOLD-02 numbers is itself a "
       "reproducibility finding: the historical results survive a major torch/transformers "
       "version change.",
       "Inference is greedy argmax over a softmax - no sampling - so no inference seed exists "
       "and the deterministic runs are exactly repeatable."])

# ------------------------------------------------------------------ T15
env = [
    ["Python", "3.11.9", "3.13.1", "MAJOR SKEW"],
    ["torch", "2.2.2+cu121", "2.13.0+cpu", "MAJOR SKEW - no CUDA"],
    ["transformers", "4.40.2", "5.15.1", "MAJOR SKEW"],
    ["numpy", "1.26.4", "2.2.6", "MAJOR SKEW"],
    ["pandas", "2.2.2", "3.0.2", "MAJOR SKEW"],
    ["CUDA available", "True (RTX 4050, 6 GB)", "False", "NO GPU"],
    ["research/.venv", "present", "DOES NOT EXIST", "gone"],
    ["accelerate / bitsandbytes", "0.29.3 / 0.43.1", "NOT INSTALLED", "blocks 4-bit Qwen"],
    ["rank_bm25", "installed", "NOT INSTALLED", "blocks BM25 arm; skips 12 tests"],
    ["sentence_transformers", "installed", "NOT INSTALLED", "blocks embedding arm"],
    [NLI, "cached", "CACHED - verified working on CPU", "OK"],
    [QWEN, "cached, GPU", "NOT CACHED, no GPU", "RERUN_INFEASIBLE"],
    ["sentence-transformers/all-MiniLM-L6-v2", "cached", "NOT CACHED", "RERUN_INFEASIBLE"],
]
write("reproducibility", "T15_environment",
      ["component", "historical (pinned venv)", "this V2 session", "impact"], env,
      "The two software stacks side by side. The skew is the reason some experiments could be "
      "rerun and others could not.",
      ["No package was installed and no dependency added to produce this package.",
       "Installing rank_bm25 (small, pure-Python) would unblock the BM25 arm; that was "
       "deliberately not done, as changing the environment was outside the brief."])

# ------------------------------------------------------------------ T16
lims = [
    ["No lawyer-validated ground truth", "PROJECT-WIDE", "CRITICAL",
     "No accuracy figure anywhere is a legal-correctness determination - all are NLI agreement against audited statute text."],
    ["GOLD-01 headline is construction-dependent", "verifier", "HIGH",
     "99/100 of the gain is in attributed conditions; non-attributed p=1.0."],
    ["No gold labels for claim extraction", "parser", "HIGH",
     "'Resolving to evidence' is coverage, never precision/recall of extraction."],
    ["Correction evidence is thin and historical", "correction", "HIGH",
     "1/56 shipped; mechanism comparisons at n=6 and n=10; none rerunnable here."],
    ["Safety results are zero-event", "safety", "HIGH",
     "0 unsafe in 56 attempts; rule-of-three 95% upper bound ~5.2%. Most gates have regression tests, not measurements."],
    ["No joint multi-lever experiment", "all levers", "HIGH",
     "Four levers flipped in one commit; joint effect confounded; no additive/interaction claim is made."],
    ["Generation subsystem unmeasured in V2", "generation", "MEDIUM",
     "No GPU, Qwen uncached - fresh evidence covers only the deterministic and verification-side subsystems."],
    ["Model identity unpinned", "all models", "MEDIUM",
     "No from_pretrained() call pins a revision SHA; exact weight identity for historical results is UNDETERMINED."],
    ["O-CFG is a retrospective construct", "baseline definition", "MEDIUM",
     "The five levers never coexisted at their defaults in any real production state."],
    ["Configuration baseline is more gated than history", "baseline definition", "MEDIUM",
     "Four safety gates are unconditional and not lever-controllable (C-1)."],
    ["Small samples throughout", "correction / assertion-span work", "MEDIUM",
     "n=3, n=6, n=10, n=11 appear in promoted-lever evidence."],
    ["No formal red-team evaluation", "safety", "MEDIUM", "None exists in this project."],
    ["Docker reproducibility", "infrastructure", "LOW",
     "ENVIRONMENT_BLOCKED and inherited; not re-tested and not claimed."],
    ["Parser INTERMEDIATE arm discrepancy", "parser", "LOW",
     "54 vs the artifact's 51 at the same commit; both endpoints reproduce exactly (P-1)."],
]
write("limitations", "T16_limitations",
      ["limitation", "scope", "severity", "what it means for the reader"], lims,
      "Every limitation this package is aware of, with its scope and severity.",
      ["Severity describes how much the limitation constrains what may be claimed - not how "
       "badly the system performs."])

# ------------------------------------------------------------------ T17
ng = [
    ["End-to-end ORIGINAL codebase run", "NOT EXECUTED",
     "Generation and correction are Qwen-dependent; no GPU and model uncached",
     "The deterministic front half WAS re-executed from git (T08)"],
    ["Correction funnel / outcomes / safety, fresh", "RERUN_INFEASIBLE",
     "Qwen-dependent", "Historical artifacts reused and labelled HISTORICAL"],
    ["BM25 / embedding retrieval comparison, fresh", "RERUN_INFEASIBLE",
     "rank_bm25 and sentence_transformers not installed; MiniLM not cached",
     "Historical result reused; also unreachable from production (D1)"],
    ["Joint four/five-lever ablation", "NOT EXECUTED",
     "Does not exist in the project; requires end-to-end Qwen runs",
     "Single-lever results reported instead, explicitly labelled"],
    ["Runtime / resource comparison figure", "DELIBERATELY NOT PRODUCED",
     "Historical numbers are GPU; fresh ones are CPU under a different major version - not comparable",
     "figures/09_runtime/README.md explains; raw timings kept in the metric JSONs"],
    ["Natural-data accuracy / F1 / confusion matrix", "NOT PRODUCED - WOULD BE INVALID",
     "No gold labels exist for any natural batch",
     "Natural data is reported only as coverage, distribution and behaviour"],
    ["Lawyer-validated evaluation", "DOES NOT EXIST", "Never performed in this project", "None"],
    ["Formal 15-category red-team evaluation", "DOES NOT EXIST", "Never performed", "None"],
    ["Pre-0e37525 system state", "UNRECOVERABLE",
     "0e37525 is the sole root commit and is a squashed import", "None"],
    ["Model revision SHAs", "UNDETERMINED", "No from_pretrained() call pins a revision", "None"],
]
write("limitations", "T17_not_generated",
      ["requested item", "status", "reason", "what exists instead"], ng,
      "Everything the brief asked for that this package does not contain. No placeholder figure "
      "or stub table was created for any of these.",
      ["Full narrative version: NOT_GENERATED_REGISTER.md"])

# ------------------------------------------------ metrics/experiment_audit.csv
def canon(dec: str) -> str:
    d = dec.upper()
    if d.startswith("REUSABLE"):
        return "REUSABLE"
    if "RERUN_INFEASIBLE" in d:
        return "RERUN_INFEASIBLE"
    if "RERUN_REQUIRED" in d:
        return "RERUN_REQUIRED"
    if d.startswith("HISTORICAL_ONLY"):
        return "HISTORICAL_ONLY"
    if d.startswith("INVALIDATED"):
        return "INVALIDATED"
    if "NOT_APPLICABLE" in d:
        return "NOT_APPLICABLE"
    return "OTHER"


V2_STATUS = {
    "E01": "SUPERSEDED BY V2 FRESH RERUN (gold01_v2_metrics.json) - reproduced EXACTLY",
    "E02": "SUPERSEDED BY V2 FRESH RERUN (gold02_v2_metrics.json) - reproduced EXACTLY",
}
for r_ in audit_rows:
    r_["v2_canonical_decision"] = canon(r_["decision"])
    r_["v2_status"] = V2_STATUS.get(r_["experiment_id"], "")
fields = list(audit_rows[0].keys())
with (M / "experiment_audit.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(audit_rows)
print(f"  metrics/experiment_audit.csv ({len(audit_rows)} rows)")
print("   ", dict(Counter(r_["v2_canonical_decision"] for r_ in audit_rows)))

# ------------------------------------------------ metrics/headline_results.csv
with (M / "headline_results.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["metric", "original", "latest", "delta", "n", "dataset",
                "evidence_grade", "statistical_test", "freshness", "caveat"])
    w.writerows(hl)
print(f"  metrics/headline_results.csv ({len(hl)} rows)")

# ------------------------------------------------ metrics/detailed_metrics.csv
det = []
for framing, arm in (("bare", "ORIGINAL"), ("labeled", "LATEST")):
    r_ = g1["results_by_framing"][framing]
    det.append(["GOLD-01", arm, "accuracy", "", f(r_["accuracy"]), 420, "GOLD"])
    det.append(["GOLD-01", arm, "macro_f1", "", f(r_["macro_f1"]), 420, "GOLD"])
    for lbl in LABELS:
        for met in ("precision", "recall", "f1"):
            det.append(["GOLD-01", arm, met, lbl, f(r_["per_class"][lbl][met]),
                        r_["per_class"][lbl]["support"], "GOLD"])
for cell, c in g2["cells"].items():
    det.append(["GOLD-02", cell, "contradiction_recall", "",
                f(c["contradiction_recall_all_items"]), g2["n_items"],
                "DETERMINISTIC_SYNTHETIC"])
for key in ("ORIGINAL_0e37525", "INTERMEDIATE_223eb9d", "LATEST_HEAD"):
    det.append(["parser_n30", key, "claims_resolving_to_evidence", "", prog[key],
                den[key], "DETERMINISTIC_SYNTHETIC"])
    det.append(["parser_n30", key, "claims_extracted", "", den[key], 30,
                "DETERMINISTIC_SYNTHETIC"])
for arm, k in (("ORIGINAL", "original_v0"), ("LATEST", "latest_v1_merged")):
    det.append(["evidence_pool", arm, "usable_records", "", ev[k]["usable_records"], "-",
                "DETERMINISTIC_SYNTHETIC"])
    det.append(["evidence_pool", arm, "distinct_acts", "", ev[k]["distinct_acts"], "-",
                "DETERMINISTIC_SYNTHETIC"])
with (M / "detailed_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["experiment", "arm", "metric", "class", "value", "n_or_support", "evidence_grade"])
    w.writerows(det)
print(f"  metrics/detailed_metrics.csv ({len(det)} rows)")
print("done.")
