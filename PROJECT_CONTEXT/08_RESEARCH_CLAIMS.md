# Research Claims Registry

**Full table with exact n, sources, and caveats**: `research/prototype/results_phase3/RESEARCH_CLAIMS.md`.
This file is a compact index — check the full table before citing any of these in a paper or
presentation.

| Claim | Classification |
|---|---|
| Labeled premise framing improves NLI verifier accuracy over bare framing | **SUPPORTED** |
| The v0+v1 evidence pool increases evidence coverage over v0-only | **SUPPORTED** |
| The claim-parser fix (223eb9d + Art./Arts.) improves evidence-matchable claim extraction | **SUPPORTED** |
| `atomic_scope_check="assertion_spans"` reduces false scope-violation rejections | **PROVISIONAL** |
| `narrow_reverification_hypothesis` produces more decisive re-verification signals | **PROVISIONAL** |
| `narrow_primary_hypothesis` shifts verdicts toward more decisive outcomes | **PROVISIONAL** |
| `assertion_span_primary_hypothesis` improves verification on "respectively" claims | **PROVISIONAL, NOT PROMOTED** |
| BM25/embedding retrieval are viable alternatives to Jaccard | **NOT SUPPORTED (evaluated and rejected)** |
| Assertion-aware (splice-based) correction ships more corrections than legacy | **NOT SUPPORTED** (0/10 vs legacy's 0/10 on the identical replay) |
| Assertion-aware correction properly integrates parser-produced `assertion_spans` | **SUPPORTED (engineering claim)** — separate from any shipping-rate claim |
| NyayaMind's correction pipeline never ships an unsafe correction | **SUPPORTED, within tested scope** (0/132) |
| NyayaMind is lawyer-validated / legally correct | **NOT SUPPORTED — never claim this** |
| NyayaMind's results generalize broadly beyond this evidence pool / case set | **NOT SUPPORTED — never claim this** |
| Docker deployment of the current codebase has been validated | **NOT SUPPORTED (ENVIRONMENT-BLOCKED)** |

## Absolutely do not claim (repeated here because it matters)

- Lawyer validation, guaranteed legal correctness, or a formal legal-correctness oracle.
- Broad generalization beyond this project's evidence pool and case set.
- A correction-rate improvement from assertion-aware correction — the current real evidence is
  a null result (0/10 vs 0/10).
- That BM25/embedding retrieval were "not evaluated" — they were, and rejected on safety
  grounds.
- That any natural-data figure is "accuracy," "precision," or "recall" — reserved for
  GOLD-01/GOLD-02 only (see `06_DATA_AND_EVIDENCE.md`).

## Final research status (as of this writing)

Research-grade: yes. End-to-end implemented: yes. Reproducible (with stated GPU/hardware
exceptions): yes. Experimentally evaluated, including honest negative results: yes. Paper-ready
as a research prototype, with limitations stated alongside: yes. NOT lawyer-validated, NOT
legally-correct-by-guarantee, NOT production-certified, NOT universally generalizable.
