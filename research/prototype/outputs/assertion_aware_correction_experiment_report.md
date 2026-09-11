# Assertion-aware vs legacy correction: paired natural-data comparison

_Generated 2026-09-11T21:25:25.360046+00:00_

Both mechanisms attempted on the EXACT SAME (document_id, arm, flagged claim) triples -- the 5 document_ids that triggered LEGACY correction in the committed n=62 batch (outputs/16gb_final_execution_report.md). LEGACY figures are READ from that already-committed experiment, not recomputed; ASSERTION-AWARE figures are freshly collected by this script, real Qwen2.5-7B + real DeBERTa, through the actual production pipeline.py code.

**n = 10 paired correction attempts** (5 documents x up to 2 arms each, exactly matching how many triggered a legacy attempt).

## Headline

| Mechanism | Shipped |
|---|---|
| LEGACY (whole-sentence regeneration) | 0/10 |
| ASSERTION-AWARE (splice-based) | 0/10 |

## Per-case detail

| Document | Arm | Legacy status | Assertion-aware status | Legacy shipped | Assertion-aware shipped |
|---|---|---|---|---|---|
| 1953_1 | OLD | correction_failed | correction_failed | no | no |
| 1953_10 | OLD | correction_failed | correction_scope_violation | no | no |
| 1953_96 | OLD | correction_scope_violation | correction_scope_violation | no | no |
| 1955_16 | OLD | not_triggered | not_triggered | no | no |
| 1955_32 | OLD | correction_scope_violation | correction_sibling_regression | no | no |
| 1953_1 | CURRENT | correction_failed | correction_failed | no | no |
| 1953_10 | CURRENT | correction_failed | correction_scope_violation | no | no |
| 1953_96 | CURRENT | correction_scope_violation | correction_scope_violation | no | no |
| 1955_16 | CURRENT | correction_failed | correction_scope_violation | no | no |
| 1955_32 | CURRENT | correction_sibling_regression | correction_sibling_regression | no | no |

## Honest interpretation

At n=10, this is NOT a statistically powered comparison -- it is a targeted, paired replay of every case that actually reached the correction-triggering step in the project's largest fresh correction-shipping batch to date. Any difference above is real (not fabricated, not cherry-picked -- every triggered case from that batch is included), but must not be reported as statistically established at this sample size.

**The honest headline: assertion-aware correction did NOT ship any additional
corrections on this real batch (0/10, same as legacy).** This is a genuine
negative/null result for correction-SHIPPING specifically, investigated
case-by-case below rather than left unexplained. It does not mean the
mechanism is broken — every rejection is a real, understood safety-gate
catch, and 0 unsafe corrections shipped under either mechanism, same as
every batch in this project's history — but the specific hypothesis that
motivated this work (that splicing would unlock the real `1955_32` case)
was tested directly and did NOT pan out, for a genuine, now-understood
reason. Reported plainly rather than reframed as a win.

### Case-by-case mechanistic analysis (real data, not speculation)

**1953_1 (both arms), 1953_96 (both arms)**: assertion-aware produced the
IDENTICAL outcome as legacy (`correction_failed`, `correction_scope_violation`
respectively). For 1953_1, the target claim's `assertion_text` WAS
successfully narrowed by a real split pattern (a citation-keyword-boundary
clause about "Section 148"), so the splice mechanism worked exactly as
designed and isolated the edit correctly — but Qwen's own corrected
fragment still did not produce a claim that re-verified as ENTAILED. This
is the same generation-quality limitation already documented as the
dominant historical failure mode (`outputs/workstream_b2_correction_error_analysis.md`)
— a corrector-model limitation, not a splice-mechanism defect; isolating
the edit more precisely cannot fix an edit that is itself inadequate.

**1953_10 (both arms), 1955_16 (CURRENT)**: assertion-aware produced a NEW
`correction_scope_violation` that legacy did not have (legacy: `correction_failed`
for both). Root cause, confirmed by inspecting the raw records
(`outputs/assertion_aware_correction_experiment_{OLD,CURRENT}.jsonl`): in
both cases, the flagged claim's `assertion_text` was NOT narrowed by any of
`_assign_assertion_texts()`'s split patterns (no semicolon / " while " /
citation-keyword-boundary / parenthetical-gloss applied), because the
sentence bundles multiple citations in an unstructured way a plain
listing ("specifically Sections 302 and 149") or a "respectively" sentence
where the SHARED intro clause itself (not the narrower per-citation
description that `assertion_spans` — not `assertion_text` — captures) is
what several claims fall back to as their `assertion_text`. In this shape,
`assertion_text` for the flagged claim is IDENTICAL to (fully overlaps) an
unflagged sibling's own `assertion_text` — so splicing "only the flagged
claim's assertion_text" is structurally equivalent to editing the whole
shared clause both claims depend on, providing NO additional isolation
over the legacy path. Qwen's own fragment output for 1953_10 also dropped
"and 149" entirely (a real generation defect, not a splice bug) — the
scope check correctly caught this rather than shipping a claim whose
sibling's own required citation had silently vanished.

**Design implication, stated honestly, not fixed this session**: the
current assertion-aware implementation uses only `assertion_text`, never
the more granular `assertion_spans` (which specifically exists for
"respectively" patterns — see `claim_parser.py`'s `_assign_respectively_spans`).
Extending assertion-aware correction to splice at the `assertion_spans`
level for "respectively" claims is a natural next step this data motivates
— NOT implemented here, since it would need its own design/safety-gate
work and this session's time was bounded; recorded as a concrete, evidence-
backed follow-up rather than attempted speculatively.

**1955_32 (both arms) — the case that specifically motivated this
mechanism**: the splice worked EXACTLY as designed here. `_assign_assertion_texts()`'s
" while " split correctly narrowed each claim to its own clause
("Section 392 defines the act of dacoity" vs "Section 395 prescribes the
punishment for..."), Qwen's fragment output was a clean, targeted, correct
fix each time (OLD arm: "dacoity"→"robbery" for Section 392, matching the
real statute; CURRENT arm: "fourteen years"→"ten years" for Section 395,
also matching the real statute), and the splice left the sibling clause's
own TEXT completely byte-identical, confirmed directly in the raw record.
**But it still did not ship** — the UNCONDITIONAL sibling-regression check
(run specifically because this project's own convention is to verify a
structural guarantee, not just trust it — see
`apply_selective_correction_assertion_aware`'s docstring) caught that the
UNTOUCHED sibling claim, when independently re-verified against its own
evidence using its own full sentence, now returns CONTRADICTED — because
that sibling's own claim was ALSO wrong (in the OLD arm, the untouched
"fourteen years" claim; in the CURRENT arm, the untouched "dacoity" claim
for Section 392, which is in fact the WRONG term — the real crime being
defined is robbery, not dacoity). Under the ORIGINAL (pre-correction)
verification, this second error had NOT been flagged as CONTRADICTED for
that arm (it was the OTHER claim that got flagged first, and per this
pipeline's v0 design, only the FIRST flagged claim per field triggers a
correction attempt) — so this genuinely is a case of TWO independent
errors in one bundled sentence, only one of which was targeted. Editing
one correctly does not make the sentence as a whole EVIDENCE-CONSISTENT,
and the sibling-regression check is doing exactly its documented job by
refusing to ship a "fix" that leaves a second, independently-wrong claim
standing in the same output text. **This is a genuine, positive finding
about the safety design, not a mechanism failure**: it demonstrates the
sibling-regression check catches a real, substantive additional error that
a naive "only check what I touched" design would have shipped past.

### What this means for the assertion-aware mechanism's status

- **Implementation correctness**: confirmed both by the controlled
  benchmark (`outputs/assertion_aware_correction_controlled_benchmark.md`)
  and by this real batch — the splice behaves exactly as designed when a
  narrowing split pattern is available, fails closed correctly when it
  isn't, and 0 unsafe corrections shipped (same as every historical
  batch). The mechanism does what it claims.
- **Correction-shipping improvement**: NOT demonstrated at this sample
  size (n=10) — 0/10 either way. The one case that structurally could have
  benefited (1955_32) was blocked by a SEPARATE, genuine issue (a second
  independent error in the same bundled sentence), not by the mechanism
  under test.
- **Decision**: `correction.assertion_aware` remains `false` in production
  (EXPERIMENTAL, not promoted) — see `FINAL_PRODUCTION_CONFIG.md` §5b for
  the full decision record. This is not a rejection either: the mechanism
  is real, tested, and available for further evaluation: it is simply not
  yet evidenced to move the shipping-rate needle at the sample sizes this
  16GB machine can currently produce.
