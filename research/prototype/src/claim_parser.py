"""
Deterministic sentence splitting + citation extraction + normalization.

No LLM is used anywhere in this module. The citation regex and act-name
normalization reuse the exact logic established during the earlier
evidence-quality audit (see research/data/evidence/README.md, "Deterministic
filtering rules") so that citations extracted here are directly comparable
to the citation keys already normalized when canonical_statutes.jsonl was
built and checked in evidence_audit.jsonl.

Only sentences containing an explicit statute/article citation are treated
as "claims" — this verifier's scope is statutory claims only, not general
factual prose. That scoping limitation is intentional (see design doc) and
is not something this module tries to work around.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Matches "Section 302 of The Indian Penal Code, 1860", "Article 21 in
# Constitution of India", "Section 25F(1) of the Arms Act, 1959", etc.
# Deliberately accepts both "in" and "of" as the connector, since generated
# prose (unlike NyayaRAG's own citation keys, which always use "in") uses
# either depending on sentence phrasing.
#
# The keyword accepts an optional trailing "s" (Article/Articles,
# Section/Sections, ...) and the provision-number slot accepts a
# comma/"and"/"&"-separated list (e.g. "Articles 1A, 31A, 31B, and 31C",
# "Sections 8, 9 and 10") so that a single citation group naming several
# provisions of the same act is captured as one match. Each individual
# provision number in that list becomes its own ExtractedCitation via
# extract_citations() / extract_claims() below.
_PROVISION_KEYWORDS = ("Section", "Article", "Order", "Rule", "Regulation", "Clause", "Schedule")
_KEYWORD_PATTERN = "|".join(f"{kw}s?" for kw in _PROVISION_KEYWORDS)

# One provision number, e.g. "302", "31A", "25F(1)", "9A".
_NUMBER_ITEM_PATTERN = r"\d+[A-Za-z\-]*(?:\s*\([^)]+\))?"

# A list of one or more provision numbers: "31A"; "8, 9"; "1A, 31A, 31B, and
# 31C"; "8, 9 and 10". finditer() over this span later pulls out each
# individual number regardless of which separator glues them together.
_NUMBER_LIST_PATTERN = (
    rf"{_NUMBER_ITEM_PATTERN}(?:\s*,\s*{_NUMBER_ITEM_PATTERN})*"
    rf"(?:\s*,?\s*(?:and|&)\s*{_NUMBER_ITEM_PATTERN})?"
)

CITATION_REGEX = re.compile(
    rf"(?P<keyword>{_KEYWORD_PATTERN})\s+"
    rf"(?P<numbers>{_NUMBER_LIST_PATTERN})"
    r"\s+(?:in|of)\s+"
    r"(?P<act>.+?)(?=[.;]|$)",
    re.IGNORECASE,
)

# Citations the generator also naturally produces but that never state an
# "in X"/"of X" act clause of their own — parenthetical shorthand like
# "murder (Section 302)" and bare mentions like "Section 148 deals with
# the unlawful assembly". Same keyword/number-list grammar as
# CITATION_REGEX, just without the trailing act-clause requirement.
# extract_citations() only consults this for spans CITATION_REGEX didn't
# already claim, then resolves the act via _sentence_level_act() (same
# sentence) or, failing that, extract_claims()'s field-wide fallback —
# never by inventing one.
BARE_CITATION_REGEX = re.compile(
    rf"(?P<keyword>{_KEYWORD_PATTERN})\s+(?P<numbers>{_NUMBER_LIST_PATTERN})",
    re.IGNORECASE,
)

_NUMBER_ITEM_RE = re.compile(_NUMBER_ITEM_PATTERN)
_NUMBER_ITEM_SPLIT_RE = re.compile(r"^(\d+[A-Za-z\-]*)(?:\s*\(([^)]+)\))?$")

_SINGULAR_PROVISION_TYPES = {kw.lower() for kw in _PROVISION_KEYWORDS}

# Detects an Act/Code/Constitution NAME mentioned without a preceding
# citation keyword at all (e.g. "...the case is governed by the Indian
# Penal Code, 1860..."), so a same-sentence bare citation like "(Section
# 302)" can inherit it. Deliberately conservative — a run of Title-Case
# words (allowing the small set of lowercase connector words real act
# names use, e.g. "Prevention OF Corruption Act", "Transfer OF Property
# Act") ending in a recognized legal-instrument suffix, or the literal
# "Constitution [of India]" — rather than a generic "any capitalized
# phrase" detector: under-matching just leaves a citation unresolved
# (safe, per the "never invent an Act name" requirement), it never causes
# a wrong act to be attached.
_ACT_SUFFIX_WORDS = ("Act", "Code", "Rules", "Regulations", "Ordinance")
_ACT_CONNECTOR_WORDS = ("of", "for", "and", "in", "on", "to", "from", "under", "the")
_ACT_WORD_PATTERN = (
    r"(?:[A-Z][\w'&\-]*(?:\s*\([^)]*\))?"
    r"|" + "|".join(_ACT_CONNECTOR_WORDS) + r")"
)
_BARE_ACT_MENTION_RE = re.compile(
    r"(?:[Tt]he\s+)?"
    r"(?:Constitution(?:\s+of\s+India)?"
    rf"|(?:{_ACT_WORD_PATTERN}\s+){{1,10}}(?:" + "|".join(_ACT_SUFFIX_WORDS) + r"))"
    r"(?:,\s*\d{4})?"
)


def _normalize_provision_type(raw: str) -> str:
    """'Article'/'article' -> 'Article'; 'Articles'/'articles' -> 'Article'.
    Evidence records store provision_type in singular form (see
    data_loader.EvidenceRecord), so plural keywords must be singularized
    here or every plural citation would silently fail evidence matching."""
    lower = raw.lower()
    if lower.endswith("s") and lower[:-1] in _SINGULAR_PROVISION_TYPES:
        return lower[:-1].capitalize()
    return lower.capitalize()

# Simple, deterministic sentence splitter. Not a full NLP sentence
# tokenizer — good enough for the short, formulaic statutory_grounding
# paragraphs this pipeline generates, and kept deliberately simple/auditable
# rather than pulling in an NLP dependency for a one-field MVP.
_SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

_STOPWORDS = {
    "the", "of", "and", "in", "for", "to", "a", "an", "this", "that",
    "act", "constitution", "india",
}

# The outer CITATION_REGEX captures the Act name non-greedily up to the next
# '.'/';'/end-of-string, which over-captures when a citation is followed
# directly by more text with no terminating punctuation in between (e.g.
# "...the Indian Penal Code, 1860 prescribes punishment...", or
# "...Constitution of India guarantees...", or "...Constitution of India,
# particularly in relation to agrarian reforms..."). _trim_act_name() cleans
# that up deterministically, trying each rule in order and using the first
# one that matches:
#   1. If a 4-digit year appears, cut right after it (covers "Act ..., YYYY").
#   2. Else, cut right before the first word from _ACT_CONTINUATION_VERBS
#      (covers year-less citations directly followed by a verb, e.g.
#      "Constitution of India guarantees...").
#   3. Else, cut at the first comma that is immediately followed by a
#      lowercase word (covers year-less citations followed by an
#      explanatory/subordinate clause, e.g. "Constitution of India,
#      particularly in relation to..."). Legal act/constitution names are
#      consistently Title Case, so a comma followed by a lowercase word is a
#      reliable signal that the act name has ended and prose has begun — as
#      opposed to a comma that's part of the act's own name (which is
#      followed by another Title-Case word, or by a year already handled by
#      rule 1).
#   4. Else, leave as captured (best effort; documented limitation).
_YEAR_TRIM_RE = re.compile(r"^(.*?\b\d{4})\b")
_ACT_CONTINUATION_VERBS = (
    "prescribes", "states", "provides", "requires", "establishes",
    "outlines", "guarantees", "protects", "empowers", "mandates",
    "defines", "deals", "addresses", "governs", "allows", "permits",
    "grants", "declares", "penalizes", "punishes", "applies",
)
_VERB_TRIM_RE = re.compile(
    r"^(.*?)\s+(?:" + "|".join(_ACT_CONTINUATION_VERBS) + r")\b",
    re.IGNORECASE,
)
_COMMA_LOWERCASE_TRIM_RE = re.compile(r"^(.*?),\s*(?=[a-z])")


def _trim_act_name(act_raw: str) -> str:
    m = _YEAR_TRIM_RE.match(act_raw)
    if m:
        return m.group(1).strip().rstrip(",")
    m = _VERB_TRIM_RE.match(act_raw)
    if m:
        return m.group(1).strip().rstrip(",")
    m = _COMMA_LOWERCASE_TRIM_RE.match(act_raw)
    if m:
        return m.group(1).strip().rstrip(",")
    return act_raw.strip().rstrip(",")


def normalize_act(act_raw: str) -> str:
    """Lowercase, strip leading 'The', strip periods/commas, collapse
    whitespace. Identical logic to the earlier evidence-quality audit so
    citations extracted here compare equal to the pre-normalized keys in
    canonical_statutes.jsonl / evidence_audit.jsonl."""
    a = act_raw.strip().lower()
    a = re.sub(r"^the\s+", "", a)
    a = re.sub(r"[.,]", "", a)
    a = re.sub(r"\s+", " ", a).strip()
    return a


def act_significant_words(act_norm: str) -> set[str]:
    words = re.findall(r"[a-z']+", act_norm)
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


@dataclass
class ExtractedCitation:
    provision_type: str          # e.g. "Section", "Article" (title-cased)
    provision_number: str        # e.g. "302", "25F"
    subsection: Optional[str]    # e.g. "1", "a" — None if absent
    # act_raw is None / act_norm is "" when the Act could not be determined
    # (a bare citation with no resolvable act clause, same-sentence mention,
    # or unambiguous field-wide mention). Never guessed/invented — an empty
    # act_norm can never equal a real corpus act_norm, so match_evidence()
    # naturally falls through to NO_EVIDENCE without any special-casing.
    act_raw: Optional[str]       # as written in the generated text, or None
    act_norm: str                # normalized for matching, or "" if unresolved

    def as_dict(self) -> dict:
        return {
            "provision_type": self.provision_type,
            "provision_number": self.provision_number,
            "subsection": self.subsection,
            "act_raw": self.act_raw,
            "act_norm": self.act_norm,
        }


@dataclass
class Claim:
    claim_id: str
    claim_text: str
    citation_extracted: Optional[ExtractedCitation] = field(default=None)


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_REGEX.split(text)
    return [p.strip() for p in parts if p.strip()]


def _citations_from_match(m: re.Match) -> list[ExtractedCitation]:
    ptype = _normalize_provision_type(m.group("keyword"))
    act_raw_clean = _trim_act_name(m.group("act"))
    act_norm = normalize_act(act_raw_clean)

    citations: list[ExtractedCitation] = []
    for item_m in _NUMBER_ITEM_RE.finditer(m.group("numbers")):
        split = _NUMBER_ITEM_SPLIT_RE.match(item_m.group(0).strip())
        if not split:
            continue  # defensive; _NUMBER_ITEM_RE's own match always fits this shape
        number, subsection = split.groups()
        citations.append(
            ExtractedCitation(
                provision_type=ptype,
                provision_number=number,
                subsection=subsection.strip() if subsection else None,
                act_raw=act_raw_clean,
                act_norm=act_norm,
            )
        )
    return citations


def _find_full_form_acts(text: str) -> list[tuple[str, str]]:
    """[(act_raw, act_norm), ...], in order of appearance, for every
    CITATION_REGEX ("<keyword> <numbers> in/of <act>") match in `text`."""
    acts = []
    for m in CITATION_REGEX.finditer(text):
        act_raw = _trim_act_name(m.group("act"))
        acts.append((act_raw, normalize_act(act_raw)))
    return acts


def _find_bare_act_mentions(text: str) -> list[tuple[str, str]]:
    """[(act_raw, act_norm), ...], in order of appearance, for every
    Act/Code/Constitution NAME mentioned in `text` without a preceding
    citation keyword (see _BARE_ACT_MENTION_RE)."""
    acts = []
    for m in _BARE_ACT_MENTION_RE.finditer(text):
        act_raw = m.group(0).strip().rstrip(",")
        acts.append((act_raw, normalize_act(act_raw)))
    return acts


def _unique_acts(mentions: list[tuple[str, str]]) -> dict[str, str]:
    """act_norm -> first-seen act_raw, deduplicating a list of
    (act_raw, act_norm) mentions."""
    seen: dict[str, str] = {}
    for raw, norm in mentions:
        if norm and norm not in seen:
            seen[norm] = raw
    return seen


def _sentence_level_act(sentence: str) -> tuple[Optional[str], str]:
    """Best-effort act for a bare citation, using ONLY this sentence's own
    content: every full-form citation's act plus every bare Act/Code/
    Constitution mention found in the sentence. Resolves ONLY if exactly
    one distinct act is present (unambiguous) — otherwise returns the
    unresolved sentinel (None, ""), never guessing between candidates."""
    acts = _unique_acts(_find_full_form_acts(sentence) + _find_bare_act_mentions(sentence))
    if len(acts) == 1:
        (norm, raw), = acts.items()
        return raw, norm
    return None, ""


def extract_citations(sentence: str) -> list[ExtractedCitation]:
    """Return every citation found in the sentence, in reading order:
    - Every CITATION_REGEX ("<keyword> <numbers> in/of <act>") group,
      expanded into one ExtractedCitation per listed provision number
      (plural/list support, e.g. "Articles 1A, 31A, 31B, and 31C of the
      Constitution of India").
    - Every remaining bare citation with no act clause of its own (e.g.
      "murder (Section 302)", "Section 148 deals with..."), whose act is
      resolved from this sentence's OWN content only (_sentence_level_act)
      — an unambiguous same-sentence Act/Code/Constitution mention, or
      another full-form citation's act in the same sentence. A bare
      citation this sentence alone can't resolve gets the unresolved
      sentinel (act_raw=None, act_norm="") here; extract_claims() may
      still resolve it via an unambiguous field-wide fallback."""
    results: list[tuple[int, ExtractedCitation]] = []
    full_spans: list[tuple[int, int]] = []

    for m in CITATION_REGEX.finditer(sentence):
        full_spans.append((m.start(), m.end()))
        for citation in _citations_from_match(m):
            results.append((m.start(), citation))

    sentence_act_raw, sentence_act_norm = _sentence_level_act(sentence)
    for m in BARE_CITATION_REGEX.finditer(sentence):
        if any(fs <= m.start() < fe for fs, fe in full_spans):
            continue  # already captured by a full-form ("... in/of <act>") match
        ptype = _normalize_provision_type(m.group("keyword"))
        for item_m in _NUMBER_ITEM_RE.finditer(m.group("numbers")):
            split = _NUMBER_ITEM_SPLIT_RE.match(item_m.group(0).strip())
            if not split:
                continue
            number, subsection = split.groups()
            results.append((
                m.start(),
                ExtractedCitation(
                    provision_type=ptype,
                    provision_number=number,
                    subsection=subsection.strip() if subsection else None,
                    act_raw=sentence_act_raw,
                    act_norm=sentence_act_norm,
                ),
            ))

    results.sort(key=lambda pair: pair[0])
    return [c for _, c in results]


def extract_citation(sentence: str) -> Optional[ExtractedCitation]:
    """Return the FIRST citation found in a sentence, or None. Backward-
    compatible single-citation accessor over extract_citations()."""
    citations = extract_citations(sentence)
    return citations[0] if citations else None


def extract_claims(generated_text: str) -> list[Claim]:
    """Split into sentences; keep only sentences with an extractable
    citation. A sentence naming several provisions of the same act (e.g.
    "Articles 1A, 31A, 31B, and 31C of the Constitution of India") becomes
    one Claim PER provision — each with the same claim_text (the original
    sentence, preserved verbatim) but its own citation_extracted, so each
    provision gets its own independent evidence lookup and verification.
    Non-citation sentences are dropped (out of scope for this verifier),
    not silently kept and mis-verified.

    Field-wide act inheritance: a bare citation extract_citations() could
    not resolve from its own sentence (e.g. "Section 148 deals with..." in
    a sentence with no act mention of its own) inherits the act ONLY if
    exactly one distinct act was resolved anywhere ELSE in this same
    field — otherwise it's left unresolved. Never invented/guessed."""
    claims: list[Claim] = []
    for sentence in split_sentences(generated_text):
        for citation in extract_citations(sentence):
            claims.append(
                Claim(
                    claim_id=f"c{len(claims) + 1}",
                    claim_text=sentence,
                    citation_extracted=citation,
                )
            )

    resolved_acts = _unique_acts(
        (c.citation_extracted.act_raw, c.citation_extracted.act_norm)
        for c in claims
        if c.citation_extracted is not None and c.citation_extracted.act_norm
    )
    if len(resolved_acts) == 1:
        (field_norm, field_raw), = resolved_acts.items()
        for c in claims:
            citation = c.citation_extracted
            if citation is not None and not citation.act_norm:
                citation.act_raw = field_raw
                citation.act_norm = field_norm

    return claims
