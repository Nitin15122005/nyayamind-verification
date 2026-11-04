# Production hardening programme

Branch: `production-hardening-2026-11-04`
Base: `publication/readiness-engineering`

This programme separates implemented engineering work from work that requires independent data, legal annotation, external infrastructure, or a full experimental run. A code change is not considered validated until its regression tests and the relevant integration checks pass.

## Changes implemented in this branch

### 1. Citation occurrence identity
- Added optional end-exclusive `start_char` and `end_char` offsets to `ExtractedCitation`.
- Populated offsets for full-form citations, plural citation lists, and bare citations.
- Included offsets in citation serialization, so pipeline output records retain occurrence provenance.
- Ordered extracted citations by individual occurrence position rather than only by citation-group position.
- Tightened clause attribution so the same provision number from a different Act or subsection is not treated as the same statutory identity.
- Updated correction re-extraction/ordinal matching identity to include subsection as well as provision type, number, and Act; this prevents same-section-number subsections from being conflated.
- Added regression tests for plural lists, repeated mentions, bare subsection citations, and cross-Act clause attribution.

### 2. Fail-closed fuzzy evidence ambiguity
- Jaccard retrieval now rejects tied top-scoring candidates instead of accepting whichever record happens to appear first in the evidence pool.
- Every fuzzy backend now enforces exact provision type, number, and subsection identity before Act-name similarity scoring; fuzzy similarity can no longer bypass the subsection gate.
- The explicit result is `ambiguous_fuzzy`, distinct from a genuinely absent match.
- Added a regression test for a year-omitted Act citation that equally matches two editions.

### 3. Model revision and runtime manifest wiring
- Added optional Hugging Face `revision` configuration for generator and verifier and passed it through the CLI to both tokenizer/model loaders.
- Added model revision fields to generation metadata and each output reproducibility record. After loading, the generator and verifier capture Hugging Face’s resolved `_commit_hash` when available, so outputs record the actual resolved revision even when the config used a mutable alias.
- Extended the run manifest with both configured revisions, an explicit immutable-pin status, CUDA availability, and subsection-aware evidence fingerprints. The default revisions remain null; no unverified commit hashes were invented.

### 4. Subsection-safe evidence lookup
- Removed the fallback that matched a subsection citation to a base-section record (or vice versa) without proof that the exact subsection was covered.
- Added regression tests for both mismatch directions. The resulting no-match is intentionally conservative and may reduce evidence coverage until subsection-level evidence is curated.

### 5. Date-aware statutory applicability plumbing
- Added optional ISO `effective_from` / `effective_to` fields to canonical evidence loading, with strict date and interval validation. No dates are fabricated or backfilled.
- Added optional `judgment_date` ingestion from the case record. If a case date is present, retrieval accepts only evidence with an explicit effective interval covering that date; missing temporal metadata yields `temporal_unverified` / `temporal_applicability_unverified` rather than a legal verdict.
- Threaded the judgment date through initial matching, correction re-matching, sibling re-verification, and output records. Dated cases therefore fail closed consistently throughout the pipeline. Missing intervals and intervals outside the case date have distinct machine-readable outcomes.
- The current corpus does not yet contain independently verified effective intervals and the current case loader only consumes an explicit `judgment_date` field. Date-aware retrieval will therefore intentionally decline evidence for dated cases until source-backed intervals are curated.

### 6. Evidence provenance in outputs
- Claim records now expose canonical `source_url` and `audit_verdict`, as well as the full evidence identity (including subsection). This makes the provenance behind a verifier premise inspectable.
- Run-manifest evidence fingerprints now include subsection and effective-date intervals.

### 7. Correction preservation regression tests
- Added tests that the legacy sentence splice preserves all surrounding non-claim prose byte-for-byte and rejects duplicate target occurrences.
- Existing deterministic splice architecture already limits edits to the single target sentence/fragment; tests now lock that contract.

## Remaining implementation work

### P0 — before calling the software publication-ready
- Run the complete deterministic test suite and resolve every failure.
- Run real-model integration tests and a clean-checkout reproduction.
- Add occurrence-aware parser tests against the real natural-data failure cases, including `1979_201`, `1972_254`, and `1996_119`.
- Review every place that compares citation identity; use Act, provision type, provision number, subsection, and occurrence order where applicable.
- Curate source-backed effective-date intervals and populate explicit `judgment_date` values for the target case corpus; the date-aware code is fail-closed but the required legal metadata is not currently present.
- Audit all correction paths for full-field preservation, repeated-citation ordering, and post-correction re-extraction.
- Supply verified immutable model commit SHAs and archive model/tokenizer artifact hashes; configuration plumbing and manifest fields are implemented, but defaults remain intentionally unpinned.

### P1 — evidence and runtime integrity
- Add temporal applicability metadata to evidence records: enactment, commencement, amendment, repeal, and historical version.
- Add a case/judgment date to the retrieval decision and fail closed when the applicable version cannot be established.
- Reject ambiguous fuzzy matches and report ambiguity separately in output metrics.
- Extend evidence integrity auditing from JSON structure/provenance to independently checked content and historical applicability.
- Add calibration and selective-risk evaluation for the NLI verifier.
- Validate input length, exceptions, provisos, negation, and long statutory passages on a held-out set.
- Add complete output-preservation tests for sentence order, non-claim prose, citation count, and unrelated text.

### P2 — research validity
- Create a legally annotated, double-reviewed held-out dataset (GOLD-03); the worksheet generator alone is not ground truth.
- Publish annotation guidelines, reviewer disagreement, adjudication and agreement statistics.
- Redesign controlled tests to separate citation-identity overlap from proposition entailment.
- Add external/simple baselines and pre-register evaluation endpoints.
- Report uncertainty intervals and group results by case/provision to avoid pseudo-replication.
- Evaluate parser spans, retrieval, verification, and correction as separate components.

### P3 — release engineering
- Add a clean environment lock and immutable model artifact manifest.
- Run CI on the hardening branch and a release candidate.
- Add dependency/security scanning, secret scanning, license inventory, and data provenance checks.
- Add structured logs, failure codes, run IDs, and bounded resource/time controls.
- Document supported hardware, model downloads, setup, rollback, and known limitations.
- Run an end-to-end release candidate on a clean machine and archive the exact outputs.

## Non-negotiable safety policy
- Do not enable experimental multi-claim or assertion-aware correction merely to increase correction yield.
- Do not weaken scope, citation-addition, ordinal, or sibling-regression gates to make examples pass.
- Unknown or ambiguous statutory identity must remain unresolved.
- A verifier verdict is a model assessment, not a legal-correctness guarantee.
- Never label synthetic labels or NLI agreement as independent legal ground truth.

## Validation record

- Repository writes in this branch are confirmed by GitHub commit responses.
- Tests have **not yet been run by the assistant** in a local checkout.
- No GPU generation, real-model integration, clean-machine reproduction, or legal annotation has been performed as part of this branch yet.
