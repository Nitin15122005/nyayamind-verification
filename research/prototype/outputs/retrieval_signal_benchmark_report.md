# Retrieval Signal Benchmark: Jaccard vs BM25 vs Embedding
Evidence pool: 136 records, 22 unique acts.
Pre-registered cases: 21 should-match, 9 should-NOT-match (safety) -- written from the corpus's real act names before running any method.

## jaccard
- Correct-accept rate: 19/21 (90.5%)
- Correct-reject (safety) rate: 9/9 (100.0%)
- Zero wrong-accepts. Safety intact.

## bm25
- Correct-accept rate: 21/21 (100.0%)
- Correct-reject (safety) rate: 3/9 (33.3%)
- **WRONG-ACCEPT (safety failure) cases:**
  - 'Code of Civil Procedure' incorrectly matched to 'code of criminal procedure 1973' (score 0.5894, threshold 0.5)
  - 'Code of Criminal Procedure' incorrectly matched to 'code of civil procedure 1908' (score 0.5894, threshold 0.5)
  - 'Civil Procedure Code' incorrectly matched to 'code of criminal procedure 1973' (score 0.5894, threshold 0.5)
  - 'Arbitration and Conciliation Act, 1996' incorrectly matched to 'arbitration act 1940' (score 1.0, threshold 0.5)
  - 'Income Tax Act' incorrectly matched to 'income tax rules 1962' (score 0.6125, threshold 0.5)
  - 'Income Tax Rules' incorrectly matched to 'income tax act 1961' (score 1.0, threshold 0.5)

  Threshold sweep (is there a fully-safe operating point?):

  | threshold | correct-accept | correct-reject (safety) |
  |---|---|---|
  | 0.5 | 21/21 | 3/9 <- production default |
  | 0.55 | 21/21 | 3/9 |
  | 0.6 | 20/21 | 6/9 |
  | 0.65 | 20/21 | 7/9 |
  | 0.7 | 19/21 | 7/9 |
  | 0.75 | 19/21 | 7/9 |
  | 0.8 | 19/21 | 7/9 |
  | 0.85 | 19/21 | 7/9 |
  | 0.9 | 19/21 | 7/9 |
  | 0.95 | 19/21 | 7/9 |
  | 1.0 | 19/21 | 7/9 |

## embedding
- Correct-accept rate: 21/21 (100.0%)
- Correct-reject (safety) rate: 2/9 (22.2%)
- **WRONG-ACCEPT (safety failure) cases:**
  - 'Code of Civil Procedure' incorrectly matched to 'code of criminal procedure 1973' (score 0.6353, threshold 0.55)
  - 'Code of Criminal Procedure' incorrectly matched to 'code of civil procedure 1908' (score 0.6353, threshold 0.55)
  - 'Civil Procedure Code' incorrectly matched to 'code of criminal procedure 1973' (score 0.6514, threshold 0.55)
  - 'Arbitration Act, 1940' incorrectly matched to 'arbitration and conciliation act 1996' (score 0.7562, threshold 0.55)
  - 'Arbitration and Conciliation Act, 1996' incorrectly matched to 'arbitration act 1940' (score 0.7562, threshold 0.55)
  - 'Income Tax Act' incorrectly matched to 'income tax rules 1962' (score 0.665, threshold 0.55)
  - 'Income Tax Rules' incorrectly matched to 'income tax act 1961' (score 0.637, threshold 0.55)

  Threshold sweep (is there a fully-safe operating point?):

  | threshold | correct-accept | correct-reject (safety) |
  |---|---|---|
  | 0.5 | 21/21 | 2/9 |
  | 0.55 | 21/21 | 2/9 <- production default |
  | 0.6 | 21/21 | 2/9 |
  | 0.65 | 20/21 | 5/9 |
  | 0.7 | 20/21 | 7/9 |
  | 0.75 | 20/21 | 7/9 |
  | 0.8 | 16/21 | 9/9 |
  | 0.85 | 12/21 | 9/9 |
  | 0.9 | 5/21 | 9/9 |
  | 0.95 | 4/21 | 9/9 |
  | 1.0 | 4/21 | 9/9 |

## Verdict

Jaccard (production default) is the ONLY method achieving 100% correct-reject (zero wrong-Act matches) among the operating points tested, while also having the highest correct-accept rate of any method at full safety (compare jaccard's 90.5% correct-accept @ 100% safety against embedding's best fully-safe point, ~76% correct-accept @ threshold=0.8 @ 100% safety, and bm25, which never reaches 100% safety at any threshold swept). Both bm25 and embedding are, at this corpus size (22 unique Acts), measurably WORSE than jaccard on the safety axis that matters most for this system: they under-penalize a query missing an Act's single distinguishing word (bm25's term-frequency weighting) or actively reward true topical/semantic similarity between LEGALLY DISTINCT enactments (embedding -- e.g. 'Arbitration Act, 1940' vs 'Arbitration and Conciliation Act, 1996' score 0.76 cosine similarity, which is semantically accurate and legally wrong). CONCLUSION: fuzzy_method remains 'jaccard' in production (config/prototype.yaml). bm25/embedding are retained as evaluated, available, OFF-by-default options (src/retrieval_signals.py) for future corpora where this measured trade-off might differ -- not adopted here.
