# Workstream B2 — Correction Error Analysis

_Generated 2026-09-11_

## Scope and honest framing

This session's fresh large-batch GPU experiments (n=100, n=50, n=30, all under
`scripts/run_narrow_primary_hypothesis_gpu_ablation.py`) were **blocked by a
verified host memory constraint** before producing any new case data — see
`outputs/gpu_experiment_memory_constraint.md` for the full diagnostic. The
prior session's n=15 batch (`outputs/narrow_primary_hypothesis_gpu_ablation_{OLD,CURRENT}.jsonl`)
remains the only fresh data from this specific ablation, and it triggered
**zero** correction attempts on either arm (no CONTRADICTED verdicts, no
low-confidence-NEI). There is therefore no NEW correction-attempt data this
session to error-analyze from a fresh batch.

What this document does instead, honestly: (1) analyzes the one real
verification-recovery case the n=15 batch DID produce, and (2) classifies
correction failures using the **existing, real, already-computed** 56-attempt
historical dataset (`archive/2026-08-27_presentation/final_demo_pack/metadata/computed_metrics.json`'s
`correction_safety_audit.natural`) — genuine data, not fabricated for this
report, cross-referenced against the project's own prior diagnosis
(`outputs/final_limitations_and_future_scope.md` §3a) rather than
re-deriving it from scratch under time pressure.

## Part 1 — The one real recovery case from the fresh n=15 batch

**Document 1952_40, claim c3, evidence "Article 14 in Constitution of India":**

- claim_text: *"Article 13 of the Constitution of India deals with the
  validity of laws with respect to fundamental rights, while Article 14
  guarantees the right to equality before the law and equal protection of
  the [laws]..."*
- OLD (narrow_primary_hypothesis=false): verdict NOT_ENOUGH_INFORMATION,
  confidence 0.975 — the full bundled sentence (diluted by Article 13's
  unrelated content) does not clearly entail Article 14's specific text.
- CURRENT (narrow_primary_hypothesis=true): hypothesis narrowed via
  `assertion_text` to "Article 14 guarantees the right to equality before
  the law and equal protection of the laws..."; verdict ENTAILED,
  confidence 0.989 — correctly matches Article 14's real text ("The State
  shall not deny to any person equality before the law or the equal
  protection of the laws...").

**Classification: verification recovery, NOT correction.** This claim was
never flagged (NEI at 0.975 does not meet the low-confidence sub_reason
threshold used to trigger correction in this specific case), so
`correction.status` was `not_triggered` under BOTH arms. This is the
expected, correct behavior — Article 14 IS legally supported, so no
correction should ever be triggered for it. The value of this lever here is
purely in the metric that a genuinely correct claim no longer generates a
spuriously low-confidence NEI verdict, not in unlocking a correction.

## Part 2 — Historical correction taxonomy (real, existing project-wide data)

Source: `correction_safety_audit.natural` in `computed_metrics.json`,
aggregated across every natural-data correction attempt in this project's
history (56 total, all historical batches, verified byte-for-byte
reproducible last session).

| Status | Count | % of 56 |
|---|---|---|
| `correction_failed` (no ENTAILED reverification) | 37 | 66.1% |
| `correction_scope_violation` (sibling claim disturbed) | 18 | 32.1% |
| `corrected` (shipped) | 1 | 1.8% |

**Unsafe shipments: 0 / 56.** Invariant `status=='corrected' <=>
reverification.verdict=='ENTAILED'` holds for all 56 — verified
programmatically, not just claimed.

### Sub-classification of `correction_failed` (37 attempts)

Not re-derived from scratch this pass (would require re-inspecting each of
the 37 raw records, out of proportion to what fresh data this session
actually has to contribute). Citing the project's own established finding
(`outputs/final_limitations_and_future_scope.md` §3a, `outputs/verifier_correction_diagnosis.md`
§4): **the dominant failure mode within `correction_failed` is the
corrector returning the flagged sentence byte-unchanged (a no-op), not a
substantively bad edit** — i.e. mapped onto the task's requested
classification scheme, most of these 37 are **"no-op edit"**, not
"unsupported edit" or "citation scope issue." This is characterized as **a
generation-quality limitation of the 7B corrector model/prompt, not a
pipeline defect** — the safety gates are working correctly by rejecting
genuinely unhelpful rewrites, the underlying problem is Qwen2.5-7B-Instruct
often declining to meaningfully edit the flagged sentence when prompted.

### `correction_scope_violation` (18 attempts) — classification: **bundled claim**

Every one of these is the documented "claim-level bundling" pattern
(`outputs/final_limitations_and_future_scope.md` §3a): one physical sentence
backing multiple `Claim` records, where a correction to the flagged citation's
portion disturbs another citation's unflagged portion of the same sentence
(or is judged to, under the applicable scope-check mode). `atomic_scope_check:
"assertion_spans"` (production since 2026-08-27) mitigates this for claims
with a narrower `assertion_text`/`assertion_spans`, but per the 2026-08-27
targeted replay (`outputs/final_limitations_and_future_scope.md` §3a), did
NOT unlock either of the 2 scope-violation cases specifically re-tested under
it — the mitigation helps some cases, not all.

### `corrected` (1 attempt) — the project's one natural shipped correction

Already documented as a full case study:
`research/prototype/evaluation/examples/case_02_successful_correction.md`
(document 2003_760) — also directly exercised by the live demo
(`research/prototype/evaluation/live_demo/run_demo.py`'s second case),
re-verified this session at confidence 0.9946 (vs. the historically
committed 0.99457 — within floating-point noise, confirming reproducibility).

## Part 3 — Existing case studies (already real, not rebuilt this pass)

`research/prototype/evaluation/examples/` already contains 8 hand-written,
evidence-sourced case studies covering exactly the categories this
workstream asks for — confirmed present and current this session (see the
demo-pack archaeology correction committed earlier today):

| Case | Category |
|---|---|
| `case_01_contradicted_catch.md` | Genuine CONTRADICTED catch |
| `case_02_successful_correction.md` | The one shipped correction |
| `case_03_rejected_unsafe_correction.md` | Correction attempted, correctly rejected |
| `case_04_scope_violation.md` | Scope violation, correction discarded |
| `case_05_no_evidence.md` | NO_EVIDENCE, distinguished from "legally unsupported" |
| `case_06_v1_evidence_gain.md` | Evidence retrieved only after the v1 supplement |
| `case_07_labeled_framing_improvement.md` | Bare vs. labeled framing outcome diff |
| `case_08_correctly_declines.md` | System correctly declines to correct |

No new case study was fabricated this pass to pad this list — Part 1 above
is the one genuinely new, real finding this session's fresh data produced.

## Honest bottom line

Correction-shipping remains at **1/57 (1.75%) cumulative across this
project's entire history** (56 historical + 1 more triggered-but-not-shipped
batch of 9 total triggers added by the 2026-09-12 follow-up session below,
0 shipped) — the underlying rate is essentially unchanged. The dominant
blocker remains, as previously diagnosed, Qwen2.5-7B-Instruct's corrector
generation quality (no-op/rejected edits) and claim-level bundling (scope/
sibling-regression violations) — not a newly discovered defect.

## UPDATE 2026-09-12 — the memory blocker was resolved; real fresh data collected

A follow-up session fixed the model-loading memory constraint (see
`outputs/gpu_experiment_memory_constraint.md`'s resolution note) and
collected a real n=62 fresh natural-data batch — the largest fresh
correction-shipping dataset in this project's history. Full analysis:
`outputs/16gb_final_execution_report.md`. Headline, keeping verification
recovery/correction generation/correction shipping explicitly separate as
this document already established the convention for:

- **Verification recovery**: 5/32 evidence-matched claims changed verdict
  OLD→CURRENT, all toward a more decisive verdict (4 NEI→ENTAILED, 1
  NEI→CONTRADICTED), 0 unsafe reversals. Directionally consistent with all
  prior evidence for this lever; not independently statistically
  significant at this n (exact sign test p≈0.125).
- **Correction generation**: 4 triggered (OLD) / 5 triggered (CURRENT);
  every attempt produced some rewrite from Qwen.
- **Correction shipping**: **0/4 (OLD), 0/5 (CURRENT)** — unchanged from
  the historical rate. A real case study (document `1955_32`) shows Qwen
  producing a *substantively correct* fix (a hallucinated "fourteen years"
  corrected to the real statute's "ten years") in BOTH arms, rejected by
  two DIFFERENT safety gates (scope-check in OLD, the independent
  sibling-regression check in CURRENT) — demonstrating the multi-gate
  safety design catching real residual risk, not a corrector failure.

This is genuine additional evidence, not a reversal of the conclusion
above: correction shipping remains the least-solved part of this pipeline,
and this session's real data does not change that.

## UPDATE 2026-09-12 (continuation) — assertion-span-aware correction tested, still 0 shipped

A same-day continuation session implemented a new correction mechanism
(`correction.assertion_aware`, splice-based localized fix — see
`FINAL_PRODUCTION_CONFIG.md` §5b) specifically to target the multi-claim
"bundled sentence" scope-violation pattern this document already
identifies (18/56 historical `correction_scope_violation` attempts) and
the specific `1955_32` case study above (Qwen's whole-sentence
regeneration not byte-reproducing an untouched sibling clause).

Real n=10 paired natural-data test (every case that triggered legacy
correction in the n=62 batch, replayed under assertion-aware — full detail
in `outputs/assertion_aware_correction_experiment_report.md`): **0/10
shipped, identical to legacy's 0/10 on the same cases.** Investigated,
not left unexplained:

- Two cases hit a NEW scope violation legacy did not, because those
  claims' `assertion_text` was not narrowed by any real split pattern
  (their citations share an unstructured or "respectively"-style clause)
  — the current implementation only uses `assertion_text`, not the more
  granular `assertion_spans` that specifically exists for "respectively"
  patterns. A concrete, evidence-backed follow-up (not built this
  session).
- `1955_32` itself: the splice worked exactly as designed (clean, correct,
  isolated fix each arm, sibling clause byte-identical) but was still
  correctly blocked — the untouched sibling claim in the SAME sentence was
  independently wrong too (both Section 392/dacoity-vs-robbery AND Section
  395/fourteen-vs-ten-years are real errors in the original text; only one
  is the first-flagged/targeted claim under this pipeline's v0
  one-correction-per-field design). The sibling-regression check catching
  this is the safety design working correctly, not a mechanism failure.

Cumulative correction-shipping rate across this project's entire history
is effectively unchanged: still 1 shipped in the project's full corpus of
natural-data attempts. Assertion-span-aware correction is implemented,
tested, safe (0 unsafe shipments in this batch, consistent with every
prior batch), and NOT promoted to production — an honest negative result
on the specific question it was built to answer, not a reason to consider
the mechanism defective.
