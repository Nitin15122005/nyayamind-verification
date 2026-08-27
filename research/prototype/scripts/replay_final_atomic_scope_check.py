#!/usr/bin/env python3
"""
Final, comprehensive replay of EVERY real scope-violation correction
attempt across BOTH natural GPU experiments (batch 1:
natural_candidates_50_gpu_corrections_detail.jsonl, batch 2:
natural_candidates_batch2_gpu_corrections_detail.jsonl) through the FULLY
EXTENDED atomic-claim mechanism (semicolon / while / citation-keyword-
boundary / parenthetical-gloss / respectively spans) — including the
citation-keyword-boundary split added AFTER the batch-2 GPU run completed,
so this replay is the authoritative final answer to "how many real
attempts does the finished Phase-1 mechanism unblock."

NO GPU, NO Qwen call — pure deterministic replay of already-captured real
text through `pipeline._scope_violation()`.

READ-ONLY: both corrections_detail.jsonl files only read. Writes
outputs/atomic_scope_check_final_replay.{md,json}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

from src import claim_parser, pipeline

SOURCES = [
    ("batch1", "natural_candidates_50_gpu_corrections_detail.jsonl"),
    ("batch2", "natural_candidates_batch2_gpu_corrections_detail.jsonl"),
]


def build_claims(generated_text: str) -> list[dict]:
    claims = claim_parser.extract_claims(generated_text)
    return [
        {"claim_id": c.claim_id, "claim_text": c.claim_text, "assertion_text": c.assertion_text,
         "assertion_spans": list(c.assertion_spans),
         "citation": c.citation_extracted.as_dict() if c.citation_extracted else None}
        for c in claims
    ]


def main() -> int:
    outputs = _PROTOTYPE_ROOT / "outputs"

    all_violations = []
    for batch_name, fname in SOURCES:
        path = outputs / fname
        if not path.exists():
            continue
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        for r in rows:
            if r["status"] == "correction_scope_violation":
                r = dict(r)
                r["batch"] = batch_name
                all_violations.append(r)

    print(f"Replaying {len(all_violations)} real scope-violation attempts "
          f"(batch1 + batch2) through the fully-extended mechanism...", flush=True)

    results = []
    for r in all_violations:
        doc_id = r["document_id"]
        target_id = r["triggered_for_claim_id"]
        original_text = r["original_field_text"]
        regenerated_text = r["regenerated_text"]

        claims = build_claims(original_text)
        by_id = {c["claim_id"]: c for c in claims}
        target = by_id.get(target_id)

        legacy_v = pipeline._scope_violation(claims, target_id, regenerated_text,
                                              use_assertion_text=False, use_assertion_spans=False)
        spans_v = pipeline._scope_violation(claims, target_id, regenerated_text,
                                             use_assertion_text=True, use_assertion_spans=True)

        results.append({
            "batch": r["batch"], "document_id": doc_id, "target_claim_id": target_id,
            "target_citation": target["citation"] if target else None,
            "target_assertion_text": target["assertion_text"] if target else None,
            "legacy_violation": legacy_v,
            "assertion_spans_violation": spans_v,
            "unblocked": legacy_v and not spans_v,
            "original_field_text": original_text,
            "regenerated_text": regenerated_text,
        })
        cit = target["citation"] if target else None
        cit_str = f"{cit['provision_type']} {cit['provision_number']}" if cit else "?"
        outcome = "UNBLOCKED" if (legacy_v and not spans_v) else "still blocked"
        print(f"  [{r['batch']}] {doc_id}/{target_id} ({cit_str}): "
              f"legacy={legacy_v} final={spans_v} -> {outcome}", flush=True)

    n_unblocked = sum(1 for r in results if r["unblocked"])
    n_total = len(results)

    (outputs / "atomic_scope_check_final_replay.json").write_text(json.dumps({
        "n_scope_violations_replayed": n_total,
        "n_unblocked_final": n_unblocked,
        "results": results,
    }, indent=2), encoding="utf-8")

    md = [
        "# Final Atomic-Claim Scope-Check Replay — all real scope violations, both GPU batches",
        "",
        "_No GPU, no new Qwen call. Replays every real `correction_scope_violation` from",
        "both natural GPU experiments through the fully-extended mechanism (semicolon /",
        "while / citation-keyword-boundary / parenthetical-gloss / respectively spans)._",
        "",
        f"**{n_unblocked}/{n_total} real scope violations unblocked** by the finished",
        "atomic-claim mechanism.",
        "",
        "| batch | document | target | citation | legacy | final | outcome |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        cit = r["target_citation"]
        cit_str = f"{cit['provision_type']} {cit['provision_number']}" if cit else "?"
        outcome = "**UNBLOCKED**" if r["unblocked"] else "still blocked"
        md.append(f"| {r['batch']} | `{r['document_id']}` | {r['target_claim_id']} | {cit_str} | "
                   f"{r['legacy_violation']} | {r['assertion_spans_violation']} | {outcome} |")

    (outputs / "atomic_scope_check_final_replay.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\n{n_unblocked}/{n_total} unblocked (final, both batches).")
    print(f"Wrote {outputs / 'atomic_scope_check_final_replay.json'}")
    print(f"Wrote {outputs / 'atomic_scope_check_final_replay.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
