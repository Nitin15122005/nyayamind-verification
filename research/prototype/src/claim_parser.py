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
_ACT_SUFFIX_WORDS = (
    "Act", "Acts", "Code", "Codes", "Rule", "Rules", "Regulation", "Regulations",
    "Ordinance", "Ordinances",
)
_ACT_CONNECTOR_WORDS = ("of", "for", "and", "in", "on", "to", "from", "under", "the")
_ACT_WORD_PATTERN = (
    r"(?:[A-Z][\w'&\-]*(?:\s*\([^)]*\))?"
    r"|" + "|".join(_ACT_CONNECTOR_WORDS) + r")"
)
# The FIRST word of a bare act mention must be a real Title-Case word — a
# bare lowercase connector (of/in/for/...) is only ever allowed to CONTINUE
# an act name already in progress, never to START one. Without this,
# "...grounded IN the United Commercial Bank... Regulation, 1976" could
# match beginning at "in" (matching _ACT_CONNECTOR_WORDS), pulling a
# stray leading "in" from the surrounding prose into the act name.
_ACT_WORD_PATTERN_FIRST = r"[A-Z][\w'&\-]*(?:\s*\([^)]*\))?"
# Trailing year is usually comma-separated ("Act, 1976") but generated prose
# sometimes drops the comma before an act's own year ("Regulations 2000") —
# both must be recognized as part of the ACT NAME here, not left for the
# citation grammar below to misread the bare year as a provision number.
_BARE_ACT_MENTION_RE = re.compile(
    r"(?:[Tt]he\s+)?"
    r"(?:Constitution(?:\s+of\s+India)?"
    rf"|{_ACT_WORD_PATTERN_FIRST}(?:\s+{_ACT_WORD_PATTERN}){{0,9}}\s+(?:" + "|".join(_ACT_SUFFIX_WORDS) + r")\b)"
    r"(?:,?\s*\d{4})?"
    r"(?:\s*\(\s*[A-Za-z0-9\s.]{1,20}\s*\))?"
)

# A bare provision number that is actually a plausible calendar year
# (1500-2099) with no letter suffix and no subsection — e.g. "Regulations
# 2000" naming the ACT's own year, not "Regulation No. 2000". Only applied
# to the BARE_CITATION_REGEX path (no explicit "of/in <act>" clause of its
# own), which is exactly the ambiguous case; an explicit full-form citation
# ("Regulation 2000 of the X Act") is left untouched.
_PLAUSIBLE_YEAR_RE = re.compile(r"^(?:15|16|17|18|19|20)\d\d$")

# Detects a NEW citation starting mid-act-name — the run-on-sentence bug
# where a greedy act capture swallows a second "and Section N of <Act2>"
# clause belonging to an entirely different citation. Cutting here (and
# letting the caller re-scan the remainder) keeps the first citation's act
# clean and recovers the second citation instead of losing/merging it.
_EMBEDDED_CITATION_RE = re.compile(
    rf"\s*(?:,\s*)?(?:and|or)?\s*\b(?:{_KEYWORD_PATTERN})\s+\d",
    re.IGNORECASE,
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
    # 3rd-person-singular forms (a single Act/Section as subject) ...
    "prescribes", "states", "provides", "requires", "establishes",
    "outlines", "guarantees", "protects", "empowers", "mandates",
    "defines", "deals", "addresses", "governs", "allows", "permits",
    "grants", "declares", "penalizes", "punishes", "applies",
    # ... and their base/plural forms (a citation LIST as subject, e.g.
    # "Sections 25 and 27 of the Arms Act require ..." — plural subject
    # agreement, not a typo). Missing these left the act-name capture
    # running on into the rest of the sentence on this exact phrasing.
    "prescribe", "state", "provide", "require", "establish",
    "outline", "guarantee", "protect", "empower", "mandate",
    "define", "deal", "address", "govern", "allow", "permit",
    "grant", "declare", "penalize", "punish", "apply",
)
_VERB_TRIM_RE = re.compile(
    r"^(.*?)\s+(?:" + "|".join(_ACT_CONTINUATION_VERBS) + r")\b",
    re.IGNORECASE,
)
_COMMA_LOWERCASE_TRIM_RE = re.compile(r"^(.*?),\s*(?=[a-z])")


def _trim_act_name(act_raw: str) -> tuple[str, int]:
    """Return (trimmed_act_name, consumed_length), where consumed_length is
    how many characters of the ORIGINAL (untrimmed) `act_raw` this act name
    actually occupies. Callers use consumed_length to know where the act
    name ENDS within the sentence, so any leftover text after it (e.g. a
    second, previously-swallowed citation in a run-on sentence) can be
    re-scanned instead of being silently discarded.

    Four candidate cut points, tried independently (not first-match-wins —
    see below):
      - A new citation starting mid-capture ("... and Section 5(2) of
        <Act2>") — cut before it (fixes the run-on-sentence act-bleed bug).
      - A 4-digit year -> cut right after it ("Act ..., YYYY").
      - A year-less citation directly followed by a continuation verb.
      - A year-less citation followed by a comma + explanatory clause.
    Whichever candidate cuts EARLIEST in the text wins. Earliest-wins
    (not a fixed rule-priority order) matters because a single greedy
    over-capture can legitimately contain more than one of these signals
    at different positions — e.g. "the Constitution of India requires ...,
    while Article 15(4) allows ..." has both a continuation verb
    ("requires", early) AND a second, unrelated, entirely legitimate
    citation later in the same over-captured span ("Article 15(4)"); the
    verb signal is the correct (earlier) cut, so a fixed "citation-cut
    always wins" rule would wrongly keep scanning past the real act-name
    boundary and swallow "requires that ... while" into the act name.
    If nothing matches, keep everything (documented limitation)."""
    candidates: list[tuple[int, str]] = []

    m = _EMBEDDED_CITATION_RE.search(act_raw)
    if m and m.start() > 0:
        candidates.append((m.start(), act_raw[:m.start()]))

    m = _YEAR_TRIM_RE.match(act_raw)
    if m:
        candidates.append((m.end(1), m.group(1)))

    m = _VERB_TRIM_RE.match(act_raw)
    if m:
        candidates.append((m.end(1), m.group(1)))

    m = _COMMA_LOWERCASE_TRIM_RE.match(act_raw)
    if m:
        candidates.append((m.end(1), m.group(1)))

    if not candidates:
        return act_raw.strip().rstrip(","), len(act_raw)

    end, name = min(candidates, key=lambda pair: pair[0])
    return name.strip().rstrip(","), end


_ABBREVIATION_PAREN_RE = re.compile(r"\(\s*[A-Za-z0-9\s.]{1,20}\s*\)")

_KNOWN_ACT_ALIASES = {
    "ipc": "indian penal code 1860",
    "indian penal code": "indian penal code 1860",
    "crpc": "code of criminal procedure 1973",
    "code of criminal procedure": "code of criminal procedure 1973",
    "cpc": "code of civil procedure 1908",
    "code of civil procedure": "code of civil procedure 1908",
    "id act": "industrial disputes act 1947",
    "industrial disputes act": "industrial disputes act 1947",
    "constitution": "constitution of india",
}


def normalize_act(act_raw: str) -> str:
    """Lowercase, strip leading 'The', strip a trailing abbreviation gloss
    in parentheses (e.g. "the Indian Penal Code (IPC)" -> same act as "the
    Indian Penal Code"), strip periods/commas, collapse whitespace.
    Applied identically to both claim-extracted act names AND the
    canonical evidence corpus's own act names (data_loader.py calls this
    same function), so exact-match equality is symmetric — this never
    creates a one-sided rewrite that could accidentally match the wrong
    act, it only recognizes that two spellings name the SAME act."""
    a = act_raw.strip().lower()
    a = re.sub(r"^the\s+", "", a)
    a = _ABBREVIATION_PAREN_RE.sub("", a)
    a = re.sub(r"[.,]", "", a)
    a = re.sub(r"\s+", " ", a).strip()
    if a in _KNOWN_ACT_ALIASES:
        return _KNOWN_ACT_ALIASES[a]
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


def _citations_from_numbers(ptype: str, numbers_text: str, act_raw_clean: Optional[str], act_norm: str) -> list[ExtractedCitation]:
    citations: list[ExtractedCitation] = []
    for item_m in _NUMBER_ITEM_RE.finditer(numbers_text):
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


def _iter_full_form_matches(sentence: str):
    """Yield (start, end, ptype, numbers_text, act_raw_clean, act_norm) for
    every CITATION_REGEX ("<keyword> <numbers> in/of <act>") match in
    `sentence`, where (start, end) is the span this citation actually
    OCCUPIES — i.e. up through the TRIMMED act name, not the full greedy
    regex match.

    This is the fix for run-on multi-act sentences (e.g. "... Sections
    120-B, 471, and 477 of the Indian Penal Code and Section 5(2) ... of
    the Prevention of Corruption Act, 1947"): CITATION_REGEX's own act
    group is greedy up to the next '.'/';', so a second citation embedded
    in what looks like the first one's act clause would otherwise be
    permanently swallowed. By continuing the scan from the end of the
    TRIMMED act (via _trim_act_name's consumed_length) instead of from
    the end of the full greedy match, the leftover text is re-offered to
    CITATION_REGEX/BARE_CITATION_REGEX on the next iteration, recovering
    the second citation instead of merging or losing it."""
    pos = 0
    while pos < len(sentence):
        m = CITATION_REGEX.search(sentence, pos)
        if not m:
            return
        act_group_start = m.start("act")
        trimmed_act, consumed_len = _trim_act_name(m.group("act"))
        consumed_abs_end = act_group_start + consumed_len
        ptype = _normalize_provision_type(m.group("keyword"))
        yield (
            m.start(), consumed_abs_end, ptype, m.group("numbers"),
            trimmed_act, normalize_act(trimmed_act),
        )
        # Continue from the end of the TRIMMED act, not m.end(), so a
        # citation embedded in the over-captured remainder gets re-scanned
        # instead of being skipped over.
        pos = max(consumed_abs_end, m.start() + 1)


def _find_full_form_acts(sentence: str) -> list[tuple[str, str, int, int]]:
    """[(act_raw, act_norm, start, end), ...], in order of appearance, for
    every citation-with-its-own-act clause in `sentence`. start/end mark
    the span this act clause occupies (see _iter_full_form_matches)."""
    return [
        (act_raw, act_norm, start, end)
        for start, end, _ptype, _numbers, act_raw, act_norm in _iter_full_form_matches(sentence)
    ]


def _find_bare_act_mentions(sentence: str, exclude_spans: list[tuple[int, int]]) -> list[tuple[str, str, int, int]]:
    """[(act_raw, act_norm, start, end), ...], in order of appearance, for
    every Act/Code/Constitution NAME mentioned in `sentence` without a
    preceding citation keyword (see _BARE_ACT_MENTION_RE), SKIPPING any
    match that overlaps `exclude_spans` (the spans already claimed by a
    full-form citation's own act clause).

    Excluding those spans matters: a full act name like "the Code of
    Criminal Procedure, 1973" can otherwise also match this generic
    Act/Code-suffix regex on a truncated sub-span (e.g. just "of the
    Code"), inventing a second, spurious "distinct act" out of a citation
    that was already correctly parsed — which then wrongly makes an
    unrelated bare citation elsewhere in the sentence look ambiguous."""
    acts = []
    for m in _BARE_ACT_MENTION_RE.finditer(sentence):
        if any(s < m.end() and m.start() < e for s, e in exclude_spans):
            continue
        act_raw = m.group(0).strip().rstrip(",")
        acts.append((act_raw, normalize_act(act_raw), m.start(), m.end()))
    return acts


def _sentence_level_act(sentence: str, citation_pos: int) -> tuple[Optional[str], str]:
    """Best-effort act for a bare citation at `citation_pos` (its match
    start within `sentence`), using ONLY this sentence's own content:
    every full-form citation's act plus every bare Act/Code/Constitution
    mention found in the sentence, whichever ENDS closest before
    `citation_pos` ("nearest preceding act"). An act mentioned AFTER the
    citation is never used — that would be guessing forward. If nothing
    precedes it, returns the unresolved sentinel (None, ""); the field-wide
    fallback in extract_claims() may still resolve it."""
    full_form = _find_full_form_acts(sentence)
    exclude_spans = [(start, end) for _raw, _norm, start, end in full_form]
    bare = _find_bare_act_mentions(sentence, exclude_spans)

    preceding = [(raw, norm, end) for raw, norm, start, end in full_form + bare if end <= citation_pos]
    if not preceding:
        return None, ""
    raw, norm, _end = max(preceding, key=lambda t: t[2])
    return raw, norm


def extract_citations(sentence: str) -> list[ExtractedCitation]:
    """Return every citation found in the sentence, in reading order:
    - Every CITATION_REGEX ("<keyword> <numbers> in/of <act>") group,
      expanded into one ExtractedCitation per listed provision number
      (plural/list support, e.g. "Articles 1A, 31A, 31B, and 31C of the
      Constitution of India"). A run-on sentence with a second citation
      embedded in the first one's over-captured act clause has both
      recovered separately (see _iter_full_form_matches) rather than
      merged into one polluted act_norm.
    - Every remaining bare citation with no act clause of its own (e.g.
      "murder (Section 302)", "Section 148 deals with..."), whose act is
      resolved from this sentence's OWN content only (_sentence_level_act)
      — the nearest PRECEDING same-sentence Act/Code/Constitution mention
      or full-form citation's act. A bare citation with no preceding act
      in this sentence gets the unresolved sentinel (act_raw=None,
      act_norm="") here; extract_claims() may still resolve it via a
      safe field-wide fallback.
    - A bare provision number that is actually a plausible calendar year
      (e.g. "Regulations 2000") is dropped entirely, never emitted as a
      citation — see _PLAUSIBLE_YEAR_RE."""
    results: list[tuple[int, ExtractedCitation]] = []
    full_spans: list[tuple[int, int]] = []

    for start, end, ptype, numbers_text, act_raw_clean, act_norm in _iter_full_form_matches(sentence):
        full_spans.append((start, end))
        for citation in _citations_from_numbers(ptype, numbers_text, act_raw_clean, act_norm):
            results.append((start, citation))

    for m in BARE_CITATION_REGEX.finditer(sentence):
        if any(fs <= m.start() < fe for fs, fe in full_spans):
            continue  # already captured by a full-form ("... in/of <act>") match
        ptype = _normalize_provision_type(m.group("keyword"))
        sentence_act_raw, sentence_act_norm = None, ""
        resolved = False
        for item_m in _NUMBER_ITEM_RE.finditer(m.group("numbers")):
            split = _NUMBER_ITEM_SPLIT_RE.match(item_m.group(0).strip())
            if not split:
                continue
            number, subsection = split.groups()
            if subsection is None and _PLAUSIBLE_YEAR_RE.match(number):
                # A bare "<keyword> YYYY" with no act clause of its own is
                # almost always the ACT's own (comma-less) year, not a real
                # provision number this large — never guess a citation here.
                continue
            if not resolved:
                sentence_act_raw, sentence_act_norm = _sentence_level_act(sentence, m.start())
                resolved = True
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

    Field-wide act inheritance for a bare citation extract_citations()
    could not resolve from its own sentence (e.g. "Section 148 deals
    with..." in a sentence with no preceding act mention of its own), in
    two safe steps, most-specific first:
      1. Same-citation reuse: if this exact (provision_type,
         provision_number) already resolved to exactly one distinct act
         elsewhere in the field, reuse it — the natural "cite once with
         the Act, refer again by number only" pattern. If that same
         number resolved to two or more DIFFERENT acts elsewhere in the
         field, this is genuinely ambiguous and step 1 does not fire.
      2. Whole-field fallback: only if step 1 didn't apply, and exactly
         one distinct act was resolved ANYWHERE ELSE in the field (the
         simple single-act-field case), inherit it.
    Otherwise the citation is left unresolved. Never invented/guessed."""
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

    resolved = [
        c.citation_extracted for c in claims
        if c.citation_extracted is not None and c.citation_extracted.act_norm
    ]
    distinct_field_acts: dict[str, str] = {}
    for citation in resolved:
        distinct_field_acts.setdefault(citation.act_norm, citation.act_raw)

    for c in claims:
        citation = c.citation_extracted
        if citation is None or citation.act_norm:
            continue  # already resolved, or not a citation at all

        # Step 1: same (provision_type, provision_number) resolved
        # elsewhere in the field — reuse it only if unambiguous.
        same_number_acts: dict[str, str] = {}
        for other in resolved:
            if (
                other.provision_type == citation.provision_type
                and other.provision_number == citation.provision_number
            ):
                same_number_acts.setdefault(other.act_norm, other.act_raw)
        if len(same_number_acts) == 1:
            (norm, raw), = same_number_acts.items()
            citation.act_raw, citation.act_norm = raw, norm
            continue

        # Step 2: exactly one distinct act resolved anywhere else in the
        # field (the common simple single-act-field case).
        if len(distinct_field_acts) == 1:
            (norm, raw), = distinct_field_acts.items()
            citation.act_raw, citation.act_norm = raw, norm

    return claims
