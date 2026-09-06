# Repository Manifest

## 0. Update — 2026-09-06 (repository cleanup PASS 1 through PASS 3B)

**Everything below this section (§1-10) is the original 2026-08-27 manifest, kept
unedited as the historical record of that specific pass.** A separate, later cleanup
(PASS 1 through PASS 3B, 2026-09-05/06) restructured `research/prototype/` further. This
section describes the **current, final structure** — read this first; treat §1-10 as
history, not as a description of the repository as it stands today.

### What changed since 2026-08-27

- Added `research/prototype/evaluation/` — a full presentation/evaluation workspace
  (input inventories, component/integration/ablation test results, dataset-level
  metrics, faculty-facing reports, figures, and the reproduction scripts for all of it).
  Built fresh across STEP 1-13, then reorganized in three cleanup passes (PASS 1, PASS 2,
  PASS 3A) — see `research/prototype/evaluation/PROVENANCE.md` and
  `research/prototype/evaluation/PASS3A_REORGANIZATION_REPORT.md` for the full history.
  It only ever reads `src/`, `config/`, `outputs/`, and `research/data/`; it writes
  nothing back into any of them.
- Added `research/prototype/archive/2026-08-27_presentation/` — `final_demo_pack/` and
  `final_comparison/` (the two presentation/comparison layers built on 2026-08-27, listed
  in §2 below under `research/prototype/`) moved here unedited in PASS 3B, since their
  role as a one-time presentation snapshot is now superseded by the live `evaluation/`
  workspace. Nothing was deleted — see that archive's own `README.md` for the full
  disposition, including two subdirectories (`live_demo/`, `examples/`) that were
  promoted into `evaluation/` instead of archived, because they are reusable tooling
  rather than presentation-snapshot narrative.
- `research/prototype/scripts/` (the production reproduction scripts described in §2
  below) is unchanged — do not confuse it with the newer, separate
  `research/prototype/evaluation/scripts/` (the evaluation workspace's own validate/build
  scripts, moved there from the workspace root in PASS 3A).
- Nothing described in §1-10 below was altered: `src/`, `tests/`, `config/prototype.yaml`,
  `research/data/`, and `research/prototype/outputs/` are exactly as this original
  manifest describes them.

### Current top-level structure (`research/prototype/`)

```
research/prototype/
├── README.md, REPRODUCIBILITY.md
├── config/prototype.yaml          — unchanged, see §2/§7 below
├── src/                           — unchanged, see §2 below
├── tests/                         — unchanged, 205 tests, see §2/§9 below
├── outputs/                       — unchanged, 125 files, see §3 below
├── scripts/                       — unchanged, production reproduction scripts, see §2 below
├── archive/2026-08-27_presentation/
│   ├── README.md                  — full disposition of what moved here and why
│   ├── final_demo_pack/           — 67 files (2 subdirs promoted out, see above)
│   └── final_comparison/          — 34 files, unedited
└── evaluation/                    — presentation/evaluation workspace (new since 2026-08-27)
    ├── README.md                  — start here for this workspace
    ├── PROVENANCE.md, MANIFEST.md, PASS1_5_VERIFICATION_REPORT.md,
    │   PASS3A_REORGANIZATION_REPORT.md, REPOSITORY_FINAL_STRUCTURE_PLAN.md
    ├── inputs/, expected_outputs/, actual_outputs/, comparisons/
    ├── components/, integration_tests/, ablation/, metrics/, figures/
    ├── live_demo/, examples/      — promoted from final_demo_pack/ in PASS 3B
    ├── scripts/                   — every run_*/build_*/validate_* script, moved from
    │                                the workspace root in PASS 3A
    ├── reports/                   — faculty/reviewer-facing final reports
    └── archive/                   — this workspace's own superseded-in-place documents
                                      (PASS 1/PASS 2 process ledgers, superseded reports)
```

For the exact file-by-file disposition of the PASS 1 through PASS 3B cleanup (what moved,
what was archived, what was verified), see `research/prototype/evaluation/PROVENANCE.md`
and the `PASS*_REPORT.md`/`PASS*_VERIFICATION_REPORT.md` files alongside it.

---

# Repository Manifest — Publication Cleanup Pass (original, 2026-08-27)

Written 2026-08-27, after the pre-publication cleanup/consolidation pass over this repository.
This document records **what remains, in what role, and why** — the inventory this cleanup was
based on, so a future maintainer (or a paper reviewer) does not have to re-derive it. It does not
replace `README.md` (architecture), `research/prototype/REPRODUCIBILITY.md` (exact repro commands)
or `FINAL_PRODUCTION_CONFIG.md` (the production-config decision record) — it indexes them.

Scope: `research/` and repo-root files. `baseline/LegalSeg` (a separate git submodule) is out of
scope, per this task's own instructions, and was not touched.

**Note**: §2's structure tree and file count below describe the repository as it stood on
2026-08-27, before the `evaluation/` workspace and PASS 1-3B cleanup existed. See §0 above
for the current structure.

---

## 1. What this pass did

- Read every tracked file (199 → 195 after cleanup) and the full git history before touching
  anything.
- Found that this repository was **already conservatively curated** by the session that produced
  the 2026-08-27 "Finalize" commit: `REPRODUCIBILITY.md` §4 explicitly states nothing in `outputs/`
  was deleted during that pass because the final documents cite the earlier-phase experimental
  history as supporting evidence. Cross-checking confirmed this — nearly every file in `outputs/`
  is named explicitly, at least once, from `final_research_results.md`, `final_metrics.json`,
  `FINAL_PRODUCTION_CONFIG.md`, or `evidence_v1_independent_audit.md`.
- Removed only what had **zero references anywhere** in the repo and was explicitly scratch work
  (see §4).
- Found and fixed one **genuine reproducibility bug** (see §5) — not a methodology/threshold/config
  change, a code-only fix so the shipped entry point matches the already-documented production
  config.
- Re-ran the full test suite and `run_mvp.py --check` after every change; validated all 99 tracked
  JSON/JSONL files parse; cross-checked `final_metrics.json` against `final_research_results.md`
  and confirmed no lawyer-validation claim is ever made without its standard disclaimer.

## 2. Final structure (195 tracked files, excluding `baseline/LegalSeg`)

```
.
├── README.md, FINAL_PRODUCTION_CONFIG.md, REPOSITORY_MANIFEST.md (this file)
├── Dockerfile, docker-compose.yml, .dockerignore, .gitignore, .gitmodules
├── baseline/LegalSeg/                     — git submodule, out of scope
└── research/
    ├── requirements.txt
    ├── baseline/                          — frozen RhetoricLLaMA baseline reproduction
    │   ├── BASELINE.md, README.md, config/baseline.yaml, scripts/run_baseline.py
    ├── data/
    │   ├── evidence/                      — canonical statute corpus (v0 + v1, both required)
    │   │   ├── canonical_statutes.jsonl, evidence_audit.jsonl, README.md          (v0, 63 recs)
    │   │   └── canonical_statutes_v1.jsonl, evidence_audit_v1.jsonl, README_v1.md (v1, 82 recs, additive)
    │   └── nyayarag/CaseText_Statutes/*.json   — source case data (NyayaRAG)
    └── prototype/
        ├── README.md, REPRODUCIBILITY.md
        ├── config/prototype.yaml          — the final production config
        ├── src/                           — 9 modules, the pipeline itself
        ├── tests/                         — 11 test files, 205 tests, all passing
        ├── scripts/                       — 27 scripts, every one either the reproduction
        │                                    entry point or a named, cited experiment script
        └── outputs/                       — 122 files: the experimental record (see §3)
```

## 3. `outputs/` — the experimental record

This directory is a **lab notebook, not clutter**: every file is a dated checkpoint in a real
experimental sequence, and the final documents build on it explicitly. Organized here by family
(full detail in each family's own `.md`, or in `final_research_results.md`'s case census):

| Family | Files | Role |
|---|---|---|
| **Final/authoritative** | `final_research_results.md`, `final_metrics.json`, `final_limitations_and_future_scope.md`, `final_gpu_validation.md` (+`_A/_B/_corrections_detail.jsonl/_metrics.json`), `evidence_v1_independent_audit.md`, `labeled_correction_validation_gpu_metrics.json`/`_corrections_detail.jsonl`, `final_validation_bare_vs_labeled_cpu_claims.jsonl`/`_metrics.json` | The consolidated, paper-citable results and their raw backing data |
| **Case batches (n=30, targeted, batch1, batch2, final validation — 180 distinct cases total)** | `run_A/B/C_n30.jsonl`, `run_natural_targeted.jsonl`, `run_C_targeted_1994_495.jsonl`, `natural_candidates_50_gpu_*.jsonl`, `natural_candidates_batch2_gpu_*.jsonl`, plus each batch's `natural_candidate_pool*.json`/`natural_candidate_selected_ids_*.json`/`natural_candidate_selection_report*.md` | Each batch is disjoint (confirmed in `final_research_results.md` §0) and pooled into the "case census" — none is a duplicate of another |
| **Synthetic stress** | `run_synthetic_stress.jsonl`, `framing_comparison_synthetic*.{jsonl,json}`, `framing_comparison_gpu_n12*`, `framing_comparison_gpu_n59*` (incl. `_postfix`), `framing_comparison_natural*` | Sequential synthetic-stress and framing-comparison experiments feeding §A of `final_research_results.md` |
| **Framing/threshold/benchmark diagnostics** | `verifier_framing_{validation,gpu_validation,natural_validation}.md`, `verifier_correction_diagnosis.md`, `verifier_benchmark.jsonl`, `controlled_verifier_benchmark*`, `controlled_benchmark_deberta*`, `threshold_sensitivity_analysis.{md,json}` | Back the `premise_framing`/threshold decisions in `FINAL_PRODUCTION_CONFIG.md` §1/§5 |
| **Scope-check evolution** | `atomic_scope_check_replay.{md,json}`, `_replay_v2.{md,json}`, `_final_replay.{md,json}`, `respectively_atomic_claims_diagnosis.md`, `correction_reverification_framing.{md,jsonl}`, `natural_reverification_framing.{md,jsonl}` | Iterative development of `atomic_scope_check`/`assertion_spans`, each phase cited by the next |
| **Evidence/parser audit** | `no_evidence_diagnosis.json`, `no_evidence_taxonomy_v2.json`, `no_evidence_taxonomy_v3.json`, `evidence_coverage_v0_vs_v1.json`, `parser_fix_before_after_n30*.json` | Back §C of `final_research_results.md` (zero confirmed parser/matcher defects across 797 claims) |
| **Annotation protocol** | `gold_annotation.jsonl`/`_guide.md`/`_summary_template.md`, `lawyer_annotation.jsonl`/`_guide.md`, `assumption_annotation.jsonl`/`_summary.md`, `assumption_vs_automated_report.md`, `assumption_gold_bare_vs_labeled_*` | Methodology record for the (never-completed) human-gold-label protocol — see §6 |
| **Status reports (chronological, each cited by a later one)** | `pre_gpu_readiness_report.md`, `research_evaluation_final.md`, `mvp_assumption_evaluation.md`, `eval_30_report.md`, `natural_candidates_50_gpu_report.md`, `research_completion_report.md` (cited by `FINAL_PRODUCTION_CONFIG.md` §16a), `research_phase_next_status.md`, `phase2_natural_evaluation_results.json` | Sequential project-history checkpoints; `final_research_results.md` is the terminal consolidation, but earlier ones remain individually cited |
| **Docker smoke outputs** | `docker_run_A_n1.jsonl`, `docker_run_C_n1.jsonl` | Confirm the Docker image path actually runs Mode A/C |

**Nothing was removed from this list.** No file here was found to be a pure, valueless duplicate.

## 4. What was removed (REDUNDANT_SAFE_TO_REMOVE)

| Path | Reason |
|---|---|
| `research/prototype/scratch/analyze_synthetic_results.py` | Ad hoc one-off analysis script, zero references anywhere in the repo (grepped), conclusions already captured in the final reports |
| `research/prototype/scratch/check_extra.py` | Same — zero references, ad hoc debug script |
| `research/prototype/scratch/final_analysis.py` | Same — zero references |
| `research/prototype/scratch/run_fast_benchmark.py` | Same — zero references, not part of the documented reproduction path (`REPRODUCIBILITY.md` §3 lists the real benchmark scripts, this isn't one of them) |

The now-empty `research/prototype/scratch/` directory was removed with them. Nothing else met the
bar for removal — see §1: this repo had already had its scratch work curated out before this pass.
(`__pycache__/`, `.pytest_cache/` directories are gitignored/untracked already — zero git-visible
effect either way, not touched.)

## 5. Code fix (not a cleanup deletion, flagged and user-approved)

`research/prototype/scripts/run_mvp.py` — the README/REPRODUCIBILITY-documented entry point for
real Mode A/B/C runs — called `load_usable_evidence()` directly instead of the config-aware
`load_usable_evidence_from_config()`. Net effect: running `run_mvp.py --check` or `--mode {A,B,C}`
against the shipped `prototype.yaml` (`use_evidence_v1: true`) silently used only the 59-record v0
evidence pool instead of the documented 136-record v0+v1 production pool — a real divergence
between the documented production configuration and the actual behavior of the officially
documented reproduction command. The specialized experiment scripts
(`run_final_gpu_validation.py`, etc.) already called the config-aware loader correctly; only this
generic entry point had the gap.

**Fixed**: both `cmd_check()` and `cmd_run()` now call `load_usable_evidence_from_config(config,
repo_root)`. No threshold, model, methodology, or config value was changed — `prototype.yaml` is
byte-for-byte unchanged. Verified after the fix: `run_mvp.py --check` now reports "loaded 136
usable evidence records ... use_evidence_v1=True", and the full test suite still passes 205/205.

## 6. Lawyer/gold-annotation provenance — verified, no false claims found

`lawyer_annotation.jsonl` (88 rows) is currently populated with **Claude-generated provisional
labels**, not a real lawyer's answers — every record and every report that touches it (`README.md`,
`research_phase_next_status.md`, `mvp_assumption_evaluation.md`, `final_metrics.json` §E) says so
explicitly and consistently: *"No lawyer ground truth exists anywhere in this project."* The
`lawyer_annotation_guide.md` is the (unused, as of this pass) instructions document for when a real
lawyer's review happens. `gold_annotation.jsonl`/`_guide.md`/`_summary_template.md` are an earlier
iteration of the same protocol, kept as a methodology record. **No file or report claims validated
lawyer/legal-professional accuracy anywhere in this repository.**

_See `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

## 7. Evidence versioning — confirmed, both required

`canonical_statutes.jsonl`/`evidence_audit.jsonl` (v0, 63 records) and `canonical_statutes_v1.jsonl`/
`evidence_audit_v1.jsonl` (v1, 82 records) are **both required** — v1 is an additive supplement
merged on top of v0 at load time (`src/data_loader.load_usable_evidence`, `extra_canonical_path`/
`extra_audit_path`), never a replacement. `README.md` and `README_v1.md` document genuinely
different corpora and audit methodologies. Confirmed directly against `config/prototype.yaml` and
`src/data_loader.py`, not just the docs.

## 8. Secrets / local-machine dependencies

None found. `HF_TOKEN` is read from environment only (never hardcoded). No API keys, passwords, or
`.env` files are tracked. `.venv/`, `__pycache__/`, `.pytest_cache/`, `.claude/` are all correctly
gitignored. One hardcoded local scratch path exists at
`research/prototype/scripts/build_evidence_v1.py` (top-of-file `SCRATCH` constant) — this is a
**pre-existing, already-documented** limitation (`REPRODUCIBILITY.md` §6: the script is retained as
a methodology record, not a runnable pipeline step) and was not introduced or altered by this pass.

## 9. Verification performed after cleanup

| Check | Result |
|---|---|
| `pytest research/prototype/tests/ -q` | **205 passed**, both before and after every change |
| `run_mvp.py --check` | Passes; now correctly reports 136 usable evidence records |
| All tracked `.json`/`.jsonl` files parse | **99/99 valid** |
| Every path-like reference in the anchor docs resolves to an existing file | Confirmed (the only "misses" were a regex false-positive on `final_research_results.md` and one illustrative example command path in `README.md` that a user would generate themselves, not a citation of a committed artifact) |
| `final_metrics.json` vs. `final_research_results.md` | Numbers agree throughout (cross-read directly) |
| `config/prototype.yaml` vs. `FINAL_PRODUCTION_CONFIG.md` | Unchanged, matches the decision record exactly |
| Lawyer-validation claims | None found; all provisional labels correctly disclaimed everywhere |
| Secrets / hardcoded local paths | None found (outside the one pre-existing, documented case above) |
| `git diff` | Reviewed in full; only the 4 scratch-file deletions and the `run_mvp.py` fix are staged/modified |

## 10. Out of scope, untouched

- `baseline/LegalSeg` — separate git submodule; shows as locally modified in `git status` (untracked
  content inside the submodule checkout) from before this pass began — not touched, per this task's
  explicit instructions.
- All research methodology, model choices, thresholds, and evaluation results — unchanged.
