# 16GB Laptop Memory Architecture Audit

_2026-09-11_

## Hardware/environment facts (measured, not assumed)

- System RAM: 15.7 GB total, 5.1-5.5 GB free during every prior loading
  failure and every recheck since (stable, not improving).
- GPU: NVIDIA RTX 4050 Laptop, 6141 MiB total VRAM, confirmed fully free
  (107 MiB used, 5814 MiB free) during the failures — **the bottleneck is
  host system RAM, not GPU VRAM.**
- Qwen2.5-7B-Instruct on-disk format: 4 safetensors shards,
  **3945441440 / 3864726352 / 3864726424 / 3556377672 bytes** (~3.7-3.9 GB
  each, bf16 weights). Confirmed via direct inspection of the HF cache
  (`~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/`).
- Libraries: `torch` 2.2.2+cu121, `transformers` 4.40.2, `accelerate`
  0.29.3, `bitsandbytes` 0.43.1.

## How the model is actually loaded (code, not guessed)

`src/generator.py::StatuteGroundingGenerator.load()`:

```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
    llm_int8_skip_modules=[],
)
self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
self._model = AutoModelForCausalLM.from_pretrained(
    self.model_id, quantization_config=bnb_config, device_map=self.device_map,
)
```

`device_map` comes from `config/prototype.yaml`'s `generation.device_map: {"": 0}`
(everything on GPU 0). `src/verifier.py::NLIVerifier.load()` loads
DeBERTa-v3-base (~184M params, ~350MB in fp16) separately, via plain
`from_pretrained(...).to(device)` — no quantization, much smaller, not a
meaningful contributor to the failures (all three failures happened during
**Qwen** loading, before the verifier was ever touched).

Answering the 10 audit questions directly:

1. **Loading dtype**: bf16 on disk, NF4 4-bit quantized in memory (the
   `bnb_4bit_compute_dtype` governs the *compute* dtype for dequantized
   matmuls, not the stored weight format).
2. **Device placement**: 100% GPU (`device_map={"": 0}`) — no CPU
   offloading configured.
3. **CPU/GPU placement**: as above; the CPU is only a transient staging
   area during `from_pretrained()`'s shard-by-shard load-then-quantize-
   then-transfer-to-GPU sequence.
4. **Multiple model instances**: No. `generator.load()` is called exactly
   once per script run; `corrector.py`'s `SelectiveCorrector` explicitly
   reuses the SAME loaded generator instance (confirmed in its own
   docstring and constructor, which takes `generator` as a parameter
   rather than loading its own copy) — there has never been a
   double-Qwen-load bug.
5. **Tokenizer/model duplication**: No duplication found.
6. **Generation workers/processes**: Single process, single thread of
   execution; `run_narrow_primary_hypothesis_gpu_ablation.py` processes
   cases in a plain Python `for` loop, no multiprocessing/threading.
7. **Batch size**: 1 (one case generated at a time; `max_new_tokens: 200`,
   `do_sample: False`).
8. **Previous model instances resident**: No — confirmed via `Get-Process`
   before each retry: zero stale `python.exe` processes were found between
   attempts, so nothing was piling up across the three tries.
9. **PyTorch caching contribution**: Plausible but unquantified — no
   explicit `gc.collect()`/`torch.cuda.empty_cache()` calls exist anywhere
   in the codebase before model loading, so any residual allocator-cached
   memory from `import torch`/CUDA context initialization is never
   explicitly released before the large `from_pretrained()` call.
10. **Existing memory-efficient inference support**: `low_cpu_mem_usage`
    is NOT explicitly passed to `from_pretrained()` anywhere in the
    codebase. Modern `transformers` (4.40.2) defaults this to `True`
    automatically **only when `device_map` is set** — which it is here —
    so it is very likely already active, but this is an implicit default,
    not an explicit, auditable guarantee, and is worth making explicit.

## Root cause (best evidence-based explanation)

Loading a single ~3.9 GB shard into CPU RAM as a staging step before
NF4-quantizing and transferring it to GPU, on a system with only 5.1-5.5 GB
free, consumes 70-77% of all currently-free memory for that one shard alone
— leaving very little headroom for Python/torch/CUDA-context overhead, the
quantization computation's own temporary buffers, the tokenizer, and normal
OS/background-process fluctuation. This is consistent with all three
observed failure points (shard 3/4, shard 1 not finishing, and shard 0
outright) being essentially random depending on exactly how much headroom
existed at that instant — not a deterministic function of case count (the
failures all happened before any case was processed).

## Conclusion

No code defect found. `low_cpu_mem_usage` is very likely already
implicitly active. The proximate cause is that this specific 7B model's
individual shard size (~3.9 GB) leaves too little headroom against this
specific machine's available free memory (~5.1-5.5 GB) for the transient
staging step `from_pretrained()` needs regardless of quantization target.
See `outputs/16gb_final_execution_report.md` for what legitimate,
model-identity-preserving mitigations were attempted and their results.
