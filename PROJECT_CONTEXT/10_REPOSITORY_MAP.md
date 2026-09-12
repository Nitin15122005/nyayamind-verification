# Repository Map

For the detailed, dated, file-by-file inventory of `research/prototype/` as of 2026-09-06 (and
the original 2026-08-27 structure it supersedes), see `REPOSITORY_MANIFEST.md` (repo root) —
this file is a live, higher-level map that also covers what has been added since (`results_phase3/`,
the newest `outputs/` files, `PROJECT_CONTEXT/` itself).

```
nyayamind-verification/                    repo root
│
├── PROJECT_CONTEXT/                        <- YOU ARE HERE. Read 01_PROJECT_BRAIN.md first.
│
├── README.md                               General project overview, setup, Docker, HF_TOKEN.
│                                            May be stale on specific numbers (e.g. evidence
│                                            pool size) relative to PROJECT_CONTEXT — trust
│                                            PROJECT_CONTEXT + config/prototype.yaml over this
│                                            file for current production values.
├── FINAL_PRODUCTION_CONFIG.md              Decision record for every production config lever.
│                                            LIVE document — appended to, never rewritten.
│                                            DO NOT casually edit; append dated updates only.
├── FINAL_RESEARCH_FREEZE_REPORT.md         Full research-freeze narrative across every
│                                            session. LIVE document, same append convention.
├── REPOSITORY_MANIFEST.md                  Dated structural inventory (2026-08-27, updated
│                                            2026-09-06). DO NOT edit; append dated updates only.
├── Dockerfile, docker-compose.yml          Docker build (currently ENVIRONMENT-BLOCKED to test
│                                            on the development machine — daemon not running).
│
├── baseline/LegalSeg/                      Git SUBMODULE — the RhetoricLLaMA baseline.
│                                            NEVER touch this. Shows as "modified" in git status
│                                            as pre-existing, expected, untracked submodule
│                                            content — not something to fix or investigate.
│
└── research/
    ├── requirements.txt                    Pinned dependencies — several pins are load-bearing
    │                                        compatibility constraints, not arbitrary.
    ├── baseline/                           Frozen RhetoricLLaMA reproduction (BASELINE.md,
    │                                        README.md). Different task/dataset from NyayaMind
    │                                        proper — never a quantitative comparison target.
    ├── data/
    │   ├── evidence/                       Canonical statute corpus, v0 + v1 (both required,
    │   │                                    additive). DO NOT MODIFY — treat as frozen research
    │   │                                    data unless given an explicit, evidence-based reason.
    │   └── nyayarag/CaseText_Statutes/      Source case data (NyayaRAG). Read-only.
    │
    └── prototype/                          The actual pipeline project.
        ├── README.md, REPRODUCIBILITY.md   Source-adjacent docs, updated incrementally —
        │                                    generally current but check dates/content against
        │                                    PROJECT_CONTEXT for anything very recent.
        ├── config/prototype.yaml           THE production config. Authoritative for "what is
        │                                    production right now" — check this, not a doc,
        │                                    when in doubt.
        ├── src/                            9 modules, the pipeline itself. PRODUCTION SOURCE —
        │                                    modify only with clear intent and test coverage.
        ├── tests/                          302 tests (grows over time). DO NOT disable a test
        │                                    to make a change pass.
        ├── scripts/                        Every reproduction/experiment/results-package-build
        │                                    entry point. Read-only against src/config/data —
        │                                    scripts write to outputs/ or results_phase3/ only.
        ├── outputs/                        100+ files — the experimental lab notebook. DO NOT
        │                                    delete or silently alter; new experiments get new
        │                                    files, historical files get dated APPENDED updates
        │                                    if something changes, never rewritten in place.
        ├── evaluation/                     Pre-2026-09-06 presentation/evaluation workspace —
        │                                    the source data the (now archived) Output_phase_3_
        │                                    vedant package was built from. Read-only historical
        │                                    source; not the current canonical results package.
        ├── archive/
        │   ├── 2026-08-27_presentation/    Frozen 2026-08-27 presentation snapshot.
        │   └── 2026-09-06_output_phase_3_vedant/
        │                                    The PRIOR Phase-3 results package, archived
        │                                    2026-09-12 when results_phase3/ superseded it.
        │                                    Preserved intact — do not resurrect it as "the"
        │                                    results package.
        └── results_phase3/                 THE CURRENT, AUTHORITATIVE results package.
                                             README.md inside it is the entry point for anyone
                                             wanting figures/tables/diagrams/claims/limitations.
                                             Built by research/prototype/scripts/build_results_
                                             phase3_*.py — regenerate via those scripts, never
                                             hand-edit a generated figure/table.
```

## Rules for this map

- **`PROJECT_CONTEXT/`** is new global context, not a replacement for any of the above — it
  summarizes and links.
- **`results_phase3/`** is the one authoritative results package. Do not create
  `results_phase3_v2`, `results_phase4`, or any parallel results directory — improve
  `results_phase3/` in place (as was done for its F16 ablation figure).
- **Never move `FINAL_PRODUCTION_CONFIG.md` or `FINAL_RESEARCH_FREEZE_REPORT.md`** out of the
  repo root without a deliberate, separately-approved reorganization — they are live decision
  records referenced by path from many other files (tests, docstrings, other reports).
- **Historical/archived material is never deleted** — only ever appended-to (if still live) or
  moved into an `archive/` directory with a dated name (if genuinely superseded), following the
  convention already established by `archive/2026-08-27_presentation/` and
  `archive/2026-09-06_output_phase_3_vedant/`.
