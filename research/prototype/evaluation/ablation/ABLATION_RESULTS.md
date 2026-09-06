# Ablation Results (STEP 7)

Machine-readable source: `ABLATION_SUMMARY.json` (canonical), `ABLATION_RESULTS.csv`,
`ABLATION_MATRIX.csv`. Every number below is read directly from those files — nothing
here was typed independently of the computed data.

## Table 1 — Factor, comparison, result, statistical support, interpretation

| Factor | Baseline | Variant | Dataset | Result | Statistical support | Interpretation |
|---|---|---|---|---|---|---|
| Evidence v1 | v0-only (59) | v0+v1 (136) | 209-paired natural | 0.632 → 0.703 coverage (+7.1pp), gained=15, lost=0 | McNemar χ²=13.067, p=0.0003; exact sign test p=6.1e-05 | **SUPPORTED** |
| Premise framing | bare | labeled | GOLD-01 (n=420) | macro F1 0.749→0.968, accuracy 0.733→0.971 | McNemar χ²=98.01, p=4.2e-23; exact sign test p=1.58e-30 | **SUPPORTED** |
| Claim parser fix | pre-223eb9d | post-223eb9d | n=30 reparse | 6/30 cases improved, 0/30 worsened, 24/30 unchanged | exact sign test p=0.03125 | **SUPPORTED** (descriptive scope, small n) |
| Atomic scope check | legacy | assertion_spans | 11 real scope violations | 1/11 unblocked at the scope gate | none (n=11, descriptive count) | **DIAGNOSTIC** |
| Narrow re-verification | off | on | 3 correction_failed cases | 2/3 diluted-NEI→CONTRADICTED, 1/3 borderline→high-conf NEI, 0 shipping changes | none performed | **DIAGNOSTIC** |
| Confidence threshold | — | 0.50–0.95 sweep | GOLD-01 (n=420) | 0.70 within 0.0021 (bare) / 0.0000 (labeled) of peak macro F1 | none (descriptive sensitivity) | **DESCRIPTIVE** |
| Correction levers (framing, isolated) | bare, else fixed | labeled, else fixed | final validation batch | 5→10 triggered, 0→1 shipped | none (n too small) | **DIAGNOSTIC** |
| Joint four-lever | — | — | — | not performed | — | **NOT_ISOLABLE** |

## Table 2 — Isolation, evidence strength, and claim boundaries

| Factor | Isolated? | Evidence strength | What we can claim | What we cannot claim |
|---|---|---|---|---|
| **Evidence v1** | YES | Strong | Increased observed evidence coverage on the paired natural evaluation (+7.1pp, zero regressions, p=0.0003) | Increased legal correctness, or accuracy on natural data |
| **Premise framing** | YES, on controlled benchmark | Strong | Substantially improved verifier benchmark performance (macro F1 0.749→0.968) | An equivalent improvement on all natural legal text — the benchmark's hypotheses are mechanically constructed |
| **Claim parser fix** | YES | Moderate (n=30, historical reproduction) | Increased per-case evidence-matched count with zero cases worsened, on this batch | Improved legal accuracy, or the same magnitude on other data |
| **Atomic scope check** | Diagnostic only | Weak-to-moderate (n=11, scope-gate only) | Changed scope-gate behavior in replay (unblocked 1/11) | Solved correction shipping — downstream shipping was not verified |
| **Narrow re-verification** | Diagnostic only | Weak (n=3, not independently isolated from other levers) | Produced more decisive re-verification confidence signals on 3 cases | Improved correction success rate — 0 shipping outcomes changed |
| **Confidence threshold** | Yes (descriptive) | N/A — not a hypothesis test | Describes a flat, non-fragile plateau around 0.70; threshold not changed | That 0.70 is proven optimal, or supports any correctness claim |
| **Correction levers (targeted)** | Yes, by design | Weak (n=5 vs 10, GPU-dependent, historical) | A directional, isolated-by-design shift (0/5→1/10 shipped) | Statistical significance, or that any lever "solved" correction |
| **Joint four-lever** | N/A | None | Nothing — the experiment does not exist | Any additive/multiplicative/interaction effect between the four levers |

## The one limitation that must appear prominently

**Joint four-lever causal isolation was not performed anywhere in this project's
history, including in this step.** Every "original vs. current" headline comparison in
this project is assembled from a chain of separate, partially-overlapping experiments,
not one controlled run varying each lever independently from a common baseline. This
does not invalidate the individual factor findings above (each of which is either
isolated on its own terms, or explicitly marked as not isolated) — it means no additive
or interactive claim about the four levers *together* can be made from the available
data.
