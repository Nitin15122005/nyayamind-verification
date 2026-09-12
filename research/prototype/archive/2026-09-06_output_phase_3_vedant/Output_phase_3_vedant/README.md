# Output_phase_3_vedant — mentor / PPT visualisation package

Generated 2026-09-06 against repository commit `b83bb6b30cf4c548d60e1c9dea23186ab0e52a68`.

A self-contained, fully traceable comparison of this project's **baseline** and **modified**
system configurations, built for faculty review. It contains **25 metric figures**,
**14 system diagrams**, **9 tables** and **26 locked metric contracts**, each
rendered twice (publication density and 16:9 presentation).

---

## The two systems, named exactly

| | Baseline | Modified |
|---|---|---|
| **Name** | NyayaMind v0 (pre-2026-08-27 baseline) | NyayaMind (2026-08-27 production) |
| **Generation model** | `Qwen/Qwen2.5-7B-Instruct` (4-bit nf4, greedy) | `Qwen/Qwen2.5-7B-Instruct` (4-bit nf4, greedy) |
| **Verification model** | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` |
| **Correction model** | `Qwen/Qwen2.5-7B-Instruct` (reuses the generator) | `Qwen/Qwen2.5-7B-Instruct` (reuses the generator) |
| **`premise_framing`** | `bare` | `labeled` |
| **`use_evidence_v1`** | `false` — 59 usable records | `true` — 136 usable records |
| **`correction.atomic_scope_check`** | `false` (full-sentence rule) | `"assertion_spans"` |
| **`correction.narrow_reverification_hypothesis`** | `false` | `true` |
| **`verification.confidence_threshold`** | `0.70` | `0.70` (unchanged) |

Both systems execute the **identical pipeline code** in `research/prototype/src/`. This is a
configuration A/B on one project, not a comparison against an external system.

**Where these definitions come from:** the modified column is read live from
`research/prototype/config/prototype.yaml`; the baseline column from
`research/prototype/archive/2026-08-27_presentation/final_comparison/comparison_config.json`
(`"ORIGINAL"`), which the repository's own regression test
`tests/test_premise_framing_production.py::test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`
pins as still reproducible byte-for-byte.

### What is NOT the baseline

The **RhetoricLLaMA / LegalSeg** reproduction (`meta-llama/Llama-2-7b-chat-hf` +
`L-NLProc/LegalSeg_RhetoricLLaMA`) is a *different task* — sentence-level rhetorical-role classification —
on a different dataset, and only a one-row smoke test was ever executed. No quantitative
comparison against it is made anywhere in this package. See
`diagrams/D14_reference_baseline_rhetoricllama_out_of_scope.png` and
`NOT_GENERATED_REGISTER.md`.

---

## Directory layout

```
Output_phase_3_vedant/
├── README.md                      this file
├── FIGURE_DATA_AUDIT.md           per-figure number-by-number audit trail
├── METRIC_SOURCE_MAP.csv          every locked metric contract and its source artifact
├── VISUALIZATION_MANIFEST.csv     every figure / diagram / table with full metadata
├── NOT_GENERATED_REGISTER.md      visuals deliberately withheld, and why
├── metrics/                       26 locked figure-data CSVs (the only input to the figures)
├── figures/                       25 metric figures, publication density
├── diagrams/                      14 system and flow diagrams
├── tables/                        9 tables, CSV + Markdown
├── ppt_assets/
│   ├── figures/                   16:9 variants of every figure
│   ├── diagrams/                  16:9 variants of every diagram
│   ├── FIGURE_INDEX.md
│   ├── DIAGRAM_INDEX.md
│   └── SLIDE_MAPPING.md           suggested 25-slide faculty presentation order
├── validation/                    QC reports, including the pytest log
└── scripts/                       the five build scripts (read-only against the repository)
```

## How traceability is enforced

1. `scripts/build_metric_tables.py` reads the committed experiment artifacts and writes one
   locked CSV per metric contract into `metrics/`. Every row carries a `source_artifact` column.
2. `scripts/generate_figures.py` opens **only** those CSVs — never a source artifact — so a
   number that is not in a locked contract cannot reach a figure.
3. `scripts/build_tables.py` builds every table from the same locked CSVs.
4. `scripts/validate_package.py` re-reads the source artifacts and re-checks each contract value,
   then checks naming, file coverage and the prohibited-claim rules.

Rebuild the whole package with:

```
python scripts/build_metric_tables.py
python scripts/generate_figures.py
python scripts/generate_diagrams.py
python scripts/build_tables.py
python scripts/build_docs.py
python scripts/validate_package.py
```

## What this package does NOT do

- It runs **no experiments** and **no GPU work**. Every GPU-dependent value is a committed
  historical result or the evaluation workspace's own STEP 10 / 10B reproduction, labelled as such.
- It **modifies nothing** outside this directory. `src/`, `tests/`, `config/`, `research/data/`,
  `research/prototype/outputs/` and `research/prototype/evaluation/` are read-only inputs.
- It makes **no legal-correctness claim**. No lawyer ground truth exists anywhere in this
  project, and every natural-data figure states that explicitly.

## Reading rules for every number in here

| Class | Meaning |
|---|---|
| **GOLD** | Real per-item labels exist, so accuracy / precision / recall / F1 are legitimate (GOLD-01, GOLD-02 only). |
| **METRIC-ONLY** | Natural NyayaRAG data with no correctness label. Descriptive and paired-comparative statements only — never accuracy. |
| **BEHAVIOUR** | A software invariant asserted by a test. Says nothing about accuracy. |
| **HISTORICAL** | Cited from a committed prior-session artifact; not re-executed here. |
| **FRESH** | Re-executed or re-derived in the evaluation workspace or in this package. |

Evidence grades A–E follow `evaluation/metrics/EVIDENCE_STRENGTH_MATRIX.csv` and communicate how
well a finding is evidenced (isolation, sample size, statistical support) — **not** effect size.

## Validation status

| Check | Result |
|---|---|
| `scripts/validate_package.py` (27 value re-verifications + coverage, naming, claim and protected-path checks) | **PASS** — 0 failures, 0 warnings (`validation/VALIDATION_REPORT.txt`) |
| `pytest research/prototype/tests/ -q` | **205 passed** (`validation/pytest_research_prototype_tests.txt`) |
| `research/prototype/scripts/run_mvp.py --check` | **All checks passed**, 136 usable evidence records (`validation/run_mvp_check.txt`) |
| 10 existing repository validators under `evaluation/scripts/` | 7 PASS; 3 FAIL on one **pre-existing Windows line-ending artifact**, diagnosed in `validation/EXTERNAL_VALIDATOR_NOTES.md` |
| `git status --porcelain` | one entry only: `?? research/prototype/Output_phase_3_vedant/` — no tracked file modified |

The three external-validator failures are all the same two GOLD fixture files, whose hard-coded
SHA-256 constants are the LF-blob hashes while this checkout materialises them with CRLF
(`core.autocrlf = true`). After CRLF→LF normalisation both hashes match the constants exactly, so
no content differs. Nothing was changed to make a validator pass — see
`validation/EXTERNAL_VALIDATOR_NOTES.md` for the full diagnosis.

## Start here

- One slide that answers "what changed?" → `diagrams/D03_baseline_vs_modified_side_by_side.png`
- One figure that answers "did it help?" → `figures/F01_headline_baseline_vs_modified.png`
- The honest limits → `NOT_GENERATED_REGISTER.md`
- The presentation plan → `ppt_assets/SLIDE_MAPPING.md`
