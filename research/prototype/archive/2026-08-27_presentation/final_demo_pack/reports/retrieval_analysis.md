# Retrieval Analysis — Evidence Matching and Coverage

Source: `research/prototype/final_demo_pack/metadata/computed_metrics.json` sections `evidence_coverage_v0_v1`, `evidence_corpus_composition`, `final_metrics_passthrough.section_C_parser_retrieval`. Raw backing files cited inline.

## The central distinction: "no evidence in our corpus" ≠ "legally unsupported"

**This is the single most important limitation in the whole system, and it must never be conflated.** A claim resolving to `NO_EVIDENCE` means only that the claim's citation was not found in this project's ~136-record evidence corpus (`research/data/evidence/`) — a corpus covering, by design, only the top ~143 most-frequently-cited provisions in the NyayaRAG source corpus. It says **nothing** about whether the underlying legal claim is true, false, or supported by law generally. Most citations in an arbitrary real case simply fall outside this project's deliberately narrow, frequency-ranked coverage. Treating `NO_EVIDENCE` as "the claim is wrong" would be a serious misreading of the system's output — the pipeline itself never makes that inference (`NO_EVIDENCE` claims are never flagged for correction).

## v0 vs. v1 coverage

| | v0 only | v0 + v1 | Change |
|---|---:|---:|---:|
| Usable evidence records | 59 | 136 | +77 |
| Paired-arm coverage (209 claims, 50 held-out cases, same generation) | 63.2% (132 matched) | 70.3% (147 matched) | **+7.1pp** |
| Statistical test | — | McNemar chi2=13.07, **p≈0.0003** | 0 regressions (no claim that matched under v0 lost its match under v0+v1) |
| Independent claim-level check (588 claims, multiple batches) | 60.2% (354 matched) | 66.3% (390 matched, +36 newly covered) | Consistent direction with the paired-arm result |

**Source:** `research/prototype/outputs/final_gpu_validation.md` §2 (paired design), `research/prototype/outputs/evidence_coverage_v0_vs_v1.json` (independent check). This is the only comparison in the project with a computed significance test — do not infer significance for any other coverage number in this pack.

## Remaining NO_EVIDENCE after v0+v1 (198 of 588 claims in the independent check; 260 of 797 in the full retrieval eval)

| Bucket | Count (retrieval eval, 797 claims) | Meaning |
|---|---:|---|
| `genuinely_absent_no_such_provision_any_act` | 140 (53.8%) | Real corpus-coverage gap — provision genuinely not in the corpus |
| `genuinely_absent_wrong_act_or_edition` | 78 (30.0%) | Correctly declined — the citation names a different Act than any in the corpus |
| `unresolved_act` | 40 (15.4%) | Correctly declined to guess — ambiguous act field |
| `parser_or_matcher_defect_candidate` | 2 (0.8%) | Both manually reviewed and **confirmed NOT bugs** |

**Zero confirmed parser or evidence-matcher defects across 797 real claims** spanning this project's entire natural-data history. Full detail, including 15 adversarial regression tests (wrong-Act, same-number/different-act, year/edition, aliases, ranges, multi-Act, ambiguous citations) added to lock this behavior: `research/prototype/outputs/evidence_v1_independent_audit.md`, `research/prototype/tests/test_adversarial_citations.py`. One confirmed latent limitation exists and is not currently triggered in any committed result: **fuzzy matching is year-blind** (it does not distinguish, e.g., different editions of an Act with the same section number).

## Act / provision diversity (evidence corpus composition)

| | v0 (63 records) | v1 supplement (82 records) | Combined (142 raw, 136 usable) |
|---|---:|---:|---:|
| Distinct Acts | 11 | 20 | 22 |
| Provision types | Section 47, Article 16 | Section 67, Article 12, Rule 3 | Section 111, Article 28, Rule 3 |
| Top Act by record count | IPC 1860 (21) | IPC 1860 (22) | IPC 1860 (42) |
| 2nd | Constitution of India (16) | Constitution of India (12) | Constitution of India (28) |

**Source distribution: 100% IndianKanoon.org, both v0 and v1.** India Code (`indiacode.nic.in`), the official Ministry of Law and Justice repository, returned HTTP 403 on every access attempt across this project's history (root, section pages, repealed-acts listing, a static PDF) — this is documented as a consistent environmental finding, not a one-off failure. IndianKanoon is explicitly labeled `authority_level: "third_party_verified"` in every record, never presented as official India Code text.

**Text provenance:** v0 is mostly `websearch_synthesized_summary` (59/63 records — search-aggregated, URL-pinned, not independently re-fetched at build time); v1 is mostly `webfetch_verbatim` (78/82 — a direct fetch, stronger provenance). A 2026-08-27 independent audit re-fetched 50% of v1's records directly (up from the original build's 10%) and found zero fabricated or wrong-provision content; two narrow defects were found and fixed in place (see `research/data/evidence/README_v1.md`).

## What "retrieval precision" actually means here

The only measurable proxy is the **match-method ratio**: `exact_normalized` matches dominate `fuzzy` matches by roughly 60:1 to 80:1 in every natural batch (e.g. final validation Arm B: 145 exact vs 2 fuzzy). This indicates the higher-risk fuzzy path is rarely exercised, which is weak positive evidence that matches are not spuriously wrong — but it is **a proxy, not a precision score**.

**Not measurable with current data:** a true retrieval false-match rate (fraction of matches that are wrong) would require an independently-labeled ground truth set of "is this the correct provision for this claim" judgments, which does not exist in this project. The closest available evidence is the manual inspection of every CONTRADICTED verdict reported in `research/prototype/outputs/final_gpu_validation.md` §3, which is qualitative, not a computed rate.

## Known unresolved categories (documented, not fixed)

- 37 of the original top-100 v0 candidate citations were never attempted (search/lookup budget exhausted) — see `research/data/evidence/README.md` "Unresolved cases."
- 4 v0 citations were attempted but dropped because an exact IndianKanoon document URL could not be individually confirmed.
- Coverage is capped at the top ~143 citation keys by frequency, not the full ~8,100 distinct citations in the underlying NyayaRAG statute data, by design/task scope.

## Addendum — 2026-09-09

Two statements above are superseded by work done since 2026-08-27 (numbers
above are otherwise still accurate as the 2026-08-27 snapshot):

- **"Fuzzy matching is year-blind" (line above, "Known unresolved
  categories") is now fixed**, not just documented — commit `adf54aa` added a
  veto in `evidence_matcher.py` that rejects a fuzzy match when the claim and
  candidate state explicit, disjoint years.
- **"Zero confirmed parser or evidence-matcher defects across 797 real
  claims" is no longer the complete picture.** Commit `c250a0e` found and
  fixed a real parser defect: Art./Arts. citation abbreviations were not
  resolved correctly. Isolated by running both parser versions in-memory on
  the same 181 unique real generated texts (not diffing against
  each experiment's own stored `claims`, which mixes parser versions across
  months): **7 claims recovered net (795 → 802)**, strictly additive/corrective
  on every real text — no claim count ever decreased. 2 of 181 texts were
  affected. Full detail:
  `research/prototype/outputs/article_abbreviation_fix_impact_report.md`.

**Also new**: commit `6347c45` evaluated BM25 and embedding as alternative
`fuzzy_method` retrieval signals and **rejected both** — at this corpus's
scale (22 unique Acts), Jaccard is the only method tested that reaches 100%
correct-reject on a 9-case safety set (BM25 and embedding both wrongly match
legally-distinct Acts at their production-default thresholds, e.g. "Code of
Civil Procedure" ↔ "Code of Criminal Procedure"), while also achieving the
highest correct-accept rate of any method at full safety. Jaccard remains
the production default. Full detail:
`research/prototype/outputs/retrieval_signal_benchmark_report.md`.
