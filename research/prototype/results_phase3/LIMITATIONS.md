# Limitations

Stated plainly, using actual repository evidence — not a generic disclaimer list.

## Ground truth and labeling

- **No lawyer-validated ground truth exists anywhere in this project.** Every natural-data
  claim's "correctness" is only ever the NLI verifier's statistical output against a
  third-party-sourced evidence corpus, never checked by a legal professional.
- The only two labeled datasets (GOLD-01, n=420; GOLD-02, n=59) are **deterministically
  constructed**, not hand-labeled by a human annotator — see `evaluation/MANIFEST.md`'s
  SHA-256-hashed provenance. This makes them internally consistent and reproducible, but they
  are not an independent human judgment of legal correctness.

## Sample sizes

- **Correction shipping is measured on small samples throughout**: 1/56 cumulative natural
  (historical), 1/10 and 0/5 in the two natural-targeted batches, 0/9 and 0/10 in the two
  newest fresh batches. None of these support a confident population-level shipping-rate
  estimate; they are reported as exact counts, never extrapolated.
- **`assertion_span_primary_hypothesis`** was evaluated on n=6 real "respectively" claims —
  this is the entire population of such claims found in this project's committed natural-data
  outputs at the time of evaluation, not an arbitrary small sample, but it is still too small
  to promote to production on its own.
- **The n=10 assertion-aware correction replay** is a targeted replay of every case that
  triggered legacy correction in the n=62 batch — not a random sample, and not large enough
  to support a shipping-rate claim in either direction.

## NLI verifier limitations

- Confidence-threshold behavior is well-characterized only within the 0.50–0.95 sweep range
  tested; behavior outside that range is not characterized.
- Negation handling has a documented, empirically-motivated exclusion rule
  (`negation_contradiction_caveat`) rather than a general negation-understanding guarantee.
- The verifier has no mechanism to detect a correction that preserves surface-level entailment
  while subtly changing legal meaning in a way outside the tested adversarial categories.

## Retrieval limitations

- Evidence matching is bounded by the 136-record production evidence pool; a citation to a
  provision genuinely absent from this pool will correctly return NO_EVIDENCE, which is not a
  retrieval failure but a real corpus-coverage limit.
- BM25 and embedding fuzzy-matching were evaluated and found materially less safe than Jaccard
  on adversarial near-miss Act names — this is a real, tested limitation of those specific
  methods on this specific 136-record pool at their production-candidate thresholds, not a
  claim about BM25/embeddings in general.

## Parser limitations

- Two confirmed, real bundled-sentence shapes never narrow via `assertion_text`/`assertion_spans`:
  (1) a bare "Sections X and Y" listing with no per-citation clause, and (2) a "respectively"
  pattern immediately followed by a trailing " while " clause (the while-split succeeding
  blocks the respectively-split from running on the same sentence). Both were newly confirmed
  via the n=10 assertion-aware correction replay (documents 1953_10, 1955_16) — root cause
  identified, not fixed this pass (fixing risks a wide-blast-radius change to shared parsing
  logic without dedicated regression coverage).

## Correction and assertion-aware correction limitations

- The dominant historical correction failure mode is a generation-quality limitation (the 7B
  corrector model producing no-op or inadequate edits), not a pipeline defect — the safety
  gates are working correctly by rejecting these.
- Assertion-aware correction currently uses only `assertion_spans[-1]` (the content/description
  item); it does not yet attempt to correct a structural element (e.g. a wrong citation number
  within a "respectively" list), and it does not yet attempt to correct MORE than one wrong
  claim in the same bundled sentence — the `1955_32` case study shows this matters: a second,
  independent error in the same sentence blocks shipping even when the targeted fix is
  correct.
- No natural-data GPU batch has yet produced a genuine multi-element (`assertion_spans`
  length > 1) correction-triggering case — the multi-span splice path is verified via
  deterministic tests and a real-corpus-derived fixture, not yet by a natural occurrence.

## Safety evaluation scope

- Safety has been tested against the categories that arose from real historical failures
  (scope violation, unauthorized citation injection, ordinal ambiguity, negation, year
  conflict, sibling regression, structural span loss, invalid span) plus a pre-registered
  adversarial retrieval set (wrong-Act near-misses). **No formal, independently-designed
  15-category red-team safety evaluation has been performed.** This is a real gap, not
  papered over with a "formally proven safe" claim.

## Resource / reproducibility

- Several historical results depend on a specific GPU (RTX 4050, 6GB class) and cannot be
  re-executed on a machine without a comparable GPU; this package distinguishes
  MEASURED/GPU-dependent results from CPU-reproducible ones throughout.
- **Docker validation is ENVIRONMENT-BLOCKED** on this machine — the Docker daemon has not
  been running across every session this project has checked it, due to host resource
  constraints. Not claimed to have passed; not repeatedly retried once confirmed blocked.
- This machine's 16GB RAM ceiling means large fresh GPU batches (n>62) have not been attempted
  since a confirmed OOM pattern at n=100/50/30 before a memory-loading fix, and per this
  project's own rule, that OOM configuration was not repeated.

## Experimental components not promoted (by design, not oversight)

`verification.assertion_span_primary_hypothesis` and `correction.assertion_aware` are both
implemented, tested, and evaluated, and both remain `false` in production. This is a
deliberate, evidence-based decision — see `RESEARCH_CLAIMS.md` C7 and C9 — not an unfinished
feature.
