# Case 4 — Correction improvement: a genuine, safe, shipped correction

**Selection criterion**: the only `status=="corrected"` (shipped) record in
`labeled_correction_validation_gpu_corrections_detail.jsonl` — not selected among
alternatives, because it is the sole example: this is the first and only correction ever
shipped under the CURRENT production regime in this project's history.

**Source**: `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl`,
`document_id="2003_760"`, `triggered_for_claim_id="c3"`. Config: CURRENT (all four levers:
v0+v1 evidence, labeled framing, `assertion_spans` scope check, narrow reverification).

| | Before correction | After correction |
|---|---|---|
| Flagged sentence | "Section 302 deals with murder, which prescribes that whoever commits the act which causes the death of a human being with the intention to cause death or with the knowledge that such act will cause death, commits murder." | "Section 302 deals with murder, which prescribes that whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine." |
| Evidence (Section 302 IPC) | "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine." | *(same)* |
| Problem | Sentence restates Section 302's *definition* language (what counts as murder) instead of the cited evidence's actual *punishment* text | Corrected sentence now matches the punishment text almost verbatim |
| Re-verification | — | **ENTAILED**, confidence 0.9946 |
| Sibling regressions | — | **0** (empty list; the sentence's other claim, Section 34, was unaffected) |

## Would ORIGINAL have shipped this?

No path to test this exact case under strict ORIGINAL config exists (bare framing rarely
reaches ENTAILED at all on natural data — 0/209 in the paired retrieval-only arms; see
`retrieval_results.csv`). The bare-framing equivalent of this same correction pathway,
tested on the same underlying 50-case batch (`final_gpu_validation` Arm B, bare framing,
same evidence pool/scope-check/narrow-reverification config), shipped **0/5** corrections —
see `outputs/final_gpu_validation_metrics.json`. This is the swing evidence behind the
`premise_framing: bare -> labeled` production decision (`FINAL_PRODUCTION_CONFIG.md` §1).

## Honest caveat — do not over-read this

This is **n=1 shipped out of 10 triggered** under the targeted validation run
(`labeled_correction_validation_gpu_metrics.json`), and the smallest, most recently
collected piece of evidence behind any CURRENT config decision. It is the first shipped
correction on a "final validation"-caliber held-out natural batch in this project's
history, not a demonstrated rate. See `correction_results.csv` and
`statistical_tests.csv` (`correction_shipping_ablation_targeted_gpu`) for why this is
reported directionally, not as a statistically significant improvement.

## Reproduce

```
python -c "
import json
recs=[json.loads(l) for l in open('research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl', encoding='utf-8')]
print([r for r in recs if r['status']=='corrected'][0])
"
```
