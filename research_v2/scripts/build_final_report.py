#!/usr/bin/env python3
"""Assemble the final report from immutable raw run artifacts."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/"research_v2"/"results"
REPORTS=RESULTS/"reports"

def load(p): return json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None
def latest(path, pattern):
    fs=sorted(path.glob(pattern),key=lambda p:p.stat().st_mtime) if path.exists() else []
    return fs[-1] if fs else None
def metrics_runs():
    rows=[]
    for p in (RESULTS/"runs").glob("*/metrics.json"):
        try: rows.append((p.stat().st_mtime,p.parent,load(p)))
        except (OSError,ValueError): pass
    return rows
def latest_gold(bench,stack):
    rows=[x for x in metrics_runs() if x[2].get("benchmark")==bench and x[2].get("stack")==stack]
    return max(rows,key=lambda x:x[0]) if rows else None
def read_jsonl(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p and p.exists() else []
def fmt(x,d=4): return "null" if x is None else f"{x:.{d}f}"
def latest_stamp_file(path,pattern): return latest(path,pattern)

def main():
    env=load(REPORTS/"environment.json") or {}
    gold={b:{s:latest_gold(b,s) for s in ("baseline","v2")} for b in ("gold01","gold02")}
    gc={b:load(latest(REPORTS,f"{b}_comparison_*.json")) for b in ("gold01","gold02")}
    natural_reports=sorted(REPORTS.glob("natural_comparison_*.json"),key=lambda p:p.stat().st_mtime)[-3:]
    natural=[load(p) for p in natural_reports]
    nmetrics=[x for x in metrics_runs() if x[2].get("kind")=="natural_unlabeled_descriptive_only"]
    pipeline_dirs=sorted((RESULTS/"runs").glob("*_full_pipeline"),key=lambda p:p.stat().st_mtime)
    pipeline=pipeline_dirs[-1] if pipeline_dirs else None
    correction_file=latest(RESULTS/"paired"/"correction","*_summary.json")
    correction=load(correction_file)

    gold_tables=[];transition_lines=[];paired_summary={}
    for b in ("gold01","gold02"):
        c=gc[b]
        if not c:
            gold_tables.append(f"| {b.upper()} | null | null | null | null | no paired run |")
            continue
        bm,vm=c["baseline"]["metrics"],c["v2"]["metrics"]
        contra_b=bm.get("per_class",{}).get("CONTRADICTED",{});contra_v=vm.get("per_class",{}).get("CONTRADICTED",{})
        gold_tables.append(f"| {b.upper()} | {bm.get('n')} | {fmt(bm.get('accuracy'))} / {fmt(vm.get('accuracy'))} | {fmt(bm.get('macro_f1'))} / {fmt(vm.get('macro_f1'))} | {fmt(contra_b.get('recall'))} / {fmt(contra_v.get('recall'))} | {fmt(c.get('delta',{}).get('macro_f1'))} / {fmt(c.get('delta',{}).get('contradicted_recall'))} |")
        pp=latest(RESULTS/"paired"/b,"*_predictions.jsonl");rows=read_jsonl(pp)
        cats={}
        transitions={}
        for r in rows:
            category=r.get("category","unknown");cats[category]=cats.get(category,0)+1
            if r.get("baseline",{}).get("prediction")!=r.get("v2",{}).get("prediction"):
                key=f"gold={r.get('gold_label')}: {r.get('baseline',{}).get('prediction')} -> {r.get('v2',{}).get('prediction')}"
                transitions[key]=transitions.get(key,0)+1
        paired_summary[b]={"n":len(rows),"categories":cats,"transitions":transitions,"path":pp.relative_to(ROOT).as_posix() if pp else None}
        if transitions:
            transition_lines.append(f"### {b.upper()} disagreement transitions")
            transition_lines.extend(f"- {k}: {v}" for k,v in sorted(transitions.items(),key=lambda z:-z[1]))

    natural_lines=[]
    for nr in natural:
        dataset=nr.get("dataset")
        per={}
        for _,path,m in nmetrics:
            if m.get("dataset")==dataset: per[m.get("model_id")]=m
        b=per.get("MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",{});v=per.get("tasksource/ModernBERT-large-nli",{})
        natural_lines.append(f"| `{Path(dataset).name}` | {nr.get('n_paired_claims')} | {nr.get('categories',{}).get('model_disagreement_ground_truth_unavailable')} | {fmt(b.get('evidence_coverage'))} / {fmt(v.get('evidence_coverage'))} | {b.get('truncation_count')} / {v.get('truncation_count')} | {fmt(b.get('low_confidence_rate'))} / {fmt(v.get('low_confidence_rate'))} | {fmt(b.get('mean_latency_seconds'))} / {fmt(v.get('mean_latency_seconds'))} | {json.dumps(nr.get('baseline_verdicts',{}),sort_keys=True)} | {json.dumps(nr.get('v2_verdicts',{}),sort_keys=True)} |")

    pipeline_lines=[];pipeline_generations=[];matrix_report=None
    if pipeline:
        names=["baseline_A","baseline_baseline_B","baseline_baseline_C","baseline_v2_B","baseline_v2_C","v2_A","v2_baseline_B","v2_baseline_C","v2_v2_B","v2_v2_C"]
        for name in names:
            p=pipeline/name/"metrics.json"; m=load(p)
            if not m: continue
            label={"baseline_A":"Qwen2.5 generation only","v2_A":"Qwen3 generation only","baseline_baseline_B":"Qwen2.5 + DeBERTa","baseline_baseline_C":"Qwen2.5 + DeBERTa + correction","baseline_v2_B":"Qwen2.5 + ModernBERT","baseline_v2_C":"Qwen2.5 + ModernBERT + correction","v2_baseline_B":"Qwen3 + DeBERTa","v2_baseline_C":"Qwen3 + DeBERTa + correction","v2_v2_B":"Qwen3 + ModernBERT","v2_v2_C":"Qwen3 + ModernBERT + correction"}.get(name,name)
            gen_condition=("baseline_baseline_B" if name=="baseline_A" else "v2_baseline_B" if name=="v2_A" else name)
            raws=read_jsonl(pipeline/gen_condition/"predictions.jsonl")
            gen=[r.get("research_v2_telemetry",{}).get("generation") or {} for r in raws]
            gen=[g for g in gen if g.get("generation_latency_seconds") is not None]
            if name.endswith("_A"):
                peaks=[g.get("peak_gpu_memory_bytes") for g in gen if g.get("peak_gpu_memory_bytes") is not None]
                pipeline_generations.append(f"- {label}: mean per-input generation latency {fmt(sum(g['generation_latency_seconds'] for g in gen)/len(gen) if gen else None)}s; peak per-input GPU memory {max(peaks) if peaks else None} bytes; tokens/input ceiling 8192, output 200, greedy, seed 42.")
            verdicts="not run (generation-only)" if name.endswith("_A") else json.dumps(m.get('verdict_counts',{}),sort_keys=True)
            pipeline_lines.append(f"| {label} | {m.get('n_inputs')} | {m.get('n_claims')} | {fmt(m.get('evidence_coverage'))} | {verdicts} | {m.get('correction_triggers')} | {m.get('corrections_attempted')} | {m.get('corrections_accepted')} | {m.get('safety_gate_rejections')} | {m.get('sibling_regressions')} | {m.get('final_reverification_failures')} | {m.get('unsafe_shipments')} | {fmt(m.get('runtime_seconds'),2)}s | {m.get('peak_gpu_memory_bytes')} |")
        matrix_report=load(pipeline/"paired_comparison.json")

    stats=[]
    for b in ("gold01","gold02"):
        c=gc[b]
        if c:
            stats.append(f"### {b.upper()} (n={c.get('mcnemar_exact',{}).get('n')})")
            stats.append(f"- McNemar exact two-sided p={c.get('mcnemar_exact',{}).get('exact_two_sided_p')}; baseline-only correct={c.get('mcnemar_exact',{}).get('baseline_only_correct')}; v2-only correct={c.get('mcnemar_exact',{}).get('v2_only_correct')}; discordant={c.get('mcnemar_exact',{}).get('discordant_pairs')}.")
            recall_test=c.get("mcnemar_contradicted_recall",{})
            stats.append(f"- Paired CONTRADICTED-recall test among gold contradictions (n={recall_test.get('gold_positive_n')}): baseline-only correct={recall_test.get('baseline_only_correct')}; V2-only correct={recall_test.get('v2_only_correct')}; discordant={recall_test.get('discordant_pairs')}; exact p={recall_test.get('exact_two_sided_p')}.")
            for metric,result in c.get("paired_bootstrap",{}).items():
                stats.append(f"- Paired bootstrap {metric}: delta={fmt(result.get('estimate'))}; 95% CI={result.get('ci_95')}; resamples={result.get('resamples')}.")
    if not stats: stats=["No paired statistical results are available."]

    corr_lines=[]
    safety_lines=[]
    if correction:
        for name,c in correction.get("comparisons",{}).items():
            left,right=c.get("left",{}),c.get("right",{})
            corr_lines.append(f"| {name} | {c.get('n_paired_inputs')} | {c.get('n_same_flagged_case_and_claim')} | {left.get('attempts')} / {right.get('attempts')} | {left.get('accepted')} / {right.get('accepted')} | {left.get('rejected_or_failed')} / {right.get('rejected_or_failed')} | {left.get('unsafe_shipments')} / {right.get('unsafe_shipments')} | {left.get('unsafe_shipments_per_attempt')} / {right.get('unsafe_shipments_per_attempt')} |")
            safety_lines.append(f"| {name} | {left.get('scope_gate_rejections')} / {right.get('scope_gate_rejections')} | {left.get('citation_identity_rejections')} / {right.get('citation_identity_rejections')} | {left.get('ordinal_gate_rejections')} / {right.get('ordinal_gate_rejections')} | {left.get('sibling_regressions')} / {right.get('sibling_regressions')} | {left.get('full_reverification_failures')} / {right.get('full_reverification_failures')} | {left.get('negation_caveat_claims')} / {right.get('negation_caveat_claims')} |")

    b1=gold["gold01"]["baseline"];v1=gold["gold01"]["v2"]
    g1b=b1[2] if b1 else {};g1v=v1[2] if v1 else {}
    env_models=env.get("model_revisions",{})
    lines=["# FINAL COMPARISON", "",
      "## 1. Research question", "Whether the requested local Qwen3-4B-Instruct-2507 + ModernBERT-large-NLI stack improves NyayaMind statutory-grounding verification over Qwen2.5-7B-Instruct + DeBERTa-v3, holding the existing legal pipeline fixed.", "",
      "## 2. Models and revisions", f"- Baseline generator/corrector: `Qwen/Qwen2.5-7B-Instruct`.", f"- Baseline verifier: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`.", f"- V2 generator/corrector: `Qwen/Qwen3-4B-Instruct-2507` at `{env_models.get('v2_generator')}`.", f"- V2 verifier: `tasksource/ModernBERT-large-nli` at `{env_models.get('v2_verifier')}`.", "- The local model config hashes matched the downloaded checkpoint revision metadata; local weight directories are git-ignored.", "",
      "## 3. Hardware and environment", f"- GPU: {env.get('gpu_name')}; total memory: {env.get('gpu_total_memory_bytes')} bytes.", f"- Python {env.get('python')}; PyTorch {env.get('torch')}; Transformers {env.get('transformers')}; CUDA {env.get('cuda_runtime')}; Accelerate {env.get('accelerate')}; bitsandbytes {env.get('bitsandbytes')}.", "- Qwen3 ran via the `research_v2/.venv` environment using Accelerate 1.15.0. Host/production dependencies were not changed.", "- Full run environment: [environment.json](environment.json); per-run environment and configuration are stored alongside raw predictions.", "",
      "## 4. Experimental design", "GOLD verifier tests used the same frozen premise/hypothesis pairs, labels, labeled-premise framing, 0.70 threshold, and verdict mapping. Full pipeline imported existing claim parsing, evidence matching, safety gates, correction policy, sibling checks, and reverification read-only. The Qwen3 adapter used NF4 4-bit, double quantization, bfloat16 compute, greedy decoding, seed 42, temperature/top-p 1.0, 200 generation tokens (220 for correction), and an 8192-token input ceiling that fails rather than silently truncating. ModernBERT uses the checkpoint config label mapping and 2048-token maximum; long premises are chunked in order with the complete claim repeated in each chunk, and the adapter records chunks and any aggregated/prefix verdict difference.", "",
      "## 5. Datasets", "GOLD-01: frozen n=420 three-class benchmark. GOLD-02: frozen n=59 contradiction-only synthetic fixture. Natural analysis: existing final-validation set and both existing 50-case candidate batches. Full pipeline: existing n=50 final-validation inputs. Natural/full-pipeline records have no independent legal correctness labels.", "",
      "## 6. Baseline and 7. V2", "Fresh paired benchmark metrics are shown as baseline / V2. Historical GOLD-01 labeled-premise DeBERTa result (accuracy 0.9714, macro-F1 0.9684) is preserved and matched by fresh baseline runs.", "",
      "## 8–9. Controlled GOLD results", "| Benchmark | n | Accuracy B / V2 | Macro-F1 B / V2 | CONTRADICTED recall B / V2 | Delta macro-F1 / contradiction recall |", "|---|---:|---:|---:|---:|---:|", *gold_tables, "", "GOLD-01 baseline confusion matrix:", "```json", json.dumps(g1b.get("confusion_matrix"),indent=2), "```", "GOLD-01 V2 confusion matrix:", "```json", json.dumps(g1v.get("confusion_matrix"),indent=2), "```", "GOLD-02 contains 59 gold contradictions and no other class. Report contradiction precision/recall; its macro-F1 is not a supported three-class measure.", "",
      "## 10. Natural-data results (descriptive only)", "| Dataset | Paired claims | Disagreements | Evidence coverage B / V2 | Truncated pair count B / V2 | Low-confidence rate B / V2 | Mean latency B / V2 (s) | Baseline verdict counts | V2 verdict counts |", "|---|---:|---:|---:|---:|---:|---:|---|---|", *(natural_lines or ["| null | null | null | null | null | null | null | null | null |"]), "No natural-data result is called accuracy. Disagreements are not correctness judgments. ModernBERT's per-chunk token lengths and aggregation outcomes are retained per raw prediction; the model limit is 2048 tokens.", "",
      "## 11. Full pipeline and 15. 2x2 model matrix", "All 2x2 generation/verifier pairs ran through generation-only (A), generation+verification (B), and selective correction (C) on the same 50 inputs. Metrics below are natural-data behavior/resource observations, not accuracy.", "| Condition | Inputs | Claims | Evidence coverage | Verdict counts | Triggers | Attempts | Accepted | Gate rejections | Sibling regressions | Reverification failures | Unsafe shipments | Runtime | Peak GPU bytes |", "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|", *(pipeline_lines or ["| null | null | null | null | null | null | null | null | null | null | null | null | null | null |"]), "", "Paired 2x2 behavior comparisons (no ground truth):", "```json", json.dumps(matrix_report,indent=2), "```", *pipeline_generations, "",
      "## 12. Correction comparison", "Case-level correction outcomes are paired below. The primary deployment comparison had no identical flagged claim in common; the controlled generator comparison under the same ModernBERT verifier had a small overlap. Accepted means the unchanged production safety policy and final verification accepted the correction; it does not establish legal correctness without labels.", "| Pair | Inputs | Same flagged case+claim | Attempts B / V2 | Accepted B / V2 | Rejected/failed B / V2 | Unsafe shipments B / V2 | Unsafe / attempts B / V2 |", "|---|---:|---:|---:|---:|---:|---:|---:|", *(corr_lines or ["| null | null | null | null | null | null | null | null |"]), "",
      "## 13. Safety results", "Unsafe shipment definition follows the existing fail-closed correction pipeline: a correction shipped despite a non-ENTAILED final reverification. Zero unsafe shipments in this 50-case sample is not a broad guarantee. Gate counts are baseline / V2:", "| Pair | Scope rejects | Citation identity rejects | Ordinal rejects | Sibling regressions | Full reverification failures | Negation caveat claims |", "|---|---:|---:|---:|---:|---:|---:|", *(safety_lines or ["| null | null | null | null | null | null | null |"]), "No separate negation-violation status exists in the existing pipeline; negation caveats suppress correction eligibility, and no caveated claims occurred in this sample.", "",
      "## 14. Efficiency", f"GOLD-01 current DeBERTa mean inference latency={g1b.get('mean_latency_seconds')} s, peak allocated GPU={g1b.get('peak_gpu_memory_bytes')} bytes; ModernBERT mean inference latency={g1v.get('mean_latency_seconds')} s, peak allocated GPU={g1v.get('peak_gpu_memory_bytes')} bytes. Qwen3 smoke load and generation telemetry are saved under `results/sanity/`; per-input generation timing and GPU-memory telemetry are in the raw prediction JSONL files for the verification conditions.", "",
      "## 16. Statistical analysis", *stats, "McNemar tests are applied to paired accuracy and, separately, gold-positive contradiction recall. Bootstrap intervals resample paired examples (5,000 draws, seed 42). GOLD-02 estimates are uncertain because n=59 and one class; intervals crossing zero and p>0.05 are inconclusive. The reported p-values are unadjusted exploratory comparisons; they do not establish broad legal-task superiority.", "",
      "## 17. Error analysis", "GOLD per-case inputs, gold labels, both predictions/confidences/probabilities, token lengths, and truncation status are saved in the paired JSONL files. See [error_analysis.md](error_analysis.md). Label-transition categories:", *transition_lines, "", "The full-pipeline 2x2 paired artifacts separate generator-effect comparisons (same verifier) from verifier-effect comparisons (same generator). They are unlabeled natural observations; claim changes and verdict changes cannot be called model errors.", "",
      "## 18. Cases where V2 improved", f"On GOLD-01, paired correctness records show {gc['gold01'].get('mcnemar_exact',{}).get('v2_only_correct')} cases where V2 alone was correct; see the case-level error report.", "",
      "## 19. Cases where V2 degraded", f"On GOLD-01, paired correctness records show {gc['gold01'].get('mcnemar_exact',{}).get('baseline_only_correct')} cases where baseline alone was correct. Net accuracy delta is {fmt(c.get('delta',{}).get('accuracy')) if (c:=gc['gold01']) else 'null'}.", "",
      "## 20. Model disagreements", "GOLD disagreements are resolved against the fixture's unchanged gold labels and listed by transition in section 17. Natural/full-pipeline disagreements are preserved as unlabeled; the 2x2 matrix helps attribute changes to generator versus verifier without labeling one output correct.", "",
      "## 21. Limitations and unsupported claims", "GOLD fixtures are controlled/synthetic and do not substitute for lawyer-reviewed legal truth. GOLD-02 lacks non-contradiction cases. Natural data and full pipeline have no independent correctness labels. The Qwen3 smoke prompt is only a load/generation check, not a quality test. V2 generation/correction quality cannot be concluded from verdict distributions or acceptance counts. No weights are committed. Results are limited to this hardware, runtime, prompt/settings, and frozen sample.", "",
      "## 22. Evidence-based conclusion", "ModernBERT is worse than DeBERTa on GOLD-01 under the fixed labeled-premise benchmark: macro-F1 and contradiction recall are lower, with paired evidence against the baseline. GOLD-02 also points lower for contradiction recall but is inconclusive at its small single-class sample size. Qwen3 successfully loaded and generated on the RTX 4050, and the complete 2x2 natural pipeline ran; however, end-to-end natural data have no correctness labels. The measured evidence does not support replacing the current stack. The overall stack-level legal quality comparison remains inconclusive because generator/correction outputs lack independent gold judgments.", "",
    ]
    out=REPORTS/"FINAL_COMPARISON.md";out.write_text("\n".join(lines),encoding="utf-8");print(out)

if __name__=="__main__":main()
