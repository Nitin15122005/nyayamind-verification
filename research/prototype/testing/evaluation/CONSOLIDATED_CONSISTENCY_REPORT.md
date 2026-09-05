# Consolidated Consistency Report (STEP 8)

Every headline value named in this step's instructions was mechanically checked against
its canonical source artifact by `validate_step8_consolidation.py`'s
`check_all_26_headline_values` function — not eyeballed, not asserted from memory. Full
raw output: `testing/actual_outputs/step8_consolidation/validate_step8_report.txt`.

## Reconciliation table

| # | Value | Reconciled against | Result |
|---|---|---|---|
| 1 | 63.2% | `paired_209_metrics.json::fresh_evidence_coverage_arm_A` | **MATCH** (63.2) |
| 2 | 70.3% | `paired_209_metrics.json::fresh_evidence_coverage_arm_B` | **MATCH** (70.3) |
| 3 | 15 gains | `paired_209_metrics.json::evidence_change_counts.evidence_gained` | **MATCH** (15) |
| 4 | 0 losses | `paired_209_metrics.json::evidence_change_counts.evidence_lost` | **MATCH** (0) |
| 5 | χ² 13.0667 | `paired_209_metrics.json::mcnemar_evidence_coverage.chi2` | **MATCH** (13.0667) |
| 6 | p 0.000301 | `paired_209_metrics.json::mcnemar_evidence_coverage.p_value` | **MATCH** (0.000301) |
| 7 | 0.7487 | `gold01_metrics.json::results_by_framing.bare.macro_f1` | **MATCH** |
| 8 | 0.9684 | `gold01_metrics.json::results_by_framing.labeled.macro_f1` | **MATCH** |
| 9 | 0.7333 | `gold01_metrics.json::results_by_framing.bare.accuracy` | **MATCH** |
| 10 | 0.9714 | `gold01_metrics.json::results_by_framing.labeled.accuracy` | **MATCH** |
| 11 | 98.01 | `ABLATION_SUMMARY.json` (factor=premise_framing).statistic | **MATCH** |
| 12 | 4.16e-23 | `ABLATION_SUMMARY.json` (factor=premise_framing).p_value | **MATCH** |
| 13 | 1.5777e-30 | `ABLATION_SUMMARY.json` (factor=premise_framing).exact_sign_test_p_value | **MATCH** |
| 14 | 6/30 | `ABLATION_SUMMARY.json` (factor=claim_parser_fix).cases_improved | **MATCH** (6) |
| 15 | 0/30 | `ABLATION_SUMMARY.json` (factor=claim_parser_fix).cases_worsened | **MATCH** (0) |
| 16 | p 0.03125 | `ABLATION_SUMMARY.json` (factor=claim_parser_fix).p_value | **MATCH** |
| 17 | 66.3% | `claims_588_metrics.json::evidence_coverage` | **MATCH** (66.3) |
| 18 | 390/588 | `claims_588_metrics.json::n_evidence_matched` | **MATCH** (390) |
| 19 | 364 NEI | `claims_588_metrics.json::verdict_distribution.NOT_ENOUGH_INFORMATION` | **MATCH** (364) |
| 20 | 198 NO_EVIDENCE | `claims_588_metrics.json::verdict_distribution.NO_EVIDENCE` | **MATCH** (198) |
| 21 | 21 ENTAILED | `claims_588_metrics.json::verdict_distribution.ENTAILED` | **MATCH** (21) |
| 22 | 5 CONTRADICTED | `claims_588_metrics.json::verdict_distribution.CONTRADICTED` | **MATCH** (5) |
| 23 | 0/5 → 1/10 | `labeled_correction_validation_gpu_metrics.json` (both fields) | **MATCH** (0, 1) |
| 24 | 1/56 | `final_metrics.json::section_D_correction_safety_cumulative.total_shipped` (n=56) | **MATCH** (1) |
| 25 | 0 unsafe | `final_metrics.json::section_D_correction_safety_cumulative.total_unsafe_shipped` | **MATCH** (0) |
| 26 | 205/205 | fresh `pytest` run, this step | **MATCH** (confirmed separately, see Phase 18) |

## Result

**No discrepancy was found.** All 26 values reconcile exactly across every artifact
that cites them (STEP 4-7's own outputs, `final_comparison/tables/statistical_tests.csv`'s
independent cross-checks, and this step's own `CANONICAL_METRICS.json`,
`ABLATION_SUMMARY.json`, `HEADLINE_RESULTS.md`, `ORIGINAL_VS_CURRENT.md`, and all 11
`figure_data/*.csv` files). Per this step's rule 15, had any discrepancy been found it
would be reported here explicitly rather than silently resolved — none was.

## Method

`validate_step8_consolidation.py::check_all_26_headline_values` loads each of the 5
canonical source JSON files directly (never a markdown file, never a hand-typed
constant) and compares the exact value against the literal number named in this step's
own instructions, using an exact-match comparator for integers and a tight relative
tolerance (≤0.1%) for floating-point statistics (accounting only for JSON
floating-point serialization, not any computational discrepancy). All 26 comparisons
passed with the tightest tolerance applied.
