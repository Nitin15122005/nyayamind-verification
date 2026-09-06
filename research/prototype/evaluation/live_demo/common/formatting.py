"""
Shared terminal-output formatting for every live_demo script, so all of
A-G read as one consistent presentation rather than seven differently
styled scripts.

Conventions used throughout live_demo/:
  - section(title)     -- a top-level demo/case banner
  - stage(n, name, tag) -- a numbered pipeline-stage header, tagged LIVE /
                           REPLAYED / SCRIPTED so a reader always knows
                           whether what follows was just executed for real
                           or is a labeled historical/substituted value
  - kv(label, value)   -- one aligned "label: value" line
  - trunc(text, n)     -- consistent truncation for long generated text
  - claim_overview(...) -- THE shared fix for the "repeated claims" demo
                           presentation problem (see live_demo/README.md
                           "Why claims repeat" section): groups atomic
                           claims by their originating sentence and by
                           evidence key instead of printing N look-alike
                           lines with no explanation.
"""
from __future__ import annotations

from typing import Optional

LIVE = "LIVE"
REPLAYED = "REPLAYED (from committed output, not re-run)"
SCRIPTED = "SCRIPTED SUBSTITUTE (real pipeline logic, GPU-only Qwen call not invoked)"
STATIC = "STATIC (curated real record, read only)"

NLI_DISCLAIMER = (
    "Disclaimer: this is a small NLI model's statistical confidence that "
    "the statute text supports the claim sentence -- not a lawyer-verified "
    "legal-correctness determination."
)


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    print(f"\n  ── {title} " + "─" * max(1, 70 - len(title)))


def stage(n, name: str, tag: str = LIVE) -> None:
    label = f"[{n}]" if n is not None else ""
    print(f"\n  --- Stage {label} {name} :: {tag} ---")


def kv(label: str, value, indent: int = 2) -> None:
    pad = " " * indent
    print(f"{pad}{label}: {value}")


def trunc(text: Optional[str], n: int = 220) -> str:
    if text is None:
        return "None"
    text = str(text)
    return text if len(text) <= n else text[:n] + "..."


def bullet(text: str, indent: int = 4) -> None:
    print(" " * indent + f"- {text}")


def rule(char: str = "-", width: int = 78) -> None:
    print(char * width)


def claim_overview(claim_records: list[dict]) -> None:
    """The shared presentation for a document's atomic claims -- replaces
    printing N potentially look-alike `claim_text` previews with three
    grouped, explained views:

      1. Unique source sentences -> how many atomic claims/citations each
         produced (this is WHY claim_text can repeat: one sentence naming
         several provisions becomes one Claim per provision, each with its
         own citation/evidence/verdict -- see
         src/claim_parser.py::extract_claims's own docstring. Confirmed
         legitimate atomic decomposition, not duplicate parsing -- see
         live_demo/README.md "Why claims repeat").
      2. A compact claim -> citation -> evidence -> verdict mapping table,
         one row per claim, so each atomic claim's own distinguishing
         information (not just its shared parent sentence) is visible.
      3. Claims grouped BY evidence key, for any evidence cited by more
         than one claim (e.g. the same section cited in two different
         sentences of the same field) -- so a reader sees "these N claims
         all resolve to the same statute" as one grouped fact, not N
         separately-verified-looking repeats.

    Expects each dict in claim_records to have (at least):
      claim_id, claim_text, citation_extracted (dict or None), evidence_id,
      evidence_match_method, and optionally verdict/confidence.
    """
    by_sentence: dict[str, list[dict]] = {}
    for c in claim_records:
        by_sentence.setdefault(c["claim_text"], []).append(c)

    print(f"\n  {len(claim_records)} atomic claim(s) extracted from "
          f"{len(by_sentence)} unique source sentence(s):")
    for sentence, claims in by_sentence.items():
        print(f"\n    Sentence: \"{trunc(sentence, 140)}\"")
        if len(claims) == 1:
            c = claims[0]
            cite = _citation_str(c.get("citation_extracted"))
            print(f"      -> 1 citation-bearing claim: [{c['claim_id']}] {cite}")
        else:
            print(f"      -> {len(claims)} citations in this sentence, each its own atomic claim"
                  " (independently matched, verified, and correctable):")
            for c in claims:
                cite = _citation_str(c.get("citation_extracted"))
                print(f"           [{c['claim_id']}] {cite}")

    print("\n  Claim -> citation -> evidence -> verdict:")
    header = f"    {'claim_id':<8} {'citation':<26} {'evidence_id':<42} {'verdict':<24} {'confidence'}"
    print(header)
    print("    " + "-" * (len(header) - 4))
    for c in claim_records:
        cite = _citation_str(c.get("citation_extracted"))
        evidence_id = c.get("evidence_id") or "(no evidence)"
        verdict = c.get("verdict") or "-"
        confidence = c.get("confidence")
        conf_str = f"{confidence:.4f}" if isinstance(confidence, float) else "-"
        print(f"    {c['claim_id']:<8} {cite:<26} {trunc(evidence_id, 40):<42} {verdict:<24} {conf_str}")

    by_evidence: dict[str, list[str]] = {}
    for c in claim_records:
        eid = c.get("evidence_id")
        if eid:
            by_evidence.setdefault(eid, []).append(c["claim_id"])
    shared = {eid: ids for eid, ids in by_evidence.items() if len(ids) > 1}
    if shared:
        print("\n  Evidence cited by more than one claim in this document"
              " (grouped, not shown as separate unexplained repeats):")
        for eid, ids in shared.items():
            print(f"    {eid!r} <- claims {', '.join(ids)}")


def _citation_str(citation: Optional[dict]) -> str:
    if not citation:
        return "(no citation)"
    parts = [citation.get("provision_type", "?"), citation.get("provision_number", "?")]
    if citation.get("subsection"):
        parts.append(f"({citation['subsection']})")
    return " ".join(str(p) for p in parts)


def final_gate_line(shipped: bool, reason: str) -> None:
    """For an actual correction SHIP/REJECT decision (the scope-safety gate
    in demos 05/06) -- never use this for a Mode-B verification-only outcome,
    which never ships or rejects anything. Use mode_b_outcome_line() there."""
    verdict_word = "SHIPPED" if shipped else "REJECTED"
    print(f"\n  >>> FINAL DECISION: {verdict_word} -- {reason}")


def mode_b_outcome_line(verdict: str, note: str = "") -> None:
    """For a Mode-B (verification-only) full-pipeline outcome demo, where
    there is no ship/reject decision to report -- only a terminal verdict
    and the fact that final_field is always the untouched original text.
    Deliberately does not say SHIPPED/REJECTED (that framing belongs to the
    correction-gate decision in 05_scope_safety_demo.py /
    06_correction_reverification_demo.py, not to a Mode-B run)."""
    line = f"\n  >>> FINAL OUTCOME: {verdict} -- final_field is the original text (Mode B never corrects)"
    if note:
        line += f"; {note}"
    print(line)
