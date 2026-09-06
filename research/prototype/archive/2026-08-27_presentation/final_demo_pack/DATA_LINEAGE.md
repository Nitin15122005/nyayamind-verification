# Data Lineage

Every number in this pack traces back through exactly one intermediate layer to a
frozen, committed raw artifact. This document draws that chain explicitly so a
reviewer can verify any figure or table without re-deriving it from scratch.

```
research/prototype/outputs/*.jsonl, *.json     (frozen, committed, never modified)
research/data/evidence/*.jsonl                  (frozen, committed, never modified)
                    |
                    |  read by
                    v
research/prototype/final_demo_pack/metadata/compute_metrics.py
                    |
                    |  writes
                    v
research/prototype/final_demo_pack/metadata/computed_metrics.json   <-- SINGLE SOURCE OF TRUTH
                    |
        +-----------+-----------+-----------+
        |           |           |           |
        v           v           v           v
   figures/     tables/    reports/    EXECUTIVE_SUMMARY.md
   *.png    *_raw.csv/.md  *_analysis.md   SYSTEM_STATUS.md
                                            METRICS_TABLE.md
```

`examples/` follows a parallel, independent chain (it does not go through
`computed_metrics.json` — exemplar cases are individual records, not aggregate
statistics):

```
research/prototype/outputs/*.jsonl (per-claim/per-case records)
                    |
                    v
research/prototype/final_demo_pack/examples/find_candidates.py
                    |
                    v
examples/candidate_pool.json  -->  examples/build_cases_json.py  -->  examples/cases.json
                    |                                                        |
                    +--------------------- both feed --------------------->  |
                                                                              v
                                                          examples/case_01..08_*.md (hand-written prose)
```

`live_demo/run_demo.py` is independent of both chains above — it imports
`research/prototype/src/*` directly and calls the real production code
(claim extraction, evidence matching, real DeBERTa verification, the real
scope-violation gate function) against real stored generated text, rather than
reading any pre-computed statistic.

## Section-by-section source map

| computed_metrics.json section | Directly sourced from | Computation performed |
|---|---|---|
| `final_metrics_passthrough` | `outputs/final_metrics.json` | None — verbatim pass-through of an already-computed, already-cross-checked artifact |
| `evidence_coverage_v0_v1` | `outputs/evidence_coverage_v0_vs_v1.json` | None — verbatim pass-through |
| `threshold_sensitivity` | `outputs/threshold_sensitivity_analysis.json` | None — verbatim pass-through |
| `controlled_benchmark_verifier` | `outputs/controlled_benchmark_deberta_metrics.json`, `..._labeled_metrics.json` | None — verbatim pass-through |
| `assumption_gold_provisional` | `outputs/assumption_gold_bare_vs_labeled_metrics.json` | None — verbatim pass-through, `defensible: false` added |
| `evidence_corpus_composition` | `research/data/evidence/{canonical_statutes,canonical_statutes_v1,evidence_audit,evidence_audit_v1}.jsonl` | Fresh: act/provision/source/provenance/audit-verdict counting, replicating `src/data_loader.py`'s own v0+v1 merge rule |
| `correction_safety_audit` | `outputs/run_C_n30.jsonl`, `outputs/natural_candidates_{50,batch2}_gpu_corrections_detail.jsonl`, `outputs/final_gpu_validation_{A,B}.jsonl`, `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl`, `outputs/framing_comparison_gpu_n59_postfix_metrics.json` | Fresh: every correction-attempt record parsed and status-counted directly; cross-checked against `final_metrics_passthrough`'s cumulative counts (see `cross_checks`) |
| `confidence_distributions` | `outputs/run_B_n30.jsonl`, `outputs/natural_candidates_*_gpu_{bare,labeled}.jsonl`, `outputs/final_gpu_validation_A.jsonl` | Fresh: mean/median/stdev/histogram over each claim's stored `confidence` field |
| `funnel` | `final_metrics_passthrough` values | Arithmetic derivation only |
| `timeline` | git commit history + artifact dates | Hand-verified static list |
| `cross_checks` | `final_metrics_passthrough` vs. `correction_safety_audit` | Equality assertions, run every time `compute_metrics.py` runs |

## How to verify any single number

1. Open `metadata/computed_metrics.json` and find the field.
2. Check that section's `source_files` array.
3. Open the named file directly under `research/prototype/outputs/` or
   `research/data/evidence/` — every one is frozen, committed, human-readable
   JSON/JSONL.
4. For the handful of freshly-computed sections (`evidence_corpus_composition`,
   `correction_safety_audit`, `confidence_distributions`), read the
   corresponding function in `metadata/compute_metrics.py` — the computation is
   a few lines of counting/aggregation, not a black box.

No number in this pack was hand-typed without this chain existing first.
