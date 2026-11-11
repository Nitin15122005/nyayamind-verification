# Lawyer-review benchmark integration plan

## Current implementation

The repository now includes a strict importer for the supplied lawyer-review workbook.
It writes normalized JSONL/CSV and a provenance/quality summary. The importer keeps
statement correctness and legal-reference correctness as separate three-class targets.

## Required local verification

1. Confirm the workbook is present at
   `research/data/lawyer-review/raw/NyayaMind_Lawyer_Review_Final_Columns.xlsx`.
2. Install research dependencies, including the Excel reader:
   `pip install -r research/requirements.txt`.
3. Run:
   `python research/prototype/scripts/import_lawyer_review.py`.
4. Inspect the generated summary and manually compare its counts with the workbook.
5. Run the focused test:
   `python -m pytest research/prototype/tests/test_lawyer_review_import.py -q`.

## Evaluation design constraints

- The workbook is human annotation, not a model-prediction file.
- Do not report verifier accuracy/F1 from the annotation distribution alone.
- A model prediction export must be joined to annotations by stable row identity before
  computing metrics.
- Do not use correction/clarification or supporting authority as verifier inputs in an
  evaluation unless the experiment explicitly defines and controls that information flow.
- Any partition must group by case reference to prevent repeated case statements crossing
  evaluation boundaries.
- Report three-class results separately for the statement and legal-reference targets.
- Treat Partially as its own class in primary reporting. Any binary collapse is secondary,
  justified, and accompanied by the original three-class results.
- Report per-class precision/recall/F1, macro-F1, balanced accuracy, confusion matrices,
  and confidence intervals where statistically defensible. Use case-clustered resampling
  rather than row-level bootstrap.

## Not yet claimed

This commit does not claim that the system has been evaluated against the lawyer labels.
It does not train or fine-tune a model. It does not claim that the annotations are
independently adjudicated or that they establish historical legal correctness.

## Next experiment stage

After the workbook is available and its provenance is confirmed, export predictions from
the frozen verifier for the same claim–provision rows. Preserve a stable annotation ID,
freeze the model/configuration, and compute separate three-class metrics for both
annotation dimensions. The model's prediction targets and the annotation definitions
must be checked for semantic compatibility before scoring.
