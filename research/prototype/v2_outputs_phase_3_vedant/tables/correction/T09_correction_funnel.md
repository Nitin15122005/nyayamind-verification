# T09_correction_funnel

Cumulative correction funnel over every natural correction attempt in the project's history. **HISTORICAL** - Qwen-dependent, RERUN_INFEASIBLE on this machine.

| stage | count | share of attempts | meaning |
|---|---|---|---|
| Correction attempts | 56 | 100.0% | all natural attempts |
| Blocked: scope violation | 18 | 32.1% | a safety gate rejected the rewrite |
| Rejected: correction_failed | 37 | 66.1% | the 7B corrector produced a no-op or inadequate edit |
| SHIPPED (status=corrected) | 1 | 1.8% | all gates passed AND re-verified ENTAILED |
| UNSAFE shipped | 0 | 0.0% | zero-event result |

## Notes

- The dominant failure is the 7B corrector producing a no-op or inadequate edit - a generation-quality limitation, not a pipeline defect.
- Synthetic-vs-natural transfer gap: corrections ship at 72.2% on synthetic contradictions but 1.8% on real generated text. This is the correction subsystem's single most important limitation.
