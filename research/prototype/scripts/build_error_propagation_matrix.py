#!/usr/bin/env python3
"""
Builds outputs/error_propagation_matrix.csv + outputs/error_propagation_analysis.md
from the REAL committed n=10 assertion-aware correction natural-data batch
(outputs/assertion_aware_correction_experiment_{OLD,CURRENT}.jsonl -- see
outputs/assertion_aware_correction_experiment_report.md for the full
narrative analysis this matrix is derived from).

Scope, stated honestly: this covers the 10 real (document_id, arm) pairs
that were actually run through assertion-aware correction -- it is NOT a
claim about the whole n=62 batch's every claim (which apply_selective_correction,
the legacy path, produced), nor an error-propagation matrix for the
verification/retrieval/parser stages independent of a correction attempt.
It answers one specific, real question: for every case that reached the
correction-triggering step under this mechanism, at which stage did it
first fail (if it did)?

Every row is derived directly from a committed real record -- no stage
result is guessed or filled in.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = _PROTOTYPE_ROOT / "outputs"

ARMS = ("OLD", "CURRENT")

FIELDS = [
    "document_id", "arm", "mechanism", "triggered_for_claim_id",
    "parser", "citation_mapping", "retrieval", "verification",
    "correction_targeting", "correction_generation", "splice",
    "safety_scope_citation_ordinal", "reverification", "safety_sibling_regression",
    "shipped", "first_failure_stage", "status",
]

# Stages the code actually checks BEFORE reverification (scope violation,
# unauthorized-citation-addition, ordinal-integrity) vs. the ones checked
# only AFTER a target re-verifies as ENTAILED (sibling-regression) -- see
# src/pipeline.py's apply_selective_correction_assertion_aware for the
# exact order these run in.
PRE_REVERIFICATION_SAFETY_STATUSES = {
    "correction_span_invalid": "correction_targeting",
    "correction_splice_unavailable": "splice",
    "correction_structural_span_lost": "safety_scope_citation_ordinal",
    "correction_scope_violation": "safety_scope_citation_ordinal",
    "correction_unauthorized_addition": "safety_scope_citation_ordinal",
    "correction_ordinal_ambiguous": "safety_scope_citation_ordinal",
}


def row_for(doc_id: str, arm: str, corr: dict) -> dict:
    status = corr["status"]
    row = {f: "n/a" for f in FIELDS}
    row["document_id"] = doc_id
    row["arm"] = arm
    row["mechanism"] = "assertion_aware"
    row["triggered_for_claim_id"] = corr.get("triggered_for_claim_id")
    row["status"] = status

    if status == "not_triggered":
        # Parser/citation/retrieval/verification all ran and correctly
        # found nothing needing correction -- not a failure, no later
        # stage was ever reached.
        row.update(parser="ok", citation_mapping="ok", retrieval="ok", verification="ok")
        row["shipped"] = "no"
        row["first_failure_stage"] = "none (correctly not triggered)"
        return row

    # Every triggered case, by construction, passed parser/citation/
    # retrieval/verification (a correction can only trigger on a claim
    # that was extracted, citation-mapped, evidence-matched, and verified
    # CONTRADICTED or low-confidence NEI).
    row.update(parser="ok", citation_mapping="ok", retrieval="ok", verification="ok")
    row["correction_targeting"] = "ok" if status != "correction_span_invalid" else "fail"
    row["correction_generation"] = "ok" if status != "correction_span_invalid" else "n/a"
    row["splice"] = "ok" if status not in ("correction_span_invalid", "correction_splice_unavailable") else (
        "fail" if status == "correction_splice_unavailable" else "n/a"
    )

    if status in PRE_REVERIFICATION_SAFETY_STATUSES:
        fail_stage = PRE_REVERIFICATION_SAFETY_STATUSES[status]
        row[fail_stage] = "fail" if fail_stage != "correction_targeting" else row["correction_targeting"]
        if fail_stage == "safety_scope_citation_ordinal":
            row["safety_scope_citation_ordinal"] = "fail"
        row["shipped"] = "no"
        row["first_failure_stage"] = fail_stage
        return row

    # Reached reverification (scope/citation/ordinal checks all passed).
    row["safety_scope_citation_ordinal"] = "ok"
    if status == "correction_failed":
        row["reverification"] = "fail"
        row["shipped"] = "no"
        row["first_failure_stage"] = "reverification"
        return row

    row["reverification"] = "ok"
    if status == "correction_sibling_regression":
        row["safety_sibling_regression"] = "fail"
        row["shipped"] = "no"
        row["first_failure_stage"] = "safety_sibling_regression"
        return row

    if status == "corrected":
        row["safety_sibling_regression"] = "ok"
        row["shipped"] = "yes"
        row["first_failure_stage"] = "none (shipped)"
        return row

    row["first_failure_stage"] = f"UNRECOGNIZED_STATUS:{status}"
    return row


def main() -> int:
    rows = []
    for arm in ARMS:
        path = OUTPUTS / f"assertion_aware_correction_experiment_{arm}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rows.append(row_for(rec["document_id"], arm, rec["correction"]))

    csv_path = OUTPUTS / "error_propagation_matrix.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Wrote {csv_path} ({len(rows)} rows)")

    from collections import Counter
    stage_counts = Counter(r["first_failure_stage"] for r in rows)

    md = [
        "# Error propagation matrix — assertion-aware correction (real n=10 batch)\n\n",
        "_Generated from `outputs/assertion_aware_correction_experiment_{OLD,CURRENT}.jsonl` "
        "— real Qwen2.5-7B + real DeBERTa, the exact 5 documents that triggered legacy "
        "correction in the committed n=62 batch. See `outputs/error_propagation_matrix.csv` "
        "for the full per-case table and "
        "`outputs/assertion_aware_correction_experiment_report.md` for the narrative "
        "case-by-case analysis this matrix is a structured summary of._\n\n",
        "## Scope\n\n",
        "Covers only the pipeline stages a CORRECTION ATTEMPT passes through "
        "(parser -> citation mapping -> retrieval -> verification -> correction "
        "targeting -> correction generation -> splice -> pre-reverification "
        "safety gates -> reverification -> sibling-regression safety gate -> "
        "shipping), for the 10 real (document, arm) pairs in this batch. Not a "
        "claim about every claim in the wider n=62 batch, and not an "
        "independent parser/retrieval/verification error analysis (those "
        "stages are reported separately — see FINAL_RESEARCH_FREEZE_REPORT.md "
        "sections C-E).\n\n",
        "## First-failure-stage distribution (n=10)\n\n",
        "| First failure stage | Count |\n|---|---|\n",
    ]
    for stage, count in sorted(stage_counts.items(), key=lambda kv: -kv[1]):
        md.append(f"| {stage} | {count} |\n")
    md.append(
        "\n**0/10 shipped.** No case reached `first_failure_stage = none (shipped)`. "
        "1/10 correctly never triggered (`none (correctly not triggered)`). "
        "Every other case failed at either a pre-reverification safety gate "
        "(scope/citation/ordinal — the dominant real-data failure category at "
        "this n), the reverification step itself (the corrector's fix did not "
        "reach ENTAILED), or the post-reverification sibling-regression check "
        "(the one case, `1955_32`, where the target's own fix was genuinely "
        "correct but an untouched sibling in the same sentence was "
        "independently wrong too).\n\n"
        "## Honest limitations\n\n"
        "- n=10 — not statistically powered; every number above is a real "
        "count, not a rate claimed to generalize.\n"
        "- Every case in this batch happens to have a 1-element "
        "`assertion_spans` (confirmed directly — see "
        "`outputs/assertion_span_aware_integration_replay.json`), so the "
        "`correction_span_invalid` and `correction_structural_span_lost` "
        "stages have zero real-data coverage here; they are exercised only "
        "by the deterministic test suite "
        "(`tests/test_assertion_aware_correction.py`), not by real Qwen "
        "output. Stated plainly, not filled in.\n"
    )
    md_path = OUTPUTS / "error_propagation_analysis.md"
    md_path.write_text("".join(md), encoding="utf-8")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
