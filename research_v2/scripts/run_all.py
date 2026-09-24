#!/usr/bin/env python3
"""Run paired GOLD comparisons sequentially and generate immutable reports."""
from __future__ import annotations
import csv, datetime, json, random, subprocess, sys, platform
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research_v2.src.comparison.paired import pair_predictions, mcnemar_exact

def mcnemar_class_recall(baseline, v2, gold, target_label):
    """Paired exact test restricted to gold-positive examples for class recall."""
    b={r["id"]:r["predicted_label"] for r in baseline};v={r["id"]:r["predicted_label"] for r in v2}
    ids=[k for k in gold if gold[k]==target_label]
    b_only=sum(b[k]==target_label and v[k]!=target_label for k in ids)
    v_only=sum(v[k]==target_label and b[k]!=target_label for k in ids)
    discordant=b_only+v_only
    p=min(1.0,2*sum(math.comb(discordant,i) for i in range(min(b_only,v_only)+1))/(2**discordant)) if discordant else 1.0
    return {"class":target_label,"gold_positive_n":len(ids),"baseline_only_correct":b_only,"v2_only_correct":v_only,"discordant_pairs":discordant,"exact_two_sided_p":p}

def _bootstrap_delta(baseline, v2, gold, metric, iterations=5000, seed=42):
    rng = random.Random(seed)
    n = len(gold); deltas = []
    for _ in range(iterations):
        ix = [rng.randrange(n) for _ in range(n)]
        if metric == "accuracy":
            a = sum(baseline[i]["predicted_label"] == gold[i] for i in ix) / n
            b = sum(v2[i]["predicted_label"] == gold[i] for i in ix) / n
        elif metric == "macro_f1":
            def macro(rows):
                fs=[]
                for label in ("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION"):
                    tp=sum(gold[i]==label and rows[i]["predicted_label"]==label for i in ix)
                    fp=sum(gold[i]!=label and rows[i]["predicted_label"]==label for i in ix)
                    fn=sum(gold[i]==label and rows[i]["predicted_label"]!=label for i in ix)
                    pr=tp/(tp+fp) if tp+fp else 0.;re=tp/(tp+fn) if tp+fn else 0.
                    fs.append(2*pr*re/(pr+re) if pr+re else 0.)
                return sum(fs)/3
            a=macro(baseline);b=macro(v2)
        else:  # CONTRADICTED recall
            denom = sum(gold[i] == "CONTRADICTED" for i in ix)
            if denom == 0: continue
            a = sum(gold[i] == "CONTRADICTED" and baseline[i]["predicted_label"] == "CONTRADICTED" for i in ix) / denom
            b = sum(gold[i] == "CONTRADICTED" and v2[i]["predicted_label"] == "CONTRADICTED" for i in ix) / denom
        deltas.append(b - a)
    deltas.sort()
    if metric == "accuracy":
        estimate = sum((v2[i]["predicted_label"] == gold[i]) - (baseline[i]["predicted_label"] == gold[i]) for i in range(n)) / n
    elif metric == "macro_f1":
        def full_macro(rows):
            fs=[]
            for label in ("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION"):
                tp=sum(gold[i]==label and rows[i]["predicted_label"]==label for i in range(n));fp=sum(gold[i]!=label and rows[i]["predicted_label"]==label for i in range(n));fn=sum(gold[i]==label and rows[i]["predicted_label"]!=label for i in range(n))
                pr=tp/(tp+fp) if tp+fp else 0.;re=tp/(tp+fn) if tp+fn else 0.;fs.append(2*pr*re/(pr+re) if pr+re else 0.)
            return sum(fs)/3
        estimate=full_macro(v2)-full_macro(baseline)
    else:
        denom = sum(x == "CONTRADICTED" for x in gold)
        estimate = ((sum(gold[i] == "CONTRADICTED" and v2[i]["predicted_label"] == "CONTRADICTED" for i in range(n)) -
                     sum(gold[i] == "CONTRADICTED" and baseline[i]["predicted_label"] == "CONTRADICTED" for i in range(n))) / denom) if denom else None
    return {"estimate": estimate,
            "ci_95": [deltas[int(.025*len(deltas))], deltas[min(len(deltas)-1, int(.975*len(deltas)))]] if deltas else None,
            "bootstrap_n": len(deltas), "resamples": iterations}

def _invoke(which, stack, device, logs_dir):
    run_id = f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}_{which}_{stack}"
    cmd = [sys.executable, str(ROOT / "research_v2" / "scripts" / f"run_{which}.py"), "--model", stack, "--device", device, "--run-id", run_id]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (logs_dir / f"{run_id}.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (logs_dir / f"{run_id}.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"{which}/{stack} failed ({proc.returncode}); see {logs_dir / f'{run_id}.stderr.log'}")
    return ROOT / "research_v2" / "results" / "runs" / run_id

def _invoke_natural(stack, device, logs_dir, input_path):
    slug=Path(input_path).stem
    run_id = f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}_natural_{stack}_{slug}"
    cmd = [sys.executable, str(ROOT / "research_v2" / "scripts" / "run_natural.py"), "--model", stack, "--device", device,"--input",input_path]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (logs_dir / f"{run_id}.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (logs_dir / f"{run_id}.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode: raise RuntimeError(f"natural/{stack} failed; see {logs_dir / f'{run_id}.stderr.log'}")
    # run_natural creates its own immutable timestamped result directory.
    latest = max((ROOT / "research_v2" / "results" / "runs").glob("*_natural_" + stack+"_"+slug), key=lambda p:p.stat().st_mtime)
    return latest

def _invoke_phase(name, command, logs_dir):
    run_id=f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}_{name}"
    proc=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (logs_dir/f"{run_id}.stdout.log").write_text(proc.stdout,encoding="utf-8")
    (logs_dir/f"{run_id}.stderr.log").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:raise RuntimeError(f"{name} failed ({proc.returncode}); see {logs_dir/f'{run_id}.stderr.log'}")
    return proc.stdout

def _compare_natural(baseline_dir, v2_dir):
    b=[json.loads(x) for x in (baseline_dir/"predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    v=[json.loads(x) for x in (v2_dir/"predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    key=lambda x:(x["document_id"],x["claim_id"])
    bm={key(x):x for x in b};vm={key(x):x for x in v}
    if bm.keys()!=vm.keys(): raise ValueError("Natural paired runs do not have identical claim IDs")
    categories={"both_agree":0,"both_abstain":0,"model_disagreement_ground_truth_unavailable":0}
    rows=[]
    for k in bm:
        x,y=bm[k],vm[k];a=x.get("verdict");z=y.get("verdict")
        cat=("both_abstain" if a==z and a in {"NOT_ENOUGH_INFORMATION","NO_EVIDENCE"} else "both_agree" if a==z else "model_disagreement_ground_truth_unavailable")
        categories[cat]=categories.get(cat,0)+1
        if a!=z: rows.append({"document_id":k[0],"claim_id":k[1],"baseline_verdict":a,"v2_verdict":z,"baseline_confidence":x.get("confidence"),"v2_confidence":y.get("confidence"),"category":cat})
    report={"dataset":json.loads((baseline_dir/"metrics.json").read_text(encoding="utf-8"))["dataset"],"baseline_model":b[0]["model_id"],"v2_model":v[0]["model_id"],"n_paired_claims":len(bm),"categories":categories,
            "baseline_verdicts":json.loads((baseline_dir/"metrics.json").read_text(encoding="utf-8"))["verdict_counts"],
            "v2_verdicts":json.loads((v2_dir/"metrics.json").read_text(encoding="utf-8"))["verdict_counts"],
            "interpretation":"Agreement and distribution only; no ground truth, so no natural-data accuracy or correctness claim."}
    reports=ROOT/"research_v2"/"results"/"reports";stamp=datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    (reports/f"natural_comparison_{stamp}.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (reports/f"natural_disagreements_{stamp}.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8")
    print(f"natural: paired={len(bm)}, disagreements={len(rows)}; no gold labels; report={reports}")

def _compare(which, baseline_dir, v2_dir):
    bp = [json.loads(x) for x in (baseline_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    vp = [json.loads(x) for x in (v2_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    bm = json.loads((baseline_dir / "metrics.json").read_text(encoding="utf-8")); vm = json.loads((v2_dir / "metrics.json").read_text(encoding="utf-8"))
    gold = {r["id"]: r["expected_label"] for r in bp}
    paired = pair_predictions(bp, vp, gold)
    paired_full=[]
    for left,right,summary in zip(bp,vp,paired):
        paired_full.append({"id":summary["id"],"input":left["source"],"premise":left["premise"],"hypothesis":left["hypothesis"],"gold_label":summary["gold_label"],
            "baseline":{"model":left["model_id"],"prediction":left["predicted_label"],"confidence":left["confidence"],"probabilities":left["probabilities"],"latency_seconds":left["latency_seconds"],"input_truncated":left.get("input_truncated"),"token_lengths":left.get("token_lengths")},
            "v2":{"model":right["model_id"],"prediction":right["predicted_label"],"confidence":right["confidence"],"probabilities":right["probabilities"],"latency_seconds":right["latency_seconds"],"input_truncated":right.get("input_truncated"),"token_lengths":right.get("token_lengths")},"category":summary["category"]})
    tests = mcnemar_exact(bp, vp, gold)
    contradiction_recall_test=mcnemar_class_recall(bp,vp,gold,"CONTRADICTED")
    gold_order = [gold[r["id"]] for r in bp]
    boot_acc = _bootstrap_delta(bp, vp, gold_order, "accuracy")
    boot_contra = _bootstrap_delta(bp, vp, gold_order, "contradicted_recall")
    boot_macro = _bootstrap_delta(bp, vp, gold_order, "macro_f1")
    macro_valid=all(bm["per_class"][c]["support"]>0 for c in ("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION"))
    primary_ci=boot_macro["ci_95"] if macro_valid else boot_contra["ci_95"]
    primary_delta=vm["macro_f1"]-bm["macro_f1"] if macro_valid else vm["per_class"]["CONTRADICTED"]["recall"]-bm["per_class"]["CONTRADICTED"]["recall"]
    primary_metric="macro_f1" if macro_valid else "CONTRADICTED_recall (only supported class)"
    interpretation=("unchanged" if primary_delta==0 else "improved" if primary_ci and primary_ci[0]>0 else "degraded" if primary_ci and primary_ci[1]<0 else "inconclusive")
    report = {"benchmark": which, "baseline": {"model": bm["model_id"], "metrics": bm}, "v2": {"model": vm["model_id"], "metrics": vm},
              "delta": {"accuracy": vm["accuracy"] - bm["accuracy"], "macro_f1": vm["macro_f1"] - bm["macro_f1"], "contradicted_recall": vm["per_class"]["CONTRADICTED"]["recall"] - bm["per_class"]["CONTRADICTED"]["recall"]},
              "mcnemar_exact": tests, "mcnemar_contradicted_recall": contradiction_recall_test, "paired_bootstrap": {"accuracy": boot_acc, "macro_f1":boot_macro, "contradicted_recall": boot_contra},
              "paired_categories": {k: sum(x["category"] == k for x in paired) for k in sorted({x["category"] for x in paired})},
              "primary_interpretable_metric":primary_metric,"macro_f1_all_classes_supported":macro_valid,
              "interpretation": interpretation,"interpretation_basis":f"paired bootstrap CI for {primary_metric}; interpretation does not mean V2 is globally better and does not override safety metrics"}
    reports = ROOT / "research_v2" / "results" / "reports"; reports.mkdir(parents=True, exist_ok=True)
    (reports / f"{which}_comparison_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (reports / f"{which}_paired_disagreements_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in paired if x["baseline"] != x["v2"]), encoding="utf-8")
    paired_dir=ROOT/"research_v2"/"results"/"paired"/which;paired_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    (paired_dir/f"{stamp}_predictions.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in paired_full),encoding="utf-8")
    (paired_dir/f"{stamp}_manifest.json").write_text(json.dumps({"baseline_run":str(baseline_dir.relative_to(ROOT)),"v2_run":str(v2_dir.relative_to(ROOT)),"n":len(paired_full)},indent=2),encoding="utf-8")
    csv_path = reports / f"{which}_comparison_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["metric", "baseline", "v2", "absolute_delta"])
        for key, bval, vval in [("accuracy", bm["accuracy"], vm["accuracy"]), ("macro_f1", bm["macro_f1"], vm["macro_f1"]), ("weighted_f1", bm["weighted_f1"], vm["weighted_f1"]), ("contradicted_precision", bm["per_class"]["CONTRADICTED"]["precision"], vm["per_class"]["CONTRADICTED"]["precision"]), ("contradicted_recall", bm["per_class"]["CONTRADICTED"]["recall"], vm["per_class"]["CONTRADICTED"]["recall"]), ("contradicted_f1", bm["per_class"]["CONTRADICTED"]["f1"], vm["per_class"]["CONTRADICTED"]["f1"]), ("entailed_recall", bm["per_class"]["ENTAILED"]["recall"], vm["per_class"]["ENTAILED"]["recall"]), ("nei_precision", bm["per_class"]["NOT_ENOUGH_INFORMATION"]["precision"], vm["per_class"]["NOT_ENOUGH_INFORMATION"]["precision"]), ("nei_recall", bm["per_class"]["NOT_ENOUGH_INFORMATION"]["recall"], vm["per_class"]["NOT_ENOUGH_INFORMATION"]["recall"])]: writer.writerow([key, bval, vval, vval-bval])
    md=[f"# {which.upper()} comparison", "", f"Baseline: `{bm['model_id']}`; V2: `{vm['model_id']}`; n={bm['n']}.", "", "| Metric | Baseline | V2 | Absolute delta |", "|---|---:|---:|---:|"]
    for key,bval,vval in [("Accuracy",bm["accuracy"],vm["accuracy"]),("Macro-F1",bm["macro_f1"],vm["macro_f1"]),("Weighted F1",bm["weighted_f1"],vm["weighted_f1"]),("CONTRADICTED precision",bm["per_class"]["CONTRADICTED"]["precision"],vm["per_class"]["CONTRADICTED"]["precision"]),("CONTRADICTED recall",bm["per_class"]["CONTRADICTED"]["recall"],vm["per_class"]["CONTRADICTED"]["recall"]),("CONTRADICTED F1",bm["per_class"]["CONTRADICTED"]["f1"],vm["per_class"]["CONTRADICTED"]["f1"]),("ENTAILED recall",bm["per_class"]["ENTAILED"]["recall"],vm["per_class"]["ENTAILED"]["recall"]),("NEI precision",bm["per_class"]["NOT_ENOUGH_INFORMATION"]["precision"],vm["per_class"]["NOT_ENOUGH_INFORMATION"]["precision"]),("NEI recall",bm["per_class"]["NOT_ENOUGH_INFORMATION"]["recall"],vm["per_class"]["NOT_ENOUGH_INFORMATION"]["recall"])]: md.append(f"| {key} | {bval:.4f} | {vval:.4f} | {vval-bval:+.4f} |")
    md += ["",f"Exact McNemar paired-accuracy test: discordant={tests['discordant_pairs']}, p={tests['exact_two_sided_p']:.6g}.",f"Exact paired CONTRADICTED-recall test among gold contradictions (n={contradiction_recall_test['gold_positive_n']}): baseline-only correct={contradiction_recall_test['baseline_only_correct']}, V2-only correct={contradiction_recall_test['v2_only_correct']}, p={contradiction_recall_test['exact_two_sided_p']:.6g}.","",f"Paired bootstrap 95% CI for accuracy delta: {boot_acc['ci_95']}; contradiction-recall delta: {boot_contra['ci_95']}.","","Interpretation: evaluate the predeclared metric hierarchy and uncertainty together; this report does not declare V2 better by default."]
    md_text="\n".join(md)+"\n"
    (reports/f"{which}_comparison_{stamp}.md").write_text(md_text,encoding="utf-8")
    (reports/f"{which}_comparison.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (reports/f"{which}_comparison.csv").write_bytes(csv_path.read_bytes())
    (reports/f"{which}_comparison.md").write_text(md_text,encoding="utf-8")
    figures=reports/"figures";figures.mkdir(parents=True,exist_ok=True)
    classes=("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION")
    short={"ENTAILED":"Entailed","CONTRADICTED":"Contradicted","NOT_ENOUGH_INFORMATION":"NEI"}
    def matrix_svg(metrics,model,name):
        cell=90;left=150;top=90;width=left+3*cell+20;height=top+3*cell+75
        pieces=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<style>text{font-family:Arial,sans-serif;font-size:13px}.title{font-size:16px;font-weight:bold}</style>',f'<text class="title" x="10" y="25">{name}: {model}</text>',f'<text x="{left+35}" y="53">Predicted label</text>',f'<text transform="translate(18 {top+120}) rotate(-90)">Gold label</text>']
        for j,c in enumerate(classes):pieces.append(f'<text x="{left+j*cell+12}" y="{top-10}">{short[c]}</text>')
        for i,g in enumerate(classes):
            pieces.append(f'<text x="15" y="{top+i*cell+48}">{short[g]}</text>');row=metrics["confusion_matrix"][g];mx=max(row.values()) or 1
            for j,pred in enumerate(classes):
                value=row.get(pred,0);red=int(245-95*value/mx);green=int(248-145*value/mx);blue=int(250-145*value/mx);x=left+j*cell;y=top+i*cell
                pieces.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="rgb({red},{green},{blue})" stroke="#fff"/><text x="{x+cell/2-5}" y="{y+cell/2+5}">{value}</text>')
        pieces.append('</svg>');(figures/f"{which}_{name.lower()}_confusion.svg").write_text("".join(pieces),encoding="utf-8")
    matrix_svg(bm,bm["model_id"],"baseline");matrix_svg(vm,vm["model_id"],"v2")
    bars=[];W,H=720,340;bars += [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><style>text{{font-family:Arial,sans-serif;font-size:13px}}.title{{font-size:16px;font-weight:bold}}</style><text class="title" x="10" y="25">{which.upper()} per-class recall and F1</text>']
    colors={"baseline":"#5875a4","v2":"#d48447"}
    for i,c in enumerate(classes):
        x0=135+i*185
        for stack,met,offset in (("baseline",bm,-35),("v2",vm,10)):
            for metric,j in (("recall",0),("f1",1)):
                value=met["per_class"][c][metric];x=x0+offset+j*18;y=285-value*210
                bars.append(f'<rect x="{x}" y="{y}" width="14" height="{value*210}" fill="{colors[stack]}"/><text x="{x-4}" y="{y-4}">{value:.2f}</text>')
        bars.append(f'<text x="{x0-20}" y="310">{short[c]}</text>')
    bars.append('<text x="120" y="335">Blue=baseline, orange=V2; within each group: recall then F1</text></svg>')
    (figures/f"{which}_class_recall_f1.svg").write_text("".join(bars),encoding="utf-8")
    sections=[]
    for benchmark in ("gold01","gold02"):
        paths=sorted((ROOT/"research_v2"/"results"/"paired"/benchmark).glob("*_predictions.jsonl"))
        if not paths:continue
        records=[json.loads(line) for line in paths[-1].read_text(encoding="utf-8").splitlines() if line.strip()]
        disagreements=[r for r in records if r["baseline"]["prediction"]!=r["v2"]["prediction"]]
        sections += [f"## {benchmark.upper()}",f"Paired cases: {len(records)}; disagreements: {len(disagreements)}. Full source, claim, evidence, probabilities, token lengths, and truncation metadata are preserved in [`{paths[-1].relative_to(ROOT).as_posix()}`]({paths[-1].as_posix()})."]
        for row in disagreements:
            sections.append(f"- `{row['id']}` gold `{row['gold_label']}`; baseline `{row['baseline']['prediction']}` ({row['baseline']['confidence']:.4f}), V2 `{row['v2']['prediction']}` ({row['v2']['confidence']:.4f}).")
        sections.append("")
    (reports/"error_analysis.md").write_text("# GOLD case-level disagreement analysis\n\n"+"\n".join(sections),encoding="utf-8")
    print(f"{which}: baseline macro-F1={bm['macro_f1']:.4f}, v2={vm['macro_f1']:.4f}, delta={vm['macro_f1']-bm['macro_f1']:+.4f}; McNemar p={tests['exact_two_sided_p']:.6g}; reports={reports}")

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--device", choices=("cpu","cuda","cuda:0"), default="cuda:0"); p.add_argument("--benchmarks", nargs="+", choices=("gold01","gold02"), default=("gold01","gold02")); p.add_argument("--skip-natural", action="store_true"); p.add_argument("--skip-sanity",action="store_true");p.add_argument("--skip-pipeline",action="store_true"); args=p.parse_args()
    logs=ROOT/"research_v2"/"logs"/datetime.datetime.now().strftime("run_all_%Y%m%dT%H%M%S"); logs.mkdir(parents=True,exist_ok=False)
    import torch, transformers
    environment={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"git_commit":subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True).stdout.strip() or None,
                 "python":platform.python_version(),"torch":torch.__version__,"transformers":transformers.__version__,"cuda_runtime":torch.version.cuda,
                 "cuda_available":torch.cuda.is_available(),"gpu_name":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                 "device":args.device,"models":{"baseline_generator":"Qwen/Qwen2.5-7B-Instruct","baseline_verifier":"MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli","v2_generator":"Qwen/Qwen3-4B-Instruct-2507","v2_verifier":"tasksource/ModernBERT-large-nli"},
                 "seed":42,"command":" ".join(sys.argv)}
    (logs/"environment.json").write_text(json.dumps(environment,indent=2),encoding="utf-8")
    reports=ROOT/"research_v2"/"results"/"reports";reports.mkdir(parents=True,exist_ok=True)
    (reports/"environment.json").write_text(json.dumps(environment,indent=2),encoding="utf-8")
    if not args.skip_sanity:
        for stack in ("baseline","v2"):
            _invoke_phase(f"sanity_{stack}",[sys.executable,str(ROOT/"research_v2"/"scripts"/"run_sanity.py"),"--model",stack,"--device",args.device],logs)
    for which in args.benchmarks:
        base=_invoke(which,"baseline",args.device,logs)
        v2=_invoke(which,"v2",args.device,logs)
        _compare(which,base,v2)
    if not args.skip_natural:
        natural_inputs=("research/prototype/outputs/final_gpu_validation_B.jsonl","research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl","research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl")
        for input_path in natural_inputs:
            base=_invoke_natural("baseline",args.device,logs,input_path)
            v2=_invoke_natural("v2",args.device,logs,input_path)
            _compare_natural(base,v2)
    if not args.skip_pipeline:
        output=_invoke_phase("full_pipeline_2x2",[sys.executable,str(ROOT/"research_v2"/"scripts"/"run_full_pipeline.py"),"--limit","50","--matrix"],logs)
        run_dir=output.strip().splitlines()[-1]
        _invoke_phase("correction_comparison",[sys.executable,str(ROOT/"research_v2"/"scripts"/"run_correction_comparison.py"),"--run-dir",run_dir],logs)
    _invoke_phase("final_report",[sys.executable,str(ROOT/"research_v2"/"scripts"/"build_final_report.py")],logs)
    return 0

if __name__ == "__main__": raise SystemExit(main())
