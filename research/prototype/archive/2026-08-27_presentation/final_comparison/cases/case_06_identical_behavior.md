# Case 6 — Both systems behave identically

**Selection criterion**: one of the 3 claims CONTRADICTED in **both** arms of the paired
`final_gpu_validation` batch with byte-identical confidence — direct evidence that CURRENT's
retrieval/scope/reverification changes left this claim's detection outcome completely
untouched, as expected (this claim was already evidence-matched under the v0-only pool, so
the v1 supplement had no path to affect it).

**Source**: `outputs/final_gpu_validation_A.jsonl` / `_B.jsonl`,
`document_id="2006_770"`, `claim_id="c2"`.

| | ORIGINAL | CURRENT (retrieval/scope/narrow-reverify only, still bare) |
|---|---|---|
| Claim text | "The Indian Penal Code, 1860 (IPC) Sections 302 and 304 Part I require the prosecution to prove the intent to cause death for a conviction under Section 302, while Section 304 Part I applies to cases where the death is caused by an act likely to cause death or such consequences, but without any intention to cause death or hurt." | *(identical)* |
| Evidence | `Section 304 in The Indian Penal Code, 1860` | *(identical)* |
| Evidence text | "Whoever commits culpable homicide not amounting to murder shall be punished with imprisonment for life... if the act... is done with the intention of causing death or such bodily injury as is likely to cause death." | *(identical)* |
| Verdict | **CONTRADICTED** | **CONTRADICTED** |
| Confidence | 0.97217 | 0.97217 |

## Why identical, and why that's expected

This claim was already evidence-matched under the 59-record v0 pool, so `use_evidence_v1`
had nothing to add for it; both arms hold `premise_framing=bare`, so framing's effect (the
lever that moves detection the most, per the controlled benchmark) is held constant too;
and `atomic_scope_check`/`narrow_reverification_hypothesis` only apply during correction,
which this claim's CONTRADICTED verdict does trigger (see the correction-attempt table in
`final_gpu_validation.md` §4) — but the verification verdict itself, shown here, is upstream
of any correction-path lever. Zero difference here is a correctly-predicted null result, not
a surprising one: `final_gpu_validation.md` §2 confirms **0 verdict flips among the 132
claims matched in both arms**, of which this is one.

## Manual inspection (why this catch is real, not a verifier artifact)

The claim's phrasing overstates what the evidence says: it describes Section 304 Part I
with "without any intention to cause death **or hurt**", but the matched evidence's own
language covers intent to cause death **or such bodily injury as is likely to cause
death** — i.e., intent to cause a specific kind of hurt is squarely inside 304 Part I,
directly contradicting the claim's blanket "without any intention... or hurt." A genuine,
checkable content error, correctly and identically caught by both configurations.

## Reproduce

```
python -c "
import json
A=[json.loads(l) for l in open('research/prototype/outputs/final_gpu_validation_A.jsonl', encoding='utf-8')]
B=[json.loads(l) for l in open('research/prototype/outputs/final_gpu_validation_B.jsonl', encoding='utf-8')]
a={(d['document_id'],c['claim_id']):c for d in A for c in d['claims']}
b={(d['document_id'],c['claim_id']):c for d in B for c in d['claims']}
print('A:', a[('2006_770','c2')]['verdict'], a[('2006_770','c2')]['confidence'])
print('B:', b[('2006_770','c2')]['verdict'], b[('2006_770','c2')]['confidence'])
"
```
