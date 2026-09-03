# Case 3 — Correction attempted, correctly rejected (not shipped)

**Document ID:** `2008_2063` &nbsp;·&nbsp; **Claim ID:** `c9` &nbsp;·&nbsp; **Source:** `research/prototype/outputs/natural_candidates_batch2_gpu_corrections_detail.jsonl` &nbsp;·&nbsp; **Framing:** labeled

## Original field text

> "The case is governed by the Indian Penal Code, 1860, specifically Sections 302,
> 307, 143, 147, 148, 149, and 452, which respectively deal with murder, attempt to
> murder, criminal force to deter public servant from discharging his duty, rioting,
> unlawful assembly, aggregation of offenders, and criminal trespass, among others.
> Section 302 requires proof of the intentional killing of a person, while Sections
> 307 and 143-149 deal with attempts, criminal force, and rioting, which are relevant
> to the facts of the case."

## Regenerated text (correction attempt)

> "... Section 302 requires proof of the intentional killing of a person, **which is
> the charge in this case**, while Sections 307 and 143-149 deal with attempts,
> criminal force, and rioting, which are relevant to the facts of the case."

(Only the italicized addition changed; the rest of the paragraph is identical.)

## Re-verification of the corrected sentence

| Field | Value |
|---|---|
| Reverified claim text | "Section 302 requires proof of the intentional killing of a person, which is the charge in this case, while Sections 307 and 143-149 deal with attempts, criminal force, and rioting, which are relevant to the facts of the case." |
| Evidence ID | `Section 307 in The Indian Penal Code, 1860` |
| Verdict | **CONTRADICTED** |
| Confidence | 0.935 |
| Unflagged claims checked / preserved | 9 / 7 |

## Final gate decision

`status == "correction_failed"` — **not shipped**. The corrector's edit did not bring
the flagged sentence into agreement with its own matched evidence (Section 307 IPC);
re-verification found it still CONTRADICTED at high confidence, so the
`status=="corrected" ⟺ reverification.verdict=="ENTAILED"` gate rejected it and the
**original**, unmodified text was kept as `final_field`.

## Why it matters

This shows the safety gate is not a rubber stamp: the model was given a chance to
fix a flagged claim, produced an edit, and the pipeline's own re-verification step
caught that the edit still didn't hold up against the evidence — so nothing was
shipped. This is one of 37 `correction_failed` outcomes out of 56 total natural
correction attempts (see `reports/correction_safety_analysis.md`); it is shown here
as a concrete instance of that category, not as evidence about how often correction
attempts fail.

**What this does NOT establish:** that the *original* sentence (also unverified by a
lawyer) was itself correct — only that the proposed *edit* did not pass the system's
own re-verification.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
