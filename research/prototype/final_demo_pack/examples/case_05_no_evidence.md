# Case 5 — NO_EVIDENCE (not the same thing as "legally unsupported")

**Document ID:** `2011_625` &nbsp;·&nbsp; **Claim ID:** `c5` &nbsp;·&nbsp; **Source:** `research/prototype/outputs/final_gpu_validation_B.jsonl` &nbsp;·&nbsp; **Regime:** final production (v0+v1 evidence pool)

## Claim (model-generated)

> "Additionally, Sections 336 and 149 of the IPC are relevant as they pertain to the
> use of weapons and the liability of persons acting in concert, respectively, though
> their direct application to the decision is not explicitly mentioned in the
> provided facts."

**Citation extracted:** Section 336, Indian Penal Code, 1860.

## Evidence match

| Field | Value |
|---|---|
| Evidence ID | `null` |
| Evidence text | `null` |
| Match method | `no_evidence` |
| Verdict | **NO_EVIDENCE** |
| Confidence | `null` — no NLI call is made when there is no evidence to check against |

Section 336 IPC simply is **not one of the 136 provisions** in this project's
canonical evidence pool (v0's top-63-by-frequency + v1's ranks 64-143) — it was never
looked up, resolved, and independently audited, so there is nothing to verify this
claim against.

## Why it matters — the distinction this case exists to make

**NO_EVIDENCE means "our corpus does not contain this provision," not "this claim is
legally wrong."** The system makes no assertion whatsoever about whether Section 336
IPC actually says what the claim says — it correctly declines to guess. Roughly a
third of all claims across every natural experiment this project has run resolve to
NO_EVIDENCE this way (`research/prototype/final_demo_pack/reports/retrieval_analysis.md`),
almost entirely because the evidence corpus is capped at the top ~140 most-cited
provisions in the source corpus (by design — see `research/data/evidence/README.md`),
not because of any parser or matching defect (0 confirmed defects found across 797
claims — see the same report).

**What this does NOT establish:** nothing about whether the underlying legal claim is
true or false. This case is included specifically to make that distinction concrete,
not to illustrate a system failure.
