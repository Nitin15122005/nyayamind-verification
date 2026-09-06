# Evidence coverage: v0 vs v0+v1

| comparison | n_claims | n_matched_v0 | coverage_v0_pct | n_matched_v1 | coverage_v1_pct | significance |
|---|---|---|---|---|---|---|
| claim-level (all natural claims) | 588 | 354 | 60.2 | 390 | 66.3 | no significance test computed |
| paired-arm (final_gpu_validation, 50 held-out cases) | 209 | 132 | 63.2 | 147 | 70.3 | McNemar chi2=13.07, p~0.0003 |

*Source: computed_metrics.json.evidence_coverage_v0_v1 and .final_metrics_passthrough.section_B_natural_regimes. The paired-arm row is the only one with an established significance test.*