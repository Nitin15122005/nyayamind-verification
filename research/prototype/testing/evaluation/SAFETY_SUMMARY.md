# Safety Summary (STEP 8)

Machine-readable source: `SAFETY_SUMMARY.csv`.

| Safety mechanism | Count | Denominator | Source |
|---|---|---|---|
| Unsafe corrections shipped (cumulative) | **0** | 56 natural + 66 synthetic = 122 total correction attempts | `outputs/final_metrics.json` |
| Scope-gate rejections (cumulative natural) | 18 | 56 natural correction attempts | `outputs/final_metrics.json` |
| Sibling-regression rejections observed (final_gpu_validation Arm B) | 0 | 5 correction attempts | `outputs/final_gpu_validation_metrics.json` |
| Citation-identity preservation failures observed | NOT AVAILABLE (not tracked as a running count; 0 confirmed false-ship cases found in the STEP 0 audit) | N/A | `outputs/final_gpu_validation.md` §4 (narrative) |
| Re-verification-not-ENTAILED rejections (cumulative natural) | 37 | 56 natural correction attempts | `outputs/final_metrics.json` |

## The exact, disciplined claim

**0 unsafe corrections observed** across every correction attempt this project has
tested — 56 real natural attempts and 66 synthetic attempts, 122 total, spanning every
configuration this project has ever shipped or evaluated.

## What this does and does not establish

This is an **observed count over a specific, finite set of tested cases**, not a proof
of a safety property. **0 unsafe corrections observed in the tested correction history
does not mean unsafe corrections are impossible** — it means none occurred in the 122
attempts actually made. The mechanisms responsible for this record (the ENTAILED-only
shipping gate, the scope-violation check, and the sibling-regression safety net) are
each individually tested and behave correctly in every case examined (see STEP 5's
component tests and STEP 7's ablation analysis) — but a mechanism working correctly on
every tested case, at n=122, is evidence of good behavior at that scale, not a
mathematical guarantee at any scale.

## Where each mechanism's own correctness is independently verified

- **ENTAILED-only shipping gate**: confirmed as an unconditional, code-level invariant
  in STEP 5's component tests (`06_correction_safety`, `07_final_assembly` — 35+5
  passing tests, including 3 using the real DeBERTa verifier).
- **Scope-violation check**: confirmed to correctly catch an altered unflagged claim
  before any re-verification call, in the same STEP 5 component tests, and its
  `assertion_spans` relaxation was independently ablated in STEP 7 (graded C —
  diagnostic, since only the scope-gate decision was tested, not downstream shipping).
- **Sibling-regression net**: structurally can only ever reject a correction, never
  approve one (confirmed by code inspection in STEP 0's audit); observed to reject 0
  cases across every experiment that tracked it, because no genuine regression occurred
  in those experiments — not because the mechanism was never exercised.
