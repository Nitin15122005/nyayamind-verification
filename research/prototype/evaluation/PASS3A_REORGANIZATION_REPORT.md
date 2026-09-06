# PASS 3A — Structural Reorganization Report

**Status**: Executed exactly per your approved scope, from `REPOSITORY_FINAL_STRUCTURE_PLAN.md`. No experimental data, metrics, results, source code, tests, or scientific conclusions were modified. The hash audit was not performed. The STEP 6 terminology-regex issue was not fixed. The root `REPOSITORY_MANIFEST.md` was not refreshed. No integration test was invented. `final_demo_pack/`/`final_comparison/` were not touched.

## 1. Directory renames (top-level)

| Old path | New path | Verification |
|---|---|---|
| `research/prototype/testing/` | `research/prototype/evaluation/` | 207 files before, 207 after (`find -type f \| wc -l`) |
| `research/prototype/evaluation/evaluation/` (the inner dir) | `research/prototype/evaluation/metrics/` | 45 files, count unchanged |
| `actual_outputs/step4_gold_verifier/` | `actual_outputs/gold_benchmark_runs/` | 16 files, count unchanged |
| `actual_outputs/step6_natural_data/` | `actual_outputs/natural_data_runs/` | 11 files, count unchanged |
| `actual_outputs/step10_gpu_experiments/` | `actual_outputs/gpu_correction_rerun/` | 3 files, count unchanged |
| `actual_outputs/step10_gpu_validation/` | `actual_outputs/gpu_capability_check/` | 5 files, count unchanged |
| `actual_outputs/step10b_gpu_experiments/` | `actual_outputs/gpu_209_reproduction/` | 5 files, count unchanged |

`actual_outputs/step2_environment_setup/`, `step3_input_validation/`, `step7_ablation/`, `step8_consolidation/`, `step9_figures/` were **not** renamed — not in your approved mapping (only step4/step6/step10/step10b were specified).

Both top-level directory renames (`testing→evaluation`, inner `evaluation→metrics`) were executed via PowerShell `Move-Item` after `bash mv` failed with a transient "Device or resource busy" error on the first attempt (no files were touched by the failed attempt — verified 207-file count unchanged before retrying). All `actual_outputs` subdirectory renames used plain `mv` successfully.

## 2. Scripts moved into `scripts/` and renamed by function

All 24 flat root-level scripts moved from `evaluation/` into the new `evaluation/scripts/`:

| Old name | New name |
|---|---|
| `analyze_step6_natural_batches.py` | `analyze_natural_batches.py` |
| `build_step4_comparison_tables.py` | `build_gold_benchmark_tables.py` |
| `build_step7_ablation_analysis.py` | `build_ablation_analysis.py` |
| `build_step8_consolidation.py` | `build_metrics_consolidation.py` |
| `run_gold01_evaluation.py` | *(unchanged — already function-named)* |
| `run_gold02_evaluation.py` | *(unchanged)* |
| `run_step10b_209_gpu_generation.py` | `run_gpu_209_reproduction.py` |
| `run_step5_component_demos.py` | `run_component_demos.py` |
| `run_step6_209_paired_evaluation.py` | `run_natural_209_paired_evaluation.py` |
| `run_step6_588_evaluation.py` | `run_natural_588_evaluation.py` |
| `step4_common.py` | `gold_benchmark_common.py` |
| `validate_figure_data.py` | *(unchanged)* |
| `validate_inputs.py` | *(unchanged)* |
| `validate_step10_gpu.py` | `validate_gpu_experiments.py` |
| `validate_step10b_gpu.py` | `validate_gpu_209_reproduction.py` |
| `validate_step11_reconciliation.py` | `validate_reconciliation.py` |
| `validate_step12_faculty_package.py` | `validate_faculty_package.py` |
| `validate_step13_release_audit.py` | `validate_release_audit.py` |
| `validate_step4_outputs.py` | `validate_gold_benchmark_outputs.py` |
| `validate_step6_natural_data.py` | `validate_natural_data.py` |
| `validate_step7_ablation.py` | `validate_ablation.py` |
| `validate_step8_consolidation.py` | `validate_metrics_consolidation.py` |
| `validate_step9_figures.py` | `validate_figures.py` |
| `verify_step6_input_integrity.py` | `verify_natural_input_integrity.py` |

**Not moved** (correctly, by design — already co-located with what they generate/audit, not part of the flat-root cleanup): `figures/generate_figures.py`, `figures/audit_figures.py`. Their internal path-string references were still fixed (see §4).

**Not renamed** (frozen historical snapshot scripts stored inside their own output directories, analogous to `run_metadata.json` — see §6): `actual_outputs/gpu_correction_rerun/rerun_labeled_correction_validation_gpu.py`, `actual_outputs/gpu_capability_check/_gpu_memory_probe.py`.

## 3. Internal script path-constant fixes

Every moved script's own directory-root computation was updated for the new nesting depth:

- `TESTING_DIR = Path(__file__).resolve().parent` → `.parent.parent` (23 scripts had this pattern; `run_gpu_209_reproduction.py` used `_TESTING_DIR` — same fix applied).
- `EVAL_DIR = TESTING_DIR / "evaluation"` → `TESTING_DIR / "metrics"` (9 scripts).
- Two additional bugs found and fixed beyond the mechanical patterns: `validate_figures.py`'s `DATA_DIR` and `verify_natural_input_integrity.py`'s `OUT_DIR` both still pointed at `"evaluation" / "figure_data"` / `"evaluation" / "input_integrity"` — missed by the generic `EVAL_DIR` pattern because they built the path directly. Fixed to `"metrics" / ...`.
- Every `actual_outputs/<old-step-name>` read/write target across all 24 scripts updated to the new directory names (verified zero old names remain — see §7).
- `step4_common` import renamed to `gold_benchmark_common` in both `run_gold01_evaluation.py` and `run_gold02_evaluation.py` (sibling import, resolved automatically since both files now live in the same `scripts/` directory).
- `validate_release_audit.py`'s `REQUIRED_DIRS` list updated: `"evaluation"` → `"metrics"`, and `"scripts"` added as a newly-required directory.
- `build_ablation_analysis.py`'s `OUT_DIR` (already redirected to `ablation/` in an earlier PASS 2 fix, to avoid recreating the PASS-1-deleted `actual_outputs/step7_ablation/`) re-verified intact after the move.

Cross-directory imports into `research/prototype/scripts/` (the **main**, unrelated scripts directory — `compare_premise_framing_synthetic`, `select_natural_candidates`) were unaffected: both importing scripts already computed `PROTOTYPE_DIR / "scripts"` independently of the renamed workspace, and continue to resolve correctly.

## 4. Documentation updated (live, current-facing files)

Path/reference fixes applied across (full list, all re-verified by re-running validators — see §8): `README.md`, `PROVENANCE.md` (~60 individual citations fixed, including 20+ specific old-script-filename citations, plus one pre-existing imprecise citation to `input_integrity/` corrected to include the `metrics/` segment it was always missing), `ablation/{ABLATION_INVENTORY.md,ABLATION_MATRIX.csv,ABLATION_SUMMARY.json}`, `comparisons/expected_vs_actual/EXPECTED_VS_ACTUAL_REPORT.md`, `expected_outputs/{controlled_benchmark_gold,synthetic_stress_gold}/SOURCE.md`, `figures/{FIGURE_CONTRACT_INVENTORY.md,FIGURE_METADATA.csv,generate_figures.py,audit_figures.py}`, `metrics/{CANONICAL_METRICS.csv,CANONICAL_METRICS.json,COMPONENT_TEST_MATRIX.csv,CONSOLIDATED_CONSISTENCY_REPORT.md,CONSOLIDATION_SOURCE_MAP.md,GPU_CORRECTION_SAFETY_STEP10.md,GPU_EXECUTION_INVENTORY.md,GPU_REPRODUCTION_CROSSCHECK.md,PAIRED_209_REPORT.md,README.md,figure_data/08_ablation_comparison.csv}`, `reports/{FACULTY_EVALUATION_REPORT.md,FINAL_CLAIM_REGISTER.csv,FINAL_RELEASE_AUDIT.md,FINAL_WORKSPACE_MANIFEST.md,README.md}`, `archive/cleanup_history/README.md`.

`reports/FINAL_WORKSPACE_MANIFEST.md`'s "Canonical source" table column — the one place in the workspace whose explicit purpose is a precise path index — had its script-file rows updated to include the new `scripts/` prefix (e.g. `validate_reconciliation.py` → `scripts/validate_reconciliation.py`), not just the bare renamed filename, since that column is read as an exact location, not a casual mention.

## 5. Two self-inflicted regressions found and fixed during validation

1. My own annotation text in `reports/FACULTY_EVALUATION_REPORT.md` — "(renamed from `run_step6_209_paired_evaluation.py` in PASS 3A)" — wrapped the now-dead old filename in backticks, which `validate_faculty_package.py`'s cited-path checker treats as a live path citation that must resolve. Fixed by removing the backticks around the historical name (matches the same pattern from PASS 2's own appendix-citation fix).
2. `evaluation/README.md`'s workspace index table still said `evaluation/` → "Dataset-level evaluation runs and their metrics" — directly stale given the inner directory is now `metrics/`. Fixed, and added an index row for the new `scripts/` directory.

## 6. Intentionally left unchanged (frozen historical records)

Consistent with this session's established precedent (the GOLD-hash reconciliation, and PASS 1/2's treatment of superseded paths inside `PROVENANCE.md`'s narrative) — files whose entire purpose is to document exactly what was run, at the time, under the old structure were **not** rewritten, since doing so would misrepresent history rather than merely fix a stale pointer:

- All `run_metadata.json` / `*.meta.json` / `execution_log.txt` files under `actual_outputs/` (8 files).
- `components/run_metadata.json`, `components/STEP5_VALIDATION_REPORT.txt`.
- `actual_outputs/step2_environment_setup/ENVIRONMENT_REPRODUCIBILITY_RESULT.md`, `step9_figures/audit_figures_report.txt`.
- `actual_outputs/gpu_209_reproduction/step10b_final_gpu_validation_metrics.json`'s `exact_command` field.
- The two frozen snapshot scripts noted in §2.
- `archive/cleanup_history/{CLEANUP_PASS1_MANIFEST.md,HASH_RECONCILIATION_REPORT.md}`, `metrics/archive/*`, `reports/archive/FINAL_RECONCILIATION_REPORT.md` — all previously-archived historical documents.
- `PASS1_5_VERIFICATION_REPORT.md` — holds the permanent git-archaeology evidentiary trail; its content is a historical snapshot of git commands run against the pre-rename path, left as originally written.
- `REPOSITORY_FINAL_STRUCTURE_PLAN.md` — the planning document that proposed this exact rename; left as the historical planning record, not updated to reflect its own completion.

## 7. Broken references found and fixed (comprehensive count)

Beyond the two self-inflicted regressions in §5, the reorganization broke a substantial number of pre-existing references, all found via systematic grep sweeps (not assumed) and fixed:

- ~40 generic `testing/` path-prefix mentions in `PROVENANCE.md` alone, plus 20+ specific old-script-filename citations within it.
- 6 files (`metrics/CONSOLIDATED_CONSISTENCY_REPORT.md`, `CONSOLIDATION_SOURCE_MAP.md`, `GPU_REPRODUCTION_CROSSCHECK.md`, `README.md`, plus `reports/FINAL_RELEASE_AUDIT.md`, `FINAL_WORKSPACE_MANIFEST.md`) missed by the first bulk pass and caught only by a second, exhaustive bare-filename sweep (no `testing/` prefix, so invisible to the first grep pattern).
- 2 scripts inside `figures/` (`audit_figures.py`, `generate_figures.py`) not part of the flat-root move but still containing old path strings, including one line of **functional code** (`audit_figures.py`'s `.replace("step4/", "step4_gold_verifier/")`) that would have silently produced wrong paths if left unfixed.
- 3 files in `comparisons/`/`expected_outputs/` referencing the old `step4_gold_verifier/` directory and `step4_common.py`/`validate_step4_outputs.py` by name.

## 8. Validation results

| Check | Result |
|---|---|
| Repo-wide search for `research/prototype/testing` | **Zero hits** anywhere in the repository |
| Old `actual_outputs` subdirectory names, live docs | **Zero hits** (all remaining hits confirmed frozen historical records, §6) |
| `validate_inputs.py` | PASS — 38/38 |
| `validate_gold_benchmark_outputs.py` | PASS — 36 passed, 4 warnings (pre-existing, known historical-metadata notices, unrelated to this pass) |
| `validate_natural_data.py` | **FAIL — 10 failures, pre-existing, confirmed unrelated to PASS 3A** (the same hash-documentation bug and terminology-regex false positives flagged in PASS 2; instructions 7/8 explicitly excluded fixing these) |
| `validate_ablation.py` | PASS — 50/50 |
| `validate_metrics_consolidation.py` | PASS — 75/75 |
| `validate_gpu_experiments.py` | PASS — 13/13 |
| `validate_gpu_209_reproduction.py` | PASS — 7/7 |
| `validate_reconciliation.py` | PASS — 10/10 |
| `validate_faculty_package.py` | PASS — 9/9 (after fixing regression #1 in §5) |
| `validate_release_audit.py` | PASS — 11/11, 1 pre-existing informational warning (self-described as "not a defect") |
| `validate_figure_data.py` | PASS — 54/54 |
| `validate_figures.py` | PASS — 66/66 |
| `pytest research/prototype/tests/ -q` | **205 passed** |
| Total file count, start to finish | **207 → 207**, unchanged |
| Re-run safety: every script's write/read target | Zero old directory names remain in any of the 24 moved scripts (verified by direct grep of every `"actual_outputs"`-adjacent path construction) |
| Substantive result files (GOLD fixtures, GPU/natural-data metrics, component demo data, ablation summary, canonical metrics, figures, faculty reports) | All spot-checked present at their new locations |
| Protected directories (`src/`, `tests/`, `config/`, `research/data/`, `final_demo_pack/`, `final_comparison/`, `outputs/`) | `git status` confirms zero diff |

## 9. Anything intentionally left unchanged (recap)

- `actual_outputs/step2_environment_setup/`, `step3_input_validation/`, `step7_ablation/`, `step8_consolidation/`, `step9_figures/` — not in your approved rename mapping.
- The GOLD-hash documentation bug beyond the two fixtures, and `validate_natural_data.py`'s terminology regex — explicitly excluded (instructions 7, 8).
- Root `REPOSITORY_MANIFEST.md` — explicitly excluded (instruction 9), remains stale and still predates this entire workspace's existence under either name.
- `integration_tests/` — untouched, no test invented (instruction 10).
- `final_demo_pack/`, `final_comparison/` — untouched, no archival begun.

---

**PASS 3A COMPLETE. Stopping here per your instruction — not starting PASS 3B or any other cleanup phase.**
