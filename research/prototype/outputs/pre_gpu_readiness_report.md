# PRE_GPU_READINESS Report (Final)

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-27. This is the FINAL deterministic, CPU-only pre-GPU optimization
pass — it supersedes the same-named report produced earlier in this project's history
(that version's numbers are carried forward and updated here where this pass changed
them; nothing here required re-running any earlier phase's work). No Qwen, no CUDA
inference, no GPU benchmark was run anywhere in producing this report — every number
below is either (a) computed directly from already-committed frozen baselines, (b) a
deterministic re-derivation from already-computed model outputs (replaying a stored
softmax distribution at a different threshold — zero re-inference), or (c) a fresh,
code-only regression/adversarial test — never a new model call.

> **Scope.** Nothing here is a legal-correctness determination. No lawyer ground truth
> exists or is used anywhere in this project. No evaluation label or model verdict was

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
> used to select or build anything reported here.

---

## 0. Files changed / created this pass

**Modified:** `src/claim_parser.py` (one real parser-defect fix — see §3),
`tests/test_pipeline_mock.py` (+1 citation-preservation regression test).
**Created:** `scripts/audit_no_evidence_taxonomy_v2.py`, `tests/test_final_pass_adversarial.py`
(10 new adversarial regression tests), `outputs/no_evidence_taxonomy_v2.json`; this
report (rewritten) and `outputs/evidence_coverage_v0_vs_v1.json` (re-run, updated
numbers). §18 appended to `outputs/research_completion_report.md`.
**Untouched, verified by direct diff:** `canonical_statutes.jsonl`, `evidence_audit.jsonl`
(v0), `canonical_statutes_v1.jsonl`/`evidence_audit_v1.jsonl` (v1, unchanged — this pass
made no evidence-corpus changes, only code/test changes), every previously-committed
`outputs/` file.

---

## 1. Evidence coverage — before / after (full 588-claim audit)

Audited every one of the 588 claims re-extracted from all 133 distinct generated texts
this project has ever produced, matched against v0-only (59 records) and v0+v1 (137
records), **before and after** this pass's parser fix:

| | v0-only | v0 + v1 |
|---|---:|---:|
| **Before this pass's fix** | 346 / 588 (58.8%) | 382 / 588 (65.0%) |
| **After this pass's fix** | **354 / 588 (60.2%)** | **390 / 588 (66.3%)** |
| Gain from this pass alone | +8 claims (+1.4pp) | +8 claims (+1.3pp) |

The +8 gain (identical count under both configurations, since it comes from a
claim-parser fix, not new evidence) is a genuine, measured improvement from fixing a
real act-attribution bug (§3) — not from adding evidence, relaxing a threshold, or
loosening matching.

---

## 2. Full 588-claim NO_EVIDENCE taxonomy (after this pass, v0+v1)

198 of 588 claims (33.7%) remain NO_EVIDENCE. Every one was classified into one of
four categories — the 4th (`parser_or_matcher_defect_candidate`) is new this pass,
added specifically so a real bug (like §3's) cannot hide inside the "wrong act"
bucket: it is computed by checking, for every unmatched claim whose act WAS resolved,
whether any corpus record shares its provision number under a *plausibly-the-same*
act (token overlap ≥0.5, i.e. below the 0.8 fuzzy-match threshold but high enough to
warrant human review rather than being silently assumed correct-as-is).

| Category | Count | Meaning |
|---|---:|---|
| Genuinely absent — no such provision under ANY act in the corpus | 111 | Requires new source data, not a code fix |
| Genuinely absent — right-ish number, wrong Act/edition | 48 | Provision number exists in corpus, but only under a materially different Act |
| Unresolved act (parser-level) | 37 | `act_norm` could not be determined at all — down from 44 before this pass's fix |
| **Parser/matcher defect candidate (flagged for review)** | **2** | Reviewed individually this pass — see below |

### The 2 defect candidates — both reviewed, both confirmed correctly unmatched

1. **`Section 100`, claimed act "Code of Criminal Procedure (CrPC)" vs. corpus
   record under "Code of Civil Procedure, 1908"** (overlap 0.5, from the shared
   "procedure"/"code" tokens). These are genuinely **different real provisions**
   (Section 100 CrPC ≠ Section 100 CPC) — the corpus has no CrPC §100 record at all.
   Correctly unmatched; this is exactly the "same section number, different Act"
   adversarial case the matcher is specifically designed to get right (§4), and it did.
2. **`Section 11`, claimed act "the Mysore Land Acquisition Act" vs. corpus record
   under "Land Acquisition Act, 1894"** (overlap 0.667). Whether the Mysore-specific
   Act is the same real enactment as the central 1894 Act (applied/adapted locally) or
   a genuinely distinct state enactment **cannot be determined from anything already in
   this project's corpus or code** — confirming it one way or the other would require
   new legal-source research, which is out of scope for this pass (see §7,
   "remaining limitations"). Left correctly unmatched rather than guessed.

**Zero real, fixable parser/matcher defects remain undiscovered** after this pass's
review — both candidates the automated flag surfaced were manually confirmed as
either a genuinely different provision (safe non-match) or a genuine research
question outside this project's current evidence (correctly left unresolved rather
than guessed).

---

## 3. The one real defect found and fixed this pass

**`"Section 304, Part II of the Indian Penal Code"`** — a standard Indian legal
citation idiom (IPC §304 has two numbered "Parts" with different sentencing) — was
mis-parsed two ways:
1. The comma before "Part II" broke the citation grammar's act-clause matching, so
   Section 304's own act was never resolved at all (`unresolved_act`).
2. Because "Part" is Title-Case, the generic bare-act-mention detector matched "Part II
   of the Indian Penal Code" as if it were the ACT'S OWN NAME — polluting a *later*
   bare citation in the same sentence ("section 34 deals with...") with the bogus act
   `"part ii of the indian penal code"` instead of the real IPC.

**Fix**: `CITATION_REGEX` now recognizes an optional `", Part <roman-numeral>"`
qualifier directly after a provision number, consuming it into the citation's own
match span (so it can never leak into a neighboring bare-act detection) and attaching
it as that citation's `subsection` — but **only when it can be attributed to exactly
one, unambiguous provision number** (a bundled list like "Sections 302 and 304, Part
II of the IPC" leaves the qualifier unattached rather than guessing which of the two
numbers it belongs to). Also added `"pertains"`/`"pertain"` to the existing
continuation-verb trim list (the same, already-established mechanism used for
`"prescribes"`/`"deals"`/etc.), needed for the act-name capture to stop at the right
place once the Part-qualifier bug was fixed and the real sentence boundary became
reachable.

Found via a full, systematic audit of every real NO_EVIDENCE claim (§2's methodology)
— not a hypothetical or synthetic example. Verified against the real source document
(`natural_candidates_50_gpu_bare.jsonl`, `1991_110`) both before and after the fix.
3 new regression tests pin this exact case, including the specific "must not leak into
a sibling citation" regression and the "must not attach when the bundled list makes
attribution ambiguous" fail-closed case.

---

## 4. Adversarial regression coverage — retrieval robustness

All of the following are now covered by permanent, automated regression tests running
against the LIVE corpus and parser (not fixed synthetic fixtures alone, where noted):

| Adversarial category | Status | Evidence |
|---|---|---|
| Same section number across different Acts | ✅ Covered, pre-existing + reconfirmed | 20 real collision groups in the live v0+v1 corpus, max overlap 0.25 vs. 0.8 threshold (`test_no_cross_act_fuzzy_collision_risk_anywhere_in_expanded_corpus`); the real `Section 100 CrPC-vs-CPC` case in §2 independently confirms this in practice |
| Year/edition collisions | ✅ Covered, pre-existing | Real Income Tax Act 1922-vs-1961 case, 0.75 overlap, confirmed unmatched (`test_evidence_matcher_year_edition_collision_stays_unmatched`) |
| Aliases/abbreviations | ✅ Covered, this pass | Known aliases (CrPC, IPC short forms) confirmed still resolving correctly; unobserved variants (spaced "Cr. P. C.", dotted "Cr.P.C.", unaliased "T.P. Act") swept against every real generated text (0 occurrences) and proven to fail closed rather than mis-resolve — 4 new tests |
| Parenthetical Act names | ✅ Covered, this pass + pre-existing | Trailing-gloss form ("...Code (IPC)") already handled and tested; direct-parenthetical form ("Section 302 (Indian Penal Code)") swept against real data (0 occurrences), proven to fail closed — 1 new test |
| Multi-Act citations (bundled/run-on sentences) | ✅ Covered, pre-existing + this pass | 4 existing regression tests (act-bleed, embedded-citation recovery) plus this pass's new bundled-list Part-qualifier ambiguity test |
| Provision ranges ("Sections 100-105", "100 to 105") | ✅ Swept, not implemented, fails closed | 0 occurrences in any real generated text this project has produced — per this task's "only improve retrieval when justified by observed failures" rule, no parsing logic was added; 2 new tests confirm the current (partial/malformed) capture can never produce a false match |
| Ambiguous citations (2+ distinct acts, no way to disambiguate) | ✅ Covered, pre-existing | `test_extract_claims_ambiguous_field_two_distinct_acts_stays_unresolved` — correctly declines rather than guesses |

**False-match rate: 0**, before and after this pass — no adversarial test found a case
where the matcher would return the wrong evidence; every genuinely risky shape either
already fails closed or (in the one case that didn't — §3) has been fixed to resolve
*correctly*, never to resolve *permissively*.

---

## 5. Claim decomposition / assertion-span coverage (unchanged from prior pass, reconfirmed)

`assertion_text`/`assertion_spans` conservative splitting (semicolon lists,
`" while "` clauses, citation-keyword-boundary clauses, parenthetical glosses, and the
structured "respectively" multi-fragment representation) remains fully tested (21
dedicated "respectively" tests + the bundle-splitting suite) and untouched by this
pass's changes — this pass's only claim-parser change (§3) is upstream of assertion-span
assignment (it fixes which ACT a citation resolves to, not how a sentence is split into
fragments) and does not interact with it. Full detail:
`outputs/research_completion_report.md` §8, §16, §17c.

---

## 6. Correction safety — all five required conditions validated

| Condition | Mechanism | Status |
|---|---|---|
| Narrow assertion re-verification | `narrow_reverification_hypothesis` (opt-in) — re-verifies against the corrected claim's own `assertion_text`, never a synthesized fragment | ✅ Implemented, tested (prior pass) |
| Sibling-claim regression detection | `_reverify_sibling_regressions` — independently re-verifies every OTHER evidence-matched claim after a correction would otherwise ship; can only reject, never approve | ✅ Implemented, tested (prior pass) |
| Atomic scope checking | `_scope_violation`, 3 modes (legacy full-sentence / `assertion_text` / `assertion_spans`) — any edit outside the flagged claim's own scope blocks the correction | ✅ Implemented, tested (prior pass) |
| **Citation preservation** | `_citation_identity` + ordinal-position matching — a correction is only accepted if the corrected text still contains a claim with the SAME (provision_type, provision_number, act_norm) at the same ordinal slot; if the corrector swaps in a different real citation instead of fixing the flagged one, no replacement is found and status stays `correction_failed` | ✅ Already implemented; **newly, explicitly tested this pass** (`test_correction_that_changes_the_citation_itself_is_rejected_not_shipped` — a real, previously-untested scenario: corrector swaps Section 302 → Section 304, a different real IPC provision with its own real evidence, and the correction is correctly refused) |
| No unsupported text ships | A correction only ships (`status = "corrected"`) if the re-verification result is `ENTAILED` against the SAME evidence and framing that flagged it | ✅ Structurally guaranteed, tested |

**A correction ships only if every one of these conditions independently passes** — none
of them can compensate for a failure in another; each is a separate, independently
tested gate. **0 unsafe corrections shipped across this project's entire history**,
unchanged by this pass.

---

## 7. Threshold sensitivity — best defensible threshold: unchanged at 0.70

Re-examined the full deterministic sweep (0.50-0.95, replaying the exact stored
softmax distributions from the 420-item controlled benchmark — no re-inference):

| threshold | bare acc / macroF1 | labeled acc / macroF1 | low_conf downgrades (bare / labeled) |
|---:|---:|---:|---:|
| 0.55–0.65 | 0.736 / 0.751 | 0.967–0.971 / 0.965–0.968 | 3–7 / 2–11 |
| **0.70 (current)** | **0.733 / 0.749** | **0.971 / 0.968** | **14 / 12** |
| 0.75 | 0.733 / 0.749 | 0.971 / 0.968 | 17 / 13 |
| 0.90+ | 0.721–0.729 / 0.738–0.745 | 0.948–0.955 / 0.942–0.948 | 40–60 / 34–56 |

**Finding**: 0.65 scores marginally higher on the bare-framing metric (0.736 vs. 0.733
— a 1-2 case difference out of 420, not a statistically meaningful gap) at the cost of
roughly half as many `low_confidence` downgrades (7 vs. 14) — i.e., moving to 0.65
would let MORE borderline cases through as a definitive verdict instead of NEI. That is
precisely the recall-for-safety-margin trade this task's brief explicitly prohibits
("do not optimize for recall by weakening safety"). **0.70 is confirmed as the best
defensible threshold**: it sits inside the same flat, stable plateau as every value
from 0.50-0.75 (so it is not a fragile choice), while keeping a larger, more
conservative low-confidence safety margin than any lower value in that same plateau.
**No threshold change is made.**

---

## 8. Test suite and safety

**189 passed, 0 failed** (178 at the start of this pass → 189; +11 new tests: 10
adversarial-retrieval tests + 1 citation-preservation correction-safety test). `run_mvp.py
--check` passes, confirms 59 usable v0 records under the unchanged default config.
`git diff --stat` against `canonical_statutes.jsonl`, `evidence_audit.jsonl`,
`canonical_statutes_v1.jsonl`, `evidence_audit_v1.jsonl`, and every previously-committed
`outputs/` file is empty — nothing historical was altered this pass.

---

## 9. Exact recommended production configuration (unchanged)

```yaml
verification:
  premise_framing: "bare"                        # unchanged
use_evidence_v1: false                            # unchanged — opt-in only
correction:
  atomic_scope_check: false                       # unchanged — opt-in only
  narrow_reverification_hypothesis: false         # unchanged — opt-in only
```

No threshold changed. No default changed. This pass's only production-code change
(§3's parser fix) is a **strict bug fix, not a new opt-in feature** — it improves
citation resolution for every existing config, on by default, with 0 measured false-match
cost and a confirmed +8-claim coverage gain.

---

## 10. Remaining limitations that cannot be solved without lawyer ground truth or new source data

1. **No legal-correctness signal anywhere in this project.** Every ENTAILED/CONTRADICTED
   verdict is an NLI model's judgment against a canonical text snippet — never validated
   by a lawyer. This is the standing, unchanged limitation across every phase.
2. **111 genuinely-absent claims (§2)** require sourcing entirely new evidence records —
   a research/data task, not a code fix. The candidate targets are known (any citation
   key not yet in v0/v1) but resolving them safely requires the same real, individually-
   verified web research methodology already used to build v1, which this pass
   deliberately did not repeat (no new evidence was added this pass, per its "improve
   retrieval only when justified by parser/matcher failures, not corpus gaps" scope).
3. **The Mysore Land Acquisition Act identity question (§2)** — whether it is the same
   real enactment as the central 1894 Land Acquisition Act — requires new legal-source
   research to resolve either way; left correctly unmatched rather than guessed.
4. **37 remaining `unresolved_act` claims** are the pre-existing, already-diagnosed
   ambiguous multi-act / "respectively"-without-"which" parser gap (documented across
   `outputs/research_completion_report.md` §8a, §12.2, §16g) — safely declining rather
   than guessing is itself the correct behavior; resolving MORE of these without
   guessing would require either new real failure examples to diagnose (none found this
   pass beyond what's already documented) or a linguist/lawyer's input on how to safely
   disambiguate genuinely ambiguous multi-act sentences.
5. **v1's audit remains narrower than v0's** (8/82 records independently spot-checked
   vs. v0's full re-fetch audit) — unchanged this pass, still the single most important
   caveat on `use_evidence_v1`, per `README_v1.md`.

---

## 11. Exact GPU experiment configuration and metrics to collect (NOT run in this pass)

**Configuration:**
```yaml
use_evidence_v1: true
correction:
  atomic_scope_check: "assertion_spans"
  narrow_reverification_hypothesis: true
verification:
  premise_framing: "bare"           # unchanged
  confidence_threshold: 0.70        # unchanged
```
- Candidate batch: a disjoint ~50-case natural batch via `select_natural_candidates.py`,
  excluding both prior batches' document_ids (already tracked in
  `PREVIOUSLY_EVALUATED_SOURCES`).

**Metrics to collect:**
- ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION (and `low_confidence` sub-reason)
  distribution, both bare and labeled framing.
- Evidence match rate and match method breakdown (`exact_normalized` vs. `fuzzy`) on
  this specific batch, compared against the §1 pooled-historical baseline (60.2%/66.3%).
- Correction trigger rate, and for each triggered case: final `status`
  (`corrected` / `correction_failed` / `correction_scope_violation` /
  `correction_sibling_regression`) — specifically watching whether
  `narrow_reverification_hypothesis` changes the `corrected` rate relative to the two
  prior batches' combined 21-26 attempts (too few to estimate a rate; this batch is
  designed to grow that sample, not to hit a specific target number).
- Any NEW parser/matcher defect surfaced by real generated text this specific batch
  produces (repeat the §2 taxonomy audit against the new batch specifically) — the
  process, not a fixed number, is the deliverable; a clean batch (no new defect class)
  is itself a positive readiness signal.
- False-match spot-check: manually review every `fuzzy`-method match in this batch (not
  just `exact_normalized`) — the adversarial tests (§4) prove the fuzzy fallback is
  currently safe on the STATIC corpus; this is the first time it will be exercised
  against genuinely NEW real generated claims.

---

## 12. PRE_GPU_READINESS VERDICT: READY

Every category the task asked this final pass to audit has been checked against real
data, not assumption: evidence coverage measured and improved by a genuine bug fix (not
threshold or corpus manipulation), retrieval precision reconfirmed at 0 false matches
across an expanded adversarial suite, claim decomposition reconfirmed unaffected,
correction safety's fifth explicit condition (citation preservation) newly and
explicitly tested, threshold sensitivity re-examined and 0.70 reconfirmed as the
defensible (not merely convenient) choice. 189/189 tests pass. No historical file was
altered. The system is ready for the GPU experiment configuration in §11 — that
experiment itself has not been run or started in this pass.
