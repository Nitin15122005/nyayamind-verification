#!/usr/bin/env python
"""
Demo A — Claim Parser (`src/claim_parser.py`).

Everything below is LIVE: real, unmodified `src.claim_parser` code, executed
now, on real text. Nothing is generated or invented for this demo.

Two real inputs are used:
  1. `research/prototype/outputs/final_gpu_validation_B.jsonl`, document
     `2011_625` — real Qwen-generated statutory-grounding text. This is the
     case that motivated this demo: naive per-claim previews make claims for
     "Section 302" / "Section 304" look repeated. They are not duplicates —
     see "Why claims are split" below.
  2. `research/prototype/evaluation/components/01_claim_parser/demo_examples.json`
     — a harder, real adversarial sentence (verbatim Qwen output, document
     `2007_1517`) already audited by `tests/test_claim_parser_bugfixes.py`,
     used here to show multi-act citation extraction and to self-check this
     demo's live output against that file's own recorded expected values.

Why claims are split (read this before the output below)
----------------------------------------------------------
`src/claim_parser.py::extract_claims()`'s own docstring states the rule
plainly: "A sentence naming several provisions of the same act ... becomes
one Claim PER provision — each with the same claim_text (the original
sentence, preserved verbatim) but its own citation_extracted, so each
provision gets its own independent evidence lookup and verification."

This is a deliberate design choice (atomic decomposition), not a parsing bug
and not duplicate parsing: two claims can legitimately share an identical
`claim_text` preview because they came from the same sentence, while still
being two independent claims — different citations, matched against
different evidence, verified independently, and (later in the pipeline)
correctable independently of one another. An earlier version of this demo
printed only a truncated `claim_text` per claim, which made this legitimate
behavior look like noise. `fmt.claim_overview()` below fixes the
*presentation*: it groups claims by their originating sentence and shows
each claim's own citation, so the reason for any repeated text is visible
instead of hidden.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/01_claim_parser_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE_DEMO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(LIVE_DEMO_ROOT))

from common import formatting as fmt  # noqa: E402
from common import pipeline_helpers as ph  # noqa: E402

from src import claim_parser  # noqa: E402

DEMO_EXAMPLES_PATH = (
    ph.EVALUATION_ROOT / "components" / "01_claim_parser" / "demo_examples.json"
)


def part_one_repeated_claims() -> None:
    fmt.section("PART 1 — Why 'Section 302' / 'Section 304' can look repeated")

    rec = ph.load_record(
        "research/prototype/outputs/final_gpu_validation_B.jsonl", "2011_625"
    )
    text = rec["generated_field"]["text"]
    fmt.stage(1, "Input text (real Qwen-generated statutory grounding)", fmt.LIVE)
    fmt.kv("Source", "research/prototype/outputs/final_gpu_validation_B.jsonl (document 2011_625)")
    print(f"    \"{fmt.trunc(text, 500)}\"")

    fmt.stage(2, "src.claim_parser.extract_claims(text)", fmt.LIVE)
    claims = claim_parser.extract_claims(text)
    claim_records = [
        {
            "claim_id": c.claim_id,
            "claim_text": c.claim_text,
            "citation_extracted": c.citation_extracted.as_dict() if c.citation_extracted else None,
            "assertion_text": c.assertion_text,
            "assertion_spans": list(c.assertion_spans),
        }
        for c in claims
    ]
    fmt.claim_overview(claim_records)

    print(
        "\n  Reading the table above: claims c1/c2 share one sentence that names two\n"
        "  provisions at once ('Sections 302 and 304 Part III') -- one Claim per\n"
        "  provision, same design as any bundled citation list. Claims c3/c4 are a\n"
        "  SEPARATE, later sentence that happens to discuss Section 302 and Section\n"
        "  304 again on their own -- the model simply mentions both sections twice in\n"
        "  this field. Both situations are legitimate: every claim above is\n"
        "  independently matched against evidence and independently verified, never\n"
        "  merged with or assumed identical to a same-numbered sibling."
    )


def part_two_adversarial_sentence() -> None:
    fmt.section("PART 2 — A harder real sentence: multi-act citation extraction")

    example = json.loads(DEMO_EXAMPLES_PATH.read_text(encoding="utf-8"))
    sentence = example["input_sentence"]
    fmt.stage(1, "Input sentence (real Qwen output, document 2007_1517)", fmt.LIVE)
    fmt.kv("Source", str(DEMO_EXAMPLES_PATH.relative_to(ph.REPO_ROOT)))
    print(f"    \"{fmt.trunc(sentence, 400)}\"")

    fmt.stage(2, "src.claim_parser.extract_citations(sentence)", fmt.LIVE)
    live_citations = [c.as_dict() for c in claim_parser.extract_citations(sentence)]
    print(f"  Extracted {len(live_citations)} citation(s):")
    for i, c in enumerate(live_citations, start=1):
        sub = f"({c['subsection']})" if c["subsection"] else ""
        fmt.bullet(f"[{i}] {c['provision_type']} {c['provision_number']}{sub} -- act_raw={c['act_raw']!r}")

    fmt.subsection("Self-check against components/01_claim_parser/demo_examples.json")
    expected = example["actual_extracted_citations"]
    expected_count = example["actual_extracted_claims_count"]
    match = live_citations == expected and len(live_citations) == expected_count
    fmt.kv("Recorded expected count", expected_count)
    fmt.kv("Live extracted count", len(live_citations))
    if match:
        print("  Result: PASS -- live extraction is byte-for-byte identical to the "
              "recorded, previously-audited result (deterministic, real, not fabricated).")
    else:
        print("  Result: MISMATCH -- live extraction differs from the recorded result:")
        fmt.kv("Recorded", expected, indent=4)
        fmt.kv("Live", live_citations, indent=4)
    fmt.kv("Software invariant this example checks", example["software_invariant_checked"])


def main() -> int:
    part_one_repeated_claims()
    part_two_adversarial_sentence()

    fmt.section("Summary")
    print(
        "  General rule: extract_claims() produces one Claim per CITATION, not one\n"
        "  Claim per SENTENCE. A sentence with N citations yields N claims that share\n"
        "  a claim_text but carry distinct citation_extracted/assertion data, so each\n"
        "  can be matched to its own evidence, verified independently, and (if\n"
        "  flagged) corrected without affecting its siblings. This demo used no model\n"
        "  and modified no file under src/, tests/, config/, research/data/, or\n"
        "  research/prototype/outputs/."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
