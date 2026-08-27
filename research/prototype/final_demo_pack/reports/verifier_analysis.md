# Verifier Analysis — DeBERTa NLI Behavior

Source: `research/prototype/final_demo_pack/metadata/computed_metrics.json` sections `controlled_benchmark_verifier`, `threshold_sensitivity`, `confidence_distributions`, `assumption_gold_provisional`, and `final_metrics_passthrough` (natural regime verdict counts).

**Throughout this report: a verifier verdict (ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION) is a small public NLI model's statistical judgment that a matched evidence text entails, contradicts, or is neutral toward a claim sentence. It is never legal truth, never a lawyer's determination, and never validated against professional legal ground truth anywhere in this project.**

## Model

`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, fp16 on GPU / fp32 on CPU, `confidence_threshold: 0.70`. A low-confidence argmax prediction is downgraded to `NOT_ENOUGH_INFORMATION` with `sub_reason: "low_confidence"`. Label order is read from the model's own `config.id2label`, never hardcoded.

## Bare vs. labeled premise framing

The **premise** given to the NLI model is either the bare statute text (`bare`) or the statute text prefixed with its own provision label, e.g. "Section 302 of the Indian Penal Code: ..." (`labeled`). Claims are almost always attributed ("According to Section 302..."), so a bare premise never mentions the section number, leaving that half of the claim structurally unsupported regardless of content — this is the mechanism the labeled framing addresses.

### Controlled benchmark (420 curated real legal claim/evidence pairs, not synthetic corruption)

| | Bare | Labeled |
|---|---:|---:|
| Accuracy | 0.733 | 0.971 |
| Macro F1 | 0.749 | 0.968 |
| ENTAILED recall | 0.500 | 1.000 |
| Per-condition regression | — | None observed |

8 conditions per claim family tested (verbatim/paraphrase × attribution, negated variants) — see `controlled_benchmark_verifier.bare/labeled.per_condition` for the full breakdown. This benchmark's ground truth is by construction (each item's correct label is known from how it was built), not lawyer-derived, but it is a stronger and more controlled signal than natural-data agreement checks.

### Natural data, pooled (100 cases, batch1+batch2, 2 disjoint sources)

| | Bare (v0 pool) | Labeled (v0 pool) |
|---|---:|---:|
| Matched claims | 454 | 284 |
| ENTAILED | 2 (0.4% of matched) | 16 (5.6% of matched) |
| CONTRADICTED | 5 | 5 |
| NOT_ENOUGH_INFORMATION | 447 | 263 |

Labeled framing produces **8x more ENTAILED-per-matched-claim** on this pooled natural sample — the clearest natural-data confirmation of the labeled framing's detection-completion benefit at a defensible pooled size.

### The genuine counter-signal (reported honestly, not suppressed)

Re-verifying the 38 evidence-matched claims from `assumption_annotation.jsonl` (an older, PROVISIONAL, Claude-generated — **NOT lawyer-verified** — label set) under labeled framing shows *slightly worse* agreement (18/38 = 47.4%) than the already-stored bare verdicts (20/38 = 52.6%), and only 2/38 claims flip to ENTAILED. This is the **opposite direction** from every other source above. The likely explanation (not confirmed): this older claim set is dominated by bundled multi-citation sentences, and the PRIMARY verification pass always hypothesizes the full `claim_text`, never the narrower `assertion_text` used elsewhere — so labeled framing's provision label helps less when sibling citations dilute the hypothesis. This is recorded in `FINAL_PRODUCTION_CONFIG.md` §1 as a real, unresolved counter-signal, not treated as outweighing the other evidence, but not hidden either.

**Reminder: these agreement numbers describe agreement between two machine-produced label sets (an NLI model and Claude's provisional labels), not verifier accuracy against real legal ground truth.**

## Confidence distributions (evidence-matched claims only; NO_EVIDENCE claims carry no verifier confidence)

| | Bare, pooled (n=454) | Labeled, pooled (n=284) |
|---|---:|---:|
| Mean | 0.945 | 0.862 |
| Median | 0.986 | 0.940 |
| Std dev | 0.095 | 0.158 |
| Min / Max | 0.521 / 0.999 | 0.370 / 0.999 |
| % in [0.9, 1.0) | 383/454 = 84.4% | 173/284 = 60.9% |

Labeled framing produces a **wider, less concentrated confidence distribution** — consistent with it making more decisive distinctions (ENTAILED vs CONTRADICTED) instead of defaulting to a uniformly high-confidence NEI. This is a distributional observation, not a claim about calibration against ground truth.

## Threshold sensitivity (controlled benchmark, deterministic replay, no re-inference)

| Threshold | Bare macro-F1 | Labeled macro-F1 |
|---:|---:|---:|
| 0.50 | 0.749 | 0.965 |
| 0.65 | 0.751 (near-peak) | 0.968 (near-peak) |
| **0.70 (production)** | **0.749** | **0.968** |
| 0.85 | 0.742 | 0.960 |
| 0.95 | 0.738 | 0.942 |

At the production threshold, both framings sit within 0.002 macro-F1 of their empirical peak. No evidence in this sweep supports moving the threshold; it was not changed. See `research/prototype/outputs/threshold_sensitivity_analysis.md` for the full 10-point sweep.

## Contradiction / ENTAILED / NEI behavior summary

- **CONTRADICTED** is rare on natural data (5-11 per batch out of 100+ claims) — most natural claims that resolve to a verdict at all land on NOT_ENOUGH_INFORMATION, reflecting genuinely ambiguous or under-specified generated text relative to the matched evidence, not necessarily a false claim.
- **ENTAILED** on natural data only appears meaningfully under labeled framing (2 under bare vs. 16 under labeled, pooled) — bare framing structurally under-detects entailment because it never sees the provision label the claim is attributing to.
- **NOT_ENOUGH_INFORMATION** is the default outcome when the model cannot confidently decide — it is the *safe* default (no correction is ever triggered by NEI alone, unless combined with `sub_reason: "low_confidence"`), not evidence that the claim is wrong.
