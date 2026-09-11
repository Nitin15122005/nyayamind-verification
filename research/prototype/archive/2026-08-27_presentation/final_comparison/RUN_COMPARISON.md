# RUN_COMPARISON — Reproducing the ORIGINAL vs CURRENT Comparison

This document is the reproduction guide for everything under `research/prototype/final_comparison/`.
It assumes you have already read `research/prototype/REPRODUCIBILITY.md` (the project-wide
reproducibility reference) — this file covers only what is specific to this comparison.

**Nothing in this comparison requires a new GPU run.** Every table and figure here is
computed from experiment artifacts already committed under `research/prototype/outputs/`
before this comparison was built — see §5 ("Is a new GPU run needed?") for the honest
answer on whether one would still be worthwhile.

---

## 1. Environment

Same as the project-wide environment (`research/prototype/REPRODUCIBILITY.md` §1):
Python 3.11.9, `research/.venv`. This comparison's own scripts additionally require
`matplotlib` (already pinned in `research/requirements.txt`) — no other new dependency.
No GPU, no network, no model weights are loaded by anything in this directory.

## 2. Exact commands

All commands assume the repo root as the working directory.

```bash
# 1. Recompute every CSV table directly from research/prototype/outputs/*
research/.venv/Scripts/python.exe research/prototype/final_comparison/scripts/build_comparison_data.py

# 2. Regenerate every PNG figure from the tables just written
research/.venv/Scripts/python.exe research/prototype/final_comparison/scripts/generate_figures.py
```

Both scripts are idempotent and side-effect-free outside `final_comparison/tables/` and
`final_comparison/figures/` respectively — they never write to `research/prototype/outputs/`
or to `config/prototype.yaml`, and they load no model.

Expected runtime: a few seconds total (CPU, no model loading — pure JSON/CSV/plotting).

## 3. What each script reads

| Script | Reads (relative to `research/prototype/outputs/`) |
|---|---|
| `build_comparison_data.py` | `final_gpu_validation_{A,B}.jsonl`, `final_gpu_validation_metrics.json`, `final_gpu_validation_corrections_detail.jsonl`, `final_validation_bare_vs_labeled_cpu_metrics.json`, `labeled_correction_validation_gpu_metrics.json`, `controlled_benchmark_deberta{,_labeled}_{metrics.json,results.jsonl}`, `evidence_coverage_v0_vs_v1.json`, `parser_fix_before_after_n30.json`, `atomic_scope_check_final_replay.json`, `final_metrics.json` |
| `generate_figures.py` | every CSV under `final_comparison/tables/` (written by the script above) plus `final_gpu_validation_{A,B}.jsonl` and `final_metrics.json` directly, for the confidence-distribution and cumulative-natural-data figures |

Neither script hand-types any metric value — every number in every table/figure traces to
one of the files above. See `comparison_config.json` for the full source-file manifest per
comparison pair.

## 4. Reproducing the full project test suite and MVP check (as instructed)

```bash
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check
```

Both were run as part of producing this comparison; results are reported verbatim in
`FINAL_BASELINE_COMPARISON.md` and were not used to justify any threshold or methodology
change.

## 5. Is a new GPU run genuinely necessary?

**Not to reproduce anything in this comparison** — every figure/table here is a
recomputation of already-committed, already-GPU-validated experiment data (or, for the
controlled benchmark and CPU re-verification pairs, already-committed CPU-only DeBERTa
results). Re-running `run_final_gpu_validation.py` or `run_labeled_correction_validation_gpu.py`
would produce a *fresh* batch of natural cases, not a re-check of these numbers — useful for
extending the evidence base, not for verifying it.

**What a new GPU run WOULD genuinely add** (see `FINAL_BASELINE_COMPARISON.md` for the full
discussion): a larger (50-100 case), fresh natural batch run under the full CURRENT config
end-to-end from scratch (not chained across four separate experiments as this comparison's
strongest evidence currently is) would let the n=1-shipped/n=10-triggered correction result
be confirmed or revised at a defensible sample size, and would let all four CURRENT levers
be measured jointly for the first time on genuinely new cases with real generation. This is
recorded in `FINAL_PRODUCTION_CONFIG.md` §8 as the condition that would justify revisiting
the `premise_framing` decision, not a gap this comparison itself needed to close.

## 6. If you want to extend this comparison with a fresh batch

```bash
# Select a new, disjoint natural batch (CPU-only, no GPU)
research/.venv/Scripts/python.exe research/prototype/scripts/select_natural_candidates.py --out-suffix _comparison_extension

# Run it end-to-end under CURRENT config (GPU, ~15-35 min depending on batch size)
research/.venv/Scripts/python.exe research/prototype/scripts/run_final_gpu_validation.py --device cuda
```

Then re-run `build_comparison_data.py` after adding the new output file(s) to the relevant
section of that script — this comparison's scripts are not written to auto-discover new
batches, by design, so that every number here stays traceable to an explicit, reviewed
source-file list.

## Addendum — 2026-09-09

`build_comparison_data.py` and `generate_figures.py` (in `scripts/`) each computed
`PROTOTYPE` (the `research/prototype/` root, used to find `outputs/`) via
`FINAL_COMPARISON.parent`, which was correct when this directory lived at
`research/prototype/final_comparison/` but resolved one level short — to
`research/prototype/archive/2026-08-27_presentation/`, which has no `outputs/`
— after the 2026-08-27 freeze/reorg archived this whole directory one level
deeper. Fixed in place this pass (`PROTOTYPE = FINAL_COMPARISON.parent.parent.parent`).
Re-ran both scripts after the fix: every table and figure reproduced
byte-for-byte identical to the committed versions (confirming this was a
path bug, not a data change), except `tables/comparison_summary.md`, whose
trailing "Project Author Statement" pointer (hand-appended after an earlier
build, not written by the script itself) was restored after regeneration.

Four commits since 2026-08-27 add new findings not reflected in this
comparison's tables/figures (none touched the `outputs/*` files these
scripts read, so no existing number changed): `adf54aa` (adversarial safety
hardening — 5 gaps fixed), `6347c45` (BM25/embedding retrieval evaluated and
rejected, Jaccard stays default), `c250a0e` (Art./Arts. parser fix, +7
claims), and `bb2cd93` (`verification.narrow_primary_hypothesis` extended to
primary verification, default flipped `true` — see
`FINAL_BASELINE_COMPARISON.md`'s own addendum for why this specifically
matters to that report's Limitations section). See
`research/prototype/archive/2026-08-27_presentation/final_demo_pack/README.md`'s
addendum for full detail and source-report pointers on all four.

## 7. Seeds, models, versions (unchanged from the project-wide record)

| | Value |
|---|---|
| Seed | 42 |
| Generation model | `Qwen/Qwen2.5-7B-Instruct`, 4-bit NF4, greedy |
| Verification model | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` |
| ORIGINAL config | `use_evidence_v1=false, premise_framing=bare, atomic_scope_check=false, narrow_reverification_hypothesis=false` |
| CURRENT config | `use_evidence_v1=true, premise_framing=labeled, atomic_scope_check=assertion_spans, narrow_reverification_hypothesis=true` |
| Full definitions | `comparison_config.json` (this directory) |

## 8. Expected artifacts after running both scripts

```
final_comparison/
├── comparison_config.json          (hand-authored, not regenerated by scripts)
├── RUN_COMPARISON.md               (this file)
├── FINAL_BASELINE_COMPARISON.md    (hand-authored narrative report)
├── scripts/
│   ├── build_comparison_data.py
│   └── generate_figures.py
├── tables/
│   ├── comparison_summary.csv / .md
│   ├── ablation_results.csv
│   ├── safety_results.csv
│   ├── correction_results.csv
│   ├── retrieval_results.csv
│   ├── efficiency_results.csv
│   ├── verdict_distribution_results.csv
│   ├── premise_framing_controlled_benchmark_results.csv
│   └── statistical_tests.csv
├── figures/
│   └── 01..11_*.png
└── cases/
    ├── CASES_INDEX.md
    └── case_01..07_*.md
```

## 9. Addendum — 2026-09-11 (post-freeze research completion pass)

Four commits landed on top of the frozen ORIGINAL/CURRENT comparison above
since 2026-08-27: `adf54aa` (safety hardening), `6347c45` (BM25/embedding
retrieval evaluated, REJECTED), `c250a0e` (Art./Arts. parser fix, +7
claims), `bb2cd93` (`narrow_primary_hypothesis`, production default since).
This pass added a fifth evaluated lever and attempted a large fresh
correction-shipping batch:

- **`verification.assertion_span_primary_hypothesis`** (new, OFF by
  default): extends `narrow_primary_hypothesis` to "respectively" claims.
  CPU-benchmarked against the entire real population of such claims found
  in this project's history (n=6) — 4/6 changed verdict, 0 unsafe
  reversals, every case manually verified genuine. **Not adopted as
  default**: n=6 is too small for a production decision, reported as
  inconclusive rather than rounded up. See
  `FINAL_PRODUCTION_CONFIG.md` §5a and
  `outputs/assertion_spans_primary_hypothesis_benchmark_report.md`.
- **Large fresh GPU batch (target n=100, fallback to 50/30) — BLOCKED**:
  three consecutive attempts all failed during model loading due to a
  verified host memory constraint (15.7GB total RAM, ~5.3-5.5GB free,
  insufficient for loading Qwen2.5-7B-Instruct in 4-bit), independent of
  requested batch size. Not a code defect — see
  `outputs/gpu_experiment_memory_constraint.md` for the full diagnostic.
  The prior session's n=15 batch remains the only fresh GPU data for the
  `narrow_primary_hypothesis` lever; correction-shipping impact at a
  statistically meaningful scale remains genuinely unmeasured.

No table/figure in this directory was regenerated this pass — the source
data (`outputs/final_metrics.json` and friends) is unchanged by either of
the above (the new lever is off by default; the blocked batch produced no
new committed data), so regeneration would reproduce byte-for-byte
identical output, as already verified for the 2026-09-09 pass.
