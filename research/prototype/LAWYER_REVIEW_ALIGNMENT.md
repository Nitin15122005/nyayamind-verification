# Lawyer-review alignment audit

Run from the repository root after importing the workbook:

```bash
python research/prototype/scripts/audit_lawyer_review_alignment.py
```

The audit compares normalized workbook rows with committed model-output JSONL files under
`research/prototype/outputs/`. It exports the lawyer's statement, provision reference,
both independent labels, correction/authority fields, and candidate model claims. Candidate
claims are annotated with typed provision-identifier and Act-name compatibility checks.
Hyphenated provision identifiers (for example, 295-A and 120-B) are normalized for
comparison. Where the lawyer reference names an Act, a different Act with the same
section number is rejected; references such as "the same Act" remain provisional.

A statement match can still be ambiguous when one generated statement expands into several
provision-level claims. The audit reports statement-level ambiguity separately from
provision-alignment ambiguity. Repeated outputs for the same claim are counted once for
alignment while source filenames and run-specific verdicts remain traceable. Same-Act,
same-number Section/Rule conflicts are surfaced as `resolved_typed_provision_mismatch`:
they are not silently coerced into exact matches, but they are distinguished from missing
records. LR-0232 is the current example: the source statement says CrPC Rule 3, whereas
the lawyer reference says CrPC Section 3. The lawyer correction and the Code text establish
that Section 3 is “Construction of references”; charge-framing provisions include Section 228.
The row therefore remains a confirmed incorrect-citation example, not an exact alignment.
See the [official Code of Criminal Procedure, 1973](https://upload.indiacode.nic.in/showfile?actid=AC_CEN_5_23_000010_197402_1517807320555&filename=a1974-02.pdf&type=actfile).

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

Inspect the revised audit's `num_reference_aligned_matches`,
`num_typed_provision_mismatch_matches`, and `act_match` for each row. Only unambiguous
statement-plus-provision pairs with compatible Act names may enter a paired evaluation, and only after a target-specific
prediction rule has been defined and frozen. Statement correctness and reference correctness
must be scored separately. Keep Partially as a distinct class; do not map NLI labels directly
to Yes/No/Partially. Use case-grouped splits and case-clustered confidence intervals.
