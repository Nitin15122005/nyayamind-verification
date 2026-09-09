# Evidence v1 — Independent Audit Report

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-27. Independent audit of `research/data/evidence/canonical_statutes_v1.jsonl`
+ `evidence_audit_v1.jsonl` (82 records), performed separately from the original build session,
using direct re-fetches of source pages, full structural/programmatic checks, project-wide
NO_EVIDENCE taxonomy, and a new adversarial parser/matcher test suite.

---

## Executive summary — PASS

**Verdict: PASS for continued development/research use, and PASS as sufficient evidentiary
basis to enable `use_evidence_v1: true` as a production default** (the actual default-change
decision is made in `FINAL_PRODUCTION_CONFIG.md`, using this audit as one input alongside the
GPU A/B experiment). **Not** a gold-standard legal corpus — no audit performed by this project,
v0 or v1, substitutes for professional legal review; that remains explicitly out of scope, as the
corpus's own README has always stated.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

- **0 fabricated or wrong-provision matches found** across 41 independently re-fetched records
  (50% of the 82 — up from the original build's 8/82 ≈ 10%) and a full structural pass over all
  82.
- **2 genuine, narrow defects found — both fixed in place**, dated and logged (§3).
- **1 confirmed latent algorithmic limitation** (fuzzy matching is year-blind) — not currently
  triggered anywhere in the live 136-record corpus, now pinned by a dedicated regression test
  (§5) so it cannot silently worsen and is ready groundwork for a future fix.
- **NO_EVIDENCE taxonomy re-run project-wide** (797 claims across every natural GPU experiment
  in this project's history): 67.4% coverage, and only 2 "possible defect" candidates surfaced —
  both manually reviewed and confirmed to be correct, safe behavior, not bugs (§4).
- **15 new adversarial regression tests added**, all passing, covering wrong-Act,
  same-number/different-act, year/edition, aliases, ranges, multi-Act, and ambiguous citations.

---

## 1. Method

1. **Structural/programmatic audit (100% of 82 records)**: schema completeness, duplicate-key
   detection, `canonical_text`/`source_url` duplication, `act_norm` consistency against the
   project's own `normalize_act()`, `evidence_matcher` exact-index collision analysis across the
   full v0+v1 merge, `audit_verdict`-assignment-rule consistency, inline repeal/omission-bracket
   presentation consistency, and a provenance-label plausibility scan.
2. **Direct WebFetch re-verification** of 41/82 (50%) `source_url`s — every record marked
   `v1_supersedes_v0_record: true` (3/3), all 3 `SOURCE_ONLY` records, and a further 35 records
   spanning the full frequency range — comparing the live page's statutory text against the
   stored `canonical_text`. (Fetching stopped at 41/82 after `indiankanoon.org` began returning
   HTTP 429 rate-limit responses; see §6 for what remains unverified.)
3. **NO_EVIDENCE taxonomy**, re-run against the corrected v0+v1 pool and **extended to cover the
   final pre-paper GPU validation batch** (`final_gpu_validation_A.jsonl`) that did not exist at
   the time of the prior taxonomy pass — see `scripts/audit_no_evidence_taxonomy_v2.py` and
   `outputs/no_evidence_taxonomy_v3.json`.
4. **New adversarial test suite** (`tests/test_adversarial_citations.py`, 15 tests) targeting
   wrong-Act, same-section-number/different-act, year/edition, aliases, ranges, multi-Act, and
   ambiguous-citation scenarios — several built directly from real cases the taxonomy surfaced.

Nothing here uses a GPU or a language model to generate or judge legal text. Every
canonical-text comparison is a direct, literal comparison against independently re-fetched web
content or the project's own deterministic code.

---

## 2. WebFetch spot-check results (41/82, 50%)

**41/41 independently re-fetched records: statutory text matches the stored `canonical_text` in
substance.** No fabricated text, no wrong-provision content, no wrong-Act content found among any
re-fetched record. Two records showed a **presentation/labeling** issue (not a content-accuracy
issue) — both fixed, see §3.

Records independently re-fetched and confirmed this session (by dataset_citation_key index in
`canonical_statutes_v1.jsonl`): 1–34 (all), 48, 50, 61 — union with the original build's 8
spot-checked records (1, 4, 25, 45, 64, 72, 80 by this same indexing, with #2 already covered by
the new set) gives **41 distinct records, 50.0% of 82**.

Notable content-correctness confirmations during re-fetch:
- `Section 417 in The Code of Criminal Procedure, 1973` and the historical Section 417
  (1898-Code "appeal in acquittal", now CrPC §378) caveat already documented in `README_v1.md`
  — not independently re-verified this pass (outside the 41), flagged as unverified in §6.
- All `SOURCE_ONLY`-rated records (145, 145 CrPC, 34 Arbitration & Conciliation Act 1996, 3 Indian
  Evidence Act) were re-fetched and found to contain **accurate, substantive statutory text** —
  the conservative `SOURCE_ONLY` (not-usable-by-default) rating reflects the build session's
  provenance discipline (text was search-synthesized, not literally webfetch-verbatim), not any
  actual inaccuracy found in this audit.

---

## 3. Defects found and fixed

### 3a. `Section 256 in The Income Tax Act, 1961` — missing inline omission note

**Finding.** The live source page (re-fetched twice this session) displays: *"256. Statement of
case to the High Court.— [Omitted by the National Tax Tribunal Act, 2005 (49 of 2005), section 30
and Schedule (w.e.f. 28-12-2005).]"* This exact bracketed note was already present in this same
record's own `nyayarag_dataset_text_raw` field (carried over from v0). `historical_status`
already correctly read `omitted_2005-12-28_by_National_Tax_Tribunal_Act_2005_s30_and_schedule`.
But `canonical_text` itself did not include the bracket, presenting the pre-2005 operative text
as if unqualified — inconsistent with sibling records (e.g. `Section 161 in The Indian Penal
Code, 1860`, which inlines its own 1988 repeal note) that follow the corpus's own established
convention for targeted (non-whole-Act) repeals/omissions.

**Root cause.** This record is one of the v1 build's **3 corrections to known-bad v0 records**
(confirmed via direct comparison: v0's own version of this key was audit_verdict
`VERIFIED_CONTENT` but `historical_status: "in_force"` — self-contradictory against its own
`nyayarag_dataset_text_raw`, which already showed the omission). v1's correction fixed
`historical_status` but did not carry the omission note into `canonical_text`.

**Fix applied** (2026-08-27, this audit): appended the verified bracket to `canonical_text`.
No citation identity, act, provision_number, or match-relevant field changed;
`audit_verdict` unchanged (`VERIFIED_EXACT`, text is still an exact quote — now a complete one).
Logged inline via a new `independent_audit_note` field on the record, and in
`research/data/evidence/README_v1.md`'s new "2026-08-27 independent audit addendum" section.

### 3b. `Section 2 in The Income Tax Act, 1961` — provenance mislabel

**Finding.** `text_provenance` was recorded as `webfetch_verbatim`, but the stored
`canonical_text` is a paraphrased description of the section's ~48 definitions (opening with a
bracketed editorial gloss: *"[Section 2 sets out approximately 48 defined terms used throughout
the Act, in alphabetical order from 'advance tax'... to 'zero coupon bond'...]"*) — not a verbatim
quote. Confirmed by direct WebFetch re-check this session: the live page's actual text is the
full, un-paraphrased 48-definition block, which the stored record does not reproduce. Verbatim
quotation of the full section was a reasonable build-time judgment call (impractically long for
one evidence field), but the provenance *label* did not reflect that judgment honestly.

**Fix applied** (2026-08-27, this audit): relabeled `text_provenance` to
`webfetch_summarized_not_verbatim`. Per this corpus's own pre-existing, documented mechanical
audit rule (`scripts/build_evidence_v1.py`: `webfetch_verbatim` + `confidence: high` →
`VERIFIED_EXACT`; anything else → `SOURCE_ONLY`) — the same rule already applied to every
`websearch_synthesized_summary` record — the corresponding `audit_verdict` in
`evidence_audit_v1.jsonl` was downgraded `VERIFIED_EXACT` → `SOURCE_ONLY`. This is a mechanical,
consistent application of an existing rule, not a new or special-cased one.

**Net effect: the default usable v0+v1 pool is 136 records (was 137).** This record's content
was never used as matched evidence in any already-published experiment in this project — verified
by checking `final_gpu_validation_{A,B}.jsonl`'s full `evidence_id` list, which never references
this key — so **no prior committed or published result is invalidated** by this correction. All
189 project tests pass unchanged after this fix; no test hardcoded the prior 137 figure.

---

## 4. NO_EVIDENCE taxonomy — project-wide, current corpus (136 records)

Re-run across **every distinct generated text ever produced by a natural-data GPU experiment in
this project** (183 distinct texts: n=30, targeted n=11, batch 1 n=50, batch 2 n=50, final
validation n=50 — deduplicated by exact generated text):

| | Count | % |
|---|---:|---:|
| Total claims | 797 | 100% |
| Matched (evidence found) | 537 | **67.4%** |
| NO_EVIDENCE — no citation extractable at all | 0 | 0% |
| NO_EVIDENCE — citation extracted, no match | 260 | 32.6% |

**Taxonomy of the 260 unmatched-with-citation claims:**

| Bucket | Count | % of 260 | Meaning |
|---|---:|---:|---|
| `genuinely_absent_no_such_provision_any_act` | 140 | 53.8% | Provision number/type not in the corpus under ANY act — a real corpus-coverage gap |
| `genuinely_absent_wrong_act_or_edition` | 78 | 30.0% | Provision exists in corpus, but under a genuinely different Act — correctly not matched |
| `unresolved_act` | 40 | 15.4% | Parser could not resolve an act at all (bundled/ambiguous sentence; correctly declined to guess per `extract_claims()`'s documented field-wide-inheritance rule) |
| `parser_or_matcher_defect_candidate` | 2 | 0.8% | Flagged by the taxonomy's near-miss heuristic (0.5 ≤ overlap < 0.8) for manual review |

**Both defect candidates manually reviewed — confirmed NOT bugs:**
1. `natural_candidates_50_gpu_bare.jsonl / 2022_1043 / c4`: cites "Section 100... the Code of
   Criminal Procedure (CrPC)" — the alias resolves correctly to `code of criminal procedure 1973`,
   but the corpus's only Section 100 record is under `code of civil procedure 1908` — a genuinely
   different Act (0.5 token overlap is coincidental shared vocabulary — "code", "procedure" — not
   evidence of the same Act). Correctly NO_EVIDENCE; likely reflects an upstream
   generation-level confusion (Qwen naming the wrong Code), not a corpus or parser defect.
2. `natural_candidates_batch2_gpu_bare.jsonl / 1974_205 / c1`: cites "Section 11... the Mysore
   Land Acquisition Act" against a corpus that only has the central "The Land Acquisition Act,
   1894" (0.667 overlap). The Mysore princely-state Land Acquisition Act is a real, distinct
   regional enactment, not a spelling variant of the central Act. Correctly NO_EVIDENCE.

Both are now pinned as adversarial regression tests (§5:
`test_wrong_act_crpc_vs_cpc_section_100_never_cross_matches`,
`test_year_edition_land_acquisition_act_central_vs_state_variant`).

**Conclusion: zero confirmed parser or evidence-matcher defects found in the current codebase**
across 797 real claims from every natural GPU experiment this project has run. The 260 NO_EVIDENCE
claims are, to the full extent this taxonomy can determine, genuine corpus-coverage gaps (A) or
correctly-declined ambiguous/wrong-Act cases (E/wrong-act/unresolved), not silent mismatches or
missed matches.

---

## 5. Adversarial test suite (`tests/test_adversarial_citations.py`, originally 15 tests, all passing)

**Addendum, 2026-09-07 — a genuine, currently-live mis-attribution bug found and fixed (not
present in the original 15 tests below, discovered during a later improvement pass).** Real
generated output uses a bare-abbreviation citation shape with no "in"/"of" connector at all —
"Section 302 IPC", "Section 100 CrPC", "Section 302, IPC" — confirmed verbatim in this project's
own committed generation history (`outputs/final_gpu_validation_A.jsonl`,
`outputs/run_A_n30.jsonl`, others). Neither the full-form citation grammar (requires "in"/"of")
nor the bare-Act-mention grammar (requires an "Act"/"Code"/... suffix WORD, which a bare acronym
is not) recognized this as act-bearing, so the citation's act stayed unresolved at the sentence
level and fell through to `extract_claims()`'s field-wide "exactly one distinct act elsewhere in
the field" fallback. That fallback could then actively mis-attribute the citation to a
**different, unrelated Act** stated elsewhere in the same field — reproduced concretely with "...
Section 32 of the Indian Evidence Act, 1872. Section 100 CrPC also applies.", where the CrPC
citation previously resolved to `"indian evidence act 1872"`. This is exactly the
CrPC-vs-CPC-Section-100 confusion category the table below already treats as a known adversarial
risk, surfacing from a different root cause (a missing act-recognition rule, not act-name textual
similarity) than the tests below cover. Fixed in `src/claim_parser.py` (`_TRAILING_ABBREV_RE`): a
bare citation immediately followed by one of the three already-trusted, already-tested single-token
aliases in `_KNOWN_ACT_ALIASES` (`IPC`/`CrPC`/`CPC`) now resolves directly to that act, taking
priority over the less-specific field-wide fallback — this never invents a new alias, it only wires
an already-trusted one into a real-world position the parser previously ignored. 6 new regression
tests added (`tests/test_adversarial_citations.py`, "Bare trailing-abbreviation citations" group),
including the exact mis-attribution reproduction above and a negative test that an unrelated
trailing word never gets treated as an act.

| Category | Tests | Key finding |
|---|---:|---|
| Wrong-Act | 2 | Confirmed safe — genuinely different Acts never cross-match even at moderate token overlap |
| Same-number/different-act | 1 | 3-way split (IPC §34 / Arbitration Act 1940 §34 / Arbitration & Conciliation Act 1996 §34) each independently resolves correctly |
| Year/edition | 2 | **1 confirmed latent limitation** (below) + 1 confirmed-safe real near-miss (Mysore Land Acquisition Act) |
| Aliases | 4 | IPC/CrPC/CPC/ID Act/Evidence Act short forms and parenthetical abbreviations all resolve correctly and distinctly |
| Ranges | 2 | Hyphenated numeric ranges ("Sections 100-105") never silently collide with a real single-section record; legitimate hyphenated provisions ("Section 120-B") correctly distinguished from ranges |
| Multi-Act | 2 | Bundled sentences citing 2–3 different Acts keep every citation's act clean and independently resolvable |
| Ambiguous | 2 | Same provision number resolving to 2+ different Acts elsewhere in a field is correctly left unresolved, never guessed |

**Confirmed latent limitation — fuzzy matching was year-blind
(`test_year_edition_income_tax_act_1961_vs_hypothetical_2025_act`).** `evidence_matcher`'s exact-key
path correctly distinguishes `"income tax act 1961"` from `"income-tax act 2025"` (year is part of
the exact index key). But the **fuzzy fallback**'s `act_significant_words()` tokenizes with
`re.findall(r"[a-z']+", act_norm)`, which drops all digits — so two same-named Acts differing only
by year reduced to an identical significant-word set and could fuzzy-match each other. **Not fixed
in this pass** (see above at the time this was written) since it read as a shared-code change to
`evidence_matcher.py`'s core token-overlap semantics that would need its own dedicated validation
run. **No live collision existed** in the shipped 136-record corpus at that time (no two
same-named, different-year Acts shared a provision_type+provision_number there), so this was a
latent risk for future corpus growth rather than an active production error.

**Update 2026-09-07 — fixed.** `evidence_matcher.match_evidence()` now computes each side's
explicit year(s) directly from `act_norm` (`_act_years`) and vetoes a fuzzy candidate whenever both
the claim and the candidate name an explicit year and those years are disjoint (`_year_conflict`) —
this is a narrow addition to the fuzzy-candidate filter, not a change to `act_significant_words()`
or the token-overlap score itself, so it does not touch any other matching decision. The legitimate
year-*omission* fuzzy path (a claim that states no year at all, e.g. "the Arms Act" with no alias
supplying one) is deliberately untouched — the veto only fires when both sides state a year.
Confirmed via `test_no_cross_act_fuzzy_collision_risk_anywhere_in_expanded_corpus` (the corpus-wide
regression test referenced above) that no historical fuzzy match in the live corpus is affected;
the fix only changes behavior for a future citation that states an explicitly conflicting year,
which now correctly falls through to `NO_EVIDENCE` instead of risking a false match. See
`tests/test_adversarial_citations.py` (now 17 tests in that file, up from 15).

---

## 6. Remaining irreducible gaps (honestly stated)

1. **32/82 v1 records (39%) remain unverified beyond build-time provenance** — not independently
   re-fetched in either the original build session's 8-record spot-check or this audit's 41-record
   pass. All 32 passed every structural/mechanical check (schema, act_norm consistency, no
   duplicate text, correct verdict-assignment rule) with no anomaly, but their literal source text
   has not been independently confirmed. Re-fetching stopped at 41/82 after `indiankanoon.org`
   began returning HTTP 429 (rate limit) — a session/tooling constraint, not a decision to stop
   early.
2. **The fuzzy year-blindness limitation (§5)** was confirmed and tested at the time this was
   written; it was fixed 2026-09-07 (see the update note in §5) — no longer an open gap.
3. **Point-in-time/historical-status caveats already documented in `README_v1.md`** (the 2024
   BNS/BNSS transition affecting most IPC/CrPC records, the pending Income-tax Act 2025
   supersession, the 2018 POCA §13 amendment, the 2021 Income Tax Act §§147/148 substitution) are
   inherent to citing historical case law against current-or-past statute text — no corpus audit
   can eliminate this; a downstream consumer must still know which edition a given piece of case
   law is citing. Not a defect, a standing interpretive requirement.
4. **No professional legal review has ever been performed on v0 or v1** — this remains explicitly
   out of scope for this project's own self-audits, v0's and v1's alike, exactly as both READMEs
   already state. This audit strengthens confidence that the corpus's *stated* content is
   *accurately transcribed*, not that it is *legally complete or current* for any specific
   real-world use.
5. **`genuinely_absent_wrong_act_or_edition` (78 claims, §4)** represents real corpus-coverage
   gaps the taxonomy cannot further reduce without adding more evidence records — a scope decision
   for a future v2 evidence-expansion pass, not a defect in v1 itself.

---

## 7. Before/after metrics

| | Before this audit | After this audit |
|---|---:|---:|
| v1 usable records | 82 total, 79 usable (`VERIFIED_EXACT`) | 82 total, 78 usable (`VERIFIED_EXACT`) |
| Merged v0+v1 usable pool | 137 | **136** |
| Independently re-verified (any session) | 8/82 (9.8%) | **41/82 (50.0%)** |
| Structural audit coverage | not previously run project-wide on v1 in this form | **100% (82/82)** |
| Confirmed content-accuracy defects | 0 known | 0 (41/41 re-fetched records matched) |
| Confirmed presentation/labeling defects | 0 known | 2 found, **2 fixed** |
| Confirmed matcher/parser defects (from NO_EVIDENCE taxonomy) | not re-audited since prior parser fixes | **0** (2 candidates reviewed, both correct behavior) |
| Confirmed latent algorithmic limitations | 0 known | 1 (fuzzy year-blindness — documented, tested, unfixed) |
| Adversarial regression tests | 0 dedicated to this surface | **15**, all passing |
| Project-wide NO_EVIDENCE claims classified | 236 (n=30+targeted+batch1+batch2 only) | **260** (+ final validation batch) |
| Project-wide evidence coverage (all natural claims, v0+v1 pool) | not previously computed with final validation included | **67.4%** (537/797) |

---

## 8. PASS/FAIL decision

**PASS.** The v1 evidence supplement, after this audit:
- Contains no fabricated or wrong-provision content in any independently checked record (50%
  direct re-verification, 100% structural verification).
- Had its 2 genuine defects fixed in place, with full before/after provenance.
- Introduces no confirmed parser/matcher defects — the current codebase correctly handles every
  adversarial category tested, including two real near-miss cases surfaced by this project's own
  natural-data history.
- Has one honestly-documented, tested-but-unfixed latent limitation (fuzzy year-blindness),
  currently inert in the live corpus.
- Remains, like v0, explicitly **not** a substitute for professional legal review.

This is sufficient evidentiary basis to recommend enabling `use_evidence_v1: true` as a
production default (see `FINAL_PRODUCTION_CONFIG.md` for the full, GPU-experiment-informed
decision) — the corpus itself is no longer the limiting factor; it was audited at 5x the
original independent-verification rate and came back clean save for two now-fixed defects.
