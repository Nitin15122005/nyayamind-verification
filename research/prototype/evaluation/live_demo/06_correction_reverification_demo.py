#!/usr/bin/env python
"""
Demo F — Correction + Re-verification.

Runs the REAL, unmodified `src.pipeline.run_case()` orchestrator end to end,
TWICE, in Mode C (generation + verification + selective correction):

  RUN A — a correction that is safe and SHIPS.
  RUN B — a correction that damages an unrelated (unflagged) sentence and is
          REJECTED by the real programmatic scope gate.

What is genuinely LIVE (real code, real model, executed now):
  - claim extraction        -- src.claim_parser.extract_claims()
  - evidence retrieval      -- src.evidence_matcher.match_evidence() against
                                the real production evidence pool
  - NLI verification        -- src.verifier.NLIVerifier, real DeBERTa-v3-
                                base-mnli-fever-anli inference (CPU or GPU,
                                auto-detected -- see common/pipeline_helpers.py)
  - selective correction orchestration -- src.pipeline.apply_selective_correction()
  - the scope-violation safety gate    -- src.pipeline._scope_violation()
  - re-verification of the (candidate) corrected sentence -- the same real
    verifier, called again

What is SCRIPTED (substituted, not fabricated):
  - text GENERATION and the CORRECTION rewrite itself both require the real
    7B Qwen2.5-Instruct model on a GPU. This demo substitutes them with
    `common.pipeline_helpers.FakeGenerator` / `ScriptedCorrector` -- the
    exact same substitution pattern used by
    `research/prototype/tests/test_correction_path_real_integration.py`
    (not reinvented here). Every piece of text they supply is copied
    VERBATIM from that real test file, which itself sources the flagged
    sentence from a real generated field in
    `research/prototype/outputs/run_C_targeted_1994_495.jsonl`
    (document_id `1994_495`) and constructs the deliberately-corrupted /
    corrected / altered variants documented inline below. Nothing here is
    invented text; only the GPU call that would have produced it is
    substituted, exactly as the real test does, so the REAL pipeline logic
    (correction trigger, scope gate, re-verification, shipping decision)
    can be exercised live on a machine with no GPU.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/06_correction_reverification_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import pipeline_helpers as ph  # noqa: E402
from common import formatting as fmt  # noqa: E402

from src import pipeline  # noqa: E402
from src.data_loader import Case  # noqa: E402

# ---------------------------------------------------------------------------
# Real fixture text, copied VERBATIM from
# research/prototype/tests/test_correction_path_real_integration.py, itself
# sourced from a real generated field in
# research/prototype/outputs/run_C_targeted_1994_495.jsonl (document_id
# "1994_495"): sentence 2 is that record's real, unflagged Section-148
# sentence; sentence 1 is a deliberately corrupted version of that record's
# real Section-302 assertion (claims murder is punishable "only by a fine",
# directly contradicting the real canonical evidence text).
# ---------------------------------------------------------------------------
REAL_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with the unlawful assembly, which may be "
    "relevant if the prosecution can show that the accused acted as part of an "
    "unlawful assembly."
)
CORRUPTED_FLAGGED_SENTENCE = (
    "The offense of murder under Section 302 of the Indian Penal Code, 1860 is "
    "punishable only by a fine and never by death or imprisonment."
)
CORRECTED_FLAGGED_SENTENCE = (
    "Whoever commits murder under Section 302 of the Indian Penal Code, 1860 "
    "shall be punished with death, or imprisonment for life, and shall also be "
    "liable to fine."
)
ALTERED_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with theft, which may be relevant if the "
    "prosecution can show that the accused acted alone."
)

CORRUPTED_TEXT = CORRUPTED_FLAGGED_SENTENCE + " " + REAL_UNFLAGGED_SENTENCE
GOOD_CORRECTED_TEXT = CORRECTED_FLAGGED_SENTENCE + " " + REAL_UNFLAGGED_SENTENCE
BAD_CORRECTED_TEXT = CORRECTED_FLAGGED_SENTENCE + " " + ALTERED_UNFLAGGED_SENTENCE


def _run_one(cfg, exact_index, all_usable, verifier, case, corrected_text: str, run_label: str) -> dict:
    fmt.section(f"RUN {run_label}")

    fmt.stage(1, "Generation (Qwen2.5-7B-Instruct)", tag=fmt.SCRIPTED)
    print("    FakeGenerator supplies the real corrupted field text directly"
          " (no GPU call made).")
    fmt.kv("Corrupted field text", fmt.trunc(CORRUPTED_TEXT))

    generator = ph.FakeGenerator(CORRUPTED_TEXT, cfg["generation"]["model_id"])
    corrector = ph.ScriptedCorrector(corrected_text, cfg["generation"]["model_id"])

    fmt.stage(2, "Claim extraction, evidence retrieval, NLI verification", tag=fmt.LIVE)
    print("    (src.claim_parser + src.evidence_matcher + src.verifier, called by"
          " the real src.pipeline.run_case())")

    record = pipeline.run_case(
        case, "C", generator, verifier, corrector, exact_index, all_usable, cfg
    )

    flagged = ph.find_claim_by_provision(record["claims"], "302")
    print(f"    Original claim [{flagged['claim_id']}]: \"{fmt.trunc(flagged['claim_text'], 140)}\"")
    fmt.kv("Verdict (live)", f"{flagged['verdict']} (confidence {flagged['confidence']:.4f})")
    fmt.kv("Evidence used", flagged["evidence_id"])

    fmt.stage(3, "Selective correction (rewrite of the flagged sentence)", tag=fmt.SCRIPTED)
    print("    ScriptedCorrector supplies this candidate correction directly"
          " (no GPU call made).")
    fmt.kv("Generated correction", fmt.trunc(record["correction"]["regenerated_text"]))

    fmt.stage(4, "Scope-violation safety gate (src.pipeline._scope_violation)", tag=fmt.LIVE)
    status = record["correction"]["status"]
    gate_passed = status != "correction_scope_violation"
    fmt.kv("Scope gate result", "PASSED (unflagged claim(s) preserved verbatim)" if gate_passed
           else "VIOLATION -- unflagged claim's required text is missing from the correction")
    fmt.kv("correction.status", status)

    fmt.stage(5, "Re-verification of the candidate correction", tag=fmt.LIVE if gate_passed else "N/A -- gate rejected before re-verification")
    reverification = record["correction"]["reverification"]
    if reverification is None:
        print("    Not reached: the scope gate rejected this correction BEFORE any"
              " re-verification call was made.")
    else:
        fmt.kv("Reverified hypothesis", fmt.trunc(reverification["reverified_hypothesis"]))
        fmt.kv("Reverification verdict", f"{reverification['verdict']} "
               f"(confidence {reverification['confidence']:.4f})")

    shipped = record["final_field"]["source"] == "corrected"
    if shipped:
        reason = (f"scope gate passed AND reverification verdict == ENTAILED "
                  f"(status={status!r})")
    elif status == "correction_scope_violation":
        reason = "scope gate caught an altered unflagged sentence -- never reached re-verification"
    else:
        reason = f"status={status!r} -- correction not shipped"
    fmt.final_gate_line(shipped=shipped, reason=reason)
    fmt.kv("final_field.source", record["final_field"]["source"])
    fmt.kv("final_field.text", fmt.trunc(record["final_field"]["text"]))
    print(f"\n  {fmt.NLI_DISCLAIMER}")

    return record


def main() -> int:
    cfg = ph.load_config()
    exact_index, all_usable = ph.load_evidence_pool(cfg)
    verifier = ph.load_verifier(cfg)

    case = Case(
        document_id="1994_495",
        case_text="Real case facts are not needed for this demo -- the generated "
                   "field is supplied directly by FakeGenerator.",
        raw_citation_keys=[],
    )

    record_a = _run_one(
        cfg, exact_index, all_usable, verifier, case, GOOD_CORRECTED_TEXT, "A -- expected to SHIP"
    )
    record_b = _run_one(
        cfg, exact_index, all_usable, verifier, case, BAD_CORRECTED_TEXT, "B -- expected to be REJECTED"
    )

    fmt.section("SHIPPED vs REJECTED -- side by side")
    header = f"  {'':<10} {'status':<28} {'reverification':<14} {'final_field.source'}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for label, rec in (("RUN A", record_a), ("RUN B", record_b)):
        reverif = rec["correction"]["reverification"]
        reverif_str = reverif["verdict"] if reverif else "None"
        print(f"  {label:<10} {rec['correction']['status']:<28} {reverif_str:<14} {rec['final_field']['source']}")

    fmt.section("Demo complete. No file under research/prototype/outputs/ or research/data/ was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
