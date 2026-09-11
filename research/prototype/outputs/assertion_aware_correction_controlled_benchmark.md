# Controlled correction benchmark: LEGACY vs ASSERTION-AWARE

_Generated 2026-09-12_

## What this is (and is not)

This is a **deterministic, mock-verifier/mock-corrector benchmark**
(`research/prototype/tests/test_assertion_aware_correction.py`, 20 tests,
no GPU, no real model) built entirely from **real corpus data** — actual
`EvidenceRecord`s and citation identities drawn from the NyayaRAG/statute
evidence pool (IPC Sections 302, 21, 420), not synthetic or invented
labels. It is NOT a natural-data end-to-end result and must never be
reported as one — its purpose is to prove the ORCHESTRATION and SAFETY
LOGIC of the new mechanism is correct, in a form that runs in ~20 seconds
and is fully reproducible by anyone (`pytest tests/test_assertion_aware_correction.py`),
independent of the natural-data GPU experiment
(`outputs/assertion_aware_correction_experiment_report.md`, real Qwen +
DeBERTa, run separately — see that report for the actual research result).

## The core motivating scenario, reproduced deterministically

`test_assertion_aware_ships_narrow_fix_legacy_regeneration_would_reject`
constructs the exact SHAPE of the real `1955_32` natural-data failure
(see `outputs/16gb_final_execution_report.md`'s case study): a bundled
`"<claim A>, while <claim B>."` sentence where claim A is flagged
CONTRADICTED and claim B is an unrelated, correctly-supported sibling.

| Mechanism | Corrector behavior simulated | Outcome |
|---|---|---|
| LEGACY (`apply_selective_correction`) | Whole-sentence regeneration that PARAPHRASES the untouched sibling clause instead of reproducing it byte-for-byte (a realistic LLM behavior — models asked to "copy verbatim" frequently paraphrase anyway) | `correction_scope_violation` — rejected, even though claim A's own fix is substantively correct |
| ASSERTION-AWARE (`apply_selective_correction_assertion_aware`) | Splices only claim A's own `assertion_text` clause; the sibling clause is never touched by the LLM call at all | `corrected` — shipped, with the sibling clause proven byte-identical (exact substring assertion, not approximate) |

Both branches run in the SAME test, against the SAME underlying fix, so
the comparison is paired and exact — not two separately-run experiments
that might differ for unrelated reasons.

## Safety-gate coverage exercised (all real code paths, not simulated)

| Category | Test | Result |
|---|---|---|
| Splice target not unique in claim_text | `test_splice_fails_closed_when_assertion_text_not_unique_in_claim_text` | fails closed, no guess |
| Splice target absent from claim_text | `test_splice_fails_closed_when_assertion_text_absent_from_claim_text` | fails closed |
| claim_text not unique in field (duplicate sentences) | `test_splice_fails_closed_when_claim_text_not_unique_in_field` | fails closed |
| Corrector returns nothing usable | `test_splice_fails_closed_on_empty_corrected_fragment`, `test_splice_unavailable_end_to_end_when_corrector_returns_empty` | `correction_splice_unavailable`, never ships raw/unspliced text |
| Genuine no-op edit | `test_splice_is_noop_safe_when_fragment_equals_original` | splices cleanly to byte-identical text (not an error) |
| Unauthorized citation hallucinated inside the fragment | `test_unauthorized_citation_injected_inside_fragment_is_rejected` | `correction_unauthorized_addition`, rejected before re-verification |
| Fix that doesn't actually resolve the contradiction | `test_correction_failed_when_reverification_stays_not_entailed` | `correction_failed`, original text shipped |
| `narrow_reverification_hypothesis` interaction | `test_narrow_reverification_hypothesis_used_when_enabled` | narrows the TARGET's own re-verification hypothesis as configured; the sibling-regression check still uses the sibling's full claim_text regardless (unaffected by this flag) |
| Sibling-regression net runs even when scope check passes | `test_sibling_regression_check_runs_unconditionally` (monkeypatched) | rejects a shipment even after the splice's structural guarantee and the scope check both passed — proves this is enforced, not merely assumed safe by construction |
| Ordinal-position matching (shared-citation siblings) | `test_replacement_matched_by_ordinal_position_under_assertion_aware` | matches the correct sibling, same technique as the legacy path |
| Negation-caveated claims | `test_negation_caveated_claim_never_triggers_assertion_aware_correction` | never auto-triggers, same exclusion as legacy |
| NO_EVIDENCE claims | `test_no_evidence_claim_never_triggers_assertion_aware_correction` | never auto-triggers |
| Config dispatch | `test_assertion_aware_true_never_calls_legacy_corrector_interface`, `test_assertion_aware_flag_recorded_in_reproducibility_block` | correct routing; `assertion_aware=False` (default) still exercises ONLY the legacy code path |

## Honest limitations of this benchmark

- Uses `ScriptedAssertionSpanCorrector`/`ScriptedVerifier` mocks that
  return exactly the text the test asks for — it proves the pipeline
  handles every INPUT SHAPE correctly, not that the real Qwen2.5-7B model
  reliably produces well-formed, correctly-scoped fragments on real case
  text. That is a genuinely separate question, answered only by the
  natural-data experiment (`outputs/assertion_aware_correction_experiment_report.md`).
- Does not attempt to enumerate every possible malformed LLM output (e.g.
  a fragment containing partial/broken sentence structure that still
  parses as valid claims) — the safety gates listed above are the ones
  this project has concrete evidence are load-bearing (each corresponds to
  a real historical rejection category — see
  `outputs/workstream_b2_correction_error_analysis.md`), not an exhaustive
  adversarial search.
