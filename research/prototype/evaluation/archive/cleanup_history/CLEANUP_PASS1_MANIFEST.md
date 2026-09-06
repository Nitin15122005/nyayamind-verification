# CLEANUP PASS 1 — Manifest

**Date**: 2026-09-05. **Scope**: `component_tests/`, `evaluation/`, `comparisons/`,
`ablation/`, `inputs/`, `actual_outputs/` under `research/prototype/testing/`, plus the
minimal cross-reference fixes these changes required elsewhere in `testing/`. Nothing
under `src/`, `tests/`, `config/`, `research/data/`, `final_demo_pack/`,
`final_comparison/`, or `reports/`/`figures/` was touched — confirmed via
`git status --short` before and after this pass.

Every row is a real, executed action, not a plan — this manifest was assembled from the
actual `git status --short` diff after execution, cross-checked file by file. No file's
content was invented; every merge concatenated real, previously-read source text.

## Component consolidation (`component_tests/` → `components/`)

| Original path | Action | Final path | Reason |
|---|---|---|---|
| `component_tests/01_claim_parser/README.md` | MOVE | `components/01_claim_parser/README.md` | No numbering collision for stage 1 |
| `component_tests/01_claim_parser/RESULT.md` | MOVE | `components/01_claim_parser/RESULT.md` | Same |
| `component_tests/02_evidence_retrieval/README.md` | MOVE | `components/02_evidence_retrieval/README.md` | Canonical name (matches project's own 8-stage index) |
| `component_tests/02_evidence_matcher/RESULT.md` | MERGE | `components/02_evidence_retrieval/RESULT.md` | Same stage under STEP 5's alternate name — verified by content (both describe `match_evidence`) |
| `component_tests/03_nli_verification/README.md` | MOVE | `components/03_nli_verification/README.md` | Canonical name |
| `component_tests/03_verifier/RESULT.md` | MERGE | `components/03_nli_verification/RESULT.md` | Same stage, verified by content |
| `component_tests/04_verdict_application/README.md` | MOVE | `components/04_verdict_application/README.md` | No collision |
| `component_tests/04_verdict_application/RESULT.md` | MOVE | `components/04_verdict_application/RESULT.md` | Same |
| `component_tests/05_correction/README.md` | MOVE | `components/05_correction/README.md` | Genuine gap noted explicitly — no RESULT.md exists for this stage; none fabricated |
| `component_tests/05_citation_adversarial/RESULT.md` | MOVE (relabeled) | `components/02_evidence_retrieval/CITATION_ADVERSARIAL_RESULT.md` | Verified by content this pass: tests `match_evidence`'s citation-identity safety (evidence-retrieval concern), NOT correction — genuinely distinct from `05_correction`, kept as its own labeled file rather than merged into either stage's primary RESULT.md |
| `component_tests/06_scope_safety/README.md` | MOVE | `components/06_scope_safety/README.md` | Canonical name |
| `component_tests/06_correction_safety/RESULT.md` | MERGE | `components/06_scope_safety/RESULT.md` | Confirmed identical stage by content (`_scope_violation`/`_reverify_sibling_regressions`) |
| `component_tests/07_reverification/README.md` | MOVE | `components/07_reverification/README.md` | Genuine gap noted explicitly — no RESULT.md exists for this stage |
| `component_tests/08_final_assembly/README.md` | MOVE | `components/08_final_assembly/README.md` | Canonical name |
| `component_tests/07_final_assembly/RESULT.md` | MERGE | `components/08_final_assembly/RESULT.md` | Confirmed by content: this file's own test filter matches Stage 8's description, not Stage 7's |
| `component_tests/README.md` | MOVE (updated) | `components/README.md` | Stage index table updated to 8-directory scheme; added a PASS 1 cleanup note |
| `component_tests/COMPONENT_TEST_SUMMARY.md` | MOVE (updated) | `components/COMPONENT_TEST_SUMMARY.md` | Row labels updated to canonical names; content otherwise identical |
| `component_tests/TEST_INVENTORY.md` | MOVE (updated) | `components/TEST_INVENTORY.md` | Added a note on removed raw logs; content otherwise identical |
| `actual_outputs/step5_components/0N_*/demo_examples.json` (7 files) | MOVE | `components/0N_*/demo_examples.json` (6 files) + `components/02_evidence_retrieval/citation_adversarial_demo_examples.json` (1 file) | Consolidated alongside their merged RESULT.md |
| `actual_outputs/step5_components/run_metadata.json` | MOVE | `components/run_metadata.json` | Unique commit-hash/environment provenance, no equivalent elsewhere |
| `actual_outputs/step5_components/validate_step5_report.txt` | MOVE (renamed) | `components/STEP5_VALIDATION_REPORT.txt` | Genuine 37-check validation record (GOLD-hash checks, historical-artifact preservation) — real content, not a log |

## Deleted — pure logs, superseded by retained artifacts

| Path | Why safe to delete | Superseding artifact |
|---|---|---|
| `actual_outputs/step5_components/0N_*/pytest_execution.log` (7 files) | Raw pytest stdout; each stage's merged RESULT.md already states exact pass/fail counts and test names in table form | `components/0N_*/RESULT.md`, `components/COMPONENT_TEST_SUMMARY.md` |
| `actual_outputs/step5_components/demo_run.log` | Console output of the demo-generation script; every "pass=True" line it recorded is restated as PASS in the corresponding RESULT.md | `components/0N_*/RESULT.md` |
| `actual_outputs/step5_components/full_suite_verbose.log` | Full 205-test verbose pytest output; count triple-recorded elsewhere | `components/COMPONENT_TEST_SUMMARY.md`, `components/run_metadata.json`, `PROVENANCE.md` §STEP5 |
| `actual_outputs/step5_components/pytest_regression_final.txt` | Short regression recap, same 205-passed fact as above | Same |
| `actual_outputs/step2_environment_setup/pip_install_log.txt` | Raw pip install console output (2.5GB download progress); every pinned package version is already in the sibling `.meta.json` and in `ENVIRONMENT_REPRODUCIBILITY_RESULT.md` | `actual_outputs/step2_environment_setup/pip_install_log.txt.meta.json` (kept), `ENVIRONMENT_REPRODUCIBILITY_RESULT.md` (kept) |
| `actual_outputs/step2_environment_setup/pytest_run_log.txt` | Raw pytest stdout; "205 passed, 46.16s" already stated in the `.md` and `.meta.json` | Same two files (kept) |
| `actual_outputs/step3_input_validation/pytest_regression_check.txt` + `.meta.json` | Pure regression re-confirmation ("no change from STEP 2"); adds nothing beyond what `run_metadata.json` and `PROVENANCE.md` already record | `components/run_metadata.json`, `PROVENANCE.md` |
| `actual_outputs/step7_ablation/pytest_regression_final.txt` | Same pure regression recap pattern | `PROVENANCE.md` §STEP7 |
| `actual_outputs/step8_consolidation/pytest_regression_final.txt` | Same | `PROVENANCE.md` §STEP8, `evaluation/CONSOLIDATED_CONSISTENCY_REPORT.md` |
| `actual_outputs/step9_figures/pytest_regression_final.txt` | Same | `PROVENANCE.md` §STEP9 |
| `validate_step5_components.py` | Obsolete one-time validator — every path it checked (`component_tests/`, `actual_outputs/step5_components/`) no longer exists after this consolidation, and its 37-check PASS outcome is fully preserved verbatim | `components/STEP5_VALIDATION_REPORT.txt` |

**Explicitly kept, not deleted, despite resembling the above**: `actual_outputs/step3_input_validation/validate_inputs_report.txt` + `.meta.json`, `actual_outputs/step7_ablation/validate_step7_report.txt`, `actual_outputs/step8_consolidation/validate_step8_report.txt` + `validate_figure_data_report.txt`, `actual_outputs/step9_figures/validate_step9_report.txt` + `audit_figures_report.txt` — each contains substantive, non-duplicated content (exact hash values, 26-value metric reconciliation, image-resolution audits) not fully captured anywhere else. `actual_outputs/step7_ablation/scope_check_replay_fresh.json` — real replay data, moved (not deleted) to `ablation/`.

## Ablation reunification

| Original path | Action | Final path |
|---|---|---|
| `evaluation/ABLATION_EVIDENCE_GRADES.md`, `ABLATION_FACULTY_SUMMARY.md`, `ABLATION_INVENTORY.md`, `ABLATION_MATRIX.csv`, `ABLATION_RESULTS.csv`, `ABLATION_RESULTS.md`, `ABLATION_SUMMARY.json` (7 files) | MOVE | `ablation/` (same filenames) |
| `actual_outputs/step7_ablation/scope_check_replay_fresh.json` | MOVE | `ablation/scope_check_replay_fresh.json` |

Internal path references inside the moved files (`ABLATION_MATRIX.csv`, `ABLATION_SUMMARY.json` citing the old `testing/actual_outputs/step7_ablation/...` path; `GPU_ABLATION_UPDATE.md` citing the old `evaluation/ABLATION_*` paths and a broken same-directory-assumed reference to `evaluation/GPU_REPRODUCTION_CROSSCHECK.md`) were corrected in place.

## Inputs consolidation

| Original path(s) | Action | Reason |
|---|---|---|
| `inputs/README.md`, `INPUT_MANIFEST.md`, `INPUT_SUMMARY.md`, `INPUT_TO_COMPONENT_MAP.md` (4 files) | MERGE | Into one rewritten `inputs/README.md`, as titled sections — no content removed |
| `inputs/gold/README.md`, `behavior/README.md`, `historical_reference/README.md`, `metric_only/README.md`, `provisional/README.md`, `cases/SOURCE.md`, `evidence/SOURCE.md` (7 files, 7 directories) | MERGE | Same target — these 7 directories held zero data files each (documentation-only), the exact "README-only directory" pattern flagged for cleanup |

Net: 11 files across 8 directories → 1 file in 1 directory. Every fact, hash, and
classification from the originals is present in the merged file (SHA-256 values, record
counts, GOLD/BEHAVIOR/METRIC-ONLY/PROVISIONAL/HISTORICAL-ONLY classifications, the full
pipeline-flow diagram, the plain-language summary).

## Documentation corrections (no files moved)

| File | Correction |
|---|---|
| `comparisons/README.md` | Removed the claim that a `metric_based/` subdirectory exists or is planned; corrected to state its content lives in `evaluation/`, with exact file citations |
| `evaluation/README.md` | Full rewrite — was a STEP-1 planning stub ("none executed... planned evaluation runs") describing hypothetical subdirectories that were never built; now describes the ~28 files actually present |
| `expected_outputs/README.md` | Fixed 2 references from `../component_tests/` to `../components/`; fixed 1 reference from `../comparisons/metric_based/` to `../evaluation/` |
| `integration_tests/README.md` | Fixed 1 reference from `component_tests/` to `components/` |
| `MANIFEST.md` (testing root) | Fixed 1 reference from `component_tests/README.md` to `components/README.md` |
| `PROVENANCE.md` | Fixed 4 path references broken by this pass's moves/deletions, each annotated in place with a "PASS 1 cleanup note" rather than silently rewritten — the historical narrative itself is unchanged |
| `README.md` (testing root) | Fixed 3 references from `component_tests/` to `components/` |
| `evaluation/CONSOLIDATION_SOURCE_MAP.md` | Fixed 1 reference from the deleted `component_tests/`/`step5_components/` paths to `components/` |
| `evaluation/COMPONENT_TEST_MATRIX.csv` | Updated the `source_artifact` column (7 rows) from the deleted `actual_outputs/step5_components/...` paths to `components/...` |
| `build_step8_consolidation.py` | Updated the same 7 `source_artifact` string literals (this is the script that generated the CSV above — fixed so a future re-run doesn't regenerate stale paths) |
| `run_step5_component_demos.py` | Updated its `OUT` write-target and all 7 `write_json()` calls from the deleted `actual_outputs/step5_components/<step5-numbering>/` to `components/<canonical-numbering>/`, so re-running this reproduction script writes to the correct, current location |
| `validate_step13_release_audit.py` | Updated its `REQUIRED_DIRS` list entry from `component_tests` to `components` |

## Not changed (in scope but found to need no action)

`comparisons/expected_vs_actual/` — real content, untouched. `evaluation/`'s ~21 other
files (CANONICAL_METRICS, CORRECTION_FUNNEL, EVIDENCE_STRENGTH_MATRIX, GPU_* reports,
NATURAL_DATA_*, STATISTICAL_RESULTS, PAIRED_209_REPORT, METRIC_DEFINITIONS,
CONSOLIDATED_CONSISTENCY_REPORT, figure_data/, input_integrity/) — reviewed, found to be
genuine, non-duplicated content; left in place. `actual_outputs/step4_gold_verifier/`,
`step6_natural_data/`, `step10*_gpu_*/` — real GOLD/natural-data/GPU results, explicitly
protected by your PRESERVE list; not reorganized or touched in this pass.

## Critical finding, unrelated to this pass (discovered during validation)

Running `validate_inputs.py`, `validate_step7_ablation.py`, and `validate_step8_consolidation.py`
after this pass's changes surfaced a **pre-existing GOLD fixture hash mismatch**: the
SHA-256 recorded for `controlled_verifier_benchmark.jsonl` and `run_synthetic_stress.jsonl`
in this workspace's own documentation (`962de21e...`, `2dba39cc...`) does not match the
hash of the file actually committed in git on this machine (`aad8018b...`, `717378e8...`).

**Confirmed not caused by this pass**: `git diff --stat` against HEAD shows zero content
change to either file (source in `outputs/` or copy in `expected_outputs/`) — only the
intentional `expected_outputs/README.md` edit appears in the diff. Both the source file
and its copy hash identically to each other right now (`aad8018b...` for both
`controlled_verifier_benchmark.jsonl` copies), meaning the "byte-identical to frozen
source" checks correctly pass — only the hash *recorded in documentation* is stale or was
computed against different bytes than what git has committed here. This is a documentation/
provenance bookkeeping issue, most likely originating from a different machine's checkout
(this workspace's `PROVENANCE.md` references a second machine at `D:\nyaymind\...`) or a
line-ending/checkout difference between environments — not a sign the GOLD data was
altered. **No GOLD file was modified by this pass or requires re-verification of its
content** — only the recorded hash strings need reconciling, which is a data-integrity
investigation outside PASS 1's authorized scope (touching GOLD-fixture-related
documentation was not part of the 6 listed areas). Flagged here for your attention.

## Deferred to PASS 2 (found during this pass, out of PASS 1's authorized scope)

- `evaluation/CONSOLIDATED_EXECUTIVE_SUMMARY.md`, `CONSOLIDATED_FACULTY_SUMMARY.md`,
  `HEADLINE_RESULTS.md`, `ORIGINAL_VS_CURRENT.md`/`.csv`, `REPRODUCIBILITY_MATRIX.md` —
  each is superseded in currency by a `reports/` document, but resolving that requires
  touching `reports/`, which this pass's stop condition excludes.
- `integration_tests/README.md` — still describes unbuilt future work; its disposition
  (build vs. fold into `reports/` as a Future Work note) is a `reports/`-adjacent decision.
- A dangling reference to a `JOINT_FOUR_LEVER_STEP10.md` file inside
  `ablation/GPU_ABLATION_UPDATE.md` (line ~20) — this file does not exist anywhere in the
  repository. Confirmed **pre-existing**, not caused by this pass. Left as-is (not a path
  this pass's scope authorizes fixing via content investigation).
- `final_comparison/`, `final_demo_pack/` — explicitly protected this pass; the earlier
  session-level cleanup plan's promote/archive recommendations for these remain
  unexecuted.
