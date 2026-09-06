# PASS 3B Reorganization Report

Executed 2026-09-06, directly following `PASS3A_REORGANIZATION_REPORT.md`. Scope: resolve
`final_demo_pack/`/`final_comparison/`, refresh the root `REPOSITORY_MANIFEST.md`, review
`integration_tests/`. No commit was made — all changes are staged/unstaged in the working
tree, per standing instruction.

## 1. Files moved (promoted into the live workspace)

Both were inspected in full before any change (README, ARTIFACT_INDEX, DATA_LINEAGE, every
script's `Path(__file__).resolve()` depth) to confirm they were reusable tooling, not
presentation-snapshot narrative, and that promoting them required no path-depth fixes
(both source and destination sit at the identical nesting depth under
`research/prototype/`).

| From | To | Files | Why |
|---|---|---|---|
| `final_demo_pack/live_demo/` | `evaluation/live_demo/` | 2 | Real, GPU-free, code-path-verifying demo (`run_demo.py`) calling `src/*` directly — reusable tooling, already identified in `integration_tests/README.md` as the strongest existing asset for future integration-test work |
| `final_demo_pack/examples/` | `evaluation/examples/` | 13 | 8 audited real-case worked examples plus their reproducible selection scripts (`find_candidates.py`, `build_cases_json.py`) — a re-runnable methodology, not a frozen snapshot |

All moves used `git mv`; `git status` confirms all 15 files as clean renames (no content
change from the move itself).

## 2. Files archived (not deleted)

| From | To | Files |
|---|---|---|
| `final_demo_pack/` (remainder after the above promotion) | `archive/2026-08-27_presentation/final_demo_pack/` | 67 |
| `final_comparison/` (entire directory) | `archive/2026-08-27_presentation/final_comparison/` | 34 |

All 101 files moved as clean `git mv` renames — zero content modification to any archived
file itself. A new `archive/2026-08-27_presentation/README.md` indexes both, explains what
was promoted out and why, and flags `final_comparison/FINAL_BASELINE_COMPARISON.md`
specifically as still worth reading directly despite being archived (it is the deepest
original-vs-current research narrative in the project, with real case studies and an
honest counter-signal — archived because it's a dated presentation narrative, not because
it's superseded content).

## 3. Files deleted

None. Nothing was deleted in this pass.

## 4. Files retained and why

- `integration_tests/README.md` — reviewed in full. It honestly documents its own status
  ("What is planned here (not yet built)") with two concrete, unbuilt wrapper designs and
  correctly identifies `research/prototype/tests/test_correction_path_real_integration.py`
  and the promoted `live_demo/run_demo.py` as the strongest existing related assets. No
  tests or results were invented; the file's only change this pass was updating its
  citation of `live_demo/run_demo.py` to its new promoted path.
- `research/prototype/scripts/` (production reproduction scripts) — confirmed untouched
  and confirmed distinct from `evaluation/scripts/` (the workspace's own validate/build
  scripts); a disambiguating note was added to `REPOSITORY_MANIFEST.md` §0 since both now
  share the name "scripts/" at different depths.

## 5. Path/reference fixes made

Two-bucket rule applied throughout, consistent with PASS 1/2/3A: **live navigation docs**
were corrected to the new paths; **frozen point-in-time historical/audit records** (STEP
7/9/13 documents that describe what was true when they were written) were left unedited,
matching the precedent already established for stale script-name citations in those same
documents.

Live docs corrected (path citations only, no content/finding changes):

- `evaluation/live_demo/run_demo.py`, `evaluation/examples/find_candidates.py`,
  `evaluation/examples/EXAMPLES_INDEX.md` (2 citations),
  `evaluation/examples/case_05_no_evidence.md` — each file's own self-reference to its old
  `final_demo_pack/...` path, corrected to its new location or (for citations of material
  that was archived rather than promoted) to `archive/2026-08-27_presentation/...`.
- `evaluation/integration_tests/README.md` — `live_demo/run_demo.py` citation updated.
- `evaluation/inputs/README.md` — 5 citations (HIST-01/HIST-02 rows, the disposition
  table, and the "Historical-Only Reference Artifacts" detail table) updated to
  distinguish promoted (`evaluation/examples/...`) from archived
  (`archive/2026-08-27_presentation/final_comparison/...`) material.
- `evaluation/figures/README.md` — figure cross-reference table updated to the archive
  path.
- `evaluation/comparisons/README.md` — `final_comparison/` citation updated to the archive
  path; also fixed a pre-existing broken relative link (`../evaluation/README.md`, which
  never resolved to anything even before this pass, since `comparisons/` sits directly
  inside `evaluation/`) to `../README.md`.
- `evaluation/metrics/CONSOLIDATION_SOURCE_MAP.md` — 2 citations updated to the archive
  path (this file was already treated as a live, maintained document in PASS 3A).
- `evaluation/README.md` — §2 (why this workspace exists), §12 (frozen-sources list), and
  §13 (workspace index table) updated to reflect the archive and the two promoted
  directories.
- `REPOSITORY_MANIFEST.md` (repo root) — see §6 below.

Left unedited (frozen historical/audit records citing the pre-archive path, describing
what was true when written): `evaluation/ablation/ABLATION_INVENTORY.md`,
`evaluation/ablation/ABLATION_EVIDENCE_GRADES.md`,
`evaluation/metrics/{STATISTICAL_RESULTS,EVIDENCE_STRENGTH_MATRIX,CONSOLIDATED_CONSISTENCY_REPORT}.md`,
`evaluation/figures/FIGURE_CLAIM_AUDIT.md`,
`evaluation/reports/{FINAL_RELEASE_AUDIT,FINAL_WORKSPACE_MANIFEST}.md`,
`evaluation/actual_outputs/step2_environment_setup/ENVIRONMENT_REPRODUCIBILITY_RESULT.md`,
and the embedded string-literal citations inside
`evaluation/scripts/{build_ablation_analysis,build_metrics_consolidation}.py` (these are
values written into already-generated historical JSON outputs, not file-existence checks
— confirmed no script anywhere reads `final_demo_pack/` or `final_comparison/` off disk,
so none of this is a functional dependency, only a citation string).

## 6. Root `REPOSITORY_MANIFEST.md`

Added a new §0 ("Update — 2026-09-06") at the top describing the current, final structure
(`evaluation/` workspace, `archive/2026-08-27_presentation/`, the promoted
`live_demo/`/`examples/`, and the disambiguation between the two same-named `scripts/`
directories at different depths). The original §1-10 were kept completely unedited below
it and relabeled as the historical record of the 2026-08-27 pass they describe, per the
same frozen-record convention used throughout this cleanup.

## 7. Validation results

- `pytest research/prototype/tests/ -q` — **205 passed**, 1 unrelated deprecation warning.
- All 12 `evaluation/scripts/validate_*.py` scripts run independently:
  - 11/12 **PASS** (ablation, faculty_package, figure_data, figures,
    gold_benchmark_outputs [4 pre-existing historical-metadata warnings, not failures —
    see PASS1_5_VERIFICATION_REPORT.md], gpu_209_reproduction, gpu_experiments, inputs,
    metrics_consolidation, reconciliation, release_audit).
  - `validate_natural_data.py` — **10 known pre-existing failures**, unrelated to this
    pass (regex false-positives on meta-commentary describing prohibited terms, not
    actual violations) — per explicit instruction, not attempted in PASS 3B.
- No validator regression was introduced by this pass's moves or path fixes.

## 8. Protected directories — confirmed untouched

`git status --short` against `research/prototype/{src,tests,config}`, `research/data/`,
and `research/prototype/outputs/` returns empty. No historical experiment result, frozen
metadata file, or already-archived document (`evaluation/archive/cleanup_history/`,
`PASS1_5_VERIFICATION_REPORT.md`) was modified.

## 9. Remaining known issues

- `validate_natural_data.py`'s 10 regex false-positives — pre-existing, explicitly out of
  scope for this pass.
- The PASS 3A `testing/` → `evaluation/` rename was done via PowerShell `Move-Item` (not
  `git mv`), so `git status` still shows that entire subtree as delete+untracked-new
  rather than paired renames — a cosmetic git-status artifact from PASS 3A, not a content
  issue, and not something PASS 3B was scoped to change.
- `evaluation/reports/FINAL_RELEASE_AUDIT.md` line ~125-126 still says work must not
  modify `final_demo_pack/`/`final_comparison/` at their pre-archive paths — left
  unedited as a frozen STEP 13 audit record of what was true at that time, per §5 above.

No further cleanup pass was started after this one, per instruction.
