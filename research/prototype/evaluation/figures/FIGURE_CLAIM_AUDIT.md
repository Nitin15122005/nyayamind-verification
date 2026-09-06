# Figure Claim Audit (STEP 9, Phase 12)

For every figure: what it demonstrates, what it does not, its dataset class, its
fresh/historical status, whether a causal claim appears, and whether any displayed
statistical significance is justified by the underlying test. **The answer to Q8 is
"YES" for every displayed p-value** — verified below individually.

## Figure 01

1. **Demonstrates:** Magnitude of change, original→current, across 4 distinct metrics.
2. **Does NOT demonstrate:** That these 4 metrics measure the same thing, or that natural coverage equals verifier accuracy.
3. **Dataset:** Mixed — natural metric-only (evidence coverage) + GOLD (macro F1, accuracy, contradiction recall).
4. **Fresh or historical:** Fresh (all 4 values computed in STEP 4/6).
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No (this figure shows magnitudes only; p-values live in Figures 02/08).
8. **If yes, supported:** N/A.

## Figure 02

1. **Demonstrates:** Observed evidence-coverage change on paired real claims, with the paired statistical test.
2. **Does NOT demonstrate:** Accuracy, correctness, or that the evidence found is legally valid.
3. **Dataset:** Natural, metric-only.
4. **Fresh or historical:** Fresh (STEP 6, reproduced and cross-checked in STEP 7/8).
5. **Causal claim:** Implicit ("evidence-v1 increased coverage") — a coverage-mechanism claim, not a legal-correctness claim.
6. **If yes, justified:** Yes — the McNemar test directly measures the paired effect of the evidence-pool change under a controlled comparison (same claims, only the pool differs); see `ABLATION_INVENTORY.md`'s isolation note.
7. **Statistical significance shown:** Yes — McNemar p=0.000301.
8. **If yes, supported:** **YES** — this exact p-value was computed from the real paired contingency table (b=15, c=0) in STEP 6 and independently re-derived in STEP 7/8 with an exact sign test (p=6.10e-05) confirming the same direction.

## Figure 03

1. **Demonstrates:** Distribution of verifier verdicts on 588 real claims.
2. **Does NOT demonstrate:** Correctness of any individual verdict.
3. **Dataset:** Natural, metric-only, descriptive.
4. **Fresh or historical:** Fresh (STEP 6).
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Figure 04

1. **Demonstrates:** Correction funnel stage counts, 5 populations, kept separate.
2. **Does NOT demonstrate:** A combined or comparable success rate across populations.
3. **Dataset:** Natural + synthetic (correction funnel), historical.
4. **Fresh or historical:** Historical (all populations, GPU-dependent generation/correction).
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Figure 05

1. **Demonstrates:** Shipped/failed/scope-violation outcome breakdown per population.
2. **Does NOT demonstrate:** That 1/10 or 1/56 is a statistically validated rate.
3. **Dataset:** Natural + synthetic, historical.
4. **Fresh or historical:** Historical.
5. **Causal claim:** No — explicitly captioned "NOT statistically established."
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No (explicitly disclaimed).
8. **If yes, supported:** N/A.

## Figure 06

1. **Demonstrates:** Observed safety-mechanism counts, including 0 unsafe shipments.
2. **Does NOT demonstrate:** That unsafe corrections are impossible.
3. **Dataset:** Natural, historical, descriptive safety count.
4. **Fresh or historical:** Historical.
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Figure 07

1. **Demonstrates:** Mean/median verifier confidence per verdict on real claims.
2. **Does NOT demonstrate:** That confidence equals correctness.
3. **Dataset:** Natural, metric-only, descriptive.
4. **Fresh or historical:** Fresh (STEP 6).
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Figure 08

1. **Demonstrates:** Evidence-strength grade (A-E) for 8 named ablation factors.
2. **Does NOT demonstrate:** Causal isolation for the Grade-E joint four-lever row, or that Grade C equals Grade A in strength.
3. **Dataset:** Mixed (GOLD, natural, behavior).
4. **Fresh or historical:** Mixed, individually labeled per bar (see `FIGURE_METADATA.csv`).
5. **Causal claim:** Grades A (evidence-v1, premise framing) do carry a supported causal-contribution claim; Grade E explicitly carries none.
6. **If yes, justified:** Yes for Grade A rows — both isolate a single-variable change with a real paired statistical test (see Figure 02's justification and `STATISTICAL_RESULTS.md`). No causal claim is made for C/E rows.
7. **Statistical significance shown:** Yes — p=3.01e-04 (evidence-v1), p=4.16e-23 (premise framing), p=3.12e-02 (claim parser).
8. **If yes, supported:** **YES** for all three — each p-value is copied unchanged from `ABLATION_SUMMARY.json`, itself computed from real paired/matched data in STEP 6/7 (verified exactly in `CONSOLIDATED_CONSISTENCY_REPORT.md`).

## Figure 09

1. **Demonstrates:** Runtime/VRAM for historical GPU arms vs. the one fresh CPU arm.
2. **Does NOT demonstrate:** That the GPU results were reproduced on this machine.
3. **Dataset:** Runtime/resource, historical (4 arms) + fresh (1 arm).
4. **Fresh or historical:** Explicitly labeled per bar; annotation states "NVIDIA GPU available: NO. Qwen generation/correction executed: NOT EXECUTED."
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Figure 10

1. **Demonstrates:** Observed evidence coverage across all natural regimes, side by side.
2. **Does NOT demonstrate:** An accuracy measure, or a trend beyond the raw per-regime values.
3. **Dataset:** Natural, metric-only.
4. **Fresh or historical:** Mixed, individually labeled per bar.
5. **Causal claim:** No.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Figure 11

1. **Demonstrates:** The magnitude difference between synthetic (72.2%) and natural cumulative (1.8%) correction shipping.
2. **Does NOT demonstrate:** That either rate predicts, transfers to, or is equivalent to the other — explicitly annotated.
3. **Dataset:** Synthetic (GOLD-adjacent, constructed) + natural, historical.
4. **Fresh or historical:** Historical (both values, GPU-dependent).
5. **Causal claim:** No — this figure exists specifically to prevent a false equivalence claim.
6. **If yes, justified:** N/A.
7. **Statistical significance shown:** No.
8. **If yes, supported:** N/A.

## Summary

Only Figures 02 and 08 display a p-value. Both are traced to real, paired statistical
tests computed on genuine experimental data in STEP 6/7, both independently
cross-checked (exact sign test agreeing with McNemar's direction, and — for two of the
three p-values — an exact bit-for-bit match against `final_comparison/tables/statistical_tests.csv`'s
independently-computed figures). **Every displayed p-value is supported by its
underlying test. No figure in this set makes an unsupported causal or statistical claim.**
