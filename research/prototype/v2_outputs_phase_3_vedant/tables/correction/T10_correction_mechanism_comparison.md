# T10_correction_mechanism_comparison

Paired replay over 5 documents x 2 arms = 10 attempts. **HISTORICAL** - Qwen-dependent, RERUN_INFEASIBLE here.

| outcome | LEGACY (production) | ASSERTION-AWARE (experimental, OFF) | note |
|---|---|---|---|
| Corrections shipped | 0 | 0 | NULL - identical outcome |
| status: correction_failed | 5 | 2 | differs |
| status: correction_scope_violation | 3 | 5 | differs |
| status: correction_sibling_regression | 1 | 2 | differs |
| status: not_triggered | 1 | 1 | same |

## Notes

- **NULL RESULT, PRESERVED AS NULL.** The assertion-aware mechanism is architecturally complete and safe, and it changes WHICH gate stops an attempt, but it ships exactly as many corrections as the legacy path: none. It must never be presented as an improvement.
- correction.assertion_aware remains FALSE in production.
