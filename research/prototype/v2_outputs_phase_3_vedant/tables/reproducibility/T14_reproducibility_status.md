# T14_reproducibility_status

What was reproduced fresh, what was reused, and what could not be rerun.

| metric / experiment | V2 status | environment used | outcome |
|---|---|---|---|
| Verifier accuracy / macro F1 (GOLD-01, n=420) | REPRODUCED FRESH | Python 3.13.1 / torch 2.13.0+cpu / transformers 5.15.1, CPU | EXACT match to the historical run on a different stack |
| Verifier per-class + confusion matrices | REPRODUCED FRESH | same | EXACT match |
| GOLD-01 condition stratification | NEW ANALYSIS (no prior artifact) | derived from fresh predictions | n/a - did not previously exist |
| Contradiction recall (GOLD-02, n=59) | REPRODUCED FRESH | same | EXACT match (0.3559 / 0.4576) |
| GOLD-02 2x2 factorial | NEW ANALYSIS | same | n/a - did not previously exist |
| Parser ORIGINAL arm (38/88) | REPRODUCED FRESH | CPU, no model | EXACT match to 0e37525:outputs/eval_30_report.md |
| Parser LATEST arm (57/93) | REPRODUCED FRESH | CPU, no model | EXACT match to parser_fix_before_after_n30_v2_postfix.json |
| Parser INTERMEDIATE arm (54) | DISCREPANCY | CPU, no model | artifact at that commit records 51; unresolved (P-1). No conclusion depends on it. |
| Evidence pool composition | REPRODUCED FRESH | CPU, no model | 59/136 confirmed; config's own arithmetic corrected |
| Threshold sensitivity | REPRODUCED FRESH | recomputed from stored softmax | consistent with the historical sweep |
| Evidence coverage (n=209) | REUSED HISTORICAL | originally GPU | RERUN_INFEASIBLE - Qwen-dependent generation |
| Correction funnel (n=56) | REUSED HISTORICAL | originally GPU | RERUN_INFEASIBLE - no GPU, Qwen uncached |
| Assertion-aware correction (n=10) | REUSED HISTORICAL | originally GPU | RERUN_INFEASIBLE - Qwen-dependent |
| narrow_primary GPU batch (n=62) | REUSED HISTORICAL | originally GPU | RERUN_INFEASIBLE - Qwen-dependent |
| Retrieval method safety (BM25/embedding) | REUSED HISTORICAL | CPU | RERUN_INFEASIBLE - rank_bm25 and sentence_transformers not installed; MiniLM not cached |
| Test suite | RE-RUN THIS SESSION | Python 3.13.1, CPU | 290 passed, 1 skipped (= a 12-test file skipped via importorskip rank_bm25). 290+12=302, reconciling the documented figure. |

## Notes

- Cross-stack exact reproduction of the GOLD-01 and GOLD-02 numbers is itself a reproducibility finding: the historical results survive a major torch/transformers version change.
- Inference is greedy argmax over a softmax - no sampling - so no inference seed exists and the deterministic runs are exactly repeatable.
