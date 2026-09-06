# RESULT — 06 Correction Scope and Safety Gates (STEP 5)

**GPU generation was not executed on this machine.** Every "correction" below is either
(a) a scripted/pre-authored text supplied by a `ScriptedCorrector` (never the real 7B
Qwen model — exactly the pattern `tests/test_correction_path_real_integration.py`
already uses), or (b) a HISTORICAL INPUT already committed to
`research/prototype/outputs/` before this step ran. No new Qwen correction text was
generated anywhere in this step.

## Execution

`research/.venv/Scripts/python.exe -m pytest test_pipeline_mock.py -k "scope or sibling or ordinal or assertion_spans or narrow_reverification or correction" test_correction_path_real_integration.py -v`

**35 executed, 35 passed, 0 failed** (32 from the mocked `test_pipeline_mock.py` filter
+ 3 from the real-model `test_correction_path_real_integration.py`, included because its
filename itself matches the `-k` pattern). (Raw log removed in PASS 1 cleanup, see
`../01_claim_parser/RESULT.md`'s note.)

## Chain demonstrated (real DeBERTa verifier + scripted corrector, CPU)

Source: `demo_examples.json` in this directory, produced by re-running
`src/pipeline.py::run_case` with the exact same fixtures
`tests/test_correction_path_real_integration.py` uses.

### Case 1 — SHIP (safe, genuine correction)

```
INPUT: corrupted claim (Section 302 IPC, deliberately says "fine only, never death")
    -> real DeBERTa verdict: CONTRADICTED (confidence above threshold)
    -> correction triggered for claim 302 only
    -> ScriptedCorrector supplies pre-authored corrected text (Qwen NOT invoked)
    -> _scope_violation() check: unflagged Section-148 sentence preserved verbatim -> PASS, no violation
    -> re-verification via real DeBERTa verifier: ENTAILED
    -> SHIP: status="corrected", final_field.source="corrected", final_field.text = the corrected sentence
```
**Expected behavior**: ship iff re-verification is ENTAILED (the unconditional gate).
**Actual**: ENTAILED, shipped. **PASS.**

### Case 2 — REJECT (scope violation correctly caught)

```
INPUT: same corrupted claim
    -> same real CONTRADICTED verdict, correction triggered
    -> a DELIBERATELY BAD ScriptedCorrector also rewrites the UNFLAGGED Section-148 sentence
    -> _scope_violation() check: unflagged sentence altered -> VIOLATION DETECTED
    -> re-verification: NEVER CALLED (caught before it would run)
    -> REJECT: status="correction_scope_violation", final_field.source="correction_scope_violation",
       final_field.text = the ORIGINAL corrupted text (never the bad correction)
```
**Expected behavior**: `_scope_violation()` must catch an altered unflagged claim
*before* re-verification and refuse to ship. **Actual**: caught exactly as expected,
`reverification` field is `null`. **PASS.**

## Citation identity

Both cases route the claim through `src/pipeline.py::_citation_identity()`'s
ordinal-position matching to find the same citation's counterpart in the
re-parsed corrected text — confirmed by the claim_id continuity visible in the full
records (`demo_examples.json`). No citation-identity failure occurred in either case.

## Re-verification gate / shipping decision

Confirmed unconditional: `status == "corrected"` **if and only if**
`reverification.verdict == ENTAILED`. No threshold was loosened, no safety gate was
bypassed, in either this step's demonstration or the underlying tests.

**Result classification: PASS (Category A — SOFTWARE BEHAVIOR PASS)** for all 35 tests
and both demonstrated fixture cases.
