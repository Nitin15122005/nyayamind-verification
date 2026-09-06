#!/usr/bin/env python
"""
Scope / Safety Check demo -- isolates and exercises the REAL, unmodified
programmatic safety gate `src.pipeline._scope_violation()` directly (no
model call, no correction attempt -- that full lifecycle is demonstrated
separately in `06_correction_reverification_demo.py`).

What this demo shows:
  - The correction prompt already asks the model to "copy every sentence
    other than the flagged one verbatim." A prompt is not an enforcement
    mechanism. `_scope_violation()` is the actual, programmatic, code-level
    gate every real Mode-C run calls (see
    `src/pipeline.py::apply_selective_correction`) before a correction is
    ever allowed to ship.
  - One SAFE case: a corrected paragraph that leaves the unflagged sibling
    sentence untouched -> no violation.
  - One REJECTED case: a corrected paragraph where the unflagged sibling
    sentence was also altered -> violation caught.

What is genuinely LIVE here: the two `_scope_violation()` calls themselves
-- real, unmodified `research/prototype/src/pipeline.py` code, executed
now. This is a pure deterministic string-containment check (no NLI model,
no GPU, no network) -- CPU-safe on any machine.

Real data used (not fabricated): the flagged/unflagged sentence text below
is copied VERBATIM from
`research/prototype/tests/test_correction_path_real_integration.py`
(`_CORRECTED_FLAGGED_SENTENCE`, `_REAL_UNFLAGGED_SENTENCE`,
`_ALTERED_UNFLAGGED_SENTENCE`), which itself sources the unflagged sentence
verbatim from the real generated field in
`research/prototype/outputs/run_C_targeted_1994_495.jsonl` (document
`1994_495`). The scope-check mode (`use_assertion_spans` vs
`use_assertion_text`) is read from the real, unmodified production config
(`research/prototype/config/prototype.yaml`), never hardcoded.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/05_scope_safety_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import pipeline_helpers as ph  # noqa: E402
from common import formatting as fmt  # noqa: E402

from src import pipeline  # noqa: E402

# Verbatim from tests/test_correction_path_real_integration.py -- see module
# docstring above for provenance. Not altered in any way.
REAL_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with the unlawful assembly, which may be "
    "relevant if the prosecution can show that the accused acted as part of an "
    "unlawful assembly."
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


def _baseline_claims() -> list[dict]:
    """Two claim records from the original (pre-correction) document: the
    flagged target (c1, Section 302 -- its own text is irrelevant to this
    check, since `_scope_violation` excludes `target_claim_id`) and the
    unflagged sibling (c2, Section 148) whose survival is what this gate
    actually verifies."""
    return [
        {
            "claim_id": "c1",
            "claim_text": (
                "The offense of murder under Section 302 of the Indian Penal "
                "Code, 1860 is punishable only by a fine and never by death or "
                "imprisonment."
            ),
            "assertion_text": (
                "The offense of murder under Section 302 of the Indian Penal "
                "Code, 1860 is punishable only by a fine and never by death or "
                "imprisonment."
            ),
            "assertion_spans": [
                "The offense of murder under Section 302 of the Indian Penal "
                "Code, 1860 is punishable only by a fine and never by death or "
                "imprisonment."
            ],
            "citation_extracted": {
                "provision_type": "Section", "provision_number": "302",
                "subsection": None, "act_norm": "indian penal code 1860",
            },
        },
        {
            "claim_id": "c2",
            "claim_text": REAL_UNFLAGGED_SENTENCE,
            "assertion_text": REAL_UNFLAGGED_SENTENCE,
            "assertion_spans": [REAL_UNFLAGGED_SENTENCE],
            "citation_extracted": {
                "provision_type": "Section", "provision_number": "148",
                "subsection": None, "act_norm": "indian penal code 1860",
            },
        },
    ]


def _run_gate(corrected_text: str, use_assertion_text: bool, use_assertion_spans: bool) -> bool:
    return pipeline._scope_violation(
        _baseline_claims(), target_claim_id="c1", corrected_text=corrected_text,
        use_assertion_text=use_assertion_text, use_assertion_spans=use_assertion_spans,
    )


def main() -> int:
    fmt.section("SCOPE / SAFETY CHECK DEMO -- src.pipeline._scope_violation() (LIVE)")

    cfg = ph.load_config()
    atomic_scope_check_mode = cfg["correction"]["atomic_scope_check"]
    use_assertion_text = bool(atomic_scope_check_mode)
    use_assertion_spans = atomic_scope_check_mode == "assertion_spans"
    fmt.kv("Production correction.atomic_scope_check", repr(atomic_scope_check_mode))
    fmt.kv("-> use_assertion_text", use_assertion_text)
    fmt.kv("-> use_assertion_spans", use_assertion_spans)

    print(
        "\n  Why this exists: the correction prompt already asks the model to "
        "'rewrite the full\n  paragraph, changing ONLY the flagged sentence' -- "
        "but a prompt is not an enforcement\n  mechanism. `_scope_violation()` "
        "is the actual programmatic gate every real Mode-C run\n  calls "
        "(src/pipeline.py::apply_selective_correction) before a correction is "
        "ever allowed\n  to ship. Both calls below are the real, unmodified "
        "function -- no model, no GPU,\n  pure deterministic verbatim-text "
        "containment checks."
    )

    # -- Case 1: SAFE correction -------------------------------------------------
    fmt.stage(1, "SAFE correction (unflagged sentence untouched)", tag=fmt.LIVE)
    safe_corrected_text = CORRECTED_FLAGGED_SENTENCE + " " + REAL_UNFLAGGED_SENTENCE
    fmt.kv("Flagged sentence, corrected", fmt.trunc(CORRECTED_FLAGGED_SENTENCE))
    fmt.kv("Unflagged sibling sentence (must survive verbatim)", fmt.trunc(REAL_UNFLAGGED_SENTENCE))
    fmt.kv("Full corrected paragraph passed to the gate", fmt.trunc(safe_corrected_text))
    safe_violation = _run_gate(safe_corrected_text, use_assertion_text, use_assertion_spans)
    fmt.kv("_scope_violation(...) returned", safe_violation)
    print(
        "  The unflagged Section-148 sentence reappears byte-for-byte in the "
        "corrected paragraph,\n  so every required assertion_span is present "
        "-- no violation."
    )
    fmt.final_gate_line(
        shipped=not safe_violation,
        reason="no violation detected; correction would proceed to re-verification",
    )

    # -- Case 2: REJECTED scope violation -----------------------------------------
    fmt.stage(2, "REJECTED correction (unflagged sentence altered)", tag=fmt.LIVE)
    unsafe_corrected_text = CORRECTED_FLAGGED_SENTENCE + " " + ALTERED_UNFLAGGED_SENTENCE
    fmt.kv("Flagged sentence, corrected", fmt.trunc(CORRECTED_FLAGGED_SENTENCE))
    fmt.kv("Unflagged sibling sentence, ORIGINAL", fmt.trunc(REAL_UNFLAGGED_SENTENCE))
    fmt.kv("Unflagged sibling sentence, AS ALTERED BY THE CORRECTOR", fmt.trunc(ALTERED_UNFLAGGED_SENTENCE))
    print(
        "  Only two words changed -- \"unlawful assembly\" -> \"theft\", \"as part of "
        "an unlawful\n  assembly\" -> \"acted alone\" -- but that is enough: the "
        "unflagged claim's required text\n  no longer appears verbatim anywhere "
        "in the corrected paragraph."
    )
    fmt.kv("Full corrected paragraph passed to the gate", fmt.trunc(unsafe_corrected_text))
    unsafe_violation = _run_gate(unsafe_corrected_text, use_assertion_text, use_assertion_spans)
    fmt.kv("_scope_violation(...) returned", unsafe_violation)
    fmt.final_gate_line(
        shipped=not unsafe_violation,
        reason="unflagged claim's required text is missing from the corrected text"
        if unsafe_violation else "unexpected: no violation detected",
    )

    fmt.section("Summary")
    print(
        "  This gate is claim-scoped, not whole-paragraph-scoped: it only checks the "
        "specific\n  claims this pipeline already tracks, using each claim's own "
        "`assertion_spans` (the\n  narrowest safe verbatim fragment(s) -- see "
        "src/claim_parser.py) rather than requiring\n  the entire original sentence "
        "to survive untouched. A correction that fails this gate\n  is never shipped: "
        "`apply_selective_correction()` sets "
        "status='correction_scope_violation'\n  and falls back to the original, "
        "uncorrected text (see 06_correction_reverification_demo.py\n  for that full "
        "ship-vs-reject lifecycle, including real re-verification)."
    )

    assert safe_violation is False, "expected the SAFE case to report no violation"
    assert unsafe_violation is True, "expected the UNSAFE case to report a violation"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
