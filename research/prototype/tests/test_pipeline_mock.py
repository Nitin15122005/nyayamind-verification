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
from src.generator import GenerationMetadata
from src.corrector import CorrectionMetadata
from src.verifier import VerificationResult, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.evidence_matcher import NO_EVIDENCE
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
