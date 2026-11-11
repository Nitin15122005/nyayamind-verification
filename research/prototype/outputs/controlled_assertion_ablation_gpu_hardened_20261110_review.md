# Hardened controlled assertion-correction ablation — review

**Run timestamp:** 2026-11-10 15:43:01 UTC  
**Protocol:** 50 paired cases; Qwen generation shared once per case; both arms use the same 136-record v0+v1 evidence pool and identical claim extraction, evidence matches, and initial verification. The only configured treatment difference is `assertion_aware_correction` (A=false, B=true). Both correction budgets are 220 tokens.

## Execution and integrity

- 50/50 document IDs align between A and B.
- Case text, judgment date, generated field, and all claim-level inputs/evidence matches/initial verdicts are identical across arms.
- 210 claims per arm; 131 evidence-matched per arm.
- Initial verdicts are identical: ENTAILED 32, NO_EVIDENCE 79, NOT_ENOUGH_INFORMATION 96, CONTRADICTED 3.
- Evidence match methods: 129 exact-normalized, 2 fuzzy, 79 no-evidence.
- The CPU audit passed; 22 correction-detail rows reconcile to 11 attempts per arm and metric status counts. The paired analyzer reported no integrity errors.
- Runtime 1,769.1 seconds (29.5 minutes); generation 1,280.3 seconds; peak VRAM 7,569 MiB on an NVIDIA GeForce RTX 4050 Laptop GPU.
- Model revisions: Qwen `a09a35458c702b33eeacc393d103063234e8bc28`; DeBERTa `6f5cf0a2b59cabb106aca4c287eed12e357e90eb`.

## Primary result

| Outcome | Legacy A | Assertion-aware B |
|---|---:|---:|
| Correction attempts | 11 | 11 |
| Accepted/shipped corrections | 0 | 0 |
| Scope violations | 10 | 5 |
| Other correction failures | 1 | 6 |
| Sibling regressions | 0 | 0 |
| Unsafe shipped corrections | 0 | 0 |

Neither method produced an accepted correction. All 11 paired documents were therefore "neither shipped"; there were no discordant accepted outcomes. The exact two-sided McNemar/binomial p-value is 1.0. This is not evidence of equivalence or non-inferiority: with zero accepted corrections in both arms, the primary acceptance endpoint cannot distinguish the methods.

## Failure-mode trade-off

- **A:** 10 scope violations; 1 re-verification failure (document `2003_760`, verdict NOT_ENOUGH_INFORMATION, confidence 0.6831).
- **B:** 5 scope violations; 4 citation-identity losses; 1 re-verification failure (document `2008_2318`, NOT_ENOUGH_INFORMATION, confidence 0.8228); 1 unauthorized addition (`2021_11`).

Assertion-aware correction halved the observed scope-violation count (10 to 5) but introduced citation-identity losses and an unauthorized-addition failure. These are descriptive counts from 11 attempts, not stable population estimates. Confidence 0.8228 is confidence in the NOT_ENOUGH_INFORMATION class, not support for the claim.

## Unflagged assertion preservation

Across 62 checked unflagged assertions, the proposed output preserved 39 in A (62.9%) and 50 in B (80.6%), a descriptive difference of 11 assertions. Whole-claim-text preservation was 35/62 in both arms.

This is a useful mechanistic signal: assertion-span correction appears to preserve more unflagged assertion spans in its *proposed rewrites*. It does not mean those rewrites are accepted or legally correct. Since all 11 proposed corrections in each arm were rejected by at least one gate, this preservation metric must not be presented as an end-to-end improvement in shipped output quality.

## Interpretation

The hardened paired run supports a narrow conclusion:

> On this 50-case pilot, assertion-aware correction reduced the number of scope-violation rejections from 10 to 5 and increased preservation of checked unflagged assertion spans from 39/62 to 50/62. However, it also incurred four citation-identity losses and one unauthorized-addition rejection. Neither arm passed any correction through all acceptance gates (0/11 each), so no improvement in accepted correction rate was demonstrated.

Do not claim legal correctness, statistically significant superiority, or production readiness from this run. The experiment is useful for locating engineering bottlenecks, not validating legal outputs.

## Engineering priorities indicated by the run

1. **Citation identity must be a hard invariant.** Preserve the exact evidence/citation identifier and require a one-to-one mapping from every corrected assertion to the original evidence item; reject paraphrases that detach the citation.
2. **Unauthorized-addition detection needs explicit tests.** In particular, ensure a correction cannot add statutory elements, qualifiers, exceptions, or factual predicates absent from the original assertion/evidence scope.
3. **Scope gate diagnostics should be decomposed.** Record whether failure is due to changed unflagged spans, deleted necessary qualifiers, changed legal subject/actor, provision identity, or unsupported additions.
4. **Use structured assertion-level edits rather than free-form full-span regeneration.** Generate a minimal replacement for the flagged assertion, retain immutable neighboring text and citation metadata, and validate the splice.
5. **Expand adjudicated evaluation.** Add independent legal-review labels for proposed corrections and failure categories; report precision/coverage and abstention, not just model-verifier acceptance.
6. **Keep a locked external test set.** Tune prompts and gates on development cases only; reserve a new case-disjoint holdout for final claims. The current 50-case pilot should not be reused as an untouched confirmatory test after these failures drive changes.

## Warnings

The Transformers warnings about temperature/top-p/top-k while `do_sample=False` mean those sampling parameters are ignored; generation is greedy/deterministic under this configuration. The flash-attention warning indicates a fallback attention implementation, not a failed run. Record these environment details, but they do not invalidate the run.

## Artifact fingerprints

SHA-256:

| Artifact | SHA-256 |
|---|---|
| `controlled_assertion_ablation_gpu_hardened_20261110_metrics.json` | `88b314cb7836a966cf305f2eea54b9dcd5897b94b0f3c73ee7b14ddd6623e487` |
| `controlled_assertion_ablation_gpu_hardened_20261110_A.jsonl` | `0df46f9bacbc1126886426907a462f5fd54fd27cd8bffe9218acd588ac995e5e` |
| `controlled_assertion_ablation_gpu_hardened_20261110_B.jsonl` | `ea17ec8f8a0425262e307200f88c7f64a0b44a9f4232970d32e7d078650af7c0` |
| `controlled_assertion_ablation_gpu_hardened_20261110_corrections_detail.jsonl` | `13fde4a3675d3c0519a819152ee66cc194a3f3eef7d211493fa5cee9ad7eb2f6` |
| `controlled_assertion_ablation_gpu_hardened_20261110_paired_analysis.json` | `c593fa9c1c82d47be3ac3b3ad008941935e91cfbb56e2df9062c92436125cd2c` |

Raw case text and correction artifacts are not committed here because they may contain legal-case text or personal information. Store them in an access-controlled research archive after confirming dataset redistribution permissions.
