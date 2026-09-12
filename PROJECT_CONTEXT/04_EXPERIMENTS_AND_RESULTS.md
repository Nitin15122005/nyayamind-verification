# Experiments and Results — the global map

This is a MAP, not a replacement for the detailed reports. Full narrative:
`research/prototype/results_phase3/FINAL_RESULTS.md`. Full ablation table (13 levers):
`research/prototype/results_phase3/tables/ablation/ablation_results.md`. Claim-by-claim
classification: `research/prototype/results_phase3/RESEARCH_CLAIMS.md`.

| Experiment | Component | Dataset | n | Model | CPU/GPU | Freshness | Metric | Result | Grade | Production status | Canonical source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Controlled verifier benchmark | Verifier | GOLD-01 | 420 | DeBERTa-v3-mnli | CPU | HISTORICAL | macro F1, accuracy | 0.749→0.968, 0.733→0.971 (McNemar p=4.16e-23) | A | premise_framing=labeled PROMOTED | `evaluation/actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json` |
| Synthetic stress (contradiction detection) | Verifier | GOLD-02 | 59 | DeBERTa-v3-mnli | CPU | HISTORICAL | recall | 0.356→0.458 | B | (same lever) | `evaluation/actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json` |
| Evidence coverage, paired | Retrieval | 209-claim natural | 209 | n/a | CPU | HISTORICAL + FRESH (two distinct columns) | evidence coverage | 63.2%→70.3% (McNemar p=0.0003) | A | use_evidence_v1=true PROMOTED | `evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json` |
| Evidence coverage, corpus | Retrieval | 588-record corpus | 588 | n/a | CPU | HISTORICAL | evidence coverage | 60.2%→66.3% (+36) | A | (same lever) | `evaluation/metrics/EVIDENCE_STRENGTH_MATRIX.md` |
| Claim parser fix | Parser | n=30 reparse | 30 | n/a | CPU | HISTORICAL REPRODUCTION | claims resolving to evidence | 6/30 improved, 0 worsened (sign test p=0.03) | B | commit 223eb9d + Art./Arts. PROMOTED | `results_phase3/tables/detailed_metrics/parser_metrics.csv` |
| Retrieval fuzzy-method safety | Retrieval | 30 pre-registered adversarial cases | 30 | n/a (lexical/embedding) | CPU | HISTORICAL | correct-reject rate | Jaccard 9/9, BM25 3/9, embedding 2/9 | B | Jaccard PROMOTED; BM25/embedding REJECTED | `outputs/retrieval_signal_benchmark_results.jsonl` |
| Scope-check replay | Correction/safety | 11 historical scope violations | 11 | n/a | CPU | FRESH REPRODUCTION | unblocked count | 1/11 | C (diagnostic) | atomic_scope_check=assertion_spans PROMOTED | `evaluation/ablation/scope_check_replay_fresh.json` |
| Narrow re-verification hypothesis | Correction | 3 real correction_failed cases | 3 | Qwen+DeBERTa | GPU (historical) | HISTORICAL | qualitative confidence shift | no outcome change | C (diagnostic) | narrow_reverification_hypothesis=true PROMOTED | `FINAL_PRODUCTION_CONFIG.md` §4 |
| Correction funnel, cumulative | Correction/safety | all natural attempts | 56 | Qwen+DeBERTa | GPU (historical) | HISTORICAL-ONLY | shipped / unsafe | 1/56 (1.8%), 0 unsafe | B/C | legacy correction PRODUCTION | `outputs/final_metrics.json` |
| narrow_primary_hypothesis (fresh) | Verifier | fresh natural GPU batch | 62 docs / 32 claims-arm | Qwen2.5-7B + DeBERTa | GPU | FRESH (2026-09-12) | verdict shift, correction shipped | shift toward decisive verdicts; 0 shipped both arms | B | PROMOTED (production default) | `outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json` |
| assertion_span_primary_hypothesis | Verifier | real "respectively" claims | 6 (entire population found) | DeBERTa-v3-mnli | CPU | HISTORICAL | verdict changed | 4/6 (3 NEI→ENTAILED, 1 NEI→CONTRADICTED) | C | EVALUATED, NOT PROMOTED (n too small) | `outputs/assertion_spans_primary_hypothesis_benchmark.jsonl` |
| Assertion-aware correction (paired replay) | Correction | 5 documents, 2 arms | 10 | Qwen2.5-7B + DeBERTa | GPU | FRESH (2026-09-12) | shipped | 0/10 (legacy: also 0/10 on same cases) | B | EXPERIMENTAL, NOT PROMOTED | `outputs/assertion_aware_correction_experiment_comparison.json` |
| Error propagation (assertion-aware) | Correction | same 10 paired attempts | 10 | — | — | FRESH, derived | first-failure stage | 5 safety-gate, 2 reverification, 2 sibling-regression, 1 not-triggered | descriptive | n/a | `outputs/error_propagation_matrix.csv` |
| Assertion-spans architecture integration replay | Correction | same 9 triggered attempts | 9 | — | CPU (verifier only) | FRESH, verification | target/outcome mismatches | 0 / 0 | ENGINEERING | n/a | `outputs/assertion_span_aware_integration_replay.json` |
| Confidence threshold sensitivity | Verifier | GOLD-01 stored distributions | 420 | n/a (no re-inference) | CPU | FRESH (recomputed) | macro F1 vs threshold | production 0.70 within 0.0022/0.0000 of optimum, flat plateau | B (descriptive) | confidence_threshold=0.70 unchanged | `outputs/threshold_sensitivity_analysis.md` |
| Component test suite | All | — | 302 tests | n/a | CPU | CURRENT | pass/fail | 302/302 passing | — | n/a | `research/prototype/tests/` |
| Joint four-lever isolation | All production levers | — | — | — | — | NOT_EXECUTED | — | — | E (NOT_ISOLABLE) | Never claim an additive/interaction effect | `results_phase3/tables/ablation/ablation_results.md` |

## Reading rules

- **Historical vs fresh**: some artifacts (notably the 209-paired evidence file) carry BOTH a
  `historical_*` and a `fresh_*` column for the same metric, computed under different
  conditions. Always check which field a number came from before quoting it.
- **CPU vs GPU**: verification-only re-analysis of already-generated text is CPU-safe;
  generation and correction (both Qwen calls) require GPU. This project's own established
  pattern (see `REPRODUCIBILITY.md`) is to prefer re-verifying existing text over a new GPU run.
- **Grade** (A-E) measures how well a result is EVIDENCED (isolation + sample size +
  statistical support), never effect size. Grade E means the isolating experiment does not
  exist anywhere in the project.
- This table is not exhaustive of every experiment ever run in this project's history — it is
  the map of every experiment that materially informed a production decision or is referenced
  as a headline/negative result. For the full historical experimental record, see
  `research/prototype/outputs/` (100+ dated files) and `research/prototype/REPRODUCIBILITY.md`.
