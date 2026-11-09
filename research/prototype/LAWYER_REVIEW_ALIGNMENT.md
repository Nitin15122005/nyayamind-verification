# Lawyer-review alignment audit

Run from the repository root:

```bash
python research/prototype/scripts/audit_lawyer_review_alignment.py
```

The script compares the normalized workbook rows with every committed model-output JSONL
artifact under `research/prototype/outputs/`. It reports case overlap, exact statement
matches, exact statement-plus-reference matches, and duplicate matches with provenance.

This is an identity audit, not a model evaluation. Missing matches are not negative
predictions. Repeated runs are deduplicated by claim content while source filenames remain
traceable.

## Why this gate is mandatory

The new workbook labels statement correctness and legal-reference correctness separately.
Existing outputs use NLI labels (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
NO_EVIDENCE). These taxonomies are not interchangeable. NOT_ENOUGH_INFORMATION is not
automatically Partially, and NO_EVIDENCE does not establish that a legal citation is invalid.
The older 88-row `lawyer_annotation.jsonl` is explicitly assumption-based, not lawyer
ground truth.

Only after identity overlap and label semantics are reviewed should a scoring adapter be
implemented. Do not calculate accuracy by naively mapping these labels.
