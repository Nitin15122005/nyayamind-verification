"""
Regression tests for the 15 claim-parser act-attribution bugs surfaced by
the provisional assumption-annotation pass (see
research/prototype/outputs/assumption_vs_automated_report.md, section 6,
and assumption_annotation_summary.md, "Extraction bugs found").

Every sentence here is copied VERBATIM from real Qwen-generated
`statutory_grounding` fields already on disk (`gold_annotation.jsonl`,
document_ids 2007_1517 / 2003_967 / 1989_184 / 2023_26) — not invented
examples — so these tests pin the fix against the actual failures found,
not an idealized version of them.

Four bug patterns, one test group each:
  1. Multi-act run-on sentence act-bleed (2007_1517, A0006-A0010)
  2. Year mistaken for a provision number (2003_967, A0050)
  3. Trim-heuristic failure swallowing the rest of the sentence
     (1989_184, A0055-A0056)
  4. Field-wide single-act fallback overriding an explicit in-sentence act
     (2023_26, A0073-A0080)
"""
from src.claim_parser import extract_citations, extract_claims


# ---------------------------------------------------------------------------
# Bug 1: 2007_1517 — multi-act run-on sentence act-bleed
# ---------------------------------------------------------------------------

_BUG1_SENTENCE = (
    "The case is grounded in the United Commercial Bank (Conduct and "
    "Discipline and Appeal) Regulation, 1976, specifically Regulation "
    "15(2), and the Manual on Disciplinary Action and Related Matters of "
    "UCO Bank, particularly Clause 22 thereof, as well as Sections 120-B, "
    "471, and 477 of the Indian Penal Code and Section 5(2) read with "
    "Section 1(d) of the Prevention of Corruption Act, 1947, which pertain "
    "to the criminal charges and the prevention of corruption respectively."
)


def test_bug1_ipc_sections_do_not_merge_with_poca_act_name():
    # Previously: act_raw for IPC 120-B/471/477 was the polluted two-act
    # string "the Indian Penal Code and Section 5(2) read with Section
    # 1(d) of the Prevention of Corruption Act, 1947" (two acts merged
    # into one act_norm). Must now be clean, single-act "Indian Penal Code".
    citations = extract_citations(_BUG1_SENTENCE)
    ipc_citations = [c for c in citations if c.provision_number in ("120-B", "471", "477")]
    assert len(ipc_citations) == 3
    for c in ipc_citations:
        assert c.act_norm in ("indian penal code", "indian penal code 1860")
        assert "prevention of corruption" not in c.act_norm
        assert "section 5" not in c.act_norm


def test_bug1_poca_citation_recovered_not_lost():
    # Previously: "Section 1(d)" of the Prevention of Corruption Act was
    # swallowed inside the first citation's over-captured act clause and
    # never became a claim at all. Must now be recovered as its own
    # citation with the correct act.
    citations = extract_citations(_BUG1_SENTENCE)
    poca = [c for c in citations if c.act_norm == "prevention of corruption act 1947"]
    assert len(poca) == 1
    assert poca[0].provision_number == "1"
    assert poca[0].subsection == "d"


def test_bug1_regulation_citation_gets_its_own_act_not_ipc_or_poca():
    # Previously: act_raw for "Regulation 15(2)" was wrongly the merged
    # IPC+POCA string (a cross-domain misattribution — a bank service
    # regulation attributed to a penal statute). Must now resolve to the
    # actual UCB Regulation named earlier in the same sentence.
    citations = extract_citations(_BUG1_SENTENCE)
    reg = next(c for c in citations if c.provision_type == "Regulation" and c.provision_number == "15")
    assert reg.subsection == "2"
    assert "united commercial bank" in reg.act_norm
    assert "indian penal code" not in reg.act_norm
    assert "prevention of corruption" not in reg.act_norm


# ---------------------------------------------------------------------------
# Bug 2: 2003_967 — year mistaken for a provision number
# ---------------------------------------------------------------------------

_BUG2_SENTENCE_1 = (
    "The case is governed by the Indian Medical Council Act, 1956, which "
    "sets out the regulatory framework for medical education and practice "
    "in India, and the Post Graduate Medical Education Regulations 2000, "
    "which provide specific rules for postgraduate medical education, "
    "including the criteria for admission."
)
_BUG2_SENTENCE_2 = (
    "Article 14 of the Constitution of India requires that any law or "
    "regulation must not discriminate unreasonably between individuals or "
    "groups, while Article 15(4) allows the state to make provisions for "
    "reserving educational facilities or appointments in favor of any "
    "backward class of citizens."
)


def test_bug2_bare_act_year_is_not_extracted_as_a_provision_number():
    # Previously: "Regulations 2000" was parsed as provision_type=Regulation,
    # provision_number="2000" (the Act's own year, not a real regulation
    # number). Must now yield NO citation for this phrase at all — dropped,
    # never guessed.
    citations = extract_citations(_BUG2_SENTENCE_1)
    assert citations == []


def test_bug2_unrelated_article_citations_do_not_inherit_wrong_act():
    # Previously: because "Regulations 2000" wrongly produced an unresolved
    # citation, extract_claims()'s field-wide fallback attached the ONE
    # other resolved act in the field ("Constitution of India", from the
    # unrelated Article 14/15(4) sentence) onto it — a cross-domain
    # misattribution. With the year-as-number bug gone, the Article
    # citations must simply resolve to their own, correct, explicit act
    # and nothing must bleed the other way.
    full_field = _BUG2_SENTENCE_1 + " " + _BUG2_SENTENCE_2
    claims = extract_claims(full_field)
    numbers = [c.citation_extracted.provision_number for c in claims]
    assert numbers == ["14", "15"]
    for c in claims:
        assert c.citation_extracted.act_norm == "constitution of india"


# ---------------------------------------------------------------------------
# Bug 3: 1989_184 — trim-heuristic failure swallowing the rest of the
# sentence (plural-subject verb agreement: "Sections ... require", not
# "Section ... requires")
# ---------------------------------------------------------------------------

_BUG3_SENTENCE = (
    "Sections 25 and 27 of the Arms Act require the lawful possession and "
    "use of firearms and impose penalties for their unlawful possession "
    "or use."
)


def test_bug3_plural_subject_verb_still_trims_act_name():
    # Previously: none of the three trim rules fired on this exact
    # phrasing (plural "require", not singular "requires"), so the act
    # name captured the entire rest of the sentence verbatim.
    citations = extract_citations(_BUG3_SENTENCE)
    assert len(citations) == 2
    assert [c.provision_number for c in citations] == ["25", "27"]
    for c in citations:
        assert c.act_raw == "the Arms Act"
        assert c.act_norm == "arms act"
        assert "require" not in c.act_norm
        assert "firearms" not in c.act_norm


# ---------------------------------------------------------------------------
# Bug 4: 2023_26 — field-wide single-act fallback overriding an explicit
# in-sentence act (IPC sections wrongly inherited CrPC because CrPC was
# the only act that resolved "unambiguously" anywhere in the field under
# the old whole-field-uniqueness rule)
# ---------------------------------------------------------------------------

_BUG4_SENTENCE_1 = (
    "The Indian Penal Code, 1860, specifically Sections 148, 302, 304 "
    "Part II, and 324, along with Section 149 of the Code of Criminal "
    "Procedure, 1973, are the statutory grounding for this case."
)
_BUG4_SENTENCE_2 = (
    "Section 148 prescribes the punishment for unlawful assembly, Section "
    "302 prescribes the punishment for murder, Section 304 Part II "
    "prescribes the punishment for culpable homicide not amounting to "
    "murder, and Section 324 prescribes the punishment for voluntarily "
    "causing hurt."
)
_BUG4_SENTENCE_3 = (
    "Section 149 of the Code of Criminal Procedure, 1973, deals with the "
    "procedure for trial of persons accused of offences committed in "
    "furtherance of the common intention of two or more persons."
)


def test_bug4_explicit_in_sentence_ipc_sections_resolve_to_ipc_not_crpc():
    # Previously: A0073/A0074/A0075 (this sentence's bare 148/302/304
    # citations) all wrongly resolved to CrPC 1973, even though the
    # sentence explicitly attributes them to "The Indian Penal Code,
    # 1860" and only Section 149 to CrPC.
    citations = extract_citations(_BUG4_SENTENCE_1)
    by_number = {c.provision_number: c for c in citations}
    assert by_number["148"].act_norm == "indian penal code 1860"
    assert by_number["302"].act_norm == "indian penal code 1860"
    assert by_number["304"].act_norm == "indian penal code 1860"
    assert by_number["149"].act_norm == "code of criminal procedure 1973"


def test_bug4_field_wide_second_sentence_reuses_ipc_via_same_number_not_crpc():
    # Previously: A0077/A0078/A0079 (the second sentence's bare 148/302/304
    # re-mentions, with no act of their own) inherited CrPC — the ONE act
    # that resolved "unambiguously" field-wide under the old rule — even
    # though CrPC has nothing to do with murder/unlawful-assembly/hurt.
    # A0078 in particular then matched real CrPC S.302 evidence
    # ("permission to conduct prosecution") against a claim asserting "the
    # punishment for murder" — a genuine CONTRADICTED case caused entirely
    # by this upstream extraction bug. Must now reuse IPC via the
    # same-(type,number)-elsewhere-in-field rule.
    full_field = _BUG4_SENTENCE_1 + " " + _BUG4_SENTENCE_2 + " " + _BUG4_SENTENCE_3
    claims = extract_claims(full_field)
    second_sentence_claims = [c for c in claims if c.claim_text == _BUG4_SENTENCE_2]
    # 148, 302, 304, 324 (324 stays unresolved — a separate, genuinely
    # ambiguous case, checked by test_bug4_ambiguous_field_wide_case_stays_unresolved_not_guessed).
    assert len(second_sentence_claims) == 4
    ipc_reused = [c for c in second_sentence_claims if c.citation_extracted.provision_number != "324"]
    assert len(ipc_reused) == 3
    for c in ipc_reused:
        assert c.citation_extracted.act_norm == "indian penal code 1860", (
            f"Section {c.citation_extracted.provision_number} wrongly resolved to "
            f"{c.citation_extracted.act_norm!r}"
        )


def test_bug4_ambiguous_field_wide_case_stays_unresolved_not_guessed():
    # "Section 324" (culpable-hurt) only ever appears in the second
    # sentence — never with its own act, and never repeated elsewhere with
    # a resolvable act (the first sentence's list stops at "304 Part II",
    # a pre-existing, unrelated list-parsing limitation on "Part II" — see
    # README "Known limitations"). The field genuinely contains TWO
    # distinct acts (IPC and CrPC) by this point, so guessing either one
    # for 324 would be wrong roughly as often as right. Per the "ambiguous
    # -> unresolved, never guessed" requirement, this must stay unresolved
    # (safe NO_EVIDENCE) rather than silently attaching the wrong act like
    # the old code did.
    full_field = _BUG4_SENTENCE_1 + " " + _BUG4_SENTENCE_2 + " " + _BUG4_SENTENCE_3
    claims = extract_claims(full_field)
    c324 = next(c for c in claims if c.citation_extracted.provision_number == "324")
    assert c324.citation_extracted.act_raw is None
    assert c324.citation_extracted.act_norm == ""


def test_bug4_second_explicit_crpc_mention_unaffected():
    # Section 149's second, fully-explicit mention (sentence 3) must keep
    # resolving to CrPC exactly as before — no regression on already-valid
    # extraction.
    citations = extract_citations(_BUG4_SENTENCE_3)
    assert len(citations) == 1
    assert citations[0].provision_number == "149"
    assert citations[0].act_norm == "code of criminal procedure 1973"


def test_parenthetical_abbreviation_industrial_disputes_act():
    s = (
        "Statutory Grounding: The Industrial Disputes Act, 1947 (ID Act) "
        "governs the dispute, specifically Section 2(s) defining a workman, "
        "and Section 10(1)(c) referring disputes to the Labour Court."
    )
    citations = extract_citations(s)
    assert len(citations) == 2
    by_num = {c.provision_number: c for c in citations}
    assert by_num["2"].act_norm == "industrial disputes act 1947"
    assert by_num["10"].act_norm == "industrial disputes act 1947"


# ---------------------------------------------------------------------------
# Bug 5: copula ("is"/"are") not recognized as an act-name-continuation
# trim point, and "Evidence Act" (no "Indian" prefix) not aliased.
#
# Found via the NO_EVIDENCE root-cause diagnosis for this task
# (research/prototype/outputs/no_evidence_diagnosis.json,
# research_phase_next_status.md): three real natural claims (documents
# 2006_650, 1998_229, 1991_582 — all the same generated sentence) captured
# act_raw="the Evidence Act is applicable" instead of stopping at "the
# Evidence Act", because none of _ACT_CONTINUATION_VERBS is a copula.
# Sentence copied verbatim from run_A_n30.jsonl (document_id 2006_650,
# claim c3).
# ---------------------------------------------------------------------------

_BUG5_SENTENCE = (
    "Additionally, Section 114 of the Evidence Act is applicable, which "
    "prescribes the onus of proof resting on the prosecution to establish "
    "the guilt of the accused."
)


def test_bug5_copula_trims_act_name_before_predicate():
    citations = extract_citations(_BUG5_SENTENCE)
    assert len(citations) == 1
    assert citations[0].act_raw == "the Evidence Act"


def test_bug5_evidence_act_short_form_resolves_to_corpus_act():
    citations = extract_citations(_BUG5_SENTENCE)
    assert citations[0].act_norm == "indian evidence act 1872"


def test_bug5_other_continuation_verbs_still_trim_correctly():
    # No regression: an existing continuation-verb sentence (not a copula)
    # must still trim exactly as before.
    s = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    citations = extract_citations(s)
    assert len(citations) == 1
    assert citations[0].act_raw == "the Indian Penal Code, 1860"
    assert citations[0].act_norm == "indian penal code 1860"


def test_bug5_was_were_also_trim_as_copulas():
    s = "Section 302 of the Indian Penal Code, 1860 was invoked, which deals with murder."
    citations = extract_citations(s)
    assert len(citations) == 1
    assert citations[0].act_raw == "the Indian Penal Code, 1860"


# ---------------------------------------------------------------------------
# Claim granularity: atomic assertion_text for bundled parallel-clause
# sentences (see research_phase_next_status.md, "claim granularity").
# assertion_text is ADDITIVE and always populated — claim_text is never
# changed, so existing callers reading claim_text see zero behaviour change.
# Sentence copied verbatim from run_A_n30.jsonl (document_id 2005_360).
# ---------------------------------------------------------------------------

def test_two_way_parallel_clause_split_gives_each_citation_its_own_clause():
    s = ("Section 302 prescribes the punishment for murder, while Section 34 "
         "deals with criminal liability for an act done by more than one "
         "person in furtherance of the common intention or common object.")
    claims = extract_claims(s)
    assert len(claims) == 2
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["302"].assertion_text == "Section 302 prescribes the punishment for murder"
    assert by_num["34"].assertion_text.startswith("Section 34 deals with criminal liability")
    # claim_text (the full original sentence) is unchanged for both — the
    # split is additive, not a replacement.
    assert by_num["302"].claim_text == s
    assert by_num["34"].claim_text == s


def test_three_citation_bundle_both_share_the_second_clause():
    # "Sections 34 and 109" bundles two citations inside ONE clause after
    # the while-split. _citation_mentioned_in() re-parses each clause with
    # extract_citations() itself (not a narrower ad-hoc regex), so BOTH
    # numbers in "Sections 34 and 109" are recognized, not just the one
    # immediately adjacent to the keyword — 109 is no longer stuck with
    # the (wider) full sentence, it correctly isolates to the same
    # (still-bundled, but narrower) second clause as 34.
    s = ("Section 302 prescribes the punishment for murder, while Sections "
         "34 and 109 address the criminal liability of an accomplice or "
         "abettor in the commission of a crime.")
    claims = extract_claims(s)
    by_num = {c.citation_extracted.provision_number: c for c in claims}
    assert by_num["302"].assertion_text == "Section 302 prescribes the punishment for murder"
    assert by_num["34"].assertion_text.startswith("Sections 34 and 109 address")
    assert by_num["109"].assertion_text.startswith("Sections 34 and 109 address")
    assert by_num["109"].assertion_text == by_num["34"].assertion_text


def test_plain_list_sentence_has_no_split_point_every_citation_gets_full_sentence():
    # A bare listing ("specifically Sections 120B, 420, and 467") has no
    # per-citation content to split at all — every citation's
    # assertion_text must stay the full sentence (there is nothing unsafe
    # here; it is simply not a splittable shape).
    s = ("The statutory grounding for this case includes the Indian Penal "
         "Code, specifically Sections 120B, 420, and 467.")
    claims = extract_claims(s)
    assert len(claims) == 3
    assert all(c.assertion_text == s for c in claims)


def test_single_citation_sentence_assertion_text_equals_claim_text():
    s = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    claims = extract_claims(s)
    assert len(claims) == 1
    assert claims[0].assertion_text == claims[0].claim_text == s


def test_multiple_while_occurrences_is_a_safe_no_split():
    s = ("Section 5 applies while the accused is in custody, while Section 6 "
         "applies while the accused is on bail.")
    claims = extract_claims(s)
    for c in claims:
        assert c.assertion_text == s  # ambiguous split point -> full sentence for all

