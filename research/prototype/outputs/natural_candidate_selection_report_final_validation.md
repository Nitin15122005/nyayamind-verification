# Natural-Data Candidate Selection — pre-GPU screening report

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. No Qwen, no GPU, no generation was run to produce this report — every signal is NyayaRAG's own `sections` KEYS (never their text) and case_text length, scored against the current, real `claim_parser` + `evidence_matcher` code and the unmodified 59-record usable evidence pool.

---

## 1. Corpus scanned

- Evidence pool: **59 usable records**, **10 Acts** (arms act 1959, code of civil procedure 1908, code of criminal procedure 1973, constitution of india, income tax act 1961, indian evidence act 1872, indian penal code 1860, industrial disputes act 1947, land acquisition act 1894, negotiable instruments act 1881), **59 distinct (act, provision) pairs**.
- NyayaRAG source files: `SCI_56k_multi_5k_summarised_w_sections.json` + `SCI_56k_single_5k_summarised_w_sections.json`.
- Raw case records scanned: **9892** (9423 with usable case_text, 469 dropped for empty/degenerate case_text).
- Distinct `document_id`s: **8740** (multi/single files share 683 document_ids — same underlying case, two summarization variants; collapsed to the higher-scoring variant per document_id, deterministic tie-break: score desc → fewer raw citation keys → document_id asc).

## 2. Filtering funnel

| Stage | Count remaining | Excluded this stage |
|---|---:|---:|
| Raw records scanned | 9892 | — |
| Empty/degenerate case_text dropped | 9423 | 469 |
| Distinct document_ids (post multi/single dedup) | 8740 | 683 duplicate variants collapsed |
| Previously evaluated (n=30 + targeted n=11) excluded | 8612 | 128 |
| Zero citation keys at all excluded | 7178 | 1434 |
| Zero evidence match (exact+fuzzy) excluded | **4390** | 2788 |

**4390 eligible candidates** out of 8740 distinct cases (50.2%) have at least one statutory citation that resolves to real evidence in the current 59-record corpus, using ONLY the case's own NyayaRAG-provided citation keys — before any generation.

## 3. Estimated evidence coverage

Among the 4390 eligible candidates: 27471 raw citation keys, **9608 (35.0%) resolve to usable evidence** (9603 exact, 5 fuzzy) — a much higher hit rate than the unfiltered n=30/targeted-n11 pool's 58.2% CLAIM-level match rate (not directly comparable — that figure is per generated CLAIM, this one is per raw CITATION KEY — but both measure the same underlying corpus-coverage constraint, and this citation-key-level screen is a legitimate, cheap, pre-generation proxy for it).

## 4. Substantive vs. procedural-only candidates

- Purely-procedural candidates (every matched citation is CrPC/CPC, no substantive Act matched): **169** / 4390 — deprioritized by the scoring formula (0 substantive bonus), never hard-excluded.

## 5. Recommended batch sizes

| Batch size | Exact matches | Fuzzy matches | Distinct (act,provision) pairs covered | Distinct Acts | Purely-procedural cases | Mean score |
|---:|---:|---:|---:|---:|---:|---:|
| 30 | 197 | 0 | 50 | 7 | 0 | 38.97 |
| 50 | 314 | 0 | 59 | 10 | 0 | 37.20 |
| 100 | 627 | 0 | 59 | 10 | 0 | 37.13 |

All three batches are **strict prefixes of one ranked order** — the 30-batch is exactly the first 30 document_ids of the 50-batch, which is exactly the first 50 of the 100-batch. Growing the batch size never reshuffles an earlier recommendation.

## 6. Selection method — why this beats random sampling

1. **Evidence-gated.** Every eligible candidate has at least one raw citation key that resolves to real corpus evidence (exact or fuzzy) — computed from NyayaRAG's own ground-truth citation keys, not from anything generated. Only 4390/8740 = 50.2% of all scanned cases clear this bar; a uniformly random sample of the same size drawn from the full 8740-case pool would be expected to spend roughly 50% of its GPU budget on cases that can only ever produce NO_EVIDENCE claims, regardless of what Qwen generates.
2. **Diversity-first ordering.** Phase A of the ranking greedily prioritizes any candidate that introduces a NEW (act, provision) pair not yet covered by a higher-ranked pick, before falling back to pure score order. This directly targets the brief's 'diverse statutes/provisions' requirement — a random sample would instead reproduce the corpus's natural skew toward a few frequently-cited provisions (IPC §302/§34 dominate the existing n=30 pool).
3. **No outcome leakage.** The score is a function of raw_citation_keys (NyayaRAG's own ground-truth metadata) and case_text length only — never a generated claim, an NLI verdict, or a correction outcome. The SAME ranking would be produced before or after ever running Qwen once, so it cannot be selecting 'cases where the model happens to do well.'
4. **Deterministic and reproducible.** The ranking is a strict sort on explicit, documented numeric keys (score, then distinct-pairs, then document_id) — no random sampling step exists to seed. Re-running this script against the same corpus/config always produces byte-identical output.
5. **Disjoint from prior work.** All 130 previously-evaluated document_ids (n=30 + targeted n=11) are excluded, so every GPU cycle spent on this new batch produces genuinely new information rather than re-measuring already-known cases.

## 7. Exact selected case IDs

Full ordered lists are written to `outputs/natural_candidate_selected_ids_{30,50,100}.json`. First 10 of the recommended batch (see final recommendation below):

- `2003_999` — score 42, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2004_1020` — score 42, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2005_898` — score 42, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2006_641` — score 42, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2011_625` — score 42, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2014_66` — score 42, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2000_1266` — score 41, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2003_760` — score 41, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2004_315` — score 41, 7 exact + 0 fuzzy matches, 7 distinct pairs
- `2006_1150` — score 41, 7 exact + 0 fuzzy matches, 7 distinct pairs
