# Expected vs. Actual — GOLD-01 and GOLD-02 (STEP 4)

This is the first genuine expected-vs-actual comparison in this testing workspace. It
uses the real, unmodified `src/verifier.py::NLIVerifier` (MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli)
against the two datasets in this project with independently-derived expected labels.
No Qwen generation or correction was run (this machine has no NVIDIA GPU — see STEP 2).

## The chain, made explicit

```
GOLD INPUT (premise + hypothesis)
    |
    v
src/verifier.py::NLIVerifier.verify()   <- real DeBERTa model, unmodified, CPU
    |
    v
ACTUAL PREDICTION (predicted_label, confidence, raw_scores)
    |
    v
GOLD EXPECTED LABEL (construction-derived, never model-derived)
    |
    v
MATCH / MISMATCH  (predicted_label == expected_label)
    |
    v
AGGREGATE METRICS (accuracy, macro P/R/F1, confusion matrix)
```

Every step of this chain is on disk and traceable:
- Raw per-record predictions: `../../actual_outputs/step4_gold_verifier/gold0{1,2}_*/gold0{1,2}_predictions_{bare,labeled}.jsonl`
- Per-record expected-vs-actual: `gold01_expected_vs_actual.csv`, `gold02_expected_vs_actual.csv` (this directory)
- Aggregate metrics: `gold_verifier_summary.csv` (this directory) and `../../actual_outputs/step4_gold_verifier/gold0{1,2}_*/gold0{1,2}_metrics.json`
- Run metadata (model, environment, command, hashes): `../../actual_outputs/step4_gold_verifier/run_metadata/`

## GOLD-01 — Controlled verifier benchmark (n=420)

**Input**: `evidence_text` (premise, built via `format_premise()`) + `hypothesis`, both from the frozen fixture.
**Component**: `src/verifier.py::NLIVerifier.verify(premise, hypothesis)`, real model, `device="cpu"`.
**Expected**: `expected_label` field, construction-derived (`scripts/build_controlled_benchmark.py`).

| Framing | N | Correct | Incorrect | Accuracy | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|---|---|---|
| **labeled (PRODUCTION)** | 420 | 408 | 12 | **0.9714** | 0.9709 | 0.9661 | **0.9684** |
| bare (secondary reference) | 420 | 308 | 112 | 0.7333 | 0.8169 | 0.7768 | 0.7487 |

Confusion matrix, labeled framing (rows = expected, cols = actual):

| | ENTAILED | CONTRADICTED | NEI |
|---|---|---|---|
| **ENTAILED** | 184 | 0 | 0 |
| **CONTRADICTED** | 5 | 110 | 3 |
| **NEI** | 0 | 4 | 114 |

## GOLD-02 — Synthetic stress set (n=59)

**Input**: `canonical_evidence_text` (premise) + `original_synthetic_text` (hypothesis, the corrupted claim), run through the REAL full retrieve-then-verify path (`build_baseline()` + `src/pipeline.py::apply_verification`) — not a raw verifier call, so claim parsing and evidence matching are also genuinely exercised.
**Expected**: CONTRADICTED for all 59 records, **by construction** (no literal `expected_label` field exists in this dataset — see `run_gold02_evaluation.py`'s module docstring for why, and the reproducibility check it performs before scoring).

| Framing | N | Correct | Incorrect | Contradiction Recall (= Accuracy) | Of which NO_EVIDENCE (never reached verifier) |
|---|---|---|---|---|---|
| **labeled (PRODUCTION)** | 59 | 27 | 32 | **0.4576** | 15 |
| bare (secondary reference) | 59 | 21 | 38 | 0.3559 | 15 |

Confusion matrix, labeled framing:

| | ENTAILED | CONTRADICTED | NEI | NO_EVIDENCE |
|---|---|---|---|---|
| **CONTRADICTED (only gold class)** | 0 | 27 | 17 | 15 |

**A note on macro F1 for GOLD-02, stated transparently rather than silently picking one number**: because every gold label here is CONTRADICTED, macro F1 depends entirely on which label space it is averaged over. Averaged over all 3 verifier labels (as `step4_common.py::compute_metrics` does, for methodological consistency with GOLD-01) it is 0.2535 (labeled) / 0.2154 (bare) — pulled down by two classes with zero gold support. Averaged only over the one class that actually has gold examples (as `gold_verifier_summary.csv` does) it equals the CONTRADICTED-class F1 alone: 0.6279 (labeled) / 0.5250 (bare). **Neither is wrong; both are reported.** The single most meaningful number for this dataset remains contradiction recall itself (= accuracy, since there is only one gold class) — exactly as this project's own documentation has always described GOLD-02's "narrower scope."

## What 15 NO_EVIDENCE records means, honestly

15 of the 59 synthetic claims never reached the verifier at all, under either framing —
the real, unmodified `src/claim_parser.py` extraction produced a citation whose act name
did not resolve to a match in the real, unmodified `src/evidence_matcher.py`. This is a
genuine characteristic of the production claim parser interacting with these specific
synthetic sentence constructions (each built by mechanically inverting one phrase in a
citation-heavy sentence), not an error introduced by this evaluation. It is recorded, not
hidden, and — notably — it reproduces the historical evidence-matched-vs-overall split
documented in `outputs/final_research_results.md` §A almost exactly (see
`HISTORICAL_CROSSCHECK.md`).

## What can legitimately be concluded

- The real DeBERTa verifier's accuracy against **construction-derived, independent gold
  labels** is measured directly here, for the first time in this testing workspace, on
  this exact machine, under the exact production config's `premise_framing` value.
- The labeled-framing advantage over bare framing (GOLD-01: 0.7333→0.9714 accuracy;
  GOLD-02: 0.3559→0.4576 contradiction recall) is now independently reproduced, not just
  cited from a historical report.

## What must NOT be concluded

- This says nothing about generation or correction quality (both are GPU-blocked on this
  machine, per STEP 2, and were not run).
- This says nothing about legal correctness — the disclaimer `src/verifier.py` itself
  attaches to every result ("NLI statistical confidence, not a legal-correctness
  determination") applies here exactly as it does in production.
- GOLD-02's numbers describe the pipeline's behavior on **synthetic, deliberately
  corrupted** text, not on real generated claims — see `../../inputs/gold/README.md`.
