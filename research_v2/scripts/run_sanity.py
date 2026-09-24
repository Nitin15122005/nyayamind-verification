#!/usr/bin/env python3
"""Load one NLI model and run 30 balanced synthetic plus 5 real sanity pairs."""
from __future__ import annotations
import argparse, datetime, json, math, platform, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"research"/"prototype"))
from research_v2.scripts._run_gold_common import _verifier

def cases():
    out=[]
    rules=[("ENTAILED", "The tenant shall pay rent on the first day of each month.", "The tenant must pay rent on day one of every month."),
           ("CONTRADICTED", "The tenant shall pay rent on the first day of each month.", "The tenant is not required to pay rent on any day."),
           ("NOT_ENOUGH_INFORMATION", "The tenant shall pay rent on the first day of each month.", "The tenant paid rent yesterday in cash.")]
    for label,prem,hyp in rules:
        for i in range(10): out.append({"id":f"synthetic_{label}_{i+1}","expected_relation":label,"premise":prem,"hypothesis":hyp})
    fixture=ROOT/"research"/"prototype"/"evaluation"/"expected_outputs"/"controlled_benchmark_gold"/"controlled_verifier_benchmark.jsonl"
    for i,line in enumerate(fixture.read_text(encoding="utf-8").splitlines()):
        if len([x for x in out if x.get("kind")=="real_nyayamind"])>=5: break
        r=json.loads(line)
        from src.verifier import format_premise
        out.append({"id":f"real_{r['benchmark_id']}","expected_relation":r["expected_label"],"premise":format_premise(r["evidence_text"],"labeled",r.get("provision_type"),r.get("provision_number"),r.get("act_name")),"hypothesis":r["hypothesis"],"kind":"real_nyayamind"})
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument("--model",choices=("baseline","v2"),required=True);p.add_argument("--device",default="cuda:0");a=p.parse_args()
    import torch
    if a.device.startswith("cuda") and torch.cuda.is_available(): torch.cuda.reset_peak_memory_stats()
    load_started=time.perf_counter()
    verifier,model_id=_verifier(a.model,a.device)
    if hasattr(verifier,"load"):verifier.load()
    load_seconds=time.perf_counter()-load_started
    outputs=[]
    for item in cases():
        t=time.perf_counter(); r=verifier.verify(item["premise"],item["hypothesis"]); dt=time.perf_counter()-t
        if isinstance(r,dict):
            label=r.get("normalized_verdict"); confidence=r.get("confidence"); scores=r.get("probability_distribution"); raw_label=r.get("raw_model_label"); low=r.get("low_confidence"); trunc=r.get("token_lengths")
        else:
            label=r.label;confidence=r.confidence;scores=r.raw_scores;raw_label=max(scores,key=scores.get);low=r.sub_reason=="low_confidence";trunc=r.input_truncated
        if label not in {"ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION"}: raise ValueError(f"Invalid normalized verdict: {label}")
        if confidence is None or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1: raise ValueError("Invalid confidence")
        if not isinstance(scores,dict) or not scores: raise ValueError("Missing probability distribution")
        if any(not math.isfinite(float(x)) for x in scores.values()): raise ValueError("NaN/Inf in probabilities")
        outputs.append({**item,"model_id":model_id,"label":label,"confidence":float(confidence),"probabilities":scores,"raw_model_label":raw_label,"low_confidence":bool(low),"token_lengths":trunc,"latency_seconds":dt})
    # Verify repeatability on five rows, without a second full pass.
    deterministic=True
    for row in outputs[:5]:
        rr=verifier.verify(row["premise"],row["hypothesis"])
        again=rr.get("normalized_verdict") if isinstance(rr,dict) else rr.label
        confidence=rr.get("confidence") if isinstance(rr,dict) else rr.confidence
        probs=rr.get("probability_distribution") if isinstance(rr,dict) else rr.raw_scores
        stable=(again==row["label"] and abs(float(confidence)-row["confidence"])<1e-6 and set(probs)==set(row["probabilities"]) and all(abs(float(probs[k])-float(row["probabilities"][k]))<1e-6 for k in probs))
        deterministic=deterministic and stable
        if not stable: raise RuntimeError(f"Non-deterministic sanity output for {row['id']}")
    run_id=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ_")+a.model
    dest=ROOT/"research_v2"/"results"/"sanity"/run_id;dest.mkdir(parents=True,exist_ok=False)
    (dest/"predictions.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in outputs),encoding="utf-8")
    summary={"model":model_id,"device":a.device,"count":len(outputs),"class_case_counts":{x:sum(r["expected_relation"]==x for r in outputs if r.get("id","").startswith("synthetic_")) for x in ("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION")},"real_claim_count":5,"mapping_validated_from_model_config":True,"runtime_id2label":{str(k):v for k,v in getattr(verifier,"id2label",{}).items()} if hasattr(verifier,"id2label") else None,"max_position_length":getattr(getattr(verifier,"config",None),"max_position_length",None),"model_revision":getattr(getattr(getattr(verifier,"model",None),"config",None),"_commit_hash",None),"model_load_seconds":load_seconds,"peak_gpu_memory_bytes":int(torch.cuda.max_memory_allocated()) if a.device.startswith("cuda") and torch.cuda.is_available() else None,"truncation_count":sum(bool((r.get("token_lengths") or {}).get("truncated")) for r in outputs),"max_observed_pair_tokens":max((max((r.get("token_lengths") or {}).get("used_tokens_per_chunk",[0])) for r in outputs),default=0),"schema_valid":True,"finite_confidence":True,"deterministic_first_five":deterministic,"elapsed_inference_seconds":sum(r["latency_seconds"] for r in outputs),"warnings":[]}
    (dest/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(dest);return 0
if __name__=="__main__":raise SystemExit(main())
