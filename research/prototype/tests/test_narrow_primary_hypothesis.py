"""
Production-path wiring tests for `verification.narrow_primary_hypothesis`
(src/pipeline.py's apply_verification()). A scripted verifier records the
exact hypothesis string it was handed, so each test asserts on what
production actually sends to the model — no NLI model is loaded.

Background: this extends the SAME technique `correction.
narrow_reverification_hypothesis` already applies during correction
re-verification to the PRIMARY verification pass — see
outputs/final_limitations_and_future_scope.md Sec.3a (documented gap) and
outputs/narrow_primary_hypothesis_benchmark_report.md (the real-data
benchmark this default is based on: 456 real evidence-matched claims
re-scored, 107 had a narrower assertion available, 31 flipped NEI->ENTAILED
with zero ENTAILED<->CONTRADICTED reversals).
"""
from __future__ import annotations

from src import pipeline
from src.data_loader import Case, EvidenceRecord
from src.generator import GenerationMetadata
from src.verifier import VerificationResult, NOT_ENOUGH_INFORMATION

MURDER_TEXT = ("Whoever commits murder shall be punished with death, or imprisonment "
               "for life, and shall also be liable to fine.")


class RecordingVerifier:
    model_id = "recording-verifier"

    def __init__(self):
        self.hypotheses: list[str] = []

    def verify(self, premise: str, hypothesis: str) -> VerificationResult:
        self.hypotheses.append(hypothesis)
        return VerificationResult(
            label=NOT_ENOUGH_INFORMATION, confidence=0.99, sub_reason=None,
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


def _baseline(claim_text: str, assertion_text: str) -> dict:
    ev = _evidence()
    return {
        "document_id": "doc-1", "case_text": "case", "generated_field": {"text": "field"},
        "claims": [{
            "claim_id": "c1",
            "claim_text": claim_text,
            "assertion_text": assertion_text,
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


def test_default_false_uses_full_claim_text():
    bundled = "Section 302 prescribes the punishment for murder, while Section 364 deals with abetment of suicide."
    narrower = "Section 302 prescribes the punishment for murder"
    baseline = _baseline(bundled, narrower)
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, narrow_primary_hypothesis=False)
    assert v.hypotheses == [bundled]
    assert baseline["claims"][0]["verified_hypothesis"] == bundled


def test_enabled_uses_narrower_assertion_text_when_available():
    bundled = "Section 302 prescribes the punishment for murder, while Section 364 deals with abetment of suicide."
    narrower = "Section 302 prescribes the punishment for murder"
    baseline = _baseline(bundled, narrower)
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, narrow_primary_hypothesis=True)
    assert v.hypotheses == [narrower]
    assert baseline["claims"][0]["verified_hypothesis"] == narrower


def test_enabled_falls_back_to_claim_text_when_no_narrower_assertion_exists():
    # assertion_text defaults to claim_text (Claim.__post_init__) whenever no
    # safe split pattern applied -- must behave identically to disabled.
    plain = "Section 302 of the Indian Penal Code prescribes the punishment for murder."
    baseline = _baseline(plain, plain)  # assertion_text == claim_text
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, narrow_primary_hypothesis=True)
    assert v.hypotheses == [plain]


def test_enabled_falls_back_when_assertion_text_field_missing_entirely():
    # Defense in depth: a claim record predating this field (older committed
    # output, or a caller that never set it) must not crash or silently
    # verify an empty hypothesis.
    baseline = _baseline("Section 302 prescribes the punishment for murder.", "irrelevant")
    del baseline["claims"][0]["assertion_text"]
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, narrow_primary_hypothesis=True)
    assert v.hypotheses == ["Section 302 prescribes the punishment for murder."]


def test_no_evidence_claims_never_reach_the_verifier_regardless_of_flag():
    baseline = _baseline("text", "text")
    baseline["claims"][0]["evidence_text"] = None
    baseline["claims"][0]["verdict"] = "NO_EVIDENCE"
    v = RecordingVerifier()
    pipeline.apply_verification(baseline, v, narrow_primary_hypothesis=True)
    assert v.hypotheses == []


class _FakeGenerator:
    def __init__(self, text: str):
        self._text = text

    def generate(self, case_text: str):
        meta = GenerationMetadata(
            model_id="mock-generator", quantization={"load_in_4bit": True},
            max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42,
        )
        return self._text, meta


def test_run_case_reads_narrow_primary_hypothesis_from_config_verification_block():
    # End-to-end (mocked generator/verifier, real claim_parser/evidence_matcher/
    # pipeline code) confirmation that run_case() threads config["verification"]
    # ["narrow_primary_hypothesis"] through to apply_verification.
    bundled_text = ("Section 302 of the Indian Penal Code, 1860 prescribes the punishment "
                    "for murder, while Section 364 of the Indian Penal Code, 1860 deals "
                    "with abetment of suicide.")
    ev = _evidence()
    all_usable = [ev]
    exact_index = {(ev.provision_type, ev.provision_number, ev.subsection, ev.act_norm): ev}
    case = Case(document_id="doc-1", case_text="facts", raw_citation_keys=[])
    config = {
        "seed": 42,
        "generation": {"model_id": "mock-generator", "quantization": {"load_in_4bit": True}},
        "verification": {
            "model_id": "mock-verifier", "confidence_threshold": 0.70,
            "premise_framing": "bare", "narrow_primary_hypothesis": True,
        },
        "evidence_matching": {"fuzzy_token_overlap_threshold": 0.8},
        "correction": {},
    }

    record = pipeline.run_case(
        case, "B", _FakeGenerator(bundled_text), RecordingVerifier(), None,
        exact_index, all_usable, config,
    )
    murder_claim = next(c for c in record["claims"] if c["citation_extracted"]["provision_number"] == "302")
    assert murder_claim["verified_hypothesis"] == (
        "Section 302 of the Indian Penal Code, 1860 prescribes the punishment for murder"
    )
    assert murder_claim["verified_hypothesis"] != murder_claim["claim_text"]
    assert record["reproducibility"]["narrow_primary_hypothesis"] is True
