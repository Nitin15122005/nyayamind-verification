# Statistical Results (STEP 8)

Machine-readable source: `STATISTICAL_RESULTS.csv`, generated directly from
`ABLATION_SUMMARY.json`'s findings that carry a `p_value` — no additional significance
test was performed or invented in this step.

## 1. Evidence v0 vs. v1

- **Hypothesis**: the evidence-pool change has no effect on the rate of finding usable
  evidence (b=c).
- **Dataset**: 209-claim paired natural evaluation. **N=209, paired.**
- **Test**: McNemar (continuity-corrected). **Statistic**: χ²=13.0667. **p=0.000301.**
- **Exact test**: two-sided sign test, p=6.10e-05 (independent confirmation).
- **Effect/change**: +7.1 percentage points (63.2%→70.3%), 15 gained / 0 lost.
- **Interpretation**: evidence-v1 materially increased observed evidence coverage on
  the paired natural evaluation.
- **Multiple-comparison status**: not applied — single, pre-specified comparison,
  reproducing this project's own existing methodology.
- **Status**: confirmatory (not exploratory) — this exact comparison was the
  project's own pre-registered rationale for shipping `use_evidence_v1=true`.

## 2. Premise framing, bare vs. labeled

- **Hypothesis**: premise framing has no effect on whether a controlled-benchmark item
  is correctly classified (b=c).
- **Dataset**: GOLD-01 controlled verifier benchmark. **N=420, paired.**
- **Test**: McNemar. **Statistic**: χ²=98.01. **p=4.16e-23.**
- **Exact test**: two-sided sign test, p=1.5777e-30 (independent confirmation, exactly
  matching `final_comparison/tables/statistical_tests.csv`'s independently-computed
  1.58e-30).
- **Effect/change**: macro F1 0.7487→0.9684, accuracy 0.7333→0.9714.
- **Interpretation**: labeled framing substantially improves verifier performance on
  the controlled GOLD benchmark.
- **Multiple-comparison status**: not applied — single, pre-specified comparison.
- **Status**: confirmatory.

## 3. Claim parser, pre/post commit 223eb9d

- **Hypothesis**: the parser change is equally likely to improve or worsen a case's
  evidence-match count (p=0.5 each direction).
- **Dataset**: n=30 reparse (same 30 texts, old vs. new parser). **N=30, paired at the
  document level** (claim segmentation itself changes between versions, so this is not
  a strict per-claim pairing — explicitly noted, per `final_comparison`'s own caveat).
- **Test**: exact two-sided sign test on the 6 non-tied pairs. **p=0.03125.**
- **Effect/change**: 6/30 improved, 0/30 worsened, 24/30 unchanged.
- **Interpretation**: the parser fix increased per-case evidence-matched counts with
  zero cases worsened, on this batch.
- **Multiple-comparison status**: not applied — single, pre-specified comparison.
- **Status**: HISTORICAL REPRODUCTION / NOT FRESH for the underlying parser change
  itself; the statistical test was freshly, independently recomputed.

## What is deliberately excluded from this table

Atomic scope check (n=11), narrow re-verification (n=3), and the targeted correction
levers comparison (n=5 vs 10) are **not included here** because no statistical test was
performed for them — their sample sizes were judged too small to support one, and this
step does not invent a test merely because a comparison exists (per this step's
explicit rule). See `EVIDENCE_STRENGTH_MATRIX.md` for how those are graded instead
(all C — diagnostic/provisional).

## Exploratory vs. confirmatory

All three tests above are confirmatory: each reproduces a comparison this project's own
prior methodology had already pre-specified (evidence-v1's promotion decision, the
premise-framing decision, and the parser-fix commit's own validation), not a new
post-hoc hypothesis invented during this consolidation. No correction for multiple
comparisons was applied because each is evaluated as its own single, independent
question, exactly as the source experiments originally treated them.
