#!/usr/bin/env python
"""
Full-pipeline demo: a claim that reaches the NO_EVIDENCE final outcome.

Document: 2011_625 (same document as nei_outcome.py, a different claim),
source research/prototype/outputs/final_gpu_validation_B.jsonl.
Target citation: Section 336, Indian Penal Code, 1860.

NO_EVIDENCE means "this provision is not one of the ~140 provisions in this
project's canonical evidence corpus" -- it is NOT a statement that the
underlying legal claim is wrong. The system makes no assertion whatsoever
about a claim it has no evidence to check. See
research/prototype/evaluation/examples/case_05_no_evidence.md for the
original curated write-up of this exact claim.

What is LIVE here (real code, executed now, CPU-only):
  - claim extraction        -- src.claim_parser.extract_claims()
  - evidence retrieval      -- src.evidence_matcher.match_evidence(), real
                                136-record production pool -- genuinely
                                returns "not found" for this citation, live
  - orchestration           -- src.pipeline.run_case(), mode "B"
  - NLI verification is deliberately NEVER invoked for this claim -- by
    design, a claim with no evidence has no premise to verify against (see
    src.pipeline.apply_verification's own docstring: "Claims with no
    evidence keep their NO_EVIDENCE verdict untouched -- the verifier is
    never called for them"). This demo verifies that live: confidence and
    verifier_model both come back None for this claim, not fabricated.

What is REPLAYED (not re-run): generation, substituted with the real,
already-committed generated text via ph.FakeGenerator.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/07_full_pipeline/no_evidence_outcome.py
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import formatting as fmt  # noqa: E402
from common import pipeline_helpers as ph  # noqa: E402

from src import pipeline  # noqa: E402
from src.data_loader import Case  # noqa: E402

DOCUMENT_ID = "2011_625"
SOURCE = "research/prototype/outputs/final_gpu_validation_B.jsonl"
TARGET_PROVISION_NUMBER = "336"
EXPECTED_VERDICT = "NO_EVIDENCE"


def main() -> int:
    fmt.section("FULL PIPELINE OUTCOME 4/4 -- NO_EVIDENCE")

    cfg = ph.load_config()
    print("\nLoading real production evidence pool (real data, no model)...")
    exact_index, all_usable = ph.load_evidence_pool(cfg)
    fmt.kv("Usable evidence records", len(all_usable))

    verifier = ph.load_verifier(cfg)

    fmt.stage(1, "Generation (Qwen2.5-7B-Instruct, 4-bit, greedy)", tag=fmt.REPLAYED)
    rec = ph.load_record(SOURCE, DOCUMENT_ID)
    fmt.kv("Source", SOURCE)
    fmt.kv("Document ID", DOCUMENT_ID)
    print(f"    Generated statutory-grounding text:\n      {fmt.trunc(rec['generated_field']['text'], 380)}")

    case = Case(document_id=rec["document_id"], case_text=rec["case_text"], raw_citation_keys=[])
    generator = ph.FakeGenerator(rec["generated_field"]["text"], rec["generated_field"]["model"])

    fmt.stage("2-4", "Claim extraction + evidence retrieval (real 'not found') + "
                      "verification routing (src.pipeline.run_case, mode B)", tag=fmt.LIVE)
    record = pipeline.run_case(
        case, "B", generator, verifier, corrector=None,
        exact_index=exact_index, all_usable=all_usable, config=cfg,
    )

    fmt.claim_overview(record["claims"])

    try:
        target = ph.find_claim_by_provision(record["claims"], TARGET_PROVISION_NUMBER, matched=False)
    except StopIteration as exc:
        print(f"\n  ERROR: {exc}")
        return 1

    fmt.subsection(f"Target claim [{target['claim_id']}] -- Section {TARGET_PROVISION_NUMBER} IPC")
    fmt.kv("Claim text", fmt.trunc(target["claim_text"], 220))
    fmt.kv("Evidence ID", target["evidence_id"])
    fmt.kv("Evidence text", target["evidence_text"])
    fmt.kv("Evidence match method", target["evidence_match_method"])
    fmt.kv("Verdict", target["verdict"])
    fmt.kv("Confidence", target["confidence"])
    fmt.kv("verifier_model", target["verifier_model"])

    checks = {
        "verdict == NO_EVIDENCE": target["verdict"] == EXPECTED_VERDICT,
        "evidence_id is None": target["evidence_id"] is None,
        "confidence is None (verifier never called)": target["confidence"] is None,
        "verifier_model is None (verifier never called)": target["verifier_model"] is None,
    }
    print("\n  Live checks:")
    ok = True
    for label, passed in checks.items():
        print(f"    [{'OK' if passed else 'FAIL'}] {label}")
        ok = ok and passed

    print("\n  Section 336 IPC is simply not one of the ~140 provisions in this project's "
          "canonical evidence pool (top-cited-provisions corpus, by design -- see "
          "research/data/evidence/README.md). This says nothing about whether the claim's "
          "underlying legal content is correct or incorrect.")

    triggers = pipeline._should_trigger_correction(target) if target["verdict"] != "NO_EVIDENCE" else False
    print(f"\n  Would this verdict trigger a Mode-C correction attempt? False "
          "(NO_EVIDENCE never triggers correction, in any mode, by construction -- "
          "callers only ever evaluate _should_trigger_correction for claims that already "
          "have evidence).")
    fmt.mode_b_outcome_line(
        target["verdict"],
        note="the verifier is never called for a NO_EVIDENCE claim regardless of mode",
    )
    fmt.kv("final_field.source", record["final_field"]["source"])

    fmt.section("Done. No file under research/prototype/outputs/ or research/data/ was modified.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
