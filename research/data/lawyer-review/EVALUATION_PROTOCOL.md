# Lawyer-review evaluation protocol

**Status:** protocol specification; no model performance result is implied by this document.

## 1. Intended construct

The lawyer-reviewed workbook supplies two independent claim-level targets:

- `statement_correctness`: whether the proposition in the supplied legal statement is correct.
- `reference_correctness`: whether the Act/provision cited for that statement is correct.

Each target has three labels: `Yes`, `No`, and `Partially`. The targets must be evaluated and reported separately. Do not combine them into one score.

The source workbook's instructions state that the underlying judgments and judgment dates were not supplied. Therefore, the annotations do not establish case-specific relevance, historical applicability on a judgment date, factual accuracy of a case summary, or correctness of a judgment outcome.

## 2. Prediction contract

The evaluation script accepts a prediction CSV with exactly one row per annotation ID and these columns:

- `annotation_id`
- `predicted_statement_correctness`
- `predicted_reference_correctness`

Predictions must use the same three labels as the annotations. The script rejects missing/extra IDs, duplicate IDs, null IDs, and unknown labels. It never maps NLI outputs to lawyer labels.

**Important:** the current NLI classes (`ENTAILED`, `CONTRADICTED`, `NOT_ENOUGH_INFORMATION`, and `NO_EVIDENCE`) are not equivalent to the lawyer labels. In particular, neither `NOT_ENOUGH_INFORMATION` nor `NO_EVIDENCE` is a synonym for `Partially` or `No`. A prediction file must come from a separately specified, construct-valid decision rule or a model explicitly trained to predict these lawyer targets. Do not create a score by renaming NLI labels.

## 3. Required metrics

For each target independently, report:

- sample size (annotation rows) and number of unique cases;
- accuracy;
- macro precision, macro recall, and macro F1;
- per-class precision, recall, F1, and support;
- confusion matrix with the fixed order `Yes`, `No`, `Partially`;
- 95% case-cluster bootstrap percentile intervals for accuracy and macro F1.

The bootstrap resamples unique `case_reference` clusters with replacement and retains all annotation rows belonging to each sampled case. This accounts for within-case clustering better than treating all annotation rows as independent. The default is 2,000 replicates and seed 20261109. Report the replicate count and seed for reproducibility.

The intervals quantify bootstrap sampling variability only. They do not correct annotation noise, reviewer disagreement, selection bias, or systematic dataset limitations. With only 45 unique cases, uncertainty may remain substantial; interpret intervals cautiously.

## 4. Leakage and split policy

The annotation row is not an independent case. Any future train/dev/test split or cross-validation must group by `case_reference`. Never randomly partition rows from the same case across partitions.

Do not use lawyer correction text, supporting authorities, or post-hoc audit findings as model input when evaluating predictions unless the experiment explicitly studies that information and prevents target leakage. Freeze model versions, prompts, thresholds, evidence corpus, retrieval configuration, and prediction-generation code before scoring.

## 5. Reference baseline

The repository includes `generate_lawyer_review_baseline.py`, which creates a **training-fold majority-class baseline** independently for each lawyer target. It uses five-fold `StratifiedGroupKFold`, groups by `case_reference`, and predicts the most frequent training label for every held-out row. The output is out-of-fold: a case is never present in both the training and test partition for the same fold.

Reproduce it with:

```bash
python research/prototype/scripts/generate_lawyer_review_baseline.py
python research/prototype/scripts/evaluate_lawyer_review.py \\
  --annotations research/data/lawyer-review/processed/lawyer_review.normalized.jsonl \\
  --predictions research/data/lawyer-review/processed/majority_baseline.oof.csv \\
  --output research/data/lawyer-review/processed/majority_baseline.metrics.json
```

This baseline is a sanity-check floor, not a NyayaMind model result. It uses only the training-fold label frequencies and no legal text or model outputs. Report the baseline separately for both targets. A future NyayaMind predictor must use the same case-grouped evaluation boundary and be compared against this baseline using frozen out-of-fold predictions. Do not interpret baseline scores as legal correctness.

## 6. Structured verifier-signal experiment

The repository includes `evaluate_lawyer_review_features.py` as an exploratory feature-based evaluation. It predicts the two lawyer targets separately with three-class logistic regression; it does not translate NLI classes into lawyer labels.

The predeclared eligibility rule is an exact legal-statement match and exactly one compatible provision/Act candidate. Rows failing candidate/reference uniqueness are excluded and counted in diagnostics. The experiment uses structured verifier/retrieval metadata only: provision type, Act match, evidence matching method, NLI verdict, verifier model, evidence presence, provision-identifier match, reference-text match, confidence, and distinct statement-match count. It excludes legal-statement text, case and annotation identifiers, correction/clarification text, supporting authorities, and annotation-derived audit conclusions.

Use five-fold StratifiedGroupKFold with `case_reference` as the group, and compare against a training-fold majority baseline on the exact same eligible rows and folds. Report both targets separately, including per-class metrics, confusion matrices, and 95% case-cluster bootstrap intervals. The eligibility subset and exclusions must be reported alongside every result. These are exploratory annotation-agreement results; they are not legal accuracy, and improvement in macro-F1 alone does not establish overall superiority if accuracy falls or intervals overlap.

## 7. Alignment is not evaluation

The alignment audit establishes whether lawyer rows can be linked to model-generated claim records. It does not establish prediction correctness. Report separately:

1. case-level presence in model outputs;
2. exact statement alignment;
3. provision/Act candidate alignment;
4. ambiguous and unmatched rows;
5. model metrics on a predeclared eligible set, if a valid prediction target and prediction file exist.

Do not silently discard ambiguous or unmatched rows. Publish their counts and a prespecified inclusion rule. Do not use a stale audit after changing the alignment script.

## 8. Reproduction

From the repository root, after importing the authorized workbook and producing an explicit prediction CSV:

```bash
python research/prototype/scripts/import_lawyer_review.py
python research/prototype/scripts/audit_lawyer_review_alignment.py
python research/prototype/scripts/evaluate_lawyer_review.py \
  --annotations research/data/lawyer-review/processed/lawyer_review.normalized.jsonl \
  --predictions PATH/TO/FROZEN_PREDICTIONS.csv \
  --output research/data/lawyer-review/processed/evaluation_metrics.json \
  --bootstrap-replicates 2000 --seed 20261109 --confidence-level 0.95
```

The audit command additionally requires the frozen model output JSONL files in `research/prototype/outputs/`. Keep raw workbook, private predictions, and generated audit artifacts out of public Git unless redistribution and disclosure are authorized.

## 9. Minimum reporting language

Describe scores as **agreement with the supplied lawyer annotations**, not legal accuracy or universal legal truth. State the number of annotation rows and unique cases, the two target definitions, label distribution, case-cluster bootstrap method, and dataset limitations. Do not claim inter-annotator agreement, adjudication, reviewer representativeness, or external validity unless independently documented.
