# Stage 5 — Correction Generation

**Source**: `research/prototype/src/corrector.py::SelectiveCorrector.correct()` +
triggering policy in `src/pipeline.py::_should_trigger_correction()`. Reuses the
generation model already loaded in stage 1 — GPU required (inherits stage 1's hard
CUDA requirement).

## Existing tests mapped here

| Test file | Functions/scope | Notes |
|---|---|---|
| `test_pipeline_mock.py` | `test_contradicted_claim_triggers_correction_and_succeeds`, `test_low_confidence_nei_triggers_correction_entailed_does_not`, `test_genuine_high_confidence_neutral_does_not_trigger_correction`, `test_correction_failure_keeps_original_text_but_flags_status` | covers the triggering policy: CONTRADICTED at any confidence, or NEI with `sub_reason=="low_confidence"` — never NO_EVIDENCE, never a genuine high-confidence neutral |
| `test_correction_path_real_integration.py` | whole file — **spans stages 05-08 together** | uses a `FakeGenerator`/`ScriptedCorrector` (never calls the real 7B Qwen model) but a REAL DeBERTa verifier, so the trigger→correct→scope-check→reverify→ship chain is exercised with genuine entailment decisions; the closest thing in this repo to a true multi-stage integration test — also referenced from `../../integration_tests/README.md` |

## What this stage's tests legitimately establish

Exact triggering-policy correctness (Category B) and — via the real-integration test —
that a genuinely CONTRADICTED verdict really does lead to a real DeBERTa-verified
correction attempt end-to-end. **Correction quality/success rate on real natural data**
(e.g. the 10%-shipped-of-triggered figure from the final production regime) is metric-only
— see `../../comparisons/metric_based/`.

## Known config/code drift affecting this stage

`correction.model_id` is declared in `config/prototype.yaml` but never read —
`corrector.py` always reuses the generator's own already-loaded model, never a separately
configured one. `correction.max_attempts` / `correction.max_reverifications` are declared
but never read — "exactly one attempt, exactly one reverification" is hardcoded control
flow in `apply_selective_correction`, not enforced via these config values.

## Relevant scripts

- `scripts/run_labeled_correction_validation_gpu.py` — real GPU correction validation
  (reuses already-generated text, makes real correction calls; ~2 min).
- `scripts/rerun_correction_reverification.py` — re-verifies already-produced corrections
  under different framings, no regeneration.

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_pipeline_mock.py -k "correction" -v
```

(`test_correction_path_real_integration.py` loads a real DeBERTa model — CPU-capable per
`REPRODUCIBILITY.md` §2 — run it separately and expect it to take longer than the fully
mocked tests.)
