"""
Focused tests for scripts/select_natural_candidates.py's scoring function —
the only non-trivial logic in that script (dedup/diversity ordering are
simple, direct sorts/greedy loops exercised end-to-end by actually running
the script, not re-tested here). No GPU, no model, no network.
"""
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from select_natural_candidates import score_case, PROCEDURAL_ACTS  # noqa: E402

from src.claim_parser import normalize_act
from src.data_loader import Case, EvidenceRecord


@pytest.fixture
def evidence_pool():
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder...",
        source_url="https://example.invalid/1", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    ipc34 = EvidenceRecord(
        dataset_citation_key="Section 34 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="34",
        subsection=None, canonical_text="Common intention...",
        source_url="https://example.invalid/2", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    crpc149 = EvidenceRecord(
        dataset_citation_key="Section 149 in Code of Criminal Procedure, 1973",
        act="The Code of Criminal Procedure, 1973", provision_type="Section", provision_number="149",
        subsection=None, canonical_text="Procedure...",
        source_url="https://example.invalid/3", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("Code of Criminal Procedure, 1973"),
    )
    all_usable = [ipc302, ipc34, crpc149]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


def test_case_with_matched_citations_scores_positive(evidence_pool):
    exact_index, all_usable = evidence_pool
    case = Case(
        document_id="doc1", case_text="Facts about a murder case, quite long enough.",
        raw_citation_keys=["Section 302 in The Indian Penal Code, 1860"],
    )
    stats = score_case(case, exact_index, all_usable, fuzzy_threshold=0.8)
    assert stats["n_matched_exact"] == 1
    assert stats["n_matched_total"] == 1
    assert stats["score"] > 0
    assert stats["is_purely_procedural"] is False


def test_case_with_no_matching_evidence_scores_zero(evidence_pool):
    exact_index, all_usable = evidence_pool
    case = Case(
        document_id="doc2", case_text="Facts about an unrelated tax dispute, long enough text.",
        raw_citation_keys=["Section 999 in Some Unrelated Act, 2001"],
    )
    stats = score_case(case, exact_index, all_usable, fuzzy_threshold=0.8)
    assert stats["n_matched_total"] == 0
    assert stats["score"] == 0
    assert stats["n_distinct_evidence_pairs"] == 0


def test_purely_procedural_case_flagged_but_not_zero_score(evidence_pool):
    exact_index, all_usable = evidence_pool
    case = Case(
        document_id="doc3", case_text="Procedural facts about a trial referral, long enough.",
        raw_citation_keys=["Section 149 in Code of Criminal Procedure, 1973"],
    )
    stats = score_case(case, exact_index, all_usable, fuzzy_threshold=0.8)
    assert stats["is_purely_procedural"] is True
    assert stats["n_matched_exact"] == 1
    # Procedural-only match still contributes exact-match + diversity points,
    # just not the substantive bonus — never a hard exclusion at this layer.
    assert stats["score"] > 0
    assert stats["substantive_matches"] == 0


def test_multiple_distinct_provisions_score_higher_than_repeated_citation(evidence_pool):
    exact_index, all_usable = evidence_pool
    diverse_case = Case(
        document_id="doc4", case_text="Facts long enough to pass the length filter easily.",
        raw_citation_keys=[
            "Section 302 in The Indian Penal Code, 1860",
            "Section 34 in The Indian Penal Code, 1860",
        ],
    )
    repeated_case = Case(
        document_id="doc5", case_text="Facts long enough to pass the length filter easily.",
        raw_citation_keys=[
            "Section 302 in The Indian Penal Code, 1860",
            "Section 302 in The Indian Penal Code, 1860",
        ],
    )
    diverse_stats = score_case(diverse_case, exact_index, all_usable, fuzzy_threshold=0.8)
    repeated_stats = score_case(repeated_case, exact_index, all_usable, fuzzy_threshold=0.8)
    assert diverse_stats["n_distinct_evidence_pairs"] == 2
    assert repeated_stats["n_distinct_evidence_pairs"] == 1
    # Same exact-match count (2 each), but diverse_case scores strictly
    # higher because of the per-distinct-pair bonus.
    assert diverse_stats["n_matched_exact"] == repeated_stats["n_matched_exact"] == 2
    assert diverse_stats["score"] > repeated_stats["score"]


def test_unparseable_citation_key_is_skipped_not_crashing(evidence_pool):
    exact_index, all_usable = evidence_pool
    case = Case(
        document_id="doc6", case_text="Facts long enough to pass the length filter easily.",
        raw_citation_keys=["not a real citation key at all"],
    )
    stats = score_case(case, exact_index, all_usable, fuzzy_threshold=0.8)
    assert stats["n_citations_parsed"] == 0
    assert stats["n_matched_total"] == 0
    assert stats["score"] == 0


def test_empty_citation_list_scores_zero(evidence_pool):
    exact_index, all_usable = evidence_pool
    case = Case(document_id="doc7", case_text="Facts with no citations mentioned at all here.",
                raw_citation_keys=[])
    stats = score_case(case, exact_index, all_usable, fuzzy_threshold=0.8)
    assert stats["n_raw_citation_keys"] == 0
    assert stats["score"] == 0


def test_procedural_acts_constant_matches_only_procedural_codes():
    assert "code of criminal procedure 1973" in PROCEDURAL_ACTS
    assert "code of civil procedure 1908" in PROCEDURAL_ACTS
    assert "indian penal code 1860" not in PROCEDURAL_ACTS
    assert "constitution of india" not in PROCEDURAL_ACTS
