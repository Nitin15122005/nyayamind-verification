# Lawyer-review alignment audit

Run from the repository root after importing the workbook:

```bash
python research/prototype/scripts/audit_lawyer_review_alignment.py
```

The audit compares normalized workbook rows with committed model-output JSONL files under
`research/prototype/outputs/`. It exports the lawyer's statement, provision reference,
both independent labels, correction/authority fields, and candidate model claims. Candidate
claims are annotated with a typed provision-identifier match where the reference field
contains parseable Section/Article/Rule/Regulation identifiers. Exact normalized reference
text is a secondary match signal.

A statement match can still be ambiguous when one generated statement expands into several
provision-level claims. The audit reports the number of candidates and the subset aligned to
the provision identifier; it does not silently choose one. Repeated runs are deduplicated by
claim content while source filenames remain traceable.

## Critical evaluation boundary

This is still an identity/provision-alignment audit, not a model evaluation. Missing matches
are not negative predictions. The workbook labels statement correctness and legal-reference
correctness separately. Existing outputs use NLI labels (ENTAILED, CONTRADICTED,
NOT_ENOUGH_INFORMATION, NO_EVIDENCE). These taxonomies are not interchangeable:
NOT_ENOUGH_INFORMATION is not automatically Partially, and NO_EVIDENCE does not establish
that a legal citation is invalid. The older 88-row `lawyer_annotation.jsonl` is
assumption-based, not lawyer ground truth.

The workbook's Read First sheet also notes that original judgments and judgment dates were
not supplied. The labels therefore cannot establish case-specific relevance or historical
applicability. Do not claim legal correctness beyond the annotated task.

## Next gate

Inspect the revised audit's `num_reference_aligned_matches` for each row. Only unambiguous
statement-plus-provision pairs may enter a paired evaluation, and only after a target-specific
prediction rule has been defined and frozen. Statement correctness and reference correctness
must be scored separately. Keep Partially as a distinct class; do not map NLI labels directly
to Yes/No/Partially. Use case-grouped splits and case-clustered confidence intervals.
