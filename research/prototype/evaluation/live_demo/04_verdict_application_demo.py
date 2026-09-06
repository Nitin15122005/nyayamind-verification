#!/usr/bin/env python
"""
Demo D — Verdict Application.

Shows the real `src.pipeline.apply_verification()` orchestration function
applied to a WHOLE document's claims at once, so the ROUTING behavior is
visible: which claims are sent to the real NLI verifier at all, and which
are correctly skipped because they never resolved to any evidence.

This is deliberately distinct from `03_nli_verification_demo.py`, which
shows the verifier called in isolation on hand-picked hypotheses. This
demo's point is the batch ROUTING/application step itself — the real
`apply_verification()` function, not a per-claim loop written here.

What is LIVE (real code, real model, executed now):
  - claim extraction        -- src.claim_parser.extract_claims()
  - evidence retrieval      -- src.evidence_matcher.match_evidence() against
                                the real production evidence pool
  - verdict application     -- src.pipeline.apply_verification(), the real,
                                unmodified orchestration function, calling
                                the real DeBERTa-v3-base-mnli-fever-anli
                                verifier (CPU/GPU auto-detected, no GPU
                                required for this small model)
  - correction-trigger check -- src.pipeline._should_trigger_correction()

What is REPLAYED (already-committed, not re-run):
  - generation — the input text is the real Qwen2.5-7B-Instruct output for
    document_id 2011_625, read verbatim from
    research/prototype/outputs/final_gpu_validation_B.jsonl. Re-running
    generation requires a GPU and is unnecessary for this demo.

This document was chosen because its real generated text genuinely
contains BOTH routing paths in one field: five claims resolve to real
evidence (Sections 302, 304 [cited in two separate sentences each], and
149) and one claim (Section 336) has no evidence in the 136-record
production pool at all — a real, not staged, no-evidence claim.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/04_verdict_application_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import formatting as fmt  # noqa: E402
from common import pipeline_helpers as ph  # noqa: E402

from src import claim_parser, pipeline  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402

DOCUMENT_ID = "2011_625"
SOURCE_FILE = "research/prototype/outputs/final_gpu_validation_B.jsonl"


def build_claim_records(generated_text: str, exact_index, all_usable, fuzzy_threshold: float) -> list[dict]:
    """Live parse + live evidence match, producing the exact claim-record
    dict shape src.pipeline.apply_verification()/_premise_for_claim()
    expect — the same shape research/prototype/evaluation/live_demo/run_demo.py's
    own stage [3] builds (that file is not modified by this one)."""
    claims = claim_parser.extract_claims(generated_text)
    claim_records = []
    for claim in claims:
        match = match_evidence(claim.citation_extracted, exact_index, all_usable, fuzzy_threshold)
        claim_records.append({
            "claim_id": claim.claim_id,
            "claim_text": claim.claim_text,
            "assertion_text": claim.assertion_text,
            "assertion_spans": list(claim.assertion_spans),
            "citation_extracted": claim.citation_extracted.as_dict() if claim.citation_extracted else None,
            "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
            "evidence_text": match.evidence.canonical_text if match.matched else None,
            "_evidence_provision": {
                "provision_type": match.evidence.provision_type,
                "provision_number": match.evidence.provision_number,
                "act": match.evidence.act,
            } if match.matched else None,
            "evidence_match_method": match.match_method,
            "verdict": None, "confidence": None, "sub_reason": None, "verifier_model": None,
        })
        if not match.matched:
            claim_records[-1]["verdict"] = "NO_EVIDENCE"
    return claim_records


def main() -> int:
    fmt.section("DEMO D — Verdict Application (evidence/no-evidence routing, real src.pipeline.apply_verification)")

    cfg = ph.load_config()
    fmt.kv("premise_framing (production config)", cfg["verification"]["premise_framing"])
    fmt.kv("confidence_threshold (production config)", cfg["verification"]["confidence_threshold"])

    print("\nLoading production evidence pool (real data, no model)...")
    exact_index, all_usable = ph.load_evidence_pool(cfg)
    fmt.kv("usable evidence records loaded", len(all_usable))

    verifier = ph.load_verifier(cfg)
    fuzzy_threshold = cfg["evidence_matching"]["fuzzy_token_overlap_threshold"]

    fmt.stage(1, f"Generation (Qwen2.5-7B-Instruct) — document_id {DOCUMENT_ID}", tag=fmt.REPLAYED)
    fmt.kv("Source", SOURCE_FILE)
    rec = ph.load_record(SOURCE_FILE, DOCUMENT_ID)
    generated_text = rec["generated_field"]["text"]
    print(f"    {fmt.trunc(generated_text, 300)}")

    fmt.stage(2, "Claim extraction + evidence retrieval", tag=fmt.LIVE)
    claim_records = build_claim_records(generated_text, exact_index, all_usable, fuzzy_threshold)
    fmt.claim_overview(claim_records)

    fmt.stage(3, "Routing preview (BEFORE apply_verification runs)", tag=fmt.LIVE)
    will_verify = [c["claim_id"] for c in claim_records if c["evidence_text"] is not None]
    skipped = [c["claim_id"] for c in claim_records if c["evidence_text"] is None]
    print("  Routing is decided purely by whether a claim resolved to evidence in stage 2 —")
    print("  apply_verification() itself never re-checks evidence, it only branches on evidence_text:")
    fmt.bullet(f"-> WILL be routed to the real verifier: {', '.join(will_verify) or '(none)'}")
    fmt.bullet(f"-> SKIPPED, no evidence to check against (stays NO_EVIDENCE, verifier never called): "
               f"{', '.join(skipped) or '(none)'}")

    fmt.stage(4, "apply_verification() — real orchestration call, real DeBERTa inference", tag=fmt.LIVE)
    baseline = {"document_id": rec["document_id"], "claims": claim_records}
    premise_framing = pipeline.resolve_premise_framing(cfg)
    pipeline.apply_verification(baseline, verifier, premise_framing=premise_framing)
    print(f"  apply_verification(baseline, verifier, premise_framing={premise_framing!r}) returned.")

    fmt.stage(5, "Result — claims now carry real verdicts (skipped claim(s) untouched)", tag=fmt.LIVE)
    fmt.claim_overview(claim_records)

    print("\n  Routing proof — the skipped claim(s) were genuinely never sent to the verifier:")
    for c in claim_records:
        if c["claim_id"] in skipped:
            proven = c["confidence"] is None and c["verifier_model"] is None and c["verdict"] == "NO_EVIDENCE"
            fmt.bullet(
                f"[{c['claim_id']}] confidence={c['confidence']!r}, verifier_model={c['verifier_model']!r}, "
                f"verdict={c['verdict']!r}  -- {'CONFIRMED never called' if proven else 'UNEXPECTED'}"
            )
    for c in claim_records:
        if c["claim_id"] in will_verify:
            fmt.bullet(
                f"[{c['claim_id']}] verifier_model={c['verifier_model']!r} "
                f"(real model id recorded -- proves the real verifier was actually invoked)"
            )
            break

    fmt.stage(6, "Correction-trigger policy (src.pipeline._should_trigger_correction)", tag=fmt.LIVE)
    print("  Policy: CONTRADICTED always triggers; NOT_ENOUGH_INFORMATION triggers only when")
    print("  sub_reason == 'low_confidence' (a genuine high-confidence neutral verdict does NOT")
    print("  trigger); NO_EVIDENCE never triggers.")
    triggered = [c["claim_id"] for c in claim_records if pipeline._should_trigger_correction(c)]
    if triggered:
        fmt.bullet(f"Claim(s) that WOULD trigger a Mode-C correction attempt: {', '.join(triggered)}")
    else:
        fmt.bullet("No claim in this document triggers correction under this policy — "
                   "every verdict here is either a genuine (non-low-confidence) neutral, "
                   "ENTAILED, or NO_EVIDENCE.")

    print(f"\n{fmt.NLI_DISCLAIMER}")
    fmt.section("Demo D complete. No file under research/prototype/outputs/ or research/data/ was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
