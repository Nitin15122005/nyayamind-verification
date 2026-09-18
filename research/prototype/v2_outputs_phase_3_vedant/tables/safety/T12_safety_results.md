# T12_safety_results

Safety outcomes, each stated WITH its exact denominator and scope, as zero-event results require.

| outcome | count | denominator | exact scope | 95% upper bound on true rate | reading |
|---|---|---|---|---|---|
| Unsafe corrections shipped | 0 | 56 | all natural correction attempts across the project's history | ~5.2% (rule of three, 95% one-sided) | ZERO-EVENT. Evidence of a fail-closed design behaving correctly on the data seen. NOT a proof of safety. |
| Unsafe verdict reversals | 0 | 56 | same scope | ~5.2% | ZERO-EVENT, same caveat. |
| Corrections blocked by a gate | 18 | 56 | same scope | n/a | Gates fired and stopped shipping - the mechanism demonstrably engages. |
| Formal 15-category red-team evaluation | NOT PERFORMED | n/a | n/a | n/a | No red-team evaluation exists anywhere in this project. |

## Notes

- With 0 events in 56 trials, the exact one-sided 95% upper bound on the true unsafe rate is approximately 5.2% (rule of three). Quoting '0 unsafe' without that bound would overstate the evidence.
- Scope is natural-data correction attempts only. It says nothing about unseen inputs.
