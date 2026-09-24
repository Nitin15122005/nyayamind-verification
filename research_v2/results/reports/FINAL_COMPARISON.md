# FINAL COMPARISON

## 1. Research question
Whether the requested local Qwen3-4B-Instruct-2507 + ModernBERT-large-NLI stack improves NyayaMind statutory-grounding verification over Qwen2.5-7B-Instruct + DeBERTa-v3, holding the existing legal pipeline fixed.

## 2. Models and revisions
- Baseline generator/corrector: `Qwen/Qwen2.5-7B-Instruct`.
- Baseline verifier: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`.
- V2 generator/corrector: `Qwen/Qwen3-4B-Instruct-2507` at `cdbee75f17c01a7cc42f958dc650907174af0554`.
- V2 verifier: `tasksource/ModernBERT-large-nli` at `ca476cb923a8637073d4ceb0f19f7fc236e260d4`.
- The local model config hashes matched the downloaded checkpoint revision metadata; local weight directories are git-ignored.

## 3. Hardware and environment
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU; total memory: 6438780928 bytes.
- Python 3.11.9; PyTorch 2.11.0+cu128; Transformers 5.17.0; CUDA 12.8; Accelerate 1.15.0; bitsandbytes 0.50.2.
- Qwen3 ran via the `research_v2/.venv` environment using Accelerate 1.15.0. Host/production dependencies were not changed.
- Full run environment: [environment.json](environment.json); per-run environment and configuration are stored alongside raw predictions.

## 4. Experimental design
GOLD verifier tests used the same frozen premise/hypothesis pairs, labels, labeled-premise framing, 0.70 threshold, and verdict mapping. Full pipeline imported existing claim parsing, evidence matching, safety gates, correction policy, sibling checks, and reverification read-only. The Qwen3 adapter used NF4 4-bit, double quantization, bfloat16 compute, greedy decoding, seed 42, temperature/top-p 1.0, 200 generation tokens (220 for correction), and an 8192-token input ceiling that fails rather than silently truncating. ModernBERT uses the checkpoint config label mapping and 2048-token maximum; long premises are chunked in order with the complete claim repeated in each chunk, and the adapter records chunks and any aggregated/prefix verdict difference.

## 5. Datasets
GOLD-01: frozen n=420 three-class benchmark. GOLD-02: frozen n=59 contradiction-only synthetic fixture. Natural analysis: existing final-validation set and both existing 50-case candidate batches. Full pipeline: existing n=50 final-validation inputs. Natural/full-pipeline records have no independent legal correctness labels.

## 6. Baseline and 7. V2
Fresh paired benchmark metrics are shown as baseline / V2. Historical GOLD-01 labeled-premise DeBERTa result (accuracy 0.9714, macro-F1 0.9684) is preserved and matched by fresh baseline runs.

## 8-9. Controlled GOLD results
| Benchmark | n | Accuracy B / V2 | Macro-F1 B / V2 | CONTRADICTED recall B / V2 | Delta macro-F1 / contradiction recall |
|---|---:|---:|---:|---:|---:|
| GOLD01 | 420 | 0.9714 / 0.9381 | 0.9684 / 0.9299 | 0.9322 / 0.8559 | -0.0385 / -0.0763 |
| GOLD02 | 59 | 0.5424 / 0.4576 | 0.2344 / 0.2093 | 0.5424 / 0.4576 | -0.0251 / -0.0847 |

GOLD-01 baseline confusion matrix:
```json
{
  "ENTAILED": {
    "ENTAILED": 184,
    "CONTRADICTED": 0,
    "NOT_ENOUGH_INFORMATION": 0
  },
  "CONTRADICTED": {
    "ENTAILED": 5,
    "CONTRADICTED": 110,
    "NOT_ENOUGH_INFORMATION": 3
  },
  "NOT_ENOUGH_INFORMATION": {
    "ENTAILED": 0,
    "CONTRADICTED": 4,
    "NOT_ENOUGH_INFORMATION": 114
  }
}
```
GOLD-01 V2 confusion matrix:
```json
{
  "ENTAILED": {
    "ENTAILED": 184,
    "CONTRADICTED": 0,
    "NOT_ENOUGH_INFORMATION": 0
  },
  "CONTRADICTED": {
    "ENTAILED": 8,
    "CONTRADICTED": 101,
    "NOT_ENOUGH_INFORMATION": 9
  },
  "NOT_ENOUGH_INFORMATION": {
    "ENTAILED": 1,
    "CONTRADICTED": 8,
    "NOT_ENOUGH_INFORMATION": 109
  }
}
```
GOLD-02 contains 59 gold contradictions and no other class. Report contradiction precision/recall; its macro-F1 is not a supported three-class measure.

## 10. Natural-data results (descriptive only)
| Dataset | Paired claims | Disagreements | Evidence coverage B / V2 | Truncated pair count B / V2 | Low-confidence rate B / V2 | Mean latency B / V2 (s) | Baseline verdict counts | V2 verdict counts |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `final_gpu_validation_B.jsonl` | 209 | 21 | 0.7033 / 0.7033 | 0 / 0 | 0.0766 / 0.2249 | 0.0231 / 0.0229 | {"CONTRADICTED": 4, "ENTAILED": 36, "NOT_ENOUGH_INFORMATION": 107, "NO_EVIDENCE": 62} | {"CONTRADICTED": 3, "ENTAILED": 42, "NOT_ENOUGH_INFORMATION": 102, "NO_EVIDENCE": 62} |
| `natural_candidates_50_gpu_labeled.jsonl` | 251 | 20 | 0.6693 / 0.6693 | 0 / 0 | 0.1474 / 0.2390 | 0.0223 / 0.0271 | {"CONTRADICTED": 2, "ENTAILED": 7, "NOT_ENOUGH_INFORMATION": 159, "NO_EVIDENCE": 83} | {"CONTRADICTED": 6, "ENTAILED": 13, "NOT_ENOUGH_INFORMATION": 149, "NO_EVIDENCE": 83} |
| `natural_candidates_batch2_gpu_labeled.jsonl` | 236 | 22 | 0.4915 / 0.4915 | 0 / 0 | 0.0593 / 0.1822 | 0.0248 / 0.0255 | {"CONTRADICTED": 3, "ENTAILED": 17, "NOT_ENOUGH_INFORMATION": 96, "NO_EVIDENCE": 120} | {"CONTRADICTED": 10, "ENTAILED": 14, "NOT_ENOUGH_INFORMATION": 92, "NO_EVIDENCE": 120} |
No natural-data result is called accuracy. Disagreements are not correctness judgments. ModernBERT's per-chunk token lengths and aggregation outcomes are retained per raw prediction; the model limit is 2048 tokens.

## 11. Full pipeline and 15. 2x2 model matrix
All 2x2 generation/verifier pairs ran through generation-only (A), generation+verification (B), and selective correction (C) on the same 50 inputs. Metrics below are natural-data behavior/resource observations, not accuracy.
| Condition | Inputs | Claims | Evidence coverage | Verdict counts | Triggers | Attempts | Accepted | Gate rejections | Sibling regressions | Reverification failures | Unsafe shipments | Runtime | Peak GPU bytes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 generation only | 50 | 207 | 0.7101 | not run (generation-only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 225.18s | None |
| Qwen2.5 + DeBERTa | 50 | 207 | 0.7101 | {"CONTRADICTED": 5, "ENTAILED": 32, "NOT_ENOUGH_INFORMATION": 110, "NO_EVIDENCE": 60} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3.56s | 5151288832 |
| Qwen2.5 + DeBERTa + correction | 50 | 207 | 0.7101 | {"CONTRADICTED": 5, "ENTAILED": 32, "NOT_ENOUGH_INFORMATION": 110, "NO_EVIDENCE": 60} | 16 | 16 | 1 | 14 | 0 | 1 | 0 | 42.98s | 5364730368 |
| Qwen2.5 + ModernBERT | 50 | 207 | 0.7101 | {"CONTRADICTED": 2, "ENTAILED": 41, "NOT_ENOUGH_INFORMATION": 104, "NO_EVIDENCE": 60} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 106.68s | 6359575552 |
| Qwen2.5 + ModernBERT + correction | 50 | 207 | 0.7101 | {"CONTRADICTED": 2, "ENTAILED": 41, "NOT_ENOUGH_INFORMATION": 104, "NO_EVIDENCE": 60} | 26 | 26 | 0 | 22 | 0 | 4 | 0 | 374.37s | 6557437440 |
| Qwen3 generation only | 50 | 239 | 0.7113 | not run (generation-only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 463.41s | None |
| Qwen3 + DeBERTa | 50 | 239 | 0.7113 | {"CONTRADICTED": 19, "ENTAILED": 38, "NOT_ENOUGH_INFORMATION": 113, "NO_EVIDENCE": 69} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3.09s | 3096357888 |
| Qwen3 + DeBERTa + correction | 50 | 239 | 0.7113 | {"CONTRADICTED": 19, "ENTAILED": 38, "NOT_ENOUGH_INFORMATION": 113, "NO_EVIDENCE": 69} | 17 | 17 | 3 | 9 | 0 | 4 | 0 | 129.91s | 3237050368 |
| Qwen3 + ModernBERT | 50 | 239 | 0.7113 | {"CONTRADICTED": 19, "ENTAILED": 43, "NOT_ENOUGH_INFORMATION": 108, "NO_EVIDENCE": 69} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 91.51s | 4301483008 |
| Qwen3 + ModernBERT + correction | 50 | 239 | 0.7113 | {"CONTRADICTED": 19, "ENTAILED": 43, "NOT_ENOUGH_INFORMATION": 108, "NO_EVIDENCE": 69} | 20 | 20 | 3 | 12 | 0 | 5 | 0 | 172.78s | 4446963200 |

Paired 2x2 behavior comparisons (no ground truth):
```json
[
  {
    "comparison": "generation_only",
    "left": "baseline_A",
    "right": "v2_A",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 50,
    "n_verdict_disagreements": 33,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  },
  {
    "comparison": "primary_generation_verification",
    "left": "baseline_baseline_B",
    "right": "v2_v2_B",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 50,
    "n_verdict_disagreements": 42,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  },
  {
    "comparison": "primary_selective_correction",
    "left": "baseline_baseline_C",
    "right": "v2_v2_C",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 50,
    "n_verdict_disagreements": 42,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  },
  {
    "comparison": "generator_effect_with_deberta",
    "left": "baseline_baseline_B",
    "right": "v2_baseline_B",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 50,
    "n_verdict_disagreements": 40,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  },
  {
    "comparison": "generator_effect_with_modernbert",
    "left": "baseline_v2_B",
    "right": "v2_v2_B",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 50,
    "n_verdict_disagreements": 43,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  },
  {
    "comparison": "verifier_effect_qwen25",
    "left": "baseline_baseline_B",
    "right": "baseline_v2_B",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 0,
    "n_verdict_disagreements": 15,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  },
  {
    "comparison": "verifier_effect_qwen3",
    "left": "v2_baseline_B",
    "right": "v2_v2_B",
    "n_paired_inputs": 50,
    "n_changed_final_outputs": 0,
    "n_verdict_disagreements": 14,
    "interpretation": "Natural-data behavior comparison only; no ground truth."
  }
]
```
- Qwen2.5 generation only: mean per-input generation latency 4.4995s; peak per-input GPU memory 5172540928 bytes; tokens/input ceiling 8192, output 200, greedy, seed 42.
- Qwen3 generation only: mean per-input generation latency 9.2674s; peak per-input GPU memory 4846893568 bytes; tokens/input ceiling 8192, output 200, greedy, seed 42.

## 12. Correction comparison
Case-level correction outcomes are paired below. The primary deployment comparison had no identical flagged claim in common; the controlled generator comparison under the same ModernBERT verifier had a small overlap. Accepted means the unchanged production safety policy and final verification accepted the correction; it does not establish legal correctness without labels.
| Pair | Inputs | Same flagged case+claim | Attempts B / V2 | Accepted B / V2 | Rejected/failed B / V2 | Unsafe shipments B / V2 | Unsafe / attempts B / V2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| primary_stack | 50 | 0 | 16 / 20 | 1 / 3 | 15 / 17 | 0 / 0 | 0.0 / 0.0 |
| same_deberta_verifier_generator_effect | 50 | 0 | 16 / 17 | 1 / 3 | 15 / 14 | 0 / 0 | 0.0 / 0.0 |
| same_modernbert_verifier_generator_effect | 50 | 3 | 26 / 20 | 0 / 3 | 26 / 17 | 0 / 0 | 0.0 / 0.0 |

## 13. Safety results
Unsafe shipment definition follows the existing fail-closed correction pipeline: a correction shipped despite a non-ENTAILED final reverification. Zero unsafe shipments in this 50-case sample is not a broad guarantee. Gate counts are baseline / V2:
| Pair | Scope rejects | Citation identity rejects | Ordinal rejects | Sibling regressions | Full reverification failures | Negation caveat claims |
|---|---:|---:|---:|---:|---:|---:|
| primary_stack | 14 / 12 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 5 | 0 / 0 |
| same_deberta_verifier_generator_effect | 14 / 9 | 0 / 1 | 0 / 0 | 0 / 0 | 1 / 4 | 0 / 0 |
| same_modernbert_verifier_generator_effect | 22 / 12 | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 5 | 0 / 0 |
No separate negation-violation status exists in the existing pipeline; negation caveats suppress correction eligibility, and no caveated claims occurred in this sample.

## 14. Efficiency
GOLD-01 current DeBERTa mean inference latency=0.018363678095071615 s, peak allocated GPU=404175360 bytes; ModernBERT mean inference latency=0.025445529523841243 s, peak allocated GPU=1608684032 bytes. Qwen3 smoke load and generation telemetry are saved under `results/sanity/`; per-input generation timing and GPU-memory telemetry are in the raw prediction JSONL files for the verification conditions.

## 16. Statistical analysis
### GOLD01 (n=420)
- McNemar exact two-sided p=0.009355306625366211; baseline-only correct=20; v2-only correct=6; discordant=26.
- Paired CONTRADICTED-recall test among gold contradictions (n=118): baseline-only correct=11; V2-only correct=2; discordant=13; exact p=0.0224609375.
- Paired bootstrap accuracy: delta=-0.0333; 95% CI=[-0.05714285714285716, -0.00952380952380949]; resamples=5000.
- Paired bootstrap macro_f1: delta=-0.0385; 95% CI=[-0.06607249071741805, -0.011183574959193754]; resamples=5000.
- Paired bootstrap contradicted_recall: delta=-0.0763; 95% CI=[-0.13740458015267165, -0.01754385964912286]; resamples=5000.
### GOLD02 (n=59)
- McNemar exact two-sided p=0.1796875; baseline-only correct=7; v2-only correct=2; discordant=9.
- Paired CONTRADICTED-recall test among gold contradictions (n=59): baseline-only correct=7; V2-only correct=2; discordant=9; exact p=0.1796875.
- Paired bootstrap accuracy: delta=-0.0847; 95% CI=[-0.1864406779661017, 0.016949152542372836]; resamples=5000.
- Paired bootstrap macro_f1: delta=-0.0251; 95% CI=[-0.05673572864760906, 0.004802604802604804]; resamples=5000.
- Paired bootstrap contradicted_recall: delta=-0.0847; 95% CI=[-0.1864406779661017, 0.016949152542372836]; resamples=5000.
McNemar tests are applied to paired accuracy and, separately, gold-positive contradiction recall. Bootstrap intervals resample paired examples (5,000 draws, seed 42). GOLD-02 estimates are uncertain because n=59 and one class; intervals crossing zero and p>0.05 are inconclusive. The reported p-values are unadjusted exploratory comparisons; they do not establish broad legal-task superiority.

## 17. Error analysis
GOLD per-case inputs, gold labels, both predictions/confidences/probabilities, token lengths, and truncation status are saved in the paired JSONL files. See [error_analysis.md](error_analysis.md). Label-transition categories:
### GOLD01 disagreement transitions
- gold=NOT_ENOUGH_INFORMATION: NOT_ENOUGH_INFORMATION -> CONTRADICTED: 8
- gold=CONTRADICTED: CONTRADICTED -> NOT_ENOUGH_INFORMATION: 6
- gold=CONTRADICTED: CONTRADICTED -> ENTAILED: 5
- gold=NOT_ENOUGH_INFORMATION: CONTRADICTED -> NOT_ENOUGH_INFORMATION: 4
- gold=CONTRADICTED: ENTAILED -> NOT_ENOUGH_INFORMATION: 2
- gold=CONTRADICTED: NOT_ENOUGH_INFORMATION -> ENTAILED: 1
- gold=CONTRADICTED: ENTAILED -> CONTRADICTED: 1
- gold=NOT_ENOUGH_INFORMATION: NOT_ENOUGH_INFORMATION -> ENTAILED: 1
- gold=CONTRADICTED: NOT_ENOUGH_INFORMATION -> CONTRADICTED: 1
### GOLD02 disagreement transitions
- gold=CONTRADICTED: CONTRADICTED -> NOT_ENOUGH_INFORMATION: 7
- gold=CONTRADICTED: NOT_ENOUGH_INFORMATION -> CONTRADICTED: 2

The full-pipeline 2x2 paired artifacts separate generator-effect comparisons (same verifier) from verifier-effect comparisons (same generator). They are unlabeled natural observations; claim changes and verdict changes cannot be called model errors.

## 18. Cases where V2 improved
On GOLD-01, paired correctness records show 6 cases where V2 alone was correct; see the case-level error report.

## 19. Cases where V2 degraded
On GOLD-01, paired correctness records show 20 cases where baseline alone was correct. Net accuracy delta is -0.0333.

## 20. Model disagreements
GOLD disagreements are resolved against the fixture's unchanged gold labels and listed by transition in section 17. Natural/full-pipeline disagreements are preserved as unlabeled; the 2x2 matrix helps attribute changes to generator versus verifier without labeling one output correct.

## 21. Limitations and unsupported claims
GOLD fixtures are controlled/synthetic and do not substitute for lawyer-reviewed legal truth. GOLD-02 lacks non-contradiction cases. Natural data and full pipeline have no independent correctness labels. The Qwen3 smoke prompt is only a load/generation check, not a quality test. V2 generation/correction quality cannot be concluded from verdict distributions or acceptance counts. No weights are committed. Results are limited to this hardware, runtime, prompt/settings, and frozen sample.

## 22. Evidence-based conclusion
ModernBERT is worse than DeBERTa on GOLD-01 under the fixed labeled-premise benchmark: macro-F1 and contradiction recall are lower, with paired evidence against the baseline. GOLD-02 also points lower for contradiction recall but is inconclusive at its small single-class sample size. Qwen3 successfully loaded and generated on the RTX 4050, and the complete 2x2 natural pipeline ran; however, end-to-end natural data have no correctness labels. The measured evidence does not support replacing the current stack. The overall stack-level legal quality comparison remains inconclusive because generator/correction outputs lack independent gold judgments.
