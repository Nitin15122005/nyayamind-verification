#!/usr/bin/env python3
"""
Measures the real coverage impact of the v1 evidence supplement on actual
natural claims — re-derives claims fresh from the same committed
generated_field.text already used throughout this project (run_A_n30.jsonl,
run_natural_targeted.jsonl, and the two 50-case GPU batches' outputs),
using the CURRENT claim_parser (all fixes from every prior phase already
applied), matched once against v0-only and once against v0+v1.

READ-ONLY: every source file here is only ever read. No committed output
is modified. No GPU, no Qwen, no model inference of any kind.

Also re-runs the NO_EVIDENCE root-cause taxonomy (same categories as
scripts/diagnose_no_evidence.py) against whatever remains uncovered even
with v1, to show the v1 expansion did not just trade precision for
recall — every match is still exact-identity or the existing conservative
fuzzy fallback, never invented.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src import claim_parser
from src.data_loader import load_usable_evidence_from_config
from src.evidence_matcher import match_evidence

SOURCES = [
    ("run_A_n30.jsonl", None),
    ("run_natural_targeted.jsonl", "mode_B"),
    ("natural_candidates_50_gpu_bare.jsonl", None),
    ("natural_candidates_batch2_gpu_bare.jsonl", None),
]


def iter_generated_texts(outputs: Path):
    for fname, sub in SOURCES:
        path = outputs / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            block = rec[sub] if sub else rec
            yield fname, rec["document_id"], block["generated_field"]["text"]


def classify_no_evidence(cit, all_usable, fuzzy_threshold: float) -> str:
    if not cit.act_norm:
        return "unresolved_act"
    same_number = [e for e in all_usable if e.provision_type == cit.provision_type
                   and e.provision_number == cit.provision_number]
    if not same_number:
        return "genuinely_absent_no_such_provision_any_act"
    return "genuinely_absent_wrong_act_or_edition"


def main() -> int:
    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    config_v0 = dict(config)
    config_v0["use_evidence_v1"] = False
    config_v1 = dict(config)
    config_v1["use_evidence_v1"] = True

    _, all_usable_v0 = load_usable_evidence_from_config(config_v0, repo_root)
    _, all_usable_v1 = load_usable_evidence_from_config(config_v1, repo_root)
    exact_index_v0, _ = load_usable_evidence_from_config(config_v0, repo_root)
    exact_index_v1, _ = load_usable_evidence_from_config(config_v1, repo_root)
    print(f"v0 usable records: {len(all_usable_v0)}   v0+v1 usable records: {len(all_usable_v1)}", flush=True)

    n_claims = 0
    n_matched_v0 = 0
    n_matched_v1 = 0
    newly_covered = []
    still_uncovered_v1 = []
    seen_texts = set()

    for fname, doc_id, text in iter_generated_texts(outputs):
        if text in seen_texts:
            continue  # avoid double-counting exact-duplicate generations across sources
        seen_texts.add(text)
        for claim in claim_parser.extract_claims(text):
            n_claims += 1
            cit = claim.citation_extracted
            m0 = match_evidence(cit, exact_index_v0, all_usable_v0, fuzzy_threshold)
            m1 = match_evidence(cit, exact_index_v1, all_usable_v1, fuzzy_threshold)
            if m0.matched:
                n_matched_v0 += 1
            if m1.matched:
                n_matched_v1 += 1
            if m1.matched and not m0.matched:
                newly_covered.append({
                    "source": fname, "document_id": doc_id, "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text[:150],
                    "citation": cit.as_dict() if cit else None,
                    "new_evidence_id": m1.evidence.dataset_citation_key,
                })
            if not m1.matched:
                bucket = classify_no_evidence(cit, all_usable_v1, fuzzy_threshold) if cit else "no_citation"
                still_uncovered_v1.append({
                    "source": fname, "document_id": doc_id, "claim_id": claim.claim_id,
                    "citation": cit.as_dict() if cit else None, "bucket": bucket,
                })

    bucket_counts = Counter(r["bucket"] for r in still_uncovered_v1)

    print(f"\nDistinct generated texts scanned: {len(seen_texts)}")
    print(f"Total claims: {n_claims}")
    print(f"Matched, v0-only:  {n_matched_v0} ({100*n_matched_v0/n_claims:.1f}%)")
    print(f"Matched, v0+v1:    {n_matched_v1} ({100*n_matched_v1/n_claims:.1f}%)")
    print(f"Newly covered by v1: {len(newly_covered)}")
    print(f"Still NO_EVIDENCE with v1: {len(still_uncovered_v1)}")
    print(f"Remaining taxonomy: {dict(bucket_counts)}")

    result = {
        "n_claims": n_claims, "n_matched_v0": n_matched_v0, "n_matched_v1": n_matched_v1,
        "coverage_v0_pct": round(100 * n_matched_v0 / n_claims, 1),
        "coverage_v1_pct": round(100 * n_matched_v1 / n_claims, 1),
        "n_newly_covered_by_v1": len(newly_covered),
        "n_still_no_evidence_with_v1": len(still_uncovered_v1),
        "remaining_taxonomy": dict(bucket_counts),
        "newly_covered_examples": newly_covered[:30],
    }
    (outputs / "evidence_coverage_v0_vs_v1.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {outputs / 'evidence_coverage_v0_vs_v1.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
