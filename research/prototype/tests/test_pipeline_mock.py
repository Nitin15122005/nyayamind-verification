"""
Deterministic pipeline orchestration tests using fake generator/verifier/
corrector objects — no real model, no GPU, no network, no NyayaRAG data.

These exercise the mode A/B/C branching, the NO_EVIDENCE-never-triggers-
correction rule, the "max one correction + one re-verification" cap, and
the corrected-vs-correction_failed final_field selection logic — the parts
of pipeline.py most likely to have orchestration bugs, independent of
whether the real generation/verification models are any good.

IMPORTANT: results produced with these mocks are NEVER written to
research/prototype/outputs/ and must never be reported as pipeline
research results — they only check that the orchestration code is wired
correctly.
"""
from dataclasses import dataclass

import pytest

from src.data_loader import Case, EvidenceRecord, load_usable_evidence
from src.claim_parser import normalize_act
from src import claim_parser
from src.generator import GenerationMetadata
from src.corrector import CorrectionMetadata
from src.verifier import VerificationResult, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.evidence_matcher import NO_EVIDENCE
from src import pipeline
from src.pipeline import run_case


# ---------------------------------------------------------------------------
# Fixtures: a tiny synthetic evidence pool + config + fake components
# ---------------------------------------------------------------------------

@pytest.fixture
def evidence_pool():
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder shall be punished with death or life imprisonment.",
        source_url="https://example.invalid/1", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    all_usable = [ipc302]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


@pytest.fixture
def config():
    return {
        "seed": 42,
        "generation": {"model_id": "mock-generator", "quantization": {"load_in_4bit": True}},
        "verification": {"model_id": "mock-verifier", "confidence_threshold": 0.70},
        "evidence_matching": {"fuzzy_token_overlap_threshold": 0.8},
    }


@pytest.fixture
def shared_citation_evidence_pool():
    """One evidence record, cited by TWO separate claim-bearing sentences in
    the same generated field — the shape that exposes the ordinal-position
    ambiguity: two distinct claims share the exact same citation identity
    (provision_type, provision_number, act_norm)."""
    ipc420 = EvidenceRecord(
        dataset_citation_key="Section 420 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="420",
        subsection=None,
        canonical_text="Whoever cheats and thereby dishonestly induces the person deceived to deliver "
                        "any property shall be punished with imprisonment.",
        source_url="https://example.invalid/3", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    all_usable = [ipc420]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


@pytest.fixture
def two_claim_evidence_pool():
    """A pool with two distinct usable evidence records, for tests that
    need one flagged claim plus one unflagged claim in the same field."""
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder shall be punished with death or life imprisonment.",
        source_url="https://example.invalid/1", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    ipc21 = EvidenceRecord(
        dataset_citation_key="Section 21 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="21",
        subsection=None, canonical_text="The words public servant denote a person falling under one of the described descriptions.",
        source_url="https://example.invalid/2", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    all_usable = [ipc302, ipc21]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


class FakeGenerator:
    def __init__(self, text: str):
        self._text = text

    def generate(self, case_text: str):
        meta = GenerationMetadata(
            model_id="mock-generator", quantization={"load_in_4bit": True},
            max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42,
        )
        return self._text, meta


class ScriptedVerifier:
    """Returns a scripted verdict per hypothesis text (exact match), so
    tests can control both the initial verification and the
    re-verification-after-correction call precisely."""

    def __init__(self, script: dict[str, VerificationResult]):
        self._script = script
        self.model_id = "mock-verifier"
        self.calls = []

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        self.calls.append((premise, hypothesis))
        if hypothesis not in self._script:
            raise AssertionError(f"ScriptedVerifier got unexpected hypothesis: {hypothesis!r}")
        return self._script[hypothesis]


class PremiseAwareScriptedVerifier:
    """Like ScriptedVerifier, but keyed by (a marker substring expected in
    the PREMISE, the exact hypothesis) — needed for "respectively"
    sentences, where apply_verification's hypothesis is always the full
    shared claim_text (identical across every citation in that one
    sentence), so multiple citations sharing a sentence can only be told
    apart by which evidence (premise) they were verified against, exactly
    as production does."""

    def __init__(self, script: dict[tuple[str, str], VerificationResult]):
        self._script = script
        self.model_id = "mock-verifier"
        self.calls = []

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        self.calls.append((premise, hypothesis))
        for (marker, hyp), result in self._script.items():
            if hyp == hypothesis and marker in premise:
                return result
        raise AssertionError(
            f"PremiseAwareScriptedVerifier got unexpected (premise={premise!r}, hypothesis={hypothesis!r})"
        )


class ScriptedCorrector:
    def __init__(self, corrected_text: str):
        self._corrected_text = corrected_text
        self.calls = []

    def correct(self, case_text, original_field_text, flagged_claim_text, evidence_text):
        self.calls.append((case_text, original_field_text, flagged_claim_text, evidence_text))
        meta = CorrectionMetadata(model_id="mock-generator", max_new_tokens=220, do_sample=False, seed=42)
        return self._corrected_text, meta


def _vr(label, confidence=0.95, sub_reason=None):
    return VerificationResult(
        label=label, confidence=confidence, sub_reason=sub_reason,
        raw_scores={}, verifier_model="mock-verifier",
    )


# ---------------------------------------------------------------------------
# Mode A: generation only
# ---------------------------------------------------------------------------

def test_mode_a_no_verification_no_correction(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(text)

    record = run_case(case, "A", generator, verifier=None, corrector=None,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["final_field"]["source"] == "original"
    assert record["final_field"]["text"] == text
    assert record["correction"]["status"] == "not_applicable_mode_A"
    assert len(record["claims"]) == 1
    assert record["claims"][0]["verdict"] is None  # never verified in mode A
    assert record["verification"]["verifier_model"] is None


# ---------------------------------------------------------------------------
# Mode B: verification only, never modifies output
# ---------------------------------------------------------------------------

def test_mode_b_verifies_but_never_changes_final_field(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(text)
    verifier = ScriptedVerifier({text: _vr(CONTRADICTED, confidence=0.91)})

    record = run_case(case, "B", generator, verifier, corrector=None,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["claims"][0]["verdict"] == CONTRADICTED
    # Mode B is diagnostic-only: even a CONTRADICTED verdict must not change output.
    assert record["final_field"]["source"] == "original"
    assert record["final_field"]["text"] == text
    assert record["correction"]["status"] == "not_applicable_mode_B"


# ---------------------------------------------------------------------------
# Mode C: NO_EVIDENCE must never trigger correction
# ---------------------------------------------------------------------------

def test_no_evidence_claim_never_triggers_correction(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    text = "Section 999 of the Unrelated Act, 2001 governs this matter."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(text)
    verifier = ScriptedVerifier({})  # should never be called: no evidence -> no verify() call
    corrector = ScriptedCorrector("should not be used")

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["claims"][0]["verdict"] == NO_EVIDENCE
    assert record["correction"]["status"] == "not_triggered"
    assert record["correction"]["attempts"] == 0
    assert corrector.calls == []
    assert record["final_field"]["source"] == "original"


# ---------------------------------------------------------------------------
# Mode C: CONTRADICTED triggers correction, successful fix
# ---------------------------------------------------------------------------

def test_contradicted_claim_triggers_correction_and_succeeds(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["claims"][0]["verdict"] == CONTRADICTED
    assert len(corrector.calls) == 1
    assert corrector.calls[0][2] == original_text  # flagged_claim_text passed through
    assert record["correction"]["status"] == "corrected"
    assert record["correction"]["attempts"] == 1
    assert record["correction"]["reverification"]["verdict"] == ENTAILED
    assert record["final_field"]["source"] == "corrected"
    assert record["final_field"]["text"] == corrected_text


def test_correction_reproducibility_metadata_reaches_output_record(evidence_pool, config):
    """Regression test: apply_selective_correction() used to key its
    generation-metadata dict as "_corr_meta", which run_case()'s generic
    underscore-strip (meant only for internal bookkeeping like
    baseline["_exact_index"]) then silently dropped from the output record.
    corr_meta (no leading underscore) must survive into record["correction"]."""
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert "corr_meta" in record["correction"]
    assert record["correction"]["corr_meta"]["model"] == "mock-generator"
    assert record["correction"]["corr_meta"]["max_new_tokens"] == 220
    assert record["correction"]["corr_meta"]["do_sample"] is False
    assert record["correction"]["corr_meta"]["seed"] == 42
    assert "corrected_at" in record["correction"]["corr_meta"]


def test_reverification_matches_replacement_by_act_not_just_provision_number(config):
    """Regression test: the replacement-sentence lookup after correction used
    to match on (provision_type, provision_number) only. If the corrected
    paragraph contains an unrelated, unflagged sentence citing the same
    section NUMBER under a DIFFERENT act (e.g. "Section 302" appears in both
    the IPC and some other act), the old code could grab that unrelated
    sentence as if it were the flagged claim's replacement. The match must
    also require the same normalized act."""
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder shall be punished with death or life imprisonment.",
        source_url="https://example.invalid/1", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    other302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Some Other Act, 1999",
        act="The Some Other Act, 1999", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Unrelated provision text, also numbered 302.",
        source_url="https://example.invalid/2", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Some Other Act, 1999"),
    )
    all_usable = [ipc302, other302]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }

    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    # The unflagged sentence (same section NUMBER, different act) is placed
    # FIRST so a number-only match would greedily pick it over the real
    # replacement that follows.
    corrected_text = (
        "Section 302 of the Some Other Act, 1999 remains applicable here. "
        "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    )
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    # Deliberately do NOT script the "Some Other Act" sentence as a
    # hypothesis: if the buggy code path picks it, ScriptedVerifier raises
    # AssertionError on an unexpected hypothesis, failing the test loudly.
    ipc_replacement_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        ipc_replacement_sentence: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "corrected"
    assert record["correction"]["reverification"]["claim_text"] == ipc_replacement_sentence
    assert record["correction"]["reverification"]["evidence_id"] == "Section 302 in The Indian Penal Code, 1860"
    assert record["correction"]["reverification"]["verdict"] == ENTAILED


# ---------------------------------------------------------------------------
# Mode C: correction attempted but still fails -> original text kept,
# never silently ships an unverified "fixed" version.
# ---------------------------------------------------------------------------

def test_correction_failure_keeps_original_text_but_flags_status(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    still_wrong_text = "Section 302 of the Indian Penal Code, 1860 prescribes a small fine only."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        still_wrong_text: _vr(CONTRADICTED, confidence=0.81),
    })
    corrector = ScriptedCorrector(still_wrong_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "correction_failed"
    assert record["correction"]["attempts"] == 1  # never retries
    assert record["final_field"]["source"] == "correction_failed"
    assert record["final_field"]["text"] == original_text  # NOT the still-wrong regenerated text
    assert record["correction"]["regenerated_text"] == still_wrong_text  # kept for inspection only


def test_correction_that_changes_the_citation_itself_is_rejected_not_shipped(evidence_pool, config):
    # Citation-preservation safety condition: a "correction" must fix the
    # WRONG CLAIM ABOUT the cited provision, never swap in a DIFFERENT
    # provision/act to dodge the contradiction. If the corrector rewrites
    # the flagged sentence's own citation (here: Section 302 -> Section
    # 304, a real, different IPC provision with real evidence of its own),
    # the re-extracted replacement no longer carries the ORIGINAL citation
    # identity the correction was scoped to, so it can never be found by
    # the ordinal-matched re-verification lookup — status must stay
    # "correction_failed", the same as a genuine re-verification failure,
    # never silently accepted as "corrected".
    exact_index, all_usable = evidence_pool
    ipc304 = EvidenceRecord(
        dataset_citation_key="Section 304 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="304",
        subsection=None, canonical_text="Whoever commits culpable homicide not amounting to murder...",
        source_url="https://example.invalid/2", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    all_usable_with_304 = all_usable + [ipc304]
    exact_index_with_304 = dict(exact_index)
    exact_index_with_304[("Section", "304", None, ipc304.act_norm)] = ipc304

    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    # The corrector swaps in an entirely different, real citation instead of
    # fixing the flagged one — must never be accepted as though it were a
    # legitimate fix for the ORIGINAL Section 302 claim.
    citation_swapped_text = "Section 304 of the Indian Penal Code, 1860 prescribes a fine only."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        # Deliberately NOT scripting citation_swapped_text with ENTAILED:
        # if the buggy code path re-verifies it anyway, ScriptedVerifier
        # raises on the unexpected hypothesis, failing the test loudly
        # rather than silently passing.
    })
    corrector = ScriptedCorrector(citation_swapped_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index_with_304, all_usable=all_usable_with_304, config=config)

    assert record["correction"]["status"] == "correction_failed"
    assert record["correction"]["reverification"] is None
    assert record["final_field"]["source"] == "correction_failed"
    assert record["final_field"]["text"] == original_text


# ---------------------------------------------------------------------------
# Mode C: NOT_ENOUGH_INFORMATION (low confidence, evidence present) also
# triggers correction; ENTAILED never does.
# ---------------------------------------------------------------------------

def test_low_confidence_nei_triggers_correction_entailed_does_not(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])

    # ENTAILED case: no correction should be triggered.
    generator = FakeGenerator(text)
    verifier_entailed = ScriptedVerifier({text: _vr(ENTAILED, confidence=0.96)})
    corrector = ScriptedCorrector("unused")
    record = run_case(case, "C", generator, verifier_entailed, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "not_triggered"
    assert corrector.calls == []

    # NOT_ENOUGH_INFORMATION (low_confidence) case: correction should trigger.
    corrector2 = ScriptedCorrector("Section 302 of the Indian Penal Code, 1860 corrected")
    generator2 = FakeGenerator(text)
    verifier_nei2 = ScriptedVerifier({
        text: _vr(NOT_ENOUGH_INFORMATION, confidence=0.55, sub_reason="low_confidence"),
        "Section 302 of the Indian Penal Code, 1860 corrected": _vr(ENTAILED, confidence=0.9),
    })
    record2 = run_case(case, "C", generator2, verifier_nei2, corrector2,
                        exact_index=exact_index, all_usable=all_usable, config=config)
    assert record2["correction"]["status"] == "corrected"


def test_genuine_high_confidence_neutral_does_not_trigger_correction(evidence_pool, config):
    """A high-confidence 'neutral' NLI prediction is a legitimate
    NOT_ENOUGH_INFORMATION verdict on its own — the design only gates
    correction on the *low-confidence-downgrade* flavor of NEI, not on
    every NEI verdict. (Caught as a real bug while implementing this
    prototype; this test pins the fix.)"""
    exact_index, all_usable = evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(text)
    verifier = ScriptedVerifier({
        text: _vr(NOT_ENOUGH_INFORMATION, confidence=0.86, sub_reason=None)  # genuine neutral, high confidence
    })
    corrector = ScriptedCorrector("unused")

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["claims"][0]["verdict"] == NOT_ENOUGH_INFORMATION
    assert record["claims"][0]["sub_reason"] is None
    assert record["correction"]["status"] == "not_triggered"
    assert corrector.calls == []


# ---------------------------------------------------------------------------
# evidence_match_method metadata preservation
# ---------------------------------------------------------------------------

def test_evidence_match_method_preserved_for_matched_and_unmatched_claims(evidence_pool, config):
    """Regression test: generate_and_parse() used to key this field as
    "_evidence_match_method", which run_case()'s underscore-strip (meant
    only for internal bookkeeping like baseline["_exact_index"]) then
    silently dropped from the output record. evidence_match_method is
    legitimate reproducibility metadata and must survive into
    record["claims"][i]."""
    exact_index, all_usable = evidence_pool
    text = (
        "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder. "
        "Section 999 of the Unrelated Act, 2001 governs this matter."
    )
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(text)

    record = run_case(case, "A", generator, verifier=None, corrector=None,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert len(record["claims"]) == 2
    assert record["claims"][0]["evidence_match_method"] == "exact_normalized"
    assert record["claims"][1]["evidence_match_method"] == "no_evidence"
    assert record["claims"][1]["verdict"] == NO_EVIDENCE


# ---------------------------------------------------------------------------
# Deterministic seed threads through every reproducibility-relevant block
# ---------------------------------------------------------------------------

def test_assertion_text_surfaces_in_output_record_additively(two_claim_evidence_pool, config):
    """assertion_text is an additive claim-record field (claim granularity
    work) — must survive into the output record and default to claim_text
    for ordinary (non-bundled) claims, changing nothing about existing
    behaviour."""
    exact_index, all_usable = two_claim_evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(text)

    record = run_case(case, "A", generator, verifier=None, corrector=None,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["claims"][0]["assertion_text"] == record["claims"][0]["claim_text"] == text


def test_deterministic_seed_threads_through_output_record(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["reproducibility"]["seed"] == config["seed"]
    assert record["generated_field"]["generation_params"]["seed"] == config["seed"]
    assert record["correction"]["corr_meta"]["seed"] == config["seed"]


# ---------------------------------------------------------------------------
# Selective correction scope enforcement: unflagged claims must survive
# verbatim; if the corrector touches one anyway, the run is flagged and the
# corrected text is never shipped.
# ---------------------------------------------------------------------------

def test_unflagged_claim_preserved_verbatim_when_correction_succeeds(two_claim_evidence_pool, config):
    exact_index, all_usable = two_claim_evidence_pool
    flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines public servants."
    original_text = f"{flagged_sentence} {unflagged_sentence}"
    corrected_flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    corrected_text = f"{corrected_flagged_sentence} {unflagged_sentence}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        flagged_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_sentence: _vr(ENTAILED, confidence=0.97),
        corrected_flagged_sentence: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "corrected"
    assert unflagged_sentence in record["final_field"]["text"]
    assert record["final_field"]["text"] == corrected_text


def test_correction_scope_violation_when_unflagged_claim_altered(two_claim_evidence_pool, config):
    exact_index, all_usable = two_claim_evidence_pool
    flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines public servants."
    original_text = f"{flagged_sentence} {unflagged_sentence}"
    corrected_flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    # The corrector was only supposed to touch the flagged sentence, but
    # here it also reworded the unflagged one — this must be caught.
    altered_unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines a public official."
    corrected_text = f"{corrected_flagged_sentence} {altered_unflagged_sentence}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        flagged_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_sentence: _vr(ENTAILED, confidence=0.97),
        # Deliberately no script for corrected_flagged_sentence or
        # altered_unflagged_sentence: the scope violation must be caught
        # BEFORE any re-verification call, so neither should ever be looked
        # up. A ScriptedVerifier AssertionError on an unexpected hypothesis
        # would fail this test loudly if that guarantee is broken.
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "correction_scope_violation"
    assert record["correction"]["original_field_text"] == original_text
    assert record["correction"]["regenerated_text"] == corrected_text
    assert record["correction"]["reverification"] is None
    # The corrupted text must never be shipped as the final field.
    assert record["final_field"]["source"] == "correction_scope_violation"
    assert record["final_field"]["text"] == original_text


# ---------------------------------------------------------------------------
# Regression tests: two claims sharing one citation identity
# (provision_type, provision_number, act_norm) — the shape that produced a
# real natural-data bug (see verifier_framing_natural_validation.md §8c).
# The re-verification lookup used to match by citation identity alone and
# take the FIRST same-citation claim found in the corrected text, which
# silently re-verified the WRONG sentence whenever an unflagged claim
# shared the flagged claim's citation and happened to come first. The fix
# matches by ordinal position among same-citation claims instead.
# ---------------------------------------------------------------------------

def test_replacement_matched_by_ordinal_position_when_claims_share_citation(
    shared_citation_evidence_pool, config
):
    """(a) two claims share one citation; (b) correcting claim B must not
    cause claim A (same citation, unflagged, appears first) to be the one
    re-verified."""
    exact_index, all_usable = shared_citation_evidence_pool
    claim_a = "Section 420 of the Indian Penal Code, 1860 is one of the provisions relied upon in this case."
    claim_b_original = "Section 420 of the Indian Penal Code, 1860 requires no proof of dishonest intention."
    claim_b_corrected = "Section 420 of the Indian Penal Code, 1860 requires proof of dishonest intention to deceive."
    original_text = f"{claim_a} {claim_b_original}"
    # claim_a copied verbatim; only claim_b (which comes second) is rewritten.
    corrected_text = f"{claim_a} {claim_b_corrected}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        claim_a: _vr(ENTAILED, confidence=0.95),            # never flagged
        claim_b_original: _vr(CONTRADICTED, confidence=0.9),
        # Only the ACTUAL replacement sentence is scripted for
        # re-verification. If the bug were present, the buggy lookup would
        # instead pick claim_a's (unchanged, already-scripted) text as the
        # "replacement" — silently succeeding with the WRONG claim_text
        # rather than raising, which is why we assert on claim_text below
        # rather than relying on an unscripted-hypothesis error.
        claim_b_corrected: _vr(ENTAILED, confidence=0.92),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    claim_b_id = next(c["claim_id"] for c in record["claims"] if c["claim_text"] == claim_b_original)
    assert record["correction"]["triggered_for_claim_id"] == claim_b_id

    # The core regression check: re-verification must be against the
    # actually-corrected claim_b sentence, never claim_a.
    assert record["correction"]["reverification"]["claim_text"] == claim_b_corrected
    assert record["correction"]["reverification"]["verdict"] == ENTAILED
    assert record["correction"]["status"] == "corrected"

    # (c) the unchanged claim (claim_a) survives byte-identical in the
    # shipped text.
    assert claim_a in record["final_field"]["text"]
    assert record["final_field"]["text"] == corrected_text


def test_scope_violation_still_caught_when_shared_citation_claim_altered(
    shared_citation_evidence_pool, config
):
    """(d) the ordinal-position fix must not weaken scope enforcement: if
    the corrector edits the OTHER same-citation claim instead of (or as
    well as) the flagged one, _scope_violation() still runs first and
    unconditionally rejects it, before any re-verification is attempted."""
    exact_index, all_usable = shared_citation_evidence_pool
    claim_a = "Section 420 of the Indian Penal Code, 1860 is one of the provisions relied upon in this case."
    claim_b_original = "Section 420 of the Indian Penal Code, 1860 requires no proof of dishonest intention."
    claim_b_corrected = "Section 420 of the Indian Penal Code, 1860 requires proof of dishonest intention to deceive."
    altered_claim_a = "Section 420 of the Indian Penal Code, 1860 is not relevant to this case."
    original_text = f"{claim_a} {claim_b_original}"
    bad_corrected_text = f"{altered_claim_a} {claim_b_corrected}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        claim_a: _vr(ENTAILED, confidence=0.95),
        claim_b_original: _vr(CONTRADICTED, confidence=0.9),
        # Deliberately nothing scripted for claim_b_corrected/altered_claim_a:
        # the scope violation must be caught BEFORE any re-verification call.
    })
    corrector = ScriptedCorrector(bad_corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "correction_scope_violation"
    assert record["correction"]["reverification"] is None
    assert record["final_field"]["source"] == "correction_scope_violation"
    assert record["final_field"]["text"] == original_text


def test_atomic_scope_check_off_by_default(config):
    assert config.get("correction", {}).get("atomic_scope_check", False) is False


# ---------------------------------------------------------------------------
# Regression tests: atomic_scope_check (opt-in, default off) — the
# assertion_text-based scope check that lets a narrowly-scoped edit inside
# a bundled multi-citation sentence ship, instead of being rejected purely
# because other claims share that same sentence as their claim_text.
# ---------------------------------------------------------------------------

def _bundled_sentence_claims(assertion_texts: dict[str, str], full_sentence: str) -> list[dict]:
    """Build claim dicts the way generate_and_parse() would: same
    claim_text (the shared sentence) for every claim, but each with its
    own (possibly narrower) assertion_text — assertion_texts maps
    claim_id -> its assertion_text."""
    return [
        {"claim_id": cid, "claim_text": full_sentence, "assertion_text": at}
        for cid, at in assertion_texts.items()
    ]


def test_atomic_scope_check_ships_a_narrowly_scoped_edit_legacy_would_reject(
    two_claim_evidence_pool, config
):
    """(atomic-claim fix, core case) Two claims share one bundled sentence
    as claim_text but have DIFFERENT assertion_text (narrower clauses).
    Editing only the flagged claim's own clause must NOT be flagged as a
    scope violation under atomic_scope_check=True, even though the shared
    claim_text changed — but WOULD be flagged under the legacy
    (claim_text-only) default."""
    exact_index, all_usable = two_claim_evidence_pool
    unflagged_clause = "Section 21 of the Indian Penal Code, 1860 defines public servants"
    flagged_clause_original = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only"
    flagged_clause_corrected = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment"
    original_sentence = f"{flagged_clause_original}, while {unflagged_clause}."
    corrected_sentence = f"{flagged_clause_corrected}, while {unflagged_clause}."

    baseline_claims = _bundled_sentence_claims(
        {"c1": flagged_clause_original, "c2": unflagged_clause}, original_sentence
    )

    # Legacy default: claim_text (the full, now-changed shared sentence)
    # must reappear verbatim -> violation, even though c2's own content
    # never changed.
    assert pipeline._scope_violation(baseline_claims, "c1", corrected_sentence) is True
    assert pipeline._scope_violation(
        baseline_claims, "c1", corrected_sentence, use_assertion_text=False
    ) is True

    # Atomic: c2's own (narrower) assertion_text still appears verbatim ->
    # no violation.
    assert pipeline._scope_violation(
        baseline_claims, "c1", corrected_sentence, use_assertion_text=True
    ) is False


def test_atomic_scope_check_still_rejects_when_unflagged_content_actually_changes(
    two_claim_evidence_pool, config
):
    """(legitimate scope violation still caught) If the corrector alters
    content INSIDE the unflagged claim's own assertion_text (not just the
    shared full sentence), atomic_scope_check must still catch it — this
    is a real, substantive scope violation, not a bundling artifact."""
    exact_index, all_usable = two_claim_evidence_pool
    unflagged_clause = "Section 21 of the Indian Penal Code, 1860 defines public servants"
    altered_unflagged_clause = "Section 21 of the Indian Penal Code, 1860 defines public officials"
    flagged_clause_original = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only"
    flagged_clause_corrected = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment"
    original_sentence = f"{flagged_clause_original}, while {unflagged_clause}."
    bad_corrected_sentence = f"{flagged_clause_corrected}, while {altered_unflagged_clause}."

    baseline_claims = _bundled_sentence_claims(
        {"c1": flagged_clause_original, "c2": unflagged_clause}, original_sentence
    )

    assert pipeline._scope_violation(
        baseline_claims, "c1", bad_corrected_sentence, use_assertion_text=True
    ) is True


def test_atomic_scope_check_falls_back_to_claim_text_when_no_assertion_text_present(
    two_claim_evidence_pool, config
):
    """(backward compatibility) A claim dict from a caller that predates
    `assertion_text` (no such key at all) must fall back to `claim_text`
    under atomic_scope_check=True, not crash and not silently pass."""
    exact_index, all_usable = two_claim_evidence_pool
    flagged = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only"
    unflagged = "Section 21 of the Indian Penal Code, 1860 defines public servants"
    original_text = f"{flagged} {unflagged}"
    corrected_text = f"Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment. {unflagged}"

    legacy_claims = [
        {"claim_id": "c1", "claim_text": flagged},        # no "assertion_text" key at all
        {"claim_id": "c2", "claim_text": unflagged},
    ]
    assert pipeline._scope_violation(
        legacy_claims, "c1", corrected_text, use_assertion_text=True
    ) is False  # unflagged text unchanged either way; falls back to claim_text cleanly


def test_atomic_scope_check_is_inert_for_the_synthetic_two_claim_shape(two_claim_evidence_pool, config):
    """Mechanical proof (substitutes for a full GPU synthetic re-run):
    the synthetic stress set's case shape is always exactly 2 claims with
    DIFFERENT citations, sharing no sentence (see
    src/synthetic_stress.py — one corrupted-provision claim, one unrelated
    Article-14 claim, always distinct citations). assertion_text can only
    ever narrow a claim's own citation span WITHIN a shared sentence
    between claims that DO share one; with no shared sentence at all here,
    claim_text and assertion_text are identical for both claims regardless
    of atomic_scope_check, so `_scope_violation`'s outcome is byte-for-byte
    identical whether atomic_scope_check is on or off — proving the
    synthetic GPU baseline (72.2% correction success,
    outputs/framing_comparison_gpu_n59_postfix_metrics.json) cannot be
    affected by this feature without needing to re-run 59 real GPU
    corrections to confirm it."""
    exact_index, all_usable = two_claim_evidence_pool
    flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines public servants."
    original_text = f"{flagged_sentence} {unflagged_sentence}"
    corrected_flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    corrected_text = f"{corrected_flagged_sentence} {unflagged_sentence}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        flagged_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_sentence: _vr(ENTAILED, confidence=0.97),
        corrected_flagged_sentence: _vr(ENTAILED, confidence=0.93),
    })

    results = {}
    for atomic in (False, True):
        cfg = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": atomic}}
        corrector = ScriptedCorrector(corrected_text)
        record = run_case(case, "C", generator, verifier, corrector,
                           exact_index=exact_index, all_usable=all_usable, config=cfg)
        results[atomic] = record["correction"]["status"], record["final_field"]["text"]

    assert results[False] == results[True] == ("corrected", corrected_text)


# ---------------------------------------------------------------------------
# Regression tests: assertion_spans / "respectively" structured-claim
# scope check (atomic_scope_check="assertion_spans"). Unlike the fixtures
# above, these build the claim list via the REAL claim_parser (through
# generate_and_parse -> FakeGenerator), not hand-built dicts, so they
# exercise the genuine parser+pipeline integration end-to-end — this is
# exactly the class of bug (assertion_spans not re-syncing after
# assertion_text narrows) these tests would have caught.
# ---------------------------------------------------------------------------

@pytest.fixture
def respectively_evidence_pool():
    """Evidence for all 4 provisions in the flagship 1991_110 sentence
    (IPC Sections 302, 149, 323, 34) plus 406/420 for the simpler 2-citation
    tests."""
    records = [
        ("302", "Whoever commits murder shall be punished with death or life imprisonment."),
        ("149", "If an offence is committed by any member of an unlawful assembly in "
                 "prosecution of the common object, every such member is liable."),
        ("323", "Whoever voluntarily causes hurt shall be punished with imprisonment."),
        ("34", "Acts done by several persons in furtherance of common intention."),
        ("406", "Whoever commits criminal breach of trust shall be punished with imprisonment."),
        ("420", "Whoever cheats and thereby dishonestly induces delivery of property."),
    ]
    all_usable = [
        EvidenceRecord(
            dataset_citation_key=f"Section {num} in The Indian Penal Code, 1860",
            act="The Indian Penal Code, 1860", provision_type="Section", provision_number=num,
            subsection=None, canonical_text=text,
            source_url=f"https://example.invalid/{num}", audit_verdict="VERIFIED_EXACT",
            act_norm=normalize_act("The Indian Penal Code, 1860"),
        )
        for num, text in records
    ]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


def test_assertion_spans_ships_respectively_edit_legacy_would_reject(
    respectively_evidence_pool, config
):
    """(core case) Two citations share one 'respectively' sentence. Editing
    ONLY the flagged citation's (406's) own description item must NOT be
    flagged under atomic_scope_check='assertion_spans', even though the
    shared sentence changed — but WOULD be flagged under legacy or plain
    assertion_text (since both citations' assertion_text still resolve to
    the same un-narrowed sentence — 'respectively' is not a pattern
    assertion_text alone can safely represent, see the module docstring).
    Uses PremiseAwareScriptedVerifier because both citations share one
    hypothesis (claim_text); only their evidence (premise) differs, as in
    real production."""
    exact_index, all_usable = respectively_evidence_pool
    original_text = (
        "Sections 406 and 420 of the Indian Penal Code, 1860, which respectively deal "
        "with criminal breach of trust and cheating."
    )
    corrected_text = (
        "Sections 406 and 420 of the Indian Penal Code, 1860, which respectively deal "
        "with dishonest misappropriation of entrusted property and cheating."
    )
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = PremiseAwareScriptedVerifier({
        ("criminal breach of trust", original_text): _vr(
            NOT_ENOUGH_INFORMATION, confidence=0.5, sub_reason="low_confidence"),  # 406: triggers
        ("cheats", original_text): _vr(ENTAILED, confidence=0.95),                # 420: does not trigger
        ("criminal breach of trust", corrected_text): _vr(ENTAILED, confidence=0.9),  # 406 re-verification
        ("cheats", corrected_text): _vr(ENTAILED, confidence=0.95),  # 420 sibling-regression re-check: unchanged
    })

    for mode, expect_violation in [(False, None), (True, True), ("assertion_spans", False)]:
        cfg = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": mode}}
        corrector = ScriptedCorrector(corrected_text)
        record = run_case(case, "C", generator, verifier, corrector,
                           exact_index=exact_index, all_usable=all_usable, config=cfg)
        if expect_violation is True:
            assert record["correction"]["status"] == "correction_scope_violation", mode
        elif expect_violation is False:
            assert record["correction"]["status"] != "correction_scope_violation", mode


def test_assertion_spans_still_rejects_when_sibling_description_changes(
    respectively_evidence_pool, config
):
    """(legitimate scope violation still caught) If the corrector alters
    the UNFLAGGED citation's (420's) own description item (not just the
    flagged 406's), atomic_scope_check='assertion_spans' must still catch
    it — a real, substantive scope violation, not a bundling artifact."""
    exact_index, all_usable = respectively_evidence_pool
    original_text = (
        "Sections 406 and 420 of the Indian Penal Code, 1860, which respectively deal "
        "with criminal breach of trust and cheating."
    )
    bad_corrected_text = (
        "Sections 406 and 420 of the Indian Penal Code, 1860, which respectively deal "
        "with criminal breach of trust and theft."
    )
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = PremiseAwareScriptedVerifier({
        ("criminal breach of trust", original_text): _vr(
            NOT_ENOUGH_INFORMATION, confidence=0.5, sub_reason="low_confidence"),
        ("cheats", original_text): _vr(ENTAILED, confidence=0.95),
        # Deliberately no re-verification entries: the scope violation must
        # be caught BEFORE any re-verification call.
    })
    cfg = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": "assertion_spans"}}
    corrector = ScriptedCorrector(bad_corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=cfg)
    assert record["correction"]["status"] == "correction_scope_violation"
    assert record["correction"]["reverification"] is None


def test_assertion_spans_still_rejects_when_sibling_number_silently_changes(
    respectively_evidence_pool, config
):
    """(number-tamper safety net) Even if a sibling's description text is
    untouched, silently changing ITS provision number must still be
    caught — assertion_spans requires both the number and the description
    fragment to survive, specifically to close this gap."""
    exact_index, all_usable = respectively_evidence_pool
    original_text = (
        "Sections 406 and 420 of the Indian Penal Code, 1860, which respectively deal "
        "with criminal breach of trust and cheating."
    )
    bad_corrected_text = (
        "Sections 406 and 421 of the Indian Penal Code, 1860, which respectively deal "
        "with criminal breach of trust and cheating."
    )
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = PremiseAwareScriptedVerifier({
        ("criminal breach of trust", original_text): _vr(
            NOT_ENOUGH_INFORMATION, confidence=0.5, sub_reason="low_confidence"),
        ("cheats", original_text): _vr(ENTAILED, confidence=0.95),
    })
    cfg = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": "assertion_spans"}}
    corrector = ScriptedCorrector(bad_corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=cfg)
    assert record["correction"]["status"] == "correction_scope_violation"


def test_flagship_1991_110_end_to_end_correction_ships_under_assertion_spans(
    respectively_evidence_pool, config
):
    """Explicit end-to-end test for the flagship 1991_110 case: real
    generated text (verbatim from the actual document), real claim
    extraction (4 citations, one shared sentence), a scripted correction
    that fixes ONLY the mislabeled Section 149 ('criminal conspiracy' ->
    a correct description) while leaving the other 3 citations' own
    content untouched. Under legacy/assertion_text this is rejected
    (siblings share the whole sentence); under assertion_spans it ships,
    because the other 3 citations' own (number, description) fragments
    are still verbatim-present."""
    exact_index, all_usable = respectively_evidence_pool
    original_text = (
        "The case was governed by sections 302, 149, 323, and 34 of the Indian Penal "
        "Code, 1860, which respectively deal with murder, criminal conspiracy, "
        "voluntarily causing hurt, and abetting the commission of a non-cognizable "
        "offense."
    )
    corrected_text = (
        "The case was governed by sections 302, 149, 323, and 34 of the Indian Penal "
        "Code, 1860, which respectively deal with murder, vicarious liability for an "
        "unlawful assembly's common object, voluntarily causing hurt, and abetting the "
        "commission of a non-cognizable offense."
    )
    case = Case(document_id="1991_110", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    # PremiseAwareScriptedVerifier: all 4 citations share ONE hypothesis
    # (claim_text is the identical full sentence for every citation in a
    # respectively-bundled sentence — exactly as real apply_verification
    # behaves), so only their evidence (premise) tells them apart, as in
    # production. Only 149 is flagged (0.80 CONTRADICTED, the real
    # recorded verdict for this exact document/claim); 302/323/34 are
    # confident ENTAILED/NEI and never trigger.
    verifier = PremiseAwareScriptedVerifier({
        ("murder", original_text): _vr(ENTAILED, confidence=0.95),
        ("unlawful assembly", original_text): _vr(CONTRADICTED, confidence=0.80),
        ("voluntarily causes hurt", original_text): _vr(ENTAILED, confidence=0.93),
        ("common intention", original_text): _vr(NOT_ENOUGH_INFORMATION, confidence=0.9),
        ("unlawful assembly", corrected_text): _vr(ENTAILED, confidence=0.9),  # 149 re-verification
        # Sibling-regression re-checks (302/323/34): unchanged, still not CONTRADICTED.
        ("murder", corrected_text): _vr(ENTAILED, confidence=0.95),
        ("voluntarily causes hurt", corrected_text): _vr(ENTAILED, confidence=0.93),
        ("common intention", corrected_text): _vr(NOT_ENOUGH_INFORMATION, confidence=0.9),
    })

    # Legacy: rejected (all 4 citations share claim_text == full sentence).
    cfg_legacy = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": False}}
    record_legacy = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                              exact_index=exact_index, all_usable=all_usable, config=cfg_legacy)
    assert record_legacy["correction"]["status"] == "correction_scope_violation"

    # assertion_spans: ships, because 302/323/34's own (number, description)
    # fragments are still verbatim-present in the corrected text.
    cfg_atomic = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": "assertion_spans"}}
    record_atomic = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                              exact_index=exact_index, all_usable=all_usable, config=cfg_atomic)
    assert record_atomic["correction"]["status"] == "corrected"
    assert record_atomic["final_field"]["text"] == corrected_text
    assert record_atomic["correction"]["reverification"]["verdict"] == ENTAILED

    # Unrelated assertions (302, 323, 34's own content) are byte-identical
    # in both the original and shipped text — proving the correction was
    # genuinely confined to the flagged claim.
    for untouched in ("murder", "voluntarily causing hurt",
                       "abetting the commission of a non-cognizable offense"):
        assert untouched in record_atomic["final_field"]["text"]
        assert original_text.count(untouched) == corrected_text.count(untouched)


@pytest.fixture
def ipc_148_evidence_pool():
    """Evidence for the real 1997_1306 sentence (IPC 148, 323, 149 — 304 is
    intentionally left unmatched/NO_EVIDENCE, exactly as this test's
    correction target does not depend on it)."""
    records = [
        ("148", "Whoever is guilty of rioting, being armed with a deadly weapon, shall be punished."),
        ("323", "Whoever voluntarily causes hurt shall be punished with imprisonment."),
        ("149", "If an offence is committed by any member of an unlawful assembly in "
                 "prosecution of the common object, every such member is liable."),
    ]
    all_usable = [
        EvidenceRecord(
            dataset_citation_key=f"Section {num} in The Indian Penal Code, 1860",
            act="The Indian Penal Code, 1860", provision_type="Section", provision_number=num,
            subsection=None, canonical_text=text,
            source_url=f"https://example.invalid/{num}", audit_verdict="VERIFIED_EXACT",
            act_norm=normalize_act("The Indian Penal Code, 1860"),
        )
        for num, text in records
    ]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


def test_real_1997_1306_correction_ships_under_citation_keyword_boundary_split(
    ipc_148_evidence_pool, config
):
    """Explicit end-to-end test for the real natural correction attempt
    that FIRST demonstrated a genuine, previously-blocked fix actually
    shipping (document 1997_1306, batch-2 natural GPU experiment,
    2026-08-27): Qwen's real correction changed Section 148's own clause
    from the wrong 'criminal trespass' to the correct 'rioting' — IPC
    Section 148 is in fact the rioting-while-armed provision — while every
    other citation's own clause (323, 149) is untouched. Legacy AND the
    pre-existing (semicolon/while/parenthetical) assertion_text mechanisms
    both reject this as a scope violation (no semicolon, no 'while', no
    adjacent parenthetical); the citation-keyword-boundary split added
    this phase is what unblocks it."""
    exact_index, all_usable = ipc_148_evidence_pool
    original_text = (
        "Section 148 of the Indian Penal Code, 1860 mandates punishment for criminal "
        "trespass, section 323 prescribes punishment for voluntarily causing hurt, and "
        "section 149 provides for the liability of every member of an unlawful assembly "
        "to the acts done by any one of them in the common object of the assembly."
    )
    corrected_text = (
        "Section 148 of the Indian Penal Code, 1860 mandates punishment for rioting, "
        "section 323 prescribes punishment for voluntarily causing hurt, and section 149 "
        "provides for the liability of every member of an unlawful assembly to the acts "
        "done by any one of them in the common object of the assembly."
    )
    case = Case(document_id="1997_1306", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = PremiseAwareScriptedVerifier({
        ("rioting, being armed", original_text): _vr(
            NOT_ENOUGH_INFORMATION, confidence=0.5, sub_reason="low_confidence"),  # 148: triggers
        ("voluntarily causes hurt", original_text): _vr(ENTAILED, confidence=0.95),  # 323: no trigger
        ("unlawful assembly", original_text): _vr(ENTAILED, confidence=0.93),        # 149: no trigger
        ("rioting, being armed", corrected_text): _vr(ENTAILED, confidence=0.92),    # 148 re-verification
        # Sibling-regression re-checks (323, 149): unchanged, still not CONTRADICTED.
        ("voluntarily causes hurt", corrected_text): _vr(ENTAILED, confidence=0.95),
        ("unlawful assembly", corrected_text): _vr(ENTAILED, confidence=0.93),
    })

    cfg_legacy = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": False}}
    record_legacy = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                              exact_index=exact_index, all_usable=all_usable, config=cfg_legacy)
    assert record_legacy["correction"]["status"] == "correction_scope_violation"

    cfg_atomic = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": "assertion_spans"}}
    record_atomic = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                              exact_index=exact_index, all_usable=all_usable, config=cfg_atomic)
    assert record_atomic["correction"]["status"] == "corrected"
    assert record_atomic["final_field"]["text"] == corrected_text
    assert record_atomic["correction"]["reverification"]["verdict"] == ENTAILED

    for untouched in ("voluntarily causing hurt", "liability of every member of an unlawful assembly"):
        assert untouched in record_atomic["final_field"]["text"]
        assert original_text.count(untouched) == corrected_text.count(untouched)


def test_atomic_scope_check_default_reproduces_legacy_end_to_end(two_claim_evidence_pool, config):
    """(backward compatibility, end-to-end) With atomic_scope_check absent
    from config (the shipped default), run_case()'s full Mode-C behaviour
    for a bundled-sentence scope violation must be BYTE-IDENTICAL to
    before this feature existed."""
    exact_index, all_usable = two_claim_evidence_pool
    flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines public servants."
    original_text = f"{flagged_sentence} {unflagged_sentence}"
    corrected_flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    altered_unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines a public official."
    corrected_text = f"{corrected_flagged_sentence} {altered_unflagged_sentence}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        flagged_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_sentence: _vr(ENTAILED, confidence=0.97),
    })
    corrector = ScriptedCorrector(corrected_text)

    assert "correction" not in config or "atomic_scope_check" not in config.get("correction", {})
    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "correction_scope_violation"
    assert record["final_field"]["text"] == original_text


def test_single_citation_claim_behaviour_unchanged_by_ordinal_fix(evidence_pool, config):
    """(e) the common case — one claim, one citation, no sharing — must
    behave exactly as before the ordinal-position fix (target_ordinal is
    always 0 of 1 here, a no-op degenerate case)."""
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "corrected"
    assert record["correction"]["reverification"]["claim_text"] == corrected_text
    assert record["correction"]["reverification"]["verdict"] == ENTAILED
    assert record["final_field"]["text"] == corrected_text


# ---------------------------------------------------------------------------
# Regression tests: narrow_reverification_hypothesis (opt-in) and the
# independent sibling-regression safety net — Priority 5 of the CPU
# pre-GPU optimization pass.
# ---------------------------------------------------------------------------

def test_narrow_reverification_hypothesis_off_by_default(config):
    assert config.get("correction", {}).get("narrow_reverification_hypothesis", False) is False


def test_narrow_reverification_ships_when_full_sentence_dilutes_confidence(
    ipc_148_evidence_pool, config
):
    """Core case: the FULL bundled sentence re-verifies as NEI (dilution
    from sibling citations' unrelated content — the real, measured
    phenomenon behind this feature; see
    outputs/research_completion_report.md §16a), but the target's own
    narrower assertion_text (a genuine substring of the corrected
    sentence, never fabricated) re-verifies ENTAILED. With
    narrow_reverification_hypothesis=False (default), the correction
    fails. With =True, it ships."""
    exact_index, all_usable = ipc_148_evidence_pool
    original_text = (
        "Section 148 of the Indian Penal Code, 1860 mandates punishment for criminal "
        "trespass, section 323 prescribes punishment for voluntarily causing hurt, and "
        "section 149 provides for the liability of every member of an unlawful assembly "
        "to the acts done by any one of them in the common object of the assembly."
    )
    corrected_text = (
        "Section 148 of the Indian Penal Code, 1860 mandates punishment for rioting, "
        "section 323 prescribes punishment for voluntarily causing hurt, and section 149 "
        "provides for the liability of every member of an unlawful assembly to the acts "
        "done by any one of them in the common object of the assembly."
    )
    narrow_hypothesis = "Section 148 of the Indian Penal Code, 1860 mandates punishment for rioting"
    case = Case(document_id="1997_1306", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = PremiseAwareScriptedVerifier({
        ("rioting, being armed", original_text): _vr(
            NOT_ENOUGH_INFORMATION, confidence=0.5, sub_reason="low_confidence"),
        ("voluntarily causes hurt", original_text): _vr(ENTAILED, confidence=0.95),
        ("unlawful assembly", original_text): _vr(ENTAILED, confidence=0.93),
        # Full-sentence re-verification: diluted, stays NEI (simulates the
        # real measured 0.54 confidence).
        ("rioting, being armed", corrected_text): _vr(
            NOT_ENOUGH_INFORMATION, confidence=0.54, sub_reason="low_confidence"),
        # Narrow-fragment re-verification: the same real evidence, the
        # target's own content in isolation, genuinely ENTAILED.
        ("rioting, being armed", narrow_hypothesis): _vr(ENTAILED, confidence=0.999),
        # Sibling-regression re-checks (only reached when the correction
        # ships, i.e. the narrow-hypothesis run): 323/149 unchanged.
        ("voluntarily causes hurt", corrected_text): _vr(ENTAILED, confidence=0.95),
        ("unlawful assembly", corrected_text): _vr(ENTAILED, confidence=0.93),
    })

    cfg_wide = {**config, "correction": {
        **config.get("correction", {}), "atomic_scope_check": "assertion_spans",
        "narrow_reverification_hypothesis": False,
    }}
    record_wide = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                            exact_index=exact_index, all_usable=all_usable, config=cfg_wide)
    assert record_wide["correction"]["status"] == "correction_failed"
    assert record_wide["correction"]["reverification"]["verdict"] == NOT_ENOUGH_INFORMATION
    assert record_wide["correction"]["reverification"]["reverified_hypothesis"] == corrected_text

    cfg_narrow = {**config, "correction": {
        **config.get("correction", {}), "atomic_scope_check": "assertion_spans",
        "narrow_reverification_hypothesis": True,
    }}
    record_narrow = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                              exact_index=exact_index, all_usable=all_usable, config=cfg_narrow)
    assert record_narrow["correction"]["status"] == "corrected"
    assert record_narrow["correction"]["reverification"]["verdict"] == ENTAILED
    assert record_narrow["correction"]["reverification"]["reverified_hypothesis"] == narrow_hypothesis
    assert record_narrow["final_field"]["text"] == corrected_text


def test_narrow_reverification_never_synthesizes_text(ipc_148_evidence_pool, config):
    """The narrowed hypothesis, whenever used, must always be a genuine
    substring of the corrected text — never a combined/reworded string."""
    exact_index, all_usable = ipc_148_evidence_pool
    original_text = (
        "Section 148 of the Indian Penal Code, 1860 mandates punishment for criminal "
        "trespass, section 323 prescribes punishment for voluntarily causing hurt, and "
        "section 149 provides for the liability of every member of an unlawful assembly "
        "to the acts done by any one of them in the common object of the assembly."
    )
    corrected_text = (
        "Section 148 of the Indian Penal Code, 1860 mandates punishment for rioting, "
        "section 323 prescribes punishment for voluntarily causing hurt, and section 149 "
        "provides for the liability of every member of an unlawful assembly to the acts "
        "done by any one of them in the common object of the assembly."
    )
    claims = claim_parser.extract_claims(corrected_text)
    target = next(c for c in claims if c.citation_extracted.provision_number == "148")
    assert target.assertion_text in corrected_text  # genuine substring, not synthesized


def test_sibling_regression_check_rejects_a_genuine_regression(
    respectively_evidence_pool, config
):
    """If a sibling's own required (assertion_spans) fragments survive —
    so the scope check itself passes — but the sibling's FULL corrected
    sentence has changed enough that an independent re-check finds it now
    genuinely CONTRADICTED its own evidence, the correction must be
    rejected (status: correction_sibling_regression), never shipped, even
    though the target's own re-verification passed."""
    exact_index, all_usable = respectively_evidence_pool
    original_text = (
        "The case was governed by sections 302, 149, 323, and 34 of the Indian Penal "
        "Code, 1860, which respectively deal with murder, criminal conspiracy, "
        "voluntarily causing hurt, and abetting the commission of a non-cognizable "
        "offense."
    )
    # 302's required assertion_spans fragments ("302", "murder") both still
    # appear, so the scope check passes -- but the added "but never
    # manslaughter" clause changes 302's own full sentence enough that an
    # independent re-check (scripted below) finds it CONTRADICTED.
    corrected_text = (
        "The case was governed by sections 302, 149, 323, and 34 of the Indian Penal "
        "Code, 1860, which respectively deal with murder but never manslaughter, "
        "vicarious liability for an unlawful assembly's common object, voluntarily "
        "causing hurt, and abetting the commission of a non-cognizable offense."
    )
    case = Case(document_id="1991_110", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    verifier = PremiseAwareScriptedVerifier({
        ("murder", original_text): _vr(ENTAILED, confidence=0.95),
        ("unlawful assembly", original_text): _vr(CONTRADICTED, confidence=0.80),
        ("voluntarily causes hurt", original_text): _vr(ENTAILED, confidence=0.93),
        ("common intention", original_text): _vr(NOT_ENOUGH_INFORMATION, confidence=0.9),
        ("unlawful assembly", corrected_text): _vr(ENTAILED, confidence=0.9),  # 149 target: passes
        # Sibling-regression re-checks:
        ("murder", corrected_text): _vr(CONTRADICTED, confidence=0.85),  # 302: genuine regression
        ("voluntarily causes hurt", corrected_text): _vr(ENTAILED, confidence=0.93),  # 323: fine
        ("common intention", corrected_text): _vr(NOT_ENOUGH_INFORMATION, confidence=0.9),  # 34: fine
    })
    cfg = {**config, "correction": {**config.get("correction", {}), "atomic_scope_check": "assertion_spans"}}

    record = run_case(case, "C", generator, verifier, ScriptedCorrector(corrected_text),
                       exact_index=exact_index, all_usable=all_usable, config=cfg)

    assert record["correction"]["status"] == "correction_sibling_regression"
    assert len(record["correction"]["sibling_regressions"]) == 1
    assert record["correction"]["sibling_regressions"][0]["verdict"] == CONTRADICTED
    # Never shipped: final field reverts to the original, untouched text.
    assert record["final_field"]["source"] == "correction_sibling_regression"
    assert record["final_field"]["text"] == original_text


def test_sibling_regression_check_does_not_run_under_legacy_mode(
    two_claim_evidence_pool, config
):
    """The extra re-verification calls must only happen when a relaxed
    (atomic) scope-check mode is active — under legacy (the shipped
    default), the full-sentence preservation requirement already makes
    sibling regressions structurally impossible, so this check must not
    fire (and, more concretely here, must not make any extra verify()
    calls the ScriptedVerifier hasn't been told about)."""
    exact_index, all_usable = two_claim_evidence_pool
    flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    unflagged_sentence = "Section 21 of the Indian Penal Code, 1860 defines public servants."
    original_text = f"{flagged_sentence} {unflagged_sentence}"
    corrected_flagged_sentence = "Section 302 of the Indian Penal Code, 1860 prescribes death or life imprisonment."
    corrected_text = f"{corrected_flagged_sentence} {unflagged_sentence}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    generator = FakeGenerator(original_text)
    # Deliberately NOT scripting ("Section 21...", corrected_text) as a
    # sibling-regression re-check hypothesis: if the check ran under
    # legacy mode, ScriptedVerifier would raise on the unexpected lookup.
    verifier = ScriptedVerifier({
        flagged_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_sentence: _vr(ENTAILED, confidence=0.97),
        corrected_flagged_sentence: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedCorrector(corrected_text)

    record = run_case(case, "C", generator, verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)  # legacy default

    assert record["correction"]["status"] == "corrected"
    assert record["correction"]["sibling_regressions"] == []
