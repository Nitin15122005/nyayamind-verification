# Reproducibility Matrix (STEP 8)

Consolidating every reproducibility fact established across STEP 2-7. **This machine
has no NVIDIA GPU** (an AMD Radeon integrated GPU only, confirmed in STEP 2) — this
single fact governs every "fresh execution status" row below.

| Result | Source data | Code/config | Model | Hardware | Fresh execution status | Historical reproduction status | Exact command | Known limitations |
|---|---|---|---|---|---|---|---|---|
| Evidence coverage (209 paired) | `outputs/final_gpu_validation_{A,B}.jsonl` | `src/evidence_matcher.py`, current v0/v0+v1 pools | none (deterministic matching) | CPU | **Yes, this workspace, STEP 6** | Exact match to `outputs/final_gpu_validation.md` | `run_step6_209_paired_evaluation.py` | None found |
| Controlled benchmark (GOLD-01) | `expected_outputs/controlled_benchmark_gold/` | `src/verifier.py` | DeBERTa-v3-base-mnli-fever-anli | CPU (`device="cpu"`) | **Yes, this workspace, STEP 4** | Exact bit-for-bit match to `outputs/controlled_benchmark_deberta*_metrics.json` | `run_gold01_evaluation.py` | Historical run used an undocumented environment (Python 3.13.1, not the pinned 3.11.9) — found in STEP 4, results unaffected |
| Synthetic stress (GOLD-02) | `expected_outputs/synthetic_stress_gold/` | `src/pipeline.py`, `src/verifier.py` | DeBERTa | CPU | **Yes, this workspace, STEP 4** | Matches historical percentages to stated precision | `run_gold02_evaluation.py` | None found |
| 588-claim aggregate | 4 historical `outputs/*.jsonl` files (already-generated text) | `src/claim_parser.py`, `src/evidence_matcher.py`, `src/verifier.py` | DeBERTa | CPU | **Yes, this workspace, STEP 6** | Exact bit-for-bit match to `outputs/evidence_coverage_v0_vs_v1.json` | `run_step6_588_evaluation.py` | Underlying generated text is historical (real Qwen, prior GPU session) — not regenerated |
| Claim parser fix statistic | `outputs/parser_fix_before_after_n30.json` | N/A (statistic only) | none | CPU | **Statistic yes; underlying code change NO** | Matches `final_comparison`'s independent figure exactly | inline computation in `build_step7_ablation_analysis.py` | The pre-fix parser version cannot be re-executed without checking out old source (not done, per rule 1) |
| Atomic scope check replay | 2 historical `*_corrections_detail.jsonl` files | `src/pipeline.py::_scope_violation`, `src/claim_parser.py` | none (deterministic replay) | CPU | **Yes, this workspace, STEP 7** | Exact match to `outputs/atomic_scope_check_final_replay.json` | `build_step7_ablation_analysis.py` | Scope-gate outcome only; does not include re-verification |
| Component tests (all 7 groups, 205 total) | `research/prototype/tests/` | all of `src/` | DeBERTa for 6 of 205 tests | CPU | **Yes, every step, STEP 2-8** | N/A (always fresh) | `pytest research/prototype/tests/ -q` | None |
| Real Qwen generation (any mode) | N/A | `src/generator.py` | Qwen2.5-7B-Instruct | **GPU required, none available** | **NOT EXECUTED, any step** | Every historical natural batch was generated on a prior GPU session | N/A (cannot run) | No CPU fallback exists in the code by design |
| Real Qwen correction (any) | N/A | `src/corrector.py` | Qwen2.5-7B-Instruct | **GPU required, none available** | **NOT EXECUTED, any step** | Targeted/cumulative correction shipping figures are entirely historical, GPU-dependent | N/A (cannot run) | No CPU fallback exists in the code by design |
| Narrow re-verification narrative evidence | `FINAL_PRODUCTION_CONFIG.md` §4 | N/A (narrative) | N/A | N/A | **NOT re-derived from raw data** | Cited directly, not modified | N/A | Raw per-case data for isolating exactly these 3 cases was not located/re-derived in STEP 7 |

## Explicit hardware/software identification

- **CPU-only current machine**: confirmed, AMD Radeon integrated GPU, no NVIDIA hardware (STEP 2).
- **No NVIDIA GPU**: confirmed via `torch.cuda.is_available() == False` and Windows WMI, independently, in STEP 2.
- **Qwen generation/correction not freshly executed**: true for every step 2-8; explicitly recorded `qwen_generation_or_correction_invoked: false` in every relevant run's metadata.
- **DeBERTa verifier CPU execution**: real, confirmed working, used in STEP 4/5/6/7's fresh reproductions.
- **Historical GPU-dependent correction results**: `outputs/final_gpu_validation_*`, `outputs/labeled_correction_validation_gpu_*`, `outputs/final_metrics.json`'s synthetic correction sections — all historical, all explicitly labeled as such throughout this workspace.
