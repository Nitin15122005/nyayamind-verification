# Art./Arts. Citation-Abbreviation Fix: Real-Data Impact Audit

Both parser versions loaded fresh via `git show` / the current working tree and run in-memory on the exact same 181 unique real generated texts (deduplicated across every outputs/*.jsonl `generated_field.text`) -- OLD = commit 6347c45 (immediately before this fix), NEW = current. This isolates ONLY this fix's effect, unlike diffing against each record's stored `claims` field (which reflects whatever parser version existed when that experiment originally ran, months of unrelated bugfixes ago in some cases).

- Total claims (OLD parser): 795
- Total claims (NEW/fixed parser, same texts): 802
- Net claims recovered: 7
- OLD claims with a matched evidence record: 531
- NEW claims with a matched evidence record: 532

## Cases where claim count changed (2 / 181)

| doc_id | source_file | old | new | delta | old w/ evidence | new w/ evidence |
|---|---|---|---|---|---|---|
| 1972_232 | final_gpu_validation_A.jsonl | 0 | 1 | +1 | 0 | 1 |
| 1983_178 | natural_candidates_50_gpu_bare.jsonl | 0 | 6 | +6 | 0 | 0 |

No claim count ever decreased between the two parser versions on any of these 181 real texts -- this fix is strictly additive/corrective on every real generated paragraph this project has produced to date.
