# GOLD-01 Construction-Validity Audit

_Date: 2026-11-04_  
_Scope: static audit of the committed GOLD-01 v2 generator, generated 420-item benchmark, and current bare/labeled CPU reruns. No item labels or historical outputs were changed._

## Executive finding

GOLD-01 is reproducible as a deterministic stress-test, but its construction labels are not independently validated legal-semantic ground truth. The observed 23.81 percentage-point item-accuracy difference and cluster-aware sensitivity result are real outputs on this benchmark; they do not isolate statutory reasoning because the treatment introduces matching citation metadata into the premise.

## 1. Attribution metadata overlap — material confound

The attributed hypotheses are constructed as `According to {provision citation}, {rule text}`. For example, the Article 21 hypothesis begins `According to Article 21 of Constitution of India...`.

The labeled premise is constructed as `{provision_type} {provision_number} of {act}: {evidence_text}`. Thus the treatment adds the same provision identifier that already appears in the attributed hypothesis. The bare premise contains no identifier.

This is not a neutral formatting change: it makes a citation proposition in the hypothesis lexically checkable against the premise. The result supports the narrower conclusion that adding matching provision metadata improves NLI classification of citation-bearing claims in this controlled setup. It does not establish that the verifier better understands the statutory rule or improves legal reasoning.

**Required follow-up experiment:** add a pre-specified negative control in which the premise receives a deliberately mismatched provision identifier (same act/different section and different act controls), plus an identifier-only premise control if feasible. Compare bare, correct-label, wrong-label, and correct-label-without-citation-in-hypothesis conditions. Keep the statutory text byte-identical. This separates citation-string matching from evidence-text entailment. Do not change production defaults based on GOLD-01 alone.

## 2. N1 “other provision” labels — plausible, not guaranteed NEI

Static audit of the 59 N1 items found:
- 59 distinct target/source pairings.
- 50 cross-Act pairings and 9 same-Act pairings.
- Jaccard lexical overlap ranged from 0.037 to 0.323; the generator's rejection threshold is 0.35.
- Two highest-overlap examples were IPC Section 147 paired with IPC Section 302 (Jaccard 0.323), and Constitution Article 22 paired with IPC Section 149 (0.200).

Different provision identity and low Jaccard overlap do not prove a neutral NLI relation. Legal provisions can qualify one another, share a subject, create exceptions, or contradict a proposition. The current rule establishes “not the same provision” and low lexical overlap—not independently adjudicated NEI. The N1 condition should be described as a cross-provision low-overlap stress condition, not guaranteed NEI ground truth.

## 3. Negation transformation — ambiguous double negatives

The generator's `prohibition_lifted` rule replaces `shall not` with `shall`. In three C1 items, the source sentence begins with “No person…” and the result contains “No person … shall not…”. The three affected provisions are:
- Constitution Article 21
- Constitution Article 22
- Constitution Article 311

These are ambiguous double-negative constructions. The existing validator only checks the contiguous phrase `not not`, so it does not catch this construction. These three items should not be treated as clean contradiction examples without manual adjudication or replacement by a controlled, unambiguous counterfactual.

## 4. Paraphrase transformation — lexical equivalence is assumed

The 32 substitution rules are deterministic lexical transformations. The generator labels the result ENTAILED whenever at least one rule fires; it does not independently establish that the substitution preserves legal meaning in context. Some substitutions may alter modality, scope, exceptions, or register. Therefore the 33 E3/E4 pairs test this finite substitution set, not general legal paraphrase robustness. The 100% model result on these conditions is descriptive and cannot validate the transformations themselves.

## 5. Statistical analysis — useful but bounded

The paired cluster bootstrap and sign-flip analysis correctly treats the 59 source provisions, rather than the 420 repeated rows, as the resampling/randomization units. It does not repair label-construction errors, citation-overlap confounding, or fixed-corpus sampling. The reported p-value and intervals should remain sensitivity estimates conditional on this benchmark.

## 6. Decision and paper-safe claims

**Retain:** raw per-arm metrics, confusion matrices, per-condition metrics, reproducible cluster analysis, and transparent construction details.

**Qualify:** state that labeled premise metadata improves performance on a deterministic citation-bearing benchmark, while explicitly noting citation overlap.

**Do not claim:** independently validated legal entailment accuracy, broad paraphrase robustness, guaranteed neutral N1 labels, or population-level significance.

**Next benchmark revision:** create a separately versioned GOLD-03 with (a) manually adjudicated or carefully rule-validated labels, (b) mismatched-citation negative controls, (c) semantically reviewed contradiction transformations, and (d) an independently reviewed N1/NEI set. Preserve GOLD-01 and its historical outputs unchanged for provenance.
