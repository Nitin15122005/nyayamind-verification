#!/usr/bin/env python3
"""
Builds the V2 package's traceability layer:

  validation/metric_traceability.csv   — one row per reported metric
  validation/figure_traceability.csv   — one row per figure
  validation/table_traceability.csv    — one row per table

Every metric row is READ OUT of a metric JSON in metrics/ — no value is typed in here.
If a metric cannot be sourced from a file, it does not get a row.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

_V2 = Path(__file__).resolve().parent.parent
M = _V2 / "metrics"
V = _V2 / "validation"
F = _V2 / "figures"
T = _V2 / "tables"

HEAD = "fb4e98fa6f62695dbac7ba6148ca20713347386d"
ORIG = "0e375250a107bd569c7cd641e50a7be3f9f59d26"
NLI = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"

FIELDS = [
    "metric_id", "metric_name", "arm", "value", "delta_vs_original",
    "dataset", "n", "labels", "metric_definition", "model", "config",
    "commit", "experiment", "source_artifact", "source_path",
    "evidence_grade", "statistical_test", "p_value", "confidence_interval",
    "caveat", "generation_script",
]

rows: list[dict] = []
_seq = {"n": 0}


def add(**kw):
    _seq["n"] += 1
    r = {f: "" for f in FIELDS}
    r["metric_id"] = f"M{_seq['n']:03d}"
    r.update(kw)
    rows.append(r)


def load(name):
    return json.loads((M / name).read_text(encoding="utf-8"))


def fmt(x, nd=6):
    if isinstance(x, float):
        return f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return str(x)


def ci(pair):
    if not pair:
        return ""
    return f"[{pair[0]:.4f}, {pair[1]:.4f}]"


# ---------------------------------------------------------------- GOLD-01
g1 = load("gold01_v2_metrics.json")
mc = g1["statistics"]["mcnemar_accuracy"]
boot = g1["statistics"]["bootstrap_macro_f1"]
G1_COMMON = dict(
    dataset="GOLD-01 controlled verifier benchmark",
    n=g1["n_items"],
    labels="GOLD (deterministic construction rule, never a model prediction)",
    model=NLI,
    commit=HEAD,
    experiment="Fresh CPU rerun, bare vs labeled premise framing (single lever)",
    source_artifact="gold01_v2_metrics.json",
    source_path="v2_outputs_phase_3_vedant/metrics/gold01_v2_metrics.json",
    evidence_grade="GOLD",
    generation_script="v2_outputs_phase_3_vedant/scripts/rerun_gold01_verifier_original_vs_latest.py",
    caveat=("SINGLE-LEVER ablation of verification.premise_framing. 99/100 of the fixed items lie "
            "in the ATTRIBUTED conditions - see M-stratified rows and gold01_v2_stratified_by_condition.json."),
)
for framing, arm in (("bare", "ORIGINAL"), ("labeled", "LATEST")):
    r = g1["results_by_framing"][framing]
    base = g1["results_by_framing"]["bare"]
    add(metric_name="Verifier accuracy", arm=arm, value=fmt(r["accuracy"]),
        delta_vs_original="" if arm == "ORIGINAL" else fmt(r["accuracy"] - base["accuracy"]),
        metric_definition="correct predictions / 420",
        config=f"premise_framing={framing}, confidence_threshold=0.70, max_sequence_length=512, device=cpu",
        statistical_test=mc["test"] if arm == "LATEST" else "",
        p_value=f"{mc['p_value']:.4e}" if arm == "LATEST" else "",
        confidence_interval=ci(r["accuracy_ci95_wilson"]) + " (Wilson)",
        **G1_COMMON)
    add(metric_name="Verifier macro F1", arm=arm, value=fmt(r["macro_f1"]),
        delta_vs_original="" if arm == "ORIGINAL" else fmt(r["macro_f1"] - base["macro_f1"]),
        metric_definition="unweighted mean of per-class F1 over ENTAILED/CONTRADICTED/NEI",
        config=f"premise_framing={framing}, confidence_threshold=0.70",
        statistical_test="paired bootstrap, 10000 resamples, seed 20260918" if arm == "LATEST" else "",
        p_value="",
        confidence_interval=ci(boot[f"{framing}_macro_f1_ci95"]) + " (bootstrap)",
        **G1_COMMON)
    for lbl in ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"):
        pc = r["per_class"][lbl]
        bpc = base["per_class"][lbl]
        for met in ("precision", "recall", "f1"):
            add(metric_name=f"Verifier {met} [{lbl}]", arm=arm, value=fmt(pc[met]),
                delta_vs_original="" if arm == "ORIGINAL" else fmt(pc[met] - bpc[met]),
                metric_definition=f"per-class {met}, support={pc['support']}",
                config=f"premise_framing={framing}",
                **G1_COMMON)

add(metric_name="Verifier items fixed by LATEST (discordant pairs)", arm="LATEST",
    value=str(mc["c_only_B_correct"]),
    metric_definition="items ORIGINAL got wrong and LATEST got right",
    statistical_test=mc["test"], p_value=f"{mc['p_value']:.4e}",
    config="premise_framing bare->labeled", **G1_COMMON)
add(metric_name="Verifier items broken by LATEST (discordant pairs)", arm="LATEST",
    value=str(mc["b_only_A_correct"]),
    metric_definition="items ORIGINAL got right and LATEST got wrong",
    statistical_test=mc["test"], p_value=f"{mc['p_value']:.4e}",
    config="premise_framing bare->labeled", **G1_COMMON)

# ------------------------------------------------- GOLD-01 stratification
st = load("gold01_v2_stratified_by_condition.json")
SC = dict(
    dataset="GOLD-01, stratified by construction condition",
    labels="GOLD", model=NLI, commit=HEAD,
    experiment="Condition stratification (no new inference; recomputed from stored predictions)",
    source_artifact="gold01_v2_stratified_by_condition.json",
    source_path="v2_outputs_phase_3_vedant/metrics/gold01_v2_stratified_by_condition.json",
    evidence_grade="GOLD",
    generation_script="v2_outputs_phase_3_vedant/scripts/stratify_gold01_by_condition.py",
)
for key, cav in (
    ("ATTRIBUTED_conditions",
     "Bare premise omits by construction the identifier the hypothesis asserts - the ORIGINAL arm cannot succeed here."),
    ("NON_ATTRIBUTED_conditions",
     "NOT SIGNIFICANT. Only 1 item changed. This is where the headline does NOT hold."),
):
    s = st["strata"][key]
    pt = s["paired_sign_test"]
    for arm, val in (("ORIGINAL", s["original_bare"]["accuracy"]),
                     ("LATEST", s["latest_labeled"]["accuracy"])):
        add(metric_name=f"Verifier accuracy [{key}]", arm=arm, value=fmt(val),
            delta_vs_original="" if arm == "ORIGINAL" else fmt(s["delta_accuracy"]),
            n=s["n_items"], metric_definition="correct predictions / stratum n",
            config="premise_framing=" + ("bare" if arm == "ORIGINAL" else "labeled"),
            statistical_test=pt["test"] if arm == "LATEST" else "",
            p_value=f"{pt['p_value']:.4g}" if arm == "LATEST" else "",
            caveat=cav, **SC)
ha = st["headline_attribution"]
add(metric_name="Share of GOLD-01 gain from ATTRIBUTED conditions", arm="LATEST",
    value=f"{ha['share_of_gain_from_attributed_conditions']:.4f}",
    n=420, metric_definition=f"{ha['of_which_in_attributed_conditions']}/{ha['total_items_fixed_by_latest']} fixed items",
    config="premise_framing bare->labeled",
    caveat="THE REQUIRED CAVEAT. Always quote the headline with this number.", **SC)

# ---------------------------------------------------------------- GOLD-02
g2 = load("gold02_v2_metrics.json")
G2 = dict(
    dataset="GOLD-02 synthetic contradiction stress set",
    n=g2["n_items"],
    labels="CONTRADICTED-by-construction for all items; re-derived and integrity-checked this run",
    model=NLI, commit=HEAD,
    experiment="Fresh CPU rerun, 2x2 factorial (premise_framing x narrow_primary_hypothesis)",
    source_artifact="gold02_v2_metrics.json",
    source_path="v2_outputs_phase_3_vedant/metrics/gold02_v2_metrics.json",
    evidence_grade="DETERMINISTIC_SYNTHETIC",
    generation_script="v2_outputs_phase_3_vedant/scripts/rerun_gold02_contradiction_original_vs_latest.py",
)
mc2 = g2["statistics"]["original_vs_latest_mcnemar"]
for cell, arm in (("ORIGINAL_config", "ORIGINAL"), ("LATEST_config", "LATEST"),
                  ("framing_only", "SINGLE-LEVER"), ("narrow_only", "SINGLE-LEVER")):
    c = g2["cells"][cell]
    o = g2["cells"]["ORIGINAL_config"]["contradiction_recall_all_items"]
    add(metric_name=f"Contradiction recall [{cell}]", arm=arm,
        value=fmt(c["contradiction_recall_all_items"]),
        delta_vs_original=fmt(c["contradiction_recall_all_items"] - o),
        metric_definition=f"CONTRADICTED verdicts / {g2['n_items']} items "
                          f"({c['n_no_evidence']} never reach the verifier: NO_EVIDENCE)",
        config=f"premise_framing={c['premise_framing']}, narrow_primary_hypothesis={c['narrow_primary_hypothesis']}",
        statistical_test=mc2["test"] if cell == "LATEST_config" else "",
        p_value=f"{mc2['p_value']:.4g}" if cell == "LATEST_config" else "",
        confidence_interval=ci(c["contradiction_recall_all_items_ci95"]) + " (Wilson)",
        caveat=("Single-class set: ONLY recall is defined; accuracy/macro F1 would be degenerate. "
                "Synthetic - probes detection, not real-world legal accuracy. "
                "NULL RESULT: narrow_primary_hypothesis changes nothing on this set."),
        **G2)

# ---------------------------------------------------------------- Parser
pr = load("parser_original_vs_latest_v2.json")
PRC = dict(
    dataset="30 real NyayaRAG documents (already-generated Qwen text, outputs/run_A_n30.jsonl)",
    n="30 documents / 88-93 claims",
    labels="NONE - no gold claim-extraction annotation exists",
    model="none (deterministic regex + lexical matching)",
    experiment="Fresh 3-arm re-execution of committed parser/matcher/loader from git",
    source_artifact="parser_original_vs_latest_v2.json",
    source_path="v2_outputs_phase_3_vedant/metrics/parser_original_vs_latest_v2.json",
    evidence_grade="DETERMINISTIC_SYNTHETIC",
    generation_script="v2_outputs_phase_3_vedant/scripts/rerun_parser_original_vs_latest.py",
    caveat=("'Resolving to evidence' is a retrieval/coverage outcome, NOT a correctness label. "
            "Evidence pool held at v0 in all arms to isolate the parser."),
)
prog = pr["progression_claims_resolving_to_evidence"]
sts = pr["statistics"]
arm_commit = {"ORIGINAL_0e37525": ORIG, "INTERMEDIATE_223eb9d": "223eb9d", "LATEST_HEAD": HEAD}
for key, arm in (("ORIGINAL_0e37525", "ORIGINAL"), ("INTERMEDIATE_223eb9d", "INTERMEDIATE"),
                 ("LATEST_HEAD", "LATEST")):
    add(metric_name="Claims resolving to evidence", arm=arm, value=str(prog[key]),
        delta_vs_original="" if arm == "ORIGINAL" else str(prog[key] - prog["ORIGINAL_0e37525"]),
        metric_definition="extracted citations that matched an audited evidence record",
        config="v0 evidence pool (59 records), fuzzy_token_overlap_threshold=0.8",
        commit=arm_commit[key],
        statistical_test=sts["original_to_latest"]["test"] if arm == "LATEST" else "",
        p_value=f"{sts['original_to_latest']['p_value']:.4g}" if arm == "LATEST" else "",
        **PRC)
    add(metric_name="Claims extracted", arm=arm,
        value=str(prog["denominator_claims_extracted"][key]),
        metric_definition="total Claim objects produced by the parser",
        config="v0 evidence pool", commit=arm_commit[key], **PRC)
for name, key in (("ORIGINAL->LATEST", "original_to_latest"),
                  ("ORIGINAL->INTERMEDIATE", "original_to_intermediate"),
                  ("INTERMEDIATE->LATEST", "intermediate_to_latest")):
    s = sts[key]
    add(metric_name=f"Documents improved / worsened [{name}]", arm="COMPARISON",
        value=f"+{s['n_improved']} / -{s['n_worsened']} (unchanged {s['unchanged']})",
        metric_definition="per-document paired change in claims resolving to evidence",
        config="v0 evidence pool", commit=HEAD,
        statistical_test=s["test"], p_value=f"{s['p_value']:.4g}",
        caveat=("NOT SIGNIFICANT at n=30." if s["p_value"] > 0.05 else PRC["caveat"]),
        **{k: v for k, v in PRC.items() if k != "caveat"})

# -------------------------------------------------------- Evidence pool
ev = load("evidence_pool_composition_v2.json")
EVC = dict(
    dataset="canonical_statutes.jsonl (+ _v1 supplement), audited",
    labels="audit verdicts VERIFIED_EXACT / VERIFIED_CONTENT",
    model="none", commit=HEAD,
    experiment="Structural recount via the production loader",
    source_artifact="evidence_pool_composition_v2.json",
    source_path="v2_outputs_phase_3_vedant/metrics/evidence_pool_composition_v2.json",
    evidence_grade="DETERMINISTIC_SYNTHETIC",
    generation_script="v2_outputs_phase_3_vedant/scripts/compute_evidence_pool_composition.py",
    caveat=("An INPUT property of the system, not a retrieval outcome. Not an accuracy, "
            "precision, recall or coverage measurement."),
)
for field, label in (("usable_records", "Usable evidence records"),
                     ("distinct_acts", "Distinct Acts covered")):
    o = ev["original_v0"][field]
    l = ev["latest_v1_merged"][field]
    add(metric_name=label, arm="ORIGINAL", value=str(o), n=str(o),
        metric_definition="records passing the audit-verdict filter", config="use_evidence_v1=false", **EVC)
    add(metric_name=label, arm="LATEST", value=str(l), delta_vs_original=f"+{l-o}", n=str(l),
        metric_definition="records passing the audit-verdict filter", config="use_evidence_v1=true", **EVC)

# ------------------------------------------------ Threshold sensitivity
ts = load("threshold_sensitivity_v2.json")
TSC = dict(
    dataset="GOLD-01 stored softmax distributions", n=420, labels="GOLD",
    model=NLI, commit=HEAD,
    experiment="Threshold sweep 0.34-0.99 (no new inference)",
    source_artifact="threshold_sensitivity_v2.json",
    source_path="v2_outputs_phase_3_vedant/metrics/threshold_sensitivity_v2.json",
    evidence_grade="GOLD",
    generation_script="v2_outputs_phase_3_vedant/scripts/compute_threshold_sensitivity_v2.py",
    statistical_test="", p_value="",
    caveat="Descriptive sensitivity analysis. No significance test is attached to a threshold sweep.",
)
for framing, arm in (("bare", "ORIGINAL"), ("labeled", "LATEST")):
    d = ts["by_framing"][framing]
    add(metric_name="Macro F1 gap to own threshold optimum", arm=arm,
        value=fmt(d["gap_to_optimum_macro_f1"]),
        metric_definition=f"best macro F1 ({d['best']['macro_f1']:.4f} @ {d['best']['threshold']}) minus value at 0.70",
        config=f"premise_framing={framing}", **TSC)
fg = ts["framing_gap"]
add(metric_name="Minimum LATEST-minus-ORIGINAL macro F1 gap across all thresholds", arm="COMPARISON",
    value=fmt(fg["min_gap"]),
    metric_definition=f"smallest advantage at any threshold (at {fg['min_gap_at_threshold']}); "
                      f"LATEST leads at every threshold = {fg['labeled_beats_bare_at_every_threshold']}",
    config="sweep 0.34-0.99", **TSC)

# ------------------------------------------------------------ write out
V.mkdir(parents=True, exist_ok=True)
with (V / "metric_traceability.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
print(f"metric_traceability.csv: {len(rows)} metric rows")

# figures
fig_rows = []
for prov_file in (F / "figure_provenance_core.json", F / "figure_provenance_historical.json"):
    if not prov_file.exists():
        continue
    for p in json.loads(prov_file.read_text(encoding="utf-8")):
        fig_rows.append({
            "figure_id": Path(p["figure"]).stem,
            "figure_path": p["figure"],
            "source_artifact": p["source_artifact"],
            "fields_used": p["fields_used"],
            "evidence_grade": p["evidence_grade"],
            "n": p["n"],
            "caveat": p["caveat"],
            "generation_script": p["generated_by"],
        })
dgi = _V2 / "diagrams" / "diagram_index.json"
if dgi.exists():
    for d in json.loads(dgi.read_text(encoding="utf-8")):
        fig_rows.append({
            "figure_id": Path(d.get("diagram_file", "")).stem,
            "figure_path": d.get("diagram_file", ""),
            "source_artifact": d.get("source_of_truth", ""),
            "fields_used": d.get("what_it_shows", ""),
            "evidence_grade": "STRUCTURAL (architecture diagram, no metrics)",
            "n": "n/a",
            "caveat": f"arm: {d.get('original_or_latest_or_both','')}",
            "generation_script": "v2_outputs_phase_3_vedant/scripts/build_v2_diagrams.py",
        })
ffields = ["figure_id", "figure_path", "source_artifact", "fields_used",
           "evidence_grade", "n", "caveat", "generation_script"]
with (V / "figure_traceability.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=ffields)
    w.writeheader()
    w.writerows(fig_rows)
print(f"figure_traceability.csv: {len(fig_rows)} rows")

# tables
tab_rows = []
for csvf in sorted(T.rglob("*.csv")):
    rel = csvf.relative_to(_V2).as_posix()
    with csvf.open(encoding="utf-8") as fh:
        n_lines = sum(1 for _ in fh)
    tab_rows.append({
        "table_id": csvf.stem,
        "table_path": rel,
        "markdown_twin": rel[:-4] + ".md" if (csvf.with_suffix(".md")).exists() else "MISSING",
        "n_data_rows": max(0, n_lines - 1),
        "generation_script": "v2_outputs_phase_3_vedant/scripts/ (table workstream)",
    })
tfields = ["table_id", "table_path", "markdown_twin", "n_data_rows", "generation_script"]
with (V / "table_traceability.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=tfields)
    w.writeheader()
    w.writerows(tab_rows)
print(f"table_traceability.csv: {len(tab_rows)} rows")
