"""
Production-path tests for the configurable premise framing.

These cover the WIRING, not the NLI model: a scripted verifier records the exact
premise string it was handed, so each test asserts on what production actually
sends to the model. No model is loaded and no GPU is touched.

The property under test is an isolated ablation — bare vs labeled premise, with
everything else (threshold, model, claim extraction, evidence matching,
correction logic, generation) held fixed.
"""
from __future__ import annotations

import copy

import pytest

from src import pipeline
from src.data_loader import Case, EvidenceRecord
from src.generator import GenerationMetadata
from src.verifier import (
    VerificationResult, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
    PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED,
)

MURDER_TEXT = ("Whoever commits murder shall be punished with death, or imprisonment "
               "for life, and shall also be liable to fine.")


class RecordingVerifier:
    """Captures every premise it is asked to score, and returns a scripted verdict."""

    model_id = "recording-verifier"

    def __init__(self, verdict=NOT_ENOUGH_INFORMATION, confidence=0.99):
        self.premises: list[str] = []
        self._verdict = verdict
        self._confidence = confidence

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        self.premises.append(premise)
        return VerificationResult(
            label=self._verdict, confidence=self._confidence, sub_reason=None,
            raw_scores={"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0},
            verifier_model=self.model_id,
        )


def _evidence() -> EvidenceRecord:
    return EvidenceRecord(
        dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section",
        provision_number="302", subsection=None, canonical_text=MURDER_TEXT,
        source_url="http://example.com", audit_verdict="VERIFIED_EXACT",
        act_norm="indian penal code 1860",
    )


def _baseline_with_matched_claim() -> dict:
    ev = _evidence()
    return {
        "document_id": "doc-1",
        "case_text": "case",
        "generated_field": {"text": "field"},
        "claims": [{
            "claim_id": "c1",
            "claim_text": "According to Section 302 of the Indian Penal Code, 1860, "
                          "whoever commits murder shall be punished with death.",
            "citation_extracted": {"provision_type": "Section", "provision_number": "302",
                                   "subsection": None, "act_raw": "the Indian Penal Code, 1860",
                                   "act_norm": "indian penal code 1860"},
            "evidence_id": ev.dataset_citation_key,
            "evidence_text": ev.canonical_text,
            "evidence_match_method": "exact_normalized",
            "_evidence_provision": {"provision_type": ev.provision_type,
                                    "provision_number": ev.provision_number, "act": ev.act},
            "verdict": None, "confidence": None, "sub_reason": None, "verifier_model": None,
        }],
    }


# --------------------------------------------------------------------------
# 1. bare framing remains unchanged
# --------------------------------------------------------------------------

def test_bare_framing_sends_the_statute_text_alone():
    """The premise under bare framing must be byte-identical to the evidence
    text — that is what produced every committed output in outputs/."""
    baseline = _baseline_with_matched_claim()
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, PREMISE_FRAMING_BARE)
    assert v.premises == [MURDER_TEXT]


def test_apply_verification_defaults_to_bare_for_callers_that_pass_nothing():
    baseline = _baseline_with_matched_claim()
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v)
    assert v.premises == [MURDER_TEXT]


def test_no_evidence_claims_never_reach_the_verifier_under_either_framing():
    for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
        baseline = _baseline_with_matched_claim()
        baseline["claims"][0]["evidence_text"] = None
        baseline["claims"][0]["verdict"] = "NO_EVIDENCE"
        v = RecordingVerifier()
        pipeline.apply_verification(baseline, v, framing)
        assert v.premises == []


# --------------------------------------------------------------------------
# 2. labeled framing carries the statutory provision identifier
# --------------------------------------------------------------------------

def test_labeled_framing_prepends_the_provision_identifier():
    baseline = _baseline_with_matched_claim()
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, PREMISE_FRAMING_LABELED)
    assert len(v.premises) == 1
    premise = v.premises[0]
    assert premise.startswith("Section 302 of The Indian Penal Code, 1860: ")
    assert "Section" in premise and "302" in premise
    assert "The Indian Penal Code, 1860" in premise
    # The statute text must survive untouched — framing may only ADD the label.
    assert premise.endswith(MURDER_TEXT)


def test_labeled_framing_uses_the_matched_evidence_identity_not_the_claims_citation():
    """A mis-cited claim must not get a premise labeled with its own error: the
    label describes the evidence actually being used as the premise."""
    baseline = _baseline_with_matched_claim()
    baseline["claims"][0]["citation_extracted"] = {
        "provision_type": "Section", "provision_number": "999",
        "subsection": None, "act_raw": "Wrong Act", "act_norm": "wrong act",
    }
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, PREMISE_FRAMING_LABELED)
    assert v.premises[0].startswith("Section 302 of The Indian Penal Code, 1860: ")
    assert "999" not in v.premises[0]
    assert "Wrong Act" not in v.premises[0]


def test_labeled_framing_falls_back_to_bare_when_provision_metadata_missing():
    baseline = _baseline_with_matched_claim()
    baseline["claims"][0]["_evidence_provision"] = None
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, PREMISE_FRAMING_LABELED)
    assert v.premises == [MURDER_TEXT]


# --------------------------------------------------------------------------
# 3. the configured framing is passed through production
# --------------------------------------------------------------------------

def _config(framing=None) -> dict:
    cfg = {
        "seed": 42,
        "generation": {"model_id": "gen", "quantization": {}},
        "evidence_matching": {"fuzzy_token_overlap_threshold": 0.8},
        "verification": {"model_id": "ver", "confidence_threshold": 0.70},
        "correction": {"max_attempts": 1, "system_prompt": "x", "max_new_tokens": 10,
                       "do_sample": False},
    }
    if framing is not None:
        cfg["verification"]["premise_framing"] = framing
    return cfg


def test_resolve_reads_the_configured_value():
    assert pipeline.resolve_premise_framing(_config("labeled")) == PREMISE_FRAMING_LABELED
    assert pipeline.resolve_premise_framing(_config("bare")) == PREMISE_FRAMING_BARE


def test_resolve_defaults_to_bare_when_key_absent():
    """An older config predating this option must keep producing bare-framing
    runs rather than silently switching behaviour."""
    assert pipeline.resolve_premise_framing(_config()) == PREMISE_FRAMING_BARE
    assert pipeline.resolve_premise_framing({}) == PREMISE_FRAMING_BARE


def test_shipped_config_locks_the_2026_08_27_final_production_decision():
    """Guards the committed prototype.yaml itself against silent drift from
    the final production configuration decided in FINAL_PRODUCTION_CONFIG.md
    (2026-08-27, extended 2026-09-09): premise_framing="labeled",
    use_evidence_v1=true, atomic_scope_check="assertion_spans",
    narrow_reverification_hypothesis=true, narrow_primary_hypothesis=true,
    confidence_threshold unchanged at 0.70. See that document for the full,
    quantitative justification of each value (evidence_v1_independent_
    audit.md, final_gpu_validation.md, threshold_sensitivity_analysis.md,
    the targeted labeled-framing correction validation, and
    narrow_primary_hypothesis_benchmark_report.md).

    Formerly named test_shipped_config_default_is_bare and asserted the
    OPPOSITE of every value below — renamed and rewritten, not just edited,
    so its git history is honest about this being a deliberate reversal of
    the prior default, not an accidental relaxation of a safety test."""
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "prototype.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert cfg["verification"]["premise_framing"] == PREMISE_FRAMING_LABELED
    assert cfg["use_evidence_v1"] is True
    assert cfg["correction"]["atomic_scope_check"] == "assertion_spans"
    assert cfg["correction"]["narrow_reverification_hypothesis"] is True
    assert cfg["verification"]["narrow_primary_hypothesis"] is True
    # Threshold explicitly NOT changed — threshold_sensitivity_analysis.md
    # found 0.70 within 0.002 macro-F1 of optimal under both framings.
    assert cfg["verification"]["confidence_threshold"] == 0.70
    assert cfg["verification"]["model_id"] == "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"


def test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output():
    """The historical (pre-2026-08-27) production behaviour must remain
    reachable by explicitly setting every flag back to its old value — this
    project never deletes the ability to reproduce a prior committed result,
    it only changes what the DEFAULT is. This test pins that the old
    combination still parses and resolves exactly as it always did, using
    the same resolve_premise_framing() production code path."""
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "prototype.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    historical = copy.deepcopy(cfg)
    historical["use_evidence_v1"] = False
    historical["verification"]["premise_framing"] = "bare"
    historical["correction"]["atomic_scope_check"] = False
    historical["correction"]["narrow_reverification_hypothesis"] = False
    assert pipeline.resolve_premise_framing(historical) == PREMISE_FRAMING_BARE


@pytest.mark.parametrize("framing,expect_label", [("bare", False), ("labeled", True)])
def test_run_case_threads_config_framing_to_the_verifier(framing, expect_label):
    """End-to-end through run_case(): what production sends depends only on the
    configured framing."""
    ev = _evidence()

    class FakeGenerator:
        model_id = "fake"

        def generate(self, case_text):
            return (
                "According to Section 302 of the Indian Penal Code, 1860, whoever "
                "commits murder shall be punished with death.",
                GenerationMetadata(
                    model_id="fake", quantization={}, max_new_tokens=10, do_sample=False,
                    temperature=1.0, top_p=1.0, seed=42,
                ),
            )

    exact_index = {("Section", "302", None, "indian penal code 1860"): ev}
    v = RecordingVerifier()
    record = pipeline.run_case(
        Case(document_id="d1", case_text="facts", raw_citation_keys=[]),
        "B", FakeGenerator(), v, None, exact_index, [ev], _config(framing),
    )
    assert v.premises, "verifier was never called — claim/evidence match failed"
    assert all(p.startswith("Section 302 of ") for p in v.premises) is expect_label
    assert record["reproducibility"]["premise_framing"] == framing


def test_reproducibility_block_records_the_framing_used():
    ev = _evidence()

    class FakeGenerator:
        model_id = "fake"

        def generate(self, case_text):
            return ("Section 302 of the Indian Penal Code, 1860 applies.",
                    GenerationMetadata(model_id="fake", quantization={}, max_new_tokens=10,
                                       do_sample=False, temperature=1.0, top_p=1.0, seed=42))

    rec = pipeline.run_case(
        Case(document_id="d1", case_text="facts", raw_citation_keys=[]),
        "A", FakeGenerator(), RecordingVerifier(), None,
        {("Section", "302", None, "indian penal code 1860"): ev}, [ev], _config("labeled"),
    )
    # Mode A runs no verification, so there is no framing to report.
    assert rec["reproducibility"]["premise_framing"] is None


def test_internal_provision_bookkeeping_is_stripped_from_output():
    """Enabling labeled framing must not change the emitted record schema, or
    new runs stop being diffable against the committed A/B/C baselines."""
    ev = _evidence()

    class FakeGenerator:
        model_id = "fake"

        def generate(self, case_text):
            return ("Section 302 of the Indian Penal Code, 1860 applies.",
                    GenerationMetadata(model_id="fake", quantization={}, max_new_tokens=10,
                                       do_sample=False, temperature=1.0, top_p=1.0, seed=42))

    rec = pipeline.run_case(
        Case(document_id="d1", case_text="facts", raw_citation_keys=[]),
        "B", FakeGenerator(), RecordingVerifier(), None,
        {("Section", "302", None, "indian penal code 1860"): ev}, [ev], _config("labeled"),
    )
    for claim in rec["claims"]:
        assert not any(k.startswith("_") for k in claim)
        assert "_evidence_provision" not in claim


# --------------------------------------------------------------------------
# 4. invalid framing configuration fails clearly
# --------------------------------------------------------------------------

def test_invalid_configured_framing_raises_naming_the_bad_value():
    with pytest.raises(ValueError) as exc:
        pipeline.resolve_premise_framing(_config("Labeled"))   # wrong case
    assert "Labeled" in str(exc.value)
    assert "premise_framing" in str(exc.value)


@pytest.mark.parametrize("bad", ["", "none", "LABELED", "labelled", "bare_premise", None, 0, True])
def test_invalid_framing_never_silently_degrades_to_bare(bad):
    """A typo must fail loudly. Falling through to bare would produce a run that
    is labelled an ablation but is not one.

    The key is set explicitly (rather than via _config's omit-if-None path) so
    that `bad=None` covers a bare `premise_framing:` line in YAML, which parses
    to None and must be rejected rather than treated as "unset".
    """
    cfg = _config()
    cfg["verification"]["premise_framing"] = bad
    with pytest.raises(ValueError):
        pipeline.resolve_premise_framing(cfg)


def test_apply_verification_rejects_an_invalid_framing_argument():
    with pytest.raises(ValueError):
        pipeline.apply_verification(_baseline_with_matched_claim(), RecordingVerifier(), "sideways")


# --------------------------------------------------------------------------
# 5. re-verification uses the same framing that produced the verdict
# --------------------------------------------------------------------------

def test_reverification_premise_uses_the_configured_framing():
    """Verifying under one framing and re-verifying under another would judge a
    correction against a different standard than the one that flagged it."""
    ev = _evidence()

    class FlagThenPassVerifier(RecordingVerifier):
        def verify(self, premise, hypothesis):
            self.premises.append(premise)
            label = CONTRADICTED if len(self.premises) == 1 else ENTAILED
            return VerificationResult(
                label=label, confidence=0.99, sub_reason=None,
                raw_scores={"entailment": 0.0, "neutral": 0.0, "contradiction": 1.0},
                verifier_model=self.model_id,
            )

    class ScriptedCorrector:
        def correct(self, case_text, original_field_text, flagged_claim_text, evidence_text):
            from src.corrector import CorrectionMetadata
            fixed = ("According to Section 302 of the Indian Penal Code, 1860, whoever "
                     "commits murder shall be punished with death.")
            return fixed, CorrectionMetadata(
                model_id="fake", max_new_tokens=10, do_sample=False, seed=42,
            )

    class FakeGenerator:
        model_id = "fake"

        def generate(self, case_text):
            return ("According to Section 302 of the Indian Penal Code, 1860, murder is "
                    "never punishable.",
                    GenerationMetadata(model_id="fake", quantization={}, max_new_tokens=10,
                                       do_sample=False, temperature=1.0, top_p=1.0, seed=42))

    v = FlagThenPassVerifier()
    pipeline.run_case(
        Case(document_id="d1", case_text="facts", raw_citation_keys=[]),
        "C", FakeGenerator(), v, ScriptedCorrector(),
        {("Section", "302", None, "indian penal code 1860"): ev}, [ev], _config("labeled"),
    )
    assert len(v.premises) >= 2, "re-verification did not run"
    assert all(p.startswith("Section 302 of The Indian Penal Code, 1860: ") for p in v.premises)
