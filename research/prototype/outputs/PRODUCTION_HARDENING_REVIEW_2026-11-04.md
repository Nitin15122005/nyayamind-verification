# Production hardening review — 2026-11-04

## Scope

This review covers the evidence loader, experimental generative verifier, automated test workflow, and local live-demo API. Changes are confined to `publication/readiness-engineering`. This is not a claim of legal validation, deployment readiness, or production certification.

## Findings addressed

### Evidence integrity
- Reject malformed JSONL, blank lines, duplicate canonical/audit keys, missing audit links, orphan audit rows, unknown verdicts, incomplete canonical records, and exact-index collisions.
- Reject a partial v1 supplement pair.
- Restrict usable verdict configuration to `VERIFIED_EXACT` and `VERIFIED_CONTENT`.
- Where audit rows repeat source URL or provision identity, require exact agreement with canonical records. Sparse v1 audit rows remain supported.
- Preserve the existing v0/v1 merge-by-key semantics.

### Experimental Qwen verifier
- Removed fabricated `confidence=1.0`; the model does not emit calibrated class probabilities.
- Accept only an unambiguous verdict label at the start of the response; malformed responses fail closed to `NOT_ENOUGH_INFORMATION`.
- Mark generative verdicts as unscored, validate input pairs and batch size, use the loaded model's device, and restore tokenizer padding configuration in a `finally` block.
- This remains an experimental alternative, not a replacement for the production DeBERTa NLI verifier.

### CI/test architecture
- Added pinned CPU dependencies matching the documented torch/transformers generation.
- Marked real pretrained-model tests as integration tests and separated them from deterministic tests.
- Added a manual workflow-dispatch option for real DeBERTa integration, which downloads model weights.
- Added synthetic tests for loader failure modes, audit identity mismatches, unsafe verdict configuration, and fail-closed verdict parsing.

## Release blockers still open

1. **Temporal legal applicability:** retrieval matches citation identity and text; it does not resolve whether a historical provision applied on the judgment date or apply repeal, savings, and transitional provisions. This must be resolved before presenting matches as date-valid legal conclusions.
2. **Evidence authority and coverage:** structural integrity does not establish authoritative legal correctness. The corpus is limited and includes third-party sources.
3. **GOLD-03:** citation-free claims, paraphrases, contradictions and NEI labels still need independent drafting/adjudication before confirmatory reasoning claims.
4. **Correction scope:** only the first eligible flagged claim is corrected. Multi-claim correction remains unimplemented.
5. **Model validation:** calibration, independent domain evaluation, drift monitoring and model artifact versioning remain incomplete.
6. **Public deployment:** the live demo binds to loopback and lacks production authentication, TLS termination, rate limiting, durable job queue and operational monitoring. It is a local demo, not a public production API.
7. **Reproducibility:** release-grade runs still need mandatory model/dataset hashes, environment lockfiles and complete run manifests.
8. **Target-environment validation:** Windows full-suite execution, real-model integration, GPU generation/correction, Docker and end-to-end deployment need validation in the target environment.

## Release decision

**Not yet production-ready.** This pass reduces silent evidence corruption, misleading experimental-verifier confidence and CI ambiguity. It does not resolve temporal legal applicability, independent benchmark adjudication, or deployment validation.
