# Figure Numeric Audit (STEP 9, Phase 10)

Every value displayed on every figure, traced back to its exact source CSV cell.
Percentages are computed as `round(fraction * 100, 1)` from the CSV's stored fraction
column — the CSV itself stores the un-rounded fraction (e.g. `0.631578947368421`), and
the plotting code performs the `*100` and display rounding only; no percentage value is
independently retyped anywhere.

| Figure | Source CSV | Values checked | Result |
|---|---|---|---|
| 01 | `01_overall_metric_comparison.csv` | 0.632/0.703 (evidence coverage), 0.749/0.968 (macro F1), 0.733/0.971 (accuracy), 0.356/0.458 (contradiction recall) — all read directly from `original_value`/`current_value` columns, displayed to 3 decimal places | **MATCH** |
| 02 | `02_evidence_coverage.csv` | 63.2%/70.3%/66.3% from `coverage` column (×100, rounded to 1dp); "gained=15, lost=0, unchanged=194" and "McNemar p=0.000301" are static annotation text drawn directly from STEP 6's `paired_209_metrics.json` (not re-derived by the plotting script, since this CSV does not carry the paired-change columns — see rounding note below) | **MATCH** |
| 03 | `03_verdict_distribution.csv` | 364, 198, 21, 5 read directly from the `count` column for the `588_claim_aggregate` rows | **MATCH** |
| 04 | `04_correction_funnel.csv` | All stage counts (triggered/generated/scope_gate_rejected/reverification_not_entailed/shipped) per population read directly from their named columns; `NOT AVAILABLE` cells rendered as "Not available" text, never a number | **MATCH** |
| 05 | `05_correction_outcome.csv` | shipped/failed/scope_violation per population read directly from their named columns; annotation text "0/5→1/10", "1/56=1.8%", "0 unsafe" drawn from the same source values already verified in Figure 04/06 | **MATCH** |
| 06 | `06_safety.csv` | 0, 18, 0, 37 read directly from the `count` column; "Not available" row rendered as text, not 0 | **MATCH** |
| 07 | `07_confidence_distribution.csv` | 0.88/0.90 (ENTAILED), 0.85/0.80 (CONTRADICTED), 0.87/0.94 (NEI), 0.87/0.94 (ALL) read directly from `mean_confidence`/`median_confidence` columns, displayed to 2 decimal places | **MATCH** |
| 08 | `08_ablation_comparison.csv` | p-values (3.01e-04, 4.16e-23, 3.12e-02) read directly from the `p_value` column; grade letters assigned per the fixed mapping documented in the plotting code, matching `ABLATION_EVIDENCE_GRADES.md` exactly (not re-derived) | **MATCH** |
| 09 | `09_runtime_resource.csv` | 2041s, 1663s, 645s, 1413s, 154s read directly from `runtime_seconds` (rounded to nearest whole second for display); N values from `n_cases` | **MATCH** |
| 10 | `10_cumulative_natural_results.csv` | All 11 coverage percentages and N values read directly from `coverage`/`n` columns | **MATCH** |
| 11 | `11_synthetic_vs_natural_transfer.csv` | 26/36=72.2% and 1/56=1.8% — the CSV stores these as pre-formatted strings (`"26/36 = 0.722"`, `"1/56 = 0.018"`) in the `synthetic_value`/`natural_value` columns; the plotting script parses the known fractions (26/36, 1/56) directly rather than re-typing a decimal, and the displayed label text is copied from the CSV's own note field | **MATCH** |

## Rounding rule, documented explicitly

Every percentage shown is `round(fraction * 100, 1)`, computed at plot time directly
from the CSV's stored high-precision fraction (e.g. `63.2%` is displayed from
`0.631578947368421`, i.e. 132/209 — the CSV itself does not store the raw 132/209
integers, only the fraction, so the plotting script does not re-derive the integer
numerator/denominator; those exact counts are independently confirmed in
`evaluation/CONSOLIDATED_CONSISTENCY_REPORT.md` from STEP 8). No denominator was
invented anywhere in this audit.

## Figure 02's annotation text — an explicit exception, documented

The "gained=15, lost=0, unchanged=194" and "McNemar p=0.000301" text drawn on Figure 02
is **not itself parsed from `02_evidence_coverage.csv`** (that specific CSV does not
carry paired-change columns — it is a per-arm coverage table, not a per-claim paired
table). This text is a fixed annotation string in the plotting code, sourced from
`evaluation/PAIRED_209_REPORT.md` / `paired_209_metrics.json` (STEP 6), both of which
were independently reconciled against the same numbers in STEP 8's
`CONSOLIDATED_CONSISTENCY_REPORT.md`. This is flagged here explicitly, per this audit's
own purpose, rather than silently presented as if it were parsed from the figure's
primary CSV.
