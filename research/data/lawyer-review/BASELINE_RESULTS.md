# Lawyer-review benchmark: current results

**Generated:** 2026-11-09  
**Dataset:** 251 claim–provision assessment rows from 45 unique cases  
**Evaluation status:** reference majority baseline plus exploratory structured verifier-signal models. The latter are not legal-accuracy estimates.

## Dataset and alignment

The workbook contains two independent three-class targets:

| Target | Yes | No | Partially |
|---|---:|---:|---:|
| Statement correctness | 43 | 73 | 135 |
| Legal-reference correctness | 150 | 26 | 75 |

The regenerated identity/provision audit reports:

- 45/45 annotated cases present in model outputs.
- 251/251 exact legal-statement text matches.
- 250/251 rows have an exact provision/Act-aligned candidate (99.60%).
- 0 ambiguous provision alignments.
- **LR-0232 is a confirmed typed-provision discrepancy, not a missing record.** The lawyer annotation identifies CrPC Section 3, while the generated statement says Rule 3. The lawyer's correction note says no such CrPC Rule 3 exists and identifies Section 3 as “Construction of references”; the official Code likewise titles Section 3 “Construction of references”, while Section 228 is “Framing of charge”. The audit now records this as `resolved_typed_provision_mismatch` rather than an unresolved/unmatched row. It does not coerce Rule 3 into Section 3 or count it as an exact reference match. The underlying statement/reference error remains visible and `reference_correctness=No` is preserved. ([India Code: Code of Criminal Procedure, 1973](https://upload.indiacode.nic.in/showfile?actid=AC_CEN_5_23_000010_197402_1517807320555&filename=a1974-02.pdf&type=actfile); see also [Section 228, Framing of charge](https://indiacode.ecourtsindia.com/crpc/section/228/)).
- 1 resolved typed-provision discrepancy; 0 unresolved reference-alignment rows.
- 224/251 rows have multiple statement matches. The statement text is repeated across multiple claim records, so statement identity alone is not sufficient; the typed provision and Act filter is necessary.

Alignment is an identity/record-linkage audit, not an evaluation of NLI or legal correctness.

## Reference baseline

A five-fold StratifiedGroupKFold split was used independently for each target. All rows from one case_reference stay in one fold. Each held-out row is predicted using the most frequent class in that fold's training partition. This is a simple out-of-fold majority baseline, not a NyayaMind model.

Metrics are computed against the supplied lawyer annotations. Confidence intervals are 95% case-cluster percentile bootstrap intervals (2,000 replicates; seed 20261109).

| Target | Accuracy | 95% CI | Macro-F1 | 95% CI |
|---|---:|---:|---:|---:|
| Statement correctness | 0.5378 | [0.4009, 0.6640] | 0.2332 | [0.1908, 0.2660] |
| Legal-reference correctness | 0.5976 | [0.5000, 0.6742] | 0.2494 | [0.2222, 0.2685] |

The macro-F1 values are low because a majority-class predictor does not learn the minority classes. These results establish a leakage-aware reference floor only. A future NyayaMind model must produce explicit predictions for both targets, use the same case-grouped evaluation boundary, and outperform this baseline before a model-performance claim is made.

## Structured verifier-signal evaluation

A separate exploratory experiment evaluates structured verifier/retrieval metadata against each lawyer target. It uses provision type, Act match, evidence matching method, NLI verdict, verifier model, evidence presence, provision-identifier match, reference-text match, confidence, and number of distinct statement matches. It excludes raw legal-statement text, case/annotation IDs, correction text, supporting authorities, and annotation-derived audit conclusions.

Eligibility is exact statement match and exactly one **typed provision/Act-compatible** candidate. The stricter alignment audit retains **220/251 rows across 44/45 cases**. Thirty rows have multiple reference-aligned claims and are excluded as ambiguous; LR-0232 is a typed Section-versus-Rule mismatch and is not treated as an exact match. This supersedes the earlier, more permissive 244-row exploratory run. Both targets use the same eligible rows and five-fold StratifiedGroupKFold partitions grouped by `case_reference`. Each target is a separate three-class logistic-regression model. No NLI-to-lawyer-label mapping is used.

Bootstrap intervals use 2,000 case-cluster percentile replicates (seed 20261109). In addition to separate model and baseline intervals, the revised pipeline computes a **paired case-cluster bootstrap of the out-of-fold model-minus-majority metric difference**. This resamples the same cases for both prediction sets and preserves the pairing. It quantifies uncertainty conditional on the generated out-of-fold predictions; it does not retrain the model within each bootstrap replicate.

| Target | Model accuracy (95% CI) | Model macro-F1 (95% CI) | Same-subset majority accuracy | Same-subset majority macro-F1 | Paired accuracy difference (95% CI) | Paired macro-F1 difference (95% CI) |
|---|---:|---:|---:|---:|---:|---:|
| Statement correctness | 0.4227 [0.3452, 0.5388] | 0.4016 [0.3298, 0.5029] | 0.5818 | 0.2452 | -0.2919 [-0.2919, -0.0209] | +0.1564 [+0.0538, +0.2593] |
| Legal-reference correctness | 0.4500 [0.3110, 0.5377] | 0.4212 [0.2898, 0.5051] | 0.6000 | 0.2500 | -0.1577 [-0.3010, -0.0238] | +0.1659 [+0.0702, +0.2598] |

Paired differences are model minus same-fold majority baseline. The interval for accuracy difference is entirely below zero for both targets; the macro-F1 difference interval is entirely above zero. Thus, on this selected subset and these OOF predictions, the model trades lower accuracy for higher macro-F1. This is a class-balance trade-off, not an overall win or evidence of legal accuracy.

Per-class structured-model results (precision / recall / F1; support):

| Target | Class | Precision | Recall | F1 | Support |
|---|---|---:|---:|---:|---:|
| Statement correctness | Yes | 0.2286 | 0.3902 | 0.2883 | 41 |
| Statement correctness | No | 0.3731 | 0.4902 | 0.4237 | 51 |
| Statement correctness | Partially | 0.6265 | 0.4063 | 0.4929 | 128 |
| Legal-reference correctness | Yes | 0.6346 | 0.5000 | 0.5593 | 132 |
| Legal-reference correctness | No | 0.3500 | 0.9130 | 0.5060 | 23 |
| Legal-reference correctness | Partially | 0.2143 | 0.1846 | 0.1983 | 65 |

The reference-correctness model has weak recall for `Partially`. The 44-case eligible subset is selected by exact statement and typed provision alignment, so the results do not generalize automatically to unmatched or ambiguous claims. These are exploratory annotation-agreement results, not legal accuracy or production validation. The models have not been fine-tuned or externally validated.

The row-level out-of-fold predictions and full metrics (including confusion matrices, fold composition, separate bootstrap intervals, and paired differences) are emitted in `structured_signals.oof.csv` and `structured_signals.metrics.json`. CI uploads these with the compact alignment summary and majority-baseline outputs as the `lawyer-review-alignment-and-baseline` artifact.

## Limitations

- These are agreement scores against the supplied annotations, not legal accuracy or universal legal truth.
- The source workbook does not include original judgment texts or judgment dates. Case-specific relevance and historical applicability are therefore not independently established.
- The annotations do not document sufficient information to claim inter-annotator agreement or adjudication.
- The benchmark contains 45 cases; uncertainty remains material despite case-cluster resampling.
- NLI labels (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, NO_EVIDENCE) are not mapped to the lawyer labels (Yes, No, Partially).
- No fine-tuning or lawyer-target NyayaMind prediction model was evaluated in this run.

## Structured-signal reproduction

After importing the workbook and regenerating the alignment audit:

```bash
python research/prototype/scripts/evaluate_lawyer_review_features.py \\
  --annotations research/data/lawyer-review/processed/lawyer_review.normalized.jsonl \\
  --audit research/data/lawyer-review/processed/alignment_audit.json \\
  --predictions research/data/lawyer-review/processed/structured_signals.oof.csv \\
  --metrics research/data/lawyer-review/processed/structured_signals.metrics.json
```

## Reproduction

From the repository root:

```bash
python research/prototype/scripts/import_lawyer_review.py
python research/prototype/scripts/audit_lawyer_review_alignment.py
python research/prototype/scripts/generate_lawyer_review_baseline.py
python research/prototype/scripts/evaluate_lawyer_review.py \
  --annotations research/data/lawyer-review/processed/lawyer_review.normalized.jsonl \
  --predictions research/data/lawyer-review/processed/majority_baseline.oof.csv \
  --output research/data/lawyer-review/processed/majority_baseline.metrics.json
```

See [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md) for the full prediction contract, metric definitions, split policy, and reporting requirements.
