# Correction funnel (all experiments, historical + fresh)

Scope-gate rejection counts for the two n=10 replay rows are read directly from `outputs/assertion_aware_correction_experiment_comparison.json`'s per-case status field, not re-derived; for the assertion-aware row, `correction_structural_span_lost`/`correction_span_invalid` are grouped with scope-gate rejections as they are pre-reverification safety gates (none occurred in this batch -- see `error_propagation_matrix.csv`).

| Population | Type | Candidate claims | Correction triggered | Scope-gate rejected | Re-verification not ENTAILED | Shipped | Unsafe shipped | Freshness | Source artifact |
|---|---|---|---|---|---|---|---|---|---|
| Synthetic stress — baseline (bare premise) | synthetic | 59 | 30 | 0 | 30 | 0 | 0 | HISTORICAL (GPU) | research/prototype/outputs/final_metrics.json |
| Synthetic stress — modified (labeled premise) | synthetic | 59 | 36 | 0 | 10 | 26 | 0 | HISTORICAL (GPU) | research/prototype/outputs/final_metrics.json |
| Natural targeted — baseline framing (Arm B, bare) | natural | 209 | 5 | 2 | 3 | 0 | 0 | HISTORICAL (GPU); exactly reproduced STEP 10B | research/prototype/outputs/final_gpu_validation_metrics.json |
| Natural targeted — modified framing (labeled) | natural | 209 | 10 | 3 | 6 | 1 | 0 | HISTORICAL (GPU); exactly reproduced STEP 10 | research/prototype/outputs/labeled_correction_validation_gpu_metrics.json |
| Natural cumulative — all correction attempts, project history | natural | NOT TRACKED as a single denominator | 56 | 18 | 37 | 1 | 0 | HISTORICAL-ONLY (protocol insufficient to reproduce) | research/prototype/outputs/final_metrics.json |
| Fresh n=62 natural batch — OLD arm (narrow_primary_hypothesis=false) | natural | 156 | 4 | 0 | 4 | 0 | 0 | FRESH (GPU, 2026-09-12) | research/prototype/outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json |
| Fresh n=62 natural batch — CURRENT arm (narrow_primary_hypothesis=true, production) | natural | 156 | 5 | 0 | 5 | 0 | 0 | FRESH (GPU, 2026-09-12) | research/prototype/outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json |
| Paired n=10 replay — LEGACY correction (whole-sentence regeneration) | natural | n/a (targeted replay, not a fresh claim population) | 10 | 3 | 5 | 0 | 0 | HISTORICAL (read from the committed n=62 batch, not recomputed) | research/prototype/outputs/assertion_aware_correction_experiment_comparison.json |
| Paired n=10 replay — ASSERTION-AWARE correction (splice-based) | natural | n/a (targeted replay, not a fresh claim population) | 10 | 5 | 4 | 0 | 0 | FRESH (GPU, 2026-09-12) | research/prototype/outputs/assertion_aware_correction_experiment_comparison.json |
