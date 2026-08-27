# Case 5 — Safe rejection of an unsafe/out-of-scope correction

**Selection criterion**: a `correction_scope_violation` triggered identically in BOTH arms
of the paired `final_gpu_validation` batch — chosen because it directly demonstrates that
CURRENT's relaxed scope-check (`assertion_spans`) is not spuriously more permissive than
ORIGINAL's legacy full-sentence check on real natural-data output.

**Source**: `outputs/final_gpu_validation_corrections_detail.jsonl`,
`document_id="2006_770"`, `triggered_for_claim_id="c1"` — one record per arm, both with
`status=="correction_scope_violation"`.

| | ORIGINAL (legacy scope check) | CURRENT (`assertion_spans` scope check) |
|---|---|---|
| Qwen's proposed edit | Removed "or hurt" from the flagged clause | *(identical edit — same Qwen call inputs)* |
| Unflagged claims sharing this sentence | 3 | 3 |
| Claim-text fragments preserved | **0/3** | — |
| Assertion-span fragments preserved | — | **1/3** |
| Result | **REJECTED** (`correction_scope_violation`) | **REJECTED** (`correction_scope_violation`) |
| Reverification | `null` (never reached — rejected before re-verification) | `null` (same) |

## What this demonstrates

Qwen's edit was a real, substantive change (not a no-op) — but it also altered text that
two *other* claims in the same bundled sentence depend on. ORIGINAL's legacy rule requires
every unflagged claim's full original sentence to survive byte-for-byte: 0/3 did, so it's
rejected. CURRENT's narrower `assertion_spans` rule only requires each unflagged claim's own
verbatim sub-span to survive: even under this relaxed bar, only 1/3 did — **still a
violation**, correctly rejected by both mechanisms. This is direct, real-data evidence that
relaxing the scope-check rule (a change motivated by unblocking legitimate bundled-sentence
edits, see `FINAL_PRODUCTION_CONFIG.md` §3) did not let an unsafe edit through in this case.

## Honest caveat

This is one of only 2 scope-violation cases in the paired 50-case batch where both
mechanisms could be directly compared side-by-side on the same edit
(`final_gpu_validation.md` §4). A separate deterministic replay across all 11 real
natural scope-violation cases from batch1+batch2 found the narrower check unblocks just
**1/11** (`outputs/atomic_scope_check_final_replay.json`) — see `case_07` and
`ablation_results.csv` for why this is reported as "no evidence of harm, weak/inconclusive
evidence of benefit," not as a demonstrated safety improvement.

## Reproduce

```
python -c "
import json
recs=[json.loads(l) for l in open('research/prototype/outputs/final_gpu_validation_corrections_detail.jsonl', encoding='utf-8')]
print([r for r in recs if r['document_id']=='2006_770' and r['triggered_for_claim_id']=='c1'])
"
```
