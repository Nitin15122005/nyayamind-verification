# Final Reproducibility Matrix — STEP 11

Supersedes `evaluation/archive/REPRODUCIBILITY_MATRIX.md` (STEP 8, written before GPU
capability existed on any machine in this project's history; moved to `evaluation/archive/`
unedited in the PASS 2 cleanup) — that file is left unedited as the accurate record of
STEP 8's own knowledge; this matrix reflects the current, post-STEP-10B status. "CPU
reproduced" and "GPU reproduced" record whether
*this workspace* (STEP 1-11) independently re-executed the result, not whether the
original historical result itself used CPU or GPU.

| Experiment | CPU reproduced | GPU reproduced | Historical-only | Not recoverable | Status |
|---|---|---|---|---|---|
| GOLD-01 controlled benchmark (n=420, bare+labeled) | Yes (STEP 4, bit-for-bit) | N/A (DeBERTa-only, no Qwen involved) | No | No | Fully reproduced |
| GOLD-02 synthetic stress (n=59, bare+labeled) | Yes (STEP 4, to stated precision) | N/A (DeBERTa-only) | No | No | Fully reproduced |
| 588-claim natural aggregate (evidence coverage + verdicts) | Yes (STEP 6, bit-for-bit) | N/A (re-verification only; underlying text is historical Qwen output) | Partially (underlying generated text not regenerated) | No | CPU-side fully reproduced; generation not re-attempted (not required — text unchanged) |
| 209-claim paired evidence coverage (v0 vs v0+v1) | Yes (STEP 6, CPU re-matching/re-verification, exact) | **Yes (STEP 10B, exact — full re-generation of all 209 claims across 50 cases)** | No | No | **Fully reproduced, both CPU and GPU layers** |
| Component test suite (205 tests, 7 groups) | Yes (every step, STEP 2-11) | Yes (STEP 10/10B, identical 205/205 on the GPU machine too) | No | No | Fully reproduced on both machines |
| Claim parser fix statistic (n=30 sign test) | Yes (STEP 7, statistic only, exact match) | N/A | Yes (the underlying code change itself; pre-fix parser not re-executed) | No | Statistic reproduced; code-change history not re-executed (by design, not a gap) |
| Atomic scope-check replay (n=11) | Yes (STEP 7, exact match) | N/A (pure Python replay, no model) | No | No | Fully reproduced |
| Confidence-threshold sensitivity sweep | Yes (STEP 7, recomputed from stored sweep) | N/A | Yes (original sweep itself not re-run; descriptive replay only) | No | Replay reproduced; original sweep not re-executed (not required) |
| Real Qwen generation (minimal, mode A n=1) | N/A (impossible on STEP 1-9 machine, CUDA-required by design) | **Yes (STEP 10, first-ever execution of this exact invocation — no historical comparator exists)** | No | No | Freshly executed; no reproduction claim possible (nothing to compare against) |
| Real correction pipeline (mode C smoke test, n=5) | N/A | **Yes (STEP 10, first-ever execution at this exact scope)** | No | No | Freshly executed; no reproduction claim possible |
| Targeted labeled-framing correction validation (n=10) | N/A (GPU-dependent, real Qwen correction calls) | **Yes (STEP 10, exact — byte-identical corrected text, identical status counts)** | No (fully reproduced) | No | **Fully reproduced on GPU** |
| 209-claim two-arm GPU generation experiment (the source of `final_gpu_validation_{A,B}.jsonl`) | N/A (generation is GPU-only by design) | **Yes (STEP 10B, exact — byte-identical text for all 50 cases, identical every metric)** | No (fully reproduced) | No | **Fully reproduced on GPU** |
| Cumulative correction rate (1/56, project history) | No | No | Yes | **Yes — protocol insufficient** | **Not recoverable**: pooled rollup, source script never committed, no per-constituent breakdown survives |
| Synthetic correction funnel (labeled 26/36, bare 0/30) | No (GPU-dependent Qwen correction calls, not re-executed this project) | No (not re-attempted in STEP 10/10B — out of scope) | Yes | No (a protocol exists — `scripts` referenced in `outputs/final_metrics.json` — simply not re-run) | Historical-only, not attempted (in scope for a possible future step, not blocked) |
| Narrow re-verification (n=3) | No | No | Yes | Yes — narrative-only, not re-derivable from raw per-case data without ambiguity | Not recoverable as a re-derivable dataset |
| Joint four-lever isolation | No | No | No experiment ever existed | Yes — no protocol, no baseline, no dataset defined anywhere | **Does not exist; none invented** |

## Legend

- **CPU reproduced**: this workspace independently re-executed the CPU-only portion
  (evidence matching, DeBERTa verification, or deterministic replay logic) and the
  result matched the historical figure to the documented precision.
- **GPU reproduced**: this workspace independently re-executed a GPU-dependent
  portion (Qwen generation and/or correction) on real CUDA hardware and the result
  matched the historical figure exactly.
- **Historical-only**: a result exists only from a prior (uncontested, not
  re-executed) run; this workspace did not attempt to re-derive it.
- **Not recoverable**: re-derivation was actively investigated and found impossible
  with the artifacts currently in the repository (missing script, missing
  per-constituent data, or no protocol ever defined) — distinct from "not attempted."

## Summary

Of the GPU-dependent experiments with a **recoverable, well-specified protocol**,
every one has now been freshly and exactly reproduced: the targeted correction
validation (STEP 10) and the 209-claim two-arm generation experiment (STEP 10B).
The synthetic correction funnel has a recoverable protocol but was not re-attempted
in STEP 10/10B (out of scope, not blocked — a candidate for a future step, not a
current gap in this reconciliation). Only two items are genuinely **not
recoverable**: the pooled cumulative 1/56 figure and the narrow re-verification
narrative. The joint four-lever experiment was never designed at all — there is
nothing to recover.
