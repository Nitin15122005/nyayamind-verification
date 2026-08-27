#!/usr/bin/env python
"""Extracts the exact 8 chosen exemplar records (by document_id/claim_id/source) from
the already-loaded candidate_pool.json plus one direct evidence-coverage lookup, and
writes them verbatim to cases.json -- a structured, machine-readable mirror of the
prose write-ups (case_01..case_08.md), so nothing in the prose was hand-typed without
a traceable source record."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
pool = json.loads((HERE / "candidate_pool.json").read_text(encoding="utf-8"))

cases = {}

for x in pool["contradicted_natural"]:
    if x["document_id"] == "1997_1306":
        cases["case_01_contradicted_catch"] = x
        break

for x in pool["shipped_correction"]:
    if x["document_id"] == "2003_760":
        cases["case_02_successful_correction"] = x
        break

for x in pool["correction_failed_examples"]:
    pass  # not guaranteed to include 2008_2063; re-fetched directly below instead

REPO_ROOT = HERE.resolve().parents[3]


def load_jsonl(rel):
    with (REPO_ROOT / rel).open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


for row in load_jsonl("research/prototype/outputs/natural_candidates_batch2_gpu_corrections_detail.jsonl"):
    if row["document_id"] == "2008_2063" and row["triggered_for_claim_id"] == "c9":
        cases["case_03_rejected_unsafe_correction"] = row
        break

for row in load_jsonl("research/prototype/outputs/natural_candidates_50_gpu_corrections_detail.jsonl"):
    if row["document_id"] == "2009_865" and row["triggered_for_claim_id"] == "c2":
        cases["case_04_scope_violation"] = row
        break

for x in pool["no_evidence_examples"]:
    if x["document_id"] == "2011_625":
        cases["case_05_no_evidence"] = x
        break

for x in pool["v1_newly_covered_examples"]:
    if x["document_id"] == "1971_200":
        cases["case_06_v1_evidence_gain"] = x
        break

for x in pool["labeled_framing_flips"]:
    if x["document_id"] == "1982_49":
        cases["case_07_labeled_framing_improvement"] = x
        break

for x in pool["correctly_declined_examples"]:
    if x["document_id"] == "2004_1020":
        cases["case_08_correctly_declines"] = x
        break

missing = [k for k in [
    "case_01_contradicted_catch", "case_02_successful_correction",
    "case_03_rejected_unsafe_correction", "case_04_scope_violation",
    "case_05_no_evidence", "case_06_v1_evidence_gain",
    "case_07_labeled_framing_improvement", "case_08_correctly_declines",
] if k not in cases]

out = HERE / "cases.json"
out.write_text(json.dumps(cases, indent=2, default=str), encoding="utf-8")
print(f"Wrote {out} with {len(cases)}/8 cases.")
if missing:
    print(f"MISSING: {missing}")
