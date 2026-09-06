# Stage 5 — Correction Generation

**Source**: `research/prototype/src/corrector.py::SelectiveCorrector.correct()` +
triggering policy in `src/pipeline.py::_should_trigger_correction()`. Reuses the
generation model already loaded in stage 1 — GPU required (inherits stage 1's hard
CUDA requirement).

## No dedicated STEP 5 RESULT.md exists for this stage

Unlike every other stage in `components/`, STEP 5's per-component execution never
produced a standalone result for correction generation itself under this name — its
`actual_outputs` folder only ran a dedicated demo for the adjacent citation-identity/
adversarial-safety group (now `../02_evidence_retrieval/CITATION_ADVERSARIAL_RESULT.md`).
This is an honest, pre-existing gap, not something PASS 1 cleanup removed — no result is
fabricated here to fill it. The closest existing empirical evidence for this stage is:
`tests/test_correction_path_real_integration.py`'s real-DeBERTa correction-trigger path
(see `06_scope_safety/RESULT.md`, which documents the same real integration run from the
scope/safety angle), and the correction activity visible inside
`../../evaluation/CORRECTION_FUNNEL.md` and `../../gpu_validation`-equivalent GPU reports
under `../../evaluation/GPU_*.md`. A dedicated `05_correction/RESULT.md` tracing
`test_correction_path_real_integration.py`'s correction-generation-specific assertions
is a reasonable PASS 2 candidate — see the PASS 1 report's recommended scope.

## Existing tests mapped here

| Test file | Functions/scope | Notes |
|---|---|---|
| `test_pipeline_mock.py` | `test_contradicted_claim_triggers_correction_and_succeeds`, `test_low_confidence_nei_triggers_correction_entailed_does_not`, `test_genuine_high_confidence_neutral_does_not_trigger_correction`, `test_correction_failure_keeps_original_text_but_flags_status` | covers the triggering policy: CONTRADICTED at any confidence, or NEI with `sub_reason=="low_confidence"` — never NO_EVIDENCE, never a genuine high-confidence neutral |
| `test_correction_path_real_integration.py` | whole file — **spans stages 05-08 together** | uses a `FakeGenerator`/`ScriptedCorrector` (never calls the real 7B Qwen model) but a REAL DeBERTa verifier, so the trigger→correct→scope-check→reverify→ship chain is exercised with genuine entailment decisions; the closest thing in this repo to a true multi-stage integration test — also referenced from `../integration_tests/README.md` |

## What this stage's tests legitimately establish

Exact triggering-policy correctness (Category B) and — via the real-integration test —
that a genuinely CONTRADICTED verdict really does lead to a real DeBERTa-verified
correction attempt end-to-end. **Correction quality/success rate on real natural data**
(e.g. the 10%-shipped-of-triggered figure from the final production regime) is metric-only
— see `../../evaluation/CORRECTION_FUNNEL.md`.

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
