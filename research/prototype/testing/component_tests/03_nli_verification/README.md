# Stage 3 — NLI Verification

**Source**: `research/prototype/src/verifier.py::NLIVerifier`
(MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli; GPU by default, explicit CPU opt-in exists
in code).

## Existing tests mapped here

| Test file | Scope here | Notes |
|---|---|---|
| `test_controlled_benchmark.py` | all 23 tests | covers `format_premise` bare/labeled construction, the device/CPU-opt-in guard, and benchmark paraphrase/negation construction-rule tests (the latter are strictly benchmark-*builder* tests, shipped in this file); no model is loaded — gold labels must be derivable as pure functions |
| `test_premise_framing_production.py` | all 17 tests | premise-framing wiring through `pipeline.apply_verification`/`run_case` via a scripted (non-real) verifier, plus the two config-lock tests (`test_shipped_config_locks_the_2026_08_27_final_production_decision`, `test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`) |

## What this stage's tests legitimately establish

Bare-vs-labeled premise construction (including the silent fallback-to-bare on missing
provision metadata — see drift item below), the confidence-threshold downgrade to
NOT_ENOUGH_INFORMATION, and that the model's own `id2label` is read rather than
hardcoded. All Category B. **Actual verifier accuracy** is only legitimately measured
against the two gold datasets in `../../expected_outputs/` — see
`../../comparisons/expected_vs_actual/`.

## Known config/code drift affecting this stage

`verifier.py::format_premise()` silently falls back from `labeled` to `bare` if the
matched evidence record's provision metadata is incomplete — documented only in a
docstring, not surfaced in `FINAL_PRODUCTION_CONFIG.md`. Currently believed inert (no
matched evidence record has been observed with incomplete metadata) but unflagged as a
production guarantee. `src/llm_verifier.py::QwenLLMVerifier` is a fully-built alternative
verifier never wired into `pipeline.py` — used only by the standalone
`scripts/run_verifier_benchmark.py` / `tests/test_verifier_benchmark.py`; do not mistake
it for a second production verification path.

## Relevant scripts

- `scripts/build_controlled_benchmark.py` — builds the 420-item gold benchmark.
- `scripts/run_controlled_benchmark.py` — evaluates a verifier against it, persists full
  softmax distributions (enables ablation without re-inference).
- `scripts/analyze_threshold_sensitivity.py` — replays the confidence-threshold decision
  rule against stored softmax distributions (see `../../ablation/`).

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_controlled_benchmark.py research/prototype/tests/test_premise_framing_production.py -v
```
