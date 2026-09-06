#!/usr/bin/env python
"""
NLI Verification demo (stage [4] of the pipeline) -- 100% LIVE.

Every verdict/confidence number printed by this script is computed just now,
by loading the real `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` checkpoint
(src.verifier.NLIVerifier, unmodified) and calling it live. Nothing here is
replayed from a committed output file, and no number is copied from any
report -- if you re-run this script, it re-computes everything from scratch.

CPU-safe: this ~184M-parameter NLI model runs fine on CPU in a few seconds
(auto-detects CUDA and uses it if present, exactly like
tests/test_correction_path_real_integration.py's own `real_verifier`
fixture -- see common/pipeline_helpers.py::load_verifier). No GPU required.

What this demonstrates:
  - premise  = the real canonical statute text for a citation, live-matched
               against the real 136-record production evidence pool, then
               formatted exactly as production does (src.verifier.format_premise,
               using the production `premise_framing` config value -- currently
               "labeled": the premise is prefixed with its own provision label,
               e.g. "Section 302 of the Indian Penal Code, 1860: ...").
  - hypothesis = a claim sentence.
  - verdict/confidence = the live NLI call's own output.

Three examples, one per label:
  - CONTRADICTED: a claim sentence that states the OPPOSITE of what Section
    302 IPC actually says (murder is punishable by death/life imprisonment,
    not "only by a fine and never by death or imprisonment").
  - ENTAILED: a claim sentence that accurately restates what Section 302 IPC
    says.
  - NOT_ENOUGH_INFORMATION (NEI): a claim sentence that mentions Section 148
    but never actually states what it punishes -- the premise can neither
    confirm nor deny an assertion the hypothesis doesn't make.

The three sentences reused below are copied VERBATIM from real generated
text in research/prototype/outputs/run_C_targeted_1994_495.jsonl (document
1994_495) and from the deliberately-corrupted/corrected variants of it that
tests/test_correction_path_real_integration.py's own module docstring
documents as being built from that same real record (see that test file for
the full provenance note) -- not invented for this demo.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/03_nli_verification_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import pipeline_helpers as ph  # noqa: E402
from common import formatting as fmt  # noqa: E402

from src.claim_parser import ExtractedCitation  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402
from src.pipeline import resolve_premise_framing  # noqa: E402
from src.verifier import format_premise  # noqa: E402

# Verbatim real text -- see module docstring for provenance.
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

IPC_1860 = ("the Indian Penal Code, 1860", "indian penal code 1860")


def _live_premise(provision_number: str, exact_index, all_usable, framing: str) -> tuple[str, str]:
    """Live-match the real evidence record for one IPC provision and build
    its production-style premise. Returns (premise, evidence_id) -- nothing
    here is hardcoded; the statute text comes from whatever the real,
    currently-loaded evidence pool actually contains."""
    act_raw, act_norm = IPC_1860
    citation = ExtractedCitation(
        provision_type="Section", provision_number=provision_number,
        subsection=None, act_raw=act_raw, act_norm=act_norm,
    )
    match = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    if not match.matched:
        raise RuntimeError(f"Section {provision_number} IPC not found in the live evidence pool -- "
                            "cannot build this demo's premise.")
    premise = format_premise(
        match.evidence.canonical_text, framing=framing,
        provision_type=match.evidence.provision_type,
        provision_number=match.evidence.provision_number,
        act=match.evidence.act,
    )
    return premise, match.evidence.dataset_citation_key


def _run_example(label: str, verifier, premise: str, evidence_id: str, hypothesis: str) -> None:
    fmt.subsection(label)
    fmt.kv("Evidence (premise source)", evidence_id)
    fmt.kv("Premise (real statute text, production-framed)", fmt.trunc(premise, 200))
    fmt.kv("Claim (hypothesis)", fmt.trunc(hypothesis, 200))
    result = verifier.verify(premise=premise, hypothesis=hypothesis)
    fmt.kv("Verdict (LIVE)", result.label)
    fmt.kv("Confidence (LIVE)", f"{result.confidence:.4f}")
    fmt.kv("sub_reason", result.sub_reason
           if result.sub_reason else "None (this is the model's own top-confidence label, "
                                      "not a low-confidence downgrade to NEI)")
    fmt.kv("raw_scores", {k: round(v, 4) for k, v in result.raw_scores.items()})


def main() -> int:
    fmt.section("NLI VERIFICATION -- LIVE (real DeBERTa-v3-base-mnli-fever-anli)")
    print(fmt.NLI_DISCLAIMER)

    fmt.stage(1, "Load production config, real evidence pool, real verifier", tag=fmt.LIVE)
    config = ph.load_config()
    framing = resolve_premise_framing(config)
    threshold = config["verification"]["confidence_threshold"]
    fmt.kv("premise_framing (production config)", framing)
    fmt.kv("confidence_threshold (production config)", threshold)
    fmt.kv("Verdicts below with confidence < threshold are downgraded to NOT_ENOUGH_INFORMATION",
           "with sub_reason='low_confidence' -- this never happens by coincidence, it's a fixed rule")

    exact_index, all_usable = ph.load_evidence_pool(config)
    fmt.kv("Evidence pool loaded", f"{len(all_usable)} usable records")

    verifier = ph.load_verifier(config)

    fmt.stage(2, "Live-match real evidence for Section 302 and Section 148 IPC", tag=fmt.LIVE)
    premise_302, evidence_id_302 = _live_premise("302", exact_index, all_usable, framing)
    premise_148, evidence_id_148 = _live_premise("148", exact_index, all_usable, framing)
    fmt.kv("Section 302 evidence_id", evidence_id_302)
    fmt.kv("Section 148 evidence_id", evidence_id_148)

    fmt.stage(3, "Three live verifier.verify() calls -- one per label", tag=fmt.LIVE)
    _run_example(
        "CONTRADICTED example -- claim states the opposite of the real Section 302 text",
        verifier, premise_302, evidence_id_302, CORRUPTED_FLAGGED_SENTENCE,
    )
    _run_example(
        "ENTAILED example -- claim accurately restates the real Section 302 text",
        verifier, premise_302, evidence_id_302, CORRECTED_FLAGGED_SENTENCE,
    )
    _run_example(
        "NOT_ENOUGH_INFORMATION example -- claim mentions Section 148 but asserts "
        "nothing the premise can confirm or deny",
        verifier, premise_148, evidence_id_148, REAL_UNFLAGGED_SENTENCE,
    )

    fmt.section("Summary")
    print("  All three verdicts above were computed just now, by this run, against the real,\n"
          "  live-loaded evidence pool and the real NLI model. A high-confidence ENTAILED verdict\n"
          "  means \"this small public NLI model's statistics favor the statute text supporting\n"
          "  this sentence\" -- it is not a lawyer-verified legal-correctness determination (see\n"
          "  the disclaimer above, and research/prototype/README.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
