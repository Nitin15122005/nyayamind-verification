# Stage 7 — Re-verification & Shipping Gate

**Source**: the re-verification step inside
`research/prototype/src/pipeline.py::apply_selective_correction` — re-matches evidence
for the replacement claim, verifies under `narrow_reverification_hypothesis`, and ships
(`status="corrected"`) **iff** the result is ENTAILED. Inherits stage 3's verifier
(GPU by default, CPU opt-in exists).

## Existing tests mapped here

| Test file | Functions | Notes |
|---|---|---|
| `test_pipeline_mock.py` | `test_narrow_reverification_hypothesis_off_by_default`, `test_narrow_reverification_ships_when_full_sentence_dilutes_confidence`, `test_narrow_reverification_never_synthesizes_text` | confirms `assertion_text` is always a genuine substring of the model's own corrected output — never fabricated — and that narrowing the hypothesis can convert a diluted result into a decisive one |
| `test_premise_framing_production.py` | `test_reverification_premise_uses_the_configured_framing` | confirms the same framing (bare/labeled) is used at re-verification as at primary verification |
| `test_correction_path_real_integration.py` | `test_full_correction_path_triggers_and_reverifies_with_real_verifier` | real-verifier confirmation of the unconditional ENTAILED-only shipping gate — spans 05-08, see stage 5's README |

## What this stage's tests legitimately establish

That the shipping gate is exactly `status == "corrected"` ⟺
`reverification.verdict == ENTAILED`, with no loosening anywhere, and that
`narrow_reverification_hypothesis` only ever narrows the *hypothesis*, never widens what
counts as evidence-consistent. Category B. The **actual observed effect** of this lever
(2 of 3 real `correction_failed` cases converted to more decisive verdicts; 0 ship/reject
outcomes changed by this lever alone in the batches tested) is metric-only — see
`../../comparisons/metric_based/`.

## Known config/code drift affecting this stage

`correction.max_reverifications` is declared in `config/prototype.yaml` but never read —
"exactly one reverification" is hardcoded, not config-enforced. See stage 5's README for
the parallel `max_attempts` finding.

## Relevant scripts

- `scripts/run_labeled_correction_validation_gpu.py`, `scripts/compare_final_validation_labeled_cpu.py`
  (CPU-only re-verification of the same 209/147 claims under both framings).

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_pipeline_mock.py -k "narrow_reverification" -v
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_premise_framing_production.py -k "reverification" -v
```
