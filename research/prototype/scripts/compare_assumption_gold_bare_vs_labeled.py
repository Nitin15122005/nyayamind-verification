#!/usr/bin/env python3
"""
Verifier performance against the provisional ("assumption") gold labels in
assumption_annotation.jsonl, bare vs labeled framing.

assumption_annotation.jsonl already stores each evidence-matched claim's
BARE automated_verdict (that is exactly how these 88 claims were produced,
in the pre-v1, pre-atomic-scope era of this project -- all under bare
framing). This script does NOT recompute bare (reuses the stored value
verbatim, avoiding any risk of silently rescoring it differently) and adds
ONE new thing: the LABELED-framing verdict for the same 38 evidence-matched
claims, via a fresh CPU-only DeBERTa call against the exact same
matched_evidence_text already on record. No claim is re-parsed, no evidence
is re-matched, no GPU is used, no Qwen model is touched.

PROVISIONAL / ASSUMPTION-BASED, same caveat as assumption_annotation.jsonl
itself: none of the numbers here are lawyer-verified ground truth. They
describe agreement between two machine-produced label sets, not correctness
against real legal ground truth.

Nothing overwritten; new, distinctly-named output files only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.data_loader import load_usable_evidence
from src.verifier import NLIVerifier, format_premise, PREMISE_FRAMING_LABELED


def main() -> int:
    outputs = _PROTOTYPE_ROOT / "outputs"
    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent

    # v0-only pool: assumption_annotation.jsonl predates the v1 supplement
    # and was built entirely against the base 59-record corpus (matching
    # its own stored evidence_match_method values).
    exact_index, all_usable = load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )
    by_key = {e.dataset_citation_key: e for e in all_usable}
    # Fallback lookup by (provision_type, provision_number, act_norm) in case
    # dataset_citation_key phrasing differs from the citation's own act_raw.
    by_identity = {(e.provision_type, e.provision_number, e.act_norm): e for e in all_usable}

    rows = [json.loads(l) for l in (outputs / "assumption_annotation.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    matched = [r for r in rows if r.get("matched_evidence_text") is not None]
    print(f"Total assumption-annotated claims: {len(rows)}; evidence-matched: {len(matched)}", flush=True)

    print("Loading DeBERTa verifier on CPU...", flush=True)
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"], confidence_threshold=0.70,
        max_sequence_length=config["verification"]["max_sequence_length"], device="cpu",
    )
    verifier.load()

    out_rows = []
    unresolved_provision = 0
    for r in matched:
        cit = r["extracted_citation"]
        ev = by_identity.get((cit["provision_type"], cit["provision_number"], cit["act_norm"]))
        if ev is None or ev.canonical_text != r["matched_evidence_text"]:
            # Fall back to a direct text-match scan (handles the rare case
            # where the stored act_norm differs slightly from the matched
            # record's own, e.g. a fuzzy match).
            ev = next((e for e in all_usable if e.canonical_text == r["matched_evidence_text"]), None)
        if ev is None:
            unresolved_provision += 1
            out_rows.append({**r, "labeled_verdict": None, "labeled_confidence": None,
                              "_note": "could not re-resolve evidence record for labeled premise"})
            continue

        premise = format_premise(
            ev.canonical_text, framing=PREMISE_FRAMING_LABELED,
            provision_type=ev.provision_type, provision_number=ev.provision_number, act=ev.act,
        )
        result = verifier.verify(premise=premise, hypothesis=r["claim_text"])
        out_rows.append({
            "annotation_id": r["annotation_id"], "document_id": r["document_id"], "claim_id": r["claim_id"],
            "claim_text": r["claim_text"],
            "bare_verdict": r["automated_verdict"], "bare_confidence": r["automated_confidence"],
            "labeled_verdict": result.label, "labeled_confidence": result.confidence,
            "assumption_evidence_entails_claim": r["assumption_annotation"]["evidence_entails_claim"],
            "assumption_citation_valid": r["assumption_annotation"]["citation_valid"],
        })

    print(f"Could not re-resolve evidence for {unresolved_provision} claims (excluded from comparison).", flush=True)

    def agreement(field: str) -> tuple[int, int]:
        agree = sum(1 for r in out_rows if r.get(field) is not None
                    and r.get(field) == r["assumption_evidence_entails_claim"])
        total = sum(1 for r in out_rows if r.get(field) is not None)
        return agree, total

    bare_agree, bare_total = agreement("bare_verdict")
    labeled_agree, labeled_total = agreement("labeled_verdict")

    bare_dist = Counter(r["bare_verdict"] for r in out_rows if r.get("bare_verdict"))
    labeled_dist = Counter(r["labeled_verdict"] for r in out_rows if r.get("labeled_verdict"))

    print(f"\nBare vs assumption:    {bare_agree}/{bare_total} = {bare_agree/bare_total*100:.1f}% agreement" if bare_total else "n/a")
    print(f"Labeled vs assumption: {labeled_agree}/{labeled_total} = {labeled_agree/labeled_total*100:.1f}% agreement" if labeled_total else "n/a")
    print(f"Bare verdict distribution: {dict(bare_dist)}")
    print(f"Labeled verdict distribution: {dict(labeled_dist)}")

    result = {
        "experiment": "assumption_gold_bare_vs_labeled_agreement",
        "scope": "PROVISIONAL/ASSUMPTION-BASED -- assumption_annotation.jsonl is Claude-generated "
                 "provisional labeling, NOT lawyer-verified ground truth. Describes agreement between "
                 "two machine-produced label sets. bare_verdict reused verbatim from "
                 "assumption_annotation.jsonl (not recomputed); labeled_verdict is a fresh CPU DeBERTa "
                 "call against the same stored evidence text, this session.",
        "n_evidence_matched_claims": len(matched),
        "n_unresolved_for_labeled": unresolved_provision,
        "bare_agreement_with_assumption": {"agree": bare_agree, "total": bare_total,
                                            "pct": round(bare_agree/bare_total*100, 1) if bare_total else None},
        "labeled_agreement_with_assumption": {"agree": labeled_agree, "total": labeled_total,
                                               "pct": round(labeled_agree/labeled_total*100, 1) if labeled_total else None},
        "bare_verdict_distribution": dict(bare_dist),
        "labeled_verdict_distribution": dict(labeled_dist),
    }
    (outputs / "assumption_gold_bare_vs_labeled_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (outputs / "assumption_gold_bare_vs_labeled_claims.jsonl").open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nWrote {outputs / 'assumption_gold_bare_vs_labeled_metrics.json'}")
    print(f"Wrote {outputs / 'assumption_gold_bare_vs_labeled_claims.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
