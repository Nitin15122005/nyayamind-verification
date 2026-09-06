# Historical Cross-Check — Natural-Data Results (STEP 6)

Distinct from `../comparisons/expected_vs_actual/HISTORICAL_CROSSCHECK.md` (STEP 4,
GOLD datasets only). This file covers the natural-data (METRIC-ONLY) cross-checks.

Every comparison below states: **fresh result**, **historical result**, **difference**,
whether the comparison is exact, whether datasets/configurations are identical, and a
possible explanation only where one is actually known (never invented).

## 588-claim aggregate — evidence coverage

| | Value |
|---|---|
| FRESH TESTING RESULT (this step) | 390/588 matched = 0.6633 (66.3%) |
| HISTORICAL RESULT | `outputs/evidence_coverage_v0_vs_v1.json`: `n_matched_v1=390`, `coverage_v1_pct=66.3` |
| Difference | **0.000000 — exact match** |
| Datasets/config identical? | Yes — same 4 source files, same dedup-by-text logic, same current v0+v1 pool (136 records) |
| Explanation needed? | No — this is deterministic code (claim parsing + evidence matching), so an exact match is expected, not merely hoped for |

## 209-claim paired set — evidence coverage and McNemar test

| | Fresh (this step) | Historical (`outputs/final_gpu_validation.md`) | Difference |
|---|---|---|---|
| Arm A evidence coverage | 132/209 = 0.6316 (63.2%) | "63.2%" | exact (to stated precision) |
| Arm B evidence coverage | 147/209 = 0.7033 (70.3%) | "70.3%" | exact (to stated precision) |
| McNemar χ² | 13.0667 | 13.07 | exact (to stated precision) |
| p-value | 0.000301 | ≈0.0003 | exact (to stated precision) |

**Datasets/config identical?** Yes — same source files, Arm A re-matched against its own
recorded original config (v0-only), Arm B against the current production pool
(v0+v1, 136 records — the same pool version this step used throughout, post the
2026-08-27 audit correction; the historical Arm B file itself was generated against a
137-record snapshot, one record earlier than the current 136, per `README_v1.md`'s
documented audit correction — this pre-existing, already-documented discrepancy does not
change the coverage percentage since the corrected record was already usable under
either count).

**Explanation needed?** No — exact reproduction, as expected for deterministic matching
logic.

## 209-claim paired set — verdict distributions (labeled framing)

There is **no historical "Arm A under labeled framing" number to cross-check against** —
Arm A (the pre-2026-08-27 baseline) was never re-verified under labeled framing anywhere
in this project's prior history; only Arm B was (via `outputs/final_validation_bare_vs_labeled_cpu_metrics.json`,
which covers the 147 evidence-matched claims from Arm B specifically). This step's fresh
Arm-A-under-labeled result is genuinely new — not a reproduction, and not claimed to be
one.

For Arm B specifically, cross-checking against `outputs/final_validation_bare_vs_labeled_cpu_metrics.json`
(confirmed directly, not assumed):

| | Fresh (this step, Arm B, labeled, 147 evidence-matched claims) | Historical (`final_validation_bare_vs_labeled_cpu_metrics.json`, `labeled_verdict_counts`) |
|---|---|---|
| n claims with evidence | 147 | 147 |
| NOT_ENOUGH_INFORMATION | 131 | 131 |
| ENTAILED | 13 | 13 |
| CONTRADICTED | 3 | 3 |

**Result: exact match on the complete verdict distribution**, not just one figure — this
step's fresh Arm-B-labeled re-verification reproduces the historical CPU-only
bare-vs-labeled experiment's `labeled_verdict_counts` field bit-for-bit.

## Natural batches — coverage figures (historical tabulation only, no fresh re-derivation claimed)

`batches_analysis.json`'s per-batch coverage figures are read directly from each batch's
own already-computed, historical `evidence_text` presence — they are not compared
against a separate historical document because they ARE the historical record itself,
freshly *tabulated* (counted) this run, not freshly *re-derived* (re-matched). No
discrepancy is possible by construction, since the same stored field is being read both
times; this is noted explicitly rather than presented as an independent cross-check.

## Summary

Every genuinely independent cross-check performed in this step (588-claim coverage,
209-claim coverage and McNemar test, Arm-B-labeled ENTAILED count) **reproduced its
historical counterpart exactly**. No discrepancy was found anywhere in this step's
natural-data work.
