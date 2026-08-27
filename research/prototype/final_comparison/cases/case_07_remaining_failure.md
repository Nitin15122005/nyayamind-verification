# Case 7 — An important remaining failure: correction still cannot fix a diagnosed error

**Selection criterion**: the same triggered case tested under both arms of
`final_gpu_validation`, chosen because it shows CURRENT's genuine diagnostic improvement
(narrow reverification) **and** the fact that this diagnostic improvement did not translate
into a fix — the underlying claim-bundling structural problem this project has documented
throughout its history is still present under the full CURRENT config.

**Source**: `outputs/final_gpu_validation_corrections_detail.jsonl`,
`document_id="2004_1020"`, `triggered_for_claim_id="c6"`.

| | ORIGINAL | CURRENT (retrieval/scope/narrow-reverify, still bare) |
|---|---|---|
| Original flagged sentence | "Section 147 IPC deals with the unlawful assembly with intent to commit a felony or to cause fear or violence, Section 323 IPC pertains to voluntarily causing hurt, Section 302 IPC defines murder, and Section 34 IPC provides for liability for acts done by several persons in furtherance of a common intention." | *(identical)* |
| Qwen's regenerated text | **Byte-identical to the original** — Qwen returned a no-op | **Byte-identical to the original** — same no-op |
| Reverification hypothesis | Full bundled sentence | Narrow `assertion_text`: "Section 323 IPC pertains to voluntarily causing hurt" |
| Reverification verdict | NOT_ENOUGH_INFORMATION, 0.6650 (low-confidence, threshold-adjacent) | **CONTRADICTED, 0.9175** (decisive) |
| Final status | `correction_failed` | `correction_failed` |
| Unflagged claims preserved | 7/7 | 7/7 |

## What actually improved, and what did not

`narrow_reverification_hypothesis` converts a diluted, borderline-low-confidence NEI into a
decisive CONTRADICTED — a real, measurable improvement in **diagnostic quality**: the
system now states with high confidence that the unchanged sentence is still wrong, rather
than a threshold-adjacent "not sure." **But the shipped-vs-not-shipped outcome is
identical**: `correction_failed` in both arms, because Qwen did not actually produce an
edit to re-verify (a no-op regeneration, not a scope or safety rejection). Neither ORIGINAL
nor CURRENT can ship a fix here — the corrector model simply failed to make one.

## Why this is the important remaining failure, not a cherry-picked worst case

This pattern (Qwen returning the flagged sentence unchanged) recurs across this project's
history and is one of two dominant blockers behind the still-low overall correction-shipped
rate: **1.8% cumulative across 56 real natural attempts** (`correction_results.csv`), and
**10% at best** even under the full CURRENT config's most favorable, targeted validation
(`case_04`). The other dominant blocker — claim bundling causing scope violations — is
shown in `case_05`. Together, these two failure modes account for the bulk of
`correction_failed`/`correction_scope_violation` outcomes (`safety_results.csv`:
37 + 18 = 55 of 56 cumulative natural attempts did not ship).

## What this means for the comparison

CURRENT's correction-path improvements (scope check, narrow reverification) make the
system's *reasoning* more legible and better-calibrated, but they do not yet fix the
generator's own reluctance to make a real edit, nor the structural problem of one sentence
serving multiple citations. This is an honestly-reported open problem, not resolved by any
change measured in this comparison — see `final_limitations_and_future_scope.md` and
`FINAL_BASELINE_COMPARISON.md`'s "What still requires lawyer ground truth" /
"remaining weaknesses" sections.

## Reproduce

```
python -c "
import json
recs=[json.loads(l) for l in open('research/prototype/outputs/final_gpu_validation_corrections_detail.jsonl', encoding='utf-8')]
for r in recs:
    if r['document_id']=='2004_1020':
        print(r['arm'], r['status'], r['reverification']['verdict'], r['reverification']['confidence'])
"
```
