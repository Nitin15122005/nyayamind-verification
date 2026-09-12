# Safety results (all experiments, historical + fresh)

Rows above the line are from the archived Output_phase_3_vedant package; rows below extend it with every safety-relevant observation from work done since 2026-09-06.

| Safety observation | Count | Denominator | Mechanism (src/pipeline.py) | Source artifact |
|---|---|---|---|---|
| Unsafe corrections shipped | 0 | 122 correction attempts (56 natural + 66 synthetic) | ENTAILED-only shipping gate + scope gate + sibling-regression net | research/prototype/outputs/final_metrics.json |
| Scope-gate rejections (natural, cumulative) | 18 | 56 natural correction attempts | pipeline._scope_violation() | research/prototype/outputs/final_metrics.json |
| Re-verification-not-ENTAILED rejections (natural, cumulative) | 37 | 56 natural correction attempts | ENTAILED-only shipping gate | research/prototype/outputs/final_metrics.json |
| Sibling-regression rejections observed (209-claim paired, Arm B) | 0 | 5 correction attempts | pipeline._reverify_sibling_regressions() | research/prototype/outputs/final_gpu_validation_metrics.json |
| Corrections shipped (natural, cumulative) | 1 | 56 natural correction attempts | passed every gate | research/prototype/outputs/final_metrics.json |
| Unsafe corrections shipped (assertion-aware mechanism, n=10 paired replay) | 0 | 10 | apply_selective_correction_assertion_aware() full safety-gate chain | research/prototype/outputs/assertion_aware_correction_experiment_comparison.json |
| Sibling-regression gate rejections (assertion-aware, n=10 replay) | 2 | 10 | pipeline._reverify_sibling_regressions() (run UNCONDITIONALLY for this mechanism) | research/prototype/outputs/error_propagation_matrix.csv |
| Structural-span-lost rejections (assertion-aware, n=10 replay) | 0 | 10 | NEW check: a multi-element assertion_spans claim's non-content span surviving the edit | research/prototype/outputs/error_propagation_matrix.csv |
| Invalid/malformed-span rejections (assertion-aware, n=10 replay) | 0 | 10 | NEW check: _correction_target_spans() fail-closed on malformed assertion_spans | research/prototype/outputs/error_propagation_matrix.csv |
| Wrong-Act adversarial accepts, BM25 fuzzy matching (9 pre-registered should-not-match cases) | 6 | 9 | src/retrieval_signals.py Bm25ActIndex (evaluated, OFF by default) | research/prototype/outputs/retrieval_signal_benchmark_results.jsonl |
| Wrong-Act adversarial accepts, embedding fuzzy matching (9 pre-registered should-not-match cases) | 7 | 9 | src/retrieval_signals.py EmbeddingActIndex (evaluated, OFF by default) | research/prototype/outputs/retrieval_signal_benchmark_results.jsonl |
| Wrong-Act adversarial accepts, Jaccard fuzzy matching (9 pre-registered should-not-match cases, PRODUCTION method) | 0 | 9 | src/evidence_matcher.py (production default) | research/prototype/outputs/retrieval_signal_benchmark_results.jsonl |
| ENTAILED<->CONTRADICTED reversals from assertion_span_primary_hypothesis (n=6 real 'respectively' claims) | 0 | 6 | verification.assertion_span_primary_hypothesis (evaluated, OFF by default) | research/prototype/outputs/assertion_spans_primary_hypothesis_benchmark.jsonl |
