"""
Regression tests for the "respectively" structured-span mechanism
(src/claim_parser.py: `_assign_respectively_spans`, `Claim.assertion_spans`).

Covers every required pattern from the design brief:
  1. simple "A and B respectively X and Y"
  2. multiple statutory citations (different Acts)
  3. multiple provisions under one Act
  4. citation order matching
  5. malformed/ambiguous respectively constructions
  6. cases where the mapping cannot be proven (fail closed)

No GPU, no model. Every assertion here is about STRUCTURE (which verbatim
substrings ended up in assertion_spans), never about verification/
correction quality — that is exercised in test_pipeline_mock.py's
atomic_scope_check tests.
"""
from src.claim_parser import extract_claims


# ---------------------------------------------------------------------------
# 1. Simple "A and B ... respectively" (2 citations, trailing form)
# ---------------------------------------------------------------------------

def test_simple_two_citation_respectively_trailing_form():
    s = ("The case is governed by Sections 300 and 324 of the Indian Penal Code (IPC), "
         "which require that the act must be done with the intention to cause death or "
         "injury, and the act must result in causing death or injury, respectively.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["300"].assertion_spans == [
        "300", "require that the act must be done with the intention to cause death or injury"
    ]
    assert by_num["324"].assertion_spans == ["324", "the act must result in causing death or injury"]


def test_simple_two_citation_respectively_prefix_form():
    s = ("Sections 406 and 420 of the Indian Penal Code, 1860, which respectively deal "
         "with criminal breach of trust and cheating.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["406"].assertion_spans == ["406", "criminal breach of trust"]
    assert by_num["420"].assertion_spans == ["420", "cheating"]


# ---------------------------------------------------------------------------
# 2. Multiple statutory citations across DIFFERENT Acts
# ---------------------------------------------------------------------------

def test_respectively_across_different_acts():
    s = ("The case relies on Section 302 of the Indian Penal Code, 1860 and Section 25 "
         "of the Arms Act, 1959, which respectively deal with murder and illegal "
         "possession of firearms.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["302"].citation_extracted.act_norm == "indian penal code 1860"
    assert by_num["25"].citation_extracted.act_norm == "arms act 1959"
    assert by_num["302"].assertion_spans == ["302", "murder"]
    assert by_num["25"].assertion_spans == ["25", "illegal possession of firearms"]


# ---------------------------------------------------------------------------
# 3. Multiple provisions under ONE Act (the flagship 1991_110 shape)
# ---------------------------------------------------------------------------

def test_flagship_1991_110_four_provisions_one_act():
    """The exact real sentence from document 1991_110 that produced this
    project's only genuine natural-data CONTRADICTED catch (bare framing
    missed the Section 149 mislabeling at 0.998 confidence; labeled framing
    correctly flagged it) — and whose correction attempt was blocked as a
    scope violation under the legacy (and Phase-1 assertion_text) checks."""
    s = ("The case was governed by sections 302, 149, 323, and 34 of the Indian Penal "
         "Code, 1860, which respectively deal with murder, criminal conspiracy, "
         "voluntarily causing hurt, and abetting the commission of a non-cognizable "
         "offense.")
    claims = extract_claims(s)
    assert len(claims) == 4
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert set(by_num) == {"302", "149", "323", "34"}
    assert all(c.citation_extracted.act_norm == "indian penal code 1860" for c in claims)

    assert by_num["302"].assertion_spans == ["302", "murder"]
    assert by_num["149"].assertion_spans == ["149", "criminal conspiracy"]
    assert by_num["323"].assertion_spans == ["323", "voluntarily causing hurt"]
    assert by_num["34"].assertion_spans == [
        "34", "abetting the commission of a non-cognizable offense"
    ]

    # No fabrication: every fragment is a genuine, findable substring of
    # the original sentence — nothing was recombined or reworded.
    for c in claims:
        for fragment in c.assertion_spans:
            assert fragment in s


# ---------------------------------------------------------------------------
# 4. Citation order matching — items must pair with citations IN ORDER,
#    never by content-guessing or reordering.
# ---------------------------------------------------------------------------

def test_citation_order_matching_not_content_matching():
    # Deliberately distinguishable, non-legally-meaningful placeholder
    # items so a test failure here can only mean order was NOT respected
    # positionally (there is no other way these could be "guessed right").
    s = ("Sections 111 and 222 of the Indian Penal Code, 1860, which respectively "
         "deal with alpha-item and beta-item.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["111"].assertion_spans[1] == "alpha-item"
    assert by_num["222"].assertion_spans[1] == "beta-item"


def test_citation_order_matching_three_way():
    s = ("Sections 10, 20, and 30 of the Industrial Disputes Act, 1947, which "
         "respectively deal with first-topic, second-topic, and third-topic.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["10"].assertion_spans[1] == "first-topic"
    assert by_num["20"].assertion_spans[1] == "second-topic"
    assert by_num["30"].assertion_spans[1] == "third-topic"


# ---------------------------------------------------------------------------
# 5. Malformed / ambiguous respectively constructions -> fail closed
#    (assertion_spans stays at its safe default, [assertion_text])
# ---------------------------------------------------------------------------

def test_multiple_respectively_occurrences_declines():
    s = ("Sections 10 and 20 of the Act, which respectively deal with A and B, "
         "and Sections 30 and 40, which respectively deal with C and D.")
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_spans == [c.assertion_text]  # default, un-narrowed


def test_no_which_anchor_declines():
    # "respectively" present, but no "which" to anchor the items zone.
    s = "Sections 10 and 20 of the Act apply to this case, respectively."
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_spans == [c.assertion_text]


def test_multiple_which_occurrences_declines():
    s = ("Sections 10 and 20 of the Act, which is old, which respectively deal with "
         "A and B.")
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_spans == [c.assertion_text]


def test_single_citation_sentence_never_engages_respectively_logic():
    s = "Section 302 of the Indian Penal Code, 1860, which respectively deals with murder."
    claims = extract_claims(s)
    assert len(claims) == 1
    assert claims[0].assertion_spans == [claims[0].assertion_text]


# ---------------------------------------------------------------------------
# 6. Mapping cannot be proven -> fail closed (item count mismatch, etc.)
# ---------------------------------------------------------------------------

def test_item_count_mismatch_declines():
    # 3 citations, but only 2 items in the trailing list.
    s = ("Sections 10, 20, and 30 of the Act, which respectively deal with "
         "first-topic and second-topic.")
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_spans == [c.assertion_text]


def test_item_count_exceeds_citation_count_declines():
    # 2 citations, but 3 items (e.g. an "and" inside one item over-split it).
    s = ("Sections 10 and 20 of the Act, which respectively deal with "
         "first-topic, second-topic, and third-topic.")
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_spans == [c.assertion_text]


def test_empty_items_zone_declines():
    s = "Sections 10 and 20 of the Act, which respectively."
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_spans == [c.assertion_text]


def test_citation_keyword_boundary_split_isolates_per_citation_clauses():
    """Real sentence from document 1997_1306, batch-2 natural GPU
    experiment: a comma-separated list of full clauses, each STARTING
    with its own citation mention, no semicolon and no 'while'. Confirmed
    against the real correction attempt: editing Section 148's own clause
    ('criminal trespass' -> 'rioting', matching real IPC content) used to
    be rejected as a scope violation under legacy AND the pre-existing
    assertion_text mechanisms; this new split unblocks it (see
    test_pipeline_mock.py's dedicated end-to-end test)."""
    s = ("Section 148 mandates punishment for criminal trespass, section 304 (Part-I) "
         "and 304 (Part-II) deal with culpable homicide not amounting to murder and "
         "voluntary manslaughter respectively, section 323 prescribes punishment for "
         "voluntarily causing hurt, and section 149 provides for the liability of every "
         "member of an unlawful assembly to the acts done by any one of them in the "
         "common object of the assembly.")
    claims = extract_claims(s)
    by_key = {(c.citation_extracted.provision_number, c.citation_extracted.subsection): c for c in claims}
    assert by_key[("148", None)].assertion_text == "Section 148 mandates punishment for criminal trespass"
    assert by_key[("323", None)].assertion_text == "section 323 prescribes punishment for voluntarily causing hurt"
    assert by_key[("149", None)].assertion_text.startswith("section 149 provides for the liability")
    # 304 Part-I and Part-II share one clause (no further separator between
    # them) -> both get that shared, still-narrower-than-full-sentence clause.
    shared_304_clause = by_key[("304", "Part-I")].assertion_text
    assert shared_304_clause == by_key[("304", "Part-II")].assertion_text
    assert shared_304_clause.startswith("section 304 (Part-I) and 304 (Part-II) deal with")
    # No fabrication: every assertion_text is a genuine substring of s.
    for c in claims:
        assert c.assertion_text in s


def test_citation_keyword_boundary_split_does_not_fragment_internal_and():
    """The split must cut ONLY before a new citation keyword, not on every
    comma/'and' — internal connectors inside one clause ('304 (Part-I)
    AND 304 (Part-II)', 'murder AND voluntary manslaughter') must not
    produce spurious extra clause boundaries."""
    s = ("Section 10 covers alpha and beta, section 20 covers gamma and delta.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["10"].assertion_text == "Section 10 covers alpha and beta"
    assert by_num["20"].assertion_text == "section 20 covers gamma and delta."


def test_already_resolved_by_earlier_pass_is_not_overridden():
    """If while-split (or another Phase-1 mechanism) already narrowed a
    sentence's citations, the respectively pass must decline entirely
    (not partially re-apply against citations another mechanism already
    reasoned about) — this sentence has both 'while' and 'respectively'."""
    s = ("Section 302 prescribes the punishment for murder, while Section 34 "
         "deals with criminal liability, respectively, for related persons.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    # while-split already resolved these via assertion_text; respectively
    # must not have touched assertion_spans beyond the [assertion_text] default.
    assert by_num["302"].assertion_spans == [by_num["302"].assertion_text]
    assert by_num["34"].assertion_spans == [by_num["34"].assertion_text]
