#!/usr/bin/env python3
"""
Final pre-GPU audit (Priority 1 of the "final pass"): classify every real
NO_EVIDENCE claim, on the full v0+v1 evidence pool, into FOUR categories
instead of three:

  - unresolved_act:        parser could not resolve act_norm at all
  - genuinely_absent_no_such_provision_any_act: provision number/type not in
                            the corpus under ANY act
  - genuinely_absent_wrong_act_or_edition: provision number/type exists
                            under a DIFFERENT act, correctly NOT matched
  - parser_or_matcher_defect: provision number/type exists under an act that
                            is plausibly THE SAME REAL ACT the citation
                            means, but normalize_act()/alias table/fuzzy
                            threshold fails to connect them — a genuine bug
                            candidate, not a corpus gap.

The 4th category is decided by evidence, not guesswork: for every
"wrong_act_or_edition" case, compute the token overlap between the
citation's act_norm and the candidate evidence act_norm. A near-miss
(0.5 <= overlap < 0.8) is flagged for manual inspection as a possible
alias/normalization gap; overlap 0.0 is a definitionally different act
(safe, correctly unmatched) and stays classified as a genuine corpus gap.

READ-ONLY. No GPU. No new evidence written. No committed output modified.
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

from src import claim_parser
from src.claim_parser import act_significant_words
from src.data_loader import load_usable_evidence_from_config
from src.evidence_matcher import match_evidence, _token_overlap

SOURCES = [
    ("run_A_n30.jsonl", None),
    ("run_natural_targeted.jsonl", "mode_B"),
    ("natural_candidates_50_gpu_bare.jsonl", None),
    ("natural_candidates_batch2_gpu_bare.jsonl", None),
    # Final pre-paper validation batch (50 more genuinely-new natural cases,
    # disjoint from all of the above) -- included so the taxonomy reflects
    # every natural GPU generation ever produced in this project, not just
    # the batches that existed as of the prior audit pass. Text is shared
    # between the A and B arms (same generation), so only one needs listing;
    # the seen_texts dedup below would skip the other anyway.
    ("final_gpu_validation_A.jsonl", None),
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


def main() -> int:
    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    config_v1 = dict(config)
    config_v1["use_evidence_v1"] = True
    exact_index, all_usable = load_usable_evidence_from_config(config_v1, repo_root)
    print(f"v0+v1 usable records: {len(all_usable)}", flush=True)

    n_claims = 0
    n_matched = 0
    n_no_citation = 0
    rows = []
    seen_texts = set()

    for fname, doc_id, text in iter_generated_texts(outputs):
        if text in seen_texts:
            continue
        seen_texts.add(text)
        for claim in claim_parser.extract_claims(text):
            n_claims += 1
            cit = claim.citation_extracted
            if cit is None:
                n_no_citation += 1
                continue
            result = match_evidence(cit, exact_index, all_usable, fuzzy_threshold)
            if result.matched:
                n_matched += 1
                continue

            row = {
                "source": fname, "document_id": doc_id, "claim_id": claim.claim_id,
                "citation": cit.as_dict(),
                "claim_text": claim.claim_text[:200],
            }

            if not cit.act_norm:
                row["bucket"] = "unresolved_act"
                rows.append(row)
                continue

            same_number = [e for e in all_usable
                           if e.provision_type == cit.provision_type
                           and e.provision_number == cit.provision_number]
            if not same_number:
                row["bucket"] = "genuinely_absent_no_such_provision_any_act"
                rows.append(row)
                continue

            claim_words = act_significant_words(cit.act_norm)
            best_overlap = 0.0
            best_ev = None
            for ev in same_number:
                ov = _token_overlap(claim_words, act_significant_words(ev.act_norm))
                if ov > best_overlap:
                    best_overlap = ov
                    best_ev = ev

            row["best_overlap"] = round(best_overlap, 3)
            row["best_overlap_candidate_act"] = best_ev.act_norm if best_ev else None
            row["best_overlap_candidate_key"] = best_ev.dataset_citation_key if best_ev else None

            if 0.5 <= best_overlap < fuzzy_threshold:
                row["bucket"] = "parser_or_matcher_defect_candidate"
            else:
                row["bucket"] = "genuinely_absent_wrong_act_or_edition"
            rows.append(row)

    bucket_counts = Counter(r["bucket"] for r in rows)
    print(f"\nDistinct generated texts scanned: {len(seen_texts)}")
    print(f"Total claims: {n_claims}")
    print(f"Matched: {n_matched} ({100*n_matched/n_claims:.1f}%)")
    print(f"No citation at all: {n_no_citation}")
    print(f"Still NO_EVIDENCE (has citation): {len(rows)}")
    print(f"Taxonomy: {dict(bucket_counts)}")

    defect_candidates = [r for r in rows if r["bucket"] == "parser_or_matcher_defect_candidate"]
    if defect_candidates:
        print(f"\n=== {len(defect_candidates)} parser/matcher defect CANDIDATES (need manual review) ===")
        for r in defect_candidates:
            c = r["citation"]
            print(f"  [{r['source']} {r['document_id']} {r['claim_id']}] "
                  f"{c['provision_type']} {c['provision_number']} "
                  f"claim_act={c['act_raw']!r} (norm={c['act_norm']!r}) "
                  f"vs corpus_act={r['best_overlap_candidate_act']!r} "
                  f"overlap={r['best_overlap']}")

    out = {
        "n_claims": n_claims, "n_matched": n_matched, "n_no_citation": n_no_citation,
        "n_no_evidence_with_citation": len(rows),
        "taxonomy": dict(bucket_counts),
        "rows": rows,
    }
    (outputs / "no_evidence_taxonomy_v3.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {outputs / 'no_evidence_taxonomy_v3.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
