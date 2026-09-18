# T08_parser_metrics

Three-arm parser + evidence-matcher progression, re-executed fresh from git over the same 30 documents of already-generated text, with the evidence pool held at v0 in every arm.

| arm | claims extracted | claims resolving to evidence | proportion resolved | exact matches | fuzzy matches | no evidence |
|---|---|---|---|---|---|---|
| ORIGINAL (0e37525) | 88 | 38 | 0.4318 | 24 | 14 | 50 |
| INTERMEDIATE (223eb9d) | 93 | 54 | 0.5806 | 52 | 2 | 39 |
| LATEST (HEAD fb4e98f) | 93 | 57 | 0.6129 | 55 | 2 | 36 |

## Notes

- Sign tests (per-document paired): ORIGINAL->LATEST +10/-0, p=0.0020; ORIGINAL->INTERMEDIATE +7/-0, p=0.0156; INTERMEDIATE->LATEST +3/-0, p=0.2500 (NOT SIGNIFICANT).
- The safety-relevant movement is fuzzy -> exact (14 -> 2 fuzzy; 24 -> 55 exact): fewer matches rest on a token-overlap heuristic.
- 'Resolving to evidence' is a coverage outcome, NOT a correctness label - no gold claim-extraction annotation exists anywhere in this project.
- Re-executing the COMMITTED 223eb9d parser source over the same 30 texts yields 54 claims resolving to evidence, where the artifact committed at that same commit records 51. Component isolation rules out the matcher and loader: holding the parser at 223eb9d and swapping the evidence_matcher/data_loader between 223eb9d and HEAD gives 54 either way, and holding the parser at HEAD gives 57 either way — so the entire 54->57 movement is parser-side and the matcher changes are inert on this data. The counting rule is also identical (claims whose evidence_id is not None). The most likely explanation is that the artifact was generated from a working tree whose parser differed slightly from the source finally committed at 223eb9d. Recorded, not resolved.
