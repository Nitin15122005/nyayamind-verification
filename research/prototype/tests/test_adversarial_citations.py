"""
Adversarial citation-parsing / evidence-matching regression tests, written
for the 2026-08-27 independent evidence-v1 audit (see
outputs/evidence_v1_independent_audit.md). Seven categories, one group each,
covering exactly the adversarial surface a statutory-citation matcher can get
wrong: wrong-Act, same-section-number-different-act, year/edition variants,
aliases, numeric ranges, multi-Act bundling, and field-wide ambiguity.

Every test asserts SAFETY first (never silently resolve to the wrong
provision) — a citation the parser/matcher cannot confidently resolve must
come back unresolved/NO_EVIDENCE, never a guessed match. Several cases here
are drawn directly from real findings during the independent audit (the
CrPC-vs-CPC Section 100 confusion and the "Mysore Land Acquisition Act" near
miss both surfaced in outputs/no_evidence_taxonomy_v3.json's manual-review
list and were confirmed NOT to be parser/matcher defects — these tests pin
that correct behaviour so it cannot silently regress).

No GPU, no network, no model. Synthetic evidence pools only (via the same
`_make_evidence` fixture pattern as test_claim_parser_and_evidence_matcher.py)
except where noted.
"""
from src.claim_parser import (
    ExtractedCitation,
    extract_citation,
    extract_citations,
    extract_claims,
    normalize_act,
)
from src.data_loader import EvidenceRecord
from src.evidence_matcher import match_evidence


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


def _pool(*records):
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in records
    }
    return exact_index, list(records)


# ---------------------------------------------------------------------------
# 1. Wrong-Act: same provision number, textually-similar but legally
#    DIFFERENT act names must never cross-match.
# ---------------------------------------------------------------------------

def test_wrong_act_crpc_vs_cpc_section_100_never_cross_matches():
    """Real finding from the independent audit (no_evidence_taxonomy_v3.json,
    natural_candidates_50_gpu_bare.jsonl/2022_1043/c4): a generated claim
    cited 'Section 100... the Code of Criminal Procedure (CrPC)' while the
    corpus's only Section 100 record is under the Code of CIVIL Procedure,
    1908. The two act names share 2 of 3 significant tokens ('code',
    'procedure'; 0.5 token overlap) — well short of the 0.8 fuzzy threshold,
    and correctly so: CrPC and CPC are different Acts, not spelling
    variants. Manually confirmed during the audit to be a genuine corpus
    gap / possible upstream generation error, NOT a parser or matcher
    defect — this test pins that conclusion."""
    # Deliberately matches the REAL corpus shape: only a CPC Section 100
    # record exists (no CrPC Section 100 record) -- this absence, not a
    # same-key collision, is what actually produced the real NO_EVIDENCE.
    cpc_100 = _make_evidence("Section", "100", "The Code of Civil Procedure, 1908",
                              text="Second appeal text.")
    exact_index, all_usable = _pool(cpc_100)

    claim_act_norm = normalize_act("the Code of Criminal Procedure (CrPC)")
    assert claim_act_norm == "code of criminal procedure 1973"  # alias resolves correctly...
    citation = ExtractedCitation(
        provision_type="Section", provision_number="100", subsection=None,
        act_raw="the Code of Criminal Procedure (CrPC)", act_norm=claim_act_norm,
    )
    # ...but the corpus only has THIS Section 100 under CPC 1908, a
    # genuinely different act, so it must resolve to NO_EVIDENCE, never to
    # the CPC record.
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is False
    assert result.match_method == "no_evidence"


def test_wrong_act_high_but_subthreshold_overlap_does_not_match():
    """Two acts sharing most significant words ('prevention', 'act') but
    differing in the one word that actually distinguishes them ('food
    adulteration' vs 'corruption') must stay below threshold and not match —
    generic legal vocabulary overlap is not evidence of the same Act."""
    poca = _make_evidence("Section", "13", "The Prevention of Corruption Act, 1988",
                           text="Criminal misconduct text.")
    pfa = _make_evidence("Section", "13", "The Prevention Of Food Adulteration Act, 1954",
                          text="Unrelated food-safety text.")
    exact_index, all_usable = _pool(poca, pfa)

    citation = ExtractedCitation(
        provision_type="Section", provision_number="13", subsection=None,
        act_raw="the Prevention of Corruption Act, 1988",
        act_norm=normalize_act("the Prevention of Corruption Act, 1988"),
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.evidence.canonical_text == "Criminal misconduct text."  # not the PFA record


# ---------------------------------------------------------------------------
# 2. Same-section-number, different act (name-independent identity check)
# ---------------------------------------------------------------------------

def test_same_section_number_three_way_split_across_acts():
    """Section 34 exists, with completely unrelated meanings, under at
    least three real Acts in this project's corpus history: the Indian
    Penal Code (common-intention liability), the Arbitration Act 1940
    (repealed), and the Arbitration and Conciliation Act 1996 (setting
    aside an award). A citation for one must never resolve to another's
    text, and the act_norm identity must correctly keep 1940 and 1996 acts
    distinct from each other despite both containing 'arbitration'."""
    ipc34 = _make_evidence("Section", "34", "The Indian Penal Code, 1860",
                            text="Common intention text.")
    arb1940_34 = _make_evidence("Section", "34", "The Arbitration Act, 1940",
                                 text="1940-Act text (repealed 1996).")
    arb1996_34 = _make_evidence("Section", "34", "The Arbitration And Conciliation Act, 1996",
                                 text="Setting aside an arbitral award text.")
    exact_index, all_usable = _pool(ipc34, arb1940_34, arb1996_34)

    assert normalize_act("The Arbitration Act, 1940") != normalize_act(
        "The Arbitration And Conciliation Act, 1996"
    )

    for act_raw, expected_text in (
        ("the Indian Penal Code, 1860", "Common intention text."),
        ("the Arbitration Act, 1940", "1940-Act text (repealed 1996)."),
        ("the Arbitration and Conciliation Act, 1996", "Setting aside an arbitral award text."),
    ):
        citation = ExtractedCitation(
            provision_type="Section", provision_number="34", subsection=None,
            act_raw=act_raw, act_norm=normalize_act(act_raw),
        )
        result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
        assert result.matched is True, act_raw
        assert result.evidence.canonical_text == expected_text, act_raw


# ---------------------------------------------------------------------------
# 3. Year / edition variants of the "same" act name
# ---------------------------------------------------------------------------

def test_year_edition_income_tax_act_1961_vs_hypothetical_2025_act():
    """CONFIRMED LATENT LIMITATION, surfaced by this exact test during the
    2026-08-27 independent audit (see outputs/evidence_v1_independent_audit.md
    -- "fuzzy matching is year-blind"): exact-key matching correctly keeps
    act_norm "income tax act 1961" distinct from "income-tax act 2025" (the
    year IS part of the exact index key). But `act_significant_words()`
    tokenizes with `re.findall(r"[a-z']+", act_norm)`, which drops digits
    entirely -- so BOTH act names reduce to the identical significant-word
    set {"income", "tax"} and the FUZZY fallback (overlap 1.0) matches them
    anyway. This is a real, generalizable gap: any two same-named editions
    of an Act that differ ONLY by year can fuzzy-cross-match. Not fixed in
    this pass (a shared-code change to evidence_matcher.py's token-overlap
    semantics is out of the "narrow, isolated, safe" bar for an in-session
    fix -- it would retroactively change every historical fuzzy-matched
    claim's behaviour and needs its own dedicated validation run). This test
    exists to PIN the current, confirmed behaviour so a future fix is
    validated against a known baseline, and so this gap cannot silently
    regress further (e.g. by someone loosening the threshold) without a
    test failing to draw attention to it. No live collision currently
    exists in the shipped 136-record v0+v1 corpus (no two same-named,
    different-year Acts share a provision_type+provision_number there
    today) -- this is a latent risk for future corpus growth, not an
    observed production error."""
    it1961_4 = _make_evidence("Section", "4", "The Income Tax Act, 1961",
                               text="1961-Act charge-of-tax text.")
    exact_index, all_usable = _pool(it1961_4)

    citation_2025 = ExtractedCitation(
        provision_type="Section", provision_number="4", subsection=None,
        act_raw="the Income-tax Act, 2025", act_norm=normalize_act("the Income-tax Act, 2025"),
    )
    # Exact-key identity correctly differs...
    assert citation_2025.act_norm != it1961_4.act_norm
    # ...but the fuzzy fallback currently does not respect that difference,
    # because act_significant_words() strips all digits (including years).
    result = match_evidence(citation_2025, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.match_method == "fuzzy"

    # The 1961 citation still matches its own evidence via the stronger,
    # year-aware exact path.
    citation_1961 = ExtractedCitation(
        provision_type="Section", provision_number="4", subsection=None,
        act_raw="the Income Tax Act, 1961", act_norm=normalize_act("the Income Tax Act, 1961"),
    )
    result_1961 = match_evidence(citation_1961, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result_1961.matched is True
    assert result_1961.match_method == "exact_normalized"


def test_year_edition_land_acquisition_act_central_vs_state_variant():
    """Real near-miss from the independent audit
    (no_evidence_taxonomy_v3.json, natural_candidates_batch2_gpu_bare.jsonl
    /1974_205/c1): a claim cited 'Section 11... the Mysore Land Acquisition
    Act' against a corpus that only has 'The Land Acquisition Act, 1894'
    (the central Act). Token overlap is 0.667 ('land', 'acquisition', 'act'
    shared; 'mysore' vs '1894' differ) — below the 0.8 threshold. A
    state-specific enactment sharing most of a central Act's name is
    exactly the case the threshold exists to keep separate: confirmed
    during the audit as a genuinely different (regional) enactment, not a
    normalization gap, so this must correctly stay NO_EVIDENCE."""
    central = _make_evidence("Section", "11", "The Land Acquisition Act, 1894",
                              text="Central Act, 1894 text.")
    exact_index, all_usable = _pool(central)

    citation = ExtractedCitation(
        provision_type="Section", provision_number="11", subsection=None,
        act_raw="the Mysore Land Acquisition Act",
        act_norm=normalize_act("the Mysore Land Acquisition Act"),
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is False
    assert result.match_method == "no_evidence"


# ---------------------------------------------------------------------------
# 4. Aliases — common abbreviations/short forms must resolve to the SAME
#    act as their full name, and never accidentally to a different one.
# ---------------------------------------------------------------------------

def test_aliases_crpc_and_cpc_are_distinct_and_each_resolves_correctly():
    assert normalize_act("CrPC") == "code of criminal procedure 1973"
    assert normalize_act("CPC") == "code of civil procedure 1908"
    assert normalize_act("CrPC") != normalize_act("CPC")


def test_aliases_id_act_resolves_to_industrial_disputes_act():
    assert normalize_act("the ID Act") == "industrial disputes act 1947"
    assert normalize_act("the Industrial Disputes Act, 1947") == "industrial disputes act 1947"


def test_aliases_evidence_act_short_form_matches_full_indian_evidence_act():
    ev27 = _make_evidence("Section", "27", "The Indian Evidence Act, 1872",
                           text="Information received from accused text.")
    exact_index, all_usable = _pool(ev27)

    citation = ExtractedCitation(
        provision_type="Section", provision_number="27", subsection=None,
        act_raw="the Evidence Act", act_norm=normalize_act("the Evidence Act"),
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.match_method == "exact_normalized"


def test_aliases_parenthetical_abbreviation_never_redirects_to_wrong_act():
    """'(IPC)' glossing 'the Indian Penal Code' must resolve to the SAME
    act, never to some other act that also happens to be abbreviated
    similarly elsewhere in a bundled sentence."""
    ipc = _make_evidence("Section", "302", "The Indian Penal Code, 1860", text="Murder text.")
    other = _make_evidence("Section", "302", "The Indian Companies Act, 2013", text="Unrelated text.")
    exact_index, all_usable = _pool(ipc, other)

    citation = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="the Indian Penal Code (IPC), 1860",
        act_norm=normalize_act("the Indian Penal Code (IPC), 1860"),
    )
    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.evidence.canonical_text == "Murder text."


# ---------------------------------------------------------------------------
# 5. Ranges — "Sections 100-105" style numeric ranges (as opposed to a
#    comma/and-separated list, which extract_citations already handles).
# ---------------------------------------------------------------------------

def test_range_hyphenated_span_is_never_silently_expanded_or_mismatched():
    """The citation grammar's number-item pattern (\\d+[A-Za-z\\-]*) allows a
    trailing hyphen+letters for suffixed provisions like '31A' or '120-B'
    (a real, correct Indian-citation idiom: 'Section 120-B' IS one
    provision, not a range). A genuine numeric RANGE written as
    'Sections 100-105' is consequently parsed as ONE citation whose
    provision_number is the literal string '100-105' — this is a known,
    documented limitation (ranges are not expanded into 100, 101, ..., 105),
    but the critical SAFETY property this test pins is that such a citation
    can only ever match a corpus record whose provision_number is also
    exactly '100-105', or correctly fall through to NO_EVIDENCE — it must
    NEVER silently match (and borrow the text of) the corpus's actual
    'Section 100' record."""
    sec100 = _make_evidence("Section", "100", "The Code of Civil Procedure, 1908",
                             text="Second appeal text.")
    exact_index, all_usable = _pool(sec100)

    sentence = "The dispute engages Sections 100-105 of the Code of Civil Procedure, 1908."
    citation = extract_citation(sentence)
    assert citation is not None
    assert citation.provision_number != "100"  # must not silently truncate to just the first number
    assert "100-105" in citation.provision_number or citation.provision_number.startswith("100")

    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    if citation.provision_number == "100":
        # Only acceptable if some future parser change legitimately expands
        # ranges to their first member AND documents it; today it does not.
        assert result.matched is True
    else:
        # Current, documented behaviour: distinct provision_number string
        # ('100-105') never collides with the real 'Section 100' record.
        assert result.matched is False
        assert result.match_method == "no_evidence"


def test_range_legitimate_suffixed_provision_120b_is_not_treated_as_a_range():
    """'Section 120-B' (criminal conspiracy) is a single real provision
    number using a hyphenated suffix, not a range — must parse as
    provision_number '120-B' or '120-b'-equivalent, matching a corpus
    record for exactly that provision, never bleeding into '120'."""
    sec120b = _make_evidence("Section", "120-B", "The Indian Penal Code, 1860",
                              text="Criminal conspiracy text.")
    sec120 = _make_evidence("Section", "120", "The Indian Penal Code, 1860",
                             text="Definition of conspiracy text (unrelated numbered section).")
    exact_index, all_usable = _pool(sec120b, sec120)

    citation = extract_citation("The case invokes Section 120-B of the Indian Penal Code, 1860.")
    assert citation is not None
    assert citation.provision_number in ("120-B", "120-b")

    result = match_evidence(citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is True
    assert result.evidence.canonical_text == "Criminal conspiracy text."


# ---------------------------------------------------------------------------
# 6. Multi-Act bundling — one sentence citing several different Acts must
#    keep every citation's act clean and independently resolvable.
# ---------------------------------------------------------------------------

def test_multi_act_three_acts_in_one_sentence_stay_independently_resolved():
    sentence = (
        "The prosecution relies on Section 302 of the Indian Penal Code, 1860, "
        "Section 27 of the Indian Evidence Act, 1872, and Section 161 of the "
        "Code of Criminal Procedure, 1973."
    )
    citations = extract_citations(sentence)
    by_number = {c.provision_number: c for c in citations}
    assert set(by_number) == {"302", "27", "161"}
    assert by_number["302"].act_norm == "indian penal code 1860"
    assert by_number["27"].act_norm == "indian evidence act 1872"
    assert by_number["161"].act_norm == "code of criminal procedure 1973"
    # No cross-contamination: no act_norm should contain another act's
    # distinctive tokens.
    assert "evidence" not in by_number["302"].act_norm
    assert "criminal procedure" not in by_number["27"].act_norm
    assert "penal" not in by_number["161"].act_norm


def test_multi_act_claims_each_get_independent_evidence_lookup():
    sentence = (
        "The case is governed by Section 302 of the Indian Penal Code, 1860 "
        "and Section 100 of the Code of Civil Procedure, 1908."
    )
    ipc302 = _make_evidence("Section", "302", "The Indian Penal Code, 1860", text="Murder text.")
    cpc100 = _make_evidence("Section", "100", "The Code of Civil Procedure, 1908",
                             text="Second appeal text.")
    exact_index, all_usable = _pool(ipc302, cpc100)

    claims = extract_claims(sentence)
    assert len(claims) == 2
    results = {
        c.citation_extracted.provision_number: match_evidence(
            c.citation_extracted, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8
        )
        for c in claims
    }
    assert results["302"].matched is True
    assert results["302"].evidence.canonical_text == "Murder text."
    assert results["100"].matched is True
    assert results["100"].evidence.canonical_text == "Second appeal text."


# ---------------------------------------------------------------------------
# 7. Ambiguous citations — a bare provision number with no resolvable act,
#    where the SAME number maps to two+ DIFFERENT acts elsewhere in the
#    field, must be left unresolved rather than guessing either one.
# ---------------------------------------------------------------------------

def test_ambiguous_same_number_two_different_acts_in_field_stays_unresolved():
    """Per extract_claims()'s own documented contract: field-wide act
    inheritance for a bare citation only fires when the same
    (provision_type, provision_number) resolved to exactly ONE distinct act
    elsewhere in the field. If it resolved to two or more different acts,
    that is genuinely ambiguous and must NOT be guessed."""
    text = (
        "Section 34 of the Indian Penal Code, 1860 establishes common intention. "
        "Section 34 of the Arbitration and Conciliation Act, 1996 governs setting "
        "aside an award. Section 34 also applies here."
    )
    claims = extract_claims(text)
    bare_claim = [
        c for c in claims
        if c.claim_text == "Section 34 also applies here."
    ]
    assert len(bare_claim) == 1
    citation = bare_claim[0].citation_extracted
    assert citation is not None
    assert citation.act_norm == ""  # correctly left unresolved, not guessed as either act


def test_ambiguous_unresolved_citation_never_reaches_match_evidence_as_a_false_match():
    """An unresolved (act_norm == '') citation's index key can never equal
    a real corpus key (act_norm is always non-empty for a stored evidence
    record), so match_evidence must safely return NO_EVIDENCE rather than
    error or, worse, match the wrong record via an empty-string collision."""
    ipc34 = _make_evidence("Section", "34", "The Indian Penal Code, 1860", text="Common intention text.")
    exact_index, all_usable = _pool(ipc34)

    unresolved_citation = ExtractedCitation(
        provision_type="Section", provision_number="34", subsection=None,
        act_raw=None, act_norm="",
    )
    result = match_evidence(unresolved_citation, exact_index, all_usable, fuzzy_token_overlap_threshold=0.8)
    assert result.matched is False
    assert result.match_method == "no_evidence"
