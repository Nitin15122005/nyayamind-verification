"""Shared direct NLI benchmark runner. Importable as a script-local helper."""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, platform, subprocess, sys, time
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "prototype"))
sys.path.insert(0, str(ROOT))

from research_v2.src.evaluation.metrics import classification_metrics, mean

BASELINE_MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
V2_MODEL = "tasksource/ModernBERT-large-nli"

def _argparse(which):
    p = argparse.ArgumentParser(description=f"Run the frozen {which.upper()} benchmark")
    p.add_argument("--model", choices=("baseline", "v2"), required=True)
    p.add_argument("--device", default="cpu")
    p.add_argument("--run-id", default=None)
    return p.parse_args()

def _verifier(kind, device):
    if kind == "baseline":
        from src.verifier import NLIVerifier
        return NLIVerifier(model_id=BASELINE_MODEL, confidence_threshold=0.70,
                           max_sequence_length=512, device=("cuda" if device.startswith("cuda") else device)), BASELINE_MODEL
    try:
        from research_v2.src.verification.modernbert_verifier import ModernBertConfig, ModernBertVerifier
    except ImportError as exc:
        raise RuntimeError("research_v2 ModernBERT adapter is not yet available") from exc
    return ModernBertVerifier(config=ModernBertConfig(device=device)), V2_MODEL

def run(which):
    args = _argparse(which)
    evaluation = ROOT / "research" / "prototype" / "evaluation"
    if which == "gold01":
        fixture = evaluation / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl"
    else:
        fixture = evaluation / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl"
    records = [json.loads(x) for x in fixture.read_text(encoding="utf-8").splitlines() if x.strip()]
    if which == "gold01":
        for r in records:
            if "expected_label" not in r:
                raise ValueError(f"Missing gold label in {r.get('benchmark_id')}")
    else:
        # This frozen set is synthetic contradiction-by-construction, documented by the
        # source evaluation runner. Do not infer expected labels from model outputs.
        for r in records:
            if not r.get("original_synthetic_text") or not r.get("canonical_evidence_text"):
                raise ValueError("Malformed GOLD-02 record")
    verifier, model_id = _verifier(args.model, args.device)
    if hasattr(verifier, "load"):
        verifier.load()
    if which == "gold01":
        from src.verifier import format_premise
        examples = [{"id": r["benchmark_id"], "expected_label": r["expected_label"],
                     "premise": format_premise(r["evidence_text"], framing="labeled",
                         provision_type=r.get("provision_type"), provision_number=r.get("provision_number"),
                         act=r.get("act_name")), "hypothesis": r["hypothesis"], "source": r}
                    for r in records]
    else:
        from src.verifier import format_premise
        examples = [{"id": r["synthetic_claim_id"], "expected_label": "CONTRADICTED",
                     "premise": format_premise(r["canonical_evidence_text"], framing="labeled",
                         provision_type=(m.group(1) if (m := re.match(r"(Article|Section)\s+([^ ]+)\s+in\s+(.+)", r["evidence_id"], re.I)) else None),
                         provision_number=(m.group(2) if m else None), act=(m.group(3) if m else None)),
                     "hypothesis": r["original_synthetic_text"], "source": r}
                    for r in records]
    run_id = args.run_id or f"{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}_{which}_{args.model}"
    outdir = ROOT / "research_v2" / "results" / "runs" / run_id
    outdir.mkdir(parents=True, exist_ok=False)
    prediction_path=outdir/"predictions.jsonl"
    import torch
    if args.device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(torch.device(args.device))
    # Same three warm-up pairs for each verifier; warm-up is excluded from the
    # reported measurement. It initializes kernels and avoids cold-start bias.
    for ex in examples[:3]:
        verifier.verify(ex["premise"], ex["hypothesis"])
    if args.device.startswith("cuda"):
        torch.cuda.synchronize(torch.device(args.device))
    predictions, elapsed = [], 0.0
    with prediction_path.open("w",encoding="utf-8") as raw_file:
        for ex in examples:
            start = time.perf_counter()
            out = verifier.verify(ex["premise"], ex["hypothesis"])
            if args.device.startswith("cuda"):
                torch.cuda.synchronize(torch.device(args.device))
            duration = time.perf_counter() - start
            elapsed += duration
            label = getattr(out, "label", None)
            confidence = getattr(out, "confidence", None)
            raw_scores = getattr(out, "raw_scores", None)
            if isinstance(out, dict):
                label = out.get("normalized_verdict", out.get("label", label)); confidence = out.get("confidence", confidence)
                raw_scores = out.get("probability_distribution", out.get("probabilities", out.get("raw_scores", raw_scores)))
            token_lengths = (out.get("token_lengths") if isinstance(out, dict) else None)
            if token_lengths is None and getattr(verifier, "_tokenizer", None) is not None:
                token_lengths = {"original_pair_tokens": len(verifier._tokenizer(ex["premise"], ex["hypothesis"])["input_ids"])}
            prediction={"id": ex["id"], "expected_label": ex["expected_label"],
                "predicted_label": label, "confidence": confidence, "probabilities": raw_scores,
                "low_confidence": (out.get("sub_reason") == "low_confidence" if isinstance(out, dict) else getattr(out, "sub_reason", None) == "low_confidence"),
                "latency_seconds": duration, "premise": ex["premise"],
                "hypothesis": ex["hypothesis"], "model_id": model_id,
                "model_revision": (out.get("model_revision") if isinstance(out, dict) else None) or getattr(verifier, "model_revision", None),
                "input_truncated": (getattr(out, "input_truncated", None) if not isinstance(out, dict)
                                    else (out.get("token_lengths") or {}).get("truncated")),
                "token_lengths": token_lengths,"source": ex["source"]}
            predictions.append(prediction);raw_file.write(json.dumps(prediction,ensure_ascii=False)+"\n");raw_file.flush()
    metrics = classification_metrics([x["expected_label"] for x in predictions],
                                     [x["predicted_label"] for x in predictions])
    try:
        import transformers
        transformers_version = transformers.__version__
    except Exception:
        transformers_version = None
    gpu_peak = (int(torch.cuda.max_memory_allocated(torch.device(args.device)))
                if args.device.startswith("cuda") and torch.cuda.is_available() else None)
    gpu_name = (torch.cuda.get_device_name(torch.device(args.device))
                if args.device.startswith("cuda") and torch.cuda.is_available() else None)
    confs=sorted(float(x["confidence"]) for x in predictions if x["confidence"] is not None)
    def quantile(q):
        if not confs:return None
        pos=(len(confs)-1)*q;lo=int(pos);hi=min(lo+1,len(confs)-1)
        return confs[lo]+(confs[hi]-confs[lo])*(pos-lo)
    metrics.update({"benchmark": which, "stack": args.model, "model_id": model_id,
                    "dataset_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                    "dataset_path": str(fixture.relative_to(ROOT)), "elapsed_seconds": elapsed,
                    "mean_latency_seconds": mean([x["latency_seconds"] for x in predictions]),
                    "throughput_examples_per_second": len(predictions) / elapsed if elapsed else None,
                    "confidence_mean": mean([x["confidence"] for x in predictions]),
                    "confidence_distribution":{"n":len(confs),"min":min(confs) if confs else None,"p10":quantile(.10),"p25":quantile(.25),"median":quantile(.50),"p75":quantile(.75),"p90":quantile(.90),"max":max(confs) if confs else None,"histogram":{"0.00-0.50":sum(x<.5 for x in confs),"0.50-0.70":sum(.5<=x<.7 for x in confs),"0.70-0.90":sum(.7<=x<.9 for x in confs),"0.90-1.00":sum(x>=.9 for x in confs)}},
                    "low_confidence_rate": sum(x["low_confidence"] for x in predictions) / len(predictions),
                    "truncation_count": sum(bool(x["input_truncated"]) for x in predictions),
                    "peak_gpu_memory_bytes": gpu_peak, "gpu_name": gpu_name,
                    "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
                    "transformers_version": transformers_version,
                    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "python": platform.python_version(), "device": args.device,
                    "confidence_threshold": 0.70,
                    "model_revision": getattr(getattr(getattr(verifier, "model", None), "config", None), "_commit_hash", None) or getattr(getattr(getattr(verifier, "_model", None), "config", None), "_commit_hash", None) or getattr(verifier, "model_revision", None),
                    "label_mapping": getattr(verifier, "id2label", None) or getattr(verifier, "_id2label_lower", None),
                    "max_sequence_length": getattr(verifier, "max_sequence_length", None) or getattr(getattr(verifier, "config", None), "max_position_length", None),
                    "warmup_examples": min(3, len(examples)),
                    "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                        capture_output=True, text=True).stdout.strip() or None,
                    "command": " ".join(sys.argv)})
    (outdir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "environment.json").write_text(json.dumps({k:metrics[k] for k in ("timestamp_utc","git_commit","python","torch_version","transformers_version","cuda_version","gpu_name","device","model_id","model_revision","command")}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"run_dir": str(outdir), "metrics": metrics}, indent=2))
    return 0
