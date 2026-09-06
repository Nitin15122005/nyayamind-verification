# Stage 4 — Verdict Application

**Source**: `research/prototype/src/pipeline.py::apply_verification` (mutates
`claims[]` in place; no model of its own, inherits stage 3's verifier).

## Existing tests mapped here

| Test file | Functions | Notes |
|---|---|---|
| `test_pipeline_mock.py` | `test_mode_a_no_verification_no_correction`, `test_mode_b_verifies_but_never_changes_final_field`, `test_no_evidence_claim_never_triggers_correction`, `test_evidence_match_method_preserved...` | fully mocked verifier; confirms NO_EVIDENCE claims never reach the verifier and Mode A/B branching is correct |
| `test_premise_framing_production.py` | `test_apply_verification_defaults_to_bare_for_callers_that_pass_nothing`, the NO_EVIDENCE-never-reaches-verifier test, `test_apply_verification_rejects_an_invalid_framing_argument` | confirms framing is threaded correctly from config into this stage |

## What this stage's tests legitimately establish

That every claim with `evidence_text is None` is skipped (never sent to the verifier),
and that the **primary** verification pass always hypothesizes the full `claim_text`
(never the narrower `assertion_text` — that narrowing only ever applies at
re-verification, stage 7). This asymmetry is a real, documented architectural limitation,
not a bug — see `FINAL_PRODUCTION_CONFIG.md`'s own discussion of why labeled framing
helps less on older, heavily-bundled claim sets.

## Relevant scripts

- `scripts/rerun_natural_verification.py`, `scripts/rerun_correction_reverification.py` —
  re-score already-generated text under different framings; do not regenerate.

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_pipeline_mock.py -k "mode_a or mode_b or no_evidence" -v
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_premise_framing_production.py -k "apply_verification" -v
```
