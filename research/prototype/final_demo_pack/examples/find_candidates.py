#!/usr/bin/env python
"""
One-off, read-only scan of committed raw outputs/*.jsonl to surface REAL
candidate cases for each exemplar category requested for the demo pack.
Writes only research/prototype/final_demo_pack/examples/candidate_pool.json
(a dump of candidates for a human to then hand-pick from and write up in
prose) -- does not modify anything under outputs/. Selection criteria for
each category are stated in the printed summary and repeated in
EXAMPLES_INDEX.md so the final choice is auditable, not cherry-picked
silently.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
OUT = REPO_ROOT / "research/prototype/outputs"


def load_jsonl(rel):
    p = REPO_ROOT / rel
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def claims_of(row):
    return row.get("claims", [])


candidates = {}

# 1. Genuine CONTRADICTED catch (real evidence, real natural case)
contradicted = []
for src in [
    "research/prototype/outputs/final_gpu_validation_A.jsonl",
    "research/prototype/outputs/final_gpu_validation_B.jsonl",
    "research/prototype/outputs/natural_candidates_50_gpu_bare.jsonl",
    "research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl",
    "research/prototype/outputs/natural_candidates_batch2_gpu_bare.jsonl",
    "research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl",
]:
    for row in load_jsonl(src):
        for c in claims_of(row):
            if c.get("verdict") == "CONTRADICTED":
                contradicted.append({"source": src, "document_id": row["document_id"], "claim": c})
candidates["contradicted_natural"] = contradicted

# 2. Successful shipped correction (already known target)
shipped = []
for row in load_jsonl("research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl"):
    if row.get("status") == "corrected":
        shipped.append(row)
candidates["shipped_correction"] = shipped

# 3. Correction attempted + correctly rejected (correction_failed: model tried,
#    reverification did not reach ENTAILED, so nothing shipped)
rejected_failed = []
for src in [
    "research/prototype/outputs/natural_candidates_50_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/natural_candidates_batch2_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl",
]:
    for row in load_jsonl(src):
        if row.get("status") == "correction_failed":
            rejected_failed.append({"source": src, **row})
candidates["correction_failed_examples"] = rejected_failed[:5]

# 4. Scope violation
scope_violations = []
for src in [
    "research/prototype/outputs/natural_candidates_50_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/natural_candidates_batch2_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl",
]:
    for row in load_jsonl(src):
        if row.get("status") == "correction_scope_violation":
            scope_violations.append({"source": src, **row})
candidates["scope_violation_examples"] = scope_violations[:5]

# 5. NO_EVIDENCE case (trivial, but pick from final production regime data if possible)
no_evidence = []
for row in load_jsonl("research/prototype/outputs/final_gpu_validation_B.jsonl"):
    for c in claims_of(row):
        if c.get("verdict") == "NO_EVIDENCE":
            no_evidence.append({"source": "final_gpu_validation_B.jsonl", "document_id": row["document_id"], "claim": c})
candidates["no_evidence_examples"] = no_evidence[:5]

# 6. Evidence successfully retrieved by v1 (already have curated list)
v1_examples = json.loads((OUT / "evidence_coverage_v0_vs_v1.json").read_text(encoding="utf-8"))["newly_covered_examples"]
candidates["v1_newly_covered_examples"] = v1_examples[:5]

# 7. Labeled framing improvement: same document_id+claim_id, bare NEI -> labeled ENTAILED/CONTRADICTED
flips = []
for bare_src, labeled_src in [
    ("research/prototype/outputs/natural_candidates_50_gpu_bare.jsonl", "research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl"),
    ("research/prototype/outputs/natural_candidates_batch2_gpu_bare.jsonl", "research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl"),
]:
    bare_rows = {r["document_id"]: r for r in load_jsonl(bare_src)}
    labeled_rows = {r["document_id"]: r for r in load_jsonl(labeled_src)}
    for doc_id, brow in bare_rows.items():
        lrow = labeled_rows.get(doc_id)
        if not lrow:
            continue
        bclaims = {c["claim_id"]: c for c in claims_of(brow)}
        lclaims = {c["claim_id"]: c for c in claims_of(lrow)}
        for cid, bc in bclaims.items():
            lc = lclaims.get(cid)
            if lc and bc.get("verdict") == "NOT_ENOUGH_INFORMATION" and lc.get("verdict") in ("ENTAILED", "CONTRADICTED") and bc.get("evidence_id"):
                flips.append({
                    "document_id": doc_id, "claim_id": cid,
                    "bare_source": bare_src, "labeled_source": labeled_src,
                    "bare_claim": bc, "labeled_claim": lc,
                })
candidates["labeled_framing_flips"] = flips[:8]

# 8. System correctly declines to correct: high-confidence NEI (not low_confidence
#    sub_reason), so never triggers correction, despite not being ENTAILED
declined = []
for row in load_jsonl("research/prototype/outputs/final_gpu_validation_B.jsonl"):
    for c in claims_of(row):
        if (c.get("verdict") == "NOT_ENOUGH_INFORMATION" and c.get("sub_reason") != "low_confidence"
                and c.get("confidence") is not None and c.get("confidence") >= 0.95 and c.get("evidence_id")):
            declined.append({"source": "final_gpu_validation_B.jsonl", "document_id": row["document_id"], "claim": c})
candidates["correctly_declined_examples"] = declined[:5]

out_path = Path(__file__).resolve().parent / "candidate_pool.json"
out_path.write_text(json.dumps(candidates, indent=2, default=str), encoding="utf-8")
print(f"Wrote {out_path}")
for k, v in candidates.items():
    print(f"  {k}: {len(v)} candidates")
