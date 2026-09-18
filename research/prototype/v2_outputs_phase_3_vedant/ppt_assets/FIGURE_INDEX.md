# FIGURE INDEX

Every figure in the package, with its source artifact, evidence grade, n and caveat.

`V2 FRESH` figures were regenerated on this machine for this package. `HISTORICAL` figures
come from committed artifacts that could not be rerun (no GPU / Qwen uncached / missing packages).

## V2 FRESH figures (13)

| figure | grade | n | source artifact | caveat |
|---|---|---|---|---|
| `figures/01_overview/F01_headline_original_vs_latest.png` | MIXED (GOLD + DETERMINISTIC_SYNTHETIC) | 420 / 59 / 30 docs / structural | `metrics/gold01_v2_metrics.json + gold02_v2_metrics.json + parser_original_vs_latest_v2.json + evidence_pool_composition_v2.json` | five independent experiments; must not be averaged or read as one system score |
| `figures/02_verifier/F03_verifier_accuracy_macro_f1.png` | GOLD | 420 | `metrics/gold01_v2_metrics.json` | single-lever ablation (premise_framing) |
| `figures/02_verifier/F04_verifier_per_class_precision.png` | GOLD | 420 | `metrics/gold01_v2_metrics.json` | single-lever ablation (premise_framing) |
| `figures/02_verifier/F05_verifier_per_class_recall.png` | GOLD | 420 | `metrics/gold01_v2_metrics.json` | single-lever ablation (premise_framing) |
| `figures/02_verifier/F06_verifier_per_class_f1.png` | GOLD | 420 | `metrics/gold01_v2_metrics.json` | single-lever ablation (premise_framing) |
| `figures/02_verifier/F07_confusion_original.png` | GOLD | 420 | `metrics/gold01_v2_metrics.json` | single-lever ablation (premise_framing) |
| `figures/02_verifier/F08_confusion_latest.png` | GOLD | 420 | `metrics/gold01_v2_metrics.json` | single-lever ablation (premise_framing) |
| `figures/02_verifier/F09_threshold_sensitivity.png` | GOLD | 420 | `metrics/threshold_sensitivity_v2.json` | descriptive sensitivity analysis, no significance test |
| `figures/02_verifier/F10_contradiction_detection_2x2.png` | DETERMINISTIC_SYNTHETIC | 59 | `metrics/gold02_v2_metrics.json` | synthetic; single-class set so only recall is defined; narrow lever null on this set |
| `figures/02_verifier/F11_gold01_stratified_by_condition.png` | GOLD | 420 | `metrics/gold01_v2_stratified_by_condition.json` | REQUIRED CAVEAT figure — headline is 99% attributable to attributed conditions |
| `figures/03_evidence_retrieval/F12_evidence_pool_composition.png` | DETERMINISTIC_SYNTHETIC | 59->136 records | `metrics/evidence_pool_composition_v2.json` | input property, not an accuracy/coverage metric |
| `figures/04_parser/F14_parser_progression.png` | DETERMINISTIC_SYNTHETIC | 30 documents | `metrics/parser_original_vs_latest_v2.json` | no gold labels for extraction; coverage outcome only |
| `figures/04_parser/F15_parser_match_methods.png` | DETERMINISTIC_SYNTHETIC | 30 documents | `metrics/parser_original_vs_latest_v2.json` | descriptive counts |

## HISTORICAL-evidence figures (8)

| figure | grade | n | source artifact | caveat |
|---|---|---|---|---|
| `figures/03_evidence_retrieval/F13_evidence_coverage_209_paired.png` | HISTORICAL / METRIC_ONLY | 209 | `evaluation\actual_outputs\natural_data_runs\209_paired\paired_209_metrics.json` | unlabelled natural data — coverage is a retrieval outcome, not accuracy |
| `figures/03_evidence_retrieval/F19_retrieval_method_safety.png` | HISTORICAL / BEHAVIORAL | 30 cases (9 adversarial) | `outputs/retrieval_signal_benchmark_results.jsonl` | rates are over the adversarial subset, not over 30 |
| `figures/05_verdict/F16_verdict_distribution_209_paired.png` | HISTORICAL / BEHAVIORAL | 209 | `evaluation\actual_outputs\natural_data_runs\209_paired\paired_209_metrics.json` | distribution only, no gold labels |
| `figures/06_correction/F17_correction_funnel_cumulative.png` | HISTORICAL / BEHAVIORAL | 56 | `outputs/final_metrics.json` | zero-event safety result over a small denominator; Qwen-dependent, not rerunnable |
| `figures/06_correction/F18_synthetic_vs_natural_transfer_gap.png` | HISTORICAL / BEHAVIORAL | 59 synthetic / 56 natural | `outputs/final_metrics.json` | a LIMITATION figure, not a success metric |
| `figures/06_correction/F21_assertion_aware_null_result.png` | HISTORICAL / BEHAVIORAL | 10 | `outputs/assertion_aware_correction_experiment_comparison.json` | NULL RESULT — never present as an improvement |
| `figures/07_safety/F22_safety_zero_event_outcomes.png` | HISTORICAL / BEHAVIORAL | 56 | `outputs/final_metrics.json` | zero-event; upper bound ~5.2% by rule of three; not a safety proof |
| `figures/08_ablation/F20_narrow_primary_hypothesis_shift.png` | HISTORICAL / BEHAVIORAL | 62 docs / 32 claims per arm | `outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json` | distribution shift only; null on GOLD-02; correction effect not significant |

## Deliberately absent

- `figures/09_runtime/` contains **no chart**. A runtime comparison is not possible from this
  session (historical numbers are GPU; fresh ones are CPU under a different major version).
  See `figures/09_runtime/README.md` and `NOT_GENERATED_REGISTER.md` §4.
