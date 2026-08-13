# Gold Annotation Guide — Statutory Claim Verification

## What you are judging

Each row in `gold_annotation.jsonl` is ONE extracted claim: a sentence
(`claim_text`) from a machine-generated "Statutory Grounding" paragraph,
naming a specific statute/article (`extracted_citation`), together with
whatever canonical evidence text the system matched for that citation
(`matched_evidence_text`, or null if none was found).

You are asked for THREE independent judgments per claim, plus free-text
notes. There is no single "correct" field — judge each one on its own
terms, as described below.

**Judge ONLY against `matched_evidence_text`.** Do not use outside legal
knowledge, do not look up the actual statute elsewhere, do not consider
whether the underlying case was decided correctly, and do not use
`claim_text`'s surrounding case facts to guess at intent. If
`matched_evidence_text` does not settle a question, the answer is
"the evidence does not tell us" (NOT_ENOUGH_INFORMATION / UNCERTAIN), even
if you personally know the real statute says something else. This dataset
evaluates the PIPELINE (does it find and use the RIGHT evidence text
correctly), not your independent knowledge of Indian law.

**Do not look at `automated_verdict` / `automated_confidence` before
forming your own judgment.** They are included for later agreement
analysis, not as a suggestion. Read `claim_text` and
`matched_evidence_text` first, decide your own answer, and only then
(optionally) compare against the automated fields if you want to note a
disagreement in `annotator_notes`.

## Fields to fill in (all four start blank)

### 1. `citation_valid` — YES / NO / UNCERTAIN
Does `claim_text` genuinely, unambiguously reference the citation recorded
in `extracted_citation` (same provision type, number, and act)? This
checks the EXTRACTION, not the evidence match — you can answer this from
`claim_text` and `extracted_citation` alone, without looking at
`matched_evidence_text` at all.
- **YES**: the citation is clearly and correctly identified from the text.
- **NO**: the citation is wrong, garbled, or not actually present in
  `claim_text` (e.g. wrong section number extracted, act misattributed).
- **UNCERTAIN**: genuinely ambiguous phrasing in `claim_text` itself.

### 2. `evidence_entails_claim` — ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION / UNCERTAIN
Does `matched_evidence_text` support what `claim_text` asserts about that
provision?
- **ENTAILED**: the evidence text confirms the assertion in `claim_text`.
- **CONTRADICTED**: the evidence text states something that conflicts with
  the assertion in `claim_text`.
- **NOT_ENOUGH_INFORMATION**: the evidence text is on-topic but doesn't
  confirm or conflict with the specific assertion — OR
  `matched_evidence_text` is null (no evidence was matched at all: there
  is nothing to entail or contradict against, so this is the correct
  answer by construction, not a judgment call).
- **UNCERTAIN**: you cannot decide even after re-reading both texts
  carefully (rare — prefer NOT_ENOUGH_INFORMATION when the issue is
  "insufficient support" rather than "genuinely unclear wording").

### 3. `evidence_relevance` — RELEVANT / NOT_RELEVANT / UNCERTAIN
Independent of entailment: is `matched_evidence_text` actually about the
SAME provision `claim_text` cites, or did the evidence matcher attach the
wrong statute/section (this can happen especially for `fuzzy`-matched
rows)? A claim can be `evidence_relevance: NOT_RELEVANT` even if
`evidence_entails_claim` happens to look plausible by coincidence, and
vice versa — a relevant match can still fail to entail the claim.
- **RELEVANT**: the evidence text is genuinely about the cited provision.
- **NOT_RELEVANT**: the evidence text is about a different provision/act
  than the one `claim_text` cites (a bad match).
- **UNCERTAIN**: can't tell from the text alone.
- If `matched_evidence_text` is null (`evidence_match_method: no_evidence`),
  there is nothing to assess — use **UNCERTAIN** and note "no evidence
  matched" in `annotator_notes`.

### 4. `annotator_notes` — free text
Optional. Use for: disagreements with `automated_verdict`, ambiguous
phrasing you had to make a judgment call on, suspected extraction bugs,
or anything else worth flagging for review. Leave blank if nothing to add.

## What NOT to do
- Do not fill in a "correct final answer" for the claim — there is no such
  field, and none of A/B/C's final output/correction result is shown to
  you (deliberately, to avoid anchoring your judgment on what the system
  already decided to do).
- Do not edit `claim_text`, `extracted_citation`, or
  `matched_evidence_text` — annotate, don't correct the data.
- Do not skip rows with `matched_evidence_text: null` — `citation_valid`
  is still answerable from `claim_text` alone; the other two fields have
  the documented fallback answers above.

## Field reference
| Field | Source | Editable by annotator? |
|---|---|---|
| `annotation_id`, `document_id`, `claim_id` | pipeline output | No |
| `claim_text`, `extracted_citation` | pipeline output | No |
| `matched_evidence_text`, `evidence_match_method` | pipeline output | No |
| `automated_verdict`, `automated_confidence` | pipeline output (reference only) | No |
| `annotation.citation_valid` | **you fill in** | Yes |
| `annotation.evidence_entails_claim` | **you fill in** | Yes |
| `annotation.evidence_relevance` | **you fill in** | Yes |
| `annotation.annotator_notes` | **you fill in** | Yes |
