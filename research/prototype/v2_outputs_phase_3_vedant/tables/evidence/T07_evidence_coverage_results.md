# T07_evidence_coverage_results

Evidence-coverage OUTCOMES (as opposed to the structural pool size in T06). Both rows are HISTORICAL - neither could be rerun here.

| dataset | n | ORIGINAL coverage | LATEST coverage | delta | per-claim change | statistical test | source artifact | freshness |
|---|---|---|---|---|---|---|---|---|
| 209-claim paired natural | 209 | 0.6316 | 0.7033 | 0.0718 | 15 gained / 0 lost | McNemar exact p=6.104e-05 | evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json | HISTORICAL |
| 588-claim corpus sweep | 588 | 0.6020 | 0.6630 | 0.0610 | 36 gained / 0 lost (354 -> 390 matched) | McNemar exact p=2.910e-11 | outputs/evidence_coverage_v0_vs_v1.json | HISTORICAL |

## Notes

- CORRECTED SOURCE POINTER: the repository documents the 588-corpus numbers as coming from `evaluation/metrics/EVIDENCE_STRENGTH_MATRIX.md`, which does not contain them. The real source is `outputs/evidence_coverage_v0_vs_v1.json`.
- 'Coverage' on unlabelled natural data is a RETRIEVAL outcome. It is never accuracy, precision or recall.
- The artifact carries both `historical_*` and `fresh_*` columns; the values above are the `fresh_evidence_coverage_arm_A/B` fields.
