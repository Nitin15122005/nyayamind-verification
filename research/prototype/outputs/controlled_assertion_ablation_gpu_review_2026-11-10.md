# Controlled assertion-aware correction ablation — review note

**Run date:** 2026-11-10  
**Status:** exploratory paired pilot; not a legal-accuracy result and not sufficient for a superiority claim.

## Run summary

The uploaded run contains 50 paired NyayaRAG cases, 210 extracted claims, and 131 evidence-matched claims per arm. Both arms share the same generated text and the same 136-record evidence pool. There were 10 correction attempts in each arm.

| Outcome | Legacy (A) | Assertion-aware (B) |
|---|---:|---:|
| Correction attempts | 10 | 10 |
| Accepted corrections | 1 | 2 |
| Scope violations | 6 | 5 |
| Re-verification failures | 3 | 3 |
| Sibling regressions | 0 | 0 |
| Unsafe shipments according to the automated gate | 0 | 0 |
| Unflagged assertions preserved | 40 / 57 | 47 / 57 |

The initial verification distributions were identical across arms: 115 NOT_ENOUGH_INFORMATION, 79 NO_EVIDENCE, 13 ENTAILED, and 3 CONTRADICTED claims.

## Paired correction outcome

The 10 correction-triggered documents yield:

| Paired outcome | Documents |
|---|---:|
| Both arms accepted a correction | 1 |
| A only accepted | 0 |
| B only accepted | 1 |
| Neither accepted | 8 |

The exact two-sided McNemar/binomial p-value for the discordant pair is **1.0** (one discordant pair). The observed difference of 2/10 versus 1/10 is descriptive only; it is not statistically persuasive evidence of a treatment advantage.

The shared accepted correction is for document `2009_119`. The B-only accepted correction is for `2021_11`. The latter changes the Section 307 statement to add “if the act would cause death.” The cited Section 307 text also contains intention/knowledge and circumstance requirements; the generated qualifier may be incomplete. A DeBERTa ENTAILED result is not a substitute for legal review. Neither accepted correction should be described as legally validated without an independent reviewer checking the authoritative statutory text and the case record.

## Failure profile

- A: 6 scope violations and 3 re-verification failures.
- B: 5 scope violations, 2 citation-identity losses, and 1 re-verification failure.
- Both arms had zero sibling regressions and zero automated unsafe shipments.
- The B path did not eliminate scope failures; 5/10 attempts still failed the scope gate.

The automated “shipped” label means only that the implementation's programmed checks passed. It does not establish that the resulting proposition is legally complete, correctly scoped, or applicable to the facts.

## Reproducibility qualification

The uploaded run was produced before the follow-up driver-hardening changes recorded in this branch. The original run metadata did not fully record the primary-hypothesis policy or case-date-aware matching. The driver has since been updated to:

1. reproduce the selector's v0-only multi/single variant tie-break;
2. pass each case's judgment date to evidence matching;
3. explicitly pass the configured primary-hypothesis policy to verification;
4. record judgment dates, immutable model revisions, and runtime environment; and
5. calculate the conventional median for even-sized confidence samples.

Therefore, **do not present this uploaded run as the output of the current hardened driver**. A fresh GPU rerun is required to produce results under the corrected protocol. Preserve the four original output files unchanged as the exploratory run.

## Artifact fingerprints

SHA-256 fingerprints of the uploaded files reviewed for this note:

| Artifact | SHA-256 |
|---|---|
| `controlled_assertion_ablation_gpu_metrics.json` | `a1975762d8e95fa5221dc16640b9d83335903901df62ea8d25110bc9fbc336ca` |
| `controlled_assertion_ablation_gpu_A.jsonl` | `ee7ebc348b3e238ccce9d1f4c16ede073574c9ac3fc83c22326526dab7c75654` |
| `controlled_assertion_ablation_gpu_B.jsonl` | `9872ce4ecc298eee4a4100d541804a12ab8c51795cb2aa02739e41432151fee6` |
| `controlled_assertion_ablation_gpu_corrections_detail.jsonl` | `88acee9427ba2f2fa49f8df573f014712f7f2221987f92a8d5c5d26236e3edc0` |

These fingerprints identify the uploaded artifacts reviewed here. The raw files themselves still need to be added to the repository's experiment archive (after checking data-sharing permissions) for a self-contained public reproduction.

## Publication wording

Permissible wording:

> In a 50-case paired pilot, assertion-aware correction passed the automated acceptance gates in 2 of 10 triggered cases, compared with 1 of 10 for legacy correction. The single discordant pair favored assertion-aware correction, but the exact two-sided paired test was not significant (p = 1.0). Both methods retained substantial scope and re-verification failure rates. These findings are exploratory and do not establish legal correctness or general superiority.

Do not claim statistically significant improvement, legal correctness, or publication-grade validation from this run.
