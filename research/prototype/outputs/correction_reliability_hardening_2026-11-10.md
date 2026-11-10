# Correction reliability hardening — 2026-11-10

## Objective

Improve the safety and acceptance rate of statutory-claim corrections without weakening evidence requirements, changing production defaults, or relabeling rejected outputs as successful.

## Baseline failure

The hardened paired GPU run produced 0 accepted corrections from 11 attempts in either arm. Assertion-aware correction reduced scope-preservation rejections, but incurred citation-identity losses and an unauthorized-addition rejection. The baseline is not a reliable correction system.

## Root cause identified and patched

Both correction paths previously compared the set of baseline citation identities with newly extracted identities and rejected only identities not already in the set. Set membership does not preserve occurrences or order. It can miss:
- deletion of one occurrence when another identical citation remains;
- duplicate injection of an already-present citation;
- reordering of same/different citation identities;
- replacement of a citation by another identity already present elsewhere in the field.

The correction gate now compares the ordered sequence of complete statutory identities, preserving multiplicity. Any insertion, deletion, substitution, or reordering fails closed with status `correction_citation_identity_changed` before re-verification. This is applied to both legacy and assertion-aware correction paths.

New deterministic tests cover exact sequence preservation, deletion, duplicate injection, reordering, and compatibility between dictionary records and parser objects.

## Second hardening change: structured minimal assertion patches\n\nThe production corrector now proposes a JSON patch with exactly two fields: a verbatim, unique source substring and its replacement. The pipeline applies only that substring edit inside the original target claim. It rejects malformed/empty JSON, non-unique source spans, whole-assertion rewrites, citation-like tokens, overlong patches, and ambiguous target occurrences. The model no longer gets to replace the complete assertion in this path. The original paragraph and all text outside the selected phrase remain unchanged by deterministic splice.\n\nRegression tests cover exact minimal edits, duplicate source spans, whole-assertion rewrites, citation injection, duplicate target sentences, empty/overlong patches, strict JSON schema parsing, extra-key rejection, fenced JSON, and malformed-output abstention. These are code-level tests; no GPU correction acceptance result has yet been measured.\n\n## Research-informed next architecture

The next performance-oriented improvement should not be unconstrained repeated self-revision. Research on LLM self-correction finds that prompted intrinsic self-feedback is unreliable in general tasks, while correction is more effective when grounded in reliable external feedback. Evidence-based factual correction work also frames correction as an evidence-conditioned edit task rather than open-ended regeneration.

Accordingly, candidate future architecture:
1. Freeze the original paragraph and citation occurrences.
2. Correct only a parser-validated assertion span.
3. Generate a small candidate set from the exact matched authoritative provision, with explicit output schema and no citation-token generation.
4. Apply deterministic splice only; no model-generated paragraph reconstruction.
5. Reparse and require exact ordered citation-identity sequence equality.
6. Check that every non-target assertion and every structural span is unchanged.
7. Re-verify the corrected target against the same authoritative evidence and same premise framing.
8. Re-verify affected sibling claims when any shared sentence context changed.
9. Select a candidate only if all gates pass; otherwise preserve original text and abstain.
10. Evaluate on a new locked case-disjoint holdout with independent legal adjudication.

Multi-candidate generation/reranking remains a future proposal, not an implemented or validated capability.

## Evidence and citations

- Kamoi et al., *When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs*, TACL 12 (2024): https://aclanthology.org/2024.tacl-1.78/. The survey reports that prompted self-feedback is generally unreliable and that reliable external feedback is an important condition for successful correction.
- Thorne & Vlachos, *Evidence-based Factual Error Correction*, ACL 2021: https://aclanthology.org/2021.acl-long.256/. This work formulates correction as evidence-conditioned edits to claims.
- Zhang et al., *Empowering open-domain LLMs for legal document correction via legal knowledge integration and decoding constraints*, Information Processing & Management (2026), DOI: https://doi.org/10.1016/j.ipm.2026.104703. Its reported approach combines legal knowledge integration with constraints intended to reduce over-correction. Results from its benchmarks must not be assumed to transfer to NyayaMind.

## Validation status

- Code change and deterministic regression tests are committed to the experimental branch.
- CI result for the new head must be checked before treating tests as passed.
- No fresh GPU rerun has been performed for this patch.
- No claim of improved correction acceptance, legal correctness, production readiness, or publication readiness is made.
- Production configuration remains unchanged.
