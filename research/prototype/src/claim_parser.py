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

# Optional trailing "Part <roman-numeral>" annotation directly after a
# provision number ("Section 304, Part II of the Indian Penal Code") — a
# standard Indian legal-citation idiom for a section that itself has
# distinct numbered/lettered "Parts" (e.g. IPC s.304 Part I / Part II).
# Consumed here (rather than left for the act-name capture) so it never
# leaks into the act clause — without this, "Part" is Title-Case and
# satisfies _BARE_ACT_MENTION_RE's own first-word rule, so "Part II of the
# Indian Penal Code" was being captured as if it were the ACT's own name
# (found via real natural-data audit, document 1991_110: the Part-qualified
# citation's own act came back unresolved, and a later bare "Section 34" in
# the same sentence inherited the polluted "part ii of the indian penal
# code" pseudo-act instead of the real IPC).
_PART_QUALIFIER_PATTERN = r"(?:\s*,?\s*Part\s+[IVXLC]+[A-Za-z]?)?"

CITATION_REGEX = re.compile(
    rf"(?P<keyword>{_KEYWORD_PATTERN})\s+"
    rf"(?P<numbers>{_NUMBER_LIST_PATTERN})"
    rf"(?P<part>{_PART_QUALIFIER_PATTERN})"
    r"\s+(?:in|of)\s+"
    r"(?P<act>.+?)(?=[.;]|$)",
    re.IGNORECASE,
)

_PART_QUALIFIER_RE = re.compile(r"Part\s+([IVXLC]+[A-Za-z]?)", re.IGNORECASE)

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
    "grants", "declares", "penalizes", "punishes", "applies", "pertains",
    # ... and their base/plural forms (a citation LIST as subject, e.g.
    # "Sections 25 and 27 of the Arms Act require ..." — plural subject
    # agreement, not a typo). Missing these left the act-name capture
    # running on into the rest of the sentence on this exact phrasing.
    "prescribe", "state", "provide", "require", "establish",
    "outline", "guarantee", "protect", "empower", "mandate",
    "define", "deal", "address", "govern", "allow", "permit",
    "grant", "declare", "penalize", "punish", "apply", "pertain",
    # ... and copula forms, for phrasing like "the Evidence Act is
    # applicable, which prescribes ..." where the continuation is a
    # predicate adjective/clause rather than one of the verbs above. Found
    # via NO_EVIDENCE root-cause diagnosis on real natural output (3 real
    # occurrences, act_raw capturing "...the Evidence Act is applicable"
    # instead of stopping at "the Evidence Act").
    "is", "are", "was", "were",
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
    # "Evidence Act" (no "Indian" prefix) is the common short form — added
    # via the same NO_EVIDENCE root-cause diagnosis as the copula-verb fix
    # above (3 real occurrences: fuzzy matching alone falls to 0.5 overlap
    # here because "indian" is a significant word in the corpus's full
    # name but absent from the common short form, unlike "IPC"/"the Indian
    # Penal Code" where the shared "indian"+"penal"+"code" tokens already
    # clear the 0.8 threshold on their own).
    "evidence act": "indian evidence act 1872",
}


# A bare citation immediately followed by one of these well-known
# single-token abbreviations -- e.g. "Section 100 CrPC", "Section 302 IPC"
# -- with NO "in"/"of" connector in between. This is an extremely common
# real Indian-legal-citation shorthand (confirmed present verbatim in this
# project's own committed generated output: "Section 147 IPC", "Section
# 302 IPC", "Section 100 CrPC", etc.), but neither CITATION_REGEX (requires
# an explicit "in"/"of" connector) nor _BARE_ACT_MENTION_RE (requires an
# Act/Code/... suffix WORD, which a bare acronym is not) recognizes it as
# an act-bearing citation.
#
# Left unhandled, this citation's act stays unresolved at the sentence
# level and falls through to extract_claims()'s field-wide "exactly one
# distinct act elsewhere in the field" fallback -- which is actively WRONG
# whenever the field also contains a different, properly-cited Act
# elsewhere (real, reproduced case: "... Section 32 of the Indian Evidence
# Act, 1872. Section 100 CrPC also applies." previously mis-resolved the
# CrPC citation's act to "indian evidence act 1872", since the field looks
# single-act to that fallback only because THIS citation's own act
# signal — its trailing abbreviation — was being silently dropped). This
# is exactly the CrPC-vs-CPC-Section-100 confusion category
# tests/test_adversarial_citations.py already treats as a known adversarial
# risk, from a different root cause than that suite covers.
#
# Deliberately restricted to the exact three single-token acronyms already
# present, tested, and trusted in _KNOWN_ACT_ALIASES above (never a new
# alias invented for this) -- this only teaches the parser to attach an
# ALREADY-TRUSTED act identity to the position it appears in real
# generated prose, it never guesses a new one.
_TRAILING_ABBREV_TOKENS = ("IPC", "CrPC", "CPC")
# No leading `^`: this is matched via `.match(sentence, pos)` at a
# specific offset, not necessarily the string start — `^` (without
# MULTILINE) anchors to index 0 of the whole string regardless of `pos`,
# not to `pos` itself, so it would silently never match here.
#
# Optional leading comma (`,?\s*`, not just `\s*`): real generated prose
# uses both "Section 302 IPC" and "Section 302, IPC" for the exact same
# citation shape (both confirmed present verbatim in this project's own
# committed output) — the comma carries no different meaning here, so
# both must resolve identically.
_TRAILING_ABBREV_RE = re.compile(
    r",?\s*(" + "|".join(re.escape(t) for t in _TRAILING_ABBREV_TOKENS) + r")\b",
    re.IGNORECASE,
)


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
    # Additive, opt-in field — ALWAYS populated (falls back to claim_text
    # when a safe split isn't possible), so nothing reading claim_text
    # changes behaviour. See _parallel_clause_for_citation()/module
    # docstring below ("Atomic assertion splitting") for what this is and
    # is not: a conservative, structural improvement to VERIFICATION
    # HYPOTHESIS PRECISION for a specific bundled-sentence shape, not a
    # general clause-splitting NLP feature, and not wired into
    # apply_verification() as the default hypothesis source — that
    # remains claim_text unless a caller opts in.
    assertion_text: str = field(default="")
    # Additive, opt-in, structured generalization of assertion_text: a LIST
    # of independently-required VERBATIM fragments (each a contiguous
    # substring of claim_text — never concatenated, reordered, or
    # synthesized into new prose) that must ALL still be present for this
    # claim to be considered unmodified. For every claim assertion_text
    # already resolves (single clause/gloss, or the unresolved full
    # sentence), this is just `[assertion_text]` — a degenerate one-element
    # case, so it changes nothing by itself. It exists specifically for
    # patterns where a citation's relevant content is not one contiguous
    # span at all — e.g. a "respectively" list, where a citation's own
    # provision number lives in one place and its paired description lives
    # elsewhere in the same sentence (see `_assign_respectively_spans`)
    # — so representing "this claim's content" ever required inventing a
    # combined sentence. A list of disjoint required spans instead proves
    # nothing was fabricated: every element is checkable, individually, as
    # a `in` substring test against the model's own original text.
    assertion_spans: list = field(default_factory=list)

    def __post_init__(self):
        if not self.assertion_text:
            self.assertion_text = self.claim_text
        if not self.assertion_spans:
            self.assertion_spans = [self.assertion_text]


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
    """Yield (start, end, ptype, numbers_text, part_designation,
    act_raw_clean, act_norm) for every CITATION_REGEX ("<keyword> <numbers>
    [, Part <roman>] in/of <act>") match in `sentence`, where (start, end)
    is the span this citation actually OCCUPIES — i.e. up through the
    TRIMMED act name, not the full greedy regex match. part_designation is
    "Part <roman>" (e.g. "Part II") when this citation carried that
    qualifier, else None.

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
        part_group = m.group("part")
        part_designation = None
        if part_group:
            part_m = _PART_QUALIFIER_RE.search(part_group)
            if part_m:
                part_designation = f"Part {part_m.group(1).upper()}"
        yield (
            m.start(), consumed_abs_end, ptype, m.group("numbers"), part_designation,
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
        for start, end, _ptype, _numbers, _part, act_raw, act_norm in _iter_full_form_matches(sentence)
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

    for start, end, ptype, numbers_text, part_designation, act_raw_clean, act_norm in _iter_full_form_matches(sentence):
        full_spans.append((start, end))
        citations = _citations_from_numbers(ptype, numbers_text, act_raw_clean, act_norm)
        # Only attach a "Part <roman>" qualifier when it unambiguously
        # belongs to a single provision number — a bundled list ("Sections
        # 302, 304, Part II of the IPC") never lets the qualifier be safely
        # attributed to one specific number, so it is dropped rather than
        # guessed at.
        if part_designation and len(citations) == 1 and citations[0].subsection is None:
            citations[0].subsection = part_designation
        for citation in citations:
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
                trailing_m = _TRAILING_ABBREV_RE.match(sentence, m.end())
                if trailing_m:
                    # A known abbreviation directly adjacent to THIS
                    # citation is a stronger, more specific signal than any
                    # other same-sentence act mention (which may belong to
                    # an entirely different citation earlier in the
                    # sentence) -- takes priority over _sentence_level_act.
                    sentence_act_raw = trailing_m.group(1)
                    sentence_act_norm = normalize_act(sentence_act_raw)
                else:
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


_PARALLEL_CLAUSE_SPLIT_RE = re.compile(r"\s*,?\s+while\s+", re.IGNORECASE)


def _split_into_parallel_clauses(sentence: str) -> list[str]:
    """Conservative, single-purpose split of a bundled multi-citation
    sentence on ' while ' into (at most) two candidate parallel clauses —
    e.g. "Section 302 prescribes the punishment for murder, while Section
    34 deals with criminal liability..." -> two clauses, one per citation.

    Deliberately narrow: only the single, unambiguous "X while Y" shape is
    handled. A sentence with zero or more-than-one "while" returns itself
    unsplit (safe no-op) rather than guessing a clause boundary — this is
    a precision aid for one common, real natural-data pattern (found via
    the claim-granularity survey for this task: 15/33 bundled-citation
    sentences in the pooled n=30 + targeted n=11 set use this exact
    connector), not a general sentence-clause parser."""
    parts = _PARALLEL_CLAUSE_SPLIT_RE.split(sentence)
    if len(parts) != 2:
        return [sentence]
    return [p.strip() for p in parts]


def _citation_mentioned_in(clause: str, citation: ExtractedCitation) -> bool:
    """True if `clause`, independently re-parsed with this module's own
    `extract_citations()`, contains a citation matching this one's
    (provision_type, provision_number) — used to decide which clause of a
    split a given citation's assertion actually lives in. Reuses the real
    citation grammar (not a narrower ad-hoc regex) specifically so a
    number that is NOT immediately adjacent to its keyword — e.g. "482" in
    "Sections 3 and 482" — is still recognized; a naive adjacency regex
    would only ever match the FIRST number in such a list."""
    for c in extract_citations(clause):
        if c.provision_type == citation.provision_type and c.provision_number == citation.provision_number:
            return True
    return False


_SEMICOLON_SPLIT_RE = re.compile(r"\s*;\s*")


def _split_by_semicolons(sentence: str) -> list[str]:
    """Split on ';' — a much stronger, less ambiguous clause boundary than
    'while' (semicolons are used almost exclusively to separate distinct,
    self-contained items in a list, e.g. "...before the Special Judge;
    Section 4 of POTA, which provides...; and Sections 3 and 482 of
    CrPC..."), so ANY number of semicolon-delimited parts is accepted (not
    capped at 2 like the while-split) — each part is still only assigned
    to a citation via the same unambiguous-single-mention rule below, so
    an over-split still cannot mis-assign anything, only decline to."""
    parts = [p.strip() for p in _SEMICOLON_SPLIT_RE.split(sentence) if p.strip()]
    return parts if len(parts) >= 2 else [sentence]


# Splits ONLY right before a comma (optionally "and") that immediately
# precedes a NEW citation keyword — e.g. "Section 148 mandates X, section
# 304 deals with Y, and section 149 provides Z" -> 3 clauses, one per
# citation group. Deliberately narrower than a generic comma/and split
# (which would also fragment on internal "and"s inside one clause, e.g.
# "304 (Part-I) and 304 (Part-II)"): the citation-keyword lookahead is the
# actual structural signal for "a new per-citation clause starts here" in
# this generated prose, so only genuine clause boundaries are cut.
_CLAUSE_BOUNDARY_RE = re.compile(
    rf",\s*(?:and\s+)?(?=(?:{_KEYWORD_PATTERN})\s)", re.IGNORECASE
)


def _split_by_citation_keyword_boundaries(sentence: str) -> list[str]:
    parts = [p.strip() for p in _CLAUSE_BOUNDARY_RE.split(sentence) if p.strip()]
    return parts if len(parts) >= 2 else [sentence]


def _assign_from_clauses(sentence_claims: list[Claim], clauses: list[str]) -> None:
    """Shared assignment rule for both the semicolon and while splitters:
    a citation gets a clause's text as its assertion_text only if its own
    "<keyword> <number>" mention appears in EXACTLY ONE of the clauses.
    Ambiguous (multiple clauses) or absent (no clause) citations are left
    untouched by the caller (still carrying whatever assertion_text they
    already had — the full sentence, by default)."""
    for claim in sentence_claims:
        if claim.assertion_text != claim.claim_text:
            continue  # already resolved by an earlier, more specific pass
        citation = claim.citation_extracted
        if citation is None:
            continue
        matches = [c for c in clauses if _citation_mentioned_in(c, citation)]
        if len(matches) == 1:
            claim.assertion_text = matches[0]
        # else: ambiguous (in >=2 clauses) or unmentioned (in 0) — leave
        # as-is; never guess.


_PARENTHETICAL_GLOSS_RE_TEMPLATE = r"\b{number}\b\s*(\([^)]{{1,80}}\))"


def _parenthetical_gloss_span(sentence: str, citation: ExtractedCitation) -> Optional[str]:
    """Verbatim-only, mechanical extraction for lists like "Sections 302
    (murder), 34 (common intention), 323 (voluntarily causing hurt), ...":
    each provision number is immediately followed by its own short
    parenthetical gloss, but (unlike the first item, which reads "Sections
    302 (murder)") the keyword is usually NOT repeated before each later
    number — only the number-plus-gloss pair is. Matching on the bare
    number is therefore deliberately looser than
    `_citation_mentioned_in()`, so it is used ONLY as a last-resort pass
    (see `_assign_assertion_texts`) and ONLY when this exact number is
    followed by a parenthetical exactly once in the whole sentence — if
    the same bare number appears with a parenthetical more than once (or
    not at all), this returns None rather than guess. The returned span is
    a CONTIGUOUS VERBATIM substring of the original sentence — nothing is
    ever synthesized or reworded."""
    pattern = re.compile(
        _PARENTHETICAL_GLOSS_RE_TEMPLATE.format(number=re.escape(citation.provision_number))
    )
    matches = list(pattern.finditer(sentence))
    if len(matches) != 1:
        return None
    m = matches[0]
    # Include the citation's own keyword immediately before the number when
    # it is right there (e.g. "Sections 302 (murder)"); otherwise the span
    # is just "<number> (<gloss>)" as written (e.g. the bare "34
    # (common intention)" items later in the same list).
    start = m.start()
    prefix_pattern = re.compile(
        rf"\b{re.escape(citation.provision_type)}s?\s+$", re.IGNORECASE
    )
    prefix_match = prefix_pattern.search(sentence[:start])
    if prefix_match:
        start = prefix_match.start()
    return sentence[start:m.end()].strip().rstrip(",")


def _assign_assertion_texts(sentence: str, sentence_claims: list[Claim]) -> None:
    """Mutates each Claim's assertion_text in place. For a sentence with a
    single citation, assertion_text is just the sentence itself (no split
    needed — set by Claim.__post_init__'s default already). For a bundled
    sentence, three conservative passes are tried IN ORDER, each only
    filling in claims the previous pass left unresolved (still equal to
    the full sentence); every pass only ever assigns a CONTIGUOUS VERBATIM
    substring of the original sentence, never synthesizes new text:

      1. Semicolon split (`_split_by_semicolons`) — any number of clauses.
      2. ' while ' split (`_split_into_parallel_clauses`) — exactly two
         clauses (unchanged from the original implementation).
      3. Citation-keyword-boundary split
         (`_split_by_citation_keyword_boundaries`) — a comma-separated list
         of full clauses, each STARTING with its own citation mention
         ("Section 148 mandates X, section 304 deals with Y, and section
         149 provides Z") — distinct from pass 1 in that there is no
         semicolon, and from pass 2 in that there is no "while"; the
         boundary signal here is "a new citation keyword starts right
         after this comma."
      4. Parenthetical-gloss span (`_parenthetical_gloss_span`) — for a
         citation still unresolved after 1-3, e.g. because it and its
         sibling citations share one clause with no further separator
         ("Sections 302 (murder), 34 (common intention), 323 (...), ...").

    Any citation not resolved by any pass keeps the full sentence as its
    assertion_text — exactly today's existing behaviour for every sentence
    this doesn't apply to; never a regression, only a possible
    improvement."""
    if len(sentence_claims) < 2:
        return  # single citation: default (full sentence) already correct

    semi_clauses = _split_by_semicolons(sentence)
    if len(semi_clauses) >= 2:
        _assign_from_clauses(sentence_claims, semi_clauses)

    while_clauses = _split_into_parallel_clauses(sentence)
    if len(while_clauses) == 2:
        _assign_from_clauses(sentence_claims, while_clauses)

    keyword_boundary_clauses = _split_by_citation_keyword_boundaries(sentence)
    if len(keyword_boundary_clauses) >= 2:
        _assign_from_clauses(sentence_claims, keyword_boundary_clauses)

    for claim in sentence_claims:
        if claim.assertion_text != claim.claim_text:
            continue
        citation = claim.citation_extracted
        if citation is None:
            continue
        span = _parenthetical_gloss_span(sentence, citation)
        if span:
            claim.assertion_text = span

    # assertion_spans defaults to [assertion_text] at Claim construction
    # time (Claim.__post_init__), which runs BEFORE any of the three
    # passes above narrow assertion_text — so it must be re-synced here,
    # after assertion_text reaches its final value for this function, or
    # assertion_spans would silently keep pointing at the original (wider)
    # claim_text for every claim these passes resolved.
    for claim in sentence_claims:
        claim.assertion_spans = [claim.assertion_text]


# ---------------------------------------------------------------------------
# "Respectively" pattern — structured, multi-fragment assertion_spans.
#
# Real generated shape #1 (citation-list, THEN "respectively <verb> list"):
#   "...sections 302, 149, 323, and 34 of the IPC, 1860, which respectively
#   deal with murder, criminal conspiracy, voluntarily causing hurt, and
#   abetting the commission of a non-cognizable offense."
#
# Real shape #2 (citation-list, "which <description list>, respectively."):
#   "Sections 300 and 324 of the IPC, which require that the act must be
#   done with the intention to cause death or injury, and the act must
#   result in causing death or injury, respectively."
#
# Both promise the SAME thing: the Nth citation (in the order it was
# written) pairs with the Nth item in a trailing description list. This is
# never resolved into one combined sentence per citation — see the Claim.
# assertion_spans docstring — instead each citation gets TWO independently
# checkable, purely verbatim fragments: its own bare provision number
# (protects against a sibling citation's number being silently altered)
# and its own description item (a genuine, disjoint substring of the
# sentence — no reordering, no concatenation, no synthesis).
# ---------------------------------------------------------------------------

_RESPECTIVELY_RE = re.compile(r"\brespectively\b", re.IGNORECASE)
_WHICH_RE = re.compile(r"\bwhich\b", re.IGNORECASE)

# A short, closed list of literal verb-phrases this generated prose is
# observed to use directly after "respectively" — stripped from the FRONT
# of an items-zone if present, purely for readability of the extracted
# fragment (it is still a verbatim slice either way; this does not change
# whether the result is "fabricated," only how much boilerplate it drags
# in). Absence of a match here changes nothing except leaving a slightly
# noisier (but still fully verbatim) fragment.
_KNOWN_VERB_PREFIX_RE = re.compile(
    r"^(?:deal(?:s)?\s+with|pertain(?:s)?\s+to|relate(?:s)?\s+to|address(?:es)?|"
    r"govern(?:s)?|concern(?:s)?|cover(?:s)?|involve(?:s)?|require(?:s)?)\s+",
    re.IGNORECASE,
)

# Splits a comma/and-delimited prose list ("murder, criminal conspiracy,
# voluntarily causing hurt, and abetting an offense") into items, handling
# the Oxford comma ("X, and Y") as a single boundary rather than two.
# Longest alternative tried first so ", and " is not first cut at just the
# comma. Every returned item is a genuine slice of the input string.
_LIST_ITEM_SPLIT_RE = re.compile(r"\s*,\s+and\s+|\s*,\s*|\s+and\s+")


def _split_list_items(text: str) -> list[str]:
    return [p.strip() for p in _LIST_ITEM_SPLIT_RE.split(text) if p.strip()]


def _respectively_items_zone(sentence: str, resp_span: tuple[int, int]) -> Optional[str]:
    """Locate the verbatim substring most likely to hold the per-citation
    description list, using "which" as an anchor (every real example
    observed uses this exact relative-pronoun). Returns None (decline) if
    "which" doesn't appear exactly once, or if neither candidate zone has
    enough content to plausibly be a list — never guesses between two
    ambiguous candidates."""
    which_matches = list(_WHICH_RE.finditer(sentence))
    if len(which_matches) != 1:
        return None
    which_end = which_matches[0].end()
    resp_start, resp_end = resp_span

    zone_between = sentence[which_end:resp_start].strip(" ,.;")
    zone_after = sentence[resp_end:].strip(" ,.;")

    # Shape #2: "which <items>, respectively" — the real list sits between
    # "which" and "respectively". Preferred when substantial.
    if len(zone_between.split()) >= 3:
        return zone_between
    # Shape #1: "which respectively <verb> <items>" — "which" and
    # "respectively" are adjacent, so the list is AFTER "respectively"
    # instead.
    if len(zone_after.split()) >= 3:
        prefix_match = _KNOWN_VERB_PREFIX_RE.match(zone_after)
        return zone_after[prefix_match.end():] if prefix_match else zone_after
    return None


def _bare_number_span(sentence: str, citation: ExtractedCitation) -> Optional[str]:
    """Verbatim search for this citation's own provision number as a
    standalone token anywhere in the sentence. Deliberately permissive
    about WHERE it appears (it may be shared with sibling citations in one
    list, e.g. "Sections 302, 149, ...") — its only job is to make sure
    THIS number does not silently vanish or change value between the
    original and corrected text; it is one of two fragments required for a
    respectively-resolved claim, not the whole story on its own."""
    m = re.search(rf"\b{re.escape(citation.provision_number)}\b", sentence)
    return m.group(0) if m else None


def _assign_respectively_spans(sentence: str, sentence_claims: list[Claim]) -> None:
    """Mutates assertion_spans (NOT assertion_text — see the module-level
    comment above) for citations resolvable via the "respectively" pattern.
    Only ever acts on claims _assign_assertion_texts left fully unresolved
    (assertion_text == claim_text), and only when EVERY citation in the
    sentence can be assigned exactly one description item, in the exact
    order both were written — the standard, and only, correct reading of
    "respectively." Any ambiguity (more than one "respectively", item
    count not matching citation count, no citations at all) leaves every
    claim's assertion_spans at its existing (safe, already-set) default —
    this function only ever narrows, never widens or guesses."""
    if len(sentence_claims) < 2:
        return
    resp_matches = list(_RESPECTIVELY_RE.finditer(sentence))
    if len(resp_matches) != 1:
        return  # zero or ambiguous multiple "respectively" -> decline

    unresolved = [c for c in sentence_claims if c.assertion_text == c.claim_text]
    if len(unresolved) != len(sentence_claims):
        # Some citations in this sentence were already atomized by another
        # pass (semicolon/while/parenthetical) — this sentence does not
        # match the clean "every citation is part of one respectively list"
        # shape this function requires; decline rather than partially
        # apply against citations another mechanism already reasoned about.
        return

    items_zone = _respectively_items_zone(sentence, resp_matches[0].span())
    if items_zone is None:
        return
    items = _split_list_items(items_zone)
    if len(items) != len(sentence_claims):
        return  # count mismatch -> mapping cannot be proven; fail closed

    for claim, item in zip(sentence_claims, items):
        citation = claim.citation_extracted
        if citation is None:
            continue
        number_span = _bare_number_span(sentence, citation)
        fragments = [f for f in (number_span, item) if f]
        if not fragments:
            continue
        claim.assertion_spans = fragments


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
        sentence_claims: list[Claim] = []
        for citation in extract_citations(sentence):
            claim = Claim(
                claim_id=f"c{len(claims) + len(sentence_claims) + 1}",
                claim_text=sentence,
                citation_extracted=citation,
            )
            sentence_claims.append(claim)
        _assign_assertion_texts(sentence, sentence_claims)
        _assign_respectively_spans(sentence, sentence_claims)
        claims.extend(sentence_claims)

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
