"""
Regression tests for a real citation-coverage bug found by scanning every
unique Qwen-generated `statutory_grounding` text already committed under
outputs/*.jsonl (181 unique texts, collected across every run_A/B/C,
natural_candidates, framing_comparison, and final_gpu_validation output
file) for sentence-segmentation and citation-extraction failures.

Bug: the generator sometimes abbreviates "Article"/"Articles" as
"Art."/"Arts." (e.g. "Art. 32", "Art.227", "Arts. 14 and 19"). Before this
fix, TWO independent problems compounded:
  1. split_sentences() had no abbreviation awareness at all and split on
     every ". " + capital-letter, so "...Art. 32... Art. 136..." shattered
     one real sentence into unrelated fragments, separating each keyword
     from its own provision number.
  2. Even within one fragment, CITATION_REGEX/BARE_CITATION_REGEX's keyword
     alternation only recognized the FULL words "Article"/"Articles", never
     "Art."/"Arts.", so the abbreviated form was never recognized as a
     citation keyword at all.
  Combined effect on one real generated paragraph citing 4 distinct
  Articles: extract_claims() returned 0 claims (verified before this fix
  via direct reproduction) -- every citation in that paragraph was
  silently dropped, not flagged, not logged, just gone.

Every sentence below is copied VERBATIM from real committed output under
outputs/*.jsonl -- not an invented example.

"S."/"Sec."/"Ss."/"O."/"r." (abbreviations for Section/Order/Rule) were
also checked for across the same 181 texts and essentially never occur, with
ONE exception: the same real document that has "Art.227" also has a
lowercase "s.3(13)" bare citation earlier in the same sentence (see
test_lowercase_s_dot_citation_in_the_same_real_sentence_is_a_KNOWN_gap
below) -- a single occurrence is not enough real evidence to justify adding
general lowercase "s." keyword recognition (a single standalone letter is
far more collision-prone than "Art."/"Arts." -- e.g. any stray initial or
abbreviation), so this one is documented as a known, deliberately deferred
gap rather than "fixed" on n=1 evidence. Fix it the same evidence-driven way
if more real examples turn up.
"""
from src.claim_parser import extract_citations, extract_claims, split_sentences

_REAL_MULTI_ARTICLE_SENTENCE_TEXT = (
    "Statutory Grounding: The application of Art. 32, which grants the "
    "Supreme Court the power to issue certain writs to enforce fundamental "
    "rights, is subject to the limitations imposed by Art. 136, which "
    "governs the Supreme Court's jurisdiction to grant special leave to "
    "appeal from any judgment, decree, or order passed by any court or "
    "tribunal in India. Additionally, the provisions of Art. 21, which "
    "protects the right to life and personal liberty, and Arts. 14 and 19, "
    "which guarantee equality before the law and certain fundamental "
    "rights, respectively, are relevant to the context of the "
    "petitioner's claim regarding the legality of his detention and the "
    "finality of the decision in the special leave petition under Art. 136."
)

_REAL_NO_SPACE_ABBREVIATION_TEXT = (
    "Statutory Grounding: The decision in this case is grounded in "
    "s.3(13) of the Bombay Industrial Relations Act of 1947, which "
    "defines an employee, and Art.227 of the Constitution of India, "
    "which empowers the High Courts to issue directions or orders or "
    "writs for the enforcement of any of the rights conferred by any of "
    "the provisions of Part III of the Constitution."
)


def test_art_abbreviation_no_longer_shatters_sentence_into_fragments():
    sentences = split_sentences(_REAL_MULTI_ARTICLE_SENTENCE_TEXT)
    # Exactly 2 real sentences (split on the period after "...India." and
    # after "...Art. 136." at the very end) -- NOT 7 fragments split after
    # every "Art." occurrence.
    assert len(sentences) == 2
    for s in sentences:
        # No fragment should start mid-citation with a bare provision
        # number (the tell-tale sign of a keyword/number split).
        assert not s[0].isdigit()


def test_art_and_arts_abbreviation_recovers_all_four_citations():
    claims = extract_claims(_REAL_MULTI_ARTICLE_SENTENCE_TEXT)
    numbers = sorted(int(c.citation_extracted.provision_number) for c in claims)
    # Art. 32, Art. 136 (cited twice -> 2 claims, once per sentence it
    # appears in), Art. 21, Arts. 14 and 19 = 6 claims total.
    assert numbers == [14, 19, 21, 32, 136, 136]
    for c in claims:
        assert c.citation_extracted.provision_type == "Article"


def test_art_dot_directly_adjacent_to_number_no_space():
    claims = extract_claims(_REAL_NO_SPACE_ABBREVIATION_TEXT)
    article_claims = [c for c in claims if c.citation_extracted.provision_type == "Article"]
    assert len(article_claims) == 1
    citation = article_claims[0].citation_extracted
    assert citation.provision_number == "227"
    assert citation.act_norm == "constitution of india"


def test_art_abbreviation_never_resolves_an_act_it_was_not_given():
    # Bare "Art. 32"/"Art. 136" mentions in _REAL_MULTI_ARTICLE_SENTENCE_TEXT
    # never state their own act clause ("...of the Constitution...") in the
    # same breath -- confirm the parser does NOT guess "Constitution of
    # India" just because that's the overwhelmingly likely real-world
    # referent. Never guessing an unstated Act is the safety property this
    # whole module is built around.
    claims = extract_claims(_REAL_MULTI_ARTICLE_SENTENCE_TEXT)
    assert all(c.citation_extracted.act_norm == "" for c in claims)


def test_bare_word_art_without_period_is_not_treated_as_a_citation_keyword():
    # "the art of persuasion" or similar bare English usage of "art" must
    # never trigger a false citation match -- only the period-terminated
    # abbreviated form does.
    text = "The art of statutory interpretation requires care."
    assert extract_citations(text) == []


def test_full_word_article_keyword_still_works_unaffected():
    # Regression guard for the \\s+ -> \\s* change in CITATION_REGEX/
    # BARE_CITATION_REGEX/_EMBEDDED_CITATION_RE made to support "Art.227"'s
    # zero-space form -- the ordinary full-word path must be unaffected.
    citations = extract_citations("Article 21 of the Constitution of India protects life and liberty.")
    assert len(citations) == 1
    assert citations[0].provision_type == "Article"
    assert citations[0].provision_number == "21"
    assert citations[0].act_norm == "constitution of india"


def test_s_sec_abbreviations_still_unrecognized_not_a_speculative_fix():
    # Documents the deliberate scope limit: only Art./Arts. was added,
    # because only Art./Arts. was ever observed (repeatedly) in the real
    # corpus scan. "S. 302" / "Sec. 302" remain unrecognized -- NOT a
    # regression, a scope boundary. If real generated text is ever observed
    # using these, add them the same evidence-driven way this fix was made.
    assert extract_citations("S. 302 of the Indian Penal Code applies.") == []
    assert extract_citations("Sec. 302 of the Indian Penal Code applies.") == []


def test_lowercase_s_dot_citation_in_the_same_real_sentence_is_a_KNOWN_gap():
    # KNOWN, DOCUMENTED, DEFERRED gap (not silently missed): the same real
    # document that motivated the Art.227 fix above ALSO has a lowercase
    # "s.3(13)" bare citation earlier in the identical sentence, which
    # extract_citations() still does not recognize -- a single real
    # occurrence is not enough evidence to justify adding general
    # lowercase-"s." keyword recognition (a bare single letter is far more
    # collision-prone with ordinary prose than "Art."/"Arts." was). This
    # test locks in the CURRENT (incomplete) behavior so a future change
    # that starts recognizing it is a deliberate, noticed decision, not an
    # accident -- update this test (and add real second/third examples to
    # justify the change) if that ever happens.
    claims = extract_claims(_REAL_NO_SPACE_ABBREVIATION_TEXT)
    provision_numbers = {c.citation_extracted.provision_number for c in claims}
    assert "227" in provision_numbers  # the Art.227 citation IS recovered
    assert "3" not in provision_numbers  # the s.3(13) citation is NOT (known gap)
