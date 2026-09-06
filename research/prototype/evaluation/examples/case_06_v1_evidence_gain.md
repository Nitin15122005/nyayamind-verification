# Case 6 — Evidence successfully retrieved by the v1 supplement

**Document ID:** `1971_200` &nbsp;·&nbsp; **Claim ID:** `c3` &nbsp;·&nbsp; **Source of the claim:** `research/prototype/outputs/run_A_n30.jsonl` &nbsp;·&nbsp; **Coverage comparison source:** `research/prototype/outputs/evidence_coverage_v0_vs_v1.json`

## Claim (model-generated)

> "The statutory grounding for this case includes the Indian Penal Code, specifically
> Sections 120B, 420, and 467."

**Citation extracted:** Section 467, Indian Penal Code, 1860.

## Before the v1 supplement (`use_evidence_v1: false`, v0-only 59-record pool)

Section 467 IPC is not among v0's top-63-by-frequency provisions → **NO_EVIDENCE**.

## After the v1 supplement (`use_evidence_v1: true`, 136-record production pool)

**New evidence ID:** `Section 467 in The Indian Penal Code, 1860` — one of the 79
genuinely new citation keys v1 adds (ranks #64-143 by the same frequency ranking
method v0 used, never chosen based on any claim's content or verdict — see
`research/data/evidence/README_v1.md` "Target selection (no outcome leakage)"). The
claim now resolves to a real, independently-sourced evidence record instead of
NO_EVIDENCE — whether the verifier then finds it ENTAILED, CONTRADICTED, or NEI is a
separate question this specific example is not about; the point is that it can now be
*checked at all*.

## Why it matters

This is one of 36 claims (out of 588 checked, same claims, two evidence pools) that
moved from NO_EVIDENCE to evidence-matched purely by adding the v1 supplement — part
of the measured **+7.1 percentage-point coverage gain** (63.2%→70.3% on the paired
final-validation batch, McNemar χ²=13.07, p≈0.0003, zero regressions — see
`reports/retrieval_analysis.md`). It illustrates concretely what "evidence coverage"
means in practice: a claim the v0-only system could not check at all becomes
checkable once its provision is added to the corpus.

**What this does NOT establish:** that Section 467 IPC's stored text is itself
error-free — v1's independent audit re-fetched 50% of its 82 records directly and
found the corpus's text accurate wherever re-checked, but this specific record's
verbatim/summarized status and confidence level are documented in
`research/data/evidence/canonical_statutes_v1.jsonl` and its audit record, not
repeated here.
