# NyayaMind research v2: controlled model comparison

This is an isolated experiment. Existing source, fixtures, and outputs are read in place; nothing in the existing pipeline is changed by this package.

## Repository audit (2026-09-24)

The active prototype pipeline is `research/prototype/src/`, configured by `research/prototype/config/prototype.yaml`. Its documented sequence is generation (`generator.py`) → claim parsing (`claim_parser.py`) → evidence matching (`evidence_matcher.py`) → NLI (`verifier.py`) → selective correction (`corrector.py`, orchestrated in `pipeline.py`) → safety checks, sibling re-verification, and fresh re-verification (`pipeline.py`). `retrieval_signals.py` supplies optional retrieval diagnostics; production config retains Jaccard matching. No model is loaded at module import.

| Component | Existing source of truth | Audited behavior |
|---|---|---|
| Generator / corrector model | `research/prototype/config/prototype.yaml`, `src/generator.py`, `src/corrector.py` | `Qwen/Qwen2.5-7B-Instruct`; 4-bit NF4, double quantization, bfloat16 compute; CUDA device map; seed 42; greedy, 200 generation tokens and 220 correction tokens. Correction reuses the loaded generator. |
| Claim parser | `src/claim_parser.py` | Deterministic citation and assertion extraction. Imported unchanged by the existing pipeline. |
| Evidence matcher | `src/evidence_matcher.py`, `src/retrieval_signals.py` | Exact and fuzzy matching, top-k 1; Jaccard fallback threshold 0.8. |
| NLI verifier | `src/verifier.py` | Exact model: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`; reads `id2label` from checkpoint config. |
| Premise construction | `src/verifier.py::format_premise`, `src/pipeline.py` | Primary framing is `labeled`: matched evidence provision identity + canonical evidence text. GOLD-01 runner directly verifies its provided pairs; pipeline runs use matched evidence. |
| Threshold / low confidence | `src/verifier.py::NLIVerifier.verify` | Softmax argmax confidence `< 0.70` becomes `NOT_ENOUGH_INFORMATION` with `sub_reason="low_confidence"`; otherwise maps entailment/contradiction/neutral to ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION. |
| Correction policy / safety | `src/pipeline.py`, `src/corrector.py`, config | At most one first eligible claim; CONTRADICTED at any confidence or low-confidence NEI triggers; high-confidence NEI and NO_EVIDENCE do not. Sentence/assertion-scoped deterministic splice, fail-closed gates, sibling checks, then fresh full re-verification. Current config uses assertion-span scope checking and narrow primary/reverification hypotheses. |
| Tests | `research/prototype/tests/` | Existing suite; documented historical count has varied (205 in an older reproducibility document, 298 passed/1 skipped in the user-provided historical claim). This experiment will record an actual run instead of treating either as current. |

### Evaluation inputs and historical artifacts

* GOLD-01: frozen 420-row fixture at `research/prototype/evaluation/expected_outputs/controlled_benchmark_gold/controlled_verifier_benchmark.jsonl`. Labels are construction-rule assigned; do not rebuild or edit it. Historical labeled DeBERTa metrics are also present at `research/prototype/outputs/controlled_benchmark_deberta_labeled_metrics.json` and the evaluation workspace's `actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json`.
* GOLD-02: frozen 59-row fixture at `research/prototype/evaluation/expected_outputs/synthetic_stress_gold/run_synthetic_stress.jsonl`; all expected labels are CONTRADICTED by deterministic construction (there is no literal label field).
* Natural/unlabeled sources include the 588-claim derived coverage population, the paired 209-claim / 50-case final validation, and natural batches documented in `research/prototype/evaluation/inputs/README.md`. Natural verdicts are descriptive, not legal accuracy.
* Existing evaluation commands are documented in `research/prototype/REPRODUCIBILITY.md` and each script header. The repo's current `run_*.py` inventory is: `research/prototype/scripts/{run_assertion_aware_correction_experiment,run_controlled_benchmark,run_eval_30,run_final_gpu_validation,run_labeled_correction_validation_gpu,run_mvp,run_narrow_primary_hypothesis_gpu_ablation,run_natural_candidates_50_gpu,run_natural_targeted_eval,run_synthetic_stress_eval,run_verifier_benchmark}.py`; and `research/prototype/evaluation/scripts/{run_component_demos,run_gold01_evaluation,run_gold02_evaluation,run_gpu_209_reproduction,run_natural_209_paired_evaluation,run_natural_588_evaluation}.py`. Golden runners are invoked as `research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/run_gold01_evaluation.py` and `.../run_gold02_evaluation.py`; generation commands include `.../research/prototype/scripts/run_final_gpu_validation.py --device cuda` and `.../run_labeled_correction_validation_gpu.py`. Existing scripts write to their own evaluation workspace; v2 scripts write only under `research_v2/`.

### Isolation and reuse

The existing `research/prototype/src/` is imported read-only for claim parsing, matching, pipeline policy, and baseline verifier behavior where interfaces allow. No production files or tests are copied or edited. New model adapters, experiment configuration, evaluation code, tests, scripts, manifests, and results live here. The frozen fixtures and natural input files are referenced by relative path and SHA-256 manifest rather than duplicated. Model weights are never stored in Git.

## Models and fixed primary design

| Role | Baseline | V2 |
|---|---|---|
| Generator/corrector | `Qwen/Qwen2.5-7B-Instruct` | `Qwen/Qwen3-4B-Instruct-2507` |
| NLI verifier | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | `tasksource/ModernBERT-large-nli` |

The primary comparison is baseline pair vs. v2 pair. GOLD runs isolate verifier replacement on identical premise/hypothesis pairs; pipeline runs use identical inputs, prompts and policy. Generation remains greedy and seed 42, with the existing max token limits unless an adapter-specific technical constraint is explicitly recorded. Confidence remains 0.70. The 2×2 generator/verifier matrix is an attribution experiment. Quality, safety, and efficiency are reported separately. No natural-data metric is called accuracy.

### Adapter-specific technical settings

Qwen3 uses the exact requested Instruct-2507 checkpoint. Its checkpoint declares Transformers 4.51.0 and its model card identifies the checkpoint as non-thinking; the adapter therefore uses the repository chat template without adding a thinking-mode flag. It keeps NF4, double quantization, bfloat16 compute, greedy decoding, seed 42, temperature/top-p metadata at 1.0, and 200 output tokens (220 for correction). The adapter caps prompt input at 8192 tokens as a memory guard for the 6 GB card and fails closed on longer inputs; it does not silently trim case facts. The active experiment environment uses Python 3.11.9, torch 2.11.0+cu128, Transformers 5.17.0, bitsandbytes 0.50.2, and accelerate 0.33.0. This differs from the existing 4.40.2 production pin because the requested Qwen3 architecture is unsupported by that older Transformers release.

ModernBERT uses the checkpoint's own label map (verified as 0 entailment, 1 neutral, 2 contradiction) and its 2048-token limit. Inputs within the limit use one full pair. Longer premises are split into ordered chunks while the complete claim is repeated in every chunk; no evidence tokens are discarded. The adapter records chunk count and each probability vector, averages the per-chunk class distributions with equal weight, then applies the unchanged argmax/0.70 rule. It also records the first-chunk-only verdict to quantify whether using the full evidence changes a verdict. This is a necessary model-input adaptation, so long-pair outcomes are reported separately from ordinary single-pair results.

Primary metric ordering is fixed: NLI macro-F1, CONTRADICTED recall, CONTRADICTED F1, accuracy, ENTAILED recall, then NEI precision/recall. Safety ordering is unsafe shipments, safety-gate violations, sibling regressions, correction success, correction acceptance. Efficiency ordering is peak VRAM, latency, throughput.

## Experiment matrix

| Experiment | Conditions | Data / output |
|---|---|---|
| Sanity | DeBERTa and ModernBERT label/schema/determinism checks | Synthetic 10/10/10 class cases plus real claim pairs; `results/sanity/` |
| GOLD-01 | DeBERTa vs ModernBERT; identical 420 pairs | `results/paired/gold01/`, metrics, paired analysis |
| GOLD-02 | DeBERTa vs ModernBERT; identical 59 pairs | `results/paired/gold02/` |
| Natural | Both verifier stacks on existing natural records | Coverage/verdict distributions and paired disagreements; no correctness labels |
| Full pipeline | A generation; B generation+verification; C selective correction, both stacks | Natural cases, with policy and safety instrumentation |
| Correction | Same flagged cases, Qwen2.5 vs Qwen3 | Paired correction and final-decision records |
| 2×2 | Qwen2.5/Qwen3 × DeBERTa/ModernBERT | Attribution where hardware permits |

## Reproducibility and current execution environment

The audited host exposes an NVIDIA GeForce RTX 4050 Laptop GPU with 6141 MiB VRAM. The default `python` is 3.14.7; Python 3.11 is also installed. PyTorch, Transformers, PyYAML, and pytest are importable under the default interpreter; scikit-learn and bitsandbytes are not. CUDA/package versions and actual GPU visibility must be captured by the environment report at run time. CPU is only used when explicitly selected. Large models are loaded serially to avoid invalid VRAM/latency measurements. Each run gets a unique ID and immutable raw prediction files.

Historical GOLD-01 labeled DeBERTa artifact reports n=420, accuracy 0.9714286 and macro-F1 0.9683613. It is a reference to verify against a fresh same-fixture run, not a value baked into v2 results. Older bare-premise metrics are an ablation, not the primary baseline. GOLD-02 historical artifacts are similarly references only.

### Historical claims checked against artifacts

* The 59-record v0 and 136-record v0+v1 usable evidence counts are documented in `research/prototype/evaluation/inputs/README.md` and the evidence audit files. The 63.2%→70.3% coverage figures are present in the committed 209-claim report; these are evidence coverage, not legal accuracy.
* The narrow-hypothesis 5→9 ENTAILED counts and zero ENTAILED↔CONTRADICTED reversals are reported in `outputs/16gb_final_execution_report.md` for n=62. They are historical behavior comparisons, not independent gold judgments.
* The supplied claim of 132 historical correction attempts does not reconcile with the consolidated `outputs/final_research_results.md`: it reports 56 natural attempts and 66 synthetic attempts (122 total), with 0 unsafe shipments. The natural-only denominator is 56. The reported parser comparison (6/30 improved, 0 worsened) is not yet confirmed from an independently machine-readable summary in this audit and will not be treated as verified.
* The supplied “298 passed, 1 skipped” suite count is not current for the available default interpreter. The executed repository suite under Python 3.14.7 completed at 291 passed, 10 failed, 1 skipped. The failing assertions include correction output/sibling-preservation expectations; no existing test or source was edited. This runtime is also unsuitable for model benchmarking because its PyTorch is CPU-only.

The exact ModernBERT checkpoint config was checked: label IDs are 0=entailment, 1=neutral, 2=contradiction and `max_position_embeddings=2048`. V2 discovers those labels at load time. The exact Qwen3 checkpoint config declares `transformers_version=4.51.0`; Qwen3 requires a newer Transformers implementation than the project's historical 4.40.2 pin. Source checkpoint references: [Qwen3 config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/main/config.json), [Qwen3 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), [ModernBERT NLI config](https://huggingface.co/tasksource/ModernBERT-large-nli/blob/main/config.json).

Use `py -3.11 research_v2/scripts/run_all.py --device cuda:0` for the master workflow. `run_all.py` runs sanity checks, paired GOLD-01/GOLD-02, three paired natural data inputs (50 final-validation cases, plus two existing 50-case labeled batches), and the full 2×2 pipeline on the existing 50-case final-validation set; flags can skip phases when reproducing a subset. Individual commands are `py -3.11 research_v2/scripts/run_sanity.py --model baseline|v2 --device cuda:0`, `run_gold01.py --model baseline|v2 --device cuda:0`, `run_gold02.py --model baseline|v2 --device cuda:0`, `run_natural.py --model baseline|v2 --device cuda:0`, `run_full_pipeline.py --matrix --limit 50`, and `run_correction_comparison.py --run-dir <completed-run-dir>`. The scripts record versions, commit, timestamp, config, fixture hash, command, runtime, and hardware. If an exact run cannot execute due to missing runtime compatibility, package, download, VRAM, or model behavior, retain its failure log and report the blocker; never silently substitute a model or revise labels/settings.

### Execution status (2026-09-24)

The fresh DeBERTa GOLD-01 baseline ran on the RTX 4050 (420 examples; accuracy 0.9714, macro-F1 0.9684), matching the historical labeled-premise figures. GOLD-02 DeBERTa baseline ran on 59 contradiction cases (CONTRADICTED precision 1.000, recall 0.542). DeBERTa descriptive baseline runs completed for all three existing natural inputs. The 35-pair DeBERTa sanity set passed schema, finite-confidence, label-map, and deterministic-repeat checks. The separate research_v2 suite passes 14 tests.

The requested ModernBERT checkpoint transfer repeatedly stalled with incomplete weights; no v2 inference ran and its runtime label map was not exercised. Qwen3 was not attempted because the paired stack could not be run. Paired GOLD, paired natural, full-pipeline, correction, safety, 2x2, and statistical comparisons are inconclusive and incomplete. See `logs/modernbert_download_attempt.md` and `results/reports/FINAL_COMPARISON.md`. This execution status is not a model-quality judgment.

The existing repository test suite was separately run under Python 3.14.7: 291 passed, 10 failed, 1 skipped. No existing source or test was modified. These failures are unrelated to research_v2 and are not evidence about v2.

## Completed local-checkpoint execution (2026-09-24; supersedes the earlier blocked status above)

The exact requested model checkpoints were available locally and evaluated; no model substitutions were made. Verified model revisions are Qwen3 `cdbee75f17c01a7cc42f958dc650907174af0554` and ModernBERT `ca476cb923a8637073d4ceb0f19f7fc236e260d4`. ModernBERT's runtime label mapping was read from the loaded config and checked by sanity inference: 0=entailment, 1=neutral, 2=contradiction. The 35-case sanity run passed finite probability, schema, determinism, and label mapping checks; no pair needed truncation (maximum observed pair was 126 tokens). Qwen3 loaded from `research_v2/models/Qwen3-4B-Instruct-2507` and generated on CUDA using the exact checkpoint. Its smoke recorded ~2.36 seconds generation latency and ~2.70 GB peak allocated GPU memory. The first host Accelerate configuration was incompatible; the isolated `.venv` uses Accelerate 1.15.0. Production dependencies were unchanged.

The active environment was Python 3.11.9, PyTorch 2.11.0+cu128, Transformers 5.17.0, Accelerate 1.15.0, bitsandbytes 0.50.2, CUDA runtime 12.8, on an NVIDIA GeForce RTX 4050 Laptop GPU (6141 MiB). ModernBERT maximum sequence length is 2048; long evidence is chunked with the full claim retained, and truncation/chunk details are recorded per example. Qwen3 uses NF4 4-bit weights, double quantization, bfloat16 compute, greedy decoding, seed 42, 8192 input-token guard, and existing 200/220 output-token settings.

Fresh GOLD-01 paired results: baseline DeBERTa accuracy 0.9714, macro-F1 0.9684; ModernBERT accuracy 0.9381, macro-F1 0.9299. Contradiction recall was 0.9322 vs 0.8559. Paired accuracy McNemar exact p=0.00936; paired contradiction-recall McNemar tests and 5,000-resample paired bootstrap intervals are in `results/reports/gold01_comparison.json`. Fresh GOLD-02 is a single-class fixture (59 contradictions only): contradiction precision 1.000 for both, recall 0.5424 baseline vs 0.4576 ModernBERT; uncertainty is substantial and comparison is inconclusive. Natural and full-pipeline results are descriptive only.

The entire Qwen2.5/Qwen3 x DeBERTa/ModernBERT 2x2 matrix completed on 50 existing final-validation inputs for generation-only, verification, and correction conditions. The correction comparison observed 0 unsafe shipments across baseline 16 and v2 20 attempts; accepted corrections were 1 and 3, respectively. This unlabeled sample does not establish correction correctness. See `results/reports/FINAL_COMPARISON.md` for measured values, failures, paired analysis, and limitations. Earlier timestamped run records remain preserved.

### Reproduction in the isolated environment

Set local-only/offline model paths, then use the research environment (not host Python):

```powershell
$env:NYAYAMIND_MODERNBERT_PATH = (Resolve-Path research_v2/models/ModernBERT-large-nli).Path
$env:NYAYAMIND_QWEN3_PATH = (Resolve-Path research_v2/models/Qwen3-4B-Instruct-2507).Path
$env:HF_HUB_OFFLINE = '1'
research_v2/.venv/Scripts/python.exe research_v2/scripts/run_all.py --device cuda:0
```

This master command runs sanity, both GOLD fixtures, the three existing natural datasets, the 2x2 full pipeline, and automatic paired correction/final reporting. Individual `run_sanity.py`, `run_gold01.py`, `run_gold02.py`, `run_natural.py`, `run_full_pipeline.py`, and `run_correction_comparison.py` scripts accept the same isolated interpreter. Unique run IDs preserve prior outputs. If creating the venv afresh, install `research_v2/requirements-research.txt` into that venv only; do not install or upgrade production dependencies.
