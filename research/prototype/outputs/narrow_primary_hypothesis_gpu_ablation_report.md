# narrow_primary_hypothesis: fresh end-to-end GPU ablation

_Generated 2026-09-09T10:10:28.462293+00:00_

Real Qwen2.5-7B generation + real DeBERTa verification + real selective correction, run through the ACTUAL production `pipeline.py` code (mode C), on **15 genuinely fresh** NyayaRAG cases never used in any prior experiment in this repo (182 document_ids excluded by scanning every committed outputs/*.jsonl file).

Generation is shared between arms (called once per case, deterministic greedy decoding); only `verification.narrow_primary_hypothesis` differs (OLD=false, matching the config immediately before Stage 4; CURRENT=true, exactly as shipped today) -- everything else (evidence pool, premise framing, scope-check mode, confidence threshold) is held identical between arms.

> Verdicts are a small public NLI model's output against a 136-record corpus. They are not legal-correctness determinations, and no lawyer ground truth exists. This is a SMALL sample (n=15 cases) -- directional evidence, not a statistically powered claim.

## Headline

| Metric | OLD (pre-Stage-4) | CURRENT (shipped) |
|---|---|---|
| Total claims | 39 | 39 |
| Claims with evidence | 12 | 12 |
| Evidence coverage | 30.8% | 30.8% |
| ENTAILED | 0 | 1 |
| CONTRADICTED | 0 | 0 |
| NOT_ENOUGH_INFORMATION | 12 | 11 |
| Correction triggered | 0/15 | 0/15 |
| **Correction SHIPPED** | **0/15** | **0/15** |

## Correction status breakdown

| Status | OLD | CURRENT |
|---|---|---|
| not_triggered | 15 | 15 |

Runtime: 381.0s total for 15 cases x 2 arms (generation shared, so this is NOT double the single-arm cost).

## Interpretation

This distinguishes VERIFICATION recovery (NEI -> ENTAILED/CONTRADICTED verdict changes) from actual CORRECTION SHIPPING (a rewritten field passing every safety gate). A verdict change does not automatically produce a shipped correction -- shipping additionally requires the flagged claim to be the one selected for correction (max_attempts=1, first-flagged-claim-only), Qwen's rewrite to pass re-verification as ENTAILED, and the sibling-regression/scope/injection/ordinal safety gates to all pass. See the correction status breakdown above for exactly which gate stopped each non-shipped attempt.
