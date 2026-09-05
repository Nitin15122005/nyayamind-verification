# Figure Contract Inventory (STEP 9, Phase 1)

All 11 locked CSV contracts from STEP 8 (`research/prototype/testing/evaluation/figure_data/`),
read exactly as they exist — none regenerated, none reinterpreted, none numerically
altered.

| File | Rows | Columns | Source artifact(s) | Dataset(s) | N | Metric classification | Intended visualization | Fresh/Historical |
|---|---|---|---|---|---|---|---|---|
| `01_overall_metric_comparison.csv` | 4 | metric, original_value, current_value, unit, dataset, n, fresh_or_historical, source | STEP 4 GOLD-01/02, STEP 6 209-paired | 209-paired natural, GOLD-01, GOLD-02 | 209 / 420 / 59 | gold_metric + natural_metric (mixed, kept on separate axes) | Grouped bar, original vs. current, separate panels/axes per metric type | FRESH |
| `02_evidence_coverage.csv` | 11 | dataset, arm_or_config, coverage, n, n_matched, fresh_or_historical, source | STEP 6 209-paired, 588-claims, batches | 209-paired + 588-claim + 8 batch regimes | 29–588 | natural_metric (METRIC-ONLY) | Bar chart of coverage %, labeled "observed evidence coverage" | Mixed (2 FRESH, 9 HISTORICAL) |
| `03_verdict_distribution.csv` | 37 | dataset, verdict, count, n_total, fresh_or_historical, source | STEP 6 588-claims, 209-paired, batches | 588-claim + 209-paired (2 arms) + 8 batches | 29–588 per row group | natural_metric (METRIC-ONLY, descriptive) | Stacked/grouped bar of verdict counts per dataset | Mixed |
| `04_correction_funnel.csv` | 5 | population, candidate, correction_triggered, correction_generated, scope_gate_rejected, reverification_not_entailed, sibling_regression_rejected, citation_identity_failures, shipped, rejected_total, source | `final_metrics.json`, `final_gpu_validation_metrics.json`, `labeled_correction_validation_gpu_metrics.json` | synthetic (bare/labeled), natural targeted (bare/labeled), natural cumulative | 30–59 / 5–10 / 56 | natural_metric (correction funnel, METRIC-ONLY) | Funnel/stage bar chart, one subplot per population, never merged | HISTORICAL, GPU-dependent |
| `05_correction_outcome.csv` | 5 | population, n_triggered, shipped, correction_failed_or_reverification_not_entailed, scope_violation, source | same as above | same 5 populations | same | natural_metric | Stacked bar: shipped / failed / scope-violation per population | HISTORICAL, GPU-dependent |
| `06_safety.csv` | 5 | safety_mechanism, count, denominator, source | `final_metrics.json`, `final_gpu_validation_metrics.json` | all correction attempts, project history | 5 / 56 / 122 (varies by row) | natural_metric (safety, descriptive count) | Horizontal bar of observed counts, "0 unsafe" prominent | HISTORICAL |
| `07_confidence_distribution.csv` | 4 | dataset, verdict, mean_confidence, median_confidence, n, source | STEP 6 588-claims | 588-claim aggregate, current config, labeled framing | 5–390 per verdict | natural_metric (descriptive) | Bar chart of mean confidence per verdict, single dataset only | FRESH |
| `08_ablation_comparison.csv` | 8 | factor, baseline_value, variant_value, primary_metric, p_value, classification, fresh_or_historical, source | STEP 7 `ABLATION_SUMMARY.json` | 8 named ablation factors | varies | mixed (gold_metric, natural_metric, behavior) | Grade-colored bar/dot chart, grades A-E visually distinct | Mixed |
| `09_runtime_resource.csv` | 5 | arm, runtime_seconds, peak_vram_mib, n_cases, fresh_or_historical, source | `final_gpu_validation_metrics.json`, `final_metrics.json`, STEP 4 gold01 | 4 historical GPU arms + 1 fresh CPU arm | 50 / 59 / 420 | runtime/resource | Bar chart, runtime seconds, GPU rows visually distinct from the 1 CPU row | Mixed (4 HISTORICAL GPU, 1 FRESH CPU) |
| `10_cumulative_natural_results.csv` | 11 | (identical shape to `02_evidence_coverage.csv`) | same as file 02 | same as file 02 | same | natural_metric | Cumulative view across all natural regimes, coverage % | Mixed |
| `11_synthetic_vs_natural_transfer.csv` | 2 | metric, synthetic_value, natural_value, populations_comparable, note, source | `final_metrics.json`, STEP 4/6 | synthetic (GOLD-02-derived) vs. natural (588/cumulative) | 36 / 56 / 59 | natural_metric + gold_metric (explicitly marked NOT comparable) | Side-by-side bars, visually separated, explicit "not directly equivalent" annotation | Mixed, explicitly disclaimed |

## Cross-cutting observations recorded before any plotting begins

- Files `02_evidence_coverage.csv` and `10_cumulative_natural_results.csv` are
  **identical in shape and content** — the STEP 8 contract deliberately produced both
  under separate names for figures 02 and 10, which have different presentational
  purposes (per-comparison vs. cumulative-across-regimes). Both are visualized
  faithfully as separate figures; no data was invented to differentiate them.
- File `04_correction_funnel.csv`'s `natural_targeted_bare` row uses `candidate=209`
  (total claims in that arm), not the 147 evidence-matched subset that actually could
  trigger correction — this is the STEP 8 contract's own recorded value and is
  **not corrected or reinterpreted here**, per this step's rule 6. The figure will
  visualize the funnel using the CSV's own stage counts (`correction_triggered=5` etc.)
  which are internally consistent regardless of the `candidate` field's exact
  denominator choice.
- Several `NOT AVAILABLE` cells appear (sibling-regression and citation-identity counts
  for most populations) — these will be rendered as explicit "Not available" labels,
  never inferred or plotted as zero.
