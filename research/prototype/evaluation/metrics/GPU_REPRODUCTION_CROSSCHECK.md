# STEP 10 — GPU Reproduction Crosscheck

Classification taxonomy (as specified for this step): A = exact reproduction,
B = matches within documented precision, C = statistically/meaningfully
different, D = execution succeeded but comparison impossible, E = historical
configuration insufficiently specified, F = experiment failed.

## Experiment 1: Labeled-framing targeted correction validation (GPU)

- **Historical source**: `scripts/run_labeled_correction_validation_gpu.py`,
  run 2026-08-27, results in `outputs/labeled_correction_validation_gpu_metrics.json`
  and `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl`.
- **Fresh source (STEP 10)**: `evaluation/actual_outputs/gpu_correction_rerun/rerun_labeled_correction_validation_gpu.py`
  — a copy of the historical script with only its two output paths redirected
  (never touches the original `outputs/*.json(l)` files). Same config
  (`use_evidence_v1=true`, `premise_framing=labeled`,
  `atomic_scope_check="assertion_spans"`, `narrow_reverification_hypothesis=true`,
  `confidence_threshold=0.70`), same inputs (`outputs/final_gpu_validation_B.jsonl`,
  `outputs/final_validation_bare_vs_labeled_cpu_claims.jsonl`, both read-only,
  unmodified), same model (`Qwen/Qwen2.5-7B-Instruct`, 4-bit nf4), same seed (42),
  `do_sample=false` (greedy/deterministic).
- **Fresh outputs**: `evaluation/actual_outputs/gpu_correction_rerun/labeled_correction_validation_gpu_metrics.fresh.json`,
  `..._corrections_detail.fresh.jsonl`.

| Metric | Historical | Fresh (STEP 10) | Match |
|---|---|---|---|
| Cases triggered | 10 | 10 | Yes — identical document/claim IDs, identical order |
| `status_counts` | `{correction_scope_violation: 3, correction_failed: 6, corrected: 1}` | `{correction_scope_violation: 3, correction_failed: 6, corrected: 1}` | Yes, exact |
| Corrections shipped | 1 | 1 | Yes |
| Unsafe shipped | 0 | 0 | Yes |
| Per-case `regenerated_text` | — | — | **Byte-for-byte identical for all 10 cases** (verified programmatically, string equality, 10/10) |
| Runtime | 84.9s | 104.8s | Different (see below) |

**Classification: A — exact reproduction.**

Every case-level status and every generated character of every correction
attempt matches the historical run exactly, including the single case that
shipped (`2003_760`/`c3`) and the three that were correctly rejected for
touching unflagged text (`correction_scope_violation`). This is consistent
with `do_sample=false` (greedy decoding): given the identical model revision,
identical quantization, identical prompt, and identical seed, byte-identical
output is the expected result, not a coincidence — this run is direct
evidence that the two machines' bitsandbytes/CUDA/transformers stack produce
identical generation results for this model and config.

**Runtime difference (84.9s historical vs. 104.8s fresh, +23%)**: expected
and not investigated further as a discrepancy — wall-clock generation time is
a hardware/thermal/background-load measure, not a correctness measure, and
this step's own hardware discovery (Phase 2) does not establish that the
historical run used identical hardware, only that the *production code*
targets "this RTX 4050 6GB machine" per `src/generator.py`'s own docstring.
No claim of hardware identity is made; only output identity is claimed.

## Experiment 2: Single real generation (mode A, n=1) and mode-C smoke test (n=5)

No directly comparable historical run exists at exactly this scope (n=1 mode
A, n=5 mode C on these specific `document_id`s) — `README.md`'s own "How to
run the first real case" section documents the *command* but STEP 1-9's
PROVENANCE explicitly records that command was never executed (no GPU).
Classification: **D — execution succeeded but comparison impossible** (there
is nothing to compare against; this is the first execution of these exact
invocations on any machine per this project's committed history). Treated as
a fresh validation run, not a reproduction.

## Experiment 3 (STEP 10B): 209-claim paired evidence-v0-vs-v1 generation experiment

- **Historical source**: `scripts/run_final_gpu_validation.py`, run
  2026-08-27, results in `outputs/final_gpu_validation_metrics.json`,
  `_A.jsonl`, `_B.jsonl`, `_corrections_detail.jsonl`.
- **Confirmed genuinely distinct from STEP 6**: `evaluation/scripts/run_natural_209_paired_evaluation.py`'s
  own docstring states it only re-reads the ORIGINALLY-STORED verdicts in
  `final_gpu_validation_A.jsonl`/`_B.jsonl` and performs fresh CPU-only
  re-evidence-matching + DeBERTa re-verification — "No Qwen generation or
  correction is invoked." The GPU-dependent work that STEP 6 never touched
  is the original generation run itself (50 real Qwen generations + up to 10
  real Qwen correction calls) that produced those two `.jsonl` files. STEP
  10B reproduces exactly that generation run, not STEP 6's CPU re-analysis.
- **Fresh source (STEP 10B)**: `evaluation/scripts/run_gpu_209_reproduction.py` —
  a copy of the historical script, logic byte-identical, with exactly two
  changes: (1) fresh outputs redirected to
  `evaluation/actual_outputs/gpu_209_reproduction/` instead of
  `research/prototype/outputs/` (which is left completely untouched — no
  file there was read for writing, only for reading the pre-existing
  candidate-ID list), and (2) a `reproducibility_metadata` block (git
  commit, torch/CUDA/driver versions, GPU name, SHA-256 of every input
  dataset file, exact command, wall-clock start/end) appended to the output
  metrics JSON. Same candidate file
  (`natural_candidate_selected_ids_50_final_validation.json`, read-only,
  unmodified, SHA-256 `954380e7695ceead984d67e7029186074a9ffd95130f02d17b01ea08d9877f9a`),
  same seed (42), same two arm configs (A = on-disk `config/prototype.yaml`
  defaults, deep-copied, never written; B = in-memory deep copy with
  `use_evidence_v1=true`, `atomic_scope_check="assertion_spans"`,
  `narrow_reverification_hypothesis=true`), same models
  (`Qwen/Qwen2.5-7B-Instruct` 4-bit nf4, `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`),
  `do_sample=false` (greedy/deterministic).
- **Fresh outputs**: `evaluation/actual_outputs/gpu_209_reproduction/step10b_final_gpu_validation_{metrics.json,A.jsonl,B.jsonl,corrections_detail.jsonl}`,
  plus `run.console.log` (full stdout).
- **Runtime**: 1539.2s total fresh (25.7 min) vs. 2040.9s historical (34.0
  min) — fresh was *faster*, not slower, this time (opposite direction from
  Experiment 1's +23%); consistent with wall-clock generation time being a
  hardware/thermal/background-load measure, not investigated further.
  Generation-only: 1252.2s fresh vs. 1662.8s historical.

| Metric | Historical (Arm A / Arm B) | Fresh (Arm A / Arm B) | Match |
|---|---|---|---|
| `n_claims_shared_generation` | 209 | 209 | Yes, exact |
| Claims evidence-matched | 132 / 147 | 132 / 147 | Yes, exact |
| `evidence_match_method_counts` | `{exact_normalized:130,no_evidence:77,fuzzy:2}` / `{exact_normalized:145,no_evidence:62,fuzzy:2}` | identical | Yes, exact |
| `verdict_counts` | `{NEI:129,NO_EVIDENCE:77,CONTRADICTED:3}` / `{NEI:144,NO_EVIDENCE:62,CONTRADICTED:3}` | identical | Yes, exact |
| `confidence_summary` (mean/median/min/max) | A: 0.9603013/0.9892578/0.5209961/0.9990234; B: 0.9618975/0.9892578/0.5209961/0.9990234 | identical to all digits shown | Yes, exact |
| Correction triggers | 5 / 5 | 5 / 5 | Yes |
| Corrections shipped | 0 / 0 | 0 / 0 | Yes |
| `correction_failed` / `correction_scope_violation` | 3+2 / 3+2 | 3+2 / 3+2 | Yes |
| `unsafe_corrections_shipped` | 0 / 0 | 0 / 0 | Yes |
| `peak_vram_mib` | 7547 | 7547 | Yes, exact (same figure) |
| Per-case generated text (all 50 cases, both facts checked programmatically) | — | — | **Byte-for-byte identical for all 50/50 cases** (string equality, verified in code, 0 mismatches) |

**Classification: A — exact reproduction.**

This is the strongest possible reproduction result available under this
project's methodology: every claim count, every evidence match, every
verdict, every confidence statistic (to the precision stored), every
correction outcome, and the raw generated text of all 50 cases are
bit-for-bit identical between the 2026-08-27 historical run and this
2026-09-05 fresh run, on two different physical machines (per STEP 10's own
finding that STEP 1-9's machine was GPU-less; the historical run's machine
identity is not independently confirmed, only that production code targets
"this RTX 4050 6GB machine" per `src/generator.py`'s docstring, and this
machine matches that GPU model/VRAM class). Under greedy decoding
(`do_sample=false`) with an identical model revision, identical 4-bit
quantization config, and an identical prompt/seed, exact reproduction is the
expected outcome of a correctly-functioning pipeline — this result is
evidence the production generation/verification/correction path is stable
across machines, not evidence of anything about legal correctness.

Historical files (`outputs/final_gpu_validation_metrics.json`, `_A.jsonl`,
`_B.jsonl`, `_corrections_detail.jsonl`) were verified untouched: file
mtimes remain `2026-08-27`, SHA-256 hashes unchanged from before this run.

## Cumulative correction rate (1/56) — PROTOCOL INSUFFICIENT, not attempted

`outputs/final_metrics.json`'s `section_D_correction_safety_cumulative`
(`total_correction_attempts: 56, total_shipped: 1, total_unsafe_shipped: 0`)
is **not a single experiment** and has no recoverable single reproduction
protocol:

- Its own `provenance` field states it was computed by "this session's
  build_final_metrics analysis" — an ad-hoc, never-committed script. A
  repository-wide search found no such script anywhere (only
  `evaluation/scripts/build_ablation_analysis.py` line ~379, which *loads* the
  already-computed JSON — it does not recompute it).
- The `56` is a pooled rollup across the project's entire historical
  correction-experiment population (at minimum: synthetic bare/labeled
  corrections from `framing_comparison_gpu_n59_postfix_metrics.json`,
  natural-targeted and natural-batch experiments, the 209-claim experiment
  reproduced above, and the labeled-correction-validation experiment already
  reproduced in STEP 10) — but `section_D_correction_safety_cumulative`
  itself carries no per-constituent breakdown, so the exact set and
  per-experiment counts that sum to 56 cannot be reconstructed from this
  file alone with certainty.
- Reconstructing it honestly would require freshly re-running *every*
  GPU-dependent correction experiment in the project's history and re-
  summing — not a bounded validation task, and explicitly out of scope for
  STEP 10B (which asks to reproduce only where the protocol is sufficiently
  specified).

**Classification: PROTOCOL INSUFFICIENT.** Not attempted. Not failed. The
two correction populations STEP 10/10B *did* freshly reproduce (5-trigger
209-claim experiment above, 10-case targeted-correction experiment in
Experiment 1) are each individually exact matches to their own historical
counterparts, which is the strongest evidence available that the
*constituent* experiments are stable/reproducible — but this does not
license reconstructing the pooled 56-attempt total, which remains
HISTORICAL ONLY.
