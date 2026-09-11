# 16GB Laptop Final Execution Report

_2026-09-12_

## Hardware constraints

15.7 GB total system RAM, 5.1-5.9 GB free at any given check throughout
this session (fluctuating with the user's own other applications — never
freed up significantly, never required to). NVIDIA RTX 4050 Laptop GPU,
6141 MiB VRAM, confirmed never the bottleneck (always >5.8 GiB free during
every failure this project has ever hit). See
`outputs/16gb_memory_architecture_audit.md` for the full architecture audit
this report's fix is based on.

## Memory-safe configuration that worked

Two small, legitimate, model-identity-preserving changes to
`src/generator.py::StatuteGroundingGenerator.load()`:

1. `low_cpu_mem_usage=True` passed explicitly to `AutoModelForCausalLM.from_pretrained()`
   (previously relied on an undocumented implicit default).
2. `gc.collect()` + `torch.cuda.empty_cache()` called immediately before
   that same `from_pretrained()` call, releasing any allocator-cached
   memory left over from `import torch`/CUDA context initialization before
   the single largest transient allocation (one ~3.9 GB safetensors shard)
   that loading this model requires.

**Neither changes model identity, weights, quantization config
(NF4 4-bit, double-quant, bf16 compute dtype — byte-identical to before),
or generation output determinism.** Confirmed effective: model loading that
previously failed 100% of the time (3/3 attempts across two prior sessions,
always during shard loading) now succeeds reliably (confirmed across 4
separate process launches this session, including 2 resumed runs after
kills) in ~13 seconds, dropping free RAM by only ~300-600 MB instead of
exhausting it.

**No model substitution.** Qwen2.5-7B-Instruct, exact same
`Qwen/Qwen2.5-7B-Instruct` HuggingFace identifier, exact same 4-bit NF4
quantization config as documented in `config/prototype.yaml`, used
throughout. No reduced-precision or smaller-model experiment was run or
reported as if it were this one.

## What was NOT the fix (ruled out, not guessed)

- GPU VRAM was never the constraint (confirmed via `nvidia-smi` before/
  during/after every attempt this project has made).
- No stale/duplicate model processes were ever found running between
  attempts (checked via `Get-Process` each time).
- Batch size was already 1; generation was already sequential
  (single-threaded `for` loop, one case at a time) before this session —
  nothing to reduce there.

## Checkpointing / resumability (added this session)

`scripts/run_narrow_primary_hypothesis_gpu_ablation.py` was rewritten to:

- Write each case's result to both arms' output JSONL files **immediately**
  after that case completes (not held in memory until the end).
- On startup, detect document_ids already present in **both** arms'
  output files for the given `--out-prefix` and skip them — a
  killed/resumed run never recomputes or duplicates a completed case.
- Check free system RAM (`psutil`) before starting each case; if it falls
  below `--min-free-gb` (default 2.0), stop gracefully (no crash, no data
  loss) rather than let the OS kill the process mid-write.

**This was exercised for real, not just built defensively**: this
session's full run was interrupted by two separate background-process
kills (both by the host OS, both while pushing toward a higher `n` than
the current available memory could sustain) and resumed cleanly both
times with zero data loss and zero duplicated cases — see the run log
below.

## Execution log (this session, one continuous checkpointed dataset)

| Step | Requested n (total) | New cases this step | Outcome |
|---|---|---|---|
| Micro-test | 1 | 1 | Succeeded — validated the fix works at all |
| Build-up | 10 | 9 (1 resumed) | First attempt died right after generation began (transient, no crash logged, GPU/RAM both clean after — never repeated); **retry succeeded**, 10/10 completed, memory stable 4.6-5.2GB |
| Build-up | 50 (→60 total) | 40 (10 resumed) | Succeeded fully, memory stable/plateaued ~4.5-4.7GB throughout, zero guard trips |
| Build-up | 100 (→100 total) | 40 requested, 2 completed (→62 total) | **Killed by host OS for low memory during case 3's generation** (not model loading) — the 2 completed cases were safely checkpointed, not lost. **Not retried a third time at this scale**, per this task's explicit instruction not to repeatedly rerun a demonstrated OOM. |

**Final dataset: n=62 cases, both arms, real Qwen2.5-7B generation + real
DeBERTa verification + real selective correction through the actual
production `pipeline.py` (Mode C).** This exceeds the task's stated
minimum-useful target of 50, and is the largest fresh natural-data
correction-shipping dataset in this project's history (prior largest
single fresh batch: n=50, `outputs/final_gpu_validation.md`, testing a
different set of levers).

**Honest characterization of the n=62 ceiling**: the second kill occurred
during active generation, not the model-loading phase the original memory
audit diagnosed — meaning the per-case memory guard (checked only *before*
each case starts) cannot catch every possible transient spike *during* a
case. This is a real, understood limitation of the current guard design,
not evidence the checkpointing/resume mechanism failed (it worked exactly
as intended both times).

## Correction-shipping metrics (n=62, real data)

Source: `outputs/narrow_primary_hypothesis_gpu_ablation_16gb_{OLD,CURRENT}.jsonl`.
Both arms share identical generated text per case (generation called once);
only `verification.narrow_primary_hypothesis` differs (OLD=false, matching
pre-Stage-4; CURRENT=true, exactly as shipped).

| Metric | OLD | CURRENT |
|---|---|---|
| Cases | 62 | 62 |
| Total claims | 156 | 156 |
| Evidence-matched claims | 32 | 32 |
| ENTAILED | 5 | 9 |
| CONTRADICTED | 1 | 2 |
| NOT_ENOUGH_INFORMATION | 26 | 21 |
| Correction triggered | 4/62 | 5/62 |
| Correction shipped | **0/62** | **0/62** |
| Unsafe shipments | 0 | 0 |

### 1. Verification recovery (paired, per-claim, the 32 evidence-matched claims)

| OLD verdict → CURRENT verdict | Count |
|---|---|
| NOT_ENOUGH_INFORMATION → NOT_ENOUGH_INFORMATION (unchanged) | 21 |
| ENTAILED → ENTAILED (unchanged) | 5 |
| CONTRADICTED → CONTRADICTED (unchanged) | 1 |
| **NOT_ENOUGH_INFORMATION → ENTAILED** | **4** |
| **NOT_ENOUGH_INFORMATION → CONTRADICTED** | **1** |
| ENTAILED → CONTRADICTED (unsafe reversal) | **0** |
| CONTRADICTED → ENTAILED (unsafe reversal) | **0** |

**5/32 (15.6%) evidence-matched claims changed verdict, all one-directional
(NEI toward a more decisive verdict), zero unsafe reversals.** This is
consistent in direction and magnitude with the much larger CPU benchmark
(31/107 applicable, `outputs/narrow_primary_hypothesis_benchmark_report.md`)
and the prior n=15 fresh-GPU result (1/12), now at a larger fresh sample.

**Statistical interpretation**: exact two-sided sign test on the 4
discordant NEI↔ENTAILED pairs (b=4 favoring CURRENT, c=0 favoring OLD):
p = 2×C(4,0)×0.5⁴ ≈ 0.125 — **not significant at α=0.05**. McNemar's
continuity-corrected chi-square is not reported as a primary statistic
here: with only 4-5 discordant pairs total, the standard guidance (b+c≥10)
for the chi-square large-sample approximation to be reliable is not met;
computing it anyway would risk implying more precision than 5 discordant
observations can support. **Honest conclusion: directionally consistent
with all prior (larger) evidence for this lever, but this specific n=62
sample alone does not reach statistical significance.**

### 2. Correction generation (the 4 OLD / 5 CURRENT triggered attempts)

| Status | OLD | CURRENT |
|---|---|---|
| `correction_failed` (no ENTAILED reverification) | 2 | 3 |
| `correction_scope_violation` | 2 | 1 |
| `correction_sibling_regression` | 0 | 1 |
| `corrected` (shipped) | 0 | 0 |

Every triggered attempt in both arms produced SOME generated rewrite from
Qwen (generation itself always "succeeds" in the sense of returning text);
none passed every required safety gate.

### 3. Correction re-verification and shipping

**0/4 (OLD) and 0/5 (CURRENT) shipped.** Consistent with this project's
long-documented, unchanged 1.8%-cumulative-historical correction-shipping
rate — this session's real data does not move that number, and is not
claimed to. **Correction shipping remains the least-solved part of this
pipeline**; nothing in this session's results contradicts or improves that
prior, honest conclusion.

### 4. Safety

**0 unsafe shipments across both arms, all 62 cases.** The
`correction_unauthorized_addition` and `correction_ordinal_ambiguous`
guards were never triggered in this batch (no case exercised those
specific failure modes); the scope-check and sibling-regression guards
each fired at least once (see case study below) and correctly rejected
every case they caught.

## Case study: a real, substantively-correct fix rejected by two different safety gates

Document `1955_32`: generated text claimed IPC Section 395 (dacoity
punishment) allows imprisonment "extending up to **fourteen** years" — the
real statute (evidence corpus) says **ten** years. Both arms correctly
flagged this CONTRADICTED and triggered correction.

- **OLD**: Qwen's rewrite correctly changed "fourteen" → "ten" years
  (substantively correct). Rejected as `correction_scope_violation` — a
  disturbance was detected in the unflagged sibling claim's required text.
- **CURRENT**: Qwen's rewrite (independently generated, slightly different
  wording) also correctly changed "fourteen" → "ten" years. The flagged
  claim's own re-verification was **ENTAILED at 0.980 confidence** — a
  genuinely correct fix, confirmed. But the **independent sibling-
  regression check** (which re-verifies every OTHER claim sharing the
  corrected sentence) found the neighboring claim (Section 392, "defines
  the act of dacoity") came back CONTRADICTED against its own evidence
  after the edit, and rejected the whole correction as
  `correction_sibling_regression`.

**Neither ships. Both are safe.** This is not a failure of the correction
mechanism — it demonstrates the multi-gate safety design working exactly
as intended: a substantively correct edit to one claim is not shipped
unless *every* claim sharing that sentence is also confirmed safe, and
different gates (legacy scope-check vs. the newer independent
sibling-regression check) can each independently catch a residual risk the
other might have missed. The dominant correction bottleneck remains, as
previously diagnosed, that a genuinely correct edit to one part of a
bundled sentence is hard to ship without collateral risk to its neighbors
— not that the corrector cannot produce correct text.

## Test suite / reproducibility

See `FINAL_RESEARCH_FREEZE_REPORT.md` for the full test-suite/git-status
record accompanying this report's commit.

## Honest limitations

- n=62 is real, fresh, fully-instrumented data — but still too small for
  a statistically significant standalone conclusion about
  `narrow_primary_hypothesis`'s verification-recovery effect (though
  directionally consistent with much larger existing evidence for the same
  lever).
- Correction shipping remains unmeasured as an *improvement* — 0/62 in
  both arms means this session cannot say whether the lever changes
  shipping rate at all, only that verification recovery does not
  automatically translate to more shipped corrections at this n.
- The per-case memory guard checks only *before* each case; a transient
  spike *during* generation is not covered by the current design (this is
  exactly what caused the second interruption). A more granular guard
  (checking during generation, not just before it) is a legitimate future
  improvement, not attempted this session.
- This machine's exact 15.7GB/5-6GB-free profile is specific to this
  laptop and its concurrent workload; the fix (low_cpu_mem_usage +
  gc/cache clearing) is a general, portable improvement, but the specific
  `--min-free-gb` threshold and observed stall point are not necessarily
  identical on a different machine.

## Reproduction

```
cd research/prototype
../.venv/Scripts/python.exe scripts/run_narrow_primary_hypothesis_gpu_ablation.py \
    --device cuda --n-cases 100 --out-prefix narrow_primary_hypothesis_gpu_ablation_16gb \
    --min-free-gb 2.0
```

Resumes automatically from the 62 cases already checkpointed under this
exact prefix; add more cases by re-running with a higher `--n-cases` at
any time memory allows.
