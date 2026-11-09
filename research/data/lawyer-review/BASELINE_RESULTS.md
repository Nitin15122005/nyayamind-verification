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

A separate exploratory experiment evaluates structured verifier/retrieval metadata against each lawyer target. It uses only provision type, Act match, evidence matching method, NLI verdict, verifier model, evidence presence, provision-identifier match, reference-text match, confidence, and number of distinct statement matches. It excludes raw legal-statement text, case/annotation IDs, correction text, supporting authorities, and annotation-derived audit conclusions.

Eligibility was fixed before scoring: exact statement match and exactly one compatible provision/Act candidate. This retained **244/251 rows across 44/45 cases**; six rows were excluded for non-unique candidate alignment and one for non-unique reference alignment. Both targets use the same eligible rows and five-fold StratifiedGroupKFold partitions grouped by `case_reference`. Each target is a separate three-class logistic-regression model. No NLI-to-lawyer-label mapping is used. Bootstrap intervals use 2,000 case-cluster percentile replicates (seed 20261109).

| Target | Structured model accuracy (95% CI) | Structured model macro-F1 (95% CI) | Same-subset majority accuracy | Same-subset majority macro-F1 (95% CI) |
|---|---:|---:|---:|---:|
| Statement correctness | 0.4303 [0.3301, 0.5287] | 0.4347 [0.3346, 0.5275] | 0.5287 [0.3954, 0.6560] | 0.2306 [0.1889, 0.2641] |
| Legal-reference correctness | 0.4426 [0.3450, 0.5296] | 0.4391 [0.3403, 0.5193] | 0.5943 [0.5000, 0.6803] | 0.2485 [0.2222, 0.2699] |

Per-class structured-model results (precision / recall / F1; support):

| Target | Class | Precision | Recall | F1 | Support |
|---|---|---:|---:|---:|---:|
| Statement correctness | Yes | 0.3474 | 0.7857 | 0.4818 | 42 |
| Statement correctness | No | 0.4000 | 0.4384 | 0.4183 | 73 |
| Statement correctness | Partially | 0.5797 | 0.3101 | 0.4040 | 129 |
| Legal-reference correctness | Yes | 0.6429 | 0.4345 | 0.5185 | 145 |
| Legal-reference correctness | No | 0.3594 | 0.9200 | 0.5169 | 25 |
| Legal-reference correctness | Partially | 0.2683 | 0.2973 | 0.2821 | 74 |

The structured models improve macro-F1 over the same-subset majority baseline for both targets, but have lower accuracy. This reflects a trade-off in minority-class prediction, not a general performance win. The reference-correctness model has particularly weak F1 for `Partially`. The confidence intervals are broad and overlap the comparator intervals; this is exploratory evidence on a small, selected subset, not proof of generalizable improvement. The models are not production-ready and have not been fine-tuned or externally validated.

The per-class metrics and confusion matrices are emitted in `structured_signals.metrics.json`; row-level out-of-fold predictions are in `structured_signals.oof.csv`. CI uploads these with the alignment and majority-baseline outputs as the `lawyer-review-alignment-and-baseline` artifact.

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
