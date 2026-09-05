# STEP 10 — Correction Safety Observations (GPU-executed populations only)

Scope: this document reports ONLY what was observed in the specific GPU
executions run during STEP 10. It makes no claim of legal correctness and no
general safety guarantee. Language throughout is "observed in this tested
population," per this step's requirement. Populations are kept separate, not
pooled, per this project's established methodology (`evaluation/ABLATION_RESULTS.md`
§ correction funnel).

## Population 1: mode-C smoke test, n=5 natural cases (NyayaRAG, arbitrary first
5 cases with >=1 evidence-overlapping citation, bare framing, production config)

Source: `actual_outputs/step10_gpu_validation/run_modeC_n5.jsonl`.

| # | Correction attempts | Corrections generated | Passed scope check | Re-verified | Shipped | Rejected | Unsafe shipped observed |
|---|---|---|---|---|---|---|---|
| 5 cases | 1 | 1 | 0 | 0 (never reached — scope check ran first and failed) | 0 | 1 (`correction_scope_violation`) | 0 |

Detail: 4 of 5 cases had no CONTRADICTED/low-confidence-NEI claim and never
triggered correction (`not_triggered`). The one case that triggered
(`1996_129`, claim `c2`, CONTRADICTED) produced a Qwen correction that
altered text outside the flagged sentence; the pipeline's own programmatic
scope gate (`pipeline._scope_violation`) caught this and the correction was
never shipped — the original field was retained
(`final_field.source == "correction_scope_violation"`). No unsafe correction
was shipped in this population; the sample is too small (n=1 trigger) to
support any rate estimate.

## Population 2: targeted natural correction validation, n=10 (labeled framing,
full improved config), freshly reproduced this step

Source: `actual_outputs/step10_gpu_experiments/labeled_correction_validation_gpu_metrics.fresh.json`.

| Correction attempts | Corrections generated | Passed scope check + re-verified ENTAILED (shipped) | Rejected: scope violation | Rejected: failed re-verification | Unsafe shipped observed |
|---|---|---|---|---|---|
| 10 | 10 | 1 | 3 | 6 | 0 |

This exactly reproduces the historical result for this same population
(`outputs/labeled_correction_validation_gpu_metrics.json`) — see
`GPU_REPRODUCTION_CROSSCHECK.md`. Of 10 real Qwen correction attempts on
cases where labeled-framing verification flagged a claim, 1 was shipped
(passed both the programmatic scope gate and DeBERTa re-verification as
ENTAILED against its own evidence), 3 were rejected for altering unflagged
text, and 6 were rejected because re-verification did not return ENTAILED
(includes cases where the corrector's rewrite still didn't satisfy the
verifier, or no scope-valid same-citation replacement claim could be
re-extracted). 0 of the 10 attempts resulted in an unsafe shipped correction
in this tested population (unsafe defined here, per the historical script's
own metric, as: status is "corrected" but re-verification verdict is not
ENTAILED — this cannot occur by construction, since `apply_selective_correction`
only sets status to "corrected" when re-verification already returned
ENTAILED; the `unsafe_shipped` counter is retained as an independent
after-the-fact check, not a tautology guard).

## Population 3: cumulative correction (project-wide rate across all runs)

Not executed or re-derived in STEP 10. The historical cumulative rate (1/56,
1.8%, from `outputs/final_metrics.json`) is HISTORICAL ONLY and is not
updated by this step's n=5 or n=10 GPU runs — those are separate, smaller
populations (5 natural cases with only 1 real trigger; 10 pre-selected
triggering cases from the labeled-framing arm), not a re-run of the
cumulative 56-case denominator.

## What this step does NOT support claiming

- No claim that corrections are legally correct — no legal ground truth
  exists anywhere in this project (unchanged from STEP 1-9).
- No claim of a general correction "shipping rate" — Population 1's n=1
  trigger and Population 2's n=10 pre-selected triggering cases are both far
  too small, and too differently selected (arbitrary vs. pre-filtered for
  labeled-framing eligibility), to combine into one rate.
- No claim that scope-violation or re-verification rejection rates
  generalize beyond the exact populations tested here.
