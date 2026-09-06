# RESULT — 08 Final Assembly / Integration (STEP 5)

**Moved here in PASS 1 cleanup** from the old `component_tests/07_final_assembly/` (a
STEP-5-only numbering artifact — verified this pass, by content, to belong to Stage 8
"Final Output Assembly," not Stage 7 "Re-verification": this file's own execution filter
(`"reproducibility or assertion_text_surfaces"`) matches `README.md`'s Stage 8 test list
exactly).

CPU-safe, multi-component integration — the full path INPUT → claim parsing → evidence
retrieval → verification → verdict → safety/final assembly, using the real, unmodified
`src/pipeline.py::run_case` and a real DeBERTa verifier. **The full GPU generation
pipeline was NOT run.**

## Execution

`research/.venv/Scripts/python.exe -m pytest test_pipeline_mock.py -k "reproducibility or assertion_text_surfaces" -v` **and, separately** `test_correction_path_real_integration.py -v` (run unconditionally — its test names don't match the `-k` filter used for the mocked file, so it is invoked directly for this group; see `../TEST_INVENTORY.md`).

**5 executed, 5 passed, 0 failed** (2 mocked + 3 real-model). (Raw log removed in PASS 1
cleanup, see `../01_claim_parser/RESULT.md`'s note.)

## The complete CPU-safe path, demonstrated end to end

Source: `demo_examples.json` in this directory — the **complete, real** `run_case()`
return records for both the SHIP and REJECT cases described in
`../06_scope_safety/RESULT.md`, included here in full (not excerpted) to show
final-assembly-specific fields:

```
INPUT CASE (case_text via FakeGenerator -- pre-existing real text, Qwen NOT invoked)
   |
   v
CLAIM PARSING          -- real src/claim_parser.py, ran on the (fake-generator-supplied) text
   |
   v
EVIDENCE RETRIEVAL      -- real src/evidence_matcher.py against the real v0 pool
   |
   v
NLI VERIFICATION        -- real src/verifier.py::NLIVerifier, DeBERTa, CPU
   |
   v
VERDICT                 -- real src/pipeline.py::apply_verification
   |
   v
CORRECTION (scripted text, Qwen NOT invoked) -- real src/pipeline.py trigger logic
   |
   v
SAFETY / SCOPE CHECK    -- real src/pipeline.py::_scope_violation
   |
   v
RE-VERIFICATION         -- real DeBERTa verifier again
   |
   v
FINAL OUTPUT            -- real src/pipeline.py::run_case assembly
```

**GPU-dependent portions not executed, explicitly**: stage 1 (real Qwen generation) and
the real-model half of stage 6 (real Qwen correction text generation) both require the
7B Qwen model, which requires an NVIDIA GPU this machine does not have (STEP 2). Both
are supplied by `FakeGenerator`/`ScriptedCorrector` here instead — the exact same
substitution `tests/test_correction_path_real_integration.py` already makes. **Every
other stage shown above is 100% real, unmodified production code**, including the
DeBERTa verifier's two real inference calls (initial verification + re-verification)
per case.

**What the final assembly stage itself specifically confirms** (from the full records):
- `final_field.source` correctly reflects `"corrected"` in the SHIP case and
  `"correction_scope_violation"` in the REJECT case.
- The `reproducibility` block (software versions, seed, framing used) is present in
  both records.
- Internal, underscore-prefixed bookkeeping keys are absent from the final claim
  records (stripped, as the production code guarantees).

**Result classification: PASS (Category A — SOFTWARE BEHAVIOR PASS)** for all 5 tests
and both full integration records.
