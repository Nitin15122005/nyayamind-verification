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
