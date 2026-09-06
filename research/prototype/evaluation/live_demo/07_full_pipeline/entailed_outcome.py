#!/usr/bin/env python
"""
Full-pipeline demo: a claim that reaches the ENTAILED final verdict.

Document: 2003_760, source research/prototype/outputs/final_gpu_validation_B.jsonl.
Target citation: Section 34, Indian Penal Code, 1860 -- this document cites
Section 34 in TWO different sentences (claims c2 and c4); only c4 (the
standalone "Section 34 addresses criminal liability..." sentence) actually
reaches ENTAILED -- c2 (from the bundled "Sections 302 and 34" sentence)
comes back NOT_ENOUGH_INFORMATION. Selection below is therefore by BOTH
provision number AND live verdict, not by provision number alone (the same
disambiguation ../07_full_pipeline/contradicted_outcome.py needs for its
own repeated citation).

What is LIVE here (real code, executed now, CPU-only):
  - claim extraction        -- src.claim_parser.extract_claims()
  - evidence retrieval      -- src.evidence_matcher.match_evidence(), real
                                136-record production pool
  - NLI verification        -- src.verifier.NLIVerifier, real DeBERTa-v3-
                                base-mnli-fever-anli inference
  - orchestration           -- src.pipeline.run_case(), the REAL, unmodified
                                pipeline entry point (mode "B": generation +
                                verification, no correction attempt)

What is REPLAYED (not re-run): generation. Qwen2.5-7B-Instruct text
generation requires a GPU; instead, the real, already-committed generated
text for this document is read from disk and handed to run_case() via
ph.FakeGenerator, which substitutes ONLY that one GPU-only call.

SCOPING NOTE: this demo runs Mode "B" (verification only) so the
ENTAILED/CONTRADICTED/NEI/NO_EVIDENCE verdict itself is isolated cleanly.
A CONTRADICTED or low-confidence-NEI verdict would, in a real Mode "C" run,
additionally trigger a correction attempt -- that full correction +
re-verification + ship/reject mechanism is demonstrated separately (and in
more depth) in ../06_correction_reverification_demo.py; it is not repeated
here. This claim's own verdict (ENTAILED) never triggers correction in any
mode, by design (src.pipeline._should_trigger_correction only fires for
CONTRADICTED or low-confidence NEI).

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/07_full_pipeline/entailed_outcome.py
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

DOCUMENT_ID = "2003_760"
SOURCE = "research/prototype/outputs/final_gpu_validation_B.jsonl"
TARGET_PROVISION_NUMBER = "34"
EXPECTED_VERDICT = "ENTAILED"


def _find_by_provision_and_verdict(claims: list[dict], provision_number: str, verdict: str):
    for c in claims:
        citation = c.get("citation_extracted")
        if citation and citation.get("provision_number") == provision_number and c.get("verdict") == verdict:
            return c
    return None


def main() -> int:
    fmt.section("FULL PIPELINE OUTCOME 1/4 -- ENTAILED")

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

    fmt.stage("2-4", "Claim extraction + evidence retrieval + NLI verification "
                      "(src.pipeline.run_case, mode B)", tag=fmt.LIVE)
    record = pipeline.run_case(
        case, "B", generator, verifier, corrector=None,
        exact_index=exact_index, all_usable=all_usable, config=cfg,
    )

    fmt.claim_overview(record["claims"])

    print(f"\n  Note: Section {TARGET_PROVISION_NUMBER} IPC is cited twice in this document "
          "(two different sentences) -- selecting the one that actually reaches ENTAILED, "
          "not just the first Section-34 claim found.")
    target = _find_by_provision_and_verdict(record["claims"], TARGET_PROVISION_NUMBER, EXPECTED_VERDICT)
    if target is None:
        print(f"\n  No claim with provision_number={TARGET_PROVISION_NUMBER!r} and "
              f"verdict={EXPECTED_VERDICT!r} was found in this live run. "
              "Reporting actual observed claims instead of forcing a match:")
        for c in record["claims"]:
            citation = c.get("citation_extracted")
            if citation and citation.get("provision_number") == TARGET_PROVISION_NUMBER:
                fmt.kv(f"  claim {c['claim_id']}", f"verdict={c['verdict']} confidence={c['confidence']}")
        return 1

    fmt.subsection(f"Target claim [{target['claim_id']}] -- Section {TARGET_PROVISION_NUMBER} IPC")
    fmt.kv("Claim text", fmt.trunc(target["claim_text"], 200))
    fmt.kv("Evidence ID", target["evidence_id"])
    fmt.kv("Evidence text", fmt.trunc(target["evidence_text"], 200))
    fmt.kv("Verdict", target["verdict"])
    conf = target["confidence"]
    fmt.kv("Confidence", f"{conf:.4f}" if isinstance(conf, float) else conf)
    fmt.kv("sub_reason", target["sub_reason"])
    print(f"\n  {fmt.NLI_DISCLAIMER}")

    ok = target["verdict"] == EXPECTED_VERDICT
    print(f"\n  Observed verdict: {target['verdict']!r} (expected {EXPECTED_VERDICT!r}) -- "
          f"{'MATCH' if ok else 'DID NOT MATCH -- reporting actual observed result, not forcing it'}")

    triggers = pipeline._should_trigger_correction(target)
    print(f"\n  Would this verdict trigger a Mode-C correction attempt? {triggers} "
          "(ENTAILED never triggers correction -- src.pipeline._should_trigger_correction "
          "only fires for CONTRADICTED or low-confidence NEI).")
    fmt.mode_b_outcome_line(
        target["verdict"],
        note="generation was already accurate for this claim, so a Mode-C run would not "
             "have attempted any correction here either",
    )
    fmt.kv("final_field.source", record["final_field"]["source"])

    fmt.section("Done. No file under research/prototype/outputs/ or research/data/ was modified.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
