# Demo Pack Validation Log

Run: 2026-08-27T09:37:08.971453+00:00
Script: `research/prototype/final_demo_pack/metadata/validate_pack.py`

**25/25 checks passed.**

| Check | Result | Detail |
|---|---|---|
| All 4 JSON files under final_demo_pack/ parse | PASS |  |
| All 17 CSV files under final_demo_pack/ parse and are non-empty | PASS |  |
| 16 figure PNGs exist | PASS | found 16 |
| Figure 01_evidence_coverage_v0_to_v1.png is non-trivial size | PASS | 189199 bytes |
| Figure 02_evidence_coverage_across_natural_batches.png is non-trivial size | PASS | 166615 bytes |
| Figure 03_bare_vs_labeled_verification_outcomes.png is non-trivial size | PASS | 157825 bytes |
| Figure 04_bare_vs_labeled_correction_outcomes.png is non-trivial size | PASS | 151402 bytes |
| Figure 05_synthetic_vs_natural_correction_success.png is non-trivial size | PASS | 153035 bytes |
| Figure 06_contradiction_detection_comparison.png is non-trivial size | PASS | 141286 bytes |
| Figure 07_no_evidence_taxonomy.png is non-trivial size | PASS | 174157 bytes |
| Figure 08_correction_failure_taxonomy.png is non-trivial size | PASS | 115765 bytes |
| Figure 09_safety_outcomes.png is non-trivial size | PASS | 146583 bytes |
| Figure 10_threshold_sensitivity_curve.png is non-trivial size | PASS | 141683 bytes |
| Figure 11_evidence_coverage_vs_batch_size.png is non-trivial size | PASS | 121435 bytes |
| Figure 12_experiment_timeline.png is non-trivial size | PASS | 145146 bytes |
| Figure 13_claim_evidence_funnel.png is non-trivial size | PASS | 132317 bytes |
| Figure 14_correction_pipeline_funnel.png is non-trivial size | PASS | 104585 bytes |
| Figure 15_production_config_summary.png is non-trivial size | PASS | 136205 bytes |
| Figure 16_natural_vs_synthetic_comparison.png is non-trivial size | PASS | 173628 bytes |
| Headline 'UNSAFE SHIPMENTS = 0 / 122' matches computed_metrics.json | PASS | unsafe=0, total_attempts=122 |
| Headline '63.2% -> 70.3% evidence coverage' matches computed_metrics.json | PASS | A=63.2, B=70.3 |
| Headline '1 natural shipped correction' matches computed_metrics.json | PASS | total_shipped=1 |
| Threshold-sensitivity macro-F1 @0.70 matches computed_metrics.json (bare~0.749, labeled~0.968) | PASS | bare=0.7486646586649771, labeled=0.9683612674297156 |
| All 8 exemplar cases present in cases.json | PASS | found 8 |
| No undisclaimed 'lawyer-verified' claims found | PASS |  |

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

Note: `pytest research/prototype/tests/ -q` and `research/prototype/scripts/run_mvp.py --check` are full-repo checks, run separately (see RUNBOOK.md) and recorded in SYSTEM_STATUS.md, not duplicated by this demo-pack-scoped script.