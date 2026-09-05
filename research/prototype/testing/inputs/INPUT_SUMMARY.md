# Input Summary — Plain Language

## 1. What inputs are we using?

Two kinds, fundamentally: (a) two small, mechanically-constructed benchmark datasets with
genuine correct answers built into how they were made, and (b) real statute text and real
previously-generated case data with no independent correct answer attached — useful for
measurement and comparison, not for scoring accuracy.

## 2. How many records are in each?

See the compact table below.

## 3. Which are GOLD?

Only two: the 420-example controlled NLI benchmark, and the 59-example synthetic stress
set. Nothing else in this project has an independently-derived correct answer.

## 4. Which are behavior-only?

The adversarial and edge-case citation-parsing test fixtures (inline in
`research/prototype/tests/`, ~61 test functions across 4 files). These check that the
*code* behaves exactly as designed for tricky inputs — not that any legal conclusion is
correct.

## 5. Which are metric-only?

Everything built from real generated case text: the 588-claim aggregate, the 209-claim
paired evaluation, all four natural batches, and the correction/safety detail files. These
support rates, distributions, and paired comparisons — never an accuracy score.

## 6. Which are provisional?

Three annotation files (`gold_annotation.jsonl`, `lawyer_annotation.jsonl`,
`assumption_annotation.jsonl`) — Claude-generated guesses, explicitly self-tagged as not
lawyer-verified. Never usable as gold, ever, under any circumstance this workspace
controls.

## 7. Which inputs can be compared against expected outputs?

Only the two GOLD datasets. Everything else in this project is measured, not scored
against a known-correct answer.

## 8. Which inputs can only produce descriptive metrics?

The 588-claim aggregate, the 209-claim paired evaluation, the four natural batches, and
the correction/safety detail files — coverage %, verdict distributions, shipping rates,
and paired statistical comparisons (e.g. McNemar's test between two configurations run on
the same underlying cases).

## 9. Which inputs are historical reference material?

The `final_demo_pack` example compilations and the `final_comparison` config/tables —
these are presentations built *from* historical results, not fresh inputs to feed into
anything.

## 10. Which inputs require NVIDIA hardware later?

Only the raw NyayaRAG case-text input (`CASE-01`), if used for **fresh generation**
(stage 1) or **fresh correction** (stage 6). Every GOLD, BEHAVIOR, and evidence-retrieval
input can be used today, on this machine, with no GPU — STEP 2 confirmed CPU-only
verification (DeBERTa) genuinely works here.

## Compact table

| Input | N | Status | Can compare expected output? | GPU required? |
|---|---|---|---|---|
| Controlled NLI benchmark | 420 | GOLD | **Yes** | No (DeBERTa runs CPU) |
| Synthetic stress set | 59 | GOLD | **Yes** (contradiction-recall only) | No |
| Adversarial citation fixtures | 15 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| Final-pass adversarial fixtures | 10 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| Respectively-claims fixtures | 16 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| Claim-parser bugfix fixtures | 20 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| 588-claim natural aggregate | 588 (derived) | METRIC-ONLY | No | No (re-derivation is CPU-only) |
| 209-claim paired evaluation | 209/arm | METRIC-ONLY | No — not ground truth | Full regen: yes; re-analysis: no |
| Natural batch n=30 | 30 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Natural batch1 (n=50) | 50 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Natural batch2 (n=50) | 50 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Final validation batch (n=50) | 50 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Correction/safety detail (×3 files) | 10+10+21 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Evidence corpus (v0+v1 merged) | 136 usable | N/A (input corpus) | N/A | No |
| NyayaRAG case source | 4,930+4,962 | N/A (input corpus) | N/A | **Yes, for fresh generation** — blocked on this machine |
| Provisional annotations (×3 files) | 88+88+88 | PROVISIONAL | No, never | No |
| final_demo_pack/final_comparison compilations | N/A | HISTORICAL-ONLY | No | No |

## The one honest limit of this summary

This table describes what *can* legitimately be measured, not what *has* been freshly
measured in this workspace yet. STEP 3 builds and validates the input layer only — no
fresh evaluation, ablation, or figure generation has been run against any of these
datasets in this step. See `../reports/README.md` for the planned sequencing.
