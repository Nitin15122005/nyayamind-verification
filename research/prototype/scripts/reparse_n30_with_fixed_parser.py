#!/usr/bin/env python
"""
Re-run the (now fixed) deterministic claim_parser + evidence_matcher stage
over the ALREADY-GENERATED Qwen output in run_A_n30.jsonl, without touching
any model or GPU. This measures Phase 1's actual before/after impact on
real generated text — not synthetic examples — by comparing the
already-on-disk `citation_extracted` / evidence-match results (produced by
the pre-fix parser) against what the fixed parser produces for the exact
same generated_field.text.

Read-only w.r.t. every existing output file: run_A_n30.jsonl is only read,
never modified. Writes a new comparison file,
outputs/parser_fix_before_after_n30.json, plus a markdown summary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.claim_parser import extract_claims
from src.data_loader import load_usable_evidence
from src.evidence_matcher import match_evidence


def main() -> int:
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    exact_index, all_usable = load_usable_evidence(
        canonical_path, audit_path, set(config["usable_evidence_verdicts"])
    )
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    in_path = _PROTOTYPE_ROOT / "outputs" / "run_A_n30.jsonl"
    out_path = _PROTOTYPE_ROOT / "outputs" / "parser_fix_before_after_n30.json"

    per_case = []
    totals = {
        "old_claims": 0, "new_claims": 0,
        "old_with_evidence": 0, "new_with_evidence": 0,
        "old_unresolved_act": 0, "new_unresolved_act": 0,
        "act_norm_changed": 0,
    }

    with in_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            doc_id = rec["document_id"]
            text = rec["generated_field"]["text"]

            old_claims = rec["claims"]
            new_claims = extract_claims(text)

            new_records = []
            for claim in new_claims:
                citation = claim.citation_extracted
                match = match_evidence(citation, exact_index, all_usable, fuzzy_threshold)
                new_records.append({
                    "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text,
                    "citation_extracted": citation.as_dict(),
                    "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
                    "evidence_match_method": match.match_method,
                })

            totals["old_claims"] += len(old_claims)
            totals["new_claims"] += len(new_records)
            totals["old_with_evidence"] += sum(1 for c in old_claims if c["evidence_id"] is not None)
            totals["new_with_evidence"] += sum(1 for c in new_records if c["evidence_id"] is not None)
            totals["old_unresolved_act"] += sum(
                1 for c in old_claims if c["citation_extracted"] and not c["citation_extracted"]["act_norm"]
            )
            totals["new_unresolved_act"] += sum(
                1 for c in new_records if not c["citation_extracted"]["act_norm"]
            )

            # Pair up old vs new by claim_text + provision_number where possible
            # (best-effort, for the act_norm_changed diagnostic count only).
            old_by_key = {}
            for c in old_claims:
                cit = c.get("citation_extracted")
                if cit:
                    old_by_key.setdefault((c["claim_text"], cit["provision_type"], cit["provision_number"]), []).append(cit["act_norm"])
            for c in new_records:
                cit = c["citation_extracted"]
                key = (c["claim_text"], cit["provision_type"], cit["provision_number"])
                old_acts = old_by_key.get(key)
                if old_acts and cit["act_norm"] not in old_acts:
                    totals["act_norm_changed"] += 1

            per_case.append({
                "document_id": doc_id,
                "old_claim_count": len(old_claims),
                "new_claim_count": len(new_records),
                "old_evidence_count": sum(1 for c in old_claims if c["evidence_id"] is not None),
                "new_evidence_count": sum(1 for c in new_records if c["evidence_id"] is not None),
                "old_claims": old_claims,
                "new_claims": new_records,
            })

    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"totals": totals, "cases": per_case}, f, indent=2, ensure_ascii=False)

    print(f"Wrote {out_path}")
    print(json.dumps(totals, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
