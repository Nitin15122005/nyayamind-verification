# Lawyer-review benchmark: current results

**Generated:** 2026-11-09  
**Dataset:** 251 claim–provision assessment rows from 45 unique cases  
**Evaluation status:** reference baseline only; no NyayaMind model score is available.

## Dataset and alignment

The workbook contains two independent three-class targets:

| Target | Yes | No | Partially |
|---|---:|---:|---:|
| Statement correctness | 43 | 73 | 135 |
| Legal-reference correctness | 150 | 26 | 75 |

The regenerated identity/provision audit reports:

- 45/45 annotated cases present in model outputs.
- 251/251 exact legal-statement text matches.
- 250/251 rows have a unique provision/Act-aligned candidate (99.60%).
- 0 ambiguous provision alignments.
- 1 unmatched provision alignment: **LR-0232**. The lawyer reference identifies CrPC Section 3, while the aligned model candidate is parsed as Rule 3 of the CrPC. This is a provision-type mismatch and should remain unmatched until the source claim/parser representation is reviewed.
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

## Limitations

- These are agreement scores against the supplied annotations, not legal accuracy or universal legal truth.
- The source workbook does not include original judgment texts or judgment dates. Case-specific relevance and historical applicability are therefore not independently established.
- The annotations do not document sufficient information to claim inter-annotator agreement or adjudication.
- The benchmark contains 45 cases; uncertainty remains material despite case-cluster resampling.
- NLI labels (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, NO_EVIDENCE) are not mapped to the lawyer labels (Yes, No, Partially).
- No fine-tuning or lawyer-target NyayaMind prediction model was evaluated in this run.

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
