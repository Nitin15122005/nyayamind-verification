# Final Atomic-Claim Scope-Check Replay — all real scope violations, both GPU batches

_No GPU, no new Qwen call. Replays every real `correction_scope_violation` from
both natural GPU experiments through the fully-extended mechanism (semicolon /
while / citation-keyword-boundary / parenthetical-gloss / respectively spans)._

**1/11 real scope violations unblocked** by the finished
atomic-claim mechanism.

| batch | document | target | citation | legacy | final | outcome |
|---|---|---|---|---|---|---|
| batch1 | `2009_865` | c2 | Section 324 | True | True | still blocked |
| batch1 | `2020_51` | c4 | Section 406 | True | True | still blocked |
| batch1 | `1978_196` | c4 | Section 324 | True | True | still blocked |
| batch1 | `2003_924` | c5 | Section 482 | True | True | still blocked |
| batch1 | `2009_431` | c2 | Section 324 | True | True | still blocked |
| batch1 | `1991_110` | c2 | Section 149 | True | True | still blocked |
| batch2 | `2022_435` | c3 | Section 148 | True | True | still blocked |
| batch2 | `2022_435` | c3 | Section 148 | True | True | still blocked |
| batch2 | `2024_300` | c2 | Section 506 | True | True | still blocked |
| batch2 | `2024_300` | c2 | Section 506 | True | True | still blocked |
| batch2 | `1997_1306` | c6 | Section 148 | True | False | **UNBLOCKED** |
