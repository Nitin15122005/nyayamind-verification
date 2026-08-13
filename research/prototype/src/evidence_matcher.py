"""
Deterministic evidence lookup: given an ExtractedCitation, find the matching
EvidenceRecord in the usable canonical-evidence index.

Exact normalized match first; fuzzy fallback only if the exact match fails.
Always k=1 (the earlier evidence audit confirmed no duplicate
(act, provision_number) pairs exist in the usable pool, so ranking multiple
candidates is not a real problem at this corpus size). Returns a sentinel
NO_EVIDENCE result when nothing matches — this is a first-class outcome,
not an error.

This module never reads NyayaRAG's own `sections` text values — only
`data_loader.EvidenceRecord` objects sourced from canonical_statutes.jsonl
are ever returned as evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .claim_parser import ExtractedCitation, act_significant_words
from .data_loader import EvidenceRecord

NO_EVIDENCE = "NO_EVIDENCE"


@dataclass
class MatchResult:
    matched: bool
    evidence: Optional[EvidenceRecord]
    match_method: str  # "exact_normalized" | "fuzzy" | "no_evidence"


def _token_overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def match_evidence(
    citation: ExtractedCitation,
    exact_index: dict[tuple, EvidenceRecord],
    all_usable: list[EvidenceRecord],
    fuzzy_token_overlap_threshold: float = 0.8,
) -> MatchResult:
    index_key = (
        citation.provision_type,
        citation.provision_number,
        citation.subsection,
        citation.act_norm,
    )
    exact = exact_index.get(index_key)
    if exact is not None:
        return MatchResult(matched=True, evidence=exact, match_method="exact_normalized")

    # Exact match with subsection ignored (a claim citing "Section 25F(1)"
    # should still find the base "Section 25F" evidence record if that's
    # what's in the corpus, and vice versa).
    if citation.subsection is not None:
        loose_key = (citation.provision_type, citation.provision_number, None, citation.act_norm)
        exact_loose = exact_index.get(loose_key)
        if exact_loose is not None:
            return MatchResult(matched=True, evidence=exact_loose, match_method="exact_normalized")

    # Fuzzy fallback: same provision_type + provision_number, act-name
    # token overlap above threshold. Deterministic, no model involved.
    claim_act_words = act_significant_words(citation.act_norm)
    best: Optional[EvidenceRecord] = None
    best_overlap = 0.0
    for ev in all_usable:
        if ev.provision_type != citation.provision_type:
            continue
        if ev.provision_number != citation.provision_number:
            continue
        ev_act_words = act_significant_words(ev.act_norm)
        overlap = _token_overlap(claim_act_words, ev_act_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best = ev

    if best is not None and best_overlap >= fuzzy_token_overlap_threshold:
        return MatchResult(matched=True, evidence=best, match_method="fuzzy")

    return MatchResult(matched=False, evidence=None, match_method="no_evidence")
