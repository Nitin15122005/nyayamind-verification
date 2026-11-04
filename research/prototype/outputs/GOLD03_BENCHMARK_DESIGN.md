# GOLD-03 Benchmark Design and Release Gate

_Date: 2026-11-04_  
_Status: protocol specification only; no GOLD-03 labels or results have been generated._

## Purpose

GOLD-03 is a follow-up evaluation intended to distinguish statutory-text entailment from citation-metadata matching. It must not overwrite GOLD-01, its JSONL, metadata, predictions, metrics, or historical reports.

## Research question

When an NLI verifier receives the statutory text, does adding accurate provision metadata improve its classification of a claim because the statutory rule is better grounded, or merely because the provision identifier in the hypothesis is repeated in the premise?

## Required experimental factors

Use the same canonical statutory text within each paired item. Cross two factors:

1. **Premise metadata:** no identifier; correct identifier; deliberately mismatched identifier.
2. **Hypothesis citation:** no citation; correct citation; deliberately mismatched citation.

The mismatched identifiers must be real provision identifiers from the same evidence corpus and must be selected deterministically and logged. Avoid matching a wrong label to a provision that is substantively related without manual review. The primary comparison should be correct metadata versus no metadata when the hypothesis citation is absent; this removes direct lexical citation overlap from the primary estimand.

Do not interpret the wrong-identifier cells as natural legal claims. They are diagnostic controls for metadata reliance.

## Label construction and review

- ENTAILED: hypothesis must be supported by the cited canonical provision. A deterministic lexical rewrite alone is not enough to certify semantic equivalence.
- CONTRADICTED: construct a minimally edited counterfactual with one clearly reversed operative proposition. Avoid ambiguous double negatives, especially “No person … shall not”. Each item requires a documented rationale and independent review.
- NOT_ENOUGH_INFORMATION: do not assign NEI solely because a different provision was selected or Jaccard overlap is low. The evidence must genuinely fail to support or refute the hypothesis. Use a reviewed claim/evidence pair and record why neither entailment nor contradiction follows.
- Paraphrases: record source text, transformed text, exact transformation, and reviewer decision. Do not label every lexical substitution ENTAILED automatically.
- Reviewers must be independent of the model outputs. Resolve disagreements through a documented adjudication step. If qualified legal review is unavailable, describe labels as expert/annotator-reviewed only if that is true; do not imply legal validation.

## Sampling and statistical plan

- Freeze the source-provision list before generating items. Report the number of independent source provisions and all per-condition counts.
- Keep all paired variants from a provision in one cluster for bootstrap and randomization.
- Pre-register one primary contrast: correct premise metadata versus no premise metadata, restricted to hypotheses without citation strings.
- Report accuracy, macro-F1, class-wise precision/recall, confusion matrices, per-condition performance, and cluster-aware paired effect estimates with confidence intervals.
- Report all secondary contrasts as exploratory and correct for multiplicity if inferential claims are made.
- The fixed project evidence pool is not a probability sample of Indian law. Avoid population-level generalisation.
- Publish item-level predictions, benchmark hashes, generation code, configuration, random seeds, and adjudication protocol, subject to source/licensing constraints.

## Mandatory release gates

GOLD-03 must not be used for confirmatory claims until all gates pass:

1. The item-generation code is deterministic and tested.
2. Every hypothesis has a traceable evidence source and a recorded construction rationale.
3. Citation-overlap controls are implemented and verified.
4. No ambiguous negation transformations remain in contradiction items.
5. NEI labels are reviewed as semantic relations, not inferred from low lexical overlap.
6. Paraphrase labels are independently checked.
7. Inter-annotator agreement and adjudication are reported where multiple reviewers are used.
8. The primary analysis and cluster unit are pre-specified.
9. The frozen benchmark, metadata, code, and analysis are versioned separately from GOLD-01.

## Current decision

Do not generate GOLD-03 automatically from GOLD-01's transformations and call the result ground truth. The next concrete task is to create a candidate item pool and annotation sheet, then obtain independent labels. Until that work is complete, GOLD-01 remains a deterministic diagnostic benchmark with the limitations documented in `GOLD01_CONSTRUCTION_VALIDITY_AUDIT.md`.
