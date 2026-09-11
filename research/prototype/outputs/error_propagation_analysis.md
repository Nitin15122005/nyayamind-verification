# Error propagation matrix — assertion-aware correction (real n=10 batch)

_Generated from `outputs/assertion_aware_correction_experiment_{OLD,CURRENT}.jsonl` — real Qwen2.5-7B + real DeBERTa, the exact 5 documents that triggered legacy correction in the committed n=62 batch. See `outputs/error_propagation_matrix.csv` for the full per-case table and `outputs/assertion_aware_correction_experiment_report.md` for the narrative case-by-case analysis this matrix is a structured summary of._

## Scope

Covers only the pipeline stages a CORRECTION ATTEMPT passes through (parser -> citation mapping -> retrieval -> verification -> correction targeting -> correction generation -> splice -> pre-reverification safety gates -> reverification -> sibling-regression safety gate -> shipping), for the 10 real (document, arm) pairs in this batch. Not a claim about every claim in the wider n=62 batch, and not an independent parser/retrieval/verification error analysis (those stages are reported separately — see FINAL_RESEARCH_FREEZE_REPORT.md sections C-E).

## First-failure-stage distribution (n=10)

| First failure stage | Count |
|---|---|
| safety_scope_citation_ordinal | 5 |
| reverification | 2 |
| safety_sibling_regression | 2 |
| none (correctly not triggered) | 1 |

**0/10 shipped.** No case reached `first_failure_stage = none (shipped)`. 1/10 correctly never triggered (`none (correctly not triggered)`). Every other case failed at either a pre-reverification safety gate (scope/citation/ordinal — the dominant real-data failure category at this n), the reverification step itself (the corrector's fix did not reach ENTAILED), or the post-reverification sibling-regression check (the one case, `1955_32`, where the target's own fix was genuinely correct but an untouched sibling in the same sentence was independently wrong too).

## Honest limitations

- n=10 — not statistically powered; every number above is a real count, not a rate claimed to generalize.
- Every case in this batch happens to have a 1-element `assertion_spans` (confirmed directly — see `outputs/assertion_span_aware_integration_replay.json`), so the `correction_span_invalid` and `correction_structural_span_lost` stages have zero real-data coverage here; they are exercised only by the deterministic test suite (`tests/test_assertion_aware_correction.py`), not by real Qwen output. Stated plainly, not filled in.
