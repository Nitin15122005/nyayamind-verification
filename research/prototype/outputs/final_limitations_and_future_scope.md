# Final Limitations and Future Scope

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-27. Companion to `final_research_results.md` (the data) and
`FINAL_PRODUCTION_CONFIG.md` (the production decision). This document answers, as directly and
evidence-first as the project's own history allows: did we actually address the limitation this
project set out to address, what is solved quantitatively, what remains unsolved, and what
evidence supports each conclusion.

> **A note on scope, stated honestly.** This repository does not contain the literal text of an
> external, separately-published "NyayaMind paper" for me to quote against. "NyayaMind" is this
> project's own internal name (`README.md`: *"Prototype v0 · NyayaMind statutory-grounding
> verification layer"*). What the project's own root `README.md` states as its motivating problem
> — under "Project purpose" — is the closest thing to a stated original limitation this repository
> gives me to answer against, and that is what the rest of this document is grounded in:
>
> > "LLMs asked to summarize Indian court judgments will readily name statutes, sections, and
> > articles that sound plausible but are wrong, outdated, or unsupported by the case."
>
> If "the original NyayaMind paper" refers to a specific external document not present in this
> repository, I do not have access to its literal text and have not fabricated one — every claim
> below is checked against this project's own README/config/code, not invented.

---

## 1. Was the stated limitation addressed?

**Partially, and unevenly across its two halves — detection and correction.**

### Detection half: substantially addressed, with measured evidence

The limitation as stated is about generated statutory citations that are **plausible-sounding but
unverified**. This project's verification layer directly attacks that:

- **Before any of this project's work, there was no mechanism at all** to check a generated
  citation against real statute text.
- **After**: 67.4% of all statutory claims ever generated across this project's history (797
  claims, 180 real cases) can be resolved to independently-sourced, individually-verified evidence
  and given a genuine NLI verdict (`final_research_results.md` §C).
- The verification layer has caught **genuine, individually-inspected, checkable content errors**
  on real, previously-unseen generated text — not just synthetic ones. Example
  (`final_gpu_validation.md` §3): a generated sentence describing IPC §304 Part I as applying
  "without any intention to cause death **or hurt**" was correctly flagged CONTRADICTED against
  evidence stating the provision applies when death OR grievous-injury-likely-hurt was intended —
  a real, checkable overstatement, not a verifier artifact.
- **Zero confirmed parser or evidence-matching defects** were found across the entire 797-claim
  history in this session's audit (`no_evidence_taxonomy_v3.json`) — the detection layer's
  remaining gaps are corpus-coverage gaps (§2 below), not implementation bugs.

### Correction half: not addressed at meaningful scale on real data

The README's framing implies the eventual goal is not just flagging bad citations but fixing them.
Here the evidence is much weaker:

- Cumulative natural-data correction success across this project's **entire history**: **1/56
  shipped (1.8%)** (`final_research_results.md` §D).
- Even under the best-evidenced, most-improved configuration this session validated (labeled +
  v0+v1 evidence + assertion_spans + narrow_reverification — now the production default), the
  targeted real-Qwen validation shipped **1/10 (10%)** — an order of magnitude below the
  synthetic-data figure (72.2%) that originally suggested correction was viable.
- The one real natural shipment (`2003_760`/c3) proves the *mechanism* works end-to-end safely on
  real data — it is not a null result — but n=1 is not "solved," it is "demonstrated possible."

**Bottom line: this project has built and validated a real, safe, measurably-effective detection
layer. It has demonstrated — not yet established at scale — that the same layer can also correct.**

---

## 2. What is solved, quantitatively

| Claim | Evidence |
|---|---|
| A working, deterministic citation-extraction + evidence-matching pipeline exists and has 0 confirmed defects | `no_evidence_taxonomy_v3.json`: 797 claims, 2 candidate defects both manually confirmed correct behavior; 15 new adversarial tests, all passing |
| Evidence coverage can be safely expanded | `final_gpu_validation.md` §2: +7.1pp (63.2%→70.3%), McNemar p≈0.0003, 0 regressions, paired design |
| The evidence corpus itself is trustworthy to the extent independently checked | `evidence_v1_independent_audit.md`: 50% of v1 (41/82 records) directly re-fetched and content-verified this session (up from 10%), 0 fabricated/wrong-provision content, 2 minor defects found AND fixed |
| Verification never produces a false-positive contradiction on the one paired synthetic control available | Synthetic c2 (unflagged true claim): 0% false-positive rate, both framings, 59/59 cases |
| The correction mechanism never ships an unsafe fix | 0/122 unsafe shipments across every correction attempt (56 natural + 66 synthetic) in this project's entire history, both by structural invariant and empirical check |
| A scope-check relaxation (assertion_spans) does not weaken safety | Every scope-violation case re-tested under it in this session's data remained correctly rejected; independent sibling-regression net fired 0 times because nothing unsafe reached it |
| Labeled framing outperforms bare on curated, non-synthetic real legal claims | Controlled benchmark: macro F1 0.749→0.968, ENTAILED recall 0.500→1.000 |
| Labeled framing detects (reaches ENTAILED) more often on natural data at a defensible sample size | Pooled 100-case labeled+v0 regime: 16/284 matched claims ENTAILED (5.6%) vs pooled 180-case bare+v0 regime: 2/454 (0.4%) — an 8x rate difference |

---

## 3. What remains unsolved

### 3a. Correction success on natural data is not solved

1.8% cumulative, 10% in the best single targeted test, n=1 in the most-improved configuration.
The dominant blockers, evidenced directly:

- **Claim-level bundling.** One physical sentence backing multiple `Claim` records remains the
  single most-cited structural cause of scope violations across every report in this project's
  history, including this session's (`final_gpu_validation.md` §4). `atomic_scope_check` and
  `narrow_reverification_hypothesis` mitigate but, per this session's own test, did not unlock
  either of the 2 scope-violation cases actually re-tested under them.
- **UPDATE 2026-09-09: partially addressed.** `verification.narrow_primary_hypothesis` (see
  `FINAL_PRODUCTION_CONFIG.md` §5, `outputs/narrow_primary_hypothesis_benchmark_report.md`) now
  extends `assertion_text`-based hypotheses to the PRIMARY verification pass, not just correction
  re-verification, exactly as recommended below. CPU re-scoring of 456 real evidence-matched
  claims: 107 (23.5%) had an actually-narrower assertion available, 31 flipped
  NEI→ENTAILED (manually verified as genuine, not spurious), 0 unsafe reversals. **Not yet
  done**: this uses only the single `assertion_text` field, not the richer `assertion_spans` list
  (the "respectively"-pattern structure) — a claim whose only narrower representation is
  `assertion_spans` still verifies against the full `claim_text` in the primary pass.
- **UPDATE 2026-09-09 (later same day): fresh GPU batch run, correction shipping still
  unmeasured.** `scripts/run_narrow_primary_hypothesis_gpu_ablation.py` ran a real, fresh
  end-to-end Mode-C GPU experiment (15 genuinely fresh natural cases, OLD vs CURRENT config,
  isolating only this lever — see `outputs/narrow_primary_hypothesis_gpu_ablation_report.md`).
  Verification recovery was directionally confirmed (1/12 evidence-matched claims flipped
  NEI→ENTAILED). **Correction triggered 0/15 times under BOTH arms** — this batch produced zero
  CONTRADICTED verdicts and zero low-confidence-NEI triggers on either config, so correction
  shipping was never exercised at all, on either side of the ablation. This is honestly reported
  as "not measured at this sample size", not as "no improvement" or "improvement confirmed" —
  a larger fresh batch (n>=50) is needed to actually observe correction behavior under this
  lever.
- ~~The primary verification pass never uses the narrower `assertion_text` hypothesis~~ — only
  re-verification does. This session's assumption-gold comparison (§E of
  `final_research_results.md`) found labeled framing does NOT improve agreement on a
  bundled-sentence-heavy older claim set, consistent with this specific gap: labeled framing's
  provision label helps less when the surrounding hypothesis is still diluted by sibling
  citations. ~~**Concrete, evidence-backed next step**: extend `assertion_text`-based (or
  `assertion_spans`-based) hypotheses to the PRIMARY verification pass, not just correction
  re-verification.~~ (superseded by the 2026-09-09 update above; assertion_spans-based primary
  verification remains open.)
- **Qwen correction quality itself** — most `correction_failed` outcomes in this project's history
  are the corrector returning the flagged sentence byte-unchanged (a no-op), not a bad edit. This
  is a generation-quality limitation of the 7B corrector model/prompt, not a pipeline defect.

### 3b. No lawyer/professional legal ground truth exists

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

Every number in this project — v0's audit, v1's audit (even at this session's expanded 50%
coverage), and the "provisional assumption gold" — is machine- or LLM-produced, never
professionally verified. This means:

- **True contradiction recall and false-positive rate cannot be computed.** The only recall/FP
  figures that exist are on synthetic (deliberately corrupted) data, which this project's own
  history has repeatedly shown does not predict natural-data behavior.
- **True retrieval precision cannot be computed.** The exact/fuzzy match-method ratio and manual
  CONTRADICTED-claim inspection (§C, §3 of `final_gpu_validation.md`) are proxies, not
  measurements.
- This is not a gap this project can close by auditing itself further — it requires the separate,
  not-yet-started lawyer annotation phase this task was explicitly instructed not to wait for.

### 3c. The evidence corpus has real, quantified, honestly-documented residual gaps

- 39% of v1's 82 records (32) remain unverified beyond build-time provenance (rate-limited by the
  source site this session, not abandoned).
- A confirmed, tested, ~~unfixed~~ **fixed 2026-09-07** latent limitation: fuzzy evidence matching
  was year-blind (`act_significant_words()` strips digits, so same-named Acts differing only by
  year could fuzzy-cross-match) — not triggered in the live 136-record corpus at the time this was
  written (so no historical output changed), but a real architectural gap for future corpus growth.
  `evidence_matcher.match_evidence()` now vetoes a fuzzy candidate whenever both the claim's and the
  candidate's `act_norm` name an explicit, conflicting year (`_year_conflict`); the legitimate
  year-omission fuzzy path (one side states no year) is untouched. See
  `tests/test_adversarial_citations.py::test_year_edition_income_tax_act_1961_vs_hypothetical_2025_act`
  (now pins the fixed behaviour) and `::test_year_omission_still_fuzzy_matches_when_claim_states_no_year`.
- 140 (53.8% of all NO_EVIDENCE claims with a citation) are genuine corpus-coverage gaps — the
  corpus does not have every provision Qwen cites, and closing this requires more evidence
  records, not code changes.

### 3d. Point-in-time legal currency is inherently unresolved by any audit this project can run

The 2024 BNS/BNSS transition, the pending Income-tax Act 2025 supersession, and several
mid-2010s-to-2020s targeted amendments mean a stored "canonical" text is only correct **for case
law from before its own supersession date**. No corpus audit eliminates this — it is a standing
interpretive requirement for any downstream user, documented consistently since v0's own README.

---

## 4. Is the case strong enough for a research paper, and on what basis specifically

**Can honestly claim, with evidence:**
- A real, working, safety-invariant-preserving verification + selective-correction pipeline for
  statutory grounding, with zero confirmed implementation defects across 797 real claims.
- Statistically significant, safe evidence-coverage improvement from a targeted corpus expansion,
  independently audited at 5x the original verification rate.
- Detection-side improvement from premise framing, confirmed on both a curated benchmark and (at
  pooled scale) real natural data.
- A first, safe, inspected proof that the full improved pipeline CAN ship a genuine correction on
  real, previously-unseen natural data — with the honest caveat that this is n=1, not a rate.

**Cannot honestly claim:**
- Solved or even reliably-effective automatic correction on real data (1.8-10% success, not 72%).
- Any precision/recall/false-positive figure as validated system accuracy (no real ground truth
  exists yet).
- That labeled framing is unconditionally better on natural data — the assumption-gold
  counter-signal (§E, `final_research_results.md`) means this is regime-dependent, not universal.
- That the evidence corpus is a legal gold standard — it is a better-audited development corpus,
  explicitly and repeatedly stated (by this project itself, both before and after this session) to
  not be one.

---

## 5. Recommended future scope, in priority order (evidence-backed, not speculative)

1. **PARTIALLY DONE 2026-09-09** (see §3a): extend narrow-hypothesis verification to the PRIMARY
   pass, not just correction re-verification — directly targeted the bundled-sentence dilution
   problem shown to exist in §3a/§E. `assertion_text`-based primary verification shipped
   (`verification.narrow_primary_hypothesis`); a fresh GPU batch confirmed the verification-recovery
   mechanism directionally (1/12 evidence-matched claims) but could not exercise correction
   shipping at all (0/15 triggers on either arm — see `outputs/narrow_primary_hypothesis_gpu_ablation_report.md`).
   **Still open**: the richer `assertion_spans`-based primary verification, and a larger (n>=50)
   fresh batch actually powered to observe correction-shipping behavior under this lever.
2. **A larger (50-100 case) fresh natural batch under the exact final production config**, to
   move the single most novel finding in this session (1/10 shipped) from "demonstrated possible"
   to "measured rate" — explicitly flagged as the needed follow-up in `FINAL_PRODUCTION_CONFIG.md`.
3. **Complete the remaining 32/82 v1 evidence re-fetches** once the source site's rate limit
   allows, to close the last gap in this session's audit.
4. **The lawyer-annotation phase** (explicitly out of scope for this task) — the only way to ever
   compute a real precision/recall/false-positive figure.
5. **A dedicated, larger-sample validation of `atomic_scope_check`/`narrow_reverification_hypothesis`'s
   effect on shipping rate specifically** — this session's evidence supports "no harm," not yet
   "measured benefit," for those two levers in isolation.
