#!/usr/bin/env python
"""
Evidence Retrieval demo (task category B).

Shows: query claim -> evidence pool -> retrieved evidence -> matching
method -> exact-match and NO_EVIDENCE cases, using the REAL production
evidence pool and the REAL, unmodified src.evidence_matcher.match_evidence().

What is LIVE here (real code, executed now, CPU-only, no model):
  - Loading the real 136-record production evidence pool
    (src.data_loader.load_usable_evidence_from_config).
  - src.evidence_matcher.match_evidence() calls for the exact-match and
    NO_EVIDENCE cases below.
  - src.claim_parser.extract_claims() on a real, already-committed
    generated field, to derive the NO_EVIDENCE citation from real text
    rather than hand-typing it.

What is STATIC here (a real, already-committed record read verbatim from
disk, not recomputed against the real production pool):
  - The "same provision number, three different Acts" illustration, which
    is read from research/prototype/evaluation/components/02_evidence_retrieval/
    demo_examples.json. That file's own result was produced against
    tests/test_adversarial_citations.py's own small scripted evidence pool
    (built specifically to exercise this disambiguation), not this
    project's real 136-record production pool -- shown here read-only, not
    recomputed, and labeled accordingly.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/02_evidence_retrieval_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import pipeline_helpers as ph  # noqa: E402
from common import formatting as fmt  # noqa: E402

from src import claim_parser  # noqa: E402
from src.claim_parser import ExtractedCitation  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402

DEMO_EXAMPLES_PATH = (
    ph.EVALUATION_ROOT / "components" / "02_evidence_retrieval" / "demo_examples.json"
)


def main() -> int:
    fmt.section("EVIDENCE RETRIEVAL — query claim -> evidence pool -> retrieved evidence")

    cfg = ph.load_config()
    fmt.kv("use_evidence_v1", cfg["use_evidence_v1"])
    fmt.kv("fuzzy_token_overlap_threshold", cfg["evidence_matching"]["fuzzy_token_overlap_threshold"])

    print("\nLoading the real production evidence pool (no model, pure data load)...")
    exact_index, all_usable = ph.load_evidence_pool(cfg)
    print(f"  Loaded {len(all_usable)} usable evidence records "
          f"(expect 136 = v0's 59-usable + v1's additive supplement).")

    # ------------------------------------------------------------------
    # Case 1 — EXACT match (LIVE)
    # ------------------------------------------------------------------
    fmt.stage(1, "Exact match — Section 302, Indian Penal Code, 1860", tag=fmt.LIVE)
    citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="the Indian Penal Code, 1860", act_norm="indian penal code 1860",
    )
    fmt.kv("Query citation", f"{citation.provision_type} {citation.provision_number} "
                              f"of {citation.act_raw}")
    match = match_evidence(citation, exact_index, all_usable,
                            cfg["evidence_matching"]["fuzzy_token_overlap_threshold"])
    fmt.kv("matched", match.matched)
    fmt.kv("match_method", match.match_method)
    fmt.kv("evidence_id", match.evidence.dataset_citation_key if match.matched else None)
    fmt.kv("evidence_text", fmt.trunc(match.evidence.canonical_text if match.matched else None, 160))

    demo_examples = json.loads(DEMO_EXAMPLES_PATH.read_text(encoding="utf-8"))
    case_a = demo_examples["case_a_real_production_pool"]
    ok = (
        match.matched
        and match.match_method == case_a["actual_match_method"]
        and match.evidence.dataset_citation_key == case_a["actual_evidence_id"]
    )
    print(f"\n  Self-check vs. components/02_evidence_retrieval/demo_examples.json"
          f" (case_a_real_production_pool): {'PASS' if ok else 'MISMATCH'}")
    fmt.kv("  recorded evidence_id", case_a["actual_evidence_id"], indent=4)
    fmt.kv("  recorded match_method", case_a["actual_match_method"], indent=4)

    # ------------------------------------------------------------------
    # Case 2 — NO_EVIDENCE (LIVE)
    # ------------------------------------------------------------------
    fmt.stage(2, "NO_EVIDENCE — Section 336, not in the ~140-provision corpus", tag=fmt.LIVE)
    rec = ph.load_record("research/prototype/outputs/final_gpu_validation_B.jsonl", "2011_625")
    text = rec["generated_field"]["text"]
    fmt.kv("Source document", "2011_625 (research/prototype/outputs/final_gpu_validation_B.jsonl)")
    claims = claim_parser.extract_claims(text)
    target = ph.find_claim_by_provision(
        [{"claim_id": c.claim_id, "claim_text": c.claim_text,
          "citation_extracted": c.citation_extracted.as_dict() if c.citation_extracted else None}
         for c in claims],
        provision_number="336",
    )
    citation_336 = next(c.citation_extracted for c in claims if c.claim_id == target["claim_id"])
    fmt.kv("Query claim", fmt.trunc(target["claim_text"], 160))
    fmt.kv("Query citation", f"{citation_336.provision_type} {citation_336.provision_number} "
                              f"of {citation_336.act_raw}")
    match2 = match_evidence(citation_336, exact_index, all_usable,
                             cfg["evidence_matching"]["fuzzy_token_overlap_threshold"])
    fmt.kv("matched", match2.matched)
    fmt.kv("match_method", match2.match_method)
    fmt.kv("evidence", match2.evidence)
    print("\n  NO_EVIDENCE means Section 336 IPC is simply not one of the ~140 provisions in this")
    print("  project's canonical evidence corpus (capped by design to the most-cited provisions in")
    print("  the source case corpus) -- it does NOT mean the claim is legally wrong. The system")
    print("  correctly declines to guess rather than verifying against a premise it doesn't have.")

    # ------------------------------------------------------------------
    # Case 3 — same provision number, three different Acts (STATIC)
    # ------------------------------------------------------------------
    fmt.stage(3, "Same provision number under three different Acts — disambiguation", tag=fmt.STATIC)
    case_b = demo_examples["case_b_same_number_three_acts"]
    print(f"  Source: components/02_evidence_retrieval/demo_examples.json (case_b_same_number_three_acts)")
    print(f"  {case_b['source_of_input']}")
    print("  NOTE: this uses tests/test_adversarial_citations.py's own small scripted evidence")
    print("  pool (built specifically to exercise this 3-way disambiguation), NOT the real")
    print("  136-record production pool loaded above -- shown here read-only, not recomputed.")
    for r in case_b["results"]:
        fmt.kv(f"  Section 34 of {r['act_raw']}", f"matched={r['matched']} "
               f"method={r['match_method']} text={fmt.trunc(r['matched_text'], 60)}", indent=4)
    print(f"\n  Expected behavior: {case_b['expected_behavior']}")

    fmt.section("Summary")
    print("  1. Exact key match (provision_type, provision_number, subsection, act_norm) is tried first.")
    print("  2. A subsection-agnostic exact fallback is tried next (e.g. a claim citing")
    print("     'Section 25F(1)' can still find a base 'Section 25F' evidence record).")
    print("  3. Fuzzy fallback (same provision_type + number, act-name token overlap >= "
          f"{cfg['evidence_matching']['fuzzy_token_overlap_threshold']}) is tried only if exact fails.")
    print("  4. NO_EVIDENCE is a first-class, expected outcome -- not an error -- for any provision")
    print("     outside the corpus; the verifier is never called for it (see demo 04).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
