# Faculty Limitations and Caveats — Standalone Reference

This document exists so a reviewer can find every material limitation of this project's
evaluation **without reading the full evaluation report**. Nothing here is new — every
item is carried forward from `reports/FINAL_RECONCILIATION_REPORT.md`'s own limitations
section (STEP 11), which itself carries them forward from STEP 1, 6, 7, and 10B. None is
minimized, softened, or omitted here.

## 1. Cumulative correction rate (1/56 = 1.8%) cannot be freshly reproduced

**What it is**: `outputs/final_metrics.json`'s `section_D_correction_safety_cumulative`
reports 1 of 56 correction attempts, across this project's entire history, has ever
shipped (0 unsafe).

**Why it cannot be reproduced**: this figure is a pooled rollup across many separate
historical correction experiments (synthetic bare/labeled, natural-targeted, natural
batches, the 209-claim run, the labeled-correction-validation run, etc.). Its own
`provenance` field names an ad-hoc, never-committed "build_final_metrics analysis"
script; no such script exists anywhere in the repository (confirmed by a repository-wide
search during STEP 10B), and no per-constituent breakdown survives that would let the
`56` be reconstructed from the stored artifact alone. Reconstructing it honestly would
require re-running every GPU-dependent correction experiment in the project's history
and re-summing — out of scope for this evaluation.

**What this does and does not affect**: it does not affect any other reported metric.
It means the 1.8% figure should be read as a historical snapshot, not a rate that can be
re-verified or that would necessarily hold if re-measured today. It is never presented
as freshly reproduced or approximated anywhere in this package.

## 2. No joint four-lever experiment exists

**What it is**: this project's production configuration has four independently-changed
levers (`premise_framing`, `use_evidence_v1`, `atomic_scope_check`,
`narrow_reverification_hypothesis`). No experiment in this project's history varies all
four, one at a time, from a single common baseline in one controlled run.

**Why it doesn't exist**: every "original vs. current" comparison in this project is
assembled from a chain of separate experiments, each changing more than one lever at
once. This was true at STEP 7 and re-confirmed absent by repository-wide search at
STEP 10, STEP 10B, and STEP 11.

**What this does and does not affect**: no additive, multiplicative, or interaction
effect between the four levers can be inferred from the available single-lever
findings, and none is inferred anywhere in this package. Each lever's evidence grade
(§8 of the main report) reflects only its own isolated finding.

## 3. Scope-check-mode discrepancy (1/11 vs. 4/6) is unreconciled

**What it is**: two different real-data replays of the atomic scope-check lever report
different unblock counts — 1 of 11 (the STEP 7/10 real scope-violation replay) versus an
earlier batch-1-only finding of 4 of 6.

**Why it's unreconciled**: both numbers are real, computed from different underlying
batches of cases, not from the same population. Neither number supersedes the other;
this is a STEP 1/7 finding, unaffected by any GPU work in STEP 10/10B.

**What this does and does not affect**: it does not change the atomic scope-check
lever's evidence grade (C — diagnostic, not statistically established either way). It
means neither "1/11" nor "4/6" should be quoted alone as *the* scope-check unblock rate
without noting the other exists on a different batch.

## 4. Evidence-v1 audit coverage is partial

**What it is**: the evidence-v1 corpus (78 new records added to the usable evidence
pool) was independently re-fetched and content-verified for only 50 of its 82 records,
as of 2026-08-27.

**Why it's partial**: the remaining 32 records rest on build-time provenance only (the
original construction process's own record-keeping), not independent re-verification.

**What this does and does not affect**: it does not change the 209-claim paired
evidence-coverage finding's evidence grade (A) — that finding is about coverage
*mechanism*, not about verifying every individual evidence record's content. It does
mean a claim like "100% of evidence-v1 records are independently verified" would be
false; only 61% (50/82) are.

## 5. The root-level "Project Author Statement" is not used as evidence

**What it is**: a statement in this repository's root-level documentation claiming
professional legal review of the project.

**Why it's excluded**: this claim is unverifiable from within this workspace — no
underlying review artifact, reviewer identity, or review methodology is available to
inspect.

**What this does and does not affect**: it is not cited as evidence for any finding
anywhere in this evaluation package. No conclusion in this report depends on it being
true or false.

## 6. Historical GPU runs' exact physical-machine identity is not independently confirmed

**What it is**: `src/generator.py`'s own docstring states its 4-bit bitsandbytes
configuration was "already validated on this RTX 4050 6GB machine." The STEP 10/10B
machine used for GPU validation also has an NVIDIA GeForce RTX 4050 Laptop GPU with
6 GB VRAM.

**Why identity isn't confirmed**: matching GPU model and VRAM class is not proof of
being the identical physical machine referenced in that docstring — no independent
hardware-identity check (e.g., a serial number or asset tag) was performed or is
available.

**What this does and does not affect**: it does not affect the validity of STEP 10/10B's
own fresh reproductions — those were verified directly (byte-identical output, hash
comparisons against historical files), independent of which physical machine originally
produced the historical data. It means only that the *specific* production-code
docstring's claim about "this machine" should be read as "a machine of this GPU class,"
not as a proven single-device identity claim.

## Additional limitations carried forward from earlier steps

- **No human/lawyer ground truth exists anywhere in this project.** All GOLD labels are
  Claude-generated/self-tagged or by-construction (synthetic corruption). This is the
  reason no natural-data accuracy or F1 figure is ever reported.
- **Natural ENTAILED/CONTRADICTED counts are model verdicts, not validated facts** — the
  verifier's own source code carries this disclaimer, unchanged throughout the project.
- **The synthetic (72.2%) and natural cumulative (1.8%) correction shipping rates are
  disjoint populations with different base rates by construction** — neither predicts or
  transfers to the other (see Figure 11, `figures/11_synthetic_vs_natural_transfer.png`).
