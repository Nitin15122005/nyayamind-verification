# Evidence Strength Matrix (STEP 8)

Machine-readable source: `EVIDENCE_STRENGTH_MATRIX.csv`. Grades reproduced unchanged
from STEP 7's `ABLATION_EVIDENCE_GRADES.md` — **no grade was upgraded or downgraded in
this step**; this is a consolidation, not a re-grading.

| Conclusion | Dataset | Evidence | Statistical support | Replicated? | Grade | Safe claim |
|---|---|---|---|---|---|---|
| Evidence-v1 increases observed coverage on paired natural claims | 209-claim paired | McNemar + exact sign test, fresh reproduction | p=0.0003 / p=6.10e-05 | Yes (STEP 6 and STEP 7 both reproduce it) | **A** | Increased observed evidence coverage, zero regressions |
| Labeled framing improves verifier benchmark performance | GOLD-01 controlled benchmark | McNemar + exact sign test, fresh | p=4.16e-23 / p=1.58e-30 | Yes (STEP 4 and STEP 7) | **A** | Substantially improved verifier accuracy/macro F1 on the controlled benchmark |
| Labeled framing improves natural-data verification decisiveness | 147-claim natural subset | Historical CPU re-verification | descriptive count only | No (single historical experiment) | **B** | More claims reach a decisive verdict (ENTAILED) under labeled framing on this subset |
| Claim parser fix increases evidence-matched count | n=30 reparse | Exact sign test, freshly recomputed | p=0.03125 | Yes (matches `final_comparison`'s independent figure) | **B** | Increased per-case evidence-matched count, zero cases worsened |
| Production confidence threshold (0.70) sits in a stable region | GOLD-01 benchmark, sweep | Descriptive sensitivity sweep, fresh | not a hypothesis test | Yes (STEP 1 and STEP 7) | **B** | 0.70 sits within ~0.002 macro-F1 of the empirical optimum, not fragile |
| Atomic scope check unblocks some real scope violations | 11 real scope violations | Deterministic replay, fresh reproduction | none (n=11, descriptive) | Yes (matches historical committed replay exactly) | **C** | Changed scope-gate behavior (1/11 unblocked); downstream shipping not verified |
| Narrow re-verification improves confidence calibration | 3 correction_failed cases | Historical narrative citation | none performed | No | **C** | More decisive re-verification signals on 3 cases; 0 shipping outcomes changed |
| Labeled framing increases shipped corrections | final validation batch, targeted | Isolated-by-design historical GPU experiment | none (n too small) | No | **C** | Directional shift (0/5→1/10), not statistically supported |
| The four current production levers interact in some specific way | N/A | None | N/A | N/A | **E / NOT_ISOLATED** | No claim can be made — the experiment does not exist |

## Grade definitions (unchanged from STEP 7)

A — Strongly supported. B — Supported/descriptive. C — Diagnostic/provisional.
D — Not isolable. E — Not executed.

No lever was forced upward or downward relative to STEP 7's assessment — three of nine
rows remain at grade C, honestly reflecting the limits of the available experiments.
