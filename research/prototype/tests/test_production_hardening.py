from src.claim_parser import ExtractedCitation, extract_citations, normalize_act
from src.data_loader import EvidenceRecord
from src.evidence_matcher import match_evidence


def _evidence(act):
    return EvidenceRecord(
        dataset_citation_key=f"Section 10 in {act}", act=act,
        provision_type="Section", provision_number="10", subsection=None,
        canonical_text="Statutory text.", source_url="https://example.invalid/source",
        audit_verdict="VERIFIED_EXACT", act_norm=normalize_act(act),
    )


def test_plural_citations_have_individual_occurrence_spans():
    sentence = "Sections 302, 304(1), and 307 of the IPC prescribe penalties."
    citations = extract_citations(sentence)
    assert [c.provision_number for c in citations] == ["302", "304", "307"]
    assert [sentence[c.start_char:c.end_char] for c in citations] == ["302", "304(1)", "307"]


def test_repeated_citations_have_distinct_occurrence_spans():
    sentence = "Section 302 of the IPC applies, whereas Section 302 of the IPC has a separate role."
    citations = extract_citations(sentence)
    assert len(citations) == 2
    assert [sentence[c.start_char:c.end_char] for c in citations] == ["302", "302"]
    assert citations[0].start_char < citations[1].start_char


def test_bare_subsection_citation_has_full_occurrence_span():
    sentence = "The applicable provision is Section 25F(1)."
    citation = extract_citations(sentence)[0]
    assert sentence[citation.start_char:citation.end_char] == "25F(1)"


def test_fuzzy_match_rejects_equal_score_ambiguous_act_editions():
    pool = [_evidence("Income Tax Act, 1961"), _evidence("Income Tax Act, 2025")]
    index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in pool}
    citation = ExtractedCitation("Section", "10", None, "Income Tax Act", normalize_act("Income Tax Act"))
    result = match_evidence(citation, index, pool, fuzzy_token_overlap_threshold=0.8)
    assert not result.matched
    assert result.evidence is None
    assert result.match_method == "ambiguous_fuzzy"


def test_clause_attribution_does_not_conflate_same_number_from_different_acts():
    from src.claim_parser import _citation_mentioned_in
    from src.claim_parser import ExtractedCitation

    target = ExtractedCitation("Section", "302", None, "Indian Penal Code, 1860", "indian penal code 1860")
    other_act_clause = "Section 302 of the Code of Criminal Procedure, 1973 governs a different matter."
    assert not _citation_mentioned_in(other_act_clause, target)


def test_subsection_citation_does_not_match_base_section_only():
    base = _evidence("Industrial Disputes Act, 1947")
    base.provision_number = "25F"
    base.subsection = None
    base.act_norm = normalize_act("Industrial Disputes Act, 1947")
    index = {(base.provision_type, base.provision_number, base.subsection, base.act_norm): base}
    citation = ExtractedCitation(
        "Section", "25F", "1", "Industrial Disputes Act, 1947",
        normalize_act("Industrial Disputes Act, 1947"),
    )
    result = match_evidence(citation, index, [base])
    assert not result.matched
    assert result.evidence is None
    assert result.match_method == "no_evidence"


def test_base_section_citation_does_not_silently_select_subsection_record():
    subsection = _evidence("Industrial Disputes Act, 1947")
    subsection.provision_number = "25F"
    subsection.subsection = "1"
    subsection.act_norm = normalize_act("Industrial Disputes Act, 1947")
    index = {(subsection.provision_type, subsection.provision_number, subsection.subsection, subsection.act_norm): subsection}
    citation = ExtractedCitation(
        "Section", "25F", None, "Industrial Disputes Act, 1947",
        normalize_act("Industrial Disputes Act, 1947"),
    )
    result = match_evidence(citation, index, [subsection])
    assert not result.matched


def test_flagged_sentence_splice_preserves_all_other_field_text_exactly():
    from src.pipeline import _splice_flagged_sentence

    original = (
        "Opening non-claim prose. Section 10 of the Test Act applies. "
        "Unrelated sentence without a citation."
    )
    corrected = _splice_flagged_sentence(
        original,
        "Section 10 of the Test Act applies.",
        "Section 10 of the Test Act does not apply.",
    )
    assert corrected == (
        "Opening non-claim prose. Section 10 of the Test Act does not apply. "
        "Unrelated sentence without a citation."
    )
    assert corrected.startswith("Opening non-claim prose. ")
    assert corrected.endswith(" Unrelated sentence without a citation.")


def test_flagged_sentence_splice_rejects_duplicate_target_occurrences():
    from src.pipeline import _splice_flagged_sentence

    sentence = "Section 10 of the Test Act applies."
    assert _splice_flagged_sentence(
        f"{sentence} {sentence}", sentence, "Corrected sentence."
    ) is None


def test_run_manifest_records_model_revisions_and_pin_state():
    from src.run_manifest import build_run_manifest

    config = {
        "generation": {"model_id": "generator", "revision": "a" * 40},
        "verification": {"model_id": "verifier", "revision": "b" * 40},
    }
    manifest = build_run_manifest(config, [])
    assert manifest["generation_model_revision"] == "a" * 40
    assert manifest["verification_model_revision"] == "b" * 40
    assert manifest["models_pinned_to_immutable_revisions"] is True


def test_run_manifest_does_not_claim_models_are_pinned_when_revisions_missing():
    from src.run_manifest import build_run_manifest

    config = {
        "generation": {"model_id": "generator", "revision": None},
        "verification": {"model_id": "verifier", "revision": None},
    }
    manifest = build_run_manifest(config, [])
    assert manifest["models_pinned_to_immutable_revisions"] is False


def test_run_manifest_does_not_treat_branch_or_tag_names_as_immutable_pins():
    from src.run_manifest import build_run_manifest

    config = {
        "generation": {"model_id": "generator", "revision": "main"},
        "verification": {"model_id": "verifier", "revision": "v1.0"},
    }
    manifest = build_run_manifest(config, [])
    assert manifest["models_pinned_to_immutable_revisions"] is False


def test_correction_citation_identity_includes_subsection():
    from src.pipeline import _citation_identity

    base = {
        "provision_type": "Section",
        "provision_number": "25F",
        "subsection": None,
        "act_norm": "industrial disputes act 1947",
    }
    subsection = {**base, "subsection": "1"}
    assert _citation_identity(base) != _citation_identity(subsection)


def test_fuzzy_subsection_identity_gate_applies_before_act_similarity():
    from src.evidence_matcher import match_evidence

    base = _evidence("Industrial Disputes Act, 1947")
    base.provision_number = "25F"
    base.subsection = None
    base.act_norm = normalize_act("Industrial Disputes Act, 1947")
    index = {}
    citation = ExtractedCitation(
        "Section", "25F", "1", "Industrial Disputes Act, 1947",
        normalize_act("Industrial Disputes Act, 1947"),
    )
    result = match_evidence(citation, index, [base])
    assert not result.matched
    assert result.match_method == "no_evidence"


def test_fuzzy_subsection_gate_does_not_match_other_subsection():
    from src.evidence_matcher import match_evidence

    other = _evidence("Industrial Disputes Act, 1947")
    other.provision_number = "25F"
    other.subsection = "2"
    other.act_norm = normalize_act("Industrial Disputes Act, 1947")
    citation = ExtractedCitation(
        "Section", "25F", "1", "Industrial Disputes Act, 1947",
        normalize_act("Industrial Disputes Act, 1947"),
    )
    result = match_evidence(citation, {}, [other])
    assert not result.matched


def test_manifest_hash_includes_subsection_identity():
    from types import SimpleNamespace
    from src.run_manifest import build_run_manifest

    base = SimpleNamespace(
        dataset_citation_key="Section 25F in Industrial Disputes Act",
        act="Industrial Disputes Act",
        provision_type="Section",
        provision_number="25F",
        subsection=None,
        canonical_text="Same text",
        source_url="https://example.invalid/act",
        audit_verdict="VERIFIED_EXACT",
    )
    subsection = SimpleNamespace(**{**base.__dict__, "subsection": "1"})
    assert build_run_manifest({}, [base])["evidence_sha256"] != (
        build_run_manifest({}, [subsection])["evidence_sha256"]
    )
