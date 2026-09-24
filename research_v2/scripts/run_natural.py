#!/usr/bin/env python3
"""Re-score the frozen final-validation natural claims with either verifier."""
from __future__ import annotations
import argparse, datetime, hashlib, json, re, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"research"/"prototype"))
from research_v2.scripts._run_gold_common import _verifier
from src.verifier import format_premise, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION

def main():
    p=argparse.ArgumentParser();p.add_argument("--model",choices=("baseline","v2"),required=True);p.add_argument("--device",default="cuda:0");p.add_argument("--input",default="research/prototype/outputs/final_gpu_validation_B.jsonl");a=p.parse_args()
    source=ROOT/a.input; cases=[json.loads(x) for x in source.read_text(encoding="utf-8").splitlines() if x.strip()]
    verifier,model_id=_verifier(a.model,a.device)
    if hasattr(verifier,"load"):verifier.load()
    import torch,platform,subprocess
    if a.device.startswith("cuda"):torch.cuda.reset_peak_memory_stats(torch.device(a.device))
    total_claims=matched=0;preds=[];started=time.perf_counter()
    for record in cases:
        for claim in record.get("claims",[]):
            total_claims+=1
            evidence=claim.get("evidence_text");evidence_id=claim.get("evidence_id")
            if not evidence or not evidence_id: continue
            matched+=1
            m=re.match(r"(Article|Section|Order|Rule|Regulation|Clause|Schedule)\s+(.+?)\s+in\s+(.+)$", evidence_id, re.I)
            premise=format_premise(evidence,"labeled",m.group(1) if m else None,m.group(2) if m else None,m.group(3) if m else None)
            hypothesis=claim.get("assertion_text") or claim.get("claim_text","")
            result=verifier.verify(premise,hypothesis)
            if isinstance(result,dict):
                label=result.get("normalized_verdict");conf=result.get("confidence");scores=result.get("probability_distribution");reason=result.get("sub_reason");trunc=result.get("token_lengths");prefix=result.get("prefix_only_verdict");chunk_changed=result.get("chunk_aggregation_changes_verdict")
            else:label=result.label;conf=result.confidence;scores=result.raw_scores;reason=result.sub_reason;trunc={"input_truncated":result.input_truncated};prefix=None;chunk_changed=False
            preds.append({"document_id":record["document_id"],"claim_id":claim["claim_id"],"claim_text":claim.get("claim_text"),"hypothesis":hypothesis,"evidence_id":evidence_id,"evidence_text":evidence,"premise":premise,"baseline_source_verdict":claim.get("verdict"),"verdict":label,"confidence":conf,"probabilities":scores,"sub_reason":reason,"low_confidence":reason=="low_confidence","token_lengths":trunc,"prefix_only_verdict":prefix,"chunk_aggregation_changes_verdict":chunk_changed,"correction_trigger":label==CONTRADICTED or (label==NOT_ENOUGH_INFORMATION and reason=="low_confidence"),"model_id":model_id})
    elapsed=time.perf_counter()-started
    for r in cases:
        for c in r.get("claims",[]):
            if not c.get("evidence_id") or not c.get("evidence_text"):
                preds.append({"document_id":r["document_id"],"claim_id":c["claim_id"],"evidence_id":None,"verdict":"NO_EVIDENCE","confidence":None,"correction_trigger":False,"model_id":model_id})
    counts={v:sum(x.get("verdict")==v for x in preds) for v in ("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION","NO_EVIDENCE")}
    metrics={"kind":"natural_unlabeled_descriptive_only","n_cases":len(cases),"n_claims":total_claims,"evidence_coverage":matched/total_claims if total_claims else None,"verdict_counts":counts,"verdict_rates":{k:v/total_claims if total_claims else None for k,v in counts.items()},"low_confidence_rate":sum(bool(x.get("low_confidence")) for x in preds)/total_claims if total_claims else None,"correction_trigger_rate":sum(bool(x.get("correction_trigger")) for x in preds)/total_claims if total_claims else None,"truncation_count":sum(bool((x.get("token_lengths") or {}).get("truncated",(x.get("token_lengths") or {}).get("input_truncated",False))) for x in preds),"chunk_aggregation_verdict_changes":sum(bool(x.get("chunk_aggregation_changes_verdict")) for x in preds),"inference_count":matched,"elapsed_seconds":elapsed,"mean_latency_seconds":elapsed/matched if matched else None,"throughput_claims_per_second":matched/elapsed if elapsed else None,"peak_gpu_memory_bytes":int(torch.cuda.max_memory_allocated(torch.device(a.device))) if a.device.startswith("cuda") and torch.cuda.is_available() else None,"gpu_name":torch.cuda.get_device_name(torch.device(a.device)) if a.device.startswith("cuda") and torch.cuda.is_available() else None,"torch_version":torch.__version__,"transformers_version":__import__("transformers").__version__,"python":platform.python_version(),"git_commit":subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True).stdout.strip() or None,"model_id":model_id,"model_revision":getattr(verifier,"model_revision",None),"dataset":a.input,"dataset_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"device":a.device,"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"note":"Descriptive natural-data comparison; no independent correctness labels, not legal accuracy."}
    run_id=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ_natural_")+a.model+"_"+source.stem;dest=ROOT/"research_v2"/"results"/"runs"/run_id;dest.mkdir(parents=True,exist_ok=False)
    (dest/"predictions.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in preds),encoding="utf-8");(dest/"metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8");print(json.dumps({"run_dir":str(dest),"metrics":metrics},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
