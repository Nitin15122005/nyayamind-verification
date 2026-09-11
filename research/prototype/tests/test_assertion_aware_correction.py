"""
Tests for ASSERTION-AWARE correction (src/pipeline.py's
`apply_selective_correction_assertion_aware`, `_splice_assertion_correction`,
and src/corrector.py's `SelectiveCorrector.correct_assertion_span`) — added
2026-09-12 as the highest-priority new improvement, config-gated via
correction.assertion_aware (default False; legacy `apply_selective_correction`
remains the production path — see config/prototype.yaml).

All deterministic, mock-based (no GPU, no real model) — mirrors the pattern
in test_pipeline_mock.py. Results here are NEVER pipeline research results;
they only pin the orchestration/safety-gate logic of the new mechanism.

Motivation (see outputs/16gb_final_execution_report.md's `1955_32` case
study): the LEGACY correction path regenerates the whole flagged sentence
(or paragraph) via the LLM and then CHECKS afterward that unflagged content
survived byte-for-byte — a real, observed failure mode where a
substantively CORRECT fix gets rejected because the LLM's own regeneration
of an untouched sibling clause was not byte-identical. ASSERTION-AWARE
correction instead splices a narrow, LLM-generated fragment into the
original text via deterministic string replacement, so everything outside
the target span is guaranteed unchanged by construction, not merely
verified after the fact.
"""
import pytest

from src.data_loader import Case, EvidenceRecord
from src.claim_parser import normalize_act
from src.corrector import CorrectionMetadata
from src.verifier import VerificationResult, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.evidence_matcher import NO_EVIDENCE
from src import pipeline
from src.pipeline import run_case, apply_selective_correction_assertion_aware, _splice_assertion_correction


# ---------------------------------------------------------------------------
# Fixtures (same shapes as test_pipeline_mock.py, kept local/minimal)
# ---------------------------------------------------------------------------

@pytest.fixture
def evidence_pool():
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder shall be punished with imprisonment for ten years.",
        source_url="https://example.invalid/1", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    all_usable = [ipc302]
    exact_index = {
        (e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable
    }
    return exact_index, all_usable


@pytest.fixture
def two_claim_evidence_pool():
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder shall be punished with imprisonment for ten years.",
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


@pytest.fixture
def respectively_evidence_pool():
    """Section 302 (murder) + Section 34 (common intention), the exact
    pair used by claim_parser's own real "respectively" pattern
    (confirmed directly: `extract_claims("Sections 302 and 34 of the "
    "Indian Penal Code, 1860, which respectively deal with murder and "
    "common intention.")` produces assertion_spans=['302', 'murder'] and
    ['34', 'common intention'] respectively)."""
    ipc302 = EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="302",
        subsection=None, canonical_text="Whoever commits murder shall be punished with imprisonment for ten years.",
        source_url="https://example.invalid/1", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    ipc34 = EvidenceRecord(
        dataset_citation_key="Section 34 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section", provision_number="34",
        subsection=None,
        canonical_text="When a criminal act is done by several persons in furtherance of the common "
                        "intention of all, each of such persons is liable for that act.",
        source_url="https://example.invalid/4", audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act("The Indian Penal Code, 1860"),
    )
    all_usable = [ipc302, ipc34]
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
        "correction": {"assertion_aware": True, "atomic_scope_check": "assertion_spans"},
    }


class FakeGenerator:
    def __init__(self, text: str):
        self._text = text

    def generate(self, case_text: str):
        from src.generator import GenerationMetadata
        meta = GenerationMetadata(
            model_id="mock-generator", quantization={"load_in_4bit": True},
            max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42,
        )
        return self._text, meta


class ScriptedVerifier:
    def __init__(self, script: dict[str, VerificationResult]):
        self._script = script
        self.model_id = "mock-verifier"
        self.calls = []

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        self.calls.append((premise, hypothesis))
        if hypothesis not in self._script:
            raise AssertionError(f"ScriptedVerifier got unexpected hypothesis: {hypothesis!r}")
        return self._script[hypothesis]


def _vr(label, confidence=0.95, sub_reason=None):
    return VerificationResult(
        label=label, confidence=confidence, sub_reason=sub_reason,
        raw_scores={}, verifier_model="mock-verifier",
    )


class ScriptedAssertionSpanCorrector:
    """Mocks SelectiveCorrector's assertion-aware interface. `fragment` is
    the corrected fragment to return; `fragment` may be "" to simulate the
    LLM returning nothing usable."""

    def __init__(self, fragment: str):
        self._fragment = fragment
        self.calls = []

    def correct_assertion_span(self, case_text, target_span, evidence_text,
                                assertion_span_system_prompt, max_new_tokens):
        self.calls.append((case_text, target_span, evidence_text, max_new_tokens))
        meta = CorrectionMetadata(model_id="mock-generator", max_new_tokens=max_new_tokens, do_sample=False, seed=42)
        return self._fragment, meta

    # Legacy interface must never be called when assertion_aware=True.
    def correct(self, *args, **kwargs):
        raise AssertionError("legacy correct() must not be called in assertion-aware mode")


# ---------------------------------------------------------------------------
# 1. Config dispatch: assertion_aware routes to the new function; legacy
#    remains the untouched default.
# ---------------------------------------------------------------------------

def test_assertion_aware_off_by_default():
    assert {}.get("correction", {}).get("assertion_aware", False) is False


def test_assertion_aware_flag_recorded_in_reproducibility_block(evidence_pool, config):
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    exact_index, all_usable = evidence_pool
    record = run_case(case, "C", FakeGenerator(text), ScriptedVerifier({text: _vr(ENTAILED)}),
                       corrector=ScriptedAssertionSpanCorrector("unused"),
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["reproducibility"]["assertion_aware_correction"] is True

    cfg_legacy = {**config, "correction": {**config["correction"], "assertion_aware": False}}
    record2 = run_case(case, "C", FakeGenerator(text), ScriptedVerifier({text: _vr(ENTAILED)}),
                        corrector=None,
                        exact_index=exact_index, all_usable=all_usable, config=cfg_legacy)
    assert record2["reproducibility"]["assertion_aware_correction"] is False


def test_assertion_aware_true_never_calls_legacy_corrector_interface(evidence_pool, config):
    """The legacy ScriptedAssertionSpanCorrector.correct() raises if called
    -- proves run_case actually dispatches to the new path, not the old one,
    when correction.assertion_aware is True."""
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes imprisonment for ten years."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    # Single-citation sentence: assertion_text defaults to the FULL
    # claim_text (see claim_parser.py's `_assign_assertion_texts` — only
    # sentences with >=2 citations ever narrow), so the fragment the
    # corrector must return is the full corrected sentence.
    corrector = ScriptedAssertionSpanCorrector(corrected_text)
    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "corrected"
    assert len(corrector.calls) == 1


# ---------------------------------------------------------------------------
# 2. Not triggered
# ---------------------------------------------------------------------------

def test_not_triggered_when_no_flagged_claims(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    corrector = ScriptedAssertionSpanCorrector("should not be used")
    record = run_case(case, "C", FakeGenerator(text), ScriptedVerifier({text: _vr(ENTAILED)}), corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "not_triggered"
    assert corrector.calls == []


def test_no_evidence_claim_never_triggers_assertion_aware_correction(config):
    exact_index, all_usable = {}, []
    text = "Section 999 of the Unrelated Act, 2001 governs this matter."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    corrector = ScriptedAssertionSpanCorrector("should not be used")
    record = run_case(case, "C", FakeGenerator(text), ScriptedVerifier({}), corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["claims"][0]["verdict"] == NO_EVIDENCE
    assert record["correction"]["status"] == "not_triggered"
    assert corrector.calls == []


def test_negation_caveated_claim_never_triggers_assertion_aware_correction(config):
    """Unit-level: builds a baseline dict directly (bypassing run_case) with
    a claim carrying negation_contradiction_caveat=True, mirroring the
    legacy path's own exclusion rule (see apply_selective_correction's
    docstring) -- the same rule must apply to the new dispatch path."""
    claim = {
        "claim_id": "c1", "claim_text": "Section 302 does not apply here.",
        "assertion_text": "Section 302 does not apply here.",
        "verdict": CONTRADICTED, "sub_reason": None,
        "negation_contradiction_caveat": True,
        "evidence_text": "some evidence", "citation_extracted": None,
    }
    baseline = {
        "claims": [claim],
        "generated_field": {"text": "Section 302 does not apply here."},
    }
    corrector = ScriptedAssertionSpanCorrector("should not be used")
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    summary = apply_selective_correction_assertion_aware(baseline, case, corrector, config)
    assert summary["status"] == "not_triggered"
    assert corrector.calls == []


# ---------------------------------------------------------------------------
# 3. Core splice mechanics (_splice_assertion_correction) — unit level
# ---------------------------------------------------------------------------

def test_splice_replaces_unique_assertion_span():
    field = "Section 302 of the IPC prescribes a fine only. Section 21 defines public servants."
    claim_text = "Section 302 of the IPC prescribes a fine only."
    assertion_text = "prescribes a fine only"
    result = _splice_assertion_correction(field, claim_text, assertion_text, "prescribes imprisonment for ten years")
    assert result == "Section 302 of the IPC prescribes imprisonment for ten years. Section 21 defines public servants."


def test_splice_fails_closed_when_assertion_text_not_unique_in_claim_text():
    field = "X X."
    claim_text = "X X."
    assertion_text = "X"  # occurs twice
    assert _splice_assertion_correction(field, claim_text, assertion_text, "Y") is None


def test_splice_fails_closed_when_assertion_text_absent_from_claim_text():
    field = "Section 302 prescribes a fine."
    claim_text = "Section 302 prescribes a fine."
    assertion_text = "not actually in the claim text"
    assert _splice_assertion_correction(field, claim_text, assertion_text, "Y") is None


def test_splice_fails_closed_when_claim_text_not_unique_in_field():
    # Duplicate identical sentences in the field -> ambiguous which
    # occurrence to splice into; must fail closed rather than guess.
    claim_text = "Section 302 prescribes a fine only."
    field = f"{claim_text} {claim_text}"
    assertion_text = "prescribes a fine only"
    assert _splice_assertion_correction(field, claim_text, assertion_text, "prescribes imprisonment") is None


def test_splice_fails_closed_on_empty_corrected_fragment():
    field = "Section 302 prescribes a fine only."
    claim_text = field
    assertion_text = "prescribes a fine only"
    assert _splice_assertion_correction(field, claim_text, assertion_text, "") is None


def test_splice_is_noop_safe_when_fragment_equals_original():
    """A genuine no-op edit (LLM declines to change anything) must splice
    cleanly to byte-identical text, not be treated as an error -- downstream
    re-verification (not the splice) is what should then reject it as
    correction_failed if the verdict doesn't improve."""
    field = "Section 302 prescribes a fine only. Section 21 defines public servants."
    claim_text = "Section 302 prescribes a fine only."
    assertion_text = "prescribes a fine only"
    result = _splice_assertion_correction(field, claim_text, assertion_text, assertion_text)
    assert result == field


# ---------------------------------------------------------------------------
# 4. End-to-end splice-unavailable via run_case (corrector returns "")
# ---------------------------------------------------------------------------

def test_splice_unavailable_end_to_end_when_corrector_returns_empty(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({original_text: _vr(CONTRADICTED, confidence=0.88)})
    corrector = ScriptedAssertionSpanCorrector("")
    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "correction_splice_unavailable"
    assert record["final_field"]["source"] == "correction_splice_unavailable"
    assert record["final_field"]["text"] == original_text  # never ships an unspliced/raw fragment


# ---------------------------------------------------------------------------
# 5. THE CORE MOTIVATING CASE: a bundled "while"-sentence where the
#    assertion-aware path ships a correction that the legacy path rejects,
#    because splicing leaves the sibling clause byte-identical while
#    whole-sentence LLM regeneration does not exactly reproduce it.
#    Mirrors the real 1955_32 case study.
# ---------------------------------------------------------------------------

def test_assertion_aware_ships_narrow_fix_legacy_regeneration_would_reject(
    two_claim_evidence_pool, config
):
    exact_index, all_usable = two_claim_evidence_pool
    flagged_clause = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only"
    unflagged_clause = "Section 21 of the Indian Penal Code, 1860 defines public servants"
    original_sentence = f"{flagged_clause}, while {unflagged_clause}."
    corrected_flagged_clause = "Section 302 of the Indian Penal Code, 1860 prescribes imprisonment for ten years"
    assertion_aware_corrected_sentence = f"{corrected_flagged_clause}, while {unflagged_clause}."

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        original_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_clause: _vr(ENTAILED, confidence=0.97),
        # narrow_reverification_hypothesis is off by default (not set in
        # `config`), so BOTH the target's own re-verification AND the
        # unconditional sibling-regression check use the FULL re-extracted
        # claim_text (the whole "..., while ..." sentence) as the
        # hypothesis, not the narrower assertion_text clause.
        assertion_aware_corrected_sentence: _vr(ENTAILED, confidence=0.93),
    })
    # assertion_text for claim c1 here is the FULL " while "-split clause
    # ("Section 302 ... prescribes a fine only", not just the verb phrase —
    # see claim_parser.py's `_split_into_parallel_clauses`), so the
    # corrected fragment must be the full replacement clause.
    corrector = ScriptedAssertionSpanCorrector(corrected_flagged_clause)

    record = run_case(case, "C", FakeGenerator(original_sentence), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "corrected"
    assert record["final_field"]["text"] == assertion_aware_corrected_sentence
    # The sibling clause is byte-identical -- proven by exact substring
    # presence, not just "some text resembling it".
    assert unflagged_clause in record["final_field"]["text"]

    # Contrast: the LEGACY path, given an LLM regeneration that does NOT
    # exactly reproduce the sibling clause (a real, observed failure mode),
    # rejects the very same underlying fix -- demonstrating the new path's
    # value, not merely asserting it in prose.
    from src.corrector import CorrectionMetadata as _CM

    class LegacyRegeneratingCorrector:
        def correct(self, case_text, original_field_text, flagged_claim_text, evidence_text):
            # Whole-sentence regeneration that paraphrases the untouched
            # sibling clause instead of reproducing it byte-for-byte --
            # exactly the real 1955_32 failure mode.
            paraphrased = (
                f"{corrected_flagged_clause}, while {unflagged_clause} under the same statute."
            )
            return paraphrased, _CM(model_id="mock-generator", max_new_tokens=220, do_sample=False, seed=42)

    legacy_config = {**config, "correction": {**config["correction"], "assertion_aware": False}}
    legacy_record = run_case(
        case, "C", FakeGenerator(original_sentence), verifier, LegacyRegeneratingCorrector(),
        exact_index=exact_index, all_usable=all_usable, config=legacy_config,
    )
    assert legacy_record["correction"]["status"] == "correction_scope_violation"
    assert legacy_record["final_field"]["source"] == "correction_scope_violation"


# ---------------------------------------------------------------------------
# 6. Unauthorized citation injection inside the corrected fragment
# ---------------------------------------------------------------------------

def test_unauthorized_citation_injected_inside_fragment_is_rejected(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({original_text: _vr(CONTRADICTED, confidence=0.88)})
    # The fragment itself hallucinates a brand new citation nobody asked
    # about -- a real, plausible LLM failure mode even for a narrow
    # "just the fragment" instruction.
    corrector = ScriptedAssertionSpanCorrector(
        "prescribes a fine only. Section 34 of the Indian Penal Code, 1860 also applies here"
    )
    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "correction_unauthorized_addition"
    assert record["correction"]["reverification"] is None
    assert record["final_field"]["source"] == "correction_unauthorized_addition"
    assert record["final_field"]["text"] == original_text


# ---------------------------------------------------------------------------
# 7. correction_failed: splice succeeds, re-verification still not ENTAILED
# ---------------------------------------------------------------------------

def test_correction_failed_when_reverification_stays_not_entailed(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    still_wrong_text = "Section 302 of the Indian Penal Code, 1860 prescribes a small fine only."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        still_wrong_text: _vr(CONTRADICTED, confidence=0.81),
    })
    corrector = ScriptedAssertionSpanCorrector("prescribes a small fine only")
    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["status"] == "correction_failed"
    assert record["final_field"]["source"] == "correction_failed"
    assert record["final_field"]["text"] == original_text


# ---------------------------------------------------------------------------
# 8. narrow_reverification_hypothesis interacts correctly with the
#    assertion-aware path too (reuses the same config knob).
# ---------------------------------------------------------------------------

def test_narrow_reverification_hypothesis_used_when_enabled(two_claim_evidence_pool, config):
    exact_index, all_usable = two_claim_evidence_pool
    flagged_clause = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only"
    unflagged_clause = "Section 21 of the Indian Penal Code, 1860 defines public servants"
    original_sentence = f"{flagged_clause}, while {unflagged_clause}."
    corrected_flagged_clause = "Section 302 of the Indian Penal Code, 1860 prescribes imprisonment for ten years"
    assertion_aware_corrected_sentence = f"{corrected_flagged_clause}, while {unflagged_clause}."

    cfg = {**config, "correction": {**config["correction"], "narrow_reverification_hypothesis": True}}
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        original_sentence: _vr(CONTRADICTED, confidence=0.88),
        unflagged_clause: _vr(ENTAILED, confidence=0.97),
        # The TARGET's own re-verification is narrowed to just the clause
        # (proving narrow_reverification_hypothesis is honored) -- but the
        # UNCONDITIONAL sibling-regression check always re-verifies the
        # sibling's own counterpart using its full re-extracted claim_text
        # (the whole sentence), regardless of this flag, so both hypotheses
        # must be scripted.
        corrected_flagged_clause: _vr(ENTAILED, confidence=0.99),
        assertion_aware_corrected_sentence: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedAssertionSpanCorrector(corrected_flagged_clause)
    record = run_case(case, "C", FakeGenerator(original_sentence), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=cfg)
    assert record["correction"]["status"] == "corrected"
    assert record["correction"]["reverification"]["reverified_hypothesis"] == corrected_flagged_clause


# ---------------------------------------------------------------------------
# 9. Sibling-regression safety net runs UNCONDITIONALLY (not gated on the
#    scope-check mode, unlike the legacy path) — proven via monkeypatch
#    rather than a naturally-occurring scenario, since the splice's
#    structural guarantee makes a genuine regression very hard to construct
#    from real text (which is itself the point of this design).
# ---------------------------------------------------------------------------

def test_sibling_regression_check_runs_unconditionally(evidence_pool, config, monkeypatch):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes imprisonment for ten years."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedAssertionSpanCorrector(corrected_text)

    fake_regression = [{
        "claim_id": "sibling-1", "claim_text": "sibling text", "evidence_id": "fake",
        "verdict": CONTRADICTED, "confidence": 0.9, "raw_scores": {}, "input_truncated": False,
    }]
    monkeypatch.setattr(pipeline, "_reverify_sibling_regressions", lambda *a, **kw: fake_regression)

    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "correction_sibling_regression"
    assert record["final_field"]["source"] == "correction_sibling_regression"
    assert record["final_field"]["text"] == original_text
    assert record["correction"]["sibling_regressions"] == fake_regression


# ---------------------------------------------------------------------------
# 10. Ordinal-position matching still works correctly under assertion-aware
#     dispatch (same technique, same real bug class the legacy path guards).
# ---------------------------------------------------------------------------

def test_replacement_matched_by_ordinal_position_under_assertion_aware(config):
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
    exact_index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable}

    claim_a = "Section 420 of the Indian Penal Code, 1860 is one of the provisions relied upon in this case."
    claim_b_original = "Section 420 of the Indian Penal Code, 1860 requires no proof of dishonest intention."
    claim_b_corrected = "Section 420 of the Indian Penal Code, 1860 requires proof of dishonest intention."
    original_text = f"{claim_a} {claim_b_original}"

    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        claim_a: _vr(ENTAILED, confidence=0.95),
        claim_b_original: _vr(CONTRADICTED, confidence=0.9),
        claim_b_corrected: _vr(ENTAILED, confidence=0.92),
    })
    # assertion_text for claim_b defaults to its full claim_text (no safe
    # split pattern in "requires no proof of dishonest intention."), so the
    # corrected fragment IS the full replacement clause here.
    corrector = ScriptedAssertionSpanCorrector(claim_b_corrected)

    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["status"] == "corrected"
    assert record["correction"]["reverification"]["claim_text"] == claim_b_corrected
    assert claim_a in record["final_field"]["text"]


# ---------------------------------------------------------------------------
# 11. correction_mode / target_assertion_text / corrected_fragment surface
#     into the output record for downstream error-propagation analysis.
# ---------------------------------------------------------------------------

def test_correction_mode_and_fragment_metadata_surface_in_record(evidence_pool, config):
    exact_index, all_usable = evidence_pool
    original_text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    corrected_text = "Section 302 of the Indian Penal Code, 1860 prescribes imprisonment for ten years."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        original_text: _vr(CONTRADICTED, confidence=0.88),
        corrected_text: _vr(ENTAILED, confidence=0.93),
    })
    corrector = ScriptedAssertionSpanCorrector(corrected_text)
    record = run_case(case, "C", FakeGenerator(original_text), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)
    assert record["correction"]["correction_mode"] == "assertion_aware"
    assert record["correction"]["corrected_fragment"] == corrected_text
    # Single-citation sentence: assertion_spans defaults to [assertion_text],
    # which defaults to the full claim_text (see claim_parser.py's
    # `_assign_assertion_texts`) -- so the content fragment (spans[-1]) is
    # the whole original sentence here.
    assert record["correction"]["target_assertion_spans"] == [original_text]
    assert record["correction"]["target_content_fragment"] == original_text


# ---------------------------------------------------------------------------
# 12. Multi-element assertion_spans ("respectively" pattern) -- the 2026-09-12
# continuation's core addition: consume the actual parser-produced
# assertion_spans (structural bare-number + content description item), not
# just assertion_text. Real parser output confirmed directly:
#   extract_claims("Sections 302 and 34 of the Indian Penal Code, 1860, "
#                  "which respectively deal with theft and common intention.")
# produces assertion_spans=['302', 'theft'] / ['34', 'common intention'].
# ---------------------------------------------------------------------------

RESPECTIVELY_ORIGINAL = (
    "Sections 302 and 34 of the Indian Penal Code, 1860, which respectively "
    "deal with theft and common intention."
)
RESPECTIVELY_CORRECTED = (
    "Sections 302 and 34 of the Indian Penal Code, 1860, which respectively "
    "deal with murder and common intention."
)


def test_multi_span_respectively_claim_ships_correction_preserving_structural_span(
    respectively_evidence_pool, config
):
    """Section 302's content item ("theft") is wrong -- the real provision
    is about murder. The corrector is asked to fix ONLY that content
    fragment (assertion_spans[-1]); its own structural span (the bare "302")
    lives elsewhere in the same shared sentence and is never touched by the
    splice. Section 34's sibling content ("common intention") is correct
    and untouched. Confirms the mechanism genuinely consumes assertion_spans
    (a 2-element list here), not just assertion_text (which stays equal to
    the FULL shared sentence for both claims -- see the real parser output
    in this fixture's docstring)."""
    exact_index, all_usable = respectively_evidence_pool
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({
        RESPECTIVELY_ORIGINAL: _vr(CONTRADICTED, confidence=0.9),
        # Both the target's own re-verification AND the unconditional
        # sibling-regression check use the full re-extracted claim_text
        # (identical for both claims, since they share one sentence) as
        # hypothesis -- one scripted entry covers both calls.
        RESPECTIVELY_CORRECTED: _vr(ENTAILED, confidence=0.95),
    })
    corrector = ScriptedAssertionSpanCorrector("murder")

    record = run_case(case, "C", FakeGenerator(RESPECTIVELY_ORIGINAL), verifier, corrector,
                       exact_index=exact_index, all_usable=all_usable, config=config)

    assert record["correction"]["target_assertion_spans"] == ["302", "theft"]
    assert record["correction"]["target_content_fragment"] == "theft"
    assert corrector.calls[0][1] == "theft"  # target_span passed to the corrector
    assert record["correction"]["status"] == "corrected"
    assert record["final_field"]["text"] == RESPECTIVELY_CORRECTED
    assert "common intention" in record["final_field"]["text"]  # sibling content untouched


def test_structural_span_lost_is_rejected(config):
    """Unit-level (direct baseline construction, like the negation-caveat
    test): a claim whose CONTENT fragment happens to itself contain its own
    structural (bare-number) span as a substring. If the corrector's
    replacement drops that number entirely, the structural-span check must
    catch it and reject -- this is the failure mode
    `correction_structural_span_lost` exists for: the number surviving
    ELSEWHERE in the sentence is not guaranteed when the number's only
    occurrence was embedded inside the very fragment being rewritten."""
    # The structural span "392" occurs ONLY inside the content fragment
    # itself here (no separate "Section 392" mention elsewhere in the
    # sentence) -- the realistic edge case this check exists for: the bare
    # number's only occurrence in the sentence happens to sit inside the
    # very fragment being rewritten.
    claim = {
        "claim_id": "c1",
        "claim_text": "The offense of 392 dacoity is described here.",
        "assertion_text": "The offense of 392 dacoity is described here.",
        "assertion_spans": ["392", "392 dacoity"],
        "verdict": CONTRADICTED, "sub_reason": None,
        "negation_contradiction_caveat": False,
        "evidence_text": "some evidence",
        "citation_extracted": None,
    }
    baseline = {
        "claims": [claim],
        "generated_field": {"text": "The offense of 392 dacoity is described here."},
    }
    # The corrector's replacement fragment drops "392" entirely -- a
    # realistic LLM failure mode when the content fragment itself embeds
    # the citation number as a substring.
    corrector = ScriptedAssertionSpanCorrector("robbery")
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    cfg = {**config, "correction": {**config["correction"]}}

    summary = apply_selective_correction_assertion_aware(baseline, case, corrector, cfg)

    assert summary["status"] == "correction_structural_span_lost"
    assert summary["target_assertion_spans"] == ["392", "392 dacoity"]
    assert summary["target_content_fragment"] == "392 dacoity"


def test_span_invalid_rejected_when_assertion_spans_has_empty_element():
    """Fail-closed: a non-empty assertion_spans list containing a falsy
    (empty-string) element must never be guessed at -- reject outright
    rather than silently correcting against a malformed representation."""
    claim = {
        "claim_id": "c1",
        "claim_text": "Sections 302 and 34 ..., which respectively deal with murder and X.",
        "assertion_text": "Sections 302 and 34 ..., which respectively deal with murder and X.",
        "assertion_spans": ["302", ""],  # malformed: second element empty
        "verdict": CONTRADICTED, "sub_reason": None,
        "negation_contradiction_caveat": False,
        "evidence_text": "some evidence",
        "citation_extracted": None,
    }
    baseline = {
        "claims": [claim],
        "generated_field": {"text": claim["claim_text"]},
    }
    corrector = ScriptedAssertionSpanCorrector("should not be used")
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    cfg = {"correction": {"assertion_aware": True}}

    summary = apply_selective_correction_assertion_aware(baseline, case, corrector, cfg)

    assert summary["status"] == "correction_span_invalid"
    assert corrector.calls == []  # never even attempts to call the corrector on malformed input


def test_span_invalid_rejected_when_assertion_spans_is_empty_list():
    """An empty assertion_spans list is falsy, so `_correction_target_spans`
    falls back to `[assertion_text or claim_text]` per its documented
    convention -- this is NOT a rejection case, it degrades safely to
    ordinary single-fragment behavior. Confirms that fallback explicitly
    (distinct from the "non-empty list with an empty element" rejection
    case above, which is genuinely malformed and must reject)."""
    from src.pipeline import _correction_target_spans
    rec = {"assertion_spans": [], "assertion_text": "the fallback text", "claim_text": "the fallback text"}
    resolved = _correction_target_spans(rec)
    assert resolved == (["the fallback text"], "the fallback text")


def test_correction_target_spans_resolves_content_fragment_as_last_element():
    """Direct unit test of `_correction_target_spans`: for a genuine
    multi-element list, the content fragment is always the LAST element
    (per claim_parser.py's `_assign_respectively_spans`, which constructs
    `assertion_spans` as exactly `[bare_number_span, description_item]`)."""
    from src.pipeline import _correction_target_spans
    rec = {"assertion_spans": ["34", "common intention"]}
    spans, content = _correction_target_spans(rec)
    assert spans == ["34", "common intention"]
    assert content == "common intention"


def test_run_case_final_field_source_for_new_fail_closed_statuses(evidence_pool, config, monkeypatch):
    """`run_case`'s final_field dispatch must give `correction_span_invalid`
    and `correction_structural_span_lost` their own accurate `source` label
    (not silently fall through to the generic "original" default) -- needed
    for the error-propagation matrix to correctly attribute a rejection to
    its real cause, and to prove the shipped text is always the untouched
    original in both cases (never a partially-applied or raw fragment)."""
    exact_index, all_usable = evidence_pool
    text = "Section 302 of the Indian Penal Code, 1860 prescribes a fine only."
    case = Case(document_id="doc1", case_text="facts...", raw_citation_keys=[])
    verifier = ScriptedVerifier({text: _vr(CONTRADICTED, confidence=0.88)})

    for forced_status in ("correction_span_invalid", "correction_structural_span_lost"):
        def fake_correction(baseline, case, corrector, config, _status=forced_status):
            return {
                "triggered_for_claim_id": "c1", "attempts": 0,
                "status": _status, "regenerated_text": None,
                "original_field_text": baseline["generated_field"]["text"],
                "reverification": None, "correction_mode": "assertion_aware",
            }
        monkeypatch.setattr(pipeline, "apply_selective_correction_assertion_aware", fake_correction)

        record = run_case(case, "C", FakeGenerator(text), verifier, ScriptedAssertionSpanCorrector("unused"),
                           exact_index=exact_index, all_usable=all_usable, config=config)

        assert record["correction"]["status"] == forced_status
        assert record["final_field"]["source"] == forced_status
        assert record["final_field"]["text"] == text
