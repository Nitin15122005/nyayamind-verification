# Historical Cross-Check — STEP 4 Fresh Results vs. Committed Historical Results

This is a cross-check only, computed AFTER the fresh metrics above were already
calculated and written to disk (`gold_verifier_summary.csv`, `gold0{1,2}_metrics.json`).
No fresh number was adjusted to agree with history.

## GOLD-01 — Controlled verifier benchmark

| Metric | Fresh (STEP 4) | Historical | Absolute difference | Source of historical number |
|---|---|---|---|---|
| bare accuracy | 0.733333 | 0.733333 | **0.000000** | `outputs/controlled_benchmark_deberta_metrics.json` |
| bare macro F1 | 0.748665 | 0.748665 | **0.000000** | same |
| bare confusion matrix | 92/0/92, 2/103/13, 0/5/113 | 92/0/92, 2/103/13, 0/5/113 | **bit-for-bit identical** | same |
| labeled accuracy | 0.971429 | 0.971429 | **0.000000** | `outputs/controlled_benchmark_deberta_labeled_metrics.json` |
| labeled macro F1 | 0.968361 | 0.968361 | **0.000000** | same |
| labeled confusion matrix | 184/0/0, 5/110/3, 0/4/114 | 184/0/0, 5/110/3, 0/4/114 | **bit-for-bit identical** | same |

**Result: exact reproduction, both framings.** Every prediction, not just the aggregate
metric, is identical between this run and the historical committed result.

**This is notable given a genuine environment discrepancy found during this step**: the
historical metrics files' own recorded `environment` field shows
`{"python": "3.13.1", "torch": "2.13.0+cpu", "transformers": "5.15.1"}` — **not** the
project's documented, pinned environment (Python 3.11.9, `torch==2.2.2+cu121`,
`transformers==4.40.2`, established in STEP 2 and used for this run). The historical
GOLD-01 results were therefore never actually produced under the environment
`REPRODUCIBILITY.md` documents as canonical. This is a real, pre-existing project
reproducibility gap (see `../../PROVENANCE.md`'s STEP 4 section) — it happens not to have
affected these particular numbers (DeBERTa inference is apparently stable across this
specific torch/transformers version range), but that stability is an empirical
observation from this cross-check, not something that was guaranteed in advance.

## GOLD-02 — Synthetic stress set

| Metric | Fresh (STEP 4) | Historical | Absolute difference | Source of historical number |
|---|---|---|---|---|
| bare contradiction recall, overall (n=59) | 21/59 = 0.3559 (35.6%) | 35.6% | ~0.0 (rounds identically) | `outputs/final_research_results.md` §A |
| labeled contradiction recall, overall (n=59) | 27/59 = 0.4576 (45.8%) | 45.8% | ~0.0 (rounds identically) | same |
| bare contradiction recall, evidence-matched only (n=44) | 21/44 = 0.4773 (47.7%) | 47.7% | ~0.0 (rounds identically) | same |
| labeled contradiction recall, evidence-matched only (n=44) | 27/44 = 0.6136 (61.4%) | 61.4% | ~0.0 (rounds identically) | same |

**Result: reproduced to the historical report's own stated precision (1 decimal
place).** The historical document reports these four numbers as percentages to one
decimal; this run's exact fractions round to the same values in all four cases.

## Possible explanations for the (near-zero) residual differences

No explanation is required for GOLD-01 (exact, bit-for-bit). For GOLD-02, the residual
is consistent with simple rounding (the historical document states percentages to 1
decimal; this run's raw fractions are not exactly round numbers) — no other explanation
is invented, per this step's rule against inventing causes for discrepancies that do not
exist.

## What this cross-check establishes

1. The real DeBERTa verifier's behavior is reproducible on this machine, under this
   step's exact commands, matching history closely enough to trust both the historical
   record and this fresh run.
2. The 15/59 NO_EVIDENCE claims found in this run's GOLD-02 evaluation are not an
   artifact of this evaluation's own construction — they are exactly the same 15 claims
   (44 = 59 − 15 evidence-matched) the historical "evidence-matched only" denominator
   already accounts for, confirmed by the fact that dividing by 44 (not 59) reproduces
   the historical evidence-matched percentages exactly.
3. The one genuine, newly-surfaced gap is procedural, not numerical: the historical
   GOLD-01 results were computed in an undocumented environment that does not match this
   project's own stated reproducibility pin. This is recorded in `../../PROVENANCE.md`
   and should be treated as an open item for a future maintainer, not silently corrected
   or hidden.
