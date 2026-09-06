# Case 2 — Successful correction (the one natural shipped correction)

**Document ID:** `2003_760` &nbsp;·&nbsp; **Claim ID:** `c3` &nbsp;·&nbsp; **Source:** `research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` &nbsp;·&nbsp; **Regime:** final production (labeled, v0+v1 evidence, assertion_spans, narrow reverification)

This is **the only correction ever shipped on real natural NyayaRAG data** in this
project's history (1 of 56 natural correction attempts total — see
`reports/correction_safety_analysis.md`). It is presented as exactly that: n=1, not a
rate.

## Original field text (before correction)

> "The statutory grounding of the case involves the Indian Penal Code, 1860,
> specifically Sections 302 and 34. Section 302 deals with murder, which prescribes
> that whoever commits the act which causes the death of a human being with the
> intention to cause death or with the knowledge that such act will cause death,
> commits murder. Section 34 addresses criminal liability for an act done by more
> than one person in furtherance of the common intention or common object, thereby
> holding each person criminally responsible for the acts of others committed in
> furtherance of the common intention or object."

The flagged sentence (claim c3) restated Section 302 IPC's **definition** of murder,
not its **punishment** — evidence-inconsistent, flagged for correction.

## Corrected field text (after correction, shipped as `final_field`)

> "The statutory grounding of the case involves the Indian Penal Code, 1860,
> specifically Sections 302 and 34. Section 302 deals with murder, which prescribes
> that whoever commits murder shall be punished with death, or imprisonment for
> life, and shall also be liable to fine. Section 34 addresses criminal liability for
> an act done by more than one person in furtherance of the common intention or
> common object, thereby holding each person criminally responsible for the acts of
> others committed in furtherance of the common intention or object."

Only the flagged sentence changed. The corrector rewrote it to state Section 302
IPC's actual **punishment** clause, matching the matched evidence text almost
verbatim.

## Re-verification

| Field | Value |
|---|---|
| Reverified hypothesis | "Section 302 deals with murder, which prescribes that whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine." |
| Evidence ID | `Section 302 in The Indian Penal Code, 1860` |
| Verdict | **ENTAILED** |
| Confidence | 0.9946 |
| Sibling regressions | **none** (0 — the Section 34 claim, left untouched, was independently re-checked and still holds) |

## Final gate decision

`status == "corrected"` — shipped, because `reverification.verdict == "ENTAILED"`,
the only condition under which any correction is ever shipped in this system.

## Why it matters

This is the first (and, as of this pack, only) time in the project's history that a
real, non-synthetic correction was proposed, independently re-verified, found to
correctly preserve every other citation in the paragraph (`assertion_spans`
scope-check + sibling-regression re-check), and shipped. It demonstrates the full
7-stage pipeline working end-to-end on a genuine natural case, not a constructed
example.

**What this does NOT establish:** n=1 is not a success rate (see
`FINAL_PRODUCTION_CONFIG.md` §1's own stated caveat: 1/10 triggered on this batch,
recommended follow-up is a larger fresh batch before treating this as settled). No
lawyer has confirmed the corrected text is legally accurate — only that it now
matches the system's own third-party-sourced evidence text.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
