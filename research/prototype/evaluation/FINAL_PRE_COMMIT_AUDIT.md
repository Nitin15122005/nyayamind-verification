# Final Pre-Commit Audit

Executed 2026-09-06, immediately after the `NATURAL_DATA_VALIDATOR_FIX_REPORT.md` pass.
Scope: **audit only** — no file was modified, staged, or committed during this pass.
Every command below is read-only (`git status`, `git diff`, `git diff --check`, running
validators/tests). This report documents what was found.

## 1. `git status --short` — every changed/untracked file accounted for

```
git status --porcelain | wc -l           -> 369 total entries
git status --porcelain | awk '{print substr($0,1,2)}' | sort | uniq -c
    229  D    (unstaged deletions)
      2  M    (unstaged modifications)
     22  ??   (untracked)
    112  R    (staged pure renames, 100% similarity)
      4  RM   (staged rename + unstaged content modification)
```

**PASS** — every one of the 369 entries is accounted for below, in six categories, all
traced to a specific, previously-documented pass. Nothing unexplained was found.

### 1a. `112 R` + `4 RM` — 116 staged renames (already in the index from PASS 3B)

- **101 files**: `research/prototype/final_comparison/**` (34) and
  `research/prototype/final_demo_pack/**` minus its promoted subdirectories (67) →
  `research/prototype/archive/2026-08-27_presentation/{final_comparison,final_demo_pack}/**`.
  Pure `git mv` renames (`R100`), zero content change — confirmed by the `R100`
  similarity index on every row of `git diff --cached --name-status`.
- **15 files**: `research/prototype/final_demo_pack/{examples,live_demo}/**` →
  `research/prototype/evaluation/{examples,live_demo}/**` (the "promoted" tooling).
  11 of these are pure renames (`R`); 4 (`EXAMPLES_INDEX.md`, `case_05_no_evidence.md`,
  `find_candidates.py`, `run_demo.py`) are renames **plus** an unstaged content edit —
  each edit is a self-referential path-citation fix (old `final_demo_pack/...` path
  corrected to the new `evaluation/...` or `archive/...` location), documented in
  `PASS3B_REORGANIZATION_REPORT.md` §5. Verified by re-reading each of the 4 diffs: no
  numeric result, claim, or finding was touched — only path strings.

### 1b. `229 D` — the old `research/prototype/testing/` tree

All 229 are deletions of paths under `research/prototype/testing/`, which **no longer
exists on disk** (confirmed: `find research/prototype/testing` → "No such file or
directory"). Root cause, previously documented in `PASS3B_REORGANIZATION_REPORT.md` §9:
PASS 3A performed the `testing/` → `evaluation/` rename with PowerShell `Move-Item`, not
`git mv`, so git's index still holds the old paths and sees them as plain deletions
rather than paired renames. This is a **cosmetic `git status` presentation artifact**,
not a content-loss risk — see §6 for the reconciliation proof.

### 1c. `22 ??` — untracked new content

- **21 entries under `research/prototype/evaluation/`**: 9 individually-listed top-level
  files (`README.md`, `MANIFEST.md`, `PROVENANCE.md`, `PASS1_5_VERIFICATION_REPORT.md`,
  `PASS3A_REORGANIZATION_REPORT.md`, `PASS3B_REORGANIZATION_REPORT.md`,
  `REPOSITORY_FINAL_STRUCTURE_PLAN.md`, `FINAL_STRUCTURE_AUDIT_REPORT.md`,
  `NATURAL_DATA_VALIDATOR_FIX_REPORT.md`) + 12 untracked directory subtrees (`ablation/`,
  `actual_outputs/`, `archive/`, `comparisons/`, `components/`, `expected_outputs/`,
  `figures/`, `inputs/`, `integration_tests/`, `metrics/`, `reports/`, `scripts/`),
  totaling 211 files on disk.
- **1 entry**: `research/prototype/archive/2026-08-27_presentation/README.md` — a
  genuinely new index file (not a rename of anything), written in PASS 3B to explain the
  archive's contents.

This pass's own two new files (`FINAL_STRUCTURE_AUDIT_REPORT.md`,
`NATURAL_DATA_VALIDATOR_FIX_REPORT.md`) and its one modified file
(`research/prototype/evaluation/scripts/validate_natural_data.py`, inside the untracked
`scripts/` subtree) are part of this bucket, alongside every other PASS 1–3B artifact.

### 1d. `2 M` — unstaged modifications

- `REPOSITORY_MANIFEST.md` — the intentional §0 update (PASS 3B) describing the final
  structure. `git diff` confirms the change is a pure prepended section (old §1-10 kept
  byte-for-byte, per the diff hunk starting at the top of the file).
- `baseline/LegalSeg` — the git submodule showing a dirty checkout. **Pre-existing**,
  present in `git status` at the very start of this entire multi-session engagement
  (visible in this conversation's initial `gitStatus` context), never touched by PASS
  1–3B, the Final Structure Audit, or the validator fix. Confirmed explicitly out of
  scope by every prior report (`REPOSITORY_MANIFEST.md` §10, `PASS3B_REORGANIZATION_REPORT.md`).

### 1e. Reconciliation: does every deletion have a corresponding addition?

`229` deleted vs. `211` new files under `evaluation/` (excluding the 15
renamed-not-deleted `examples/`/`live_demo/` files, which are accounted for in §1a) plus
`6` genuinely-new files with no `testing/` counterpart
(`FINAL_STRUCTURE_AUDIT_REPORT.md`, `NATURAL_DATA_VALIDATOR_FIX_REPORT.md`,
`PASS1_5_VERIFICATION_REPORT.md`, `PASS3A_REORGANIZATION_REPORT.md`,
`PASS3B_REORGANIZATION_REPORT.md`, `REPOSITORY_FINAL_STRUCTURE_PLAN.md`) leaves a gap of
`229 - (211 - 6) = 24` files that were deleted with no direct one-to-one replacement.
This gap is **fully explained and pre-documented**, not unaccounted loss:
`archive/cleanup_history/CLEANUP_PASS1_MANIFEST.md` records exactly this arithmetic —
an 11-files-across-8-directories → 1-file inputs/ consolidation, a
component_tests → components merge (README+RESULT pairs merged, duplicate stage
numbering resolved), and a documented list of pure regression-log files deleted because
their pass/fail facts are already restated in a kept `.md`/`.json` (e.g.
`pytest_execution.log` files superseded by each stage's `RESULT.md`). Spot-checked: none
of the deleted log files are cited by any live script or currently-read documentation
(§7). **PASS.**

## 2. `git diff --check`

```
git diff --check
```
**Exit 0, no output.** **PASS** — zero whitespace errors in any tracked, staged, or
unstaged change.

## 3. All workspace validators

```
research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_*.py
```

| Validator | Result |
|---|---|
| `validate_ablation.py` | **PASS** (50 checks passed, 0 warnings, 0 failures) |
| `validate_faculty_package.py` | **PASS** (9 checks passed, 0 failures, 0 warnings) |
| `validate_figure_data.py` | **PASS** (54 checks passed, 0 warnings, 0 failures) |
| `validate_figures.py` | **PASS** (66 checks passed, 0 failures) |
| `validate_gold_benchmark_outputs.py` | **PASS** (36 checks passed, 4 warnings, 0 failures) — pre-existing historical-metadata-hash warnings, documented since `PASS1_5_VERIFICATION_REPORT.md` |
| `validate_gpu_209_reproduction.py` | **PASS** (7 checks passed, 0 failures, 0 warnings) |
| `validate_gpu_experiments.py` | **PASS** (13 checks passed, 0 failures, 0 warnings) |
| `validate_inputs.py` | **PASS** (38 checks passed, 0 warnings, 0 failures) |
| `validate_metrics_consolidation.py` | **PASS** (75 checks passed, 0 warnings, 0 failures) |
| `validate_natural_data.py` | **PASS** (32 checks passed, 1 warning, 0 failures) — fixed this session; see §9 |
| `validate_reconciliation.py` | **PASS** (10 checks passed, 0 failures, 0 warnings) |
| `validate_release_audit.py` | **PASS** (11/11 checks passed, 0 failures, 1 warning) — pre-existing informational note (`PROVENANCE.md` has no dedicated STEP 11/12 header; documented as intentional) |

**12/12 PASS. Overall: PASS.**

## 4. `pytest research/prototype/tests/`

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
```

```
........................................................................ [ 35%]
........................................................................ [ 70%]
.............................................................            [100%]
205 passed, 1 warning in 11.28s
```

**205/205 passed. PASS.** (The 1 warning is the pre-existing, unrelated
`huggingface_hub` `resume_download` `FutureWarning` from
`test_correction_path_real_integration.py`, present in every prior run of this suite.)

## 5. Protected paths — `src/`, `tests/`, `config/`, `research/data/`, `outputs/`

```
git status --short research/prototype/src research/prototype/tests \
  research/prototype/config research/data research/prototype/outputs
```

**Empty output. PASS.** None of the five protected paths appear anywhere in `git
status` — not modified, not staged, not deleted, not untracked. `git diff --stat --
research/prototype/config/prototype.yaml` also returns empty (the production config
hash is unchanged).

## 6. Final repository structure coherent after PASS 1–3B

**PASS**, on the following evidence:

- Root: `README.md`, `REPOSITORY_MANIFEST.md` (with its new §0), `FINAL_PRODUCTION_CONFIG.md`,
  `Dockerfile`, `docker-compose.yml` — all present, all previously reviewed as current
  (Final Structure Audit §2c).
- `research/prototype/`: `README.md`, `REPRODUCIBILITY.md`, `config/`, `src/`, `tests/`,
  `scripts/` (production reproduction scripts, untouched), `outputs/` (125 files,
  untouched), `archive/2026-08-27_presentation/` (101 archived files + 1 new README),
  `evaluation/` (226 files: the full PASS 1–13/3B workspace plus this session's 3 report
  files and validator fix).
- No orphaned directory: `research/prototype/testing/`, `research/prototype/final_demo_pack/`,
  and `research/prototype/final_comparison/` no longer exist anywhere on disk — confirmed
  via `find`, not just `git status`.
- `research/prototype/evaluation/` internal structure matches exactly what
  `REPOSITORY_MANIFEST.md` §0 and `evaluation/README.md` §13 describe (component
  categories: production code references, production test references, dataset/input
  sources (`inputs/`), final evaluation results (`reports/`, `metrics/`), component-level
  evidence (`components/`), GPU validation evidence (`actual_outputs/gpu_*`,
  `metrics/GPU_*`), figures (`figures/`), and archived historical/presentation material
  (`archive/`) — all clearly separated into distinct, correctly-named subdirectories).

## 7. No deleted/intermediate artifact required by any live script or documentation

Checked two ways:

1. **Grep for literal old-path strings** (`component_tests`, `prototype/testing`,
   `prototype\testing`) across every live `.py`/`.md`/`.json`/`.csv` file under
   `evaluation/`, excluding `archive/`, the PASS reports, and the two STEP-13 frozen
   audit documents (which are documented, intentionally-frozen historical records).
   **Zero hits in any `.py` script.** The only hits anywhere are inside `run_metadata.json`/
   `*.meta.json` files, in a `"command_executed"`/`"cwd"`-style provenance field
   recording the literal command that was run **at the time**, when the workspace was
   still physically at `testing/` — a frozen historical fact, not a path a script
   resolves today. Confirmed by inspection: e.g.
   `evaluation/components/run_metadata.json` line 12 reads
   `"research/.venv/Scripts/python.exe research/prototype/testing/run_step5_component_demos.py"`
   as a recorded string value, not code.
2. **`validate_release_audit.py`'s own `REQUIRED_DIRS`/path checks** (11/11 passing, §3)
   independently confirm every currently-required directory resolves.

One known, pre-existing, out-of-scope dangling reference remains and was **not**
introduced or touched by this pass: `evaluation/ablation/GPU_ABLATION_UPDATE.md` line 20
cites a `JOINT_FOUR_LEVER_STEP10.md` file that does not exist anywhere in the repository.
This was first flagged in `archive/cleanup_history/CLEANUP_PASS1_MANIFEST.md` §"Deferred
to PASS 2" as confirmed pre-existing and explicitly left as-is (fixing it would require a
content investigation outside every subsequent pass's authorized scope, including this
one). **PASS, with this one documented, carried-forward limitation** (see §11).

## 8. All live README/navigation links resolve

Re-ran the same real-hyperlink checker (`[text](path)` syntax only, not prose backtick
mentions) used in the Final Structure Audit, across every `.md` file under `research/`,
excluding files already established as frozen historical/process records
(`archive/`, `PASS*_REPORT.md`, `PASS1_5_VERIFICATION_REPORT.md`,
`REPOSITORY_FINAL_STRUCTURE_PLAN.md`, `reports/archive/`,
`reports/FINAL_RELEASE_AUDIT.md`, `reports/FINAL_WORKSPACE_MANIFEST.md`):

```
CHECKED 5 links across 90 live files
BROKEN 1  (research/prototype/evaluation/FINAL_STRUCTURE_AUDIT_REPORT.md -> "path")
```

Inspected the one hit directly: it is literal example text —
`` `[text](path)` `` — inside a sentence *describing* the link-check methodology, not an
actual link. **0 genuine broken links. PASS.**

## 9. Review of `NATURAL_DATA_VALIDATOR_FIX_REPORT.md` — did the fix weaken a genuine check?

Independently re-verified, not just re-read, by constructing synthetic adversarial
inputs and running them through the exact regex/logic now in
`validate_natural_data.py`:

- **Hash-comparison check** (`check_sources_unchanged`): the new `is_baseline_only`
  branch only changes behavior for the 8 entries whose own `hash_report.json`
  `"comparison"` field literally reads `"no prior recorded hash..."`. The 4 entries with
  a genuine `"against STEP 3 recorded hash"` comparison are untouched by the new branch
  — a hash mismatch on any of those would still call `fail()` exactly as before. Verified
  by re-reading the code path: the `is_baseline_only` flag gates only the `warn()`
  vs. `fail()` choice, never suppresses the check itself.
- **Accuracy/F1 terminology check** (`check_no_accuracy_terms`): built 5 synthetic
  natural-data violation strings (e.g. `"the 588-claim natural aggregate achieved 66.3%
  accuracy"`, a table row `"| 588-claim aggregate | 0.6633 accuracy | natural | 588 |"`,
  and a prose bullet under an explicit `- **Dataset**: 209-claim paired natural
  evaluation` line) and ran them through the exact `forbidden`/`allowed_context`/
  `gold_dataset` regex objects now in the file: **all 5 are still correctly flagged**.
  Also tested the specific adjacency risk called out in the fix report — a fabricated
  natural-data accuracy row placed immediately after a real GOLD-01 row in the same
  markdown table — to confirm the table-row-scoped (not section-wide) context check does
  not leak a GOLD exemption onto a neighboring natural-data row: **confirmed correctly
  flagged** (`[False, True]` — GOLD row exempted, natural row still caught).

**No genuine integrity or terminology check was weakened.** Both changes are narrowly
additive: one recognizes a self-declared "no baseline to compare" data state and reports
it as an accurately-worded warning instead of a mischaracterized failure; the other
recognizes the two datasets (GOLD-01, GOLD-02) where accuracy/F1 language is legitimate,
without loosening the check for any natural-data context. **PASS.**

## 10. Commit candidate list

### 10a. Should be committed (one coherent change set — the full PASS 1–3B
reorganization plus this session's navigation and validator fixes)

**Modified:**
- `REPOSITORY_MANIFEST.md`

**Staged renames (116 total, `git add` already reflects these — no action needed beyond
including them in the commit):**
- `research/prototype/final_comparison/**` → `research/prototype/archive/2026-08-27_presentation/final_comparison/**` (34 files)
- `research/prototype/final_demo_pack/**` (non-promoted remainder) → `research/prototype/archive/2026-08-27_presentation/final_demo_pack/**` (67 files)
- `research/prototype/final_demo_pack/examples/**` → `research/prototype/evaluation/examples/**` (13 files, 4 with an additional path-citation edit)
- `research/prototype/final_demo_pack/live_demo/**` → `research/prototype/evaluation/live_demo/**` (2 files, 1 with an additional path-citation edit)

**Deletions (229 files, the superseded `research/prototype/testing/` tree — commit the
deletion; the paths no longer exist and nothing references them, per §7):**
- `research/prototype/testing/**` (entire tree)

**New/untracked (22 entries, 212 files — the full evaluation workspace plus this
session's two prior reports and the validator fix, plus the new archive index):**
- `research/prototype/evaluation/**` (all 226 files currently on disk, i.e. every
  currently-untracked file/directory under it — `README.md`, `MANIFEST.md`,
  `PROVENANCE.md`, `PASS1_5_VERIFICATION_REPORT.md`, `PASS3A_REORGANIZATION_REPORT.md`,
  `PASS3B_REORGANIZATION_REPORT.md`, `REPOSITORY_FINAL_STRUCTURE_PLAN.md`,
  `FINAL_STRUCTURE_AUDIT_REPORT.md`, `NATURAL_DATA_VALIDATOR_FIX_REPORT.md`,
  `ablation/`, `actual_outputs/`, `archive/`, `comparisons/`, `components/`,
  `expected_outputs/`, `figures/`, `inputs/`, `integration_tests/`, `metrics/`,
  `reports/`, `scripts/`)
- `research/prototype/archive/2026-08-27_presentation/README.md` (new archive index)
- `research/prototype/evaluation/FINAL_PRE_COMMIT_AUDIT.md` (this report, once saved)

A plain `git add -A` (or an equivalent scoped `git add REPOSITORY_MANIFEST.md
research/prototype/final_comparison research/prototype/final_demo_pack
research/prototype/testing research/prototype/evaluation
research/prototype/archive/2026-08-27_presentation`) followed by a commit captures all
of the above as one coherent, internally-consistent change. Git's own diff-time rename
detection (`git log --follow`, `git diff -M`, GitHub/GitLab's PR view) will still
recognize the `testing/` → `evaluation/` correspondence heuristically from content
similarity even though it is recorded as delete+add rather than an explicit rename —
this is a cosmetic difference only (already flagged in `PASS3B_REORGANIZATION_REPORT.md`
§9), not a functional or reviewability problem, and is **not** a blocker.

### 10b. Should NOT be committed / should remain excluded

- **`baseline/LegalSeg`** (the dirty submodule state). This predates every pass in this
  engagement, was never touched by any of them, and is explicitly out of scope per
  `REPOSITORY_MANIFEST.md` §10 ("out of scope, untouched... shows as locally modified in
  `git status`... not touched, per this task's explicit instructions"). Committing it
  would either require `git add baseline/LegalSeg` (updating the submodule's recorded
  commit, which is not this engagement's decision to make) or would otherwise be
  silently skipped by `git add -A` for regular files but still show as dirty — recommend
  leaving it exactly as found and calling it out to whoever performs the commit so they
  don't `git add` it by accident with a blanket `git add .` at the repo root run from
  outside `research/`.
- Nothing else. No secrets, credentials, `.env` files, `.venv/`, `__pycache__/`, or
  `.pytest_cache/` content appears anywhere in `git status` (all correctly excluded by
  `.gitignore`, independently re-confirmed this pass) or the untracked-file scan.

## 11. Remaining known limitations (carried forward, not introduced by this pass)

- **`validate_natural_data.py`'s 1 remaining warning** (§3, §9): the
  `run_natural_targeted.jsonl` entry in `hash_report.json` records a baseline hash that
  does not match the file's actual (git-confirmed unchanged) content — a pre-existing
  data-entry error in that one historical record, not a live integrity problem.
  Un-fixed by design (fixing it would mean editing a historical record, out of this
  task's scope) and now surfaced accurately instead of as a false failure.
- **`validate_gold_benchmark_outputs.py`'s 4 warnings**: pre-existing GOLD-01/GOLD-02
  dataset-hash inconsistencies in two historical metadata files, traced to the
  workspace's creation commit and documented since `PASS1_5_VERIFICATION_REPORT.md`. The
  live GOLD fixtures on disk are independently confirmed correct; only the historical
  metadata strings are stale.
- **`validate_release_audit.py`'s 1 informational warning**: `PROVENANCE.md` has no
  dedicated `## STEP 11` / `## STEP 12` header (those deliverables live under `reports/`
  instead, by their own documented task scope) — a documentation-completeness note, not
  a defect.
- **`JOINT_FOUR_LEVER_STEP10.md` dangling reference** (§7): a citation in
  `ablation/GPU_ABLATION_UPDATE.md` to a file that was never created. Pre-existing since
  PASS 1, confirmed not caused by any subsequent pass, left as-is per every prior
  report's scope boundary.
- **Cosmetic `git status` rename detection** (§1b, §10a): the `testing/` → `evaluation/`
  move shows as 229 deletions + a separate untracked-additions set rather than paired
  renames, because PASS 3A used PowerShell `Move-Item` instead of `git mv`. Functionally
  inert (content is complete and correct; git's diff-time similarity detection still
  recognizes the correspondence) — a `git log --follow` ergonomics note only.

None of these four limitations block a commit: each is a previously-documented,
independently-verified non-issue (stale historical metadata, a scope-excluded frozen
citation, or a cosmetic git-history artifact), not a defect in the current, live
repository state.

## 12. Final recommendation

**READY TO COMMIT.**

All ten requested checks passed:

| # | Check | Result |
|---|---|---|
| 1 | `git status --short` accounted for | **PASS** — all 369 entries traced to a documented cause |
| 2 | `git diff --check` | **PASS** — 0 whitespace errors |
| 3 | All workspace validators | **PASS** — 12/12 |
| 4 | `pytest research/prototype/tests/` | **PASS** — 205/205 |
| 5 | Protected paths untouched | **PASS** — `git status` empty for all five |
| 6 | Final structure coherent | **PASS** |
| 7 | No live script/doc needs a deleted artifact | **PASS** (1 pre-existing, documented, out-of-scope exception) |
| 8 | Live README/navigation links resolve | **PASS** — 0 genuine broken links |
| 9 | Validator fix didn't weaken a genuine check | **PASS** — independently re-verified with synthetic adversarial inputs |
| 10 | Commit candidate list identified | **DONE** — §10 |

No blocking issue was found. The only file that should be deliberately excluded from
the commit is the pre-existing, out-of-scope `baseline/LegalSeg` submodule state. This
audit did not modify, stage, or commit anything.
