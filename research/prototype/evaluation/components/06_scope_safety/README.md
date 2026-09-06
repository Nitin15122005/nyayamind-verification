# Stage 6 — Scope Violation Gate & Sibling-Regression Safety Net

**Source**: `research/prototype/src/pipeline.py::_scope_violation`,
`_reverify_sibling_regressions`, `_citation_identity` + ordinal-position matching
(deterministic checks; `_reverify_sibling_regressions` inherits stage 3's verifier for
its own re-verification calls).

## Existing tests mapped here

| Test file | Functions/scope | Notes |
|---|---|---|
| `test_pipeline_mock.py` | the bulk of this file: `test_unflagged_claim_preserved_verbatim...`, `test_correction_scope_violation_when_unflagged_claim_altered`, `test_replacement_matched_by_ordinal_position_when_claims_share_citation`, the full `atomic_scope_check_*` family, the `test_assertion_spans_*` family, `test_sibling_regression_check_rejects_a_genuine_regression`, `test_sibling_regression_check_does_not_run_under_legacy_mode` | covers all three `atomic_scope_check` modes (`false`/`true`/`"assertion_spans"`), ordinal citation-identity matching, and confirms the sibling-regression net can only ever reject a correction, never approve one |
| `test_correction_path_real_integration.py` | `test_scope_violation_protection_when_corrector_alters_unflagged_claim` | real-verifier variant of the scope-violation check — spans 05-08, see stage 5's README |

## What this stage's tests legitimately establish

Exact scope-check-mode logic (Category B) — including that `assertion_spans` mode
requires *all* fragments in a claim's `assertion_spans` list to survive verbatim, not
just one — and that citation-identity ordinal matching correctly finds each corrected
claim's counterpart even when several claims share one citation. **Whether relaxing the
scope check from legacy to `assertion_spans` actually unlocks more genuine fixes in
practice** is a separate, metric-only, and explicitly **weak/inconclusive** finding — see
`../../ablation/README.md` (the final scope-check replay found only 1/11 real scope
violations unblocked, contradicting an earlier, unreconciled batch-1 finding of 4/6).

## Known config/code drift affecting this stage

`atomic_scope_check: "assertion_spans"` sets two internal flags
(`use_assertion_text=True` and `use_assertion_spans=True`), but `_scope_violation`'s
branch order makes `use_assertion_text` a no-op whenever `use_assertion_spans` is true —
correct output, but redundant plumbing worth simplifying in a future pass (not done in
this step).

## Relevant scripts

- `scripts/replay_atomic_scope_check.py` → `replay_assertion_spans_check.py` →
  `replay_final_atomic_scope_check.py` — the 3-stage deterministic replay lineage over
  real, already-produced correction attempts; no GPU, no new model calls. See
  `../../ablation/README.md`.

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_pipeline_mock.py -k "scope or sibling or ordinal or assertion_spans" -v
```
