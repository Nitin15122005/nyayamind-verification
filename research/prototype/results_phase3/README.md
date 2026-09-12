# NyayaMind — Phase-3 Final Results Package

**The single authoritative results package for this project.** Everything scientifically
relevant about NyayaMind's evaluation — verifier accuracy, evidence retrieval, parser fixes,
correction and safety behavior, ablations, natural-data observations, and the newest
assertion-span/assertion-aware-correction work — lives here, in one place.

Generated 2026-09-12. Supersedes the archived
`research/prototype/archive/2026-09-06_output_phase_3_vedant/Output_phase_3_vedant/` package
(generated 2026-09-06), which is preserved as historical record, not deleted — this package
reuses its already-validated figures/tables/diagrams verbatim wherever nothing has changed,
and adds every result produced since (narrow_primary_hypothesis, retrieval BM25/embedding
evaluation, assertion-span verification, the n=62 fresh correction batch, assertion-aware
correction, and the assertion_spans architecture completion).

## The two systems, named exactly

| | Baseline | Modified NyayaMind |
|---|---|---|
| **Name** | NyayaMind v0 (pre-2026-08-27 baseline) | NyayaMind (current production, 2026-09-12) |
| **Generation model** | `Qwen/Qwen2.5-7B-Instruct` (4-bit NF4, greedy) | unchanged |
| **Verification model** | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | unchanged |
| **Correction model** | `Qwen/Qwen2.5-7B-Instruct` (reuses the generator) | unchanged |
| `premise_framing` | `bare` | `labeled` |
| `use_evidence_v1` | `false` (59 records) | `true` (136 records) |
| `correction.atomic_scope_check` | `false` | `"assertion_spans"` |
| `correction.narrow_reverification_hypothesis` | `false` | `true` |
| `verification.narrow_primary_hypothesis` | `false` | `true` |
| `verification.assertion_span_primary_hypothesis` | `false` | `false` (evaluated, not promoted) |
| `correction.assertion_aware` | `false` | `false` (evaluated, not promoted) |

Both systems execute the **identical pipeline code** in `research/prototype/src/`. This is a
configuration comparison on one project, not a comparison against an external system. See
`tables/headline_results/T07_model_and_configuration_comparison.md` for the complete list.

## Navigation

| I want... | Go to |
|---|---|
| The headline numbers | `tables/headline_results/headline_results.md` |
| The full scientific narrative | `FINAL_RESULTS.md` |
| What we can/cannot claim | `RESEARCH_CLAIMS.md` |
| Known limitations | `LIMITATIONS.md` |
| Verifier accuracy/precision/recall/F1/confusion matrices | `figures/02_verifier/`, `tables/detailed_metrics/verifier*.csv` |
| Evidence coverage and retrieval | `figures/03_evidence_retrieval/`, `tables/detailed_metrics/evidence*.csv`, `retrieval_metrics.csv` |
| Parser results | `figures/04_parser/`, `tables/detailed_metrics/parser_metrics.csv` |
| Correction funnel and outcomes | `figures/05_correction/`, `tables/correction_safety/correction_funnel.csv` |
| Safety results | `figures/06_safety/`, `tables/correction_safety/safety_results.csv` |
| Ablations (every lever ever evaluated) | `figures/07_ablation/`, `tables/ablation/ablation_results.md` |
| Natural-data observations | `figures/08_natural_data/` |
| Architecture / pipeline diagrams | `diagrams/` |
| Component-by-component comparison | `tables/component_results/component_comparison.md` |
| PPT / slide guidance | `ppt/SLIDE_GUIDE.md` |
| Where a number came from | `sources/RESULT_INDEX.csv`, `sources/SOURCE_MAP.csv` |

## Directory layout

```
results_phase3/
├── README.md                      this file
├── FINAL_RESULTS.md               the complete scientific results narrative
├── RESEARCH_CLAIMS.md             every paper-facing claim, classified
├── LIMITATIONS.md                 what this project does NOT show
├── figures/                       30 metric figures (25 reused + 5 new), 8 topic folders
├── diagrams/                      15 system/flow diagrams (14 reused + 1 new), 5 topic folders
├── tables/                        headline / detailed_metrics / component_results / ablation / correction_safety
├── ppt/                           FIGURE_INDEX.md, DIAGRAM_INDEX.md, SLIDE_GUIDE.md (reference canonical files, no copies)
└── sources/                       RESULT_INDEX.csv, SOURCE_MAP.csv — full traceability
```

## What can we claim?

- NyayaMind is a **research-grade, end-to-end implemented, reproducible research prototype**,
  experimentally evaluated across parser, retrieval, verifier, correction, and safety
  components, with both controlled-benchmark and natural-data evidence.
- Every promoted production lever (`use_evidence_v1`, `premise_framing=labeled`,
  `atomic_scope_check=assertion_spans`, `narrow_reverification_hypothesis`,
  `narrow_primary_hypothesis`, the claim-parser Art./Arts. fix) has real, sourced evidence —
  see `RESEARCH_CLAIMS.md`.
- Two mechanisms were built, tested, and evaluated but **honestly NOT promoted** because the
  evidence didn't support it: `assertion_span_primary_hypothesis` (n=6, too small) and
  `correction.assertion_aware` (0/10 shipped, no improvement over legacy on this real batch).
  Both are reported as real results, not hidden.

## What can we NOT claim?

- **No lawyer-validated ground truth exists anywhere in this project.** Natural-data figures
  report evidence coverage, verdict distributions, and paired outcome shifts — never
  "accuracy," "precision," or "recall," which require labels this project does not have.
- **No legal-correctness guarantee.** The NLI verifier is a small public model's statistical
  confidence, not a legal-correctness oracle.
- **No production certification and no claim of universal generalization.** This is a
  research prototype, evaluated on a bounded evidence pool and a bounded set of NyayaRAG
  cases.
- Docker validation is **ENVIRONMENT-BLOCKED** on this machine (daemon not running) — not
  claimed to have passed.

## Visual QC and duplication check (done as part of building this package)

Every figure/diagram produced or copied into this package was visually inspected; two real
layout issues (a legend overlapping a bar-top label, and a diagram edge label overlapping a
box) were found and fixed before this package was finalized — see `FINAL_RESULTS.md` §Visual
QC for the full account. A duplication pass confirmed no figure/table/diagram exists in more
than one canonical location in this package; the PPT directory contains only index documents
that reference these canonical files, never copies.
