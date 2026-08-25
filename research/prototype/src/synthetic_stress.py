"""
Deterministic, evidence-grounded synthetic contradiction generation.

Why this exists: the natural 30-case A/B/C evaluation produced ZERO
CONTRADICTED verdicts and ZERO correction triggers (see
outputs/mvp_assumption_evaluation.md, section 3) — either because the
small NLI verifier genuinely never disagreed with the (limited) generated
claims it could evidence-match, or because contradiction is simply rare in
practice. Either way, that 30-case run alone cannot tell us whether
selective correction WORKS when it does trigger, because it never
triggered. This module builds a SEPARATE, clearly-labeled stress-test set
to answer that narrower question.

Every synthetic claim here:
  - cites the REAL (provision_type, provision_number, act) of an actual
    usable canonical evidence record (so evidence matching is exact and
    the NLI premise is the real, audited statute text — never fabricated).
  - asserts something that deterministically, mechanically inverts a
    specific phrase actually present in that record's canonical_text
    (punishment type, "may"/"must", a conditional "unless/except", or a
    generic "shall" duty) — never a hand-authored or LLM-authored "wrong"
    legal claim. The transformation rule that fired is recorded, so every
    synthetic claim's provenance is auditable.
  - is tagged claim_source="SYNTHETIC_STRESS_TEST" end to end, and is
    never merged into the natural-generation evaluation set.

This is a robustness probe, not a legal-accuracy benchmark: it tests
whether the pipeline's verify -> correct -> reverify -> accept-only-if-
ENTAILED machinery functions correctly on GENUINELY contradictory input,
using real statute text as the premise. It says nothing about how well the
pipeline performs on genuinely-generated model claims, most of which are
para-phrase-shaped, not flatly contradictory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .data_loader import EvidenceRecord

SYNTHETIC_STRESS_TEST = "SYNTHETIC_STRESS_TEST"


@dataclass
class SyntheticClaim:
    claim_id: str
    claim_text: str
    transform_rule: str
    evidence: EvidenceRecord
    provision_type: str
    provision_number: str
    subsection: Optional[str]
    act_raw: str
    act_norm: str
    claim_source: str = SYNTHETIC_STRESS_TEST


def _article_prefix(text: str) -> str:
    return "an" if text[:1].lower() in "aeiou" else "a"


def _cite(rec: EvidenceRecord) -> str:
    sub = f"({rec.subsection})" if rec.subsection else ""
    return f"{rec.provision_type} {rec.provision_number}{sub} of {rec.act}"


# Each rule: (name, trigger_substring_lowercase, claim_builder). Tried in
# order; the FIRST rule whose trigger phrase is present in canonical_text
# (case-insensitive) is used, so every record gets exactly one synthetic
# claim and the choice of transform is a deterministic function of the
# record's own text, not a random or LLM choice.

def _rule_death_penalty_to_fine_only(rec: EvidenceRecord) -> str:
    return (
        f"{_cite(rec)} provides that the only punishment is a nominal fine, "
        f"and death or imprisonment can never be imposed under this provision."
    )


def _rule_life_imprisonment_to_short_term(rec: EvidenceRecord) -> str:
    return (
        f"{_cite(rec)} limits the maximum punishment to a fine of five "
        f"hundred rupees, with no possibility of imprisonment for life."
    )


def _rule_may_to_must(rec: EvidenceRecord) -> str:
    return (
        f"{_cite(rec)} makes this action an absolute, non-discretionary "
        f"legal duty that must always be carried out, with no discretion "
        f"permitted."
    )


def _rule_shall_negated(rec: EvidenceRecord) -> str:
    return (
        f"{_cite(rec)} makes compliance with this requirement entirely "
        f"optional, and it need not be followed under any circumstances."
    )


def _rule_condition_reversed(rec: EvidenceRecord) -> str:
    return (
        f"{_cite(rec)} applies unconditionally in every case, without any "
        f"of the exceptions or qualifying conditions it actually states."
    )


def _rule_generic_negation(rec: EvidenceRecord) -> str:
    return (
        f"{_cite(rec)} has no legal effect in this case and imposes no "
        f"obligation, right, or restriction of any kind."
    )


_TRANSFORM_RULES: list[tuple[str, Optional[str], "callable"]] = [
    ("punishment_death_to_fine_only", "death", _rule_death_penalty_to_fine_only),
    ("punishment_life_imprisonment_to_short_term", "imprisonment for life", _rule_life_imprisonment_to_short_term),
    ("may_to_must", " may ", _rule_may_to_must),
    ("shall_negated", " shall ", _rule_shall_negated),
    ("condition_reversed_unless_except", None, _rule_condition_reversed),  # handled specially below
    ("generic_negation", None, _rule_generic_negation),  # fallback, always fires
]

_CONDITION_TRIGGER_RE = re.compile(r"\b(unless|except|without prejudice|provided that)\b", re.IGNORECASE)


def _pick_rule(canonical_text: str) -> tuple[str, "callable"]:
    lower = canonical_text.lower()
    for name, trigger, builder in _TRANSFORM_RULES:
        if name == "condition_reversed_unless_except":
            if _CONDITION_TRIGGER_RE.search(canonical_text):
                return name, builder
            continue
        if name == "generic_negation":
            return name, builder  # always-fires fallback, must be last
        if trigger is not None and trigger in lower:
            return name, builder
    # Unreachable: generic_negation always fires as the last entry.
    return "generic_negation", _rule_generic_negation


def build_synthetic_stress_claims(usable_evidence: list[EvidenceRecord]) -> list[SyntheticClaim]:
    """One synthetic contradicted claim per usable evidence record,
    deterministic and reproducible (same input list -> same output every
    time, no randomness). See module docstring for the design rationale."""
    claims: list[SyntheticClaim] = []
    for i, rec in enumerate(usable_evidence, start=1):
        rule_name, builder = _pick_rule(rec.canonical_text)
        claim_text = builder(rec)
        claims.append(
            SyntheticClaim(
                claim_id=f"s{i}",
                claim_text=claim_text,
                transform_rule=rule_name,
                evidence=rec,
                provision_type=rec.provision_type,
                provision_number=rec.provision_number,
                subsection=rec.subsection,
                act_raw=rec.act,
                act_norm=rec.act_norm,
            )
        )
    return claims
