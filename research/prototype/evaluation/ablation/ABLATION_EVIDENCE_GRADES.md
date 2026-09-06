# Ablation Evidence Grades (STEP 7)

Grades reflect the strength of the **experimental evidence available**, not the
importance of the underlying idea. A lever graded C or D may still be a good design
decision — the grade only says how well the available data isolates and supports it.

| Grade | Meaning |
|---|---|
| **A** | Strongly supported — isolated comparison, adequate sample, statistically significant |
| **B** | Supported/descriptive — isolated comparison but smaller sample, or a legitimate descriptive (non-hypothesis-test) result |
| **C** | Diagnostic/provisional — real evidence exists but is small-sample, not fully isolated from other levers, or measures a proxy rather than the outcome of interest |
| **D** | Not isolable — no comparison exists that separates this factor from confounds |
| **E** | Not executed — no experiment exists at all |

## Grades

### Evidence v1 — **A**
209-claim paired natural evaluation, McNemar p=0.0003 and an independently-matching
exact sign test p=6.1e-05, zero regressions, genuinely isolated (evidence matching
depends only on the pool). This is the strongest natural-data ablation in the project.

### Premise framing (controlled benchmark) — **A**
420-item GOLD benchmark, McNemar p=4.2e-23 and exact sign test p=1.58e-30, genuinely
isolated (only the framing argument differs between two otherwise-identical runs). The
single strongest statistical result in this project, on curated (not natural) data.

### Premise framing (natural, 147-claim subset) — **B**
Real natural claims, ENTAILED count 0→13, its own McNemar/sign test reported in
`final_comparison/tables/statistical_tests.csv` (χ²=11.08, p=0.0009) — isolated on this
specific subset, but n=147 is smaller and this is a secondary confirmation, not the
headline result.

### Claim parser fix (commit 223eb9d) — **B**
n=30, sign test p=0.03 (freshly recomputed, matches history exactly), genuinely
isolated (same texts, only parser code differs) but a modest sample and a historical,
not fresh, reproduction of the underlying code change itself.

### Atomic scope check (assertion_spans) — **C**
n=11, purely descriptive count (1/11 unblocked), no statistical test performed or
appropriate at this sample size, and — critically — measures scope-gate behavior only,
not downstream shipping. Diagnostic, not supported.

### Narrow re-verification — **C**
n=3, no statistical test, and not independently isolated from the other three levers
already being on in the source experiment. Real, honestly-reported evidence of a
confidence-calibration effect, with zero shipping-decision changes — squarely
diagnostic.

### Confidence threshold — **B**
Not a hypothesis test by design (a descriptive sensitivity sweep), but the comparison is
genuinely isolated (pure replay of the decision rule against already-computed
distributions, no confound) and directly supports the existing threshold choice without
retuning it. Graded B because it is a legitimate, isolated descriptive result, not
because a p-value exists.

### Correction levers (targeted, framing-isolated) — **C**
Isolated by the source experiment's own design (only framing varies, confirmed from its
own metadata), but n=5 vs 10 is far too small for any statistical claim, and the
underlying data is GPU-dependent, historical, and not reproducible on this machine.

### Correction levers (cumulative, 1/56) — **D**
Not an ablation at all — a single-arm cumulative count across this project's entire
history, with no baseline comparison. Included for context only, not graded above C.

### Joint four-lever isolation — **E**
No experiment exists.

## Summary table

| Lever | Grade |
|---|---|
| Evidence v1 | A |
| Premise framing (controlled benchmark) | A |
| Premise framing (natural, 147-claim) | B |
| Claim parser fix | B |
| Confidence threshold | B |
| Atomic scope check | C |
| Narrow re-verification | C |
| Correction levers (targeted) | C |
| Joint four-lever isolation | E |

No lever was forced into A or B merely because it is part of the shipped production
configuration — three of the eight graded items sit at C, honestly reflecting the limits
of the available experiments.
