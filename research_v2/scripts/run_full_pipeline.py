#!/usr/bin/env python3
"""Run paired generation-only, verification, and correction pipeline conditions.

Uses the production parser/matcher/safety/reverification functions read-only.
The primary source is the existing n=50 final-validation case set.
"""
from __future__ import annotations
import argparse, datetime, json, sys, time, gc
from pathlib import Path
from types import SimpleNamespace
import yaml
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"research"/"prototype"))
from src import pipeline
from src.corrector import SelectiveCorrector
from src.data_loader import load_usable_evidence_from_config
from src.generator import StatuteGroundingGenerator, GenerationMetadata
from src.verifier import NLIVerifier, VerificationResult

class CachedGenerator:
    def __init__(self, inner):self.inner=inner;self.cache={};self.telemetry={}
    def is_loaded(self):return self.inner.is_loaded()
    def __getattr__(self,name):return getattr(self.inner,name)
    def generate(self,case_text):
        if case_text not in self.cache:
            import torch
            if torch.cuda.is_available():torch.cuda.reset_peak_memory_stats()
            started=time.perf_counter();self.cache[case_text]=self.inner.generate(case_text)
            if torch.cuda.is_available():torch.cuda.synchronize()
            text,meta=self.cache[case_text]
            item=getattr(self.inner,"telemetry_by_case",{}).get(case_text,{})
            if not item:
                prompt=self.inner._build_prompt(case_text) if hasattr(self.inner,"_build_prompt") else case_text
                tok=getattr(self.inner,"_tokenizer",None)
                item={"input_tokens":len(tok(prompt,add_special_tokens=True)["input_ids"]) if tok else None,"output_tokens":len(tok(text,add_special_tokens=False)["input_ids"]) if tok else None}
            self.telemetry[case_text]={**item,"generation_latency_seconds":time.perf_counter()-started,"peak_gpu_memory_bytes":int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None,"model_id":meta.model_id,"generation_parameters":{"max_new_tokens":meta.max_new_tokens,"do_sample":meta.do_sample,"temperature":meta.temperature,"top_p":meta.top_p,"seed":meta.seed}}
        return self.cache[case_text]

class TimedCorrector:
    def __init__(self,inner):self.inner=inner;self.telemetry={}
    def __getattr__(self,name):return getattr(self.inner,name)
    def correct(self,case_text,*args,**kwargs):
        start=time.perf_counter();result=self.inner.correct(case_text,*args,**kwargs);self.telemetry[case_text]=time.perf_counter()-start;return result
    def correct_assertion_span(self,case_text,*args,**kwargs):
        start=time.perf_counter();result=self.inner.correct_assertion_span(case_text,*args,**kwargs);self.telemetry[case_text]=time.perf_counter()-start;return result

class TimedVerifier:
    def __init__(self,inner):self.inner=inner;self.latencies=[]
    def __getattr__(self,name):return getattr(self.inner,name)
    def verify(self,*args,**kwargs):
        start=time.perf_counter();result=self.inner.verify(*args,**kwargs);self.latencies.append(time.perf_counter()-start);return result

class Qwen3PipelineGenerator:
    def __init__(self,cfg):
        from research_v2.src.generation.qwen3_adapter import Qwen3Adapter,Qwen3Config
        g=cfg["generation"]
        self.adapter=Qwen3Adapter(Qwen3Config(model_id="Qwen/Qwen3-4B-Instruct-2507",device="cuda:0",allow_cpu_fallback=False,quantization="4bit_nf4",dtype="bfloat16",max_input_length=8192,max_new_tokens=g["max_new_tokens"],temperature=g["temperature"],top_p=g["top_p"],do_sample=g["do_sample"],seed=cfg["seed"]))
        self._tokenizer=self.adapter.tokenizer;self._model=self.adapter.model;self.model_id=self.adapter.config.model_id;self.seed=self.adapter.config.seed
        self.quantization={"load_in_4bit":True,"bnb_4bit_use_double_quant":True,"bnb_4bit_quant_type":"nf4","bnb_4bit_compute_dtype":"bfloat16"}
        self.system_prompt=g["system_prompt"];self.user_prompt_template=g["user_prompt_template"]
        self.telemetry_by_case={}
    def is_loaded(self):return self._model is not None
    def generate(self,case_text):
        res=self.adapter.generate(self.user_prompt_template.format(case_text=case_text),system_prompt=self.system_prompt,max_new_tokens=200)
        self.telemetry_by_case[case_text]={k:res.get(k) for k in ("input_tokens","output_tokens","input_truncated","latency_seconds","peak_gpu_memory_bytes","device","config","model_revision","transformers_version","torch_version")}
        meta=GenerationMetadata(self.model_id,self.quantization,200,False,1.0,1.0,self.seed)
        return res["text"],meta

class ModernPipelineVerifier:
    def __init__(self,device):
        from research_v2.src.verification.modernbert_verifier import ModernBertConfig,ModernBertVerifier
        self.inner=ModernBertVerifier(ModernBertConfig(device=device));self.model_id=self.inner.config.model_id
    def is_loaded(self):return self.inner.model is not None
    def verify(self,premise,hypothesis):
        r=self.inner.verify(premise,hypothesis)
        return VerificationResult(label=r["normalized_verdict"],confidence=r["confidence"],sub_reason=r["sub_reason"],raw_scores=r["probability_distribution"],verifier_model=self.model_id,input_truncated=r["token_lengths"]["truncated"])

def summarize(records):
    claims=[c for r in records for c in r.get("claims",[])]; corr=[r.get("correction",{}) for r in records]
    verdicts={k:sum(c.get("verdict")==k for c in claims) for k in ("ENTAILED","CONTRADICTED","NOT_ENOUGH_INFORMATION","NO_EVIDENCE")}
    statuses={}
    for c in corr:statuses[c.get("status","unknown")]=statuses.get(c.get("status","unknown"),0)+1
    return {"n_inputs":len(records),"n_claims":len(claims),"evidence_coverage":sum(bool(c.get("evidence_id")) for c in claims)/len(claims) if claims else None,"verdict_counts":verdicts,"correction_status_counts":statuses,
            "correction_triggers":sum(bool(c.get("triggered_for_claim_id")) for c in corr),"corrections_attempted":sum(int(c.get("attempts",0) or 0) for c in corr),"corrections_accepted":sum(c.get("status")=="corrected" for c in corr),
            "corrections_rejected":sum(int(c.get("attempts",0) or 0) for c in corr)-sum(c.get("status")=="corrected" for c in corr),
            "safety_gate_rejections":sum("scope_violation" in str(c.get("status","")) or "sibling_regression" in str(c.get("status","")) or "citation_violation" in str(c.get("status","")) or "ordinal_violation" in str(c.get("status","")) or "negation_violation" in str(c.get("status","")) for c in corr),
            "sibling_regressions":sum(len(c.get("sibling_regressions",[]) or []) for c in corr),"final_reverification_failures":sum(bool(c.get("reverification")) and (c.get("reverification") or {}).get("verdict")!="ENTAILED" for c in corr),
            "fail_closed_events":sum(str(c.get("status","")).startswith("correction_") and c.get("status")!="corrected" for c in corr),"unsafe_shipments":sum(c.get("status")=="corrected" and (c.get("reverification") or {}).get("verdict")!="ENTAILED" for c in corr)}

def main():
    p=argparse.ArgumentParser();p.add_argument("--limit",type=int,default=50);p.add_argument("--input",default="research/prototype/outputs/final_gpu_validation_B.jsonl");p.add_argument("--stack",choices=("baseline","v2","both"),default="both");p.add_argument("--matrix",action="store_true",help="run all four generator/verifier pairings");args=p.parse_args()
    source=ROOT/args.input;source_records=[json.loads(x) for x in source.read_text(encoding="utf-8").splitlines() if x.strip()][:args.limit]
    cfg=yaml.safe_load((ROOT/"research/prototype/config/prototype.yaml").read_text(encoding="utf-8"));exact,usable=load_usable_evidence_from_config(cfg,ROOT)
    run_id=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ");run_root=ROOT/"research_v2"/"results"/"runs"/f"{run_id}_full_pipeline";run_root.mkdir(parents=True,exist_ok=False)
    import torch, transformers, hashlib, platform, subprocess
    environment={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"git_commit":subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True).stdout.strip() or None,"python":platform.python_version(),"torch":torch.__version__,"transformers":transformers.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"input":args.input,"input_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"n_inputs":len(source_records),"seed":cfg["seed"],"device":"cuda:0","command":" ".join(sys.argv)}
    (run_root/"environment.json").write_text(json.dumps(environment,indent=2),encoding="utf-8")
    pairs=(("baseline","baseline"),("baseline","v2"),("v2","baseline"),("v2","v2")) if args.matrix else ((("baseline","baseline"),("v2","v2")) if args.stack=="both" else ((args.stack,args.stack),))
    gen_names=tuple(dict.fromkeys(x[0] for x in pairs))
    for gen_name in gen_names:
        local=dict(cfg);local["verification"]=dict(cfg["verification"]);local["generation"]=dict(cfg["generation"])
        if gen_name=="baseline":
            gen=StatuteGroundingGenerator(**{k:local["generation"][k] for k in ("model_id","quantization","device_map","max_new_tokens","do_sample","temperature","top_p","system_prompt","user_prompt_template")},seed=local["seed"]);gen.load()
        else:
            gen=Qwen3PipelineGenerator(local)
        gen=CachedGenerator(gen)
        local["generation"]["model_id"]=gen.model_id
        corrector=TimedCorrector(SelectiveCorrector(gen,local["correction"]["max_new_tokens"],local["correction"]["do_sample"],local["correction"]["system_prompt"]))
        # A is measured without a verifier resident, then the exact same
        # cached generation is reused by B/C for paired comparisons.
        a_records=[];a_dir=run_root/f"{gen_name}_A";a_dir.mkdir();a_started=time.perf_counter()
        with (a_dir/"predictions.jsonl").open("w",encoding="utf-8") as f:
            for r in source_records:
                case=SimpleNamespace(document_id=r["document_id"],case_text=r["case_text"])
                rec=pipeline.run_case(case,"A",gen,None,None,exact,usable,local);a_records.append(rec);f.write(json.dumps(rec,ensure_ascii=False)+"\n");f.flush()
        a_metrics=summarize(a_records);a_metrics.update({"generator":gen.model_id,"verifier":None,"condition":"A","runtime_seconds":time.perf_counter()-a_started,"dataset":args.input})
        (a_dir/"metrics.json").write_text(json.dumps(a_metrics,indent=2),encoding="utf-8")
        conditions=[{"condition":"A","metrics":a_metrics}]
        for verifier_name in tuple(dict.fromkeys(v for g,v in pairs if g==gen_name)):
            local["verification"]["model_id"]=("MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli" if verifier_name=="baseline" else "tasksource/ModernBERT-large-nli")
            if verifier_name=="baseline":
                verifier=NLIVerifier(local["verification"]["model_id"],0.70,local["verification"]["max_sequence_length"],device="cuda");verifier.load()
            else:verifier=ModernPipelineVerifier("cuda:0")
            timed_verifier=TimedVerifier(verifier)
            for mode in ("B","C"):
                import torch;torch.cuda.reset_peak_memory_stats()
                out=[];dest=run_root/f"{gen_name}_{verifier_name}_{mode}";dest.mkdir()
                raw=dest/"predictions.jsonl"
                condition_started=time.perf_counter()
                with raw.open("w",encoding="utf-8") as f:
                    for r in source_records:
                        case=SimpleNamespace(document_id=r["document_id"],case_text=r["case_text"])
                        before=len(timed_verifier.latencies)
                        result=pipeline.run_case(case,mode,gen,timed_verifier,corrector if mode=="C" else None,exact,usable,local)
                        result["research_v2_telemetry"]={"generation":gen.telemetry.get(case.case_text),"verification_latency_seconds":sum(timed_verifier.latencies[before:]),"correction_latency_seconds":corrector.telemetry.get(case.case_text)}
                        out.append(result);f.write(json.dumps(result,ensure_ascii=False)+"\n");f.flush()
                metrics=summarize(out);metrics.update({"generator_stack":gen_name,"verifier_stack":verifier_name,"condition":mode,"generator":gen.model_id,"verifier":verifier.model_id,"dataset":args.input,"input_sha256":__import__("hashlib").sha256(source.read_bytes()).hexdigest(),"runtime_seconds":time.perf_counter()-condition_started,"throughput_inputs_per_second":len(out)/(time.perf_counter()-condition_started) if out else None,"peak_gpu_memory_bytes":int(torch.cuda.max_memory_allocated()),"generation_records":sum(bool(r.get("generated_field")) for r in out)})
                (dest/"metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
                conditions.append({"condition":f"{gen_name}_{verifier_name}_{mode}","metrics":metrics})
            del verifier;gc.collect();torch.cuda.empty_cache()
        (run_root/f"{gen_name}_manifest.json").write_text(json.dumps({"generator_stack":gen_name,"inputs":len(source_records),"conditions":conditions,"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2),encoding="utf-8")
        del corrector,gen;gc.collect()
        import torch;torch.cuda.empty_cache()
    # Case-level paired comparison. Natural cases have no independent truth,
    # so disagreements are explicitly unlabeled and never counted as errors.
    comparisons=[]
    candidate_pairs=[("baseline_A","v2_A","generation_only"),
                     ("baseline_baseline_B","v2_v2_B","primary_generation_verification"),
                     ("baseline_baseline_C","v2_v2_C","primary_selective_correction")]
    if args.matrix:
        candidate_pairs += [("baseline_baseline_B","v2_baseline_B","generator_effect_with_deberta"),
                            ("baseline_v2_B","v2_v2_B","generator_effect_with_modernbert"),
                            ("baseline_baseline_B","baseline_v2_B","verifier_effect_qwen25"),
                            ("v2_baseline_B","v2_v2_B","verifier_effect_qwen3")]
    for left,right,name in candidate_pairs:
        lp=run_root/f"{left}"/"predictions.jsonl";rp=run_root/f"{right}"/"predictions.jsonl"
        if not lp.exists() or not rp.exists():continue
        lrows={x["document_id"]:x for x in (json.loads(z) for z in lp.read_text(encoding="utf-8").splitlines())}
        rrows={x["document_id"]:x for x in (json.loads(z) for z in rp.read_text(encoding="utf-8").splitlines())}
        rows=[]
        for did in sorted(lrows.keys()&rrows.keys()):
            l,r=lrows[did],rrows[did]
            rows.append({"document_id":did,"left_condition":left,"right_condition":right,"left_generated_text":l.get("generated_field",{}).get("text"),"right_generated_text":r.get("generated_field",{}).get("text"),
                         "left_final_text":l.get("final_field",{}).get("text"),"right_final_text":r.get("final_field",{}).get("text"),
                         "left_correction":l.get("correction"),"right_correction":r.get("correction"),
                         "left_verdicts":[c.get("verdict") for c in l.get("claims",[])],"right_verdicts":[c.get("verdict") for c in r.get("claims",[])],
                         "category":"both_agree" if [c.get("verdict") for c in l.get("claims",[])]==[c.get("verdict") for c in r.get("claims",[])] else "model_disagreement_ground_truth_unavailable"})
        comparisons.append({"comparison":name,"left":left,"right":right,"n_paired_inputs":len(rows),"n_changed_final_outputs":sum(x["left_final_text"]!=x["right_final_text"] for x in rows),"n_verdict_disagreements":sum(x["category"]!="both_agree" for x in rows),"interpretation":"Natural-data behavior comparison only; no ground truth."})
        (run_root/f"paired_{name}.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8")
    (run_root/"paired_comparison.json").write_text(json.dumps(comparisons,indent=2),encoding="utf-8")
    print(run_root);return 0
if __name__=="__main__":raise SystemExit(main())
