# Headline Results (STEP 8)

Only the strongest, most defensible results from STEP 4-7, consolidated here unchanged.
Every number below was verified against its source artifact by `build_step8_consolidation.py`
before this document was written (see `CONSOLIDATION_SOURCE_MAP.md`).

## A. Evidence coverage (209 paired natural claims)

| | v0-only | v0+v1 |
|---|---|---|
| Coverage | 63.2% | 70.3% |
| Gained / Lost / Unchanged | — | gained=15, lost=0, unchanged=194 |

McNemar χ²=13.0667, p=0.000301. Exact sign test p=6.10e-05.
**Classification: SUPPORTED.**

## B. Controlled verifier (GOLD-01, N=420)

| | Bare | Labeled |
|---|---|---|
| Accuracy | 0.7333 | 0.9714 |
| Macro F1 | 0.7487 | 0.9684 |

McNemar χ²=98.01, p=4.16e-23. Exact sign test p=1.5777e-30.
**Classification: SUPPORTED.**

## C. Claim parser (N=30)

6 improved, 0 worsened, 24 unchanged. Exact sign test p=0.03125.
**Classification: SUPPORTED / HISTORICAL REPRODUCTION** (the underlying parser-code
change itself cannot be re-executed without checking out old source; the statistical
test was freshly recomputed from the raw historical per-case data).

## D. Natural 588-claim aggregate (N=588)

Evidence coverage: 66.3% (390/588).

Observed verdict distribution: NEI=364, NO_EVIDENCE=198, ENTAILED=21, CONTRADICTED=5.

**This is descriptive natural-data behavior — not accuracy or F1.** No independent
label exists for any of these 588 claims; these are raw observed verifier-outcome
counts on real, previously-generated text.

## E. Correction

- Targeted: 0/5 → 1/10 shipped.
- Cumulative (project history): 1/56 = 1.8%.
- Unsafe: 0.

**Classification: DIAGNOSTIC / UNDERPOWERED.** Neither the targeted nor the cumulative
figure supports a statistical claim at this sample size.

## F. Safety

**0 unsafe corrections observed** across every correction attempt tested in this
project's history (56 natural + 66 synthetic = 122 total attempts).

This is reported as an observed count, not a probabilistic guarantee: **0 unsafe
corrections observed in the tested correction history** does not mean unsafe
corrections are impossible — it means none occurred in the cases actually tested.
