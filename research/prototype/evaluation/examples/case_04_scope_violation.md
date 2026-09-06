# Case 4 — Scope violation (unflagged claim damaged, correction discarded)

**Document ID:** `2009_865` &nbsp;·&nbsp; **Claim ID:** `c2` &nbsp;·&nbsp; **Source:** `research/prototype/outputs/natural_candidates_50_gpu_corrections_detail.jsonl` &nbsp;·&nbsp; **Framing:** labeled

## Original field text

> "The Indian Penal Code, 1860, specifically Sections 302 and 324 read with Section
> 34, require that an individual be held criminally responsible for causing death of
> another person through intentional acts or by criminal negligence, and for causing
> injury leading to death, respectively, while acting in concert with others as
> provided in Section 34."

Three citations share this one sentence: Section 302, Section 324, Section 34.

## Regenerated text (correction attempt)

> "The Indian Penal Code, 1860, specifically Sections 302 and 34, require that an
> individual be held criminally responsible for causing death of another person
> through intentional acts or by criminal negligence, and for acting in concert with
> others as provided in Section 34, respectively."

**Section 324 — and the entire clause about "causing injury leading to death" —
disappeared from the rewritten sentence.** The corrector was asked to fix the
sentence's flagged portion, but its rewrite silently dropped an unrelated,
*unflagged* citation instead of leaving it untouched.

## Scope-violation check

| Field | Value |
|---|---|
| Unflagged claims checked | 3 |
| Unflagged claims preserved | **0** |
| Reverification | not run — the pipeline discards the correction before reaching re-verification once a scope violation is detected |

## Final gate decision

`status == "correction_scope_violation"` — **not shipped**. The programmatic
scope-violation gate (`src/pipeline.py::_scope_violation`, checked against each
unflagged claim's `assertion_spans` under the `assertion_spans` scope-check mode)
detected that Section 324's citation no longer appears in the corrected text, so the
entire correction was discarded and the **original** text was kept as `final_field`.

## Why it matters

This is exactly the failure mode the scope-violation gate exists to catch: a
correction that fixes what it was asked to fix but, as a side effect, deletes or
alters something it wasn't asked to touch. The gate is enforced **programmatically**
(a verbatim-substring check), not by asking the model nicely — this case shows it
actually firing on real model output, not just existing in theory. It is one of 18
`correction_scope_violation` outcomes out of 56 natural correction attempts (see
`reports/correction_safety_analysis.md`).
