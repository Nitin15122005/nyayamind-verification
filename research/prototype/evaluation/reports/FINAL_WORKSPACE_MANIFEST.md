# Final Workspace Manifest — STEP 13

A single reference table of every major deliverable across the whole
`research/prototype/evaluation/` workspace, STEP 1 through STEP 13, as it now stands. For
per-metric detail see `FINAL_CLAIM_REGISTER.csv`; for the reproducibility grid see
`FINAL_REPRODUCIBILITY_MATRIX.md`; for the full narrative see `FINAL_RECONCILIATION_REPORT.md`
and `FACULTY_EVALUATION_REPORT.md`.

## Core provenance and structure

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `PROVENANCE.md` | Step-by-step build/provenance narrative, STEP 0 through STEP 10B | Current (STEP 11/12 documented separately under `reports/`, not appended here — see `FINAL_RELEASE_AUDIT.md` Phase 8) | `PROVENANCE.md` |
| `MANIFEST.md` | Original workspace file manifest | Historical (STEP 1) | `MANIFEST.md` |
| `inputs/` | Frozen input data + integrity checks | GOLD / BEHAVIOR (input fixtures) | `inputs/README.md` |
| `expected_outputs/` | Pre-recorded expected outputs for GOLD comparisons | GOLD | `expected_outputs/` |
| `actual_outputs/` | Fresh run outputs, per step | Mixed FRESH/HISTORICAL, per subdirectory | `actual_outputs/step*/` |
| `comparisons/` | Original-vs-current comparison scaffolding | METRIC-ONLY / HISTORICAL | `comparisons/` |
| `components/` (renamed from `component_tests/` in the PASS 1 cleanup) | Per-stage component test results | BEHAVIOR (205-test suite subset categorization) | `components/` |
| `integration_tests/` | End-to-end pipeline integration tests | BEHAVIOR | `integration_tests/` |

## Evaluation and ablation

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `evaluation/CANONICAL_METRICS.csv`/`.json` | STEP 8 per-metric canonical values (M01-M16+) | GOLD/METRIC-ONLY, mixed by row | `evaluation/CANONICAL_METRICS.csv` |
| `evaluation/HEADLINE_RESULTS.md` | STEP 8 headline narrative | Historical (STEP 8), consistent with STEP 11 reconciliation; **PASS 2**: archived to `evaluation/archive/` — superseded in currency by `FACULTY_EXECUTIVE_SUMMARY.md`/`FACULTY_RESULTS_TABLE.md` | `evaluation/archive/HEADLINE_RESULTS.md` |
| `evaluation/GPU_EXECUTION_INVENTORY.md` | Catalogue of every GPU-dependent operation, traced to source | FRESH (STEP 10) | `evaluation/GPU_EXECUTION_INVENTORY.md` |
| `evaluation/GPU_REPRODUCTION_CROSSCHECK.md` | Fresh-vs-historical comparison for GPU experiments | FRESH GPU REPRODUCED (STEP 10/10B) | `evaluation/GPU_REPRODUCTION_CROSSCHECK.md` |
| `evaluation/GPU_CORRECTION_SAFETY_STEP10.md` | Correction-safety observations, populations kept separate | FRESH (STEP 10) | `evaluation/GPU_CORRECTION_SAFETY_STEP10.md` |
| `evaluation/GPU_LIMITATIONS.md` | STEP 1-9 machine's GPU limitation (historical record) | HISTORICAL-ONLY, scoped to STEP 1-9 machine | `evaluation/GPU_LIMITATIONS.md` |
| `ablation/GPU_ABLATION_UPDATE.md` | Ablation findings updated for GPU-reproduced results | Mixed FRESH GPU REPRODUCED / HISTORICAL / DIAGNOSTIC, per finding | `ablation/GPU_ABLATION_UPDATE.md` |
| `ablation/ABLATION_EVIDENCE_GRADES.md` (moved from `evaluation/` in the PASS 1 cleanup) | Evidence-grade (A-E) assignment per ablation factor | HISTORICAL (STEP 7), unchanged by GPU work except where noted | `ablation/ABLATION_EVIDENCE_GRADES.md` |
| `ablation/ABLATION_FACULTY_SUMMARY.md` (moved from `evaluation/` in the PASS 1 cleanup) | Faculty-oriented ablation summary | HISTORICAL (STEP 7/8) | `ablation/ABLATION_FACULTY_SUMMARY.md` |
| `evaluation/ORIGINAL_VS_CURRENT.md`/`.csv` (via `ABLATION_MATRIX.csv` etc.) | Original-vs-current config comparison | METRIC-ONLY/HISTORICAL; **PASS 2**: archived to `evaluation/archive/` — no unique content vs. `final_comparison/tables/comparison_summary.csv` | `evaluation/archive/ORIGINAL_VS_CURRENT.md` |

## GPU validation and experiment reproduction (STEP 10/10B)

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `actual_outputs/gpu_capability_check/` | Env validation, 1-case real generation, 5-case correction smoke test | FRESH, GPU-executed (STEP 10) | `actual_outputs/gpu_capability_check/` |
| `actual_outputs/gpu_correction_rerun/` | 10-case targeted-correction exact reproduction | FRESH GPU REPRODUCED (STEP 10), exact match | `actual_outputs/gpu_correction_rerun/labeled_correction_validation_gpu_metrics.fresh.json` |
| `run_gpu_209_reproduction.py` | Redirected-output copy of the production 209-claim generation script | Tooling (STEP 10B), unmodified production logic | `scripts/run_gpu_209_reproduction.py` |
| `actual_outputs/gpu_209_reproduction/` | Full 209-claim/50-case/two-arm fresh GPU generation | FRESH GPU REPRODUCED (STEP 10B), exact match (byte-identical text, identical metrics, identical peak VRAM) | `actual_outputs/gpu_209_reproduction/step10b_final_gpu_validation_metrics.json` |
| `validate_gpu_experiments.py`, `validate_gpu_209_reproduction.py` | Automated checks for STEP 10/10B claims | PASS (13/13, 7/7 on last independent run) | `scripts/validate_gpu_experiments.py`, `scripts/validate_gpu_209_reproduction.py` |

## Final reconciliation and faculty package (STEP 11/12)

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `reports/FINAL_RECONCILIATION_REPORT.md` | STEP 11 full reconciliation narrative | Current, zero discrepancies found against source artifacts | `reports/FINAL_RECONCILIATION_REPORT.md` |
| `reports/FINAL_CLAIM_REGISTER.csv` | STEP 11 authoritative claim-to-source register (C01-C26) | Current, canonical for faculty-facing claims | `reports/FINAL_CLAIM_REGISTER.csv` |
| `reports/FINAL_REPRODUCIBILITY_MATRIX.md` | STEP 11 experiment-by-experiment reproduction grid | Current, supersedes STEP 8's `evaluation/REPRODUCIBILITY_MATRIX.md` (**PASS 2**: moved unedited to `evaluation/archive/REPRODUCIBILITY_MATRIX.md` as its own historical record) | `reports/FINAL_REPRODUCIBILITY_MATRIX.md` |
| `validate_reconciliation.py` | Automated checks for STEP 11 reconciliation | PASS (10/10 on last independent run) | `scripts/validate_reconciliation.py` |
| `reports/FACULTY_EVALUATION_REPORT.md` | Main faculty-facing evaluation report (16 sections) | Current, primary reviewer document | `reports/FACULTY_EVALUATION_REPORT.md` |
| `reports/FACULTY_EXECUTIVE_SUMMARY.md` | One-page standalone summary | Current | `reports/FACULTY_EXECUTIVE_SUMMARY.md` |
| `reports/FACULTY_RESULTS_TABLE.md` | Compact 26-row results table, each row cited to a claim ID | Current | `reports/FACULTY_RESULTS_TABLE.md` |
| `reports/FACULTY_LIMITATIONS_AND_CAVEATS.md` | Standalone limitations document, 6 headed subsections | Current | `reports/FACULTY_LIMITATIONS_AND_CAVEATS.md` |
| `validate_faculty_package.py` | Automated checks for the faculty package | PASS (9/9 on last independent run) | `scripts/validate_faculty_package.py` |

## Release audit (STEP 13, this step)

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `reports/FINAL_RELEASE_AUDIT.md` | Independent pre-commit audit of the whole workspace | PASS, 1 non-blocking documentation observation | `reports/FINAL_RELEASE_AUDIT.md` |
| `reports/FINAL_WORKSPACE_MANIFEST.md` | This document | Current | `reports/FINAL_WORKSPACE_MANIFEST.md` |
| `validate_release_audit.py` | Automated checks for the release audit | PASS (11/11) | `scripts/validate_release_audit.py` |

## Figures (STEP 9, referenced not modified)

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `figures/01_overall_metric_comparison.png` … `figures/11_synthetic_vs_natural_transfer.png` | 11 faculty-facing figures | Unchanged since STEP 9; underlying data confirmed still valid post-STEP-10B | `figures/FIGURE_INDEX.md`, `figures/FIGURE_METADATA.csv` |
| `figures/FIGURE_CLAIM_AUDIT.md`, `FIGURE_CONTRACT_INVENTORY.md`, `FIGURE_NUMERIC_AUDIT.md` | STEP 9's own figure-safety audits | Historical (STEP 9), unchanged | same filenames |

## Regression evidence

| Deliverable | Purpose | Status | Canonical source |
|---|---|---|---|
| `research/prototype/tests/` (205 tests) | Full deterministic regression suite | FRESH — 205/205 passed, re-confirmed at every step including this one | `research/prototype/tests/` |
