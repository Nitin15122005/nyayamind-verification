# Figure Index

References canonical figures only — no copies exist in this directory. All paths relative to
`results_phase3/`.

| # | File | Purpose | Experiment | Source | Presentation use | Caveat |
|---|---|---|---|---|---|---|
| F01 | figures/01_overview/F01_headline_baseline_vs_modified.png | Four strongest baseline-vs-modified comparisons on one axis | GOLD-01/02, 209-paired | evaluation/actual_outputs/... | Opening headline slide | Heterogeneous metric types — bar heights not interchangeable |
| F17 | figures/01_overview/F17_runtime_resource.png | Runtime/VRAM by experiment | Multiple GPU runs | outputs/*.json | Resource/engineering slide | Environmental observation, not a formal benchmark suite |
| F22 | figures/01_overview/F22_gpu_reproduction_crosscheck.png | Fresh vs historical GPU reproduction | STEP10/10B | evaluation/actual_outputs/... | Reproducibility slide | — |
| F23 | figures/01_overview/F23_component_test_coverage.png | Component test matrix (205 tests) | COMPONENT_TEST_MATRIX.csv | evaluation/components/ | Engineering-rigor slide | 205 is not a sum across components (overlap) |
| F02 | figures/02_verifier/F02_gold01_accuracy_macro_f1.png | Accuracy + macro F1, baseline vs modified | GOLD-01 (n=420) | gold01_metrics.json | Verifier results slide | Controlled benchmark |
| F03 | figures/02_verifier/F03_gold01_per_class_precision_recall_f1.png | Per-class P/R/F1 | GOLD-01 (n=420) | gold01_metrics.json | Verifier results slide | — |
| F04 | figures/02_verifier/F04_gold01_confusion_matrices.png | 3×3 confusion matrices | GOLD-01 (n=420) | gold01_metrics.json | Verifier results slide | — |
| F05 | figures/02_verifier/F05_gold02_synthetic_contradiction_detection.png | Contradiction recall | GOLD-02 (n=59) | gold02_metrics.json | Verifier results slide | No statistical test performed |
| F11 | figures/02_verifier/F11_confidence_distribution_588.png | Confidence by verdict | 588-corpus | evaluation/metrics/ | Verifier deep-dive | — |
| F12 | figures/02_verifier/F12_confidence_threshold_sensitivity.png | Macro-F1 vs threshold sweep | GOLD-01 (n=420) | evaluation/ablation/ | Verifier deep-dive | Production threshold near plateau optimum |
| **NEW** | figures/02_verifier/assertion_span_verification_shift.png | Verdict shift, full-sentence vs assertion_spans hypothesis | n=6 real "respectively" claims | outputs/assertion_spans_primary_hypothesis_benchmark.jsonl | Verifier extensions slide | Evaluated, NOT promoted (n too small) |
| F06 | figures/03_evidence_retrieval/F06_evidence_coverage_209_paired.png | Evidence coverage, paired | 209 paired | paired_209_metrics.json | Evidence/retrieval slide | See FINAL_RESULTS.md §5 historical/fresh distinction |
| F07 | figures/03_evidence_retrieval/F07_evidence_coverage_588_corpus.png | Evidence coverage, corpus | 588 corpus | evaluation/metrics/ | Evidence/retrieval slide | — |
| F20 | figures/03_evidence_retrieval/F20_no_evidence_taxonomy.png | NO_EVIDENCE taxonomy | 797 claims | evaluation/metrics/ | Evidence deep-dive | — |
| F24 | figures/03_evidence_retrieval/F24_evidence_pool_composition.png | Evidence pool composition | 136-record pool | config/prototype.yaml | Evidence deep-dive | — |
| **NEW** | figures/03_evidence_retrieval/retrieval_method_safety_comparison.png | Jaccard vs BM25 vs embedding safety | 30 pre-registered cases | outputs/retrieval_signal_benchmark_results.jsonl | Retrieval extensions slide | Jaccard remains sole production method |
| F21 | figures/04_parser/F21_claim_parser_fix_n30.png | Parser fix before/after | n=30 | evaluation/ablation/ | Parser slide | Historical reproduction |
| F13 | figures/05_correction/F13_correction_funnel.png | Correction funnel (historical) | synthetic + natural | outputs/final_metrics.json | Correction slide | — |
| F14 | figures/05_correction/F14_correction_outcomes.png | Correction outcomes breakdown | historical | outputs/final_metrics.json | Correction slide | — |
| F25 | figures/05_correction/F25_scope_gate_replay.png | Scope-gate replay | 11 historical cases | evaluation/ablation/ | Correction deep-dive | 1/11 unblocked |
| **NEW** | figures/05_correction/assertion_aware_vs_legacy_correction_funnel.png | Legacy vs assertion-aware shipping | n=10 paired | outputs/assertion_aware_correction_experiment_comparison.json | Correction extensions slide | 0/10 both — no improvement measured |
| **NEW** | figures/05_correction/error_propagation_first_failure_stage.png | First-failure-stage breakdown | n=10 paired | outputs/error_propagation_matrix.csv | Correction extensions slide | Derived programmatically |
| F15 | figures/06_safety/F15_safety_observations.png | Safety observations | 122 historical attempts | outputs/final_metrics.json | Safety slide | Extend mentally with the 10 new attempts (safety_results.csv) |
| F16 | figures/07_ablation/F16_ablation_evidence_strength.png | Ablation matrix (8 pre-09-06 factors) | Multiple | evaluation/ablation/ | Ablation slide | Table (ablation_results.md) has 5 more rows not in this figure |
| F08 | figures/08_natural_data/F08_verdict_distribution_natural.png | Verdict distribution, natural | Multiple batches | evaluation/metrics/ | Natural-data slide | — |
| F09 | figures/08_natural_data/F09_premise_framing_natural_batches.png | Premise framing, natural batches | Multiple | evaluation/metrics/ | Natural-data slide | — |
| F10 | figures/08_natural_data/F10_natural_147_framing_shift.png | 147-claim framing shift | n=147 | evaluation/metrics/ | Natural-data slide | BEHAVIORAL, not accuracy |
| F18 | figures/08_natural_data/F18_natural_regimes_coverage.png | Coverage across regimes | Multiple | evaluation/metrics/ | Natural-data deep-dive | Not a time series |
| F19 | figures/08_natural_data/F19_synthetic_vs_natural_transfer.png | Synthetic vs natural transfer | Multiple | evaluation/metrics/ | Transfer observations slide | No generalization claim |
| **NEW** | figures/08_natural_data/narrow_primary_hypothesis_verdict_shift.png | Verdict shift, narrow_primary_hypothesis | n=62 fresh | outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json | Natural-data extensions slide | Not independently significant at this n |
