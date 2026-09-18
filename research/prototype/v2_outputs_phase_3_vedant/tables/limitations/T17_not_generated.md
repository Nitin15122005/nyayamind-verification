# T17_not_generated

Everything the brief asked for that this package does not contain. No placeholder figure or stub table was created for any of these.

| requested item | status | reason | what exists instead |
|---|---|---|---|
| End-to-end ORIGINAL codebase run | NOT EXECUTED | Generation and correction are Qwen-dependent; no GPU and model uncached | The deterministic front half WAS re-executed from git (T08) |
| Correction funnel / outcomes / safety, fresh | RERUN_INFEASIBLE | Qwen-dependent | Historical artifacts reused and labelled HISTORICAL |
| BM25 / embedding retrieval comparison, fresh | RERUN_INFEASIBLE | rank_bm25 and sentence_transformers not installed; MiniLM not cached | Historical result reused; also unreachable from production (D1) |
| Joint four/five-lever ablation | NOT EXECUTED | Does not exist in the project; requires end-to-end Qwen runs | Single-lever results reported instead, explicitly labelled |
| Runtime / resource comparison figure | DELIBERATELY NOT PRODUCED | Historical numbers are GPU; fresh ones are CPU under a different major version - not comparable | figures/09_runtime/README.md explains; raw timings kept in the metric JSONs |
| Natural-data accuracy / F1 / confusion matrix | NOT PRODUCED - WOULD BE INVALID | No gold labels exist for any natural batch | Natural data is reported only as coverage, distribution and behaviour |
| Lawyer-validated evaluation | DOES NOT EXIST | Never performed in this project | None |
| Formal 15-category red-team evaluation | DOES NOT EXIST | Never performed | None |
| Pre-0e37525 system state | UNRECOVERABLE | 0e37525 is the sole root commit and is a squashed import | None |
| Model revision SHAs | UNDETERMINED | No from_pretrained() call pins a revision | None |

## Notes

- Full narrative version: NOT_GENERATED_REGISTER.md
