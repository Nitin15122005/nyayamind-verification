# GOLD-03 Annotation Instructions

This worksheet is a candidate pool, not a labelled dataset. No gold labels are pre-filled.

## Generate the worksheet

From the repository root:

```powershell
research/.venv/Scripts/python.exe research/prototype/scripts/build_gold03_annotation_worksheet.py
```

Output: `research/prototype/outputs/GOLD03_ANNOTATION_WORKSHEET.csv`.

The script reads the v0 and v1 canonical/audit JSONL pairs, applies the same-key replacement order (v1 replaces v0), and then retains only records whose final audit verdict is `VERIFIED_EXACT`. It does not modify source evidence or GOLD-01 files.

## How to annotate

For each source provision:

1. Read the complete `source_text` and source URL.
2. Write a short, natural-language statutory claim in `candidate_claim_without_citation`. Do not copy the provision verbatim. Do not include an Article/Section number or Act name in this primary claim.
3. Reviewer 1 and Reviewer 2 independently classify the claim against the source text as ENTAILED, CONTRADICTED, or NOT_ENOUGH_INFORMATION, and explain the decision. Do not see model predictions before annotation.
4. Record any paraphrase, contradiction, or NEI candidate only after writing the exact claim and its rationale. Do not infer NEI from a different provision or low lexical overlap.
5. Adjudicate disagreements and record the final label and rationale. Preserve both initial decisions.
6. Use `correct_identifier` and `mismatched_identifier` only to populate controlled metadata conditions. The mismatch is a deterministic next-row pairing, not a claim that the provisions are legally unrelated. Review every mismatch before including it in an experiment.

## Experimental controls

For each reviewed claim, create paired verifier inputs with:
- no provision identifier in the premise;
- the correct provision identifier in the premise;
- a deliberately incorrect provision identifier in the premise (diagnostic condition only).

Keep the claim citation-free for the primary comparison. Separate any experiment where the hypothesis itself contains a citation. This makes citation-string overlap an explicit factor rather than an accidental confound.

## Important limitations

- `VERIFIED_EXACT` is an evidence-audit status, not a legal endorsement of a generated claim.
- Historical status is copied for context; applicability to a particular case requires its relevant date and transitional rules.
- The mismatched pairing is a mechanical candidate and may be substantively related.
- Do not report model performance on this worksheet as GOLD-03 until independent annotations, adjudication, and the pre-registered analysis are complete.
- Report annotator identities/roles appropriately, agreement, adjudication, exclusions, and all condition counts. Do not imply lawyer or legal validation unless it actually occurred.
