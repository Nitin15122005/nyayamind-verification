# Premise-Framing Natural-Data Validation — genuine end-to-end correction path on real NyayaRAG claims

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. Follows `verifier_framing_gpu_validation.md` (synthetic GPU phase) and
`natural_reverification_framing.md` (natural CPU re-scoring phase). Answers the question those
left open: **does the synthetic labeled-framing correction gain transfer to real NyayaRAG
claims?**

> **Scope of every verdict below.** These are outputs of a small public NLI model
> (DeBERTa-v3-base-mnli-fever-anli) and a 7B instruction model (Qwen2.5-7B-Instruct, 4-bit) run
> against real NyayaRAG-generated statutory-grounding text, checked against a 59-record
> third-party-sourced evidence corpus. They are **not** legal-correctness determinations. No
> lawyer ground truth exists (`lawyer_annotation.jsonl` still holds Claude-generated assumption
> labels only, per `mvp_assumption_evaluation.md`) and none is fabricated here.

---

## 0. Environment confirmed before running anything

| Check | Result |
|---|---|
| Git branch | `main` |
| Working tree | clean except `baseline/LegalSeg` submodule pointer (unrelated, pre-existing) and this task's new files |
| GPU environment | `research/.venv` (torch 2.2.2+cu121), NVIDIA GeForce RTX 4050 Laptop GPU |
| Qwen2.5-7B-Instruct / DeBERTa-v3-base-mnli-fever-anli | Both already cached locally, same models as the synthetic GPU run |
| Pre-run test suite | 119 passed, 0 failed |
| Post-run test suite | 119 passed, 0 failed |

No fallback to CPU was used for the correction pass. `--with-correction` refuses to run without
CUDA (same guard as `compare_premise_framing_synthetic.py`).

---

## 1. What data this uses, and what it does NOT do

Per the brief: **no new dataset, no new arbitrary natural sweep.** This reuses exactly the two
committed natural-evaluation output files that already exist in this project:

- `run_B_n30.jsonl` — 30 documents, 88 claims (the original A/B/C n=30 run's mode-B block)
- `run_natural_targeted.jsonl` — 11 documents, 29 claims (`mode_B` block)

Both were produced by the existing `run_eval_30.py` / `run_natural_targeted_eval.py`
infrastructure, under production's bare-framing default, on the real NyayaRAG case corpus. This
is the same pooling `scripts/rerun_natural_verification.py` already used for the earlier CPU
re-scoring pass (`natural_reverification_framing.md`).

**The generated statutory-grounding text is reused verbatim — the generator was never invoked
in this task.** Only two things are genuinely re-run: (1) verification, per framing, using the
real `pipeline.apply_verification`, and (2) — new in this report — **correction**, using the
real `pipeline.apply_selective_correction`, genuinely invoking Qwen2.5-7B on GPU whenever a
claim triggers under a given framing. This is the natural-data analogue of the synthetic GPU
report's method, via a new harness, `scripts/compare_premise_framing_natural.py`, built for this
task and mirroring `compare_premise_framing_synthetic.py` line-for-line in structure.

**Overlap note (transparency, not a bug fix):** all 11 documents in the targeted set are also
present in the n=30 set (same `document_id`s). They are **not byte-identical generations** —
comparing `generated_field.text` for the 11 shared document_ids: 6/11 identical, 5/11 differ
(consistent with known minor run-to-run non-determinism in 4-bit GPU inference between separate
sessions, not something this task modifies or investigates further). So this evaluation pools
**41 (document, source-run) pairs over 30 distinct underlying cases** — 11 of which were
generated twice, independently. Every downstream count in this report (117 claims, 52
evidence-matched) is the pooled 41-pair figure, matching the convention `natural_reverification_framing.md`
already established, not a claim of 41 independent documents.

Same Qwen model, same DeBERTa model, same 0.70 threshold, same seed (42), same evidence pool,
same claim extraction (`claim_parser.py`, unmodified), same correction policy
(`apply_selective_correction`, unmodified), same safety gate (`status = "corrected"` iff
re-verification == ENTAILED, unmodified). `config/prototype.yaml`'s default (`bare`) was not
changed for this run.

---

## 2. Validity gate

The bare arm's freshly-computed verdicts, for every evidence-matched claim, must reproduce the
verdict already committed in `run_B_n30.jsonl` / `run_natural_targeted.jsonl` (which were
produced under production's bare default).

**52/52 evidence-matched claims reproduced exactly.** Gate passed; the comparison below is
trusted. (This also cross-checks against the independent CPU re-scoring pass in
`natural_reverification_framing.md`, which reported the same 52/52 reproduction and the same 3
verdict flips — see §5.)

---

## 3. Results — full pooled natural set (41 document-runs, 117 claims)

| # | metric | bare | labeled |
|---|---|---|---|
| 1 | ENTAILED | 0 | **3** |
| 2 | CONTRADICTED | **0** | **0** |
| 3 | NOT_ENOUGH_INFORMATION | 52 | 49 |
| 4 | NO_EVIDENCE | 65 | 65 |
| 5 | documents with ≥1 correction-triggering claim | **0** | **3** |
| 6 | correction attempts | 0 | 3 |
| 7 | corrections shipped (SUCCESS, `status="corrected"`) | 0 | **0** |
| 8 | correction_failed | 0 | 2 |
| 9 | correction_scope_violation | 0 | **1** |
| 10 | unsafe corrections shipped (shipped but not ENTAILED) | 0 | **0** |
| 11 | unflagged-claim preservation | 0/0 (n/a) | **14/16 = 87.5%** |
| 12 | peak VRAM (cumulative) | 5,408 MiB | 7,531 MiB |
| 13 | runtime (verification / correction) | 1.2s / 0.0s | 1.0s / 97.7s |

**Evidence coverage:** 52/117 = 44.4% of claims matched evidence; 65/117 = 55.6% NO_EVIDENCE.
Identical in both arms — evidence matching does not depend on premise framing (see §9 for why
this is a separate problem, not a verifier-framing effect).

**Correction success rate on natural data: 0/3 = 0.0%,** vs. the synthetic GPU run's 26/36 =
72.2% (`verifier_framing_gpu_validation.md`). See §7 for why, and §8 for why the raw 0% number
understates how little actually happened.

---

## 4. Correction triggers happen almost exclusively under labeled framing — as predicted

Bare framing triggered **zero** corrections on natural data, consistent with every prior
natural-data report in this project (`research_evaluation_final.md`: 0/88 and 0/29 triggers;
`mvp_assumption_evaluation.md`: 0/30 triggers). This report is the first to actually attempt
correction once labeled framing unlocks 3 triggers — nothing new happened on bare because bare
never reaches the corrector on real claims. This is expected and reported here for completeness,
not as a new finding.

---

## 5. Every natural-data verdict flip between bare and labeled (full 117-claim set)

**3/117 claims changed verdict.** All three are the same three the earlier CPU re-scoring pass
found (`natural_reverification_framing.md`), now reproduced under GPU/fp16 as well:

| claim | evidence | bare → labeled | labeled confidence |
|---|---|---|---|
| n30/1971_200/c1 | Section 120B, IPC | NEI → **ENTAILED** | 0.807 |
| n30/1971_200/c2 | Section 420, IPC | NEI → **ENTAILED** | 0.738 |
| targeted_n11/2009_1385/c1 | Section 302, IPC | NEI → **ENTAILED** | 0.875 |

Claim text (n30/1971_200/c1, c2): *"The statutory grounding for this case includes the Indian
Penal Code, specifically Sections 120B, 420, and 467."* — a **single generic multi-citation
listing sentence** that gets extracted as one claim record per cited section, each checked
against a different section's evidence text alone.

This is the same "shallow entailment" pattern flagged as a concern in
`verifier_framing_validation.md` §7 before the GPU run: labeled framing makes the model treat "X
is among the sections that apply" as entailed by any one of those sections' bare statute text,
once the label matches. That is a defensible reading (the sentence names Section 120B; Section
120B's text is the premise) but it is **not** evidence that the model verified the *content* of
what each section requires — the claim doesn't assert any content, it only names sections. None
of the 3 flips involve a claim that states what a section *does* (contrast with the still-NEI
claims in §6 of `natural_reverification_framing.md`, e.g. "Section 302 prescribes the punishment
for murder... Section 34 deals with criminal liability...", which stayed NEI in both arms).

**None of these 3 flips triggered correction** (their confidence was above 0.70, so no
`low_confidence` downgrade applied) — they are a precision observation about ENTAILED, not a
CONTRADICTED finding, and are unrelated to the 3 correction attempts in §7–8, which came from
entirely different claims.

---

## 6. Every CONTRADICTED result — inspected for shallow/multi-citation artifacts

**There are none to inspect.** CONTRADICTED count is 0/117 in both bare and labeled framing.
This matches every prior natural-data report in this project without exception
(`research_evaluation_final.md`, `mvp_assumption_evaluation.md`): Qwen2.5-7B's natural
statutory-grounding generations have never produced a single claim the DeBERTa verifier calls
CONTRADICTED, under either premise framing, across 41 document-runs sampled so far. That absence
is consistent with either (a) Qwen's natural generations being largely faithful paraphrases, or
(b) the verifier/evidence pool being insufficient to detect the errors that are there — this
report cannot distinguish the two, and neither could any prior report in this project. No lawyer
ground truth exists to settle it.

---

## 7. Does labeled framing create any false-positive contradictions on natural data?

**No — trivially, because it produces zero contradictions of any kind** (§6). Labeled framing's
only observable effect on natural verdicts is the ENTAILED shift in §5 and the three
low-confidence-NEI correction triggers in §8, never a new CONTRADICTED verdict. The
zero-false-positive property that held on the synthetic set (§6 of the GPU synthetic report)
holds here too, but on natural data the claim is close to vacuous — there is no CONTRADICTED
verdict of any kind to be a false positive.

---

## 8. Correction quality on natural data — inspected sentence-by-sentence, not just by verdict

Three documents triggered correction under labeled framing (all via the `low_confidence`
NEI downgrade — natural data has never produced an outright CONTRADICTED trigger). Each is
examined below because the raw "0/3 shipped" number, read alone, understates what actually
happened: **in two of the three cases, Qwen did not change the flagged sentence at all.**

### 8a. `n30/2004_632`, target `c3` → **correction_scope_violation**

Flagged claim (confidence 0.496, matched against Section 109 IPC — abetment): *"...and Section
109, which pertains to the liability of an **abetter**."* Qwen's only edit, anywhere in the
280-word paragraph, was **"abetter" → "abettor"** — a spelling correction, not a substantive
rewrite toward the evidence text.

That one-word edit was enough to trip the scope-violation gate, but not for the reason the gate
exists to catch. `c1` and `c2` in this document are **duplicate claim records that share the
exact same sentence text as `c3`** — a known, previously-documented parser limitation (a single
sentence citing three sections becomes three claim records, one per citation, all with identical
`claim_text`; see `mvp_assumption_evaluation.md` §5's flagged extraction-bug pattern). Because
`c1`/`c2`'s recorded `claim_text` still contains the old spelling "abetter", and the corrected
paragraph now reads "abettor", the scope-violation check (`pipeline._scope_violation`, correctly
and exactly as designed) found that `c1`'s and `c2`'s claim text no longer appears verbatim in
the corrected text, and rejected the correction. **The safety gate worked correctly** — it is
not wrong to reject this — but the *reason* it fired is a claim-parser duplication artifact
(the same document sentence counted three times), not the corrector touching unrelated content
in any meaningful sense. This is the only one of the 3 attempts where Qwen changed anything.

### 8b. `n30/2023_26`, target `c2` → **correction_failed**

Flagged claim: *"The Indian Penal Code, 1860, specifically Sections 148, 302, 304 Part II, and
324, along with Section 149 of the Code of Criminal Procedure, 1973, are the statutory grounding
for this case."* — matched (confidence 0.599) against **"Section 302 in The Code of Criminal
Procedure, 1973"** (permission-to-conduct-prosecution text), not IPC Section 302 (murder). This
is the same **act-attribution bug already flagged** in `mvp_assumption_evaluation.md` §2
(disagreement pattern "`A0078`... an upstream act-attribution bug fed in CrPC §302 'permission to
conduct prosecution' text as if it were IPC §302 murder text") — the evidence being verified
against is wrong-act evidence from a pre-existing, documented parser/matcher bug, not a
genuinely ambiguous legal claim.

Qwen's output is **byte-identical to the input** — a complete no-op. Sensible, arguably: the
prompt asks it to rewrite the flagged sentence to be consistent with the (wrong-act) evidence
text it was given, and the sentence as written is not actually inconsistent with real law, so
there was nothing coherent to rewrite it into. Re-parsing the identical output found no claim
matching the original citation closely enough to re-verify (`reverification: {}`), so this was
recorded as `correction_failed` by default rather than compared against anything.

### 8c. `n30/2008_2648`, target `c4` → **correction_failed**

Flagged claim: *"Section 420 mandates the proof that the accused made a contract with the
intention to deceive or cheat the other party, leading to the other party suffering a loss."*
(confidence 0.693, just under the 0.70 threshold) against evidence *"Whoever cheats and thereby
dishonestly induces the person deceived to deliver any property... "* This is arguably a
reasonable paraphrase of the elements of cheating under IPC §420 — not an obvious error. Qwen's
output is again **byte-identical to the input.**

**A genuine pipeline artifact was found and is reported, not fixed, here:** the corrector's
re-verification step re-extracts claims from the corrected text and picks the *first* one whose
citation (provision type + number + act) matches the originally-flagged claim's citation
(`pipeline.py`, `apply_selective_correction`, the `for c in reverify_claims: ... break` loop).
This document's first sentence — *"The case is governed by sections 406 and 420 of the Indian
Penal Code, 1860"* — cites Section 420 too, and appears **before** the actually-flagged sentence
in extraction order. Confirmed directly: re-running `claim_parser.extract_claims()` on the
(unchanged) corrected text shows two separate claim records both carrying citation
`{Section, 420, indian penal code 1860}` — one from the first sentence, one from the actually-
targeted sentence. The reverification logic re-verified the **wrong sentence** (the first
sentence's generic "governed by sections 406 and 420" listing, confidence 0.741 NEI) instead of
the flagged one. Because Qwen made no edit at all, this mismatch happens not to change the
*outcome* here (a no-op sentence re-verified against the same evidence still fails to reach
ENTAILED either way) — but the specific confidence number recorded for this "correction attempt"
(0.741) does not describe the sentence that was actually flagged and (nominally) corrected. This
is a **pre-existing bug in `apply_selective_correction`'s citation-matching, newly exposed here**
because natural documents routinely have multiple claim records sharing one citation identity — a
pattern the 59 two-claim synthetic cases never produce (each synthetic case has exactly one
corrupted claim and one unrelated true claim, never two claims citing the same section). Per the
brief, **claim extraction and the correction pipeline were not modified for this report**; this
is flagged as a finding for a future pass, not patched here.

### 8 summary

| doc | Qwen changed the flagged sentence? | outcome | why |
|---|---|---|---|
| 2004_632 | one-word spelling fix only | scope_violation | duplicate-claim-record artifact, not real scope creep |
| 2023_26 | no (byte-identical) | correction_failed | wrong-act evidence match (pre-existing bug); nothing coherent to correct |
| 2008_2648 | no (byte-identical) | correction_failed | re-verified the wrong (also-420-citing) sentence (pre-existing bug); moot since no edit was made anyway |

**In zero of the three cases did Qwen produce a substantive rewrite of the flagged sentence's
content.** This is qualitatively different from the synthetic run, where every trigger was a
deliberately, obviously corrupted statement (negated "shall", "may" flipped to "must", death
penalty changed to fine-only) that Qwen could straightforwardly revert toward the evidence text.
Natural low-confidence triggers are borderline, plausible-sounding claims — Qwen's greedy,
deterministic generation apparently has no strong signal for what to change, and in 2/3 cases
changed nothing.

---

## 9. Does the 72.2% synthetic correction success rate transfer to natural data?

**No — explicitly, on the evidence gathered here.** Natural correction success is 0/3 = 0%. But
this comparison must be stated carefully:

- **The sample is 3 attempts**, against synthetic's 36. A 0/3 result is statistically compatible
  with a "true" success rate anywhere from 0% up to a fairly wide upper bound — this is not
  enough data to estimate a natural-data success rate with any precision, only to observe that
  it did not succeed on the only 3 real opportunities that existed to test it.
- **The 3 triggers are not comparable in kind to the 36 synthetic triggers.** Every synthetic
  trigger was an artificial, extreme corruption with a clear "correct" target (the untouched
  canonical text). All 3 natural triggers here are borderline low-confidence NEI cases on claims
  that are plausible on their face, and 2 of the 3 are confounded by pre-existing parser/matcher
  bugs (wrong-act evidence, duplicate claim records) unrelated to premise framing. There is no
  clean natural analogue of "Qwen must revert an obvious corruption" in this data yet.
- **Qwen did not attempt a substantive correction in any of the 3 natural cases** (§8) — the
  0% figure mostly reflects "the corrector made no meaningful edit," not "the corrector tried and
  DeBERTa rejected a reasonable rewrite," which is a different failure mode than the synthetic
  run exhibited (where Qwen genuinely rewrote text and DeBERTa was often still unsatisfied).

**Conclusion: the 72.2% synthetic figure does not transfer, and no natural evidence supports
using it as an expectation for real-claim correction.** The honest summary is that this
prototype's correction path has, as of this report, **never shipped a single correction on real
NyayaRAG output** — 0/3 here, 0/0 in every prior natural evaluation (because bare framing never
triggered before).

---

## 10. Is labeled framing justified as the production default?

Restating the decision inputs precisely, separating what improved from what did not:

**In favour of labeled framing:**
- Controlled benchmark (rule-generated, not natural): macro F1 0.749 → 0.968.
- Synthetic GPU correction: 0/30 → 26/36 (72.2%) genuinely regenerated corrections shipped,
  clean safety numbers.
- On natural data, labeled framing is strictly safer or equal on every safety metric measured
  here: 0 unsafe shipments (both arms), and the one scope violation it produced was correctly
  caught, not silently shipped.
- Labeled framing does surface 3 additional correction opportunities on natural data that bare
  framing structurally cannot reach at all (bare has *never* triggered a natural correction, in
  any evaluation this project has run).

**Against, specifically from this report:**
- **Zero natural corrections have ever shipped, under either framing.** Labeled framing's only
  demonstrated natural-data advantage is *reaching* the corrector, not correcting anything
  successfully once there — 0/3 shipped.
- Labeled framing's ENTAILED gains on natural data (§5, 3/117 flips) are concentrated in a
  shallow-entailment pattern (multi-citation listing sentences), not claims that assert
  statutory content — a genuine precision concern for treating labeled ENTAILED as "verified,"
  independent of the correction question.
- This report surfaced a real, previously-latent pipeline bug (§8c) in the correction
  re-verification path that natural multi-citation documents expose and synthetic data never
  could. It was not fixed here (out of scope per the brief), but it means at least one of the
  three natural correction_failed outcomes is not a clean measurement.
- n=3 correction attempts is not enough evidence, in either direction, to characterize
  natural-data correction behavior at all.

**This report does not change `config/prototype.yaml`.** The default remains `bare`, per
instruction.

---

## 11. The 55.6% NO_EVIDENCE problem — explained separately, not as a verifier failure

65/117 pooled natural claims (55.6%, consistent with the previously reported 50/88 = 56.8% on
n=30 alone) have `NO_EVIDENCE` in **both** framing arms — identical counts, because evidence
matching runs once, before verification, and does not depend on `premise_framing` at all.
`format_premise()` is never even called for these claims; the verifier is never invoked. This is
**not a verifier-framing effect, and not something either bare or labeled framing could ever
fix**, because there is no premise-construction question for a claim the evidence matcher never
matched anything to.

Per `research_evaluation_final.md` §E–F and `mvp_assumption_evaluation.md` §5, this is a known,
separately-tracked combination of: (a) the evidence corpus covering only 59 usable IPC/
Constitution provisions, nowhere near the citations real NyayaRAG cases actually reference
(CrPC, other Acts, state law), and (b) `act_norm` extraction/matching fragility on real
multi-clause sentences. Nothing in this report adds to or changes that diagnosis; it is
reproduced here only to confirm it is unaffected by the framing ablation, consistent with prior
findings.

---

## 12. Test suite

- **Before this run** (`research/.venv`): 119 passed, 0 failed.
- **After GPU correction run**, same command: **119 passed, 0 failed.**

No regressions from `scripts/compare_premise_framing_natural.py` — it is a new, standalone
script under `scripts/`, imports only already-tested `src/` functions unchanged, and is not
itself under `tests/` (matching the synthetic comparison script's precedent).

---

## 13. Final summary

1. **Data** — 41 pooled document-runs (30 distinct underlying cases, 11 generated twice across
   two separate committed evaluation files) / 117 claims / 52 evidence-matched (44.4% coverage),
   reused verbatim from `run_B_n30.jsonl` and `run_natural_targeted.jsonl`. No new dataset, no
   regeneration.
2. **Verification, both arms genuinely re-run**: bare 0 CONTRADICTED / 0 ENTAILED / 52 NEI / 65
   NO_EVIDENCE; labeled 0 CONTRADICTED / 3 ENTAILED / 49 NEI / 65 NO_EVIDENCE. Validity gate:
   52/52 bare-arm reproduction of the committed record.
3. **Correction triggers**: bare 0/117 (as in every prior natural report); labeled 3/117, all via
   the `low_confidence` NEI downgrade, never a CONTRADICTED trigger.
4. **Correction, genuinely attempted on GPU**: 3/3 attempted, **0/3 shipped (0.0%)**, 2
   correction_failed, 1 correction_scope_violation, 0 unsafe shipments, 14/16 (87.5%)
   unflagged-claim preservation. Inspected sentence-by-sentence (§8): Qwen made **no substantive
   edit in any of the 3 cases** — one spelling fix (which alone caused the scope violation, via a
   pre-existing claim-duplication artifact) and two byte-identical no-ops.
5. **A previously-latent pipeline bug was found** (§8c): the correction re-verification step can
   re-verify the wrong claim when multiple claim records in a document share one citation
   identity — a pattern natural documents produce routinely and the synthetic set never does.
   Not fixed here, per the brief's scope.
6. **3 verdict flips total** (all NEI→ENTAILED, §5), all on shallow generic multi-citation
   "includes sections X, Y, Z" sentences, not content-bearing claims. No CONTRADICTED verdict
   occurred in either arm, so no false-positive contradiction is possible on this data (§6–7).
7. **The 72.2% synthetic correction-success figure does not transfer to natural data.** Natural
   success is 0/3, and — more informative than the raw ratio — the corrector essentially never
   attempted a real edit on any of the 3 real trigger cases it saw. Correction has, cumulatively
   across every evaluation this project has run, **never shipped once on real NyayaRAG output.**
8. **Safety held on natural data**: 0 unsafe shipments, the 1 scope violation was correctly
   caught and not shipped, 87.5% unflagged-claim preservation (the 2 failures are the same
   parser-duplication artifact behind the one scope violation, not independent incidents).
9. **The 55.6% NO_EVIDENCE rate is unaffected by framing** and is not attributable to the
   verifier or this ablation — it is evidence-corpus coverage and claim-extraction fragility,
   tracked separately since `research_evaluation_final.md`.
10. **Tests**: 119 passed / 0 failed before, 119 passed / 0 failed after.
11. **Production default**: not changed. `config/prototype.yaml` still defaults to `bare`.

### Recommendation

**C. INCONCLUSIVE — NEED LAWYER GROUND TRUTH** (specifically for the correction question; see
below for what *is* settled).

This is not a symmetric "not enough evidence either way." What this report settles:

- Labeled framing's **verification-only** natural-data behavior (§5–7, §11) is safe and mostly
  neutral — it unlocks 3 ENTAILED verdicts of a shallow kind, produces no new contradictions
  (there are none to produce), and does not touch the NO_EVIDENCE problem. Nothing here argues
  against labeled framing on safety grounds.
- What remains unsettled is the thing promotion actually turns on: **whether labeled framing's
  synthetic correction gain (72.2%) says anything useful about real correction quality.** This
  report's answer is that it does not — 0/3 shipped, and in 0/3 cases did the corrector even
  attempt a substantive fix — but n=3 is too small, and 2 of the 3 attempts are confounded by
  pre-existing parser/matcher bugs unrelated to framing, to conclude "labeled framing's
  correction path fails on natural data" as a general claim either. Both "promote" and "the
  correction path doesn't work naturally" are claims this data cannot support yet.
- No lawyer has reviewed any claim, correction, or verdict in this project. Every "ENTAILED",
  "correction_failed", and "scope_violation" label above is model behavior, not a legal-
  correctness judgment — that remains true whichever framing is used, and is the actual blocker
  on a confident A or B recommendation, exactly as `mvp_assumption_evaluation.md` §6 already
  flagged before this report existed.

**Recommended next step, in dependency order:** (1) fix the citation-matching bug in
`apply_selective_correction` found in §8c, since it corrupts any future correction-quality
measurement on multi-citation documents; (2) gather more natural correction triggers — either by
running labeled framing across a larger natural sample than 41 pooled document-runs, or by
lowering the sample-size ceiling on how much can be concluded from n=3; (3) lawyer review of
whatever corrections that larger run produces, since that is the only route from "DeBERTa says
ENTAILED" to an actual correctness claim.
