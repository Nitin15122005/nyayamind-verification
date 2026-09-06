# Final Structure Audit & Navigation Cleanup Report

Executed 2026-09-06, immediately after PASS 1 through PASS 3B. Scope, per instruction:
**final navigation/structure polish only** — no further reorganization, no deletions, no
rewriting of historical experiment claims. No commit was made.

## 1. Method

1. Read the full repository tree (root, `research/prototype/`, `research/prototype/evaluation/`,
   `research/prototype/archive/`) to build a current picture of the final architecture.
2. Read every top-level navigation document: root `README.md`, `REPOSITORY_MANIFEST.md`,
   `research/prototype/README.md`, `evaluation/README.md`, `evaluation/MANIFEST.md`,
   `evaluation/PROVENANCE.md`, `evaluation/reports/README.md`,
   `evaluation/reports/FINAL_WORKSPACE_MANIFEST.md`, `PASS3A_REORGANIZATION_REPORT.md`,
   `PASS3B_REORGANIZATION_REPORT.md`.
3. Ran an automated link check over every real Markdown hyperlink (`[text](path)`, not
   prose backtick-path mentions) in all live navigation docs under `research/`, excluding
   files already established by prior passes as frozen historical/process records
   (`archive/`, `PASS*_REPORT.md`, `PASS1_5_VERIFICATION_REPORT.md`,
   `REPOSITORY_FINAL_STRUCTURE_PLAN.md`, `reports/archive/`,
   `reports/FINAL_RELEASE_AUDIT.md`, `reports/FINAL_WORKSPACE_MANIFEST.md`).
   **Result: 0 broken hyperlinks.** PASS 1 through PASS 3B had already resolved every
   real navigational link; nothing new was broken by those passes.
4. Grepped every `evaluation/**/*.md` file for stale "not built yet" / "empty" / "planned"
   / "STEP N" status language, then read each hit in context to classify it as (a) an
   honest, still-true statement of a genuinely unbuilt future feature, (b) an already
   correctly-flagged historical note (e.g. `figures/README.md`'s own "Superseded by
   STEP 9" correction), or (c) a stale claim contradicted by the directory's actual,
   current contents.
5. Cross-checked directory contents against README claims for `actual_outputs/`,
   `figures/`, `reports/`, `comparisons/`, `inputs/`, `components/`, `ablation/`,
   `metrics/`, `expected_outputs/`, `integration_tests/`.

## 2. Findings

### 2a. Real navigation links — clean

Zero broken relative hyperlinks found in any live document. Prior passes' "two-bucket
rule" (fix live docs, leave frozen historical records citing old paths as they were
written) had already been applied consistently and correctly.

### 2b. Stale top-level status claims — the one real problem found

Three files carried a status header/section written at an early step (STEP 1/STEP 2) that
was **never updated** even though the workspace was subsequently built out completely
through STEP 13 and cleaned up through PASS 3B. These are the first thing a new reviewer
opening the workspace would read, so the contradiction between the header and the actual
directory contents is a genuine, misleading navigation defect — not a broken link, but
false orientation information at the entry point:

| File | Stale claim | Actual state |
|---|---|---|
| `evaluation/README.md` (top-level entry point) | "STEP 1 — structure and provenance only. No fresh model runs have been executed in this workspace yet." | Workspace complete through STEP 13 / PASS 3B; `actual_outputs/`, `figures/`, `reports/` all fully populated |
| `evaluation/README.md` §5 | "`actual_outputs/` is empty; nothing has been (re-)run yet" | 9 populated subdirectories (GPU capability checks, 209-claim reproduction, gold-benchmark reruns, natural-data reruns, per-step validator logs) |
| `evaluation/README.md` §10 | "`figures/` ... No images exist here yet" / "`reports/` ... No reports exist here yet" | 11 figures generated; 10-document faculty report package complete |
| `evaluation/actual_outputs/README.md` | "Status: one real artifact as of STEP 2" | 9 populated subdirectories spanning STEP 2 through STEP 10B |

Contributing cause: later passes (PASS 1 through PASS 3B) correctly updated *other*
sections of `evaluation/README.md` (§2, §9, §12, §13 — confirmed by reading
`PASS3B_REORGANIZATION_REPORT.md`'s own change list) but never revisited the header or
§5/§10, which were written at STEP 1 and left behind as the rest of the document grew
around them.

By contrast, `figures/README.md` already contains a correct, explicit self-correction
("Superseded by STEP 9 ... no images exist here yet [STEP 1 claim, now false]") — proof
this class of problem was already recognized and fixed once elsewhere, just not
consistently everywhere.

`MANIFEST.md` (the STEP 1 file-inventory snapshot) is explicitly labeled "Historical
(STEP 1)" in `reports/FINAL_WORKSPACE_MANIFEST.md`'s own index table, but nothing told a
reader who opens `MANIFEST.md` directly (or follows the `evaluation/README.md` §13 index,
which linked to it with no such caveat) that a newer, complete inventory exists.

### 2c. Everything else checked and found current

- Root `README.md`, `REPOSITORY_MANIFEST.md` — already carry an accurate, up-to-date §0
  describing the final structure (added in PASS 3B); no changes needed.
- `evaluation/PROVENANCE.md`, `evaluation/comparisons/README.md`,
  `evaluation/inputs/README.md`, `evaluation/components/README.md`,
  `evaluation/expected_outputs/README.md`, `evaluation/ablation/README.md`,
  `evaluation/metrics/README.md`, `evaluation/reports/README.md` — all read in full;
  all describe current, correct structure. Remaining "component_tests/" /
  "STEP N" mentions in these files are correctly-contextualized historical footnotes
  (e.g. "renamed from `component_tests/` in the PASS 1 cleanup"), not stale
  self-descriptions.
- `evaluation/integration_tests/README.md`'s "What is planned here (not yet built)" and
  `evaluation/ablation/README.md`'s "What is not yet built here" are honest, still-true
  statements about genuinely unbuilt future work (a joint-lever ablation, an integration
  wrapper) — not stale claims contradicted by existing content. Left unedited.
- No STEP-numbered *paths* (e.g. old `step5_components/`, `component_tests/0N_*` as a
  literal current path) remain anywhere outside frozen historical records.
- Protected directories (`src/`, `tests/`, `config/`, `research/data/`,
  `research/prototype/outputs/`) — confirmed untouched, no navigation issue required
  touching them.

## 3. Classification of proposed changes

| # | Change | Class | Rationale |
|---|---|---|---|
| 1 | `evaluation/README.md`: update header Status line | **REQUIRED** | Primary workspace entry point; actively misleads a new reviewer about whether the workspace has any content |
| 2 | `evaluation/README.md` §5: update `actual_outputs/` description | **REQUIRED** | Directly contradicted by the directory's actual (populated) contents |
| 3 | `evaluation/README.md` §10: update figures/reports description | **REQUIRED** | Directly contradicted; figures and reports are the two most important faculty-facing deliverables in the whole workspace |
| 4 | `evaluation/README.md` §13 index: flag `MANIFEST.md` as a historical snapshot, point to `reports/FINAL_WORKSPACE_MANIFEST.md` | **REQUIRED** | The index is a reviewer's first navigation choice; sending them to a STEP-1 snapshot with no signal that a complete version exists is a real navigation defect |
| 5 | `evaluation/actual_outputs/README.md`: update header Status line | **REQUIRED** | Same class of problem as #1, for the directory a reviewer is most likely to check when asking "did anything actually run?" |
| 6 | `evaluation/MANIFEST.md`: add a one-line pointer at the top to `reports/FINAL_WORKSPACE_MANIFEST.md` | **REQUIRED** | Covers the reader who opens this file directly rather than through the workspace README; the file's own content already says it was "verified 2026-09-05" with no forward pointer, and it is directly linked from `evaluation/README.md` |
| 7 | Re-stage the `evaluation/` workspace's PASS 3A `Move-Item`-created files as proper `git mv` renames | OPTIONAL | Cosmetic `git status`/`git diff` presentation only (already called out as a known, non-content issue in `PASS3B_REORGANIZATION_REPORT.md` §9); no effect on navigation for a reviewer reading the repository, only on `git log --follow` ergonomics for a future contributor |
| 8 | Normalize "STEP N" language project-wide into a single consistent style/glossary | OPTIONAL | Cosmetic; current usage is already unambiguous in context everywhere it was checked, and rewriting it broadly risks touching frozen historical records against instruction |
| 9 | Fix `validate_natural_data.py`'s 10 pre-existing regex false-positives and `validate_gold_benchmark_outputs.py`'s 4 pre-existing hash-metadata warnings | OPTIONAL, and explicitly **out of scope** | Both are documented, pre-existing, non-blocking issues already flagged in `PASS3B_REORGANIZATION_REPORT.md` as "not attempted in PASS 3B" / "unrelated to this pass"; they are validator/metadata quirks, not navigation problems, and fixing them would mean editing frozen historical metadata or tuning a validator's regex — a different kind of task than this pass's scope |

Only items 1-6 (all classified REQUIRED) were implemented. Items 7-9 were left
untouched, per instruction to perform navigation polish only.

## 4. Changes made

- `research/prototype/evaluation/README.md` — header Status line, §5 (`actual_outputs/`
  description), §10 (figures/reports description), and the `MANIFEST.md` row in the §13
  index table, rewritten to describe the current, complete state. No section was
  deleted; the STEP-based provenance framing elsewhere in the document (§9, §11-13) was
  left as-is since it was already accurate.
- `research/prototype/evaluation/actual_outputs/README.md` — header Status line rewritten
  to list all 9 current subdirectories (previously described only the first,
  `step2_environment_setup/`).
- `research/prototype/evaluation/MANIFEST.md` — added a 3-line pointer at the top to
  `reports/FINAL_WORKSPACE_MANIFEST.md`, leaving the rest of the file (a STEP 1 record,
  already independently labeled "Historical" elsewhere) completely unedited.

No file was moved, renamed, or deleted. No historical claim, number, or experimental
finding was altered anywhere.

## 5. Post-change verification

- **Link check re-run**: 0 broken hyperlinks (same script as §1 step 3), confirming the
  edits introduced no new broken references.
- **`pytest research/prototype/tests/ -q`**: **205 passed**, 1 pre-existing unrelated
  deprecation warning (`huggingface_hub`'s `resume_download`). No change from the
  PASS 3B baseline.
- **All 12 `evaluation/scripts/validate_*.py` scripts**, run independently:
  - **11/12 PASS**: `validate_ablation.py`, `validate_faculty_package.py`,
    `validate_figure_data.py`, `validate_figures.py`,
    `validate_gold_benchmark_outputs.py` (36 passed, 4 pre-existing warnings — known
    historical dataset-hash metadata inconsistency from the workspace's creation commit,
    documented in `PASS1_5_VERIFICATION_REPORT.md`, unrelated to this pass),
    `validate_gpu_209_reproduction.py`, `validate_gpu_experiments.py`,
    `validate_inputs.py`, `validate_metrics_consolidation.py`,
    `validate_reconciliation.py`, `validate_release_audit.py` (11/11 passed, 1
    pre-existing informational warning about `PROVENANCE.md`'s STEP 11/12 sections living
    under `reports/` instead).
  - `validate_natural_data.py` — **10 pre-existing failures**, identical in nature and
    count to the ones documented in `PASS3B_REORGANIZATION_REPORT.md` §7 (regex
    false-positives on meta-commentary that *describes* prohibited terms, e.g. table rows
    listing "macro F1"/"accuracy" as *disclaimed, cited historical figures*, not as
    affirmative natural-data accuracy claims). **No new failures were introduced by this
    pass** — the failure count and messages match the pre-existing baseline exactly.
  - No validator regression was introduced by this pass's edits (all three edited files
    are prose-only READMEs/manifests that no validator script parses for pass/fail
    content — confirmed by inspecting each validator's file list).
- **Protected directories** — `git status --short` against
  `research/prototype/{src,tests,config}`, `research/data/`, and
  `research/prototype/outputs/` returns empty: none were touched.
- **Files actually changed this pass** (`git status --short`):
  `research/prototype/evaluation/README.md`,
  `research/prototype/evaluation/MANIFEST.md`,
  `research/prototype/evaluation/actual_outputs/README.md`. (`baseline/LegalSeg` shows as
  locally modified from before this pass began — the pre-existing, out-of-scope submodule
  state noted in every prior pass's own report — not touched here either.)

## 6. Summary for a new reviewer

The repository's navigation was, by this point, already in good shape: PASS 1 through
PASS 3B had correctly fixed every real broken link, archived the superseded presentation
snapshots without deleting them, and kept root-level docs (`README.md`,
`REPOSITORY_MANIFEST.md`) current. The one class of defect this pass found and fixed was
**stale point-in-time status language surviving at the top of the three files a reviewer
reads first** (`evaluation/README.md`, its `actual_outputs/README.md`, and `MANIFEST.md`),
left behind because later passes updated the *body* of these documents without revisiting
their *headers*. That gap is now closed. No other structural, deletion, or reorganization
work was found to be necessary or was performed.
