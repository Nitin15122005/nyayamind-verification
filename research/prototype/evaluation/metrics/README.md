# Evaluation

## Scope, and the boundary with `comparisons/` and `ablation/`

`evaluation/` is where a dataset-level evaluation is **run and its raw output/metrics are
computed and stored**. `comparisons/` is where results already computed here or in
`research/prototype/outputs/` are organized and narrated side-by-side for presentation
(currently: `comparisons/expected_vs_actual/`, the gold-vs-actual comparison — see that
directory's own README). `ablation/` is specifically single-variable sweeps/replays.

**PASS 1 correction (2026-09-05)**: this file previously described evaluation work as
"planned, none executed in this step," with a table of hypothetical output subdirectories
(`evaluation/controlled_benchmark/`, `evaluation/synthetic_stress/`, etc.) that were never
built. That was accurate for STEP 1/3, when this file was first written, but the
evaluation work described below **was subsequently run** (STEP 4-8) and its output landed
as flat files directly under this directory, not under the planned per-evaluation
subdirectories. This rewrite describes what is actually here now. The 7 `ABLATION_*`
files that used to live here were moved to `../ablation/` in this same cleanup pass, to
reunite them with that directory's own README.

## What is actually here

| File(s) | What it is |
|---|---|
| `CANONICAL_METRICS.json` / `.csv` | The master, cross-component metrics rollup — the single reconciled source for every headline number cited elsewhere in this workspace |
| `COMPONENT_TEST_MATRIX.csv` | Machine-readable counterpart of `../components/COMPONENT_TEST_SUMMARY.md` |
| `CONSOLIDATED_CONSISTENCY_REPORT.md` | STEP 8's mechanical reconciliation of 26 headline values against their source artifacts (real check, not narrative) |
| `CONSOLIDATION_SOURCE_MAP.md` | Traces every consolidated number back to the exact STEP/script/file that produced it |
| `archive/` | **PASS 2 (2026-09-06)**: 5 STEP-8 files moved here — `CONSOLIDATED_EXECUTIVE_SUMMARY.md`, `CONSOLIDATED_FACULTY_SUMMARY.md`, `HEADLINE_RESULTS.md`, `REPRODUCIBILITY_MATRIX.md`, `ORIGINAL_VS_CURRENT.md`/`.csv` — each superseded in currency by a `reports/FACULTY_*` document; see `archive/README.md` for the exact mapping |
| `CORRECTION_FUNNEL.md` / `.csv` | Correction-attempt funnel (triggered → scope-checked → re-verified → shipped), synthetic and natural populations kept as separate rows |
| `EVIDENCE_STRENGTH_MATRIX.md` / `.csv` | Grades the strength of evidence behind each headline claim across components (claim parser, evidence retrieval, verifier, ablation levers) |
| `GPU_CORRECTION_SAFETY_STEP10.md`, `GPU_EXECUTION_INVENTORY.md`, `GPU_LIMITATIONS.md`, `GPU_REPRODUCTION_CROSSCHECK.md` | STEP 10/10B's GPU-hardware reproduction findings — see also `../ablation/GPU_ABLATION_UPDATE.md` |
| `HISTORICAL_CROSSCHECK_NATURAL.md`, `NATURAL_DATA_INVENTORY.md`, `NATURAL_DATA_METRICS.csv`, `NATURAL_DATA_REPORT.md` | The 588-claim aggregate and natural-batch evaluation (evidence coverage, NO_EVIDENCE taxonomy) |
| `METRIC_DEFINITIONS.md` | Glossary of every metric name used across this workspace, so a term is defined once, not per-report |
| `paired_209_analysis.csv`, `PAIRED_209_REPORT.md` | The 209-claim paired (McNemar) evidence-coverage comparison |
| `SAFETY_SUMMARY.md` / `.csv` | Safety-net outcome counts (sibling-regression rejections, scope-violation catches) across the project's history |
| `STATISTICAL_RESULTS.md` / `.csv` | Statistical tests computed against GOLD-01 (premise-framing McNemar/sign tests) and the 209-claim paired set (evidence-coverage McNemar test) |
| `figure_data/` | 11 CSVs, one per canonical figure in `../figures/`, each row traced to a source metric |
| `input_integrity/` | `hash_report.json` + `validation_log.txt` — hash-verification record for the GOLD fixtures and evidence corpus |

## Environment gap affecting fresh re-runs

`research/.venv/` **does not exist in this checkout** (verified 2026-09-05) — only a
system Python 3.14 install is present, newer than this project's pinned
Python 3.11.9 / torch==2.2.2+cu121 / transformers==4.40.2 stack, with no guarantee of
compatibility. Any command that assumes `research/.venv/Scripts/python.exe` requires
creating that venv first:
```
python -m venv research/.venv
research/.venv/Scripts/python.exe -m pip install -r research/requirements.txt
```
This is a real, currently-unaddressed reproducibility gap — see `../PROVENANCE.md`.

## Reproduction scripts

The evaluation runs summarized above were produced by (all in `../`, run from
`research/.venv/Scripts/python.exe`): `run_gold01_evaluation.py`,
`run_gold02_evaluation.py`, `run_natural_588_evaluation.py`,
`run_natural_209_paired_evaluation.py`, `analyze_natural_batches.py`,
`verify_natural_input_integrity.py`, `build_gold_benchmark_tables.py`,
`build_ablation_analysis.py`, `build_metrics_consolidation.py`. Each is a
re-runnable reproduction tool, not one-shot scratch — see `../components/README.md`'s
"Known reproducibility gap" note before running any of them.
