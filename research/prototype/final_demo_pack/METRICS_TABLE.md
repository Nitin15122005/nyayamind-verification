# Consolidated Metrics Table

Every value below is read directly from `research/prototype/final_demo_pack/metadata/computed_metrics.json` (built by `metadata/compute_metrics.py` from raw, frozen experiment artifacts — never hand-typed). The machine-readable, more granular companion is `tables/METRICS_COMPREHENSIVE.csv`. Where a value could not be honestly derived, this table says so explicitly rather than omitting the row.

**Legend — defensible column:** ✅ = numeric, traceable, appropriate to cite as measured; ⚠️PROVISIONAL = real number but source data is not lawyer-verified ground truth, cite only as "agreement between machine-produced label sets"; ❌ = not measurable with current data.

## 1. Case / claim volume

| Metric | Value | Dataset | n (cases) | Defensible |
|---|---|---|---:|---|
| Total distinct natural cases ever processed | 180 | n=30 + batch1(50) + batch2(50) + final-validation(50); targeted(11) excluded as confirmed subset of n=30 | 180 | ✅ |
| Synthetic stress cases | 59 | Deliberately-corrupted claim pairs (c1/c2) | 59 | ✅ |
| Controlled verifier benchmark items | 420 | Curated real legal claim/evidence pairs, 8 conditions | 420 | ✅ |
| Total claims, pooled bare+v0 regime | 784 | 180 cases (n30, batch1, batch2, final-A) | 180 | ✅ |
| Total claims, pooled labeled+v0 regime | 487 | 100 cases (batch1, batch2) | 100 | ✅ |
| Total claims re-parsed with current parser (retrieval eval) | 797 | Every natural GPU experiment ever run | 183 texts | ✅ |

## 2. Evidence matching / coverage

| Metric | Value | Dataset | n | Defensible |
|---|---|---|---:|---|
| Evidence-matched, pooled bare+v0 | 454/784 = 57.9% | 180 cases | 784 claims | ✅ |
| Evidence-matched, pooled labeled+v0 | 284/487 = 58.3% | 100 cases | 487 claims | ✅ |
| Coverage, v0-only (paired arm A) | 132/209 = 63.2% | Final validation, 50 held-out cases | 209 claims | ✅ |
| Coverage, v0+v1 (paired arm B) | 147/209 = 70.3% | Same 50 cases, same generation | 209 claims | ✅ |
| Coverage improvement | +7.1pp, McNemar chi2=13.07, **p≈0.0003**, 0 regressions | Paired design | 209 claims | ✅ (only metric in this pack with a computed significance test) |
| v0 vs v1 coverage, independent claim-level check | 60.2% -> 66.3% (+36 newly covered, 198 still NO_EVIDENCE) | 588 claims across multiple batches | 588 | ✅ |
| NO_EVIDENCE rate (retrieval eval, current parser) | 260/797 = 32.6% | All natural texts ever generated | 797 | ✅ |
| Retrieval precision proxy (exact vs fuzzy match ratio) | ~60:1 to ~80:1 in every batch (e.g. final-B: 145 exact vs 2 fuzzy) | Per-batch match_methods | varies | ✅ (proxy only — see limitation below) |
| True retrieval false-match rate | — | — | — | ❌ NOT MEASURABLE — no independently-labeled ground truth for "is this match correct" exists; the exact/fuzzy ratio is a proxy, not a precision score |

## 3. Verdict distributions

| Metric | Value | Dataset | n | Defensible |
|---|---|---|---:|---|
| Verdicts, pooled bare+v0 | NEI 447 / NO_EVIDENCE 330 / CONTRADICTED 5 / ENTAILED 2 | 180 cases | 784 claims | ✅ |
| Verdicts, pooled labeled+v0 | NO_EVIDENCE 203 / NEI 263 / ENTAILED 16 / CONTRADICTED 5 | 100 cases | 487 claims | ✅ |
| Verdicts, final production regime (verification-only CPU recheck) | NEI 131 / ENTAILED 13 / CONTRADICTED 3 | 50 cases, Arm B's matched claims | 147 claims | ✅ |
| Controlled benchmark confusion matrix, bare | acc 0.733, macro-F1 0.749 | 420 curated items | 420 | ✅ |
| Controlled benchmark confusion matrix, labeled | acc 0.971, macro-F1 0.968 | Same 420 items | 420 | ✅ |

## 4. Contradiction detection (synthetic stress only — do not extrapolate to natural)

| Metric | Value | Dataset | n | Defensible |
|---|---|---|---:|---|
| Contradiction recall, overall, bare | 35.6% | Synthetic stress | 59 | ✅ (synthetic only) |
| Contradiction recall, overall, labeled | 45.8% | Synthetic stress | 59 | ✅ (synthetic only) |
| Contradiction recall, evidence-matched, bare | 47.7% | Synthetic stress | 44 | ✅ (synthetic only) |
| Contradiction recall, evidence-matched, labeled | 61.4% | Synthetic stress | 44 | ✅ (synthetic only) |
| False-positive rate (unflagged true claim wrongly CONTRADICTED) | 0.0% both framings | Synthetic stress c2 claims | 59+59 | ✅ |
| Natural-data contradiction recall against real gold | — | — | — | ❌ NOT MEASURABLE — no lawyer-verified gold contradiction set exists on natural data |

## 5. Correction / safety audit

| Metric | Value | Dataset | n | Defensible |
|---|---|---|---:|---|
| Total correction attempts, all history | 122 (56 natural + 66 synthetic) | All batches | 122 | ✅ |
| Natural correction attempts | 56 | All natural batches | 56 | ✅ |
| Natural: correction_failed | 37 | — | — | ✅ |
| Natural: correction_scope_violation | 18 | — | — | ✅ |
| Natural: corrected (shipped) | 1 | — | — | ✅ |
| Natural shipped rate | 1.8% | — | 56 | ✅ |
| Final-production-regime shipped rate | 10% (1/10) | Targeted GPU validation | 10 | ✅ (small n, stated) |
| Synthetic bare shipped rate | 0% (0/30) | Synthetic stress | 30 | ✅ (synthetic only) |
| Synthetic labeled shipped rate | 72.2% (26/36) | Synthetic stress | 36 | ✅ (synthetic only) |
| **Unsafe shipments** | **0 / 122 (0%)** | Entire project history, natural + synthetic | 122 | ✅ — invariant (`status=='corrected' <=> reverification.verdict=='ENTAILED'`) checked against every single attempt |
| Sibling-regression flags | 0 attempts flagged | Natural, all batches | 56 | ✅ |
| Citation-identity preservation | Every correction-scope check confirmed; citation-identity-lost cases correctly produced `correction_failed` with `reverification: null` | `final_gpu_validation.md` §4 | — | ✅ (qualitative; see that report for the per-case table) |
| Unflagged-claim preservation | Batch1 bare 100% / batch1 labeled 77.6% / final validation 76.2%(claim-text)–85.7%(assertion-span) | Per-batch | varies | ✅ |
| Assertion-span / atomic-scope behavior | assertion_spans mode unlocked 4/6 previously-blocked genuine edits in batch-1 motivation data; this session's own re-test (final_gpu_validation) found its 2 scope-violation cases correctly still rejected | `FINAL_PRODUCTION_CONFIG.md` §3 | — | ✅ (qualitative, batch-specific — not repeated in every batch) |

## 6. Threshold sensitivity

| Metric | Value | Dataset | n | Defensible |
|---|---|---|---:|---|
| Bare macro-F1 at production threshold 0.70 | 0.749 (peak 0.751 @0.55-0.65) | Controlled benchmark | 420 | ✅ |
| Labeled macro-F1 at production threshold 0.70 | 0.968 (peak also at ~0.70) — inside the optimal plateau | Controlled benchmark | 420 | ✅ |

## 7. Verifier vs. provisional assumption-gold labels

| Metric | Value | Dataset | n | Defensible |
|---|---|---|---:|---|
| Bare agreement with assumption labels | 52.6% (20/38) | 38 evidence-matched claims | 38 | ⚠️PROVISIONAL — `assumption_annotation.jsonl` is Claude-generated, NOT lawyer-verified |
| Labeled agreement with assumption labels | 47.4% (18/38) | Same 38 claims | 38 | ⚠️PROVISIONAL — same caveat; also the direction contradicts the labeled-framing improvements measured elsewhere |
| Any number described as "verifier accuracy against legal ground truth" | — | — | — | ❌ NOT MEASURABLE — no lawyer ground truth exists in this project |

## 8. v0 vs v1 evidence corpus composition

| Metric | Value | Defensible |
|---|---|---|
| v0 records / distinct acts | 63 / 11 | ✅ |
| v1 records / distinct acts | 82 / 20 | ✅ |
| Combined usable pool (VERIFIED_EXACT+VERIFIED_CONTENT, current production) | 136 | ✅ |
| Source distribution | 100% IndianKanoon.org (both v0 and v1) — India Code returned HTTP 403 on every attempt | ✅ |

*Full per-category detail, methodology, and limitations for every row above: `tables/METRICS_COMPREHENSIVE.csv` and the deep-dive reports in `reports/`.*
