#!/usr/bin/env python
"""
Full-pipeline demo: a claim that reaches the NOT_ENOUGH_INFORMATION (NEI)
final verdict -- specifically a GENUINE high-confidence neutral verdict,
not a low-confidence downgrade.

Document: 2011_625, source research/prototype/outputs/final_gpu_validation_B.jsonl.
Target citation: Section 149, Indian Penal Code, 1860.

Two different things both produce a NOT_ENOUGH_INFORMATION verdict, and
they are NOT the same, downstream:
  - A genuine high-confidence "neutral" NLI prediction (sub_reason is None)
    -- the model is confident the premise neither entails nor contradicts
    the hypothesis. This is a legitimate, final NEI outcome on its own; it
    does NOT trigger correction.
  - A LOW-CONFIDENCE downgrade (sub_reason == "low_confidence") -- the raw
    argmax label (of any kind) scored below the confidence threshold, so
    the verdict is downgraded to NEI as a safety measure. THIS case DOES
    trigger a Mode-C correction attempt.
This demo verifies, live, which of the two this specific claim actually is.

What is LIVE here (real code, executed now, CPU-only):
  - claim extraction, evidence retrieval, NLI verification, orchestration
    via src.pipeline.run_case() (mode "B") -- identical technique to
    entailed_outcome.py / contradicted_outcome.py, see those files' longer
    docstrings for the full LIVE/REPLAYED breakdown.

What is REPLAYED (not re-run): generation, substituted with the real,
already-committed generated text via ph.FakeGenerator.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/07_full_pipeline/nei_outcome.py
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
TARGET_PROVISION_NUMBER = "149"
EXPECTED_VERDICT = "NOT_ENOUGH_INFORMATION"


def main() -> int:
    fmt.section("FULL PIPELINE OUTCOME 3/4 -- NOT_ENOUGH_INFORMATION (genuine, not a downgrade)")

    cfg = ph.load_config()
    print("\nLoading real production evidence pool (real data, no model)...")
    exact_index, all_usable = ph.load_evidence_pool(cfg)
    fmt.kv("Usable evidence records", len(all_usable))
    fmt.kv("Confidence threshold", cfg["verification"]["confidence_threshold"])

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

    try:
        target = ph.find_claim_by_provision(record["claims"], TARGET_PROVISION_NUMBER)
    except StopIteration as exc:
        print(f"\n  ERROR: {exc}")
        return 1

    fmt.subsection(f"Target claim [{target['claim_id']}] -- Section {TARGET_PROVISION_NUMBER} IPC")
    fmt.kv("Claim text", fmt.trunc(target["claim_text"], 200))
    fmt.kv("Evidence ID", target["evidence_id"])
    fmt.kv("Evidence text", fmt.trunc(target["evidence_text"], 200))
    fmt.kv("Verdict", target["verdict"])
    conf = target["confidence"]
    conf_str = f"{conf:.4f}" if isinstance(conf, float) else conf
    fmt.kv("Confidence", conf_str)
    fmt.kv("sub_reason", target["sub_reason"])
    print(f"\n  {fmt.NLI_DISCLAIMER}")

    ok = target["verdict"] == EXPECTED_VERDICT
    print(f"\n  Observed verdict: {target['verdict']!r} (expected {EXPECTED_VERDICT!r}) -- "
          f"{'MATCH' if ok else 'DID NOT MATCH'}")

    is_downgrade = target["sub_reason"] == "low_confidence"
    kind = "a LOW-CONFIDENCE DOWNGRADE" if is_downgrade else "a GENUINE high-confidence neutral verdict"
    print(f"\n  This is {kind} "
          f"(confidence {conf_str} {'<' if is_downgrade else '>='} threshold "
          f"{cfg['verification']['confidence_threshold']}).")

    triggers = pipeline._should_trigger_correction(target)
    print(f"\n  Would this verdict trigger a Mode-C correction attempt? {triggers} "
          f"({'low-confidence NEI triggers correction' if is_downgrade else 'a genuine high-confidence NEI does NOT trigger correction'}"
          " -- src.pipeline._should_trigger_correction.)")
    fmt.mode_b_outcome_line(
        target["verdict"],
        note="a low-confidence downgrade WOULD trigger correction" if is_downgrade
        else "a genuine high-confidence neutral verdict never triggers correction",
    )
    fmt.kv("final_field.source", record["final_field"]["source"])

    fmt.section("Done. No file under research/prototype/outputs/ or research/data/ was modified.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
