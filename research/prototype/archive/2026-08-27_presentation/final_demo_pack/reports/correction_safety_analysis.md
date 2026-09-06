# Correction + Safety Analysis

Source: `research/prototype/final_demo_pack/metadata/computed_metrics.json` section `correction_safety_audit`. This section was **recomputed fresh** from every raw per-attempt artifact this project ever produced (not copied from a narrative report), and cross-checked against `final_metrics.json`'s independently-computed cumulative count — both agree exactly (`cross_checks.all_match: true`).

## Headline

> **UNSAFE SHIPMENTS = 0 across 122 total correction attempts (56 natural + 66 synthetic) in this project's entire history.**

This is a structural invariant, not a sampled observation: every attempt whose `status == "corrected"` was checked against `reverification.verdict == "ENTAILED"`, and the invariant holds for all 122 without exception (`correction_safety_audit.natural.invariant_holds: true`, `n_unsafe_shipped: 0` in both natural and synthetic).

## Every historical correction-attempt category

### Natural (real NyayaRAG cases, all batches: n=30, batch1, batch2, final validation)

| Status | Count | % of 56 |
|---|---:|---:|
| `correction_failed` | 37 | 66.1% |
| `correction_scope_violation` | 18 | 32.1% |
| `corrected` (shipped) | 1 | 1.8% |
| **Total attempts** | **56** | 100% |

Sources (parsed directly, one row = one attempt): `run_C_n30.jsonl`, `final_gpu_validation_A.jsonl`, `final_gpu_validation_B.jsonl` (5 attempts each), `natural_candidates_50_gpu_corrections_detail.jsonl` (21), `natural_candidates_batch2_gpu_corrections_detail.jsonl` (15), `labeled_correction_validation_gpu_corrections_detail.jsonl` (10, includes the 1 shipped correction).

### Synthetic stress (deliberately corrupted claims, real GPU Qwen correction)

| | Bare | Labeled |
|---|---:|---:|
| Attempts | 30 | 36 |
| `correction_failed` | 30 | 10 |
| `corrected` (shipped) | 0 | 26 |
| Shipped rate | 0% | 72.2% |

Source: `framing_comparison_gpu_n59_postfix_metrics.json` (correction stats only — the per-claim results jsonl for this experiment does not carry per-attempt correction records, so these numbers are reused verbatim from the dedicated metrics file rather than mis-recomputed).

**The synthetic 72.2% shipped rate has never transferred to natural data** (1.8% pooled, 10% final-production-regime best case) — see `EXECUTIVE_SUMMARY.md` and `reports/verifier_analysis.md`.

## Shipped vs. rejected, by mechanism

- **`correction_failed`** (37 natural + 40 synthetic = 77 total): the corrector's rewrite, when re-verified, did not reach ENTAILED. The pipeline discards the correction and ships the original text. This is the single most common outcome.
- **`correction_scope_violation`** (18 natural, 0 synthetic): the corrector altered text belonging to an unflagged claim. Caught **programmatically** (`src/pipeline.py::_scope_violation()`), not just by prompt instruction — every unflagged claim's required text (full sentence under the legacy check, or its narrower `assertion_spans` under the current production check) must survive verbatim in the corrected paragraph, or the entire correction is discarded and the original text ships. Both texts are retained in the output record for inspection.
- **`corrected`** (1 natural + 26 synthetic = 27 total, all safe): shipped only when reverification reaches ENTAILED.

## Sibling-regression protection

`src/pipeline.py::_reverify_sibling_regressions()` runs automatically whenever `atomic_scope_check` is truthy — it independently re-verifies every sibling claim's own counterpart in the corrected text (not just checks the required text is present), specifically to catch a case the relaxed `assertion_spans` check could in principle miss: a sibling's *surrounding* text changing enough to alter what it entails. **0 attempts were flagged by this check across every natural correction this project has run** (`correction_safety_audit.natural.n_attempts_with_sibling_regression_flagged: 0`). This check can only ever additionally reject a correction, never approve one.

## Citation-identity preservation

`apply_selective_correction()`'s ordinal-position citation-identity matching guarantees a corrected replacement claim is matched back to the *same* citation the original flagged claim named. This is core pipeline logic, not a config toggle. Every case where a correction's edit disturbed a claim's citation identity correctly produced `correction_failed` with `reverification: null` (the "citation identity lost" category) — see `research/prototype/outputs/final_gpu_validation.md` §4 for the full per-case breakdown; this is a qualitative confirmation from manual inspection, not a count re-derived in this pack.

## Atomic scope check / assertion-spans behavior

The production `atomic_scope_check: "assertion_spans"` mode narrows what counts as an unflagged claim's "required surviving text" from the full original sentence to a conservative, verbatim sub-span (or, for "respectively"-pattern claims, a list of independently-required verbatim fragments) — never a synthesized combination. Motivation: on real data, one physical sentence often backs multiple claims sharing that sentence as `claim_text`; under the legacy full-sentence rule, editing any part of that shared sentence broke every other claim's check regardless of whether the edit was substantively correct. In the batch-1 motivating data, 4 of 6 genuine scope-violation-blocked edits were substantively valid fixes blocked purely by this legacy structural limitation. In this project's own re-test on the final validation batch, the 2 scope-violation cases actually re-tested under `assertion_spans` were **correctly still rejected** — the narrower check did not spuriously let anything through in that specific batch (the decision to adopt it rests on the larger batch-1 sample plus the independent sibling-regression safety net, not a repeated result in every batch).

## Unflagged-claim preservation

| Batch | Preservation rate |
|---|---|
| Batch 1, bare | 45/45 = 100% |
| Batch 1, labeled | 83/107 = 77.6% |
| Final validation, both arms (claim-text basis) | 16/21 = 76.2% |
| Final validation, both arms (assertion-span basis) | 18/21 = 85.7% |

Measured per-batch (not pooled, since the preservation denominator depends on the scope-check mode active for that batch) — full per-claim breakdown: `research/prototype/outputs/final_gpu_validation.md` §4.

## The one shipped natural correction, in full

Document `2003_760`, claim `c3`, final production regime (labeled + v0+v1 + assertion_spans + narrow_reverification). Original text incorrectly restated IPC §302's *definition* language under what should have been its *punishment* text; the correction rewrote it to the actual punishment text, matching real evidence almost verbatim. Reverified **ENTAILED at 0.995 confidence, 0 sibling regressions**. Full record: `research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl`; narrative: `FINAL_PRODUCTION_CONFIG.md` §1. This is presented as **one genuine, checkable improvement in citation-content alignment** — not a legal-correctness determination, and n=1 is explicitly not treated as a rate.
