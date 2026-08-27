# Case 8 — System correctly declines to correct

**Document ID:** `2004_1020` &nbsp;·&nbsp; **Claim ID:** `c1` &nbsp;·&nbsp; **Source:** `research/prototype/outputs/final_gpu_validation_B.jsonl` &nbsp;·&nbsp; **Regime:** final production

## Claim (model-generated)

> "The statutory grounding in this case involves Sections 147, 323, 302, and 34 of the
> Indian Penal Code (IPC)."

**Citation extracted:** Section 147, Indian Penal Code, 1860 (first citation in the
sentence).

## Evidence matched

**Evidence ID:** `Section 147 in The Indian Penal Code, 1860` (match method: `exact_normalized`)

> "Whoever is guilty of rioting, shall be punished with imprisonment of either
> description for a term which may extend to two years, or with fine, or with both."

## Verifier result

| Field | Value |
|---|---|
| Verdict | NOT_ENOUGH_INFORMATION |
| Confidence | **0.993** (high) |
| `sub_reason` | `null` — **not** `"low_confidence"` |

## Why no correction was ever attempted

Correction only triggers for a claim that is **CONTRADICTED at any confidence**, or
**NOT_ENOUGH_INFORMATION with `sub_reason == "low_confidence"`** (i.e. the verifier's
own argmax was ambiguous enough to be downgraded). This claim is genuinely,
confidently neutral: the sentence merely *lists* Section 147 as applicable without
asserting anything about its content, so there is nothing in it for the evidence text
to confirm or deny — a real, decisive NEI, not an uncertain one. The pipeline
correctly leaves it as `final_field == generated_field` rather than inventing a
"fix" for a claim that was never actually shown to be wrong.

## Why it matters

This distinguishes the system's actual trigger condition from "correct anything that
isn't ENTAILED." A confidently-neutral claim (no over-claiming, no
under-substantiated attribution problem) is left alone by design — correction is
reserved for claims the pipeline has an evidence-based reason to flag, not applied
indiscriminately to every claim short of full entailment.
