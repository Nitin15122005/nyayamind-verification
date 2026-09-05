# METRIC-ONLY Inputs

**No files are copied here.** Every dataset below is frozen, already sizeable, and
already documented with hashes/counts in `../README.md` and `../../MANIFEST.md` — this
directory references them and states, explicitly and without exception, that none of
them carries an independently established expected label.

## Non-negotiable rule this directory exists to enforce

No verdict, label, or "expected output" may ever be attached to any dataset below merely
because the production system itself previously produced one. A historical verdict is the
system's own output, not ground truth about what the correct verdict should have been.

## Inventory

### 588-claim natural aggregate
- **Not a standalone file** — a derived aggregate: every claim re-extracted (with the
  *current* parser, against the *current* evidence pool) from all 133 distinct
  generated texts this project has produced.
- Reproducible, CPU-only, no GPU: `scripts/measure_evidence_coverage_v0_vs_v1.py`.
- Used for: a NO_EVIDENCE root-cause taxonomy (genuinely-absent / wrong-act /
  unresolved-act / parser-defect-candidate) — itself a re-derived classification, not a
  pre-existing label.
- **Status: METRIC-ONLY.** No independent gold verdict exists for any of these 588
  claims.

### 209-claim paired natural evaluation
- `outputs/final_gpu_validation_A.jsonl` / `_B.jsonl` — 50 real generated cases, same
  generation, evidence-matched independently under two configurations (Arm A =
  pre-2026-08-27 baseline, Arm B = current production config).
- Used for: a **paired comparison** (McNemar's test) of whether the two configurations
  *behaved differently* on identical underlying cases (χ²=13.07, p≈0.0003, +7.1pp
  evidence coverage, 0 regressions) — never a statement about which arm was *correct*.
- **Status: METRIC-ONLY, explicitly not ground truth.** Neither arm's verdicts should
  ever be described as the "expected" answer for the other arm to match.

### Natural evaluation batches (n=30, batch1, batch2, final_validation, targeted)
- `outputs/run_{A,B,C}_n30.jsonl`, `outputs/natural_candidates_50_gpu_*.jsonl`,
  `outputs/natural_candidates_batch2_gpu_*.jsonl`, `outputs/final_gpu_validation_*.jsonl`
  (same as 209-claim set above), `outputs/run_natural_targeted.jsonl`.
- Confirmed disjoint by direct case-ID intersection (STEP 0).
- **Status: METRIC-ONLY.** Internal metrics only: verdict distributions, evidence
  coverage %, correction-shipping rate. No dataset here has an independent gold label.

### Correction / sibling-safety datasets
- `outputs/final_gpu_validation_corrections_detail.jsonl` (10),
  `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` (10),
  `outputs/natural_candidates_50_gpu_corrections_detail.jsonl` (21).
- **Status: METRIC-ONLY.** "0 sibling regressions / 0 unsafe shipments" is a real,
  countable safety-net outcome across these records — it is not a labeled accuracy
  figure, and must not be presented as one.

## What can legitimately be concluded from METRIC-ONLY data

Descriptive statistics (rates, distributions, funnel counts) and paired/comparative
statistics between two configurations run on identical underlying cases (which is
exactly what makes the evidence-coverage McNemar result meaningful — it compares the
*same* 209 claims under two configs, not against a gold label).

## What must NOT be concluded

Any accuracy, precision, recall, or F1 number against a "correct answer," for any of the
datasets above. The only two datasets in this project supporting that kind of number are
`../gold/README.md`'s GOLD-01 and GOLD-02.

## Known caveats that must travel with any report drawing on this data

1. The correction-shipping-rate improvement (5→10 triggered, 0→1 shipped) is **not
   statistically significant** at this sample size.
2. **No single experiment combines all four current production-config levers in one
   fresh generation pass** — see `../../PROVENANCE.md`.
3. The scope-check-mode ablation is **unreconciled** (1/11 vs. an earlier 4/6 unblocked
   finding) — see `../../ablation/README.md`.
