# Consolidated Faculty Summary (STEP 8)

## 1. Research question

Does statutory-claim verification and selective correction improve a generated Indian
court-judgment summary's "Statutory Grounding" field, and which specific design changes
are responsible for any observed improvement?

## 2. What was input

Real Indian Supreme Court case text (NyayaRAG corpus), a statute evidence corpus (v0:
59 records; v0+v1: 136 records), and two independently-derived gold datasets (a 420-item
controlled NLI benchmark and a 59-item synthetic contradiction set). Full detail:
`../inputs/INPUT_SUMMARY.md`.

## 3. What was tested

Every pipeline component individually (STEP 5: 205 tests, 0 failures), the verifier
against true gold labels (STEP 4), the pipeline's descriptive behavior on real natural
claims (STEP 6: 588 claims, 209 paired claims, 8 batch regimes), and 8 named ablation
factors isolating the project's own design changes (STEP 7).

## 4. What improved

| Area | Original | Current | Evidence strength |
|---|---|---|---|
| Evidence coverage (natural, paired) | 63.2% | 70.3% | **A** |
| Verifier benchmark accuracy | 73.3% | 97.1% | **A** |
| Verifier benchmark macro F1 | 0.749 | 0.968 | **A** |
| Natural verification decisiveness (147-claim subset) | 0/147 ENTAILED | 13/147 ENTAILED | **B** |
| Claim parser evidence-match count (n=30) | 38 matched | 51 matched, 6/30 cases improved, 0 worsened | **B** |
| Scope-gate flexibility (n=11 real violations) | 0 unblocked | 1 unblocked | **C** |

## 5. Strongest evidence

Two results are **strongly supported** (grade A): the premise-framing improvement on
the 420-item controlled benchmark (macro F1 0.749→0.968, McNemar p=4.2×10⁻²³, exact
sign test p=1.6×10⁻³⁰), and the evidence-v1 coverage gain on the 209-claim paired
natural set (63.2%→70.3%, McNemar p=0.0003, zero regressions).

## 6. Natural-data behavior

On 588 real, previously-generated claims under the current production configuration:
66.3% receive usable evidence; of those, the verifier's judgments split
NEI=364, NO_EVIDENCE=198, ENTAILED=21, CONTRADICTED=5. **These are descriptive counts,
not accuracy figures** — no independent label exists for what a real generated claim's
"correct" statutory grounding should say.

## 7. Correction results

Correction remains rare and small-sample: 0/5→1/10 shipped on the targeted comparison,
1/56 (1.8%) cumulative across the project's history, with a much higher 26/36 (72.2%)
rate on the synthetic (deliberately corrupted) test set. **The synthetic and natural
rates describe different populations and must never be presented as the same number.**

## 8. Safety

**0 unsafe corrections observed** across 122 tested correction attempts (56 natural +
66 synthetic). This is an observed count over tested cases, not a guarantee of absolute
safety at any scale.

## 9. What is not proven

- That any change improved legal correctness (no independent legal ground truth exists
  anywhere in this project).
- That the natural-data correction pipeline works reliably (n=56 cumulative attempts,
  1 shipped).
- That the four current production levers (evidence-v1, premise framing, scope
  checking, narrow re-verification) combine additively or interact in any specific way
  — **this was never tested**.

## 10. Remaining limitations

- **Joint four-lever causal isolation was not performed** anywhere in this project's
  history. Every "original vs. current" comparison is a chain of separate experiments,
  not one controlled joint run.
- Narrow re-verification (n=3) and the targeted correction-levers comparison (n=5 vs 10)
  remain diagnostic only — real evidence exists, but not enough to support a
  statistical claim.
- This machine has no NVIDIA GPU — no fresh Qwen generation or correction was possible
  in any step of this workspace; all such figures remain historical.

## 11. Final takeaway

The two strongest, most defensible findings in this project are the premise-framing
improvement on the controlled verifier benchmark and the evidence-v1 coverage gain on
real paired natural claims — both statistically supported, both independently
reproduced multiple times across this workspace. Everything downstream of verification
(correction triggering, scope checking, shipping) remains real but small-sample, and
should be described as diagnostic evidence, not a proven capability.

## Safe conclusions

- Labeled premise framing substantially improves verifier accuracy on the controlled
  GOLD benchmark.
- Evidence-v1 materially increases observed evidence coverage on real natural claims,
  with zero regressions.
- The claim parser fix increased evidence-matched counts on a 30-case batch with no
  case worsened.
- 0 unsafe corrections have been observed across every correction attempt tested.

## Claims we deliberately do not make

- "NyayaMind achieves 66.3% accuracy on natural data" — 66.3% is evidence coverage, not
  accuracy, and no natural-data accuracy figure exists anywhere in this project.
- "Evidence-v1 improved legal correctness" — no legal ground truth exists to support this.
- "The correction system is solved" — 1.8% cumulative shipping rate, n too small for
  any confident capability claim.
- "0 unsafe corrections proves the system is safe" — 0 observed incidents at n=122 is
  evidence of good behavior on tested cases, not a safety proof.
