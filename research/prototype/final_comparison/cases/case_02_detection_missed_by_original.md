# Case 2 — Genuine detection missed by ORIGINAL, caught by CURRENT

**Selection criterion**: from the same 15-flip list, the one case where the flip direction
is toward CONTRADICTED rather than ENTAILED — i.e. a genuine detection event, not just a
confirmation. This is the only such case in the flip list; it is shown, not cherry-picked
among alternatives, because it is the single available example of this category.

**Source**: `outputs/final_validation_bare_vs_labeled_cpu_metrics.json` → `flips[5]`
(`document_id="2006_1150"`, `claim_id="c12"`).

| | ORIGINAL (`bare`) | CURRENT (`labeled`) |
|---|---|---|
| Claim text | "Section 420 criminalizes cheating, Section 467 and 468 deal with forgery and criminal conspiracy respectively, and Section 471 pertains to the use of a forged document." | *(identical)* |
| Evidence | `Section 468 in The Indian Penal Code, 1860` | *(identical)* |
| Verdict | **NOT_ENOUGH_INFORMATION** (0.9131) | **CONTRADICTED** (0.8111) |

## What changed and why

Section 468 IPC is "forgery for purpose of cheating," not "criminal conspiracy" — the
claim's gloss ("forgery and criminal conspiracy respectively") misattributes the wrong
concept to this citation (conspiracy is properly Section 120B, a *different* citation in
the same bundled sentence — see `case_07` for how this bundling pattern also defeats
correction). Under `bare` framing the mismatch is diluted enough to stay at NEI; under
`labeled` framing, prepending "Section 468 in The Indian Penal Code, 1860:" to the premise
sharpens the model's read of what the evidence is actually about, and it now flags the
"conspiracy" gloss as contradicted.

## Honest caveat

This is the **only** ORIGINAL-misses/CURRENT-catches CONTRADICTED flip in the entire
147-claim paired re-verification — not a rate, a single instance. The reverse direction (a
claim CONTRADICTED under bare that becomes NEI under labeled) also occurs once in this same
147-claim set (`2021_11`/c3, confidence 0.984→0.965) — see `ablation_results.csv`'s framing
row, "1 CONTRADICTED->NEI reversal also occurred." Labeled framing is not purely
one-directional on detection; this case shows its strongest available example of a genuine
catch, not a general detection-rate claim (see `retrieval_results.csv`/`final_gpu_validation.md`
§9: "Did detection improve? No, not in the paired 209-claim retrieval-only sample" — that
result and this one measure different, non-conflicting things: retrieval-only holds framing
at bare, this case isolates framing itself).

## Reproduce

```
python -c "
import json
d = json.load(open('research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json', encoding='utf-8'))
print([f for f in d['flips'] if f['document_id']=='2006_1150' and f['claim_id']=='c12'])
"
```
