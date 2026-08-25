# Provisional Assumption Annotation — Summary

> **These annotations are provisional assumptions for development/evaluation
> preparation only. They are NOT lawyer-verified ground truth. Final human
> labels will be obtained from the lawyer-provided annotated PDF.**

This document summarizes `assumption_annotation.jsonl`, produced by
independently judging each of the 88 statutory claims in
`gold_annotation.jsonl` against `matched_evidence_text` only (never outside
legal knowledge, never `claim_text`'s underlying case facts, and never a
copy of `automated_verdict`), per the instructions in
`gold_annotation_guide.md`. Every original field from `gold_annotation.jsonl`
is preserved unchanged; a new `assumption_annotation` object was appended to
each record, and the original (blank) `annotation` block was left untouched.

`citation_valid` in this pass uses a corpus-representation definition (not
the extraction-accuracy definition in `gold_annotation_guide.md`):
**YES** only when the citation is genuinely represented by a matched
canonical evidence record; **UNKNOWN** when the citation is simply absent
from this 59-record development corpus (which does not prove it's
invalid); **NO** reserved for cases where the citation extraction itself is
clearly broken (wrong act attached, a year mistaken for a provision number,
etc.) — a corpus/parser observation, not a legal-validity judgment.

## Headline counts

| Metric | Count |
|---|---|
| Total claims | 88 |
| Claims with matched evidence | 38 (43.2%) |
| Claims without matched evidence | 50 (56.8%) |

### `citation_valid`

| Value | Count | Meaning here |
|---|---|---|
| YES | 36 | Citation genuinely represented by a matched canonical evidence record |
| UNKNOWN | 37 | No evidence in the 59-record corpus (28), or a plausible-but-unresolved act reference (9) — absence is not proof of invalidity |
| NO | 15 | A clear extraction/parser bug (wrong act attached, or a year mistaken for a provision number) — see "Extraction bugs found" below |

### `evidence_entails_claim`

| Value | Count |
|---|---|
| NOT_ENOUGH_INFORMATION | 70 |
| ENTAILED | 16 |
| CONTRADICTED | 2 |
| (UNCERTAIN) | 0 |

### `evidence_relevance`

| Value | Count |
|---|---|
| RELEVANT | 36 |
| UNCERTAIN | 50 |
| NOT_RELEVANT | 2 |

All 50 no-evidence rows use the documented fallback
(`evidence_entails_claim=NOT_ENOUGH_INFORMATION`,
`evidence_relevance=UNCERTAIN`) per the annotation guide — these are not
independent judgment calls, they are the correct answer "by construction"
when `matched_evidence_text` is null.

## Comparison against automated NLI verdicts

`automated_verdict` in this 88-claim sample only ever takes two values:
`NOT_ENOUGH_INFORMATION` (38 claims, one for every evidence-matched claim —
the NLI model never predicted ENTAILED or CONTRADICTED here) and
`NO_EVIDENCE` (50 claims). The cross-tabulation against this pass's
independent `evidence_entails_claim` judgment:

| automated_verdict | assumption evidence_entails_claim | Count |
|---|---|---|
| NOT_ENOUGH_INFORMATION | NOT_ENOUGH_INFORMATION | 20 |
| NOT_ENOUGH_INFORMATION | ENTAILED | 16 |
| NOT_ENOUGH_INFORMATION | CONTRADICTED | 2 |
| NO_EVIDENCE | NOT_ENOUGH_INFORMATION | 50 |

### Disagreements (18 of 38 evidence-matched claims, 47%)

Every disagreement is among the 38 evidence-matched claims (the 50
NO_EVIDENCE claims can't disagree — both sides use the fixed fallback).

- **16 claims where this pass says ENTAILED but the NLI model said NEI.**
  These are mostly claims with a tight, specific factual assertion that the
  matched evidence text directly and simply states (e.g. "Section 302
  prescribes the punishment for murder" against evidence that is exactly
  the Section 302 punishment sentence; "Section 109... pertains to the
  liability of an abetter" against the Section 109 abetment text). The
  small public NLI model used by the pipeline appears to be conservative /
  under-confident on this kind of short statute-paraphrase pair, most
  likely because `verifier.py`'s confidence-threshold downgrade rule turns
  any low-confidence entailment prediction into NEI (`sub_reason:
  "low_confidence"`), and per `eval_30_report.md` every one of the 38
  matched-evidence verdicts in this run had `sub_reason: None` at *high*
  confidence (mean 0.989) — meaning the model's raw argmax class itself was
  "neutral", not that entailment was downgraded. This is a genuine
  candidate NLI-model weakness worth flagging for the lawyer's review, not
  a labeling inconsistency in this pass.
  Affected: A0002, A0023, A0024, A0029, A0030, A0042, A0043, A0044, A0045,
  A0051, A0067, A0068, A0069, A0070, A0071, A0072.
- **2 claims where this pass says CONTRADICTED but the NLI model said NEI:**
  - **A0039** (`1970_250`, c3): claim asserts "Section 201... pertain[s] to
    abetment"; the matched Section 201 evidence is actually about causing
    evidence of an offence to disappear / screening an offender — a
    different subject from abetment.
  - **A0078** (`2023_26`, c6): claim asserts "Section 302 prescribes the
    punishment for murder", but — due to an upstream extraction bug (see
    below) — the evidence actually matched is CrPC §302 ("permission to
    conduct prosecution"), which has nothing to do with murder.
- **0 claims where this pass says NOT_ENOUGH_INFORMATION but the NLI model
  disagreed** — every remaining evidence-matched claim (20 of 38) agrees
  with the automated NEI verdict, generally because the claim only makes a
  generic "grounding/applies to this case" assertion that no statute
  excerpt alone could confirm, or because the claim adds a specific
  legal-elements/mens-rea/standard-of-proof detail the matched evidence
  text simply doesn't state.

## Extraction bugs found (citation_valid = NO, 15 claims)

Reviewing every claim against its own `claim_text` and `extracted_citation`
surfaced three distinct `claim_parser.py` failure patterns, independent of
the evidence corpus:

1. **Multi-act run-on sentence act-bleed** (`2007_1517`, A0006–A0010): one
   sentence names three different instruments (a UCB Regulation, a UCO Bank
   Manual, the IPC, and the Prevention of Corruption Act). The act-name
   capture for `Regulation 15(2)` and `Clause 22` was pulled from a much
   later clause in the sentence and attached the wrong act entirely (IPC +
   POCA instead of the actual UCB Regulation / UCO Bank Manual); the IPC
   sections in the same sentence (120-B, 471, 477) also ended up with a
   garbled two-act-merged `act_norm` string.
2. **Year mistaken for a provision number** (`2003_967`, A0050): "the Post
   Graduate Medical Education Regulations 2000" was parsed as `provision_type:
   Regulation, provision_number: 2000` (the year, not a real regulation
   number), and the act was wrongly field-wide-inherited as "Constitution
   of India" from an unrelated Article 14 citation elsewhere in the same
   field.
3. **Trim-heuristic failure swallowing the rest of the sentence**
   (`1989_184`, A0055–A0056): "the Arms Act require the lawful possession
   and use of firearms and impose penalties..." was captured whole as the
   act name because none of `_trim_act_name`'s three rules (year /
   continuation-verb / comma+lowercase) fired on this exact phrasing.
4. **Field-wide single-act fallback overriding an explicit in-sentence act**
   (`2023_26`, A0073, A0074, A0075, A0077, A0078, A0079, A0080): the
   sentence explicitly attributes Sections 148, 302, 304 Part II, and 324
   to "The Indian Penal Code, 1860" and only Section 149 to "the Code of
   Criminal Procedure, 1973" — but all five IPC sections were extracted
   with act = CrPC 1973, apparently because CrPC was the only act that
   resolved unambiguously anywhere in the field. Two of these
   (A0074, A0078) then matched real — but wrong-act — CrPC §302 evidence
   ("permission to conduct prosecution"), which is unrelated to murder;
   A0078 is the CONTRADICTED case described above.

These are genuine, reproducible bugs in `claim_parser.py`'s act-name
resolution on long/multi-act sentences, surfaced as a byproduct of this
annotation pass. They were **not fixed** here per the task's constraint not
to modify source code — flagging them for a future `claim_parser.py` fix is
the appropriate next step, not a code change in this pass.

## Limitations

- **Not lawyer-verified.** Every judgment here was made by an AI assistant,
  reading only `claim_text` and `matched_evidence_text`, with no legal
  training and no access to the actual case documents, the real statute
  text, or Indian case law. It is a development/QA aid, not ground truth.
- **Evidence corpus itself is not gold.** Per
  `research/data/evidence/README.md`, the 59-record usable corpus behind
  `matched_evidence_text` is only 39.7% `VERIFIED_EXACT` against its
  third-party (IndianKanoon) source; the rest is `VERIFIED_CONTENT`
  (paraphrased/restructured) or worse. An `ENTAILED`/`CONTRADICTED` call
  made here reflects the *stored* evidence text, which may itself be a
  paraphrase of the real provision, not the provision's literal wording.
- **No case-fact or outside-law verification.** Per the guide, claims like
  "the case was governed by Section X" were judged as NOT_ENOUGH_INFORMATION
  whenever they made no checkable substantive assertion, deliberately
  *not* verified against the real case or real statute — that is out of
  scope for this evidence-only pass.
- **Single-annotator, single-pass.** No second reviewer, no adjudication,
  no inter-annotator agreement statistics. Treat disagreement counts above
  as descriptive of one AI reviewer's reading, not as an established error
  rate.
- **Small, skewed sample.** 88 claims from 30 cases, all citation types
  weighted heavily toward IPC/Constitution provisions already in the
  top-100 corpus; findings (e.g. the NLI model's apparent conservatism)
  should not be generalized beyond this sample without a larger run.
- **`citation_valid` here is a different question than in
  `gold_annotation_guide.md`.** The guide's original definition asks
  "does `claim_text` genuinely reference `extracted_citation`"; this pass's
  task instructions redefine it around corpus representation instead (see
  above). Anyone consuming this file for another purpose should re-read the
  field's actual definition here rather than assume the guide's.
