# Repository Final Structure Plan

**Status**: PLANNING ONLY. No file was modified, moved, deleted, renamed, or generated
by this document's analysis — the only file this phase creates is this report itself,
per your explicit instruction. **Do not execute anything below without separate
approval.**

**Baseline inspected**: the repository as it stands after PASS 1 (component/input/
ablation consolidation), PASS 1.5 (move verification), the GOLD hash reconciliation, and
PASS 2 (reports/evaluation/figures/integration_tests cleanup) — all four already
executed and reported earlier in this session, none committed. This plan looks at what's
left.

---

## 1. Recursive inspection summary

| Area | Current state |
|---|---|
| `research/prototype/src/` | 10 production modules, untouched by any pass |
| `research/prototype/tests/` | 12 files, 205 tests, untouched |
| `research/prototype/config/` | 1 file (`prototype.yaml`), untouched |
| `research/prototype/scripts/` | 31 reusable scripts, untouched |
| `research/prototype/outputs/` | 120 files, the frozen raw experimental ledger, untouched |
| `research/prototype/final_demo_pack/` | 2026-08-27 presentation pack, untouched, protected |
| `research/prototype/final_comparison/` | 2026-08-27 comparison pack, untouched, protected |
| `research/prototype/testing/` | The STEP 1-13 workspace — this is where PASS 1/1.5/2 did all their work; see below |
| Root: `README.md`, `FINAL_PRODUCTION_CONFIG.md`, `REPOSITORY_MANIFEST.md` | Untouched by any pass; `REPOSITORY_MANIFEST.md` confirmed severely stale (dated 2026-08-27, zero mention of `testing/`, wrong file count) |

`research/prototype/testing/` current layout (post-PASS-2):

```
testing/
├── README.md, MANIFEST.md, PROVENANCE.md          [root navigation, all PASS-1/1.5-corrected]
├── PASS1_5_VERIFICATION_REPORT.md                  [kept permanent — evidentiary trail]
├── 13 validate_step*.py + 8 run_step*/build_step*.py + step4_common.py   [flat at root]
├── archive/cleanup_history/                        [2 files — PASS 1/reconciliation ledgers]
├── inputs/                                          [1 file — consolidated README.md]
├── expected_outputs/                                [1 top file + 2 GOLD-fixture subdirs]
├── actual_outputs/                                  [1 top file + 11 step-numbered subdirs]
├── comparisons/                                     [1 top file + expected_vs_actual/]
├── components/                                      [5 top files + 8 stage subdirs]
├── ablation/                                         [10 files, reunited in PASS 1]
├── evaluation/                                       [25 top files + archive/ (7) + figure_data/ (11) + input_integrity/ (2)]
├── figures/                                          [19 files: 11 PNGs + 8 index/audit/script files]
├── integration_tests/                                [1 file — honest unbuilt-work stub]
└── reports/                                          [9 files + archive/ (1 file)]
```

---

## 2-3. Classification and DELETE_CANDIDATE analysis

### CORE

| Path | Notes |
|---|---|
| `research/prototype/src/` (10 files) | Production pipeline code |
| `research/prototype/tests/` (12 files, 205 tests) | Production test suite |
| `research/prototype/config/prototype.yaml` | Production config |
| `research/prototype/scripts/` (31 files) | Reusable pipeline/reproduction scripts |

No DELETE_CANDIDATEs here — none inspected, per your protection list.

### INPUT

| Path | Notes |
|---|---|
| `research/data/` | Canonical evidence corpora (v0/v1), NyayaRAG case source — protected, untouched |
| `testing/inputs/README.md` | Consolidated (PASS 1) master input reference — GOLD/BEHAVIOR/METRIC-ONLY/PROVISIONAL classification, hashes, pipeline-flow diagram |
| `testing/expected_outputs/{controlled_benchmark_gold,synthetic_stress_gold}/` | The two true-GOLD fixtures, hash-verified (PASS 1.5 corrected the recorded hash) |

No DELETE_CANDIDATEs. `testing/expected_outputs/README.md` is real content (Category A/B/C taxonomy), not a pointer stub.

### COMPONENT_EVIDENCE

Per your instruction 7 — **none of this is classified as intermediate**, even though a
full-pipeline result also exists:

| Path | Notes |
|---|---|
| `testing/components/{01-08}_*/` | 8 pipeline-stage directories, each with merged README+RESULT (PASS 1), real demo data, real pass/fail counts. `05_correction` and `07_reverification` have README only — an honest, documented gap (no fabricated RESULT ever added) |
| `testing/components/{README,COMPONENT_TEST_SUMMARY,TEST_INVENTORY}.md` | Stage index, cross-cutting summary, full test inventory |
| `testing/components/run_metadata.json`, `STEP5_VALIDATION_REPORT.txt` | Unique commit-hash provenance and a real 37-check validation record |

No DELETE_CANDIDATEs. This is exactly the category your instruction 7 protects.

### EVALUATION

| Path | Notes |
|---|---|
| `testing/evaluation/` (25 top-level files) | `CANONICAL_METRICS.*`, `CONSOLIDATION_SOURCE_MAP.md`, `CONSOLIDATED_CONSISTENCY_REPORT.md`, `CORRECTION_FUNNEL.*`, `EVIDENCE_STRENGTH_MATRIX.*`, `GPU_*.md` (4), `HISTORICAL_CROSSCHECK_NATURAL.md`, `METRIC_DEFINITIONS.md`, `NATURAL_DATA_*` (3), `paired_209_analysis.csv`, `PAIRED_209_REPORT.md`, `SAFETY_SUMMARY.*`, `STATISTICAL_RESULTS.*`, `README.md` — all confirmed (twice, by independent forks in earlier turns) to carry real, non-duplicated evidentiary content |
| `testing/evaluation/figure_data/` (11 CSVs) | Locked source-data contracts for the 11 figures |
| `testing/evaluation/input_integrity/` | Hash-verification record for natural-batch data (separate from the GOLD fixtures) |
| `testing/actual_outputs/step4_gold_verifier/`, `step6_natural_data/` | Raw GOLD-verification and natural-data run outputs — the evidentiary base `evaluation/`'s reports narrate |

No new DELETE_CANDIDATEs found. **One REQUIRES_DECISION item** (see §10): the
`step4_`/`step6_`-prefixed directory names are chronological-workflow naming, not
functional naming — see §5/§6.

### ABLATION

| Path | Notes |
|---|---|
| `testing/ablation/` (10 files) | Reunited in PASS 1: README, GPU update, 7 `ABLATION_*` files, the real scope-check replay JSON |
| `testing/actual_outputs/step7_ablation/` | Now contains only substantive validator reports (`validate_step7_report.txt`) — the pure logs and the one real data file were already handled in PASS 1/2 |

No DELETE_CANDIDATEs. Same naming concern as EVALUATION (§5/§6).

### COMPARISON

| Path | Notes |
|---|---|
| `testing/comparisons/README.md`, `comparisons/expected_vs_actual/` | The one true GOLD-vs-actual comparison result, corrected in PASS 1 to stop citing a `metric_based/` subfolder that never existed |
| `research/prototype/final_comparison/` | Protected, not re-inspected this pass — see §10 for the carried-forward recommendation from earlier session-wide analysis |

### FIGURE

| Path | Notes |
|---|---|
| `testing/figures/` (19 files) | 11 canonical PNGs + `README.md`, `FIGURE_INDEX.md`, `FIGURE_CONTRACT_INVENTORY.md`, `FIGURE_NUMERIC_AUDIT.md`, `FIGURE_CLAIM_AUDIT.md`, `FIGURE_METADATA.csv`, `generate_figures.py`, `audit_figures.py` — confirmed by independent audit to have **zero redundant files**; every doc answers a distinct question |

No DELETE_CANDIDATEs — this directory needs nothing further.

### REPORT

| Path | Notes |
|---|---|
| `testing/reports/` (9 files) | `README.md` (rewritten, PASS 2), `FACULTY_EXECUTIVE_SUMMARY.md`, `FACULTY_EVALUATION_REPORT.md` (now includes the STEP 11 technical appendix), `FACULTY_RESULTS_TABLE.md`, `FACULTY_LIMITATIONS_AND_CAVEATS.md`, `FINAL_CLAIM_REGISTER.csv`, `FINAL_RELEASE_AUDIT.md`, `FINAL_REPRODUCIBILITY_MATRIX.md`, `FINAL_WORKSPACE_MANIFEST.md` — confirmed genuinely audience-tiered, no internal duplication |
| Root: `README.md`, `FINAL_PRODUCTION_CONFIG.md` | Real content, no overlap with each other |

No DELETE_CANDIDATEs remain here — PASS 2 already resolved this directory's redundancy.

### ARCHIVE

| Path | Contents | Why archived, not deleted |
|---|---|---|
| `testing/evaluation/archive/` (6 files + README) | STEP-8 pre-GPU summaries (`CONSOLIDATED_EXECUTIVE_SUMMARY.md`, `CONSOLIDATED_FACULTY_SUMMARY.md`, `HEADLINE_RESULTS.md`, `REPRODUCIBILITY_MATRIX.md`, `ORIGINAL_VS_CURRENT.{md,csv}`) | Each superseded in currency by a `reports/FACULTY_*` document, but each is a real, dated artifact — deleting would discard a legitimate point-in-time record |
| `testing/reports/archive/FINAL_RECONCILIATION_REPORT.md` | STEP 11's full reconciliation report | ~70% duplicated `FACULTY_EVALUATION_REPORT.md`; its 2 unique sections were copied forward before archiving; kept whole for anyone wanting the original |
| `testing/archive/cleanup_history/` (2 files + README) | `CLEANUP_PASS1_MANIFEST.md`, `HASH_RECONCILIATION_REPORT.md` | Process ledgers whose job is done, kept as a record of what PASS 1/reconciliation actually did |

Not moved (deliberately kept as a permanent, non-archived record):
`testing/PASS1_5_VERIFICATION_REPORT.md` — holds the only full git-archaeology
evidentiary trail behind the GOLD-hash finding.

### DELETE_CANDIDATE

**None identified this pass.** After two cleanup passes plus verification, every file
still on disk either (a) carries content with no full duplicate elsewhere, or (b) has
already been moved to an ARCHIVE location rather than deleted. This is a materially
different finding from PASS 1's audit (which found 26 pure-log files to delete) — the
easy deletions are already done. The remaining opportunities in this repository are
**renames and reorganizations for clarity**, not deletions — see §5/§6.

The closest things to a delete candidate, both rejected on inspection:

| Candidate | Why NOT a delete candidate |
|---|---|
| `.pytest_cache/` directories (root and `research/prototype/`) | Already gitignored, zero tracked footprint, regenerated automatically — not a real cleanup target |
| `testing/comparisons/expected_vs_actual/` raw CSVs | Looked like they might duplicate `evaluation/`'s data — confirmed distinct: this is the one true GOLD-vs-actual comparison, not duplicated anywhere |

---

## 4. Duplicate/superseded documentation — status check

Every item PASS 1/PASS 2 found has been resolved. Re-checked for anything missed:

| Item | Status |
|---|---|
| `component_tests/` vs `components/` numbering split | Resolved (PASS 1) |
| `inputs/` 11-file, 8-directory sprawl | Resolved (PASS 1, merged to 1 file) |
| `evaluation/ABLATION_*` split from `ablation/` | Resolved (PASS 1) |
| STEP-8 summaries superseded by faculty reports | Resolved (PASS 2, archived) |
| `FINAL_RECONCILIATION_REPORT.md` ~70% duplicate | Resolved (PASS 2, appendix-ized + archived) |
| `reports/README.md`, `evaluation/README.md` stale stubs | Resolved (PASS 1/2 rewrites) |
| `comparisons/metric_based/` phantom directory references | Resolved (PASS 1) |
| **Root `REPOSITORY_MANIFEST.md`** | **NOT resolved** — explicitly deferred to its own phase in PASS 2 (your decision 5). Still stale: predates `testing/` entirely, wrong file count. **Carried forward as a REQUIRES_DECISION item below.** |
| **`final_demo_pack/EXECUTIVE_SUMMARY.md` vs `reports/FACULTY_EXECUTIVE_SUMMARY.md`, `final_comparison/figures/` vs `testing/figures/`** | **NOT resolved** — `final_demo_pack/`/`final_comparison/` are protected directories this session has not touched since the very first planning pass flagged this overlap. Still an open, real duplication across the two 2026-08-27 packs and the newer `testing/` workspace. **Carried forward below.** |

No new duplication was found beyond these two known, already-flagged, deliberately
untouched items.

---

## 5. Confusing directory names for a final academic project

| Name | Why confusing | Recommendation |
|---|---|---|
| `research/prototype/tests/` vs `research/prototype/testing/` | One character apart, completely different purposes (production pytest suite vs. a STEP 1-13 evaluation workspace). This is the single most reader-hostile naming collision in the repository — a new developer cannot tell them apart from the name alone. | **Rename `testing/` → `evaluation/`** (see §6 for the resulting inner-directory collision and its resolution) |
| `testing/evaluation/` (inner) | Would collide with the proposed outer rename above | **Rename to `testing/metrics/`** (or, after the outer rename, `evaluation/metrics/`) — matches its actual content (computed metric rollups, not narrative) |
| `actual_outputs/step2_environment_setup/`, `step3_input_validation/`, `step4_gold_verifier/`, `step6_natural_data/`, `step7_ablation/`, `step8_consolidation/`, `step9_figures/`, `step10_gpu_experiments/`, `step10_gpu_validation/`, `step10b_gpu_experiments/` | Chronological workflow-step naming, meaningless to a reader who doesn't know there were 13 build steps — exactly the "STEP 1-13 history" your very first cleanup request asked to make invisible to a new developer | Rename to function-based names: `gold_benchmark_runs/`, `natural_data_runs/`, `gpu_validation_runs/`, and fold the now-log-only `step2/step3/step8/step9` directories' remaining validator reports into the directories they validate (see §6) |
| `components/05_correction/`, `07_reverification/` | Not confusing, but worth noting: these are the two stages with no RESULT.md (an honest, documented gap, not a naming problem) | No change needed |
| 13 `validate_step*.py` + 8 `run_step*.py`/`build_step*.py` files flat at `testing/` root | 21 scripts named by STEP number, sitting in one flat directory — a future developer has to open each to learn what it validates | Consider a `testing/scripts/` subdirectory, or rename by function (`validate_gold_benchmark.py` instead of `validate_step4_outputs.py`) — flagged as a REQUIRES_DECISION item, not a strong recommendation, since STEP-number names do at least map 1:1 to `PROVENANCE.md`'s own STEP sections |

---

## 6. Proposed final architecture

```
research/prototype/
├── README.md, REPRODUCIBILITY.md, FINAL_PRODUCTION_CONFIG.md   [unchanged]
├── src/, tests/, config/, scripts/, outputs/                    [unchanged — CORE/INPUT, untouched]
├── archive/                                                      [NEW top-level, see below]
│   └── 2026-08-27_presentation/
│       ├── final_demo_pack/       [moved here — see §10, REQUIRES_DECISION]
│       └── final_comparison/      [moved here — see §10, REQUIRES_DECISION]
└── evaluation/                                                   [RENAMED from testing/]
    ├── README.md, MANIFEST.md, PROVENANCE.md                     [unchanged content, path-updated]
    ├── PASS1_5_VERIFICATION_REPORT.md                            [unchanged — permanent]
    ├── scripts/                                                  [NEW — the 21 validate/run/build *.py files, optionally renamed by function]
    ├── archive/
    │   └── cleanup_history/                                      [unchanged]
    ├── inputs/                                                   [unchanged]
    ├── expected_outputs/                                         [unchanged]
    ├── gold_benchmark_runs/                                      [RENAMED from actual_outputs/step4_gold_verifier/]
    ├── natural_data_runs/                                        [RENAMED from actual_outputs/step6_natural_data/]
    ├── gpu_validation_runs/                                      [RENAMED from actual_outputs/step10*/]
    ├── build_process_logs/ (or deleted — see decision needed)    [the residual step2/3/8/9 validator-only folders]
    ├── comparisons/                                               [unchanged]
    ├── components/                                                [unchanged]
    ├── ablation/                                                  [unchanged]
    ├── metrics/                                                   [RENAMED from the inner evaluation/]
    │   ├── archive/                                                [unchanged]
    │   ├── figure_data/                                            [unchanged]
    │   └── input_integrity/                                        [unchanged]
    ├── figures/                                                    [unchanged — already clean]
    ├── integration_tests/                                          [unchanged, or resolved per §10]
    └── reports/                                                    [unchanged]
        └── archive/                                                [unchanged]
```

This tree is a **proposal**, not an instruction to execute. Two structural decisions
(the `final_demo_pack`/`final_comparison` disposition, and whether to rename the
`step*_` output directories at all given they map to `PROVENANCE.md`'s own section
numbers) are listed as REQUIRES_DECISION in §10, not assumed.

---

## 7. Component-level evidence preservation — explicit confirmation

Every file under `testing/components/` is classified COMPONENT_EVIDENCE, not
intermediate, in §2 above. None is proposed for deletion, archival, or merging into a
"final pipeline result" document. The only content-level actions ever taken against this
directory (in PASS 1) were: consolidating two STEP-numbering schemes for the *same*
stage into one directory (verified by content, not assumed from naming), and merging
README+RESULT pairs — zero content was dropped, verified line-by-line at the time. This
plan proposes no further change to `components/` beyond the pure directory rename that
comes from moving its parent from `testing/` to `evaluation/`.

---

## 8. Historical evidence — archive-not-delete confirmation

Every item in §2's ARCHIVE category is a **move recommendation already executed** (PASS
2), never a deletion. This plan finds no additional historical evidence that isn't
already either (a) live and current, or (b) already archived. The `final_demo_pack/` and
`final_comparison/` packs (§10) are the one remaining body of historical evidence this
session has not yet acted on, and this plan recommends ARCHIVE (not delete) for them
too, consistent with the pattern already established.

---

## 9. Path/code/reference impact if this architecture is adopted

This is the largest risk in this proposal — larger than PASS 1's `component_tests/` →
`components/` rename, because `testing/` → `evaluation/` touches the *directory every
other path in this workspace is relative to*.

| Change | Blast radius |
|---|---|
| `testing/` → `evaluation/` | Every one of the ~150 files under this directory that uses a relative path like `../../actual_outputs/...` is unaffected (relative paths survive a pure parent rename) — but every **absolute-looking** string like `"testing/components/..."` embedded in `.md`/`.csv`/`.json`/`.py` content (confirmed to exist in dozens of places from PASS 1/2's own cleanup work) needs a find-and-replace pass. Also: `research/prototype/README.md`, `REPRODUCIBILITY.md`, and any root-level doc that names `research/prototype/testing/` needs updating. |
| Inner `evaluation/` → `metrics/` | All `EVAL_DIR`/`ABLATION_DIR`-style path constants in the 21 root-level scripts need re-checking (PASS 1/2 already introduced `ABLATION_DIR` as a separate constant from `EVAL_DIR` in several scripts — a `metrics/` rename would require updating `EVAL_DIR` itself in each) |
| `actual_outputs/step4_gold_verifier/` etc. → function-named dirs | `run_gold01_evaluation.py`'s own `RUN_DIR`/`OUT_DIR` constants, `build_step8_consolidation.py`'s `STEP4`/`STEP6` constants, `reports/FINAL_CLAIM_REGISTER.csv`'s and `FINAL_WORKSPACE_MANIFEST.md`'s path citations, and `PROVENANCE.md`'s narrative citations all reference these paths by their current STEP-numbered names |
| 21 scripts → `scripts/` subdirectory | Every script's own `TESTING_DIR = Path(__file__).resolve().parent` would need to become `.parent.parent`, and every doc that says "run `research/.venv/Scripts/python.exe research/prototype/testing/validate_X.py`" needs its path string updated |
| `final_demo_pack/`/`final_comparison/` → `archive/2026-08-27_presentation/` | Citers already inventoried in this session's first planning pass: `ARTIFACT_INDEX.md`, `DATA_LINEAGE.md`, several `inputs/`-adjacent docs, `testing/PROVENANCE.md` |

**None of this has been executed.** Given the size of the `testing/` → `evaluation/`
blast radius specifically, if approved, it should be its own isolated phase with a
full grep-and-fix pass immediately after the rename, followed by re-running every
validator and `pytest` — the same discipline PASS 1 used for the smaller
`component_tests/` → `components/` rename.

---

## 10. SAFE TO DELETE / SAFE TO ARCHIVE / KEEP WHERE IT IS / REQUIRES YOUR DECISION

### SAFE TO DELETE
**Nothing.** No new delete candidates were found this pass (see §3).

### SAFE TO ARCHIVE
Nothing new — all prior archive recommendations (§2 ARCHIVE category) are already
executed. The only remaining archive candidate is `final_demo_pack/`/`final_comparison/`,
which is listed under REQUIRES YOUR DECISION below because it is a protected directory
this plan was not authorized to inspect deeply enough to finalize on its own.

### KEEP WHERE IT IS
`src/`, `tests/`, `config/`, `scripts/`, `outputs/`, `research/data/` — all CORE/INPUT,
untouched by any pass, no change proposed. `components/`, `ablation/`, `comparisons/`,
`figures/`, `reports/`, `inputs/`, `expected_outputs/` — all confirmed clean; the only
change proposed for these is the pure parent-directory rename in §6, not any internal
reorganization.

### REQUIRES YOUR DECISION

1. **`testing/` → `evaluation/` rename** (+ inner `evaluation/` → `metrics/`). Resolves
   the `tests/`/`testing/` confusion you specifically flagged. Largest blast radius in
   this plan (§9) — recommend as its own isolated phase if approved.
2. **`actual_outputs/step*_*/` → function-named directories** (`gold_benchmark_runs/`,
   `natural_data_runs/`, `gpu_validation_runs/`). Removes STEP-chronology naming from the
   final-facing structure, but these names currently map 1:1 to `PROVENANCE.md`'s own
   STEP sections — renaming means `PROVENANCE.md`'s narrative and the directory
   structure would use different vocabularies unless `PROVENANCE.md` is also annotated.
3. **The now-log-thin `actual_outputs/step2_environment_setup/`, `step3_input_validation/`,
   `step8_consolidation/`, `step9_figures/`** — each now holds only its substantive
   validator report(s) (the pure logs were deleted in PASS 1). Fold these into the
   directories/reports they validate, rename, or leave as-is? Not a delete question
   (their content is real) — purely an organizational one.
4. **21 root-level scripts → `scripts/` subdirectory**, or rename-by-function while
   staying flat? Either is defensible; flagged because it changes every script's own
   `TESTING_DIR` constant if moved.
5. **`final_demo_pack/`/`final_comparison/` disposition** — carried forward from the
   very first planning pass this session, never executed because both are protected
   directories. Recommend: archive the bulk of both to
   `research/prototype/archive/2026-08-27_presentation/`, but first promote
   `final_demo_pack/live_demo/` (a unique, runnable demo script) and
   `final_demo_pack/examples/` (8 unique hand-picked case studies) into the renamed
   `evaluation/` tree, since archiving them wholesale would bury genuinely unique
   content found nowhere else.
6. **Root `REPOSITORY_MANIFEST.md` refresh** — still stale, still deferred (your PASS 2
   decision 5). Needs its own pass regardless of whether the renames above are approved.
7. **`integration_tests/`** — still the honest, unbuilt-work stub. Build the two
   described wrappers, or fold the design note into `reports/` as "Future Work" and
   retire the directory? No test will be invented either way, per your standing
   instruction.
8. **Pre-existing hash-documentation bug beyond the two GOLD fixtures** — PASS 2's
   validator run surfaced that `outputs/run_natural_targeted.jsonl`'s recorded hash has
   the same defect as the original GOLD-hash finding (confirmed via `git log --follow`:
   the file has one commit, one hash, and the recorded value was never correct). A full
   audit of every recorded hash in `evaluation/input_integrity/hash_report.json` and
   elsewhere would be needed to find every remaining instance. Not attempted in PASS 2
   (declared out of scope); still open.
9. **`validate_step6_natural_data.py`'s over-broad terminology regex** — produces 9
   false positives on legitimate GOLD-benchmark accuracy mentions in files this session
   never edited. A validator-quality fix, not a structural cleanup action; flagged for a
   separate decision on whether to invest in tightening it.

---

**PLANNING COMPLETE — NO FILES MODIFIED, MOVED, DELETED, OR RENAMED.** Waiting for your
approval on any of the 9 items in §10 before a PASS 3 executes anything.
