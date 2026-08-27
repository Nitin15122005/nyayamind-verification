"""
Tiny, deterministic unit tests for citation parsing and evidence matching.

No model, no GPU, no network access, no NyayaRAG data required for the
synthetic tests. A second, small suite of "real data" tests loads the
actual (read-only) canonical_statutes.jsonl + evidence_audit.jsonl to check
that the loader correctly excludes SOURCE_ONLY / INVALID / UNRESOLVED
records from the usable evidence pool — this is the single most
safety-critical property of the whole pipeline (never trust unverified
evidence), so it gets a dedicated real-data check rather than only a
synthetic one.
"""
from pathlib import Path

import pytest

from src.claim_parser import (
    ExtractedCitation,
    extract_citation,
    extract_citations,
    extract_claims,
    normalize_act,
    split_sentences,
)
from src.data_loader import EvidenceRecord, load_usable_evidence, load_usable_evidence_from_config
from src.evidence_matcher import match_evidence

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CANONICAL_PATH = REPO_ROOT / "research/data/evidence/canonical_statutes.jsonl"
AUDIT_PATH = REPO_ROOT / "research/data/evidence/evidence_audit.jsonl"
CANONICAL_V1_PATH = REPO_ROOT / "research/data/evidence/canonical_statutes_v1.jsonl"
AUDIT_V1_PATH = REPO_ROOT / "research/data/evidence/evidence_audit_v1.jsonl"


# ---------------------------------------------------------------------------
# normalize_act
# ---------------------------------------------------------------------------

def test_normalize_act_strips_leading_the_and_punctuation():
    assert normalize_act("The Indian Penal Code, 1860") == "indian penal code 1860"


def test_normalize_act_handles_no_leading_the():
    assert normalize_act("Constitution of India") == "constitution of india"


def test_normalize_act_collapses_whitespace():
    assert normalize_act("The   Arms  Act,   1959") == "arms act 1959"


# ---------------------------------------------------------------------------
# split_sentences
# ---------------------------------------------------------------------------

def test_split_sentences_basic():
    text = "This is sentence one. This is sentence two! Is this sentence three?"
    assert split_sentences(text) == [
        "This is sentence one.",
        "This is sentence two!",
        "Is this sentence three?",
    ]


def test_split_sentences_empty_string():
    assert split_sentences("") == []
    assert split_sentences("   ") == []


# ---------------------------------------------------------------------------
# extract_citation — the case that originally over-captured the Act name
# into the following verb phrase (caught while writing this test suite,
# fixed in src/claim_parser.py via _trim_act_name()).
# ---------------------------------------------------------------------------

def test_extract_citation_stops_at_year_before_trailing_verb():
    sentence = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_type == "Section"
    assert c.provision_number == "302"
    assert c.act_raw == "the Indian Penal Code, 1860"
    assert c.act_norm == "indian penal code 1860"


def test_extract_citation_stops_at_verb_when_no_year_present():
    sentence = "Article 21 of the Constitution of India guarantees personal liberty."
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_type == "Article"
    assert c.provision_number == "21"
    assert c.act_norm == "constitution of india"


def test_extract_citation_handles_subsection():
    sentence = "Section 25F(1) of the Industrial Disputes Act, 1947 requires notice."
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_number == "25F"
    assert c.subsection == "1"


def test_extract_citation_returns_none_for_non_citation_sentence():
    sentence = "The court found the appeal to be without merit."
    assert extract_citation(sentence) is None


def test_extract_citation_uses_in_connector_like_nyayarag_keys():
    # NyayaRAG's own citation keys always use "in", e.g.
    # "Section 482 in The Code of Criminal Procedure, 1973".
    sentence = "Section 482 in The Code of Criminal Procedure, 1973 is relevant here."
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_number == "482"
    assert "code of criminal procedure" in c.act_norm


# ---------------------------------------------------------------------------
# _trim_act_name / act-name extraction — trailing explanatory prose must not
# be captured into the act name. Regression tests for the evidence-matching
# bug: "Articles 1A, 31A, 31B, and 31C of the Constitution of India,
# particularly in relation to agrarian reforms..." produced an act_norm
# polluted with the whole trailing clause, so exact AND fuzzy evidence
# matching both failed even though the citations were correctly parsed.
# ---------------------------------------------------------------------------

def test_act_name_trims_trailing_prose_after_comma_no_year_plural_articles():
    sentence = (
        "The statutory grounding includes protections provided by Articles "
        "1A, 31A, 31B, and 31C of the Constitution of India, particularly in "
        "relation to agrarian reforms and the protection of such measures "
        "from certain constitutional challenges."
    )
    citations = extract_citations(sentence)
    assert [c.provision_number for c in citations] == ["1A", "31A", "31B", "31C"]
    for c in citations:
        assert c.act_raw == "the Constitution of India"
        # Requirement 3: "the Constitution of India" -> "constitution of india"
        assert c.act_norm == "constitution of india"


def test_act_name_year_case_still_works_unchanged():
    # Preserve existing matching behavior: the year-trim rule fires first
    # and must be unaffected by the new comma/lowercase fallback rule.
    sentence = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    c = extract_citation(sentence)
    assert c is not None
    assert c.act_raw == "the Indian Penal Code, 1860"
    assert c.act_norm == "indian penal code 1860"


def test_act_name_trims_trailing_prose_after_comma_no_year_generic_act():
    # A year-less act name (not "Constitution of India") directly followed
    # by a comma + explanatory clause, with no word from
    # _ACT_CONTINUATION_VERBS present, so only the new comma/lowercase rule
    # can fix it.
    sentence = (
        "Section 8 of the Fair Compensation Act, particularly relevant to "
        "land valuation disputes in rural areas."
    )
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_number == "8"
    assert c.act_raw == "the Fair Compensation Act"
    assert c.act_norm == "fair compensation act"


def test_act_name_same_section_number_different_acts_no_collision_after_trim():
    # Same provision_type + provision_number across two different acts (one
    # year-cited, one comma/prose-trimmed) must still normalize to distinct
    # act_norm values so evidence lookup never conflates the two statutes.
    ipc = extract_citation(
        "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    )
    other = extract_citation(
        "Section 302 of the Prevention of Corruption Act, particularly regarding public servants."
    )
    assert ipc is not None and other is not None
    assert ipc.provision_number == other.provision_number == "302"
    assert ipc.act_norm == "indian penal code 1860"
    assert other.act_norm == "prevention of corruption act"
    assert ipc.act_norm != other.act_norm


# ---------------------------------------------------------------------------
# Bare citations — citation forms the generator naturally produces that
# never state an "in X"/"of X" act clause of their own: parenthetical
# shorthand ("murder (Section 302)") and bare mentions ("Section 148 deals
# with..."). Regression tests for the Mode-C case (document_id 1994_495)
# where these forms produced zero claims even though "Section 302" is
# right there in the text and in the evidence pool.
# ---------------------------------------------------------------------------

def test_bare_citation_parenthetical_inherits_same_sentence_act():
    # "(Section 302)" has no act clause of its own; the sentence's own
    # "governed by the Indian Penal Code, 1860" mention is unambiguous, so
    # it's inherited directly (sentence-level resolution, no field-wide
    # fallback needed).
    sentence = (
        "The case is governed by the Indian Penal Code, 1860, which requires "
        "that the prosecution prove the offense of murder (Section 302)."
    )
    citations = extract_citations(sentence)
    assert len(citations) == 1
    c = citations[0]
    assert c.provision_type == "Section"
    assert c.provision_number == "302"
    assert c.act_norm == "indian penal code 1860"


def test_bare_citation_deals_with_no_own_act_stays_unresolved_at_sentence_level():
    # "Section 148 deals with..." on its own sentence, with no act mention
    # anywhere in that sentence, cannot be resolved by extract_citations()
    # alone (no field-wide context available at this level) — it must stay
    # unresolved (never guessed), not silently attached to some act.
    sentence = "Section 148 deals with the unlawful assembly."
    citations = extract_citations(sentence)
    assert len(citations) == 1
    c = citations[0]
    assert c.provision_type == "Section"
    assert c.provision_number == "148"
    assert c.act_raw is None
    assert c.act_norm == ""


def test_extract_citation_still_handles_existing_full_form():
    # Requirement: the existing "<keyword> <number> of/in <Act>" form must
    # keep working exactly as before.
    sentence = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_number == "302"
    assert c.act_norm == "indian penal code 1860"


def test_extract_claims_field_wide_inheritance_for_bare_citation_without_own_act():
    # The full regression scenario: sentence 1 establishes the act via a
    # bare mention ("governed by the Indian Penal Code, 1860") and cites
    # three provisions parenthetically; sentence 2's "Section 148 deals
    # with..." has no act of its own and must inherit it from the field
    # (exactly one distinct act resolved elsewhere in the same field).
    text = (
        "The case is governed by the Indian Penal Code, 1860, which requires that the "
        "prosecution must prove the guilt of the accused beyond a reasonable doubt for "
        "the offenses of murder (Section 302), voluntary causing of hurt (Section 323), "
        "and criminal conspiracy (Section 149). "
        "Additionally, Section 148 deals with the unlawful assembly, which may be "
        "relevant if the prosecution can show that the accused acted as part of an "
        "unlawful assembly."
    )
    claims = extract_claims(text)
    numbers = [c.citation_extracted.provision_number for c in claims]
    assert numbers == ["302", "323", "149", "148"]
    for c in claims:
        assert c.citation_extracted.act_norm == "indian penal code 1860"
        assert c.citation_extracted.act_raw == "the Indian Penal Code, 1860"
        # claim_text must be the exact original sentence, unmodified.
        assert c.citation_extracted is not None
    assert claims[0].claim_text.startswith("The case is governed by")
    assert claims[3].claim_text.startswith("Additionally, Section 148")


def test_extract_claims_unresolved_citation_no_identifiable_act_anywhere():
    # No act is mentioned anywhere in the field (not even ambiguously) —
    # the citation must still be extracted (provision_type/number present)
    # but with act left unresolved, never invented.
    text = "Section 55 deals with an unrelated procedural matter."
    claims = extract_claims(text)
    assert len(claims) == 1
    c = claims[0].citation_extracted
    assert c.provision_number == "55"
    assert c.act_raw is None
    assert c.act_norm == ""


def test_extract_claims_unresolved_citation_evidence_match_returns_no_evidence():
    # End-to-end guarantee: an unresolved act must never be guessed by the
    # evidence matcher either — it must cleanly fall through to
    # NO_EVIDENCE, not raise or coincidentally match.
    text = "Section 55 deals with an unrelated procedural matter."
    claims = extract_claims(text)
    citation = claims[0].citation_extracted

    ev = _make_evidence("Section", "55", "Some Unrelated Act, 2000", text="Unrelated text.")
    all_usable = [ev]
    exact_index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable}

    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is False
    assert result.match_method == "no_evidence"


def test_extract_claims_ambiguous_field_two_distinct_acts_stays_unresolved():
    # Two DIFFERENT acts are mentioned in the field, so field-wide
    # inheritance must not guess between them — the bare citation with no
    # act of its own must stay unresolved.
    text = (
        "The case is governed by the Indian Penal Code, 1860. "
        "It is also governed by the Arms Act, 1959. "
        "Section 55 deals with an unrelated procedural matter."
    )
    claims = extract_claims(text)
    bare_claim = next(c for c in claims if c.citation_extracted.provision_number == "55")
    assert bare_claim.citation_extracted.act_raw is None
    assert bare_claim.citation_extracted.act_norm == ""


def test_bare_citation_plural_keywords_still_supported():
    # Preserve existing plural-citation support in the bare-citation path
    # too (no act clause at all, field has no resolvable act either).
    text = "Articles 14 and 21 are fundamental rights."
    claims = extract_claims(text)
    assert [c.citation_extracted.provision_number for c in claims] == ["14", "21"]
    assert all(c.citation_extracted.provision_type == "Article" for c in claims)
    assert all(c.citation_extracted.act_norm == "" for c in claims)


def test_bare_citation_same_section_number_different_acts_no_collision():
    # Two different sentences, each with their own bare citation of the
    # same provision number, resolving to two different acts via their
    # own same-sentence bare Act mention — no cross-contamination.
    ipc_sentence = (
        "The case is governed by the Indian Penal Code, 1860, addressing "
        "the offense of murder (Section 302)."
    )
    other_sentence = (
        "The case is governed by the Prevention of Corruption Act, 1988, "
        "addressing bribery (Section 302)."
    )
    ipc_citation = extract_citations(ipc_sentence)[0]
    other_citation = extract_citations(other_sentence)[0]
    assert ipc_citation.provision_number == other_citation.provision_number == "302"
    assert ipc_citation.act_norm == "indian penal code 1860"
    assert other_citation.act_norm == "prevention of corruption act 1988"
    assert ipc_citation.act_norm != other_citation.act_norm


# ---------------------------------------------------------------------------
# extract_citations — plural keywords, provision-list expansion (regression
# tests for the Mode-C bug: "Articles 1A, 31A, 31B, and 31C" produced zero
# claims because the old regex only matched singular "Article" immediately
# followed by whitespace + one number).
# ---------------------------------------------------------------------------

def test_extract_citations_plural_keyword_singular_number():
    # A bare plural keyword ("Articles") with only one number must still
    # match and singularize provision_type.
    sentence = "Articles 21 of the Constitution of India guarantees personal liberty."
    citations = extract_citations(sentence)
    assert len(citations) == 1
    assert citations[0].provision_type == "Article"
    assert citations[0].provision_number == "21"


def test_extract_citations_oxford_comma_and_list():
    sentence = "Articles 1A, 31A, 31B, and 31C of the Constitution of India apply here."
    citations = extract_citations(sentence)
    assert [c.provision_number for c in citations] == ["1A", "31A", "31B", "31C"]
    assert all(c.provision_type == "Article" for c in citations)
    assert all("constitution of india" in c.act_norm for c in citations)


def test_extract_citations_no_oxford_comma_and_list():
    sentence = "Sections 8, 9 and 10 of the Arms Act, 1959 apply here."
    citations = extract_citations(sentence)
    assert [c.provision_number for c in citations] == ["8", "9", "10"]
    assert all(c.provision_type == "Section" for c in citations)


def test_extract_citations_two_item_and_only_list_no_comma():
    sentence = "Rules 8 and 9 of the Civil Procedure Rules, 1908 apply here."
    citations = extract_citations(sentence)
    assert [c.provision_number for c in citations] == ["8", "9"]
    assert all(c.provision_type == "Rule" for c in citations)


def test_extract_citations_list_with_per_item_subsections():
    sentence = "Clauses 8(1), 9A(2) of the Some Act, 1950 apply here."
    citations = extract_citations(sentence)
    assert [c.provision_number for c in citations] == ["8", "9A"]
    assert [c.subsection for c in citations] == ["1", "2"]
    assert all(c.provision_type == "Clause" for c in citations)


def test_extract_citations_singular_keyword_still_works_unexpanded():
    # Backward compatibility: a plain singular citation still yields
    # exactly one citation (no regression from the list-expansion logic).
    sentence = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    citations = extract_citations(sentence)
    assert len(citations) == 1
    assert citations[0].provision_number == "302"


def test_extract_citations_returns_empty_list_for_non_citation_sentence():
    sentence = "The court found the appeal to be without merit."
    assert extract_citations(sentence) == []


def test_extract_citation_still_returns_first_of_expanded_list():
    # extract_citation() (singular) stays backward compatible: it returns
    # just the first citation of an expanded plural group.
    sentence = "Sections 8, 9 and 10 of the Arms Act, 1959 apply here."
    c = extract_citation(sentence)
    assert c is not None
    assert c.provision_number == "8"


# ---------------------------------------------------------------------------
# extract_claims — only citation-bearing sentences become claims
# ---------------------------------------------------------------------------

def test_extract_claims_drops_non_citation_sentences():
    text = (
        "This case concerns a property dispute. "
        "Section 106 of the Transfer of Property Act, 1882 governs lease duration. "
        "The parties disagreed on the notice period."
    )
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].claim_id == "c1"
    assert claims[0].claim_text == "Section 106 of the Transfer of Property Act, 1882 governs lease duration."
    assert claims[0].citation_extracted.provision_number == "106"


def test_extract_claims_assigns_sequential_ids_skipping_non_citation_sentences():
    text = (
        "No citation here. "
        "Section 34 of the Indian Penal Code, 1860 addresses common intention. "
        "Also no citation. "
        "Article 21 of the Constitution of India guarantees personal liberty."
    )
    claims = extract_claims(text)
    assert [c.claim_id for c in claims] == ["c1", "c2"]


def test_extract_claims_expands_plural_citation_into_one_claim_per_provision():
    # Regression test for the Mode-C bug: a single sentence naming several
    # provisions of the same act must become one Claim per provision, each
    # sharing the exact same (verbatim, unmodified) sentence text, so each
    # provision gets its own independent evidence lookup/verification.
    text = "Articles 1A, 31A, 31B, and 31C of the Constitution of India apply here."
    claims = extract_claims(text)
    assert len(claims) == 4
    assert [c.claim_id for c in claims] == ["c1", "c2", "c3", "c4"]
    assert [c.citation_extracted.provision_number for c in claims] == ["1A", "31A", "31B", "31C"]
    assert all(c.citation_extracted.provision_type == "Article" for c in claims)
    # Every expanded claim must preserve the original sentence verbatim.
    assert all(c.claim_text == text for c in claims)


def test_extract_claims_expansion_ids_continue_across_sentences():
    text = (
        "Sections 8 and 9 of the Arms Act, 1959 apply here. "
        "Article 21 of the Constitution of India guarantees personal liberty."
    )
    claims = extract_claims(text)
    assert [c.claim_id for c in claims] == ["c1", "c2", "c3"]
    assert [c.citation_extracted.provision_number for c in claims] == ["8", "9", "21"]


# ---------------------------------------------------------------------------
# evidence_matcher — synthetic evidence pool
# ---------------------------------------------------------------------------

def _make_evidence(provision_type, provision_number, act, subsection=None, text="dummy text"):
    return EvidenceRecord(
        dataset_citation_key=f"{provision_type} {provision_number} in {act}",
        act=act,
        provision_type=provision_type,
        provision_number=provision_number,
        subsection=subsection,
        canonical_text=text,
        source_url="https://example.invalid/doc/1",
        audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act(act),
    )


@pytest.fixture
def synthetic_pool():
    ev1 = _make_evidence("Section", "302", "The Indian Penal Code, 1860", text="Murder punishment text.")
    ev2 = _make_evidence("Article", "21", "Constitution of India", text="Personal liberty text.")
    all_usable = [ev1, ev2]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


def test_evidence_matcher_exact_match(synthetic_pool):
    exact_index, all_usable = synthetic_pool
    citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="the Indian Penal Code, 1860", act_norm="indian penal code 1860",
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.match_method == "exact_normalized"
    assert result.evidence.canonical_text == "Murder punishment text."


def test_evidence_matcher_fuzzy_fallback_on_slightly_different_act_wording(synthetic_pool):
    exact_index, all_usable = synthetic_pool
    # "Indian Penal Code 1860" without "The" and without comma still
    # normalizes almost identically; force a near-miss by adding one
    # extra significant token so the exact key doesn't match but fuzzy
    # overlap does. (NOT a parenthetical abbreviation like "(IPC)" — that
    # is now stripped by normalize_act() as the SAME act, per the
    # claim-parser fix, and would match exact_normalized instead; see
    # test_normalize_act_strips_parenthetical_abbreviation below.)
    citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="Indian Penal Code Statute 1860",
        act_norm=normalize_act("Indian Penal Code Statute 1860"),
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.5)
    assert result.matched is True
    assert result.match_method == "fuzzy"
    assert result.evidence.dataset_citation_key.startswith("Section 302")


def test_normalize_act_strips_parenthetical_abbreviation():
    # Regression test: "the Indian Penal Code (IPC)" is the SAME act as
    # "the Indian Penal Code" — generated prose commonly appends this kind
    # of abbreviation gloss, and previously it made exact evidence lookup
    # fail (act_norm carried the "(ipc)" token, never equal to the corpus's
    # clean "indian penal code" key), silently downgrading a real citation
    # to fuzzy-or-nothing. Applied identically to both sides (evidence
    # corpus normalization uses this same function), so it only recognizes
    # two spellings as the same act — it never redirects a citation to a
    # DIFFERENT act.
    assert normalize_act("The Indian Penal Code (IPC), 1860") == normalize_act("The Indian Penal Code, 1860")
    assert normalize_act("the Code of Criminal Procedure (CrPC), 1973") == normalize_act(
        "the Code of Criminal Procedure, 1973"
    )


def test_evidence_matcher_returns_no_evidence_when_nothing_matches(synthetic_pool):
    exact_index, all_usable = synthetic_pool
    citation = ExtractedCitation(
        provision_type="Section", provision_number="999", subsection=None,
        act_raw="Some Unrelated Act, 2000", act_norm=normalize_act("Some Unrelated Act, 2000"),
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is False
    assert result.evidence is None
    assert result.match_method == "no_evidence"


def test_evidence_matcher_same_section_number_different_acts_no_collision():
    """Two evidence records can share the same provision_type/number as
    long as their acts differ (e.g. Section 302 exists in both the IPC and
    some other act). The exact-match index key includes act_norm, so a
    claim citing one act must never resolve to the other act's text —
    a number-only lookup would silently return the wrong statute."""
    ipc302 = _make_evidence(
        "Section", "302", "The Indian Penal Code, 1860", text="Murder punishment text."
    )
    other302 = _make_evidence(
        "Section", "302", "The Some Other Act, 1999", text="Unrelated provision text."
    )
    all_usable = [ipc302, other302]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }

    ipc_citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="the Indian Penal Code, 1860", act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    other_citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="the Some Other Act, 1999", act_norm=normalize_act("The Some Other Act, 1999"),
    )

    ipc_result = match_evidence(ipc_citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    other_result = match_evidence(other_citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)

    assert ipc_result.matched is True
    assert ipc_result.evidence.canonical_text == "Murder punishment text."
    assert other_result.matched is True
    assert other_result.evidence.canonical_text == "Unrelated provision text."


def test_evidence_matcher_subsection_falls_back_to_base_section(synthetic_pool):
    exact_index, all_usable = synthetic_pool
    # Corpus has "Section 302" (no subsection); claim cites "Section 302(1)".
    citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection="1",
        act_raw="the Indian Penal Code, 1860", act_norm="indian penal code 1860",
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.evidence.subsection is None


def test_evidence_matcher_adjacent_provision_numbers_never_cross_match():
    """Section 302 and Section 303 of the SAME act must never be confused —
    match_evidence requires an EXACT provision_number match even in the
    fuzzy-fallback path (only the Act-name comparison is approximate), so
    an off-by-one citation number can only ever resolve to its own
    evidence or to NO_EVIDENCE, never quietly borrow a neighbour's text."""
    sec302 = _make_evidence("Section", "302", "The Indian Penal Code, 1860", text="Murder punishment text.")
    sec303 = _make_evidence("Section", "303", "The Indian Penal Code, 1860", text="Murder by life-convict text.")
    all_usable = [sec302, sec303]
    exact_index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable}

    citation_303 = ExtractedCitation(
        provision_type="Section", provision_number="303", subsection=None,
        act_raw="the Indian Penal Code, 1860", act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    result = match_evidence(citation_303, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.evidence.canonical_text == "Murder by life-convict text."  # never sec302's text

    # A number with NO evidence record at all (304) must be NO_EVIDENCE,
    # never silently fall back to its numeric neighbour.
    citation_304 = ExtractedCitation(
        provision_type="Section", provision_number="304", subsection=None,
        act_raw="the Indian Penal Code, 1860", act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    result_304 = match_evidence(citation_304, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result_304.matched is False


def test_evidence_matcher_year_edition_collision_stays_unmatched():
    """Two editions of an Act with the same short name but different years
    (e.g. Income Tax Act, 1922 vs 1961) are DIFFERENT acts —
    normalize_act() keeps the year as part of act_norm, so a claim citing
    the wrong edition's year must not silently fall back to the other
    edition's text, even though the section number and Act family name
    otherwise match closely."""
    itax_1961 = _make_evidence("Section", "8", "The Income Tax Act, 1961", text="1961-edition section 8 text.")
    all_usable = [itax_1961]
    exact_index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable}

    citation_1922 = ExtractedCitation(
        provision_type="Section", provision_number="8", subsection=None,
        act_raw="The Indian Income Tax Act, 1922", act_norm=normalize_act("The Indian Income Tax Act, 1922"),
    )
    result = match_evidence(citation_1922, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    # "indian income tax act 1922" (4 significant words: indian/income/tax/act)
    # vs "income tax act 1961" (3: income/tax/act) -> Jaccard overlap 3/4 =
    # 0.75, below the 0.8 fuzzy threshold -- correctly stays unmatched. This
    # is a real, previously-observed case (a genuinely different Act edition,
    # not a normalization near-miss), not a hypothetical.
    assert result.matched is False, "a 1922 citation must never resolve to the 1961 edition's text"


# ---------------------------------------------------------------------------
# Real-data checks against the (read-only) evidence files. Skipped if the
# files aren't present rather than failing the whole suite in an
# unexpected environment.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not CANONICAL_PATH.exists() or not AUDIT_PATH.exists(), reason="evidence files not found")
def test_real_evidence_loader_excludes_non_usable_verdicts():
    exact_index, all_usable = load_usable_evidence(
        CANONICAL_PATH, AUDIT_PATH, {"VERIFIED_EXACT", "VERIFIED_CONTENT"}
    )
    # From evidence_audit.jsonl (see research/data/evidence/README.md):
    # 25 VERIFIED_EXACT + 34 VERIFIED_CONTENT = 59 usable; 1 INVALID,
    # 1 UNRESOLVED, 2 SOURCE_ONLY must never appear.
    assert len(all_usable) == 59
    keys = {e.dataset_citation_key for e in all_usable}
    assert "Section 100 in The Code of Civil Procedure, 1908" not in keys  # INVALID
    assert "Section 161 in The Indian Penal Code, 1860" not in keys        # UNRESOLVED
    assert "Section 25 in The Arms Act, 1959" not in keys                  # SOURCE_ONLY
    assert "Section 5 in The Limitation Act, 1963" not in keys             # SOURCE_ONLY


@pytest.mark.skipif(not CANONICAL_PATH.exists() or not AUDIT_PATH.exists(), reason="evidence files not found")
def test_real_evidence_known_good_record_is_present_and_correct():
    exact_index, all_usable = load_usable_evidence(
        CANONICAL_PATH, AUDIT_PATH, {"VERIFIED_EXACT", "VERIFIED_CONTENT"}
    )
    key = ("Section", "302", None, normalize_act("The Indian Penal Code, 1860"))
    assert key in exact_index
    rec = exact_index[key]
    assert "murder" in rec.canonical_text.lower()
    assert rec.audit_verdict in ("VERIFIED_EXACT", "VERIFIED_CONTENT")


# ---------------------------------------------------------------------------
# v1 evidence supplement (opt-in merge) — Priority 1/6 of the CPU pre-GPU
# optimization pass. v0-only behaviour (no extra_* args) must be completely
# unaffected; the merge must be additive, and the 3 known v1 corrections
# must replace their v0 counterparts, never merely add alongside them.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not CANONICAL_V1_PATH.exists() or not AUDIT_V1_PATH.exists(),
                     reason="v1 evidence supplement not built")
def test_v0_only_call_unaffected_by_v1_files_existing():
    """Merely having v1 files ON DISK must not change v0-only behaviour —
    load_usable_evidence() without extra_* args is byte-for-byte the same
    as before v1 was ever built."""
    exact_index, all_usable = load_usable_evidence(
        CANONICAL_PATH, AUDIT_PATH, {"VERIFIED_EXACT", "VERIFIED_CONTENT"}
    )
    assert len(all_usable) == 59


@pytest.mark.skipif(not CANONICAL_V1_PATH.exists() or not AUDIT_V1_PATH.exists(),
                     reason="v1 evidence supplement not built")
def test_v1_merge_expands_pool_and_applies_corrections():
    exact_index, all_usable = load_usable_evidence(
        CANONICAL_PATH, AUDIT_PATH, {"VERIFIED_EXACT", "VERIFIED_CONTENT"},
        extra_canonical_path=CANONICAL_V1_PATH, extra_audit_path=AUDIT_V1_PATH,
    )
    # Pool expands substantially (see research/data/evidence/README_v1.md).
    assert len(all_usable) > 100

    keys = {e.dataset_citation_key for e in all_usable}
    # The 2 v0 INVALID/UNRESOLVED records are now present via their v1
    # CORRECTED replacements (different source_url than the old bad one).
    assert "Section 100 in The Code of Civil Procedure, 1908" in keys
    assert "Section 161 in The Indian Penal Code, 1860" in keys
    corrected = exact_index[("Section", "100", None, normalize_act("The Code of Civil Procedure, 1908"))]
    assert corrected.source_url != "https://indiankanoon.org/doc/143489098/"  # the old INVALID URL

    # A genuinely new v1 citation is present and correctly resolved.
    assert "Section 498A in The Indian Penal Code, 1860" in keys
    new_rec = exact_index[("Section", "498A", None, normalize_act("The Indian Penal Code, 1860"))]
    assert "cruelty" in new_rec.canonical_text.lower()

    # v1's SOURCE_ONLY records must NOT be usable under the default verdict
    # set, exactly like v0's own SOURCE_ONLY records — the filtering
    # happens at load time, so a SOURCE_ONLY key never even enters the
    # index.
    assert ("Section", "145", None, normalize_act("The Code of Criminal Procedure, 1973")) not in exact_index


def test_load_usable_evidence_from_config_defaults_to_v0_only():
    config = {
        "paths": {
            "canonical_statutes": "research/data/evidence/canonical_statutes.jsonl",
            "evidence_audit": "research/data/evidence/evidence_audit.jsonl",
            "canonical_statutes_v1": "research/data/evidence/canonical_statutes_v1.jsonl",
            "evidence_audit_v1": "research/data/evidence/evidence_audit_v1.jsonl",
        },
        "usable_evidence_verdicts": ["VERIFIED_EXACT", "VERIFIED_CONTENT"],
        # "use_evidence_v1" deliberately absent -> must default to False
    }
    exact_index, all_usable = load_usable_evidence_from_config(config, REPO_ROOT)
    assert len(all_usable) == 59


@pytest.mark.skipif(not CANONICAL_V1_PATH.exists() or not AUDIT_V1_PATH.exists(),
                     reason="v1 evidence supplement not built")
def test_load_usable_evidence_from_config_opt_in_expands_pool():
    config = {
        "paths": {
            "canonical_statutes": "research/data/evidence/canonical_statutes.jsonl",
            "evidence_audit": "research/data/evidence/evidence_audit.jsonl",
            "canonical_statutes_v1": "research/data/evidence/canonical_statutes_v1.jsonl",
            "evidence_audit_v1": "research/data/evidence/evidence_audit_v1.jsonl",
        },
        "usable_evidence_verdicts": ["VERIFIED_EXACT", "VERIFIED_CONTENT"],
        "use_evidence_v1": True,
    }
    exact_index, all_usable = load_usable_evidence_from_config(config, REPO_ROOT)
    assert len(all_usable) > 100


# ---------------------------------------------------------------------------
# Priority 3 (evidence matching robustness): every REAL same-provision-
# number collision across different Acts in the expanded (v0+v1) corpus —
# e.g. Section 3 exists under 5 different Acts, Section 302 under both IPC
# and CrPC — must have act-name token overlap safely below the fuzzy
# threshold, so the fuzzy fallback can never cross-match the wrong Act's
# evidence for a shared section number. This is exercised against the
# REAL corpus (not synthetic examples), because the corpus itself is the
# actual adversarial surface: a bigger corpus creates more opportunities
# for this exact failure mode, so the safety property must be checked on
# the corpus as it actually is, not just a hand-picked example.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not CANONICAL_V1_PATH.exists() or not AUDIT_V1_PATH.exists(),
                     reason="v1 evidence supplement not built")
def test_no_cross_act_fuzzy_collision_risk_anywhere_in_expanded_corpus():
    """For every (provision_type, provision_number) shared by 2+ different
    Acts in the real v0+v1 corpus, the token overlap between any two of
    those Acts' names must stay below the fuzzy_token_overlap_threshold —
    otherwise a citation with an unresolved/ambiguous act_norm could, in
    principle, fuzzy-match the WRONG Act's evidence for that same number.
    A single query using the CORRECT act_norm still exact-matches instantly
    (exact_index lookup, unaffected) — this test is specifically about the
    fuzzy FALLBACK path's blast radius."""
    from collections import defaultdict
    from src.claim_parser import act_significant_words
    from src.evidence_matcher import _token_overlap
    import yaml

    config = yaml.safe_load((REPO_ROOT / "research/prototype/config/prototype.yaml").read_text(encoding="utf-8"))
    config["use_evidence_v1"] = True
    _, all_usable = load_usable_evidence_from_config(config, REPO_ROOT)
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    by_number = defaultdict(set)
    for e in all_usable:
        by_number[(e.provision_type, e.provision_number)].add(e.act_norm)
    collisions = {k: v for k, v in by_number.items() if len(v) > 1}
    assert len(collisions) >= 10, "expected the expanded corpus to contain real cross-act collisions to test against"

    violations = []
    for (ptype, pnum), acts in collisions.items():
        acts = sorted(acts)
        for i in range(len(acts)):
            for j in range(i + 1, len(acts)):
                overlap = _token_overlap(act_significant_words(acts[i]), act_significant_words(acts[j]))
                if overlap >= fuzzy_threshold:
                    violations.append((ptype, pnum, acts[i], acts[j], overlap))

    assert violations == [], f"cross-act fuzzy-collision risk found: {violations}"
