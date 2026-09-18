# SLIDE GUIDE — NyayaMind ORIGINAL vs LATEST

A ready-to-present 14-slide deck built only from assets in this package. Every slide names the
exact file to drop in and the one sentence that must be said with it.

**The three things that must survive contact with an audience:**

1. The models never changed — every difference is a system/pipeline/configuration change.
2. "ORIGINAL" means two different things in this project, and they are not interchangeable.
3. The headline verifier number is 99% a benchmark-construction effect, and the deck says so
   out loud rather than being caught out in questions.

---

## Slide 1 — Title

> **NyayaMind: statutory-claim verification and selective correction**
> From the original prototype to the current system — what changed, and what the evidence shows

Nothing else. No numbers on the title slide.

---

## Slide 2 — The problem

**Say:** LLMs asked to summarise Indian judgments name statutes that sound plausible but are
wrong. We built a deterministic, auditable layer that checks one specific field — Statutory
Grounding — and selectively corrects it.

**Asset:** none, or `diagrams/12_data_flow/D12_data_flow.png`.

---

## Slide 3 — The original system, and why it needed work

**Asset:** `diagrams/01_original_architecture/D01_original_architecture.png`

**Say:** This is the original prototype, commit `0e37525`. It ran end to end. On 30 real cases it
resolved 38 of 88 claims to evidence, returned NEI for **every single one**, and triggered
**zero** corrections. The system worked mechanically and did nothing useful.

*This is the strongest framing available — the problem statement is measured, not asserted.*

---

## Slide 4 — Three concrete flaws

**Asset:** `diagrams/14_flaw_fix_behavior/D14_flaw_fix_behavior.png` (top three rows)

**Say:** The NLI premise never named the provision the claim was about; the evidence pool was too
small; the parser could not normalise real Indian citation forms.

---

## Slide 5 — What we changed

**Asset:** `diagrams/03_side_by_side/D03_original_vs_latest_side_by_side.png`

**Say — verbatim, this is the load-bearing sentence:** *The models never changed. Same
Qwen2.5-7B-Instruct, same DeBERTa NLI checkpoint. Every difference you are about to see is a
pipeline or configuration change.*

---

## Slide 6 — The current pipeline

**Asset:** `diagrams/04_end_to_end_pipeline/D04_complete_latest_pipeline.png`

**Say:** 26 stages. Corrected text ships in exactly one case — every gate passed **and**
re-verification returns ENTAILED. Everything else ships the original text with a recorded reason.

---

## Slide 7 — Headline results

**Asset:** `figures/01_overview/F01_headline_original_vs_latest.png`

**Say:** Five independent experiments, each with its own lever and denominator.

**Do NOT say:** "the system improved by X%". The panels are not averageable, and the figure's own
footnote says so.

---

## Slide 8 — Verifier result

**Asset:** `figures/02_verifier/F03_verifier_accuracy_macro_f1.png`

**Say:** On 420 gold-labelled items, macro F1 0.749 → 0.968, 100 items fixed and **zero broken**,
McNemar exact p ≈ 1.6e-30. Regenerated from scratch for this deck and it reproduced the historical
numbers exactly on a completely different software stack.

---

## Slide 9 — …and the caveat, stated by us first

**Asset:** `figures/02_verifier/F11_gold01_stratified_by_condition.png`

**Say:** 99 of those 100 fixed items are in benchmark conditions where the original premise was
*constructed* to omit the identifier the claim asserts. On the other 269 items the two arms are
statistically identical. So this evidences a **fixed premise/hypothesis mismatch**, not better
legal reasoning.

**Then immediately:** It still matters — real generated claims *are* overwhelmingly attributed, so
those are the realistic conditions. And it is not a threshold artifact either (next slide).

*Putting this slide in yourself is worth more than any result on slide 8. It is the difference
between a reviewer trusting the rest of the deck and not.*

---

## Slide 10 — Not a threshold artifact

**Asset:** `figures/02_verifier/F09_threshold_sensitivity.png`

**Say:** Across every confidence threshold from 0.34 to 0.99 the labelled framing leads, and the
production 0.70 sits on a flat plateau. The result does not depend on a tuned threshold.

---

## Slide 11 — Parser and evidence

**Assets:** `figures/04_parser/F14_parser_progression.png` and
`figures/03_evidence_retrieval/F12_evidence_pool_composition.png`

**Say:** We re-executed the *original parser source* straight out of git against the current one on
identical text: claims resolving to evidence 38 → 57, ten documents improved, none worsened,
p = 0.002. The evidence pool went from 59 records over 10 Acts to 136 over 22.

**Careful:** "resolving to evidence" is coverage, **not** correctness — there are no gold labels
for claim extraction.

---

## Slide 12 — Safety

**Assets:** `diagrams/10_safety/D10_safety_gate_chain.png`, then
`figures/07_safety/F22_safety_zero_event_outcomes.png`

**Say:** One safety gate became a fail-closed chain. Zero unsafe corrections shipped in 56
attempts — but that is a zero-event result over a small denominator: the 95% upper bound on the
true rate is about 5.2%, and most gates are evidenced by regression tests, not by measured harm.

---

## Slide 13 — What did *not* work

**Assets:** `figures/06_correction/F21_assertion_aware_null_result.png` and
`figures/06_correction/F18_synthetic_vs_natural_transfer_gap.png`

**Say:** Assertion-aware correction ships 0/10 — exactly as many as the legacy path. The narrow
hypothesis lever does nothing at all on the gold contradiction set. And correction ships 72% of
the time on synthetic contradictions but 1.8% on real text. The correction subsystem is the weak
link and we are not hiding it.

*Expect this to be the best-received slide in the deck.*

---

## Slide 14 — Limitations and what is next

**Asset:** `tables/limitations/T16_limitations.md` (top 5 rows)

**Say:** No lawyer-validated ground truth exists anywhere in this project. Correction evidence is
thin and could not be rerun here for want of a GPU. No joint multi-lever experiment exists, so we
claim no additive effects. Next: a lawyer-validated subset, and a larger correction batch.

---

## Backup slides (have these ready, do not present them)

| Question you will get | Slide to have ready |
|---|---|
| "Show me the confusion matrices" | `figures/02_verifier/F07_confusion_original.png`, `F08_confusion_latest.png` |
| "What about per-class performance?" | `figures/02_verifier/F04/F05/F06_*` |
| "Why not BM25 or embeddings?" | `figures/03_evidence_retrieval/F19_retrieval_method_safety.png` |
| "Did evidence coverage help on real data?" | `figures/03_evidence_retrieval/F13_evidence_coverage_209_paired.png` |
| "What changed in the verdicts?" | `figures/05_verdict/F16_verdict_distribution_209_paired.png` |
| "How many changes were there in total?" | `CHANGE_IMPACT_AUDIT.md` summary table — 47, of which 29 promoted |
| "Can I trace this number?" | `validation/metric_traceability.csv` — 49 metrics, full provenance |
| "Is any of this reproducible?" | `tables/reproducibility/T14_reproducibility_status.md` |

---

## Language rules for the talk

**Never say:** lawyer-validated · guaranteed legally correct · production-ready ·
"the system is 97% accurate" · any accuracy/precision/recall figure about natural data.

**Always say:** "NLI agreement against audited statute text", not "legal correctness" ·
"coverage", not "accuracy", for anything parser- or retrieval-side · "n = …" with every number ·
"single-lever" whenever you quote a lever's effect.

**If asked "so is it better?"** — *Measurably better at finding and checking statutory claims.
Not demonstrably better at fixing them: correction still ships about 2% of the time, and the two
mechanisms we built to improve that both returned null.*
