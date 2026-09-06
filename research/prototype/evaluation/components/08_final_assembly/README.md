# Stage 8 — Final Output Assembly

**Source**: `research/prototype/src/pipeline.py::run_case` — assembles the final JSONL
record (`final_field` source selection across `original`/`corrected`/`correction_failed`/
`correction_scope_violation`/`correction_sibling_regression`, stripped internal keys, the
`reproducibility` block with live-introspected software versions).

## Existing tests mapped here

| Test file | Functions | Notes |
|---|---|---|
| `test_pipeline_mock.py` | `test_correction_reproducibility_metadata_reaches_output_record`, `test_assertion_text_surfaces_in_output_record_additively` | confirms metadata propagation and that internal fields are additive, never destructive |
| `test_premise_framing_production.py` | `test_reproducibility_block_records_the_framing_used`, `test_internal_provision_bookkeeping_is_stripped_from_output` | confirms the framing actually used is recorded, and that underscore-prefixed internal keys never leak into the final record |
| `test_correction_path_real_integration.py` | whole file (real-verifier) | end-to-end output-record shape check — spans 05-08, see stage 5's README |

## What this stage's tests legitimately establish

That the final record's shape and provenance metadata are correct and complete for every
possible `final_field.source` value (Category B). No dedicated script exists solely for
this stage — it is exercised implicitly by every `run_*.py` / `run_*_gpu.py` script's
output file, since assembly is the last step of every real run.

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_pipeline_mock.py -k "reproducibility or assertion_text_surfaces" -v
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_premise_framing_production.py -k "reproducibility_block or internal_provision" -v
```
