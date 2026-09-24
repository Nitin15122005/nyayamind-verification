#!/usr/bin/env python3
"""Load exact Qwen3 adapter and run a tiny deterministic smoke generation."""
from __future__ import annotations
import datetime, json, platform, subprocess, sys, time, traceback, warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research_v2.src.generation.qwen3_adapter import Qwen3Adapter,Qwen3Config,MODEL_ID

def main():
    import torch, transformers
    out=ROOT/"research_v2"/"results"/"sanity"/datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ_qwen3_smoke")
    out.mkdir(parents=True,exist_ok=False)
    config=Qwen3Config(device="cuda:0",allow_cpu_fallback=False,quantization="4bit_nf4",dtype="bfloat16",max_input_length=8192,max_new_tokens=32,temperature=1.0,top_p=1.0,do_sample=False,seed=42)
    if torch.cuda.is_available(): torch.cuda.reset_peak_memory_stats()
    captured=[]
    try:
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            adapter=Qwen3Adapter(config)
            captured=[str(w.message) for w in ws]
        generated=adapter.generate("State one reason statutory evidence must be checked before making a legal claim.")
        record={"status":"PASS","model_id":MODEL_ID,"model_revision":generated.get("model_revision"),"load_seconds":adapter._load_s,"config":generated["config"],"generation":generated,"runtime_id2label":None,"torch_version":torch.__version__,"transformers_version":transformers.__version__,"python":platform.python_version(),"cuda_version":torch.version.cuda,"gpu_name":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"peak_gpu_memory_bytes":int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None,"warnings":captured,"command":"py -3.11 research_v2/scripts/run_qwen3_smoke.py"}
    except Exception as exc:
        record={"status":"FAILED","model_id":MODEL_ID,"error_type":type(exc).__name__,"error":str(exc),"traceback":traceback.format_exc(),"torch_version":torch.__version__,"transformers_version":transformers.__version__,"python":platform.python_version(),"cuda_version":torch.version.cuda,"gpu_name":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"peak_gpu_memory_bytes":int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None,"warnings":captured,"command":"py -3.11 research_v2/scripts/run_qwen3_smoke.py"}
        (out/"result.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        print(json.dumps({"status":"FAILED","path":str(out),"error":record["error"]},indent=2));return 1
    (out/"result.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps({"status":"PASS","path":str(out),"model_id":MODEL_ID,"revision":record["model_revision"],"load_seconds":record["load_seconds"],"generation_seconds":generated["latency_seconds"],"peak_gpu_memory_bytes":record["peak_gpu_memory_bytes"],"warnings":captured},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
