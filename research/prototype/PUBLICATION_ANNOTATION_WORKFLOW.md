# Publication annotation tooling

This module prepares annotation data; it never invents legal labels.

## GOLD-03 blind review

1. Generate the candidate worksheet (claims must be independently drafted):
   `python research/prototype/scripts/build_gold03_annotation_worksheet.py`
2. Split into independent reviewer packets:
   `python research/prototype/scripts/publication_annotation.py split-gold03 --worksheet research/prototype/outputs/GOLD03_ANNOTATION_WORKSHEET.csv --outdir research/prototype/outputs/gold03_review`
3. Give R1 and R2 separate files. Reviewers must not see model predictions or each other's work.
4. Merge after both are complete:
   `python research/prototype/scripts/publication_annotation.py merge-gold03 --reviewer1 research/prototype/outputs/gold03_review/GOLD03_R1_BLIND.csv --reviewer2 research/prototype/outputs/gold03_review/GOLD03_R2_BLIND.csv --output research/prototype/outputs/GOLD03_DOUBLE_ANNOTATED.csv`
5. Fill adjudicated_label, adjudication_rationale, adjudicator_id; then validate and summarize:
   `python research/prototype/scripts/publication_annotation.py validate-gold03 --input research/prototype/outputs/GOLD03_DOUBLE_ANNOTATED.csv`
   `python research/prototype/scripts/publication_annotation.py summarize-gold03 --input research/prototype/outputs/GOLD03_DOUBLE_ANNOTATED.csv --output research/prototype/outputs/GOLD03_ANNOTATION_SUMMARY.json`

Allowed labels: ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION. Every decision requires a rationale. The validator does not determine whether a legal label is correct.

## Natural-case annotation export

`python research/prototype/scripts/publication_annotation.py export-natural --input research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl --output research/prototype/outputs/NATURAL_ANNOTATION_PACKET.csv`

The exporter excludes automated verdicts and confidence scores. Preserve document_id so all claims from a case stay in one split. Review citation correctness and temporal applicability against authoritative sources; an empty matched-evidence field is not proof of NEI.

The exporter uses assertion_text where available to avoid scoring an entire multi-claim sentence as one atomic claim. Keep the original claim_text in a separate archival copy if needed.

## Integrity and interpretation

- No predictions are labels.
- Do not treat a mechanically generated candidate claim as a confirmed entailment.
- Do not describe provisional or model-assisted annotations as independent human ground truth.
- Report reviewer roles, agreement, adjudication, exclusions, class prevalence, and case-level split policy.
- Preserve source files; generated packets are new artifacts.


## Natural-data scoring after adjudication

Once the natural packet has been independently annotated and adjudicated, use the frozen annotation file with the exact archived run used to generate those claims:

`python research/prototype/scripts/evaluate_natural_annotations.py --annotations research/prototype/outputs/NATURAL_DOUBLE_ANNOTATED.csv --predictions research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl --output research/prototype/outputs/NATURAL_ANNOTATION_METRICS.json`

The evaluator joins by (document_id, claim_id), refuses duplicate/missing labels, reports the three-class confusion matrix and per-class metrics, and uses a document-level bootstrap. Claims with NO_EVIDENCE are reported separately as evidence-coverage failures, not silently counted as NOT_ENOUGH_INFORMATION. Do not run this against a different generation batch or changed parser output.
