# PROVISIONAL Inputs

**No files are copied here, and none should ever be.** This directory documents, by
reference only, the three datasets in this project that carry provisional,
non-independently-verified labels — specifically so a future contributor has a positive,
documented place to look and finds an explicit warning, rather than silently
rediscovering these files unlabeled somewhere in `outputs/`.

## The three datasets

| File | Records | Self-tagged as |
|---|---|---|
| `research/prototype/outputs/gold_annotation.jsonl` | 88 | template only — annotation fields are empty strings, never filled in by anyone |
| `research/prototype/outputs/lawyer_annotation.jsonl` | 88 | `annotation_source: "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"` on every record |
| `research/prototype/outputs/assumption_annotation.jsonl` | 88 | same self-tag; same underlying claim_id sequence as `lawyer_annotation.jsonl` — a later iteration of the same batch, not new data |

Confirmed directly by reading the `annotation_source` field on real records, not by
trusting a doc's claim about them (STEP 0 dataset-inventory finding).

## Non-negotiable rule

**No real lawyer or human ground truth exists anywhere in this project.** These are
Claude-generated provisional guesses about verdicts. They must never be:
- copied into `../gold/`,
- described as "expected output," "ground truth," or "validated" in any report,
- used as the denominator or reference in an accuracy calculation,
- silently relabeled if a future annotation pass fills in the empty `gold_annotation.jsonl`
  template — even a completed version of that template would need its own, separately
  documented provenance (who annotated it, when, under what protocol) before it could be
  considered for GOLD status, and that decision belongs to a future step, not this one.

## What these files are legitimately useful for

Methodology/process transparency (showing what a human-annotation protocol was designed
to look like — `outputs/lawyer_annotation_guide.md`), and — with explicit, repeated
caveats — an *agreement* measurement against the automated verifier's own verdicts
(`outputs/assumption_gold_bare_vs_labeled_metrics.json`: labeled framing agrees
*slightly less*, 47.4% vs. bare's 52.6%, the opposite direction from every other
convergent finding in this project — reported honestly, not suppressed, in
`FINAL_PRODUCTION_CONFIG.md`). This is an agreement-with-a-guess number, not an accuracy
number.

## Classification

**PROVISIONAL**, permanently, unless and until a real, independently-documented human
annotation process produces a genuinely new artifact — which this step does not do and
is not authorized to do (rule 5 of this step's non-negotiable research rules: do not
create, infer, or manufacture new ground-truth labels).
