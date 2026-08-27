"""
Final pre-GPU adversarial pass: regression test for the one real parser
defect found this pass (the "Section N, Part <roman>" act-pollution bug),
plus fail-closed safety-net tests for citation shapes that were checked
against every real generated text this project has ever produced and found
NOT to occur (see scripts/audit_no_evidence_taxonomy_v2.py and the
paren-act / abbreviation-year sweep in outputs/pre_gpu_readiness_report.md
section "Adversarial audit") — so no fix was made for them (per this
task's "only improve retrieval when justified by observed failures" rule),
but their current behavior must still be proven safe (never a false
match, never a crash) rather than merely assumed.
"""
from src.claim_parser import extract_citations, extract_claims


# ---------------------------------------------------------------------------
# Real defect fix: "Section 304, Part II of the Indian Penal Code" — found
# via scripts/audit_no_evidence_taxonomy_v2.py against real document
# 1991_110. Before the fix: "Part II" (Title-Case) satisfied the bare-act
# first-word rule, so it was captured as if it were part of the ACT's own
# name — leaving Section 304's own act unresolved AND polluting a later
# bare "Section 34" mention (which inherits the nearest preceding
# same-sentence act) with the bogus "part ii of the indian penal code"
# pseudo-act instead of the real IPC.
# ---------------------------------------------------------------------------

_REAL_1991_110_SENTENCE = (
    "Section 304, Part II of the Indian Penal Code pertains to culpable "
    "homicide not amounting to murder, while section 34 deals with the "
    "liability of persons aiding, abetting, counseling, or procuring the "
    "commission of an offense."
)


def test_section_with_part_qualifier_resolves_to_correct_act_not_polluted():
    citations = extract_citations(_REAL_1991_110_SENTENCE)
    s304 = next(c for c in citations if c.provision_number == "304")
    assert s304.act_norm == "indian penal code 1860"
    assert s304.subsection == "Part II"


def test_part_qualifier_does_not_leak_into_later_bare_citations_act():
    # The real, previously-observed regression: a LATER bare citation in the
    # same sentence must inherit the real IPC, not "part ii of the indian
    # penal code".
    citations = extract_citations(_REAL_1991_110_SENTENCE)
    s34 = next(c for c in citations if c.provision_number == "34")
    assert s34.act_norm == "indian penal code 1860"
    assert "part" not in s34.act_norm


def test_part_qualifier_not_attached_when_ambiguous_bundled_list():
    # "Sections 302 and 304, Part II of the IPC" — the Part qualifier
    # cannot be safely attributed to just one of two bundled numbers, so it
    # must be dropped rather than guessed onto either.
    sentence = "Sections 302 and 304, Part II of the Indian Penal Code apply here."
    citations = extract_citations(sentence)
    assert len(citations) == 2
    for c in citations:
        assert c.subsection is None
        assert c.act_norm == "indian penal code 1860"


# ---------------------------------------------------------------------------
# Aliases / abbreviations — already-correct cases stay correct, and the
# untested corpus-observed-absent variants are proven to fail CLOSED
# (never resolve to a wrong act) rather than silently guessing.
# ---------------------------------------------------------------------------

def test_known_alias_crpc_undotted_resolves():
    citations = extract_citations("Section 41 of the CrPC governs arrest without warrant.")
    assert citations[0].act_norm == "code of criminal procedure 1973"


def test_unseen_spaced_abbreviation_fails_closed_not_wrong_act():
    # "Cr. P. C." (space-separated letters) never occurs in any real
    # generated text this project has produced (verified by corpus sweep)
    # — not aliased, and MUST NOT coincidentally normalize to some other
    # real corpus act. Failing closed (empty/unmatched act) is correct;
    # inventing an alias for an unobserved shape is not.
    citations = extract_citations("Section 41 of the Cr. P. C. governs arrest without warrant.")
    assert citations[0].act_norm not in {
        "code of criminal procedure 1973", "code of civil procedure 1908",
        "indian penal code 1860",
    }


def test_unseen_dotted_abbreviation_fails_closed_not_wrong_act():
    # "Cr.P.C." (dotted, no internal spaces) also never occurs in any real
    # generated text (verified by corpus sweep — the generator consistently
    # uses either full names or the undotted "CrPC"/"IPC" short forms). The
    # act-name capture's own terminator (the first '.'/';' after "of/in")
    # fires on the FIRST internal period of "Cr.P.C." itself, truncating
    # the captured act to just "Cr" — a real capture artifact, but one that
    # provably cannot cause a false match: "cr" is not any real corpus
    # act_norm, so this still fails closed rather than silently guessing.
    citations = extract_citations("Section 41 of the Cr.P.C., 1973 governs arrest without warrant.")
    assert citations[0].act_norm not in {
        "code of criminal procedure 1973", "code of civil procedure 1908",
        "indian penal code 1860",
    }


def test_unaliased_abbreviation_fails_closed_not_wrong_act():
    # "T.P. Act" (Transfer of Property Act) has no alias table entry and
    # does not occur in any real generated text this project has produced.
    citations = extract_citations("Section 54 of the T.P. Act deals with sale of immovable property.")
    assert citations[0].act_norm not in {
        "transfer of property act 1882", "indian penal code 1860",
    }


# ---------------------------------------------------------------------------
# Parenthetical Act names directly after a bare number (no "of/in" clause)
# — never observed in any real generated text (verified by corpus sweep;
# the only real parenthetical-Act pattern this project's data actually
# uses is the ALREADY-handled trailing-abbreviation-gloss form, e.g. "the
# Indian Penal Code (IPC)", covered by
# test_normalize_act_strips_parenthetical_abbreviation /
# test_parenthetical_abbreviation_industrial_disputes_act). Proven here to
# fail closed rather than silently misreading the paren content as a
# subsection.
# ---------------------------------------------------------------------------

def test_unseen_direct_parenthetical_act_name_fails_closed():
    citations = extract_citations("Section 302 (Indian Penal Code) deals with murder.")
    assert citations[0].act_norm == ""  # unresolved, never guessed


# ---------------------------------------------------------------------------
# Provision ranges ("Sections 100-105", "Sections 100 to 105") — never
# observed in any real generated text this project has produced (verified
# by corpus sweep). Not implemented (no observed failure to justify it,
# per this task's explicit scope rule) — proven here to fail closed: the
# malformed/partial number this produces normalizes to an act that is
# never resolved, so it can never silently produce a false match.
# ---------------------------------------------------------------------------

def test_unseen_hyphen_range_fails_closed():
    citations = extract_citations("Sections 100-105 of the Indian Penal Code deal with public tranquility.")
    assert citations[0].act_norm == ""


def test_unseen_to_range_fails_closed():
    citations = extract_citations("Sections 100 to 105 of the Indian Penal Code deal with public tranquility.")
    assert citations[0].act_norm == ""
