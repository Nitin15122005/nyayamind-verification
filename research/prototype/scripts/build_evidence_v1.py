#!/usr/bin/env python3
"""
Builds research/data/evidence/canonical_statutes_v1.jsonl and
evidence_audit_v1.jsonl from the 82 records researched for this task
(3 corrections to known-bad v0 records + 79 genuinely new citations,
ranked 64-143 by real NyayaRAG corpus citation frequency). Source data:
JSON files written to the session scratchpad during research (4 parallel
agents, each independently fetching/searching IndianKanoon.org, one
attempt at indiacode.nic.in per agent — consistently 403, matching the
v0 corpus's own documented finding).

READ-ONLY w.r.t. the v0 corpus: canonical_statutes.jsonl and
evidence_audit.jsonl are read (to confirm which 3 keys are corrections)
but never written. This script's own output files
(canonical_statutes_v1.jsonl, evidence_audit_v1.jsonl) are new,
additive files — the v0 files remain byte-identical.

Audit policy for evidence_audit_v1.jsonl (distinct from, and less
exhaustive than, v0's audit): 8 of the 82 records (~10%, spread across
all 4 research batches) were independently re-fetched and spot-checked
directly in this session against the researching agent's reported
canonical_text -- all 8 matched exactly. Given that result, records with
text_provenance="webfetch_verbatim" and confidence="high" are assigned
audit_verdict="VERIFIED_EXACT" (matching v0's own definition: text is a
direct fetch, not a paraphrase). Records with
text_provenance="websearch_synthesized_summary" are assigned
audit_verdict="SOURCE_ONLY" (source confirmed to exist and be the right
provision, but the exact text was not independently re-fetched) --
`usable_evidence_verdicts` in config only accepts VERIFIED_EXACT/
VERIFIED_CONTENT by default, so SOURCE_ONLY records are NOT usable unless
someone deliberately widens that config set, exactly as for v0's own
SOURCE_ONLY records. This is an honest, smaller-scale audit, not a claim
of the same 100% independent-re-fetch coverage v0's audit achieved.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = _PROTOTYPE_ROOT.parent.parent
EVIDENCE_DIR = REPO_ROOT / "research" / "data" / "evidence"

SCRATCH = Path(
    r"C:\Users\NITINS~1\AppData\Local\Temp\claude\D--Programs-nyayamind-verification"
    r"\504df47e-1e59-42b7-8df8-0efa4e032e11\scratchpad"
)

# The 8 source_urls independently re-fetched and confirmed exact in this
# session (see build notes above) -- these get an extra provenance note.
SPOT_CHECKED_URLS = {
    "https://indiankanoon.org/doc/192138551/",
    "https://indiankanoon.org/doc/538436/",
    "https://indiankanoon.org/doc/555882/",
    "https://indiankanoon.org/doc/1791573/",
    "https://indiankanoon.org/doc/1030013/",
    "https://indiankanoon.org/doc/151999671/",
    "https://indiankanoon.org/doc/48127346/",
    "https://indiankanoon.org/doc/1841764/",
}


def main() -> int:
    v0_keys = set()
    with (EVIDENCE_DIR / "canonical_statutes.jsonl").open(encoding="utf-8") as f:
        for line in f:
            v0_keys.add(json.loads(line)["dataset_citation_key"])

    all_records = []
    for i in range(1, 5):
        all_records.extend(json.loads((SCRATCH / f"batch{i}.json").read_text(encoding="utf-8")))

    assert len(all_records) == 82, f"expected 82 records, got {len(all_records)}"
    keys = [r["dataset_citation_key"] for r in all_records]
    assert len(set(keys)) == 82, "duplicate dataset_citation_key found"

    corrections = [r for r in all_records if r["dataset_citation_key"] in v0_keys]
    new_records = [r for r in all_records if r["dataset_citation_key"] not in v0_keys]
    assert len(corrections) == 3, f"expected exactly 3 corrections, got {len(corrections)}"
    assert len(new_records) == 79, f"expected exactly 79 new records, got {len(new_records)}"

    canonical_out = []
    audit_out = []
    for r in all_records:
        r = dict(r)
        r.pop("supersedes_v0_key", None)
        is_correction = r["dataset_citation_key"] in v0_keys
        r["v1_supersedes_v0_record"] = is_correction
        canonical_out.append(r)

        if r["text_provenance"] == "webfetch_verbatim" and r["confidence"] == "high":
            verdict = "VERIFIED_EXACT"
        elif r["text_provenance"] == "websearch_synthesized_summary":
            verdict = "SOURCE_ONLY"
        else:
            verdict = "SOURCE_ONLY"  # conservative default for anything unexpected

        audit_out.append({
            "dataset_citation_key": r["dataset_citation_key"],
            "audit_verdict": verdict,
            "audit_method": (
                "independently_refetched_and_spot_checked_this_session"
                if r["source_url"] in SPOT_CHECKED_URLS
                else "build_time_provenance_only_not_independently_refetched"
            ),
            "audit_date": "2026-08-27",
            "notes": (
                "Corrects a known v0 INVALID/UNRESOLVED/wrong-historical_status record; see "
                "research/data/evidence/README.md 'Invalid / unresolved / source-only examples'."
                if is_correction else ""
            ),
        })

    canonical_path = EVIDENCE_DIR / "canonical_statutes_v1.jsonl"
    audit_path = EVIDENCE_DIR / "evidence_audit_v1.jsonl"
    with canonical_path.open("w", encoding="utf-8") as f:
        for r in canonical_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with audit_path.open("w", encoding="utf-8") as f:
        for r in audit_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_exact = sum(1 for a in audit_out if a["audit_verdict"] == "VERIFIED_EXACT")
    n_source_only = sum(1 for a in audit_out if a["audit_verdict"] == "SOURCE_ONLY")
    print(f"v1 corpus: {len(canonical_out)} records ({len(corrections)} corrections to v0, "
          f"{len(new_records)} genuinely new)")
    print(f"v1 audit: {n_exact} VERIFIED_EXACT (usable), {n_source_only} SOURCE_ONLY (not usable by default)")
    print(f"Wrote {canonical_path}")
    print(f"Wrote {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
