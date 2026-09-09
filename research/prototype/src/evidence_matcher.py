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

import re
from dataclasses import dataclass
from typing import Optional

from .claim_parser import ExtractedCitation, act_significant_words
from .data_loader import EvidenceRecord

NO_EVIDENCE = "NO_EVIDENCE"

# `act_significant_words()` tokenizes with `[a-z']+`, which drops digits
# entirely — so two same-named Acts differing ONLY by year (e.g. "Income
# Tax Act, 1961" vs "Income-tax Act, 2025") reduce to an identical
# significant-word set and can fuzzy-cross-match at overlap 1.0, even
# though they are legally distinct enactments. Confirmed, documented latent
# limitation (see outputs/evidence_v1_independent_audit.md §5,
# tests/test_adversarial_citations.py::test_year_edition_...) — not
# triggered in the shipped 136-record corpus, but a real gap for any future
# corpus growth or new citation. Fixed here: if BOTH sides of a fuzzy
# comparison name an explicit year and those years differ, the pair can
# never fuzzy-match, regardless of token overlap. A side with NO explicit
# year (e.g. a claim that never states one, or an alias without one) is
# unaffected — that is the legitimate, intentional year-omission fuzzy path
# this project relies on elsewhere, and this change never narrows it.
_YEAR_RE = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")


def _act_years(act_norm: str) -> set[str]:
    return set(_YEAR_RE.findall(act_norm))


def _year_conflict(claim_years: set[str], ev_years: set[str]) -> bool:
    return bool(claim_years) and bool(ev_years) and claim_years.isdisjoint(ev_years)


@dataclass
class MatchResult:
    matched: bool
    evidence: Optional[EvidenceRecord]
    match_method: str  # "exact_normalized" | "fuzzy" | "no_evidence"


def _token_overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    a_no_digits = {w for w in a if not w.isdigit()}
    b_no_digits = {w for w in b if not w.isdigit()}
    if a_no_digits and a_no_digits == b_no_digits:
        return 1.0
    return len(a & b) / len(a | b)


def match_evidence(
    citation: ExtractedCitation,
    exact_index: dict[tuple, EvidenceRecord],
    all_usable: list[EvidenceRecord],
    fuzzy_token_overlap_threshold: float = 0.8,
    fuzzy_method: str = "jaccard",
    fuzzy_act_index: "object | None" = None,
    fuzzy_bm25_threshold: float = 0.5,
    fuzzy_embedding_threshold: float = 0.55,
) -> MatchResult:
    """
    fuzzy_method: "jaccard" (default, production-unchanged) | "bm25" |
    "embedding". Selects the act-name SIMILARITY SCORING function used only
    in the fuzzy fallback step below -- it never changes the legal-identity
    gate above (exact (provision_type, provision_number[, subsection]) key
    lookup) or the year-conflict veto. "bm25"/"embedding" require
    `fuzzy_act_index` (a prebuilt src.retrieval_signals.Bm25ActIndex /
    EmbeddingActIndex over the same `all_usable` list -- build once, reuse
    across calls; see scripts/benchmark_retrieval_signals.py for the
    measured comparison this default is based on). Thresholds are
    method-specific because the two backends' score scales differ (BM25 is
    min-max normalized per candidate set; embedding is raw cosine
    similarity) -- see retrieval_signals.best_match_among()'s docstring.
    """
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
    # similarity above threshold. The legal-identity gate (provision_type +
    # provision_number match, year-conflict veto) is IDENTICAL for every
    # fuzzy_method -- only the act-name scoring function below changes.
    claim_years = _act_years(citation.act_norm)
    same_number_year_ok: list[EvidenceRecord] = [
        ev for ev in all_usable
        if ev.provision_type == citation.provision_type
        and ev.provision_number == citation.provision_number
        and not _year_conflict(claim_years, _act_years(ev.act_norm))
    ]

    if fuzzy_method == "jaccard":
        claim_act_words = act_significant_words(citation.act_norm)
        best: Optional[EvidenceRecord] = None
        best_overlap = 0.0
        for ev in same_number_year_ok:
            ev_act_words = act_significant_words(ev.act_norm)
            overlap = _token_overlap(claim_act_words, ev_act_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best = ev
        if best is not None and best_overlap >= fuzzy_token_overlap_threshold:
            return MatchResult(matched=True, evidence=best, match_method="fuzzy")
        return MatchResult(matched=False, evidence=None, match_method="no_evidence")

    if fuzzy_method in ("bm25", "embedding"):
        if fuzzy_act_index is None:
            raise ValueError(f"fuzzy_method={fuzzy_method!r} requires fuzzy_act_index")
        from .retrieval_signals import best_match_among  # deferred: keeps optional deps optional

        scored = best_match_among(citation.act_norm, same_number_year_ok, fuzzy_act_index, fuzzy_method)
        threshold = fuzzy_bm25_threshold if fuzzy_method == "bm25" else fuzzy_embedding_threshold
        if scored.evidence is not None and scored.score >= threshold:
            return MatchResult(matched=True, evidence=scored.evidence, match_method="fuzzy")
        return MatchResult(matched=False, evidence=None, match_method="no_evidence")

    raise ValueError(f"unknown fuzzy_method: {fuzzy_method!r}")


# Failure-category taxonomy for a NO_EVIDENCE claim — mirrors, exactly, the
# already-validated methodology scripts/audit_no_evidence_taxonomy_v2.py has
# used project-wide (see outputs/final_research_results.md's NO_EVIDENCE
# taxonomy table, and outputs/evidence_v1_independent_audit.md §4): every
# NO_EVIDENCE claim genuinely falls into exactly one of these, decided by
# evidence (corpus content + measured token overlap), never guessed. This
# was previously only computable by re-running that standalone offline
# script over already-produced outputs — promoting it into a reusable,
# importable function closes a real ablation-readiness gap (mission
# priority: "the system must expose enough information to understand WHY
# an outcome occurred", not just a black-box NO_EVIDENCE label) without
# changing the taxonomy's own decision rule at all.
UNRESOLVED_ACT = "unresolved_act"
GENUINELY_ABSENT_NO_SUCH_PROVISION = "genuinely_absent_no_such_provision_any_act"
GENUINELY_ABSENT_WRONG_ACT_OR_EDITION = "genuinely_absent_wrong_act_or_edition"
PARSER_OR_MATCHER_DEFECT_CANDIDATE = "parser_or_matcher_defect_candidate"


def classify_no_evidence(
    citation: ExtractedCitation,
    all_usable: list[EvidenceRecord],
    fuzzy_token_overlap_threshold: float = 0.8,
) -> str:
    """Only meaningful (and only ever called by the pipeline) when
    match_evidence() already returned matched=False for this exact
    citation — this never re-derives or second-guesses the match/no-match
    decision itself, only explains it after the fact.

    - `unresolved_act`: the parser could not resolve an act at all
      (act_norm == "") — a parser-side limitation (see claim_parser.py's
      "never guess" field-wide-inheritance contract), not a corpus gap.
    - `genuinely_absent_no_such_provision_any_act`: no record for this
      (provision_type, provision_number) exists under ANY act in the
      corpus — a pure coverage gap, closing it needs more evidence data,
      not a code change.
    - `genuinely_absent_wrong_act_or_edition`: the provision number exists
      under a DIFFERENT act, correctly not matched (token overlap below
      threshold, or vetoed by an explicit year conflict) — the citation's
      own act really is a different enactment.
    - `parser_or_matcher_defect_candidate`: the provision number exists
      under an act with SUBSTANTIAL (0.5 <= overlap < threshold) but
      sub-threshold name overlap to the citation's own act — a genuine
      candidate for a normalization/alias gap, flagged for manual review
      rather than auto-corrected (this project's own project-wide review
      of every candidate ever surfaced this way found zero confirmed
      defects — see outputs/evidence_v1_independent_audit.md §4 — so this
      label means "worth a human look," never "confirmed bug")."""
    if not citation.act_norm:
        return UNRESOLVED_ACT

    same_number = [
        e for e in all_usable
        if e.provision_type == citation.provision_type
        and e.provision_number == citation.provision_number
    ]
    if not same_number:
        return GENUINELY_ABSENT_NO_SUCH_PROVISION

    claim_words = act_significant_words(citation.act_norm)
    best_overlap = 0.0
    for ev in same_number:
        overlap = _token_overlap(claim_words, act_significant_words(ev.act_norm))
        if overlap > best_overlap:
            best_overlap = overlap

    if 0.5 <= best_overlap < fuzzy_token_overlap_threshold:
        return PARSER_OR_MATCHER_DEFECT_CANDIDATE
    return GENUINELY_ABSENT_WRONG_ACT_OR_EDITION
