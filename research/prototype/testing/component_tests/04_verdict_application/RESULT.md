# RESULT — 04 Verdict Application (STEP 5)

Tests `src/pipeline.py::apply_verification` — the deterministic logic that converts a
verifier's raw result into the claim's stored verdict, and decides which claims even
reach the verifier.

## Execution

`research/.venv/Scripts/python.exe -m pytest test_pipeline_mock.py -k "mode_a or mode_b or no_evidence or apply_verification" -v`

**3 executed, 3 passed, 0 failed, 0 skipped** (31 deselected — other
`test_pipeline_mock.py` tests not relevant to this narrow filter; see
`TEST_INVENTORY.md` for where those are covered). Full log:
`../../actual_outputs/step5_components/04_verdict_application/pytest_execution.log`.

Test names: `test_mode_a_no_verification_no_correction`,
`test_mode_b_verifies_but_never_changes_final_field`,
`test_no_evidence_claim_never_triggers_correction`.

## Representative input → actual output (real verdict, not mocked)

Source: `../../actual_outputs/step5_components/04_verdict_application/demo_examples.json`
— the same real `run_case()` call documented in `03_verifier/RESULT.md`, examined here
from the verdict-application angle instead.

**Input**: a real, matched claim (Section 302 IPC) whose hypothesis deliberately
contradicts its real evidence text.
**Actual output**: `claim["verdict"] = "CONTRADICTED"`, `confidence` recorded, evidence
identity (`evidence_id`, `evidence_text`) preserved unchanged from the matched record.

**Software invariants checked, all confirmed by the executed tests above**:
- A claim with `evidence_text is None` is never sent to the verifier at all
  (`test_no_evidence_claim_never_triggers_correction`).
- Mode A never calls the verifier; Mode B calls it but never changes `final_field`
  regardless of verdict (`test_mode_a_...`, `test_mode_b_...`).
- Confidence-threshold downgrade to NOT_ENOUGH_INFORMATION is the verifier's own
  responsibility (tested in `03_verifier`), not re-implemented here — this stage applies
  whatever the verifier returns verbatim.

**No legal expected label was invented here.** "CONTRADICTED" in the representative
example above is expected only because the hypothesis was deliberately, mechanically
constructed to contradict its own cited evidence (the same pattern GOLD-02 uses) — this
is a software-behavior expectation, not a legal-ground-truth claim.

**Result: PASS (Category A — SOFTWARE BEHAVIOR PASS).**
