#!/usr/bin/env python
"""
Builds the human-gold annotation dataset from the completed 30-case A/B/C
evaluation. Read-only over research/prototype/outputs/run_{A,B,C}_n30.jsonl
— does not touch src/, config/, the evidence corpus, or those three files.
No model is loaded; this is pure data transformation.

Claim-level data (claim_text, extracted citation, matched evidence,
automated verdict/confidence) is pulled from run_B_n30.jsonl specifically
("generation + verification, no correction") — mode A has no verdict at
all, and mode C's claims are identical to B's (same shared generation
baseline, verified by the document_id-order + claim-count check below) but
B is the cleanest source that carries a verdict without being entangled
with any correction outcome, so the final A/B/C system result is never
exposed as (or conflated with) an annotation target.

Outputs:
  research/prototype/outputs/gold_annotation.jsonl        (88 claim records, blank annotation fields)
  research/prototype/outputs/gold_annotation_guide.md      (annotator instructions)
  research/prototype/outputs/gold_annotation_summary_template.md  (blank summary template)
"""
from __future__ import annotations

import json
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = _PROTOTYPE_ROOT / "outputs"

GOLD_PATH = OUTPUT_DIR / "gold_annotation.jsonl"
GUIDE_PATH = OUTPUT_DIR / "gold_annotation_guide.md"
SUMMARY_TEMPLATE_PATH = OUTPUT_DIR / "gold_annotation_summary_template.md"


def load_records(mode: str) -> list[dict]:
    path = OUTPUT_DIR / f"run_{mode}_n30.jsonl"
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_gold_records(records_b: list[dict]) -> list[dict]:
    gold = []
    counter = 0
    for rec in records_b:
        document_id = rec["document_id"]
        for claim in rec["claims"]:
            counter += 1
            gold.append({
                "annotation_id": f"A{counter:04d}",
                "document_id": document_id,
                "claim_id": claim["claim_id"],
                "claim_text": claim["claim_text"],
                "extracted_citation": claim["citation_extracted"],
                "matched_evidence_text": claim["evidence_text"],  # None if no match
                "evidence_match_method": claim["evidence_match_method"],
                "automated_verdict": claim["verdict"],
                "automated_confidence": claim["confidence"],
                "annotation": {
                    "citation_valid": "",
                    "evidence_entails_claim": "",
                    "evidence_relevance": "",
                    "annotator_notes": "",
                },
            })
    return gold


def run_checks(gold: list[dict], records_a: list[dict], records_b: list[dict], records_c: list[dict]) -> dict:
    problems = []

    # A/B/C document_id order + per-case claim count must match (paired
    # comparison, same shared baseline) — otherwise B's claims aren't a
    # faithful stand-in for "every extracted claim from the 30 cases".
    doc_ids_a = [r["document_id"] for r in records_a]
    doc_ids_b = [r["document_id"] for r in records_b]
    doc_ids_c = [r["document_id"] for r in records_c]
    if not (doc_ids_a == doc_ids_b == doc_ids_c):
        problems.append("document_id order differs across run_A/B/C_n30.jsonl")

    claims_a = [len(r["claims"]) for r in records_a]
    claims_b = [len(r["claims"]) for r in records_b]
    claims_c = [len(r["claims"]) for r in records_c]
    if not (claims_a == claims_b == claims_c):
        problems.append("per-case claim counts differ across run_A/B/C_n30.jsonl")

    # annotation_id uniqueness
    ann_ids = [g["annotation_id"] for g in gold]
    if len(ann_ids) != len(set(ann_ids)):
        problems.append("duplicate annotation_id values")

    # (document_id, claim_id) uniqueness
    pairs = [(g["document_id"], g["claim_id"]) for g in gold]
    if len(pairs) != len(set(pairs)):
        problems.append("duplicate (document_id, claim_id) pairs")

    # exact full-row duplicates (same text+citation+evidence repeated)
    dupe_keys = [
        (g["document_id"], g["claim_text"], json.dumps(g["extracted_citation"], sort_keys=True))
        for g in gold
    ]
    if len(dupe_keys) != len(set(dupe_keys)):
        problems.append("duplicate claim_text+citation rows within the same document_id")

    # required-field schema check
    required_top = {
        "annotation_id", "document_id", "claim_id", "claim_text",
        "extracted_citation", "matched_evidence_text", "evidence_match_method",
        "automated_verdict", "automated_confidence", "annotation",
    }
    required_annotation = {"citation_valid", "evidence_entails_claim", "evidence_relevance", "annotator_notes"}
    for g in gold:
        if set(g.keys()) != required_top:
            problems.append(f"{g['annotation_id']}: unexpected/missing top-level keys")
            break
        if set(g["annotation"].keys()) != required_annotation:
            problems.append(f"{g['annotation_id']}: unexpected/missing annotation keys")
            break
        if any(g["annotation"][k] != "" for k in required_annotation):
            problems.append(f"{g['annotation_id']}: annotation field not blank (pre-labeled)")
            break
        # gold file must never carry the A/B/C final system result / correction outcome
        if "final_field" in g or "correction" in g or "source" in g:
            problems.append(f"{g['annotation_id']}: leaks final_field/correction (forbidden)")
            break

    n_cases = len({g["document_id"] for g in gold})
    n_with_evidence = sum(1 for g in gold if g["matched_evidence_text"] is not None)
    n_without_evidence = len(gold) - n_with_evidence

    return {
        "problems": problems,
        "num_claims": len(gold),
        "num_cases": n_cases,
        "num_with_evidence": n_with_evidence,
        "num_without_evidence": n_without_evidence,
    }


GUIDE_MD = """\
# Gold Annotation Guide — Statutory Claim Verification

## What you are judging

Each row in `gold_annotation.jsonl` is ONE extracted claim: a sentence
(`claim_text`) from a machine-generated "Statutory Grounding" paragraph,
naming a specific statute/article (`extracted_citation`), together with
whatever canonical evidence text the system matched for that citation
(`matched_evidence_text`, or null if none was found).

You are asked for THREE independent judgments per claim, plus free-text
notes. There is no single "correct" field — judge each one on its own
terms, as described below.

**Judge ONLY against `matched_evidence_text`.** Do not use outside legal
knowledge, do not look up the actual statute elsewhere, do not consider
whether the underlying case was decided correctly, and do not use
`claim_text`'s surrounding case facts to guess at intent. If
`matched_evidence_text` does not settle a question, the answer is
"the evidence does not tell us" (NOT_ENOUGH_INFORMATION / UNCERTAIN), even
if you personally know the real statute says something else. This dataset
evaluates the PIPELINE (does it find and use the RIGHT evidence text
correctly), not your independent knowledge of Indian law.

**Do not look at `automated_verdict` / `automated_confidence` before
forming your own judgment.** They are included for later agreement
analysis, not as a suggestion. Read `claim_text` and
`matched_evidence_text` first, decide your own answer, and only then
(optionally) compare against the automated fields if you want to note a
disagreement in `annotator_notes`.

## Fields to fill in (all four start blank)

### 1. `citation_valid` — YES / NO / UNCERTAIN
Does `claim_text` genuinely, unambiguously reference the citation recorded
in `extracted_citation` (same provision type, number, and act)? This
checks the EXTRACTION, not the evidence match — you can answer this from
`claim_text` and `extracted_citation` alone, without looking at
`matched_evidence_text` at all.
- **YES**: the citation is clearly and correctly identified from the text.
- **NO**: the citation is wrong, garbled, or not actually present in
  `claim_text` (e.g. wrong section number extracted, act misattributed).
- **UNCERTAIN**: genuinely ambiguous phrasing in `claim_text` itself.

### 2. `evidence_entails_claim` — ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION / UNCERTAIN
Does `matched_evidence_text` support what `claim_text` asserts about that
provision?
- **ENTAILED**: the evidence text confirms the assertion in `claim_text`.
- **CONTRADICTED**: the evidence text states something that conflicts with
  the assertion in `claim_text`.
- **NOT_ENOUGH_INFORMATION**: the evidence text is on-topic but doesn't
  confirm or conflict with the specific assertion — OR
  `matched_evidence_text` is null (no evidence was matched at all: there
  is nothing to entail or contradict against, so this is the correct
  answer by construction, not a judgment call).
- **UNCERTAIN**: you cannot decide even after re-reading both texts
  carefully (rare — prefer NOT_ENOUGH_INFORMATION when the issue is
  "insufficient support" rather than "genuinely unclear wording").

### 3. `evidence_relevance` — RELEVANT / NOT_RELEVANT / UNCERTAIN
Independent of entailment: is `matched_evidence_text` actually about the
SAME provision `claim_text` cites, or did the evidence matcher attach the
wrong statute/section (this can happen especially for `fuzzy`-matched
rows)? A claim can be `evidence_relevance: NOT_RELEVANT` even if
`evidence_entails_claim` happens to look plausible by coincidence, and
vice versa — a relevant match can still fail to entail the claim.
- **RELEVANT**: the evidence text is genuinely about the cited provision.
- **NOT_RELEVANT**: the evidence text is about a different provision/act
  than the one `claim_text` cites (a bad match).
- **UNCERTAIN**: can't tell from the text alone.
- If `matched_evidence_text` is null (`evidence_match_method: no_evidence`),
  there is nothing to assess — use **UNCERTAIN** and note "no evidence
  matched" in `annotator_notes`.

### 4. `annotator_notes` — free text
Optional. Use for: disagreements with `automated_verdict`, ambiguous
phrasing you had to make a judgment call on, suspected extraction bugs,
or anything else worth flagging for review. Leave blank if nothing to add.

## What NOT to do
- Do not fill in a "correct final answer" for the claim — there is no such
  field, and none of A/B/C's final output/correction result is shown to
  you (deliberately, to avoid anchoring your judgment on what the system
  already decided to do).
- Do not edit `claim_text`, `extracted_citation`, or
  `matched_evidence_text` — annotate, don't correct the data.
- Do not skip rows with `matched_evidence_text: null` — `citation_valid`
  is still answerable from `claim_text` alone; the other two fields have
  the documented fallback answers above.

## Field reference
| Field | Source | Editable by annotator? |
|---|---|---|
| `annotation_id`, `document_id`, `claim_id` | pipeline output | No |
| `claim_text`, `extracted_citation` | pipeline output | No |
| `matched_evidence_text`, `evidence_match_method` | pipeline output | No |
| `automated_verdict`, `automated_confidence` | pipeline output (reference only) | No |
| `annotation.citation_valid` | **you fill in** | Yes |
| `annotation.evidence_entails_claim` | **you fill in** | Yes |
| `annotation.evidence_relevance` | **you fill in** | Yes |
| `annotation.annotator_notes` | **you fill in** | Yes |
"""


def _summary_template_md(num_claims: int, num_cases: int, num_with_evidence: int, num_without_evidence: int) -> str:
    return f"""\
# Gold Annotation Summary — TEMPLATE (fill in after annotation completes)

This is a blank template. Every count below is a placeholder ("__") to be
filled in once human annotation of `gold_annotation.jsonl` is complete.
Do not fill this in before annotation starts.

## Coverage (known now, from the completed pipeline run)
- Total claims: {num_claims}
- Total cases: {num_cases}
- Claims with matched evidence: {num_with_evidence}
- Claims without evidence (no_evidence): {num_without_evidence}

## Citation validity (`citation_valid`) — fill in after annotation
| Value | Count | % of {num_claims} |
|---|---|---|
| YES | __ | __ |
| NO | __ | __ |
| UNCERTAIN | __ | __ |

## Evidence entailment (`evidence_entails_claim`) — fill in after annotation
| Value | Count | % of {num_claims} |
|---|---|---|
| ENTAILED | __ | __ |
| CONTRADICTED | __ | __ |
| NOT_ENOUGH_INFORMATION | __ | __ |
| UNCERTAIN | __ | __ |

## Evidence relevance (`evidence_relevance`) — fill in after annotation
| Value | Count | % of {num_claims} |
|---|---|---|
| RELEVANT | __ | __ |
| NOT_RELEVANT | __ | __ |
| UNCERTAIN | __ | __ |

## Automated-vs-human agreement — fill in after annotation
Computed only over the {num_with_evidence} claims with matched evidence
(automated_verdict is one of ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION
for these; the {num_without_evidence} NO_EVIDENCE claims are excluded from
this comparison since automated_verdict is NO_EVIDENCE for those, a
different label space than evidence_entails_claim).

- Agreement definition: `annotation.evidence_entails_claim == automated_verdict`
  (UNCERTAIN human labels excluded from the denominator — decide before
  finalizing whether to treat UNCERTAIN as disagreement or exclude it, and
  state the choice here).
- Number of comparable claims (evidence matched, human label not UNCERTAIN): __
- Number of agreements: __
- Agreement rate: __%
- Confusion breakdown (human label x automated_verdict): __ (fill in a
  small table once counts are available)

## Notes
- These are preliminary counts pending full annotation; do not report them
  as final results until every row has a non-blank `annotation` block.
"""


def main() -> int:
    records_a = load_records("A")
    records_b = load_records("B")
    records_c = load_records("C")

    gold = build_gold_records(records_b)

    with GOLD_PATH.open("w", encoding="utf-8") as f:
        for g in gold:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")

    checks = run_checks(gold, records_a, records_b, records_c)

    GUIDE_PATH.write_text(GUIDE_MD, encoding="utf-8")
    SUMMARY_TEMPLATE_PATH.write_text(
        _summary_template_md(
            checks["num_claims"], checks["num_cases"],
            checks["num_with_evidence"], checks["num_without_evidence"],
        ),
        encoding="utf-8",
    )

    print("=== Schema / duplicate check ===")
    if checks["problems"]:
        print("PROBLEMS FOUND:")
        for p in checks["problems"]:
            print(" -", p)
    else:
        print("No problems found.")
    print()
    print(f"number of claims: {checks['num_claims']}")
    print(f"number of cases: {checks['num_cases']}")
    print(f"number with evidence: {checks['num_with_evidence']}")
    print(f"number without evidence: {checks['num_without_evidence']}")
    print()
    print("output paths:")
    print(" ", GOLD_PATH)
    print(" ", GUIDE_PATH)
    print(" ", SUMMARY_TEMPLATE_PATH)

    return 1 if checks["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
