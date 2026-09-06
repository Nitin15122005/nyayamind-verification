# 2026-08-27 Presentation Materials (Archived in PASS 3B)

`final_demo_pack/` and `final_comparison/` were built on 2026-08-27 as a self-contained
presentation/comparison layer on top of `research/prototype/outputs/` and
`research/data/`. They are archived here unedited (moved, not modified) during PASS 3B
of the repository cleanup (2026-09-06) because their role — a one-time presentation
snapshot — is now superseded by the live `research/prototype/evaluation/` workspace's
own reports, figures, and metrics, which supersede them in currency and cross-reference
the same underlying `outputs/` evidence directly.

**Nothing here was deleted.** Every file from both original directories is preserved
below, byte-identical to how it was written on 2026-08-27.

## What was promoted out before archiving

Two subdirectories of `final_demo_pack/` were reusable tooling, not presentation-snapshot
narrative, and were promoted to the live workspace instead of archived:

| Original location | New location | Why promoted |
|---|---|---|
| `final_demo_pack/live_demo/` | `research/prototype/evaluation/live_demo/` | A real, GPU-free, code-path-verifying demo script (`run_demo.py`) that calls `src/*` directly — reusable tooling, not a historical artifact. Referenced by `evaluation/integration_tests/README.md` as the strongest existing asset for future integration-test work. |
| `final_demo_pack/examples/` | `research/prototype/evaluation/examples/` | Eight audited, real-case worked examples plus their reproducible selection scripts (`find_candidates.py`, `build_cases_json.py`) — a reusable, re-runnable methodology, not a frozen snapshot. |

Both promoted directories had their own internal self-references (comments/docstrings
pointing at their old `final_demo_pack/...` path) corrected to the new path. Everything
else in this archive was moved with its internal content untouched — cross-references
inside these archived files that still say `final_demo_pack/...` or `final_comparison/...`
refer to sibling files that moved with them and remain valid as relative citations within
this archive folder; any such reference to `live_demo/` or `examples/` specifically means
the promoted copy now at `evaluation/live_demo/` or `evaluation/examples/`.

## What's here

- `final_demo_pack/` (67 files) — `README.md`, `ARTIFACT_INDEX.md`, `DATA_LINEAGE.md`,
  `EXECUTIVE_SUMMARY.md`, `METRICS_TABLE.md`, `RUNBOOK.md`, `SYSTEM_STATUS.md`,
  `figures/` (16 PNGs + generator), `metadata/` (5 files, includes the single-source-of-truth
  `computed_metrics.json`), `reports/` (3 analysis docs), `tables/` (35 files).
- `final_comparison/` (34 files) — `FINAL_BASELINE_COMPARISON.md`, `RUN_COMPARISON.md`,
  `comparison_config.json`, `cases/` (7 case files + index), `figures/` (11 PNGs),
  `scripts/` (`build_comparison_data.py`, `generate_figures.py`), `tables/` (9 CSV/MD files).

**Worth reading despite being archived**: `final_comparison/FINAL_BASELINE_COMPARISON.md`
is the single deepest, most complete original-vs-current research narrative in this
project — a controlled configuration A/B with real case studies and an honest
counter-signal (an assumption-gold disagreement) — richer than any single STEP 8/11
document in `evaluation/`. It is archived here (not promoted) because it is a dated
presentation narrative rather than reusable tooling, but it remains a primary source
worth consulting directly, not just a superseded draft.

## What still cites paths inside this archive

Live navigation docs in `research/prototype/evaluation/` (e.g. `README.md`,
`inputs/README.md`, `figures/README.md`, `comparisons/README.md`,
`metrics/CONSOLIDATION_SOURCE_MAP.md`) were updated in PASS 3B to point here. A handful
of frozen STEP 7/9/13 historical records (e.g. `ablation/ABLATION_EVIDENCE_GRADES.md`,
`metrics/STATISTICAL_RESULTS.md`, `figures/FIGURE_CLAIM_AUDIT.md`,
`reports/FINAL_RELEASE_AUDIT.md`) still cite the pre-archive path (`final_comparison/...`,
`final_demo_pack/...`) unchanged — those are frozen, point-in-time audit narratives
describing what was true when they were written, not live indexes, and were deliberately
left as-is per the same convention applied throughout this cleanup (see
`../../evaluation/archive/cleanup_history/README.md` for the precedent). The file is
still exactly where this note says: `archive/2026-08-27_presentation/final_comparison/...`
and `archive/2026-08-27_presentation/final_demo_pack/...` respectively.
