# narrow_primary_hypothesis: fresh end-to-end GPU ablation (checkpointed)

**SUPERSEDED by 2 more checkpointed cases** (n=60 → n=62; the run that would
have regenerated this auto-generated file past n=60 was interrupted by the
host OS for low memory during case 63's generation — see
`outputs/16gb_final_execution_report.md` for the complete, final, correct
n=62 analysis including the paired verification-recovery statistics and a
detailed case study. `outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json`
has been regenerated to reflect the true final n=62 state; this file's own
headline table below (n=60) is stale and kept only as an intermediate
snapshot, not the final result.

---

_Generated 2026-09-11T18:40:54.070509+00:00 (intermediate n=60 snapshot)_

Real Qwen2.5-7B generation + real DeBERTa verification + real selective correction, run through the ACTUAL production `pipeline.py` code (mode C). **60 total cases in output** (10 resumed from a prior checkpointed run + 50 completed this run).

Generation is shared between arms (called once per case, deterministic greedy decoding); only `verification.narrow_primary_hypothesis` differs (OLD=false, matching the config immediately before Stage 4; CURRENT=true, exactly as shipped today) -- everything else (evidence pool, premise framing, scope-check mode, confidence threshold) is held identical between arms.

> Verdicts are a small public NLI model's output against a 136-record corpus. They are not legal-correctness determinations, and no lawyer ground truth exists.

## Headline

| Metric | OLD (pre-Stage-4) | CURRENT (shipped) |
|---|---|---|
| Total claims | 153 | 153 |
| Claims with evidence | 32 | 32 |
| ENTAILED | 5 | 9 |
| CONTRADICTED | 1 | 2 |
| NOT_ENOUGH_INFORMATION | 26 | 21 |
| Correction triggered | 4/60 | 5/60 |
| **Correction SHIPPED** | **0/60** | **0/60** |

## Correction status breakdown

| Status | OLD | CURRENT |
|---|---|---|
| correction_failed | 2 | 3 |
| correction_scope_violation | 2 | 1 |
| correction_sibling_regression | 0 | 1 |
| not_triggered | 56 | 55 |

Runtime this run: 1175.0s for 50 newly-completed case(s) x 2 arms (generation shared, so this is NOT double the single-arm cost).

## Interpretation

This distinguishes VERIFICATION recovery (NEI -> ENTAILED/CONTRADICTED verdict changes) from actual CORRECTION SHIPPING (a rewritten field passing every safety gate). A verdict change does not automatically produce a shipped correction -- shipping additionally requires the flagged claim to be the one selected for correction (max_attempts=1, first-flagged-claim-only), Qwen's rewrite to pass re-verification as ENTAILED, and the sibling-regression/scope/injection/ordinal safety gates to all pass. See the correction status breakdown above for exactly which gate stopped each non-shipped attempt.
