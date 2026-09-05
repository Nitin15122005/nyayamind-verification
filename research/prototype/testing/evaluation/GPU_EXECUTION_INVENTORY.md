# STEP 10 — GPU Execution Inventory

Derived directly from `src/generator.py`, `src/corrector.py`, `src/verifier.py`,
`src/pipeline.py`, and `config/prototype.yaml` as they exist at commit `4e221ba`
(see `PROVENANCE.md` STEP 10 section for the full commit/environment record).
This is not the example list from the STEP 10 instructions — every row below was
found by reading the actual source.

| Operation | Source Function | Model | GPU Required | Historical Evidence | Fresh Status (STEP 10) |
|---|---|---|---|---|---|
| Statutory-grounding generation | `StatuteGroundingGenerator.load()` / `.generate()` (`src/generator.py:65,107`) | `Qwen/Qwen2.5-7B-Instruct`, 4-bit nf4 bitsandbytes | Yes — `load()` raises `RuntimeError` if `torch.cuda.is_available()` is False (`src/generator.py:71-77`), by design, no CPU fallback | `outputs/final_gpu_validation_{A,B}.jsonl` (209-claim paired generation, historical, 2026-08-27); `outputs/run_mode*.jsonl` referenced in `README.md` "How to run the first real case" | **Freshly executed** — 1 case mode A (`actual_outputs/step10_gpu_validation/run_modeA_n1.jsonl`) + 5 cases as part of mode C (`run_modeC_n5.jsonl`) |
| Selective correction generation | `SelectiveCorrector.correct()` (`src/corrector.py:43`), reuses the already-loaded generator's model/tokenizer | Same Qwen model, no second model loaded | Yes — inherits the loaded generator's CUDA-resident model; raises if generator not loaded | `outputs/labeled_correction_validation_gpu_metrics.json` + `..._corrections_detail.jsonl` (10-case targeted correction experiment, 2026-08-27); `outputs/final_metrics.json` (cumulative 1/56 correction rate, historical) | **Freshly executed** — 1 real trigger inside the mode-C n=5 smoke test (case `1996_129`, claim `c2`, rejected as `correction_scope_violation`); full 10-case targeted experiment reproduced exactly (see `GPU_REPRODUCTION_CROSSCHECK.md`) |
| Scope-violation check on corrected text | `pipeline._scope_violation()` (`src/pipeline.py:210`) | None (pure Python string containment) | No — CPU-only, deterministic | `outputs/atomic_scope_check_final_replay.json` (STEP 7 fresh replay, CPU) | Ran fresh as part of every mode-C case above (CPU, no GPU involved) |
| Sibling-regression re-verification | `pipeline._reverify_sibling_regressions()` (`src/pipeline.py:296`), calls `NLIVerifier.verify()` | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | Only if verifier is loaded with `device="cuda"` (production default in `NLIVerifier.__init__`, `src/verifier.py:95`); `device="cpu"` is a valid, explicit opt-in used by every prior CPU-only benchmark and by `scripts/run_labeled_correction_validation_gpu.py` | STEP 6 natural-data verification (CPU, historical) | Ran fresh, **on GPU** in the mode-C n=5 smoke test (verifier loaded via `run_mvp.py`'s default `NLIVerifier(...)`, no `device=` override → `cuda`); ran fresh **on CPU** (explicit `device="cpu"`) inside the 10-case targeted correction reproduction, matching the original script's own explicit choice |
| Field-level NLI verification (mode B/C) | `pipeline.apply_verification()` → `NLIVerifier.verify()` (`src/verifier.py:163`) | Same DeBERTa model | Same as above — device is a constructor parameter, defaults to `"cuda"`, requires explicit `device="cpu"` opt-in for CPU-only runs | STEP 6's 588-claim and 209-claim CPU verification runs (historical, this project's normal mode) | Ran fresh, on GPU, for the mode-C n=5 cases (via `run_mvp.py`'s default verifier construction) |
| Correction/re-verification decision (ship vs. reject) | `pipeline.apply_selective_correction()` (`src/pipeline.py:366`) | Orchestrates the above; no model of its own | Indirectly — depends on whichever of the above it calls | `outputs/labeled_correction_validation_gpu_metrics.json`'s `status_counts` | Ran fresh in both the n=5 smoke test and the 10-case reproduction; see `GPU_REPRODUCTION_CROSSCHECK.md` and `GPU_CORRECTION_SAFETY_STEP10.md` |

## Notes

- No production source file (`src/*.py`) was modified to produce any of the
  "Fresh Status" results above. `StatuteGroundingGenerator`, `SelectiveCorrector`,
  `NLIVerifier`, and `pipeline.run_case`/`apply_selective_correction` were called
  exactly as written, via the existing production entry point
  `scripts/run_mvp.py` (mode A / mode C) and via a byte-for-byte copy of
  `scripts/run_labeled_correction_validation_gpu.py` with only its two output
  file paths redirected (see `actual_outputs/step10_gpu_experiments/rerun_labeled_correction_validation_gpu.py`'s
  own docstring for the diff).
- `outputs/final_gpu_validation_{A,B}.jsonl` (the 209-claim paired generation
  experiment behind the historical χ²=13.07 result) was **not** freshly
  regenerated this step — reproducing it from scratch means ~100+ new Qwen
  generations (two arms × ~50-105 cases each) and was judged out of scope for
  a GPU-execution-*validation* step; it remains HISTORICAL ONLY. See
  "GPU EXPERIMENTS BLOCKED / NOT EXECUTED" in the STEP 10 final report.
