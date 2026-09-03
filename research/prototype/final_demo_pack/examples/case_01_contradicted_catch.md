# Case 1 — Genuine CONTRADICTED catch

**Document ID:** `1997_1306` &nbsp;·&nbsp; **Claim ID:** `c6` &nbsp;·&nbsp; **Source:** `research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl` &nbsp;·&nbsp; **Framing:** labeled

## Original claim (model-generated)

> "Section 148 mandates punishment for criminal trespass, section 304 (Part-I) and
> 304 (Part-II) deal with culpable homicide not amounting to murder and voluntary
> manslaughter respectively, section 323 prescribes punishment for voluntarily
> causing hurt, and section 149 provides for the liability of every member of an
> unlawful assembly to the acts done by any one of them in the common object of the
> assembly."

**Citation extracted:** Section 148, Indian Penal Code, 1860 (the first citation in
this bundled sentence — this is a documented v0 simplification: one claim per
sentence, first citation only).

## Evidence matched

**Evidence ID:** `Section 148 in The Indian Penal Code, 1860` (match method: `exact_normalized`)

> "Whoever is guilty of rioting, being armed with a deadly weapon or with anything
> which, used as a weapon of offence, is likely to cause death, shall be punished
> with imprisonment of either description for a term which may extend to three
> years, or with fine, or with both."

## Verifier result

| Field | Value |
|---|---|
| Verdict | **CONTRADICTED** |
| Confidence | 0.987 |
| Model | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` |

## Correction / re-verification / gate

Not applicable to this record as retrieved (this run was Mode B/verification-only for
this batch; no correction attempt is attached to this particular claim in the source
file). See Case 2/3 for correction-path examples.

## Why it matters

The claim states Section 148 IPC is about **"criminal trespass."** The matched,
independently-sourced evidence text for Section 148 IPC is actually about **rioting
while armed with a deadly weapon** — a different offence entirely. The mismatch
between what the generated sentence *claims* the section says and what the section's
own text (per this project's evidence corpus) *actually* says is exactly the failure
mode this system is built to catch, and it did so with a high-confidence verdict.

**What this does NOT establish:** the verifier's CONTRADICTED verdict is a small NLI
model's statistical judgment against a third-party (IndianKanoon), not
official-India-Code, evidence corpus — not a lawyer-confirmed legal-accuracy ruling.
No lawyer has reviewed this specific case.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
