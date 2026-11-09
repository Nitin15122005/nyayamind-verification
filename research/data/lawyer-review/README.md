# Lawyer-reviewed statutory claim dataset

## Status

This directory contains the data contract and import workflow for the lawyer-reviewed
statutory claim workbook. The source workbook is intentionally not duplicated by this
commit. Place the supplied workbook at:

`research/data/lawyer-review/raw/NyayaMind_Lawyer_Review_Final_Columns.xlsx`

The raw workbook must be treated as immutable. Do not edit it in place.

## What the workbook contains

The `Legal Review` worksheet contains claim–provision assessments with two distinct
labels:

1. **Statement correctness** — whether the legal statement accurately describes the law.
2. **Legal-reference correctness** — whether the cited Act/provision is the correct legal
   authority for the statement.

Both use `Yes`, `No`, and `Partially`. These dimensions must remain separate in
all analyses. Do not collapse them into a single correctness label.

The `Read First` worksheet defines the annotation instructions and notes that original
judgments and their dates were not supplied. Consequently, these annotations do not by
themselves establish case-specific relevance or historical applicability on the date of
a judgment.

## Import

From the repository root, using the research environment:

```bash
python research/prototype/scripts/import_lawyer_review.py
```

Or specify paths explicitly:

```bash
python research/prototype/scripts/import_lawyer_review.py \
  --input research/data/lawyer-review/raw/NyayaMind_Lawyer_Review_Final_Columns.xlsx \
  --output-dir research/data/lawyer-review/processed
```

Outputs:

- `processed/lawyer_review.normalized.jsonl` — one record per source row.
- `processed/lawyer_review.normalized.csv` — spreadsheet-friendly equivalent.
- `processed/lawyer_review.summary.json` — counts, label distributions, missingness,
  duplicate diagnostics, and source-file SHA-256.

The importer preserves the source row number and original text. It validates required
fields and label values and fails loudly rather than silently dropping malformed rows.

## Unit of analysis and leakage control

The source row is a **claim–provision assessment**, not an independent case. Multiple
rows can refer to the same case and the same statement. Any train/dev/test partition or
cross-validation must group by `case_reference`; never randomly split individual rows.
The importer does not create a split or imply that the workbook is training data.

## Evaluation rules

The executable scoring contract, metric definitions, case-cluster bootstrap procedure, and publication reporting requirements are specified in [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md). Read and follow that protocol before producing or reporting any model score.


- Report statement correctness and legal-reference correctness separately.
- Preserve the three-way labels. If a binary analysis is later justified, document the
  mapping and report the original three-way results as the primary analysis.
- Report counts at both row and unique-case level.
- Do not treat `Partially` as automatically correct or incorrect.
- Do not use correction text or supporting authority as model input unless the
  experiment explicitly studies that information and controls for leakage.
- Keep all lawyer-provided corrections and authorities as human annotations, not as
  automatically verified legal truth.
- Report reviewer count, qualifications, annotation date, adjudication procedure and
  any inter-annotator agreement only when those facts are actually documented.

## Data governance

Before making the repository public or distributing this dataset, confirm permission to
redistribute the workbook and its annotations. Check whether it contains reviewer
identifiers, confidential comments, or third-party material. If redistribution is not
authorized, keep the raw workbook out of Git and provide an access-controlled procedure
or a derived dataset whose release has been approved.

## Limitations

The workbook's own instructions state that original judgments and judgment dates were
not included. The annotations therefore support claim-level assessment of the supplied
statement and cited legal reference, but do not independently establish:

- whether the cited provision was applicable to the underlying case;
- whether the provision was in force on the judgment date;
- whether the case facts were accurately represented; or
- whether the judgment outcome was legally correct.

These limitations must be reflected in any paper using this dataset.
