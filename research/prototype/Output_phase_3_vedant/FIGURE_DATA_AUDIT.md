# FIGURE_DATA_AUDIT — every plotted number and where it came from

Generated 2026-09-06 against repository commit `b83bb6b30cf4c548d60e1c9dea23186ab0e52a68`.

## How to read this document

This package enforces a two-stage rule so that no number can reach a figure without a
traceable origin:

1. `scripts/build_metric_tables.py` reads the committed experiment artifacts and writes
   one locked CSV per metric contract into `metrics/`. Every row carries its own
   `source_artifact` column.
2. `scripts/generate_figures.py` opens **only** those CSVs. It never opens an experiment
   artifact directly, so a value that is not in a locked CSV cannot appear in a figure.

`scripts/validate_package.py` re-checks stage 1 against the source artifacts on every run.

## Metric contracts

| Metric CSV | Purpose | Source artifact(s) | Dataset | n | Freshness | Evidence grade | Caveat |
|---|---|---|---|---|---|---|---|
| `M01_headline_baseline_vs_modified.csv` | Four strongest baseline-vs-modified comparisons on one 0-1 axis | research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json ; research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json ; research/prototype/evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json ; research/prototype/evaluation/ablation/ABLATION_SUMMARY.json | GOLD-01 / GOLD-02 / 209-claim paired natural | 420 / 59 / 209 | FRESH | A | Heterogeneous metric types on a shared axis; bar heights are NOT interchangeable across categories. Natural evidence coverage is not accuracy. |
| `M02_gold01_overall.csv` | GOLD-01 accuracy and macro F1, baseline (bare) vs modified (labeled) | research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json ; research/prototype/evaluation/ablation/ABLATION_SUMMARY.json | GOLD-01_controlled_verifier_benchmark | 420 | FRESH (CPU) | A | Curated controlled benchmark; hypotheses are mechanically constructed, not free-running generated claims. |
| `M03_gold01_per_class.csv` | GOLD-01 per-class precision / recall / F1 for both systems | research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json | GOLD-01_controlled_verifier_benchmark | 420 | FRESH (CPU) | A | Precision/recall are legitimate here ONLY because GOLD-01 carries real per-item labels; no natural-data figure in this package uses them. |
| `M04_gold01_confusion.csv` | GOLD-01 3x3 confusion matrices, baseline vs modified | research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json | GOLD-01_controlled_verifier_benchmark | 420 | FRESH (CPU) | A | Counts are per-item verifier decisions against GOLD labels. |
| `M05_gold02_synthetic_stress.csv` | GOLD-02 synthetic stress-set contradiction recall and outcome split | research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json | GOLD-02_synthetic_stress_set | 59 | FRESH (CPU) | A | Every record is CONTRADICTED by construction, so recall here is a detection-sensitivity measure on deliberately corrupted claims — it is not a natural-data accuracy figure. |
| `M06_evidence_coverage_209_paired.csv` | Paired 209-claim evidence coverage, baseline v0 pool vs modified v0+v1 pool | research/prototype/evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json | 209_claim_paired_natural_evaluation | 209 | FRESH REPRODUCTION (CPU) | A | Coverage = retrieval found a usable record. NOT a correctness or accuracy measure. |
| `M06b_evidence_209_discordance.csv` | McNemar discordant-pair counts behind the 209-claim coverage result | research/prototype/evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json | 209_claim_paired_natural_evaluation | 209 | FRESH REPRODUCTION (CPU) | A | Paired binary event: claim received usable evidence. |
| `M07_evidence_coverage_588_corpus.csv` | Corpus-level evidence coverage over all 588 pooled natural claims, v0 vs v0+v1 | research/prototype/outputs/evidence_coverage_v0_vs_v1.json | 588 pooled natural claims (all experiments) | 588 | HISTORICAL (corpus-level replay, CPU) | B | Corpus-level, not a paired-arm experiment; complements the paired 209 result. |
| `M08_verdict_distribution.csv` | Verifier verdict distributions on natural claims | research/prototype/evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json ; research/prototype/evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json | 209-claim paired + 588-claim aggregate | 209 / 588 | FRESH (CPU) | n/a (descriptive) | Verdict counts are the NLI model's own outputs, NOT correctness labels. |
| `M09_premise_framing_natural_batches.csv` | Premise-framing effect on natural-data verdicts (batch1 n=251, batch2 n=236) | research/prototype/evaluation/actual_outputs/natural_data_runs/batches/batches_analysis.json | natural_candidates batch1 / batch2 | 251 / 236 | HISTORICAL | B | Same claims and same v0 evidence pool in each pair; only premise framing differs. Verdict shifts are decisiveness, not measured correctness. |
| `M10_natural_147_framing_shift.csv` | Premise-framing verdict shift on the same 147 evidence-matched natural claims | research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json | final_validation Arm B evidence-matched subset | 147 | HISTORICAL (CPU verification-only re-run) | B | ENTAILED 0 -> 13 is a count of model verdicts reached, NOT of claims proven correct. |
| `M11_confidence_by_verdict_588.csv` | Verifier confidence per verdict on the 588-claim natural aggregate | research/prototype/evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json | 588_claim_natural_aggregate | 390 evidence-matched of 588 | FRESH (CPU) | n/a (descriptive) | Confidence is the NLI model's own softmax certainty, not correctness. |
| `M12_confidence_threshold_sweep.csv` | Deterministic threshold sweep (0.50-0.95) on GOLD-01 for both premise framings | research/prototype/outputs/threshold_sensitivity_analysis.json | GOLD-01_controlled_verifier_benchmark (stored softmax replay) | 420 | FRESH (deterministic replay, no re-inference) | B | A sensitivity description, not a threshold search; production threshold was not changed on the strength of this sweep. |
| `M13_correction_funnel.csv` | Correction funnel stage counts, five populations kept strictly separate | research/prototype/outputs/final_metrics.json ; research/prototype/outputs/final_gpu_validation_metrics.json ; research/prototype/outputs/labeled_correction_validation_gpu_metrics.json | synthetic + natural targeted + natural cumulative | 59 / 209 / 56 | HISTORICAL (GPU-dependent) | C | Synthetic and natural populations must never be pooled into one rate. The natural cumulative denominator is a project-history rollup, not one experiment. |
| `M14_correction_outcomes.csv` | Shipped / re-verification-failed / scope-rejected split per population | research/prototype/outputs/final_metrics.json ; research/prototype/outputs/final_gpu_validation_metrics.json ; research/prototype/outputs/labeled_correction_validation_gpu_metrics.json | synthetic + natural targeted + natural cumulative | 59 / 209 / 56 | HISTORICAL (GPU-dependent) | C | 0/5 -> 1/10 is a directional, isolated-by-design shift, not a statistically supported rate. |
| `M15_safety_observations.csv` | Observed counts for each programmatic safety mechanism | research/prototype/outputs/final_metrics.json ; research/prototype/outputs/final_gpu_validation_metrics.json | all tested correction attempts | 122 | HISTORICAL | n/a (observed counts) | 0 observed unsafe shipments is an observation on a finite tested history, not a proof that unsafe shipments are impossible. |
| `M16_ablation_matrix.csv` | All eight ablation factors with evidence grade, isolation status and statistics | research/prototype/evaluation/ablation/ABLATION_SUMMARY.json ; research/prototype/evaluation/metrics/EVIDENCE_STRENGTH_MATRIX.csv | 8 named ablation factors | varies (3-420) | MIXED | A-E | Grade communicates evidence strength (isolation + n + statistical support), not effect size. Grade E = the experiment does not exist. |
| `M25_scope_gate_replay.csv` | Deterministic scope-gate replay over 11 real historical scope violations | research/prototype/evaluation/ablation/scope_check_replay_fresh.json | 11 real historical scope-violation correction attempts | 11 | FRESH REPRODUCTION (CPU) | C | The replay stops at the scope gate. Whether the one unblocked case would actually ship an ENTAILED correction is NOT answered by this artifact. |
| `M17_runtime_resource.csv` | Wall-clock runtime and peak VRAM per experiment arm, GPU and CPU rows separated | research/prototype/outputs/final_gpu_validation_metrics.json ; research/prototype/outputs/final_metrics.json ; research/prototype/evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json ; research/prototype/evaluation/actual_outputs/gpu_209_reproduction/step10b_final_gpu_validation_metrics.json ; research/prototype/evaluation/actual_outputs/gpu_correction_rerun/labeled_correction_validation_gpu_metrics.fresh.json | mixed experiment arms | 50 / 59 / 10 / 420 | MIXED (GPU historical + fresh; CPU fresh) | n/a (resource measure) | Wall-clock time is a hardware/thermal/load measure, not a correctness measure. GPU and CPU arms are never compared as if equivalent. |
| `M18_natural_regimes_coverage.csv` | Observed evidence coverage across every natural-data regime, never pooled | research/prototype/evaluation/actual_outputs/natural_data_runs/batches/batches_analysis.json ; research/prototype/evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json ; research/prototype/evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json | 11 natural-data regimes | 29-588 per regime | MIXED (3 FRESH, 8 HISTORICAL) | n/a (descriptive) | Regimes differ in case selection and configuration; the spread is not a trend. |
| `M19_synthetic_vs_natural_transfer.csv` | Synthetic vs natural correction shipping rates, explicitly marked non-equivalent | research/prototype/outputs/final_metrics.json | synthetic stress vs natural corpus | 36 / 56 / 10 | HISTORICAL (GPU) | D | Disjoint populations with different base rates by construction. 72.2% and 1.8% do NOT measure the same capability and must never be plotted as a single trend. |
| `M20_no_evidence_taxonomy.csv` | Why claims resolve to NO_EVIDENCE, across all 797 claims in project history | research/prototype/outputs/no_evidence_taxonomy_v3.json | 797 pooled claims from every natural experiment | 797 (260 NO_EVIDENCE) | HISTORICAL (audit re-run) | B | A NO_EVIDENCE claim is not shown to be wrong — the corpus is ~140 provisions and most citations simply fall outside it. |
| `M21_parser_fix_n30.csv` | Claim-parser fix (commit 223eb9d) re-parse of the same 30 generated texts | research/prototype/outputs/parser_fix_before_after_n30.json ; research/prototype/evaluation/ablation/ABLATION_SUMMARY.json | n30_reparse | 30 cases / 88 vs 93 claims | HISTORICAL REPRODUCTION (code change not re-executed; statistic recomputed fresh) | B | This is a code-version ablation, not a configuration ablation, and is measured separately from the four production levers. |
| `M22_gpu_reproduction_crosscheck.csv` | Historical vs freshly-reproduced GPU experiment values (STEP 10 / 10B) | research/prototype/outputs/final_gpu_validation_metrics.json ; research/prototype/evaluation/actual_outputs/gpu_209_reproduction/step10b_final_gpu_validation_metrics.json ; research/prototype/outputs/labeled_correction_validation_gpu_metrics.json ; research/prototype/evaluation/actual_outputs/gpu_correction_rerun/labeled_correction_validation_gpu_metrics.fresh.json | 209-claim paired + 10-case targeted correction | 209 / 10 | FRESH GPU REPRODUCTION vs HISTORICAL | A (reproducibility only) | Exact reproduction under greedy decoding evidences pipeline stability across machines. It adds no new statistical evidence about legal correctness. |
| `M23_component_test_matrix.csv` | Per-component test counts and representative behaviour cases | research/prototype/evaluation/metrics/COMPONENT_TEST_MATRIX.csv | research/prototype/tests/ | 205 authoritative total | FRESH (re-run for this package: 205 passed) | n/a (software behaviour) | Per-component counts overlap where tests span stages; 205 is the only authoritative non-duplicated total — never sum the component rows. |
| `M24_evidence_pool_composition.csv` | Usable canonical-evidence pool size for each system, loaded live from source | research/prototype/config/prototype.yaml | research/data/evidence/ | 59 vs 136 usable records | FRESH (computed live via the unmodified production loader) | A | Only VERIFIED_EXACT / VERIFIED_CONTENT audit verdicts are usable; SOURCE_ONLY / INVALID / UNRESOLVED are excluded by design. |

## Per-figure audit

### F01 — Headline comparison: baseline NyayaMind v0 vs modified NyayaMind production

- **File:** `figures/F01_headline_baseline_vs_modified.png` · PPT variant `ppt_assets/figures/F01_headline_baseline_vs_modified.png`
- **Purpose:** Show the four strongest supported baseline/modified comparisons at a glance
- **Metric contract(s):** M01_headline_baseline_vs_modified.csv
- **Source artifact(s):** gold01_metrics.json; gold02_metrics.json; paired_209_metrics.json
- **Dataset / n:** GOLD-01; GOLD-02; 209-claim paired natural · n = 420 / 59 / 209
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH
- **Evidence grade:** A
- **Caveat printed on the figure:** Heterogeneous metrics on one axis; not interchangeable.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F02 — Verifier accuracy and macro F1 on the GOLD-01 controlled benchmark

- **File:** `figures/F02_gold01_accuracy_macro_f1.png` · PPT variant `ppt_assets/figures/F02_gold01_accuracy_macro_f1.png`
- **Purpose:** Quantify the premise-framing lever on labelled ground truth
- **Metric contract(s):** M02_gold01_overall.csv
- **Source artifact(s):** evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH (CPU)
- **Evidence grade:** A
- **Caveat printed on the figure:** Benchmark performance, not legal correctness.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F03 — Per-class precision, recall and F1 — GOLD-01 controlled benchmark

- **File:** `figures/F03_gold01_per_class_precision_recall_f1.png` · PPT variant `ppt_assets/figures/F03_gold01_per_class_precision_recall_f1.png`
- **Purpose:** Show where the premise-framing gain actually lands (ENTAILED recall 0.50 → 1.00)
- **Metric contract(s):** M03_gold01_per_class.csv
- **Source artifact(s):** evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH (CPU)
- **Evidence grade:** A
- **Caveat printed on the figure:** Legitimate only because GOLD-01 has per-item labels.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F04 — Verifier confusion matrices — GOLD-01 controlled benchmark

- **File:** `figures/F04_gold01_confusion_matrices.png` · PPT variant `ppt_assets/figures/F04_gold01_confusion_matrices.png`
- **Purpose:** Expose the exact error structure behind the accuracy difference
- **Metric contract(s):** M04_gold01_confusion.csv
- **Source artifact(s):** evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH (CPU)
- **Evidence grade:** A
- **Caveat printed on the figure:** Benchmark labels, not legal ground truth.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F05 — Contradiction detection on the GOLD-02 synthetic stress set

- **File:** `figures/F05_gold02_synthetic_contradiction_detection.png` · PPT variant `ppt_assets/figures/F05_gold02_synthetic_contradiction_detection.png`
- **Purpose:** Show adversarial detection sensitivity and its residual failure mode
- **Metric contract(s):** M05_gold02_synthetic_stress.csv
- **Source artifact(s):** evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json
- **Dataset / n:** GOLD-02_synthetic_stress_set · n = 59
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH (CPU)
- **Evidence grade:** A
- **Caveat printed on the figure:** Contradictory by construction; not a natural-data accuracy claim.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F06 — Evidence retrieval coverage on 209 paired natural claims

- **File:** `figures/F06_evidence_coverage_209_paired.png` · PPT variant `ppt_assets/figures/F06_evidence_coverage_209_paired.png`
- **Purpose:** The strongest natural-data baseline/modified result in the project
- **Metric contract(s):** M06_evidence_coverage_209_paired.csv ; M06b_evidence_209_discordance.csv
- **Source artifact(s):** evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json
- **Dataset / n:** 209_claim_paired_natural_evaluation · n = 209
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH REPRODUCTION (CPU)
- **Evidence grade:** A
- **Caveat printed on the figure:** Retrieval coverage, never accuracy.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F07 — Corpus-level evidence coverage over all 588 pooled natural claims

- **File:** `figures/F07_evidence_coverage_588_corpus.png` · PPT variant `ppt_assets/figures/F07_evidence_coverage_588_corpus.png`
- **Purpose:** Show the evidence-pool change at the largest available claim scale
- **Metric contract(s):** M07_evidence_coverage_588_corpus.csv
- **Source artifact(s):** research/prototype/outputs/evidence_coverage_v0_vs_v1.json
- **Dataset / n:** 588 pooled natural claims · n = 588
- **System designation:** Baseline vs Modified
- **Freshness:** HISTORICAL (CPU replay)
- **Evidence grade:** B
- **Caveat printed on the figure:** Corpus-level, not paired-arm.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F08 — Verifier verdict distribution on natural NyayaRAG claims

- **File:** `figures/F08_verdict_distribution_natural.png` · PPT variant `ppt_assets/figures/F08_verdict_distribution_natural.png`
- **Purpose:** Describe what the verifier actually outputs on real generated text
- **Metric contract(s):** M08_verdict_distribution.csv
- **Source artifact(s):** paired_209_metrics.json; claims_588_metrics.json
- **Dataset / n:** 209-claim paired; 588-claim aggregate · n = 209 / 588
- **System designation:** Baseline vs Modified (209) plus Modified-only (588)
- **Freshness:** FRESH (CPU)
- **Evidence grade:** n/a (descriptive)
- **Caveat printed on the figure:** Verdict counts are not correctness labels.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F09 — Premise framing on real natural data — verdict decisiveness at fixed retrieval

- **File:** `figures/F09_premise_framing_natural_batches.png` · PPT variant `ppt_assets/figures/F09_premise_framing_natural_batches.png`
- **Purpose:** Isolate the framing lever on natural text with retrieval held constant
- **Metric contract(s):** M09_premise_framing_natural_batches.csv
- **Source artifact(s):** evaluation/actual_outputs/natural_data_runs/batches/batches_analysis.json
- **Dataset / n:** natural_candidates batch1 / batch2 · n = 251 / 236
- **System designation:** Baseline vs Modified
- **Freshness:** HISTORICAL
- **Evidence grade:** B
- **Caveat printed on the figure:** Decisiveness, not measured correctness.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F10 — Premise framing on the same 147 evidence-matched natural claims

- **File:** `figures/F10_natural_147_framing_shift.png` · PPT variant `ppt_assets/figures/F10_natural_147_framing_shift.png`
- **Purpose:** Paired natural-data evidence for the framing lever
- **Metric contract(s):** M10_natural_147_framing_shift.csv
- **Source artifact(s):** research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json
- **Dataset / n:** final_validation Arm B evidence-matched subset · n = 147
- **System designation:** Baseline vs Modified
- **Freshness:** HISTORICAL (CPU)
- **Evidence grade:** B
- **Caveat printed on the figure:** Verdicts reached, not correctness.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F11 — Verifier confidence distribution by verdict — 588-claim natural aggregate

- **File:** `figures/F11_confidence_distribution_588.png` · PPT variant `ppt_assets/figures/F11_confidence_distribution_588.png`
- **Purpose:** Show how decisively the verifier reaches each verdict on real claims
- **Metric contract(s):** M11_confidence_by_verdict_588.csv
- **Source artifact(s):** evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json
- **Dataset / n:** 588_claim_natural_aggregate · n = 390 of 588
- **System designation:** Modified only (no baseline arm exists)
- **Freshness:** FRESH (CPU)
- **Evidence grade:** n/a (descriptive)
- **Caveat printed on the figure:** Confidence is not correctness.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F12 — Confidence-threshold sensitivity on GOLD-01, both premise framings

- **File:** `figures/F12_confidence_threshold_sensitivity.png` · PPT variant `ppt_assets/figures/F12_confidence_threshold_sensitivity.png`
- **Purpose:** Show the production threshold is in a flat, non-fragile region
- **Metric contract(s):** M12_confidence_threshold_sweep.csv
- **Source artifact(s):** research/prototype/outputs/threshold_sensitivity_analysis.json
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH (replay)
- **Evidence grade:** B
- **Caveat printed on the figure:** Sensitivity description, not a tuning result.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F13 — Selective-correction funnel — five populations kept strictly separate

- **File:** `figures/F13_correction_funnel.png` · PPT variant `ppt_assets/figures/F13_correction_funnel.png`
- **Purpose:** Show where correction attempts are stopped, per population
- **Metric contract(s):** M13_correction_funnel.csv
- **Source artifact(s):** final_metrics.json; final_gpu_validation_metrics.json; labeled_correction_validation_gpu_metrics.json
- **Dataset / n:** synthetic + natural targeted + natural cumulative · n = 59 / 209 / 56
- **System designation:** Baseline vs Modified (within each population)
- **Freshness:** HISTORICAL (GPU)
- **Evidence grade:** C
- **Caveat printed on the figure:** Never pool populations into one rate.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F14 — Correction outcomes by population — shipped vs each rejection reason

- **File:** `figures/F14_correction_outcomes.png` · PPT variant `ppt_assets/figures/F14_correction_outcomes.png`
- **Purpose:** Show that almost every correction attempt is stopped by a safety gate
- **Metric contract(s):** M14_correction_outcomes.csv
- **Source artifact(s):** final_metrics.json; final_gpu_validation_metrics.json; labeled_correction_validation_gpu_metrics.json
- **Dataset / n:** synthetic + natural targeted + natural cumulative · n = 59 / 209 / 56
- **System designation:** Baseline vs Modified (within each population)
- **Freshness:** HISTORICAL (GPU)
- **Evidence grade:** C
- **Caveat printed on the figure:** n too small for a statistical shipping-rate claim.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F15 — Observed safety-gate behaviour across the full tested correction history

- **File:** `figures/F15_safety_observations.png` · PPT variant `ppt_assets/figures/F15_safety_observations.png`
- **Purpose:** Evidence the safety layer is the binding constraint, and that nothing unsafe shipped
- **Metric contract(s):** M15_safety_observations.csv
- **Source artifact(s):** final_metrics.json; final_gpu_validation_metrics.json
- **Dataset / n:** all tested correction attempts · n = 122
- **System designation:** Modified system's gates (cumulative)
- **Freshness:** HISTORICAL
- **Evidence grade:** n/a (observed counts)
- **Caveat printed on the figure:** Observed counts, not a safety guarantee.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F16 — Ablation evidence strength for all eight studied factors

- **File:** `figures/F16_ablation_evidence_strength.png` · PPT variant `ppt_assets/figures/F16_ablation_evidence_strength.png`
- **Purpose:** Communicate honestly how well each design decision is evidenced
- **Metric contract(s):** M16_ablation_matrix.csv
- **Source artifact(s):** evaluation/ablation/ABLATION_SUMMARY.json
- **Dataset / n:** 8 named ablation factors · n = 3–420 per factor
- **System designation:** Baseline vs Modified per factor
- **Freshness:** MIXED
- **Evidence grade:** A–E
- **Caveat printed on the figure:** Grade is evidence strength, not effect size.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F17 — Runtime and peak VRAM per experiment arm

- **File:** `figures/F17_runtime_resource.png` · PPT variant `ppt_assets/figures/F17_runtime_resource.png`
- **Purpose:** Give the mentor a realistic cost picture for each stage
- **Metric contract(s):** M17_runtime_resource.csv
- **Source artifact(s):** final_gpu_validation_metrics.json; final_metrics.json; gold01_metrics.json
- **Dataset / n:** mixed experiment arms · n = 10–420
- **System designation:** Baseline vs Modified within paired arms
- **Freshness:** MIXED
- **Evidence grade:** n/a (resource)
- **Caveat printed on the figure:** Runtime is not a correctness measure.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F18 — Evidence coverage across every natural-data regime in the project

- **File:** `figures/F18_natural_regimes_coverage.png` · PPT variant `ppt_assets/figures/F18_natural_regimes_coverage.png`
- **Purpose:** Give the honest spread rather than a single flattering number
- **Metric contract(s):** M18_natural_regimes_coverage.csv
- **Source artifact(s):** batches_analysis.json; paired_209_metrics.json; claims_588_metrics.json
- **Dataset / n:** 11 natural-data regimes · n = 29–588
- **System designation:** Mixed baseline and modified regimes
- **Freshness:** MIXED
- **Evidence grade:** n/a (descriptive)
- **Caveat printed on the figure:** Not a trend; regimes are not comparable samples.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F19 — Correction shipping rate: synthetic stress set vs natural data

- **File:** `figures/F19_synthetic_vs_natural_transfer.png` · PPT variant `ppt_assets/figures/F19_synthetic_vs_natural_transfer.png`
- **Purpose:** State the synthetic-to-natural transfer gap explicitly rather than hiding it
- **Metric contract(s):** M19_synthetic_vs_natural_transfer.csv
- **Source artifact(s):** research/prototype/outputs/final_metrics.json
- **Dataset / n:** synthetic vs natural correction attempts · n = 36 / 56 / 10
- **System designation:** Modified system across two populations
- **Freshness:** HISTORICAL (GPU)
- **Evidence grade:** D
- **Caveat printed on the figure:** Disjoint populations; never plot as a single trend.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F20 — Why claims resolve to NO_EVIDENCE — audit over all 797 claims

- **File:** `figures/F20_no_evidence_taxonomy.png` · PPT variant `ppt_assets/figures/F20_no_evidence_taxonomy.png`
- **Purpose:** Explain the dominant natural-data outcome honestly
- **Metric contract(s):** M20_no_evidence_taxonomy.csv
- **Source artifact(s):** research/prototype/outputs/no_evidence_taxonomy_v3.json
- **Dataset / n:** 797 pooled claims · n = 797 (260 NO_EVIDENCE)
- **System designation:** Modified system's retrieval stage
- **Freshness:** HISTORICAL
- **Evidence grade:** B
- **Caveat printed on the figure:** NO_EVIDENCE is a corpus limit, not a detected error.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F21 — Claim-parser fix (commit 223eb9d) — re-parse of the same 30 generated texts

- **File:** `figures/F21_claim_parser_fix_n30.png` · PPT variant `ppt_assets/figures/F21_claim_parser_fix_n30.png`
- **Purpose:** Show the one code-level (not configuration-level) improvement measured in the project
- **Metric contract(s):** M21_parser_fix_n30.csv
- **Source artifact(s):** research/prototype/outputs/parser_fix_before_after_n30.json
- **Dataset / n:** n30_reparse · n = 30 cases
- **System designation:** Baseline vs Modified (parser code version)
- **Freshness:** HISTORICAL REPRODUCTION
- **Evidence grade:** B
- **Caveat printed on the figure:** Not a 1:1 paired-claim comparison.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F22 — GPU reproducibility crosscheck — historical run vs fresh re-execution

- **File:** `figures/F22_gpu_reproduction_crosscheck.png` · PPT variant `ppt_assets/figures/F22_gpu_reproduction_crosscheck.png`
- **Purpose:** Demonstrate the reported GPU results are independently reproducible
- **Metric contract(s):** M22_gpu_reproduction_crosscheck.csv
- **Source artifact(s):** final_gpu_validation_metrics.json; step10b_final_gpu_validation_metrics.json
- **Dataset / n:** 209-claim paired + 10-case targeted correction · n = 209 / 10
- **System designation:** Modified system, two machines
- **Freshness:** FRESH vs HISTORICAL
- **Evidence grade:** A (reproducibility only)
- **Caveat printed on the figure:** Determinism evidence, not accuracy evidence.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F23 — Component regression coverage — research/prototype/tests/

- **File:** `figures/F23_component_test_coverage.png` · PPT variant `ppt_assets/figures/F23_component_test_coverage.png`
- **Purpose:** Show the behavioural test surface behind each pipeline stage
- **Metric contract(s):** M23_component_test_matrix.csv
- **Source artifact(s):** evaluation/metrics/COMPONENT_TEST_MATRIX.csv
- **Dataset / n:** research/prototype/tests/ · n = 205
- **System designation:** Modified system (current code)
- **Freshness:** FRESH
- **Evidence grade:** n/a (software behaviour)
- **Caveat printed on the figure:** Software behaviour, not accuracy.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F24 — Canonical evidence pool available to the verifier in each system

- **File:** `figures/F24_evidence_pool_composition.png` · PPT variant `ppt_assets/figures/F24_evidence_pool_composition.png`
- **Purpose:** Make the single largest structural difference between the systems concrete
- **Metric contract(s):** M24_evidence_pool_composition.csv
- **Source artifact(s):** config/prototype.yaml; research/data/evidence/*.jsonl via src/data_loader.py
- **Dataset / n:** research/data/evidence/ · n = 59 vs 136 usable records
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH
- **Evidence grade:** A
- **Caveat printed on the figure:** Audit-excluded records are never used as premises.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

### F25 — Scope-gate behaviour replay on 11 real historical scope violations

- **File:** `figures/F25_scope_gate_replay.png` · PPT variant `ppt_assets/figures/F25_scope_gate_replay.png`
- **Purpose:** Show precisely what the relaxed scope check did and did not change
- **Metric contract(s):** M25_scope_gate_replay.csv
- **Source artifact(s):** evaluation/ablation/scope_check_replay_fresh.json
- **Dataset / n:** 11 real scope violations · n = 11
- **System designation:** Baseline vs Modified
- **Freshness:** FRESH REPRODUCTION
- **Evidence grade:** C
- **Caveat printed on the figure:** Stops at the gate; downstream shipping not verified.
- **Generated by:** `Output_phase_3_vedant/scripts/generate_figures.py`

## Classification rules applied throughout

| Class | Meaning | Where it is used |
|---|---|---|
| GOLD | The dataset carries real per-item labels, so accuracy / precision / recall / F1 are legitimate | GOLD-01 (420 curated items), GOLD-02 (59 synthetic items) |
| METRIC-ONLY | Natural NyayaRAG data with no independent correctness label; only descriptive and paired-comparative statements are permitted | every natural-data figure |
| BEHAVIOUR | A software invariant asserted by a test; says nothing about accuracy | F23 component coverage |
| HISTORICAL | Cited from a committed prior-session artifact and NOT re-executed here | every GPU-dependent correction figure |
| PROVISIONAL | Claude-generated labels, never lawyer-verified | **excluded from this package entirely** — see NOT_GENERATED_REGISTER.md |

## Standing prohibitions honoured by every figure in this package

- No natural-data result is ever called accuracy, precision, recall or F1.
- GOLD and METRIC-ONLY values are never averaged, pooled or plotted as one series.
- Synthetic and natural correction rates are never merged into a single rate (see F19).
- No legal-correctness claim is made anywhere; no lawyer ground truth exists in this project.
- No additive or interaction effect between the four production levers is asserted; that experiment does not exist (F16, Grade E).

