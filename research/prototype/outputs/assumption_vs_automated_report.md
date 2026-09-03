# Assumption Labels vs. Automated NLI Verdicts — Comparison Report

> **PROVISIONAL / ASSUMPTION-BASED.** Every number in this report is derived from
> `assumption_annotation.jsonl` -- Claude-generated provisional labels, not
> lawyer-verified ground truth. `lawyer_annotation.jsonl` has been temporarily
> populated with these same assumption values (`annotation_source:
> "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"`) purely as a stand-in so downstream
> tooling has something to run against while the real lawyer PDF is pending.
> **None of the metrics below may be reported, published, or cited as validated
> system accuracy.** They describe agreement/disagreement between two
> machine-produced label sets (an NLI classifier and an LLM assistant reading the
> same evidence text), not correctness against real legal ground truth.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

Claims compared: **88** (all from `gold_annotation.jsonl` / `assumption_annotation.jsonl`).
Claims with matched evidence (the only ones where `automated_verdict` is a real NLI call, not `NO_EVIDENCE`): **38**.

## 1. Assumption entailment vs. automated NLI

Cross-tabulation, evidence-matched claims only (`NO_EVIDENCE` claims are excluded --
both sides trivially agree there via the fixed no-evidence fallback, so they add no
signal):

| automated_verdict | assumption evidence_entails_claim | Count |
|---|---|---|
| NOT_ENOUGH_INFORMATION | CONTRADICTED | 2 |
| NOT_ENOUGH_INFORMATION | ENTAILED | 16 |
| NOT_ENOUGH_INFORMATION | NOT_ENOUGH_INFORMATION | 20 |

**Agreement: 20/38 = 52.6%. Disagreement: 18/38 = 47.4%.**

## 2. Assumption citation validity (all 88 claims)

| citation_valid | Count | % of 88 |
|---|---|---|
| YES | 36 | 40.9% |
| NO | 15 | 17.0% |
| UNKNOWN | 37 | 42.0% |

`UNKNOWN` dominates (claim absent from the 59-record evidence corpus, which does not prove it's an invalid citation -- see `assumption_annotation_summary.md`). `NO` marks claims where the assumption pass found the citation *extraction itself* clearly broken (wrong act attached, a year mistaken for a section number, etc.), independent of whether evidence was found.

## 3. Assumption evidence relevance

| evidence_relevance | Count | % of 88 | % of 38 evidence-matched |
|---|---|---|---|
| RELEVANT | 36 | 40.9% | 94.7% |
| NOT_RELEVANT | 2 | 2.3% | 5.3% |
| UNCERTAIN | 50 | 56.8% | n/a (mostly no-evidence claims) |

Of the 38 evidence-matched claims specifically: 36 RELEVANT, 2 NOT_RELEVANT.

## 4. Disagreement counts and percentages

- Comparable claims (evidence matched, so automated NLI actually ran): **38**
- Agreements: **20** (52.6%)
- Disagreements: **18** (47.4%)
- Disagreements as a share of all 88 claims: **18/88 = 20.5%**

## 5. Every disagreement (document_id, claim_id, reason)

| annotation_id | document_id | claim_id | automated_verdict | assumption evidence_entails_claim | reason |
|---|---|---|---|---|---|
| A0002 | 1992_534 | c2 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0023 | 2005_360 | c3 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0024 | 2005_360 | c4 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0029 | 1971_200 | c4 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0030 | 1971_200 | c5 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0039 | 1970_250 | c3 | NOT_ENOUGH_INFORMATION | CONTRADICTED | Assumption: matched evidence is on-topic (right section) but describes a different legal concept than what claim asserts, so it conflicts; NLI model called it neutral. |
| A0042 | 1971_379 | c2 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0043 | 1996_439 | c1 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0044 | 1996_439 | c2 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0045 | 1996_439 | c3 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0051 | 2003_967 | c2 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0067 | 2004_632 | c1 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0068 | 2004_632 | c2 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0069 | 2004_632 | c3 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0070 | 2004_632 | c4 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0071 | 2004_632 | c5 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0072 | 2004_632 | c6 | NOT_ENOUGH_INFORMATION | ENTAILED | Assumption: evidence directly confirms claim's specific assertion; NLI model called it neutral (likely low-confidence-on-neutral pattern, not a downgrade). |
| A0078 | 2023_26 | c6 | NOT_ENOUGH_INFORMATION | CONTRADICTED | Assumption: matched evidence is for the WRONG act (act-misattribution bug fed wrong-act evidence in) and directly conflicts with claim's specific assertion; NLI model called it neutral. |

## 6. Parser / evidence-matching problems identified (separate from NLI disagreement)

These are extraction/matching-pipeline bugs the assumption pass surfaced while reading `claim_text` against `extracted_citation` and `matched_evidence_text` -- distinct from any disagreement with the NLI model above. **15 claims** were marked `citation_valid=NO` for this reason (see `assumption_annotation_summary.md`, "Extraction bugs found", for full detail on each pattern):

| annotation_id | document_id | claim_id | extracted_citation act_raw (as captured) | problem type |
|---|---|---|---|---|
| A0006 | 2007_1517 | c1 | 'the Indian Penal Code and Section 5(2) read with Section 1(d) of the Prevention of Corruption Act, 1947' | multi-act run-on sentence: wrong act attached (bled in from a later clause) |
| A0007 | 2007_1517 | c2 | 'the Indian Penal Code and Section 5(2) read with Section 1(d) of the Prevention of Corruption Act, 1947' | multi-act run-on sentence: wrong act attached (bled in from a later clause) |
| A0008 | 2007_1517 | c3 | 'the Indian Penal Code and Section 5(2) read with Section 1(d) of the Prevention of Corruption Act, 1947' | multi-act run-on sentence: two acts merged into one act_norm string |
| A0009 | 2007_1517 | c4 | 'the Indian Penal Code and Section 5(2) read with Section 1(d) of the Prevention of Corruption Act, 1947' | multi-act run-on sentence: two acts merged into one act_norm string |
| A0010 | 2007_1517 | c5 | 'the Indian Penal Code and Section 5(2) read with Section 1(d) of the Prevention of Corruption Act, 1947' | multi-act run-on sentence: two acts merged into one act_norm string |
| A0050 | 2003_967 | c1 | 'the Constitution of India' | year ('2000') mistaken for a provision number; act field wrongly inherited from an unrelated citation |
| A0055 | 1989_184 | c3 | 'the Arms Act require the lawful possession and use of firearms and impose penalties for their unlawful possession or use' | trim heuristic failed: rest of sentence swallowed into act name |
| A0056 | 1989_184 | c4 | 'the Arms Act require the lawful possession and use of firearms and impose penalties for their unlawful possession or use' | trim heuristic failed: rest of sentence swallowed into act name |
| A0073 | 2023_26 | c1 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC |
| A0074 | 2023_26 | c2 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC (matched wrong-act CrPC evidence) |
| A0075 | 2023_26 | c3 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC |
| A0077 | 2023_26 | c5 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC |
| A0078 | 2023_26 | c6 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC (matched wrong-act CrPC evidence) |
| A0079 | 2023_26 | c7 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC |
| A0080 | 2023_26 | c8 | 'the Code of Criminal Procedure, 1973' | field-wide act fallback wrongly overrode an explicit in-sentence IPC attribution with CrPC |

Separately, **2 claims** had evidence *matched* (so no NO_EVIDENCE gap) but judged `evidence_relevance=NOT_RELEVANT` -- i.e. the matcher attached a real record for the wrong act/section, a direct consequence of the act-attribution bug above (both of these are `2023_26` claims already listed in the table: the ones whose act was wrongly rewritten to CrPC and then genuinely matched CrPC's Section 302 record instead of IPC's).

**These are source-code (`claim_parser.py`) observations only -- no source code was modified in this task.** They are flagged here for a future fix, not acted on.

## 7. Development metrics (provisional, from assumption labels only)

> These are **not validated accuracy figures**. They measure internal consistency
> between two machine-generated label sets over a 88-claim / 30-case sample drawn
> from a 59-record third-party evidence corpus that is itself only 39.7%
> byte-verbatim-verified (see `research/data/evidence/README.md`). Treat as
> pipeline-debugging signal only, pending the lawyer's real annotation.

- **Coverage** (claims with matched evidence / total): 38/88 = 43.2%
- **Citation validity rate** (assumption `citation_valid=YES` / total): 36/88 = 40.9% (NO=15, UNKNOWN=37)
- **Evidence relevance rate** (assumption `RELEVANT` / claims with evidence): 36/38 = 94.7% (NOT_RELEVANT=2)
- **Entailment agreement with automated NLI** (matching label / claims with evidence): 20/38 = 52.6%
- **Contradiction detection (recall)**: of 2 claims the assumption pass labeled CONTRADICTED, automated NLI also flagged CONTRADICTED for 0/2 = 0%

## Reminder

`lawyer_annotation.jsonl` currently holds these same assumption values as a **temporary stand-in** (`annotation_source: "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"` on every record) so downstream tooling has something to run against. **It must be overwritten with the lawyer's real judgments from the annotated PDF as soon as that is available, and nothing in this report should be cited outside this project as validated system accuracy until that happens.**
