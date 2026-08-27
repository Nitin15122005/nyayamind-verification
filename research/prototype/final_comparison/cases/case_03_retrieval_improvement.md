# Case 3 — Retrieval improvement (v0 → v0+v1 evidence pool)

**Selection criterion**: mechanically scanned every claim in the paired
`final_gpu_validation` batch for `A.evidence_id is None and B.evidence_id is not None`
(15 such claims exist — see `retrieval_results.csv`). Picked the first single-citation,
non-bundled example for narrative clarity.

**Source**: `outputs/final_gpu_validation_A.jsonl` / `outputs/final_gpu_validation_B.jsonl`,
`document_id="2000_1266"`, `claim_id="c1"`. Both arms share the same Qwen generation for
this case — only the evidence pool differs.

| | ORIGINAL (v0 pool, 59 records) | CURRENT (v0+v1 pool, 137 records) |
|---|---|---|
| Claim text | "Section 197 of the Code of Criminal Procedure applies to the facts of the present case, providing that the accused can take a plea of official duty immediately after cognizance is taken and process is..." | *(identical — shared generation)* |
| Evidence match | **None** | `Section 197 in The Code of Criminal Procedure, 1973` |
| Verdict | **NO_EVIDENCE** | **NOT_ENOUGH_INFORMATION** (confidence 0.9800) |

## What changed and why

Section 197 CrPC (sanction requirement for prosecuting public servants) was simply absent
from the 59-record v0 corpus. The v1 supplement added it as a new `VERIFIED_EXACT` record
(see `research/data/evidence/README_v1.md`). With the record present, the claim moves from
"cannot be evaluated at all" (`NO_EVIDENCE`) to "evaluated, and not confidently entailed or
contradicted" (`NOT_ENOUGH_INFORMATION`) — this is the general pattern found across all 15
gained-evidence claims in this batch (`final_gpu_validation.md` §2): coverage expansion
under `bare` framing converts `NO_EVIDENCE` into high-confidence NEI, not into a new
detection event. (For what labeled framing does with this newly-available evidence, see
`case_01`/`case_02` — framing and retrieval are separate, additive levers, not yet jointly
measured in one experiment; see `comparison_config.json`, `never_jointly_measured`.)

## What this case does and does not show

- **Does show**: a real, previously-unresolvable claim on a genuinely new natural case now
  has a citation-matched statute record to be checked against at all — the v1 corpus
  directly closes a coverage gap in the original 59-record evidence pool.
- **Does not show**: that the claim's content is legally accurate — NEI means "not
  confidently either," not "confirmed correct."

## Reproduce

```
python -c "
import json
A=[json.loads(l) for l in open('research/prototype/outputs/final_gpu_validation_A.jsonl', encoding='utf-8')]
B=[json.loads(l) for l in open('research/prototype/outputs/final_gpu_validation_B.jsonl', encoding='utf-8')]
a={(d['document_id'],c['claim_id']):c for d in A for c in d['claims']}
b={(d['document_id'],c['claim_id']):c for d in B for c in d['claims']}
print('A:', a[('2000_1266','c1')])
print('B:', b[('2000_1266','c1')])
"
```
