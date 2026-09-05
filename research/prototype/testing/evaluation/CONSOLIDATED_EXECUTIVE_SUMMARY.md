# Consolidated Executive Summary (STEP 8)

## System purpose

NyayaMind's prototype pipeline extracts statutory claims from a generated Indian
court-judgment summary field, verifies each claim against an independently-sourced
statute corpus using a small NLI model, and — in its correction mode — selectively
rewrites and re-verifies claims flagged as unsupported or contradicted, shipping a fix
only if it passes an unconditional entailment gate.

## Evaluation design

This workspace (`research/prototype/testing/`) built a four-layer evaluation: (1) a
component-level test layer covering every pipeline stage independently (205 tests, 0
failures), (2) an expected-vs-actual layer against the project's only two
independently-derived gold datasets (a 420-item controlled NLI benchmark and a 59-item
synthetic contradiction set), (3) a metric-only descriptive layer over real natural
claims (588 aggregate, 209 paired), and (4) an ablation layer isolating 8 specific
design changes with statistical testing where the sample size supports it. This step
consolidates all four layers into one cross-referenced, figure-ready package —
introducing no new experiment, methodology, or number.

## Strongest quantitative improvements

Two results are statistically strong and independently reproduced: **premise framing**
(labeled vs. bare) raised the controlled benchmark's macro F1 from 0.749 to 0.968
(McNemar p=4.2×10⁻²³, exact sign test p=1.6×10⁻³⁰, n=420), and **evidence-v1** (the
expanded statute corpus) raised observed evidence coverage on paired real claims from
63.2% to 70.3% with zero regressions (McNemar p=0.0003, n=209).

## Natural-data findings

On 588 real, previously-generated claims under the current configuration, 66.3% (390)
receive usable evidence; verifier verdicts split NEI=364, NO_EVIDENCE=198, ENTAILED=21,
CONTRADICTED=5. These are descriptive counts — no independent correctness label exists
for natural data anywhere in this project, so no accuracy or F1 figure is reported for
it.

## Correction limitation

Correction remains rare: 1 of 56 (1.8%) natural correction attempts have ever shipped
across the project's history, versus 26 of 36 (72.2%) on the synthetic, deliberately
corrupted test set — two disjoint populations that must not be conflated. The one
isolated natural comparison available (0/5 bare → 1/10 labeled) is directionally
suggestive but too small to be statistically supported.

## Safety

0 unsafe corrections have been observed across all 122 tested correction attempts (56
natural, 66 synthetic). This is an observed record over tested cases, not a
mathematical safety guarantee.

## Ablation evidence

Of 9 graded conclusions, 2 are grade A (evidence-v1; premise framing on the controlled
benchmark), 3 are grade B (natural premise framing; the claim-parser fix; the
confidence-threshold sensitivity), 3 are grade C (atomic scope checking; narrow
re-verification; the targeted correction-levers comparison), and 1 is grade E: **no
experiment in this project's history jointly isolates all four current production
levers (evidence-v1, premise framing, scope checking, narrow re-verification) from one
common baseline** — this is an explicit, unresolved limitation, not an oversight.

## Reproducibility status

Every fresh number in this workspace was independently re-derived on this exact
machine and cross-checked against its historical counterpart — with exact, bit-for-bit
agreement in every case checked (evidence coverage, McNemar statistics, exact sign
tests, scope-check replay counts). This machine has no NVIDIA GPU; no Qwen generation
or correction was executed at any point across this entire testing workspace — every
figure involving real generation or correction is explicitly historical.

## Major remaining limitations

1. No joint four-lever causal isolation exists.
2. Narrow re-verification and the targeted correction comparison remain small-sample,
   diagnostic evidence only.
3. No independent legal ground truth exists anywhere in this project — every verifier
   verdict is a statistical NLI judgment, never a validated legal fact.
4. GPU-dependent results (all real generation and correction) cannot be freshly
   reproduced on the current machine.
