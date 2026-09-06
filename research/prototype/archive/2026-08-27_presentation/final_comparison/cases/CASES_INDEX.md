# Case-Level Evidence — Index

Seven real system outputs, one per requested category (per this comparison's own task
brief). Every field below is copied verbatim from committed raw JSONL/JSON artifacts under
`research/prototype/outputs/` — extraction commands are given in each case file so any
reader can re-pull the exact record. **No case here has been reviewed by a lawyer.** Read
every verdict as "what the automated system did," never as "what the law actually says."

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

These are not a random sample and not a rate estimate — see `../tables/*.csv` for the
actual population-level counts each category is drawn from. Selection criterion for each
case is stated in its own file header, before the outcome, to keep selection auditable.

| # | Category | Case | File |
|---|---|---|---|
| 1 | Genuine improvement (bare misses, labeled catches ENTAILED) | `2002_731`/c4 | `case_01_genuine_improvement.md` |
| 2 | Genuine detection missed by ORIGINAL, caught by CURRENT | `2006_1150`/c12 | `case_02_detection_missed_by_original.md` |
| 3 | Retrieval improvement (v0 NO_EVIDENCE -> v0+v1 matched) | `2000_1266`/c1 | `case_03_retrieval_improvement.md` |
| 4 | Correction improvement (shipped, safe, substantively correct) | `2003_760`/c3 | `case_04_correction_improvement.md` |
| 5 | Safe rejection of an unsafe/out-of-scope correction | `2006_770`/c1 | `case_05_safe_rejection.md` |
| 6 | Both systems behave identically | `2006_770`/c2 | `case_06_identical_behavior.md` |
| 7 | Important remaining failure (claim bundling defeats correction) | `2004_1020`/c6 | `case_07_remaining_failure.md` |

All seven are drawn from the paired `final_gpu_validation` 50-case batch (Arms A/B) plus
its two direct follow-on experiments (`final_validation_bare_vs_labeled_cpu`,
`labeled_correction_validation_gpu`) — the single most tightly controlled, most-recent,
largest real-natural-data chain in this project, so that ORIGINAL and CURRENT outputs for
each case come from the same underlying case and the same generation pass wherever
possible.
