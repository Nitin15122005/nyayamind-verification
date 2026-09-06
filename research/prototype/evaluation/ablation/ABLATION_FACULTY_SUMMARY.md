# Ablation Analysis — Faculty Summary (STEP 7)

## 1. What changed from the original system?

Four configuration values changed on 2026-08-27: the evidence corpus (v0-only → v0+v1),
the NLI premise construction (bare statute text → labeled with its provision number),
the correction scope-check granularity (whole-sentence → per-citation spans), and the
re-verification hypothesis (whole sentence → narrower fragment, when safely available).
See `../PROVENANCE.md`'s STEP 0 pipeline map for exact code locations.

## 2. Which change has the strongest evidence of benefit?

**Premise framing**, on the 420-item controlled GOLD benchmark: macro F1 0.749→0.968,
McNemar p=4.2×10⁻²³, an independently-matching exact sign test p=1.58×10⁻³⁰. This is the
single strongest statistical result anywhere in this project. **Caveat**: this is a
curated benchmark with mechanically-constructed hypotheses, not real generated text.

**Evidence v1** is the strongest result specifically *on real natural data*: +7.1
percentage points evidence coverage on the 209-claim paired set, McNemar p=0.0003, zero
regressions (no claim ever lost evidence it previously had).

## 3. Which changes improve observed evidence coverage?

Only **evidence v1**. Coverage went from 63.2% to 70.3% on the 209-claim paired natural
set (fresh reproduction this step), with 15 claims gaining evidence and zero losing it.

## 4. Which change improves verifier benchmark performance?

**Premise framing** (see #2). No other lever changes verifier benchmark performance —
scope checking, narrow re-verification, and the confidence threshold all operate
downstream of, or independently from, the verifier's core benchmark accuracy.

## 5. Which changes only have diagnostic evidence?

**Atomic scope check** (1/11 real scope violations unblocked, no downstream shipping
verified), **narrow re-verification** (2/3 and 1/3 confidence-calibration shifts on
correction_failed cases, zero shipping-decision changes), and the **targeted correction
levers comparison** (0/5→1/10 shipped, isolated by design but far too small a sample).

## 6. Which results are based on small samples?

- Claim parser fix: n=30 cases.
- Atomic scope check: n=11 scope violations.
- Narrow re-verification: n=3 correction_failed cases.
- Correction levers (targeted): n=5 vs 10 triggers, 0 vs 1 shipped.
- Cumulative correction rate: n=56 attempts total, 1 shipped (1.8%) — not treated as a
  stable rate estimate anywhere in this analysis.

## 7. Which causal interactions remain untested?

**All of them.** No experiment in this project's history varies evidence-v1, premise
framing, atomic scope check, and narrow re-verification one at a time from a single
common baseline in one fresh, controlled run. Every "original vs. current" comparison is
assembled from a chain of separate experiments, each changing more than one lever at
once. No additive, multiplicative, or interaction effect between these four levers can
be inferred from the available data — this is stated explicitly, not glossed over.

## 8. What cannot be concluded from these experiments?

- That any lever improved **legal correctness** — no independent legal ground truth
  exists anywhere in this project (see STEP 0-1's audit).
- That the natural-data correction pipeline is "solved" — 1.8% cumulative shipping rate,
  n too small for any lever's individual contribution to shipping to be statistically
  supported.
- That the four current-production levers combine additively, multiplicatively, or in
  any specific way — this was never tested.
- That the premise-framing benchmark result transfers with the same magnitude to real
  generated text — the natural-data premise-framing evidence (147-claim subset) is real
  but smaller in scale and scope.

## What we can safely say

**STRONGLY SUPPORTED:**
- Premise framing (labeled) substantially improves verifier performance on the 420-item
  controlled GOLD benchmark.
- Evidence-v1 materially increases observed evidence coverage on real natural claims,
  with zero regressions.

**DESCRIPTIVELY SUPPORTED:**
- The parser fix (commit 223eb9d) increased per-case evidence-matched counts on a 30-case
  batch with no case worsened.
- The production confidence threshold (0.70) sits in a flat, non-fragile region of the
  benchmark's sensitivity curve — not proven optimal, but not fragile either.
- Premise framing also improves natural-data verification decisiveness on a smaller
  (147-claim) real subset.

**DIAGNOSTIC ONLY:**
- Atomic scope check changed scope-gate behavior (1/11 unblocked) — does not establish
  safe or successful downstream correction shipping.
- Narrow re-verification changed confidence calibration on 3 cases — zero shipping
  outcomes changed.
- The targeted correction-levers comparison (0/5→1/10 shipped) is directionally
  suggestive but not statistically supported.

**NOT YET ISOLATED:**
- Any interaction or combined effect among the four current production levers.
- The individual, standalone contribution of narrow re-verification apart from the other
  three levers already being active in every experiment that touches it.
