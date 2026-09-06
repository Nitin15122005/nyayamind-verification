# FIGURE_INDEX — metric figures

Each figure exists twice: `figures/<name>.png` (publication density) and
`ppt_assets/figures/<name>.png` (16:9 landscape, presentation type sizes). Both are
rendered from the same locked CSV by `scripts/generate_figures.py`.

**Baseline:** Baseline: NyayaMind v0 (bare premise · evidence v0, 59 rec)  
**Modified:** Modified: NyayaMind production (labeled premise · evidence v0+v1, 136 rec)  
**Shared stack:** Generator Qwen/Qwen2.5-7B-Instruct (4-bit nf4) + Verifier MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli — identical in both systems; only configuration differs

### F01 — Headline comparison: baseline NyayaMind v0 vs modified NyayaMind production

- **File:** `F01_headline_baseline_vs_modified.png`
- **Purpose:** Show the four strongest supported baseline/modified comparisons at a glance
- **Dataset / n:** GOLD-01; GOLD-02; 209-claim paired natural · n = 420 / 59 / 209
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH · evidence grade A
- **Source:** gold01_metrics.json; gold02_metrics.json; paired_209_metrics.json
- **Do not claim:** Heterogeneous metrics on one axis; not interchangeable.

### F02 — Verifier accuracy and macro F1 on the GOLD-01 controlled benchmark

- **File:** `F02_gold01_accuracy_macro_f1.png`
- **Purpose:** Quantify the premise-framing lever on labelled ground truth
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH (CPU) · evidence grade A
- **Source:** evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json
- **Do not claim:** Benchmark performance, not legal correctness.

### F03 — Per-class precision, recall and F1 — GOLD-01 controlled benchmark

- **File:** `F03_gold01_per_class_precision_recall_f1.png`
- **Purpose:** Show where the premise-framing gain actually lands (ENTAILED recall 0.50 → 1.00)
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH (CPU) · evidence grade A
- **Source:** evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json
- **Do not claim:** Legitimate only because GOLD-01 has per-item labels.

### F04 — Verifier confusion matrices — GOLD-01 controlled benchmark

- **File:** `F04_gold01_confusion_matrices.png`
- **Purpose:** Expose the exact error structure behind the accuracy difference
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH (CPU) · evidence grade A
- **Source:** evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json
- **Do not claim:** Benchmark labels, not legal ground truth.

### F05 — Contradiction detection on the GOLD-02 synthetic stress set

- **File:** `F05_gold02_synthetic_contradiction_detection.png`
- **Purpose:** Show adversarial detection sensitivity and its residual failure mode
- **Dataset / n:** GOLD-02_synthetic_stress_set · n = 59
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH (CPU) · evidence grade A
- **Source:** evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json
- **Do not claim:** Contradictory by construction; not a natural-data accuracy claim.

### F06 — Evidence retrieval coverage on 209 paired natural claims

- **File:** `F06_evidence_coverage_209_paired.png`
- **Purpose:** The strongest natural-data baseline/modified result in the project
- **Dataset / n:** 209_claim_paired_natural_evaluation · n = 209
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH REPRODUCTION (CPU) · evidence grade A
- **Source:** evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json
- **Do not claim:** Retrieval coverage, never accuracy.

### F07 — Corpus-level evidence coverage over all 588 pooled natural claims

- **File:** `F07_evidence_coverage_588_corpus.png`
- **Purpose:** Show the evidence-pool change at the largest available claim scale
- **Dataset / n:** 588 pooled natural claims · n = 588
- **Systems shown:** Baseline vs Modified
- **Status:** HISTORICAL (CPU replay) · evidence grade B
- **Source:** research/prototype/outputs/evidence_coverage_v0_vs_v1.json
- **Do not claim:** Corpus-level, not paired-arm.

### F08 — Verifier verdict distribution on natural NyayaRAG claims

- **File:** `F08_verdict_distribution_natural.png`
- **Purpose:** Describe what the verifier actually outputs on real generated text
- **Dataset / n:** 209-claim paired; 588-claim aggregate · n = 209 / 588
- **Systems shown:** Baseline vs Modified (209) plus Modified-only (588)
- **Status:** FRESH (CPU) · evidence grade n/a (descriptive)
- **Source:** paired_209_metrics.json; claims_588_metrics.json
- **Do not claim:** Verdict counts are not correctness labels.

### F09 — Premise framing on real natural data — verdict decisiveness at fixed retrieval

- **File:** `F09_premise_framing_natural_batches.png`
- **Purpose:** Isolate the framing lever on natural text with retrieval held constant
- **Dataset / n:** natural_candidates batch1 / batch2 · n = 251 / 236
- **Systems shown:** Baseline vs Modified
- **Status:** HISTORICAL · evidence grade B
- **Source:** evaluation/actual_outputs/natural_data_runs/batches/batches_analysis.json
- **Do not claim:** Decisiveness, not measured correctness.

### F10 — Premise framing on the same 147 evidence-matched natural claims

- **File:** `F10_natural_147_framing_shift.png`
- **Purpose:** Paired natural-data evidence for the framing lever
- **Dataset / n:** final_validation Arm B evidence-matched subset · n = 147
- **Systems shown:** Baseline vs Modified
- **Status:** HISTORICAL (CPU) · evidence grade B
- **Source:** research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json
- **Do not claim:** Verdicts reached, not correctness.

### F11 — Verifier confidence distribution by verdict — 588-claim natural aggregate

- **File:** `F11_confidence_distribution_588.png`
- **Purpose:** Show how decisively the verifier reaches each verdict on real claims
- **Dataset / n:** 588_claim_natural_aggregate · n = 390 of 588
- **Systems shown:** Modified only (no baseline arm exists)
- **Status:** FRESH (CPU) · evidence grade n/a (descriptive)
- **Source:** evaluation/actual_outputs/natural_data_runs/588_claims/claims_588_metrics.json
- **Do not claim:** Confidence is not correctness.

### F12 — Confidence-threshold sensitivity on GOLD-01, both premise framings

- **File:** `F12_confidence_threshold_sensitivity.png`
- **Purpose:** Show the production threshold is in a flat, non-fragile region
- **Dataset / n:** GOLD-01_controlled_verifier_benchmark · n = 420
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH (replay) · evidence grade B
- **Source:** research/prototype/outputs/threshold_sensitivity_analysis.json
- **Do not claim:** Sensitivity description, not a tuning result.

### F13 — Selective-correction funnel — five populations kept strictly separate

- **File:** `F13_correction_funnel.png`
- **Purpose:** Show where correction attempts are stopped, per population
- **Dataset / n:** synthetic + natural targeted + natural cumulative · n = 59 / 209 / 56
- **Systems shown:** Baseline vs Modified (within each population)
- **Status:** HISTORICAL (GPU) · evidence grade C
- **Source:** final_metrics.json; final_gpu_validation_metrics.json; labeled_correction_validation_gpu_metrics.json
- **Do not claim:** Never pool populations into one rate.

### F14 — Correction outcomes by population — shipped vs each rejection reason

- **File:** `F14_correction_outcomes.png`
- **Purpose:** Show that almost every correction attempt is stopped by a safety gate
- **Dataset / n:** synthetic + natural targeted + natural cumulative · n = 59 / 209 / 56
- **Systems shown:** Baseline vs Modified (within each population)
- **Status:** HISTORICAL (GPU) · evidence grade C
- **Source:** final_metrics.json; final_gpu_validation_metrics.json; labeled_correction_validation_gpu_metrics.json
- **Do not claim:** n too small for a statistical shipping-rate claim.

### F15 — Observed safety-gate behaviour across the full tested correction history

- **File:** `F15_safety_observations.png`
- **Purpose:** Evidence the safety layer is the binding constraint, and that nothing unsafe shipped
- **Dataset / n:** all tested correction attempts · n = 122
- **Systems shown:** Modified system's gates (cumulative)
- **Status:** HISTORICAL · evidence grade n/a (observed counts)
- **Source:** final_metrics.json; final_gpu_validation_metrics.json
- **Do not claim:** Observed counts, not a safety guarantee.

### F16 — Ablation evidence strength for all eight studied factors

- **File:** `F16_ablation_evidence_strength.png`
- **Purpose:** Communicate honestly how well each design decision is evidenced
- **Dataset / n:** 8 named ablation factors · n = 3–420 per factor
- **Systems shown:** Baseline vs Modified per factor
- **Status:** MIXED · evidence grade A–E
- **Source:** evaluation/ablation/ABLATION_SUMMARY.json
- **Do not claim:** Grade is evidence strength, not effect size.

### F17 — Runtime and peak VRAM per experiment arm

- **File:** `F17_runtime_resource.png`
- **Purpose:** Give the mentor a realistic cost picture for each stage
- **Dataset / n:** mixed experiment arms · n = 10–420
- **Systems shown:** Baseline vs Modified within paired arms
- **Status:** MIXED · evidence grade n/a (resource)
- **Source:** final_gpu_validation_metrics.json; final_metrics.json; gold01_metrics.json
- **Do not claim:** Runtime is not a correctness measure.

### F18 — Evidence coverage across every natural-data regime in the project

- **File:** `F18_natural_regimes_coverage.png`
- **Purpose:** Give the honest spread rather than a single flattering number
- **Dataset / n:** 11 natural-data regimes · n = 29–588
- **Systems shown:** Mixed baseline and modified regimes
- **Status:** MIXED · evidence grade n/a (descriptive)
- **Source:** batches_analysis.json; paired_209_metrics.json; claims_588_metrics.json
- **Do not claim:** Not a trend; regimes are not comparable samples.

### F19 — Correction shipping rate: synthetic stress set vs natural data

- **File:** `F19_synthetic_vs_natural_transfer.png`
- **Purpose:** State the synthetic-to-natural transfer gap explicitly rather than hiding it
- **Dataset / n:** synthetic vs natural correction attempts · n = 36 / 56 / 10
- **Systems shown:** Modified system across two populations
- **Status:** HISTORICAL (GPU) · evidence grade D
- **Source:** research/prototype/outputs/final_metrics.json
- **Do not claim:** Disjoint populations; never plot as a single trend.

### F20 — Why claims resolve to NO_EVIDENCE — audit over all 797 claims

- **File:** `F20_no_evidence_taxonomy.png`
- **Purpose:** Explain the dominant natural-data outcome honestly
- **Dataset / n:** 797 pooled claims · n = 797 (260 NO_EVIDENCE)
- **Systems shown:** Modified system's retrieval stage
- **Status:** HISTORICAL · evidence grade B
- **Source:** research/prototype/outputs/no_evidence_taxonomy_v3.json
- **Do not claim:** NO_EVIDENCE is a corpus limit, not a detected error.

### F21 — Claim-parser fix (commit 223eb9d) — re-parse of the same 30 generated texts

- **File:** `F21_claim_parser_fix_n30.png`
- **Purpose:** Show the one code-level (not configuration-level) improvement measured in the project
- **Dataset / n:** n30_reparse · n = 30 cases
- **Systems shown:** Baseline vs Modified (parser code version)
- **Status:** HISTORICAL REPRODUCTION · evidence grade B
- **Source:** research/prototype/outputs/parser_fix_before_after_n30.json
- **Do not claim:** Not a 1:1 paired-claim comparison.

### F22 — GPU reproducibility crosscheck — historical run vs fresh re-execution

- **File:** `F22_gpu_reproduction_crosscheck.png`
- **Purpose:** Demonstrate the reported GPU results are independently reproducible
- **Dataset / n:** 209-claim paired + 10-case targeted correction · n = 209 / 10
- **Systems shown:** Modified system, two machines
- **Status:** FRESH vs HISTORICAL · evidence grade A (reproducibility only)
- **Source:** final_gpu_validation_metrics.json; step10b_final_gpu_validation_metrics.json
- **Do not claim:** Determinism evidence, not accuracy evidence.

### F23 — Component regression coverage — research/prototype/tests/

- **File:** `F23_component_test_coverage.png`
- **Purpose:** Show the behavioural test surface behind each pipeline stage
- **Dataset / n:** research/prototype/tests/ · n = 205
- **Systems shown:** Modified system (current code)
- **Status:** FRESH · evidence grade n/a (software behaviour)
- **Source:** evaluation/metrics/COMPONENT_TEST_MATRIX.csv
- **Do not claim:** Software behaviour, not accuracy.

### F24 — Canonical evidence pool available to the verifier in each system

- **File:** `F24_evidence_pool_composition.png`
- **Purpose:** Make the single largest structural difference between the systems concrete
- **Dataset / n:** research/data/evidence/ · n = 59 vs 136 usable records
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH · evidence grade A
- **Source:** config/prototype.yaml; research/data/evidence/*.jsonl via src/data_loader.py
- **Do not claim:** Audit-excluded records are never used as premises.

### F25 — Scope-gate behaviour replay on 11 real historical scope violations

- **File:** `F25_scope_gate_replay.png`
- **Purpose:** Show precisely what the relaxed scope check did and did not change
- **Dataset / n:** 11 real scope violations · n = 11
- **Systems shown:** Baseline vs Modified
- **Status:** FRESH REPRODUCTION · evidence grade C
- **Source:** evaluation/ablation/scope_check_replay_fresh.json
- **Do not claim:** Stops at the gate; downstream shipping not verified.

