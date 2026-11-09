# Dataset Card: Lawyer-Reviewed Statutory Claim Assessments

## Dataset identity

- Name: NyayaMind Lawyer-Reviewed Statutory Claim Dataset
- Source: `NyayaMind_Lawyer_Review_Final_Columns.xlsx`
- Worksheet: `Legal Review`
- Schema: `research/data/lawyer-review/README.md`
- Importer: `research/prototype/scripts/import_lawyer_review.py`

## Intended use

Research evaluation of two separate tasks:

1. Whether a generated legal statement accurately describes the law.
2. Whether the legal authority cited for that statement is correct.

The labels are three-way: Yes, No, and Partially. The two tasks must not be conflated.

## Unit and dependence

Each row is a claim–provision assessment. Several rows can belong to one case and
can repeat a statement across different provision references. Rows are therefore not
independent observations. All future data partitions and statistical resampling must
group by case reference.

## Known source limitations

The workbook's Read First worksheet says that original judgments and their dates were
not included. The data cannot, on its own, establish historical statutory applicability,
case-specific relevance, or correctness of the underlying judgment.

## Annotation provenance still to document

The supplied workbook does not establish the number of reviewers, their qualifications,
annotation date, adjudication procedure, or inter-annotator agreement. These must be
obtained from the project team and reported only when verified.

## Release restrictions

Do not publish the raw workbook or derived annotations until permission to redistribute
the annotations and all supporting legal material has been confirmed. Remove reviewer
identifiers or confidential notes if present and permitted/required by the data owner.
