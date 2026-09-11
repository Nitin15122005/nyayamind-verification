"""
Tests for `verification.assertion_span_primary_hypothesis`
(src/pipeline.py: `_assertion_spans_hypothesis()`, and its wiring into
`apply_verification()`).

Background: `narrow_primary_hypothesis` (Stage 4, 2026-09-09) narrows the
primary-verification hypothesis to a claim's own `assertion_text` whenever
one exists. But for "respectively" claims (claim_parser.py's
`_assign_respectively_spans`), `assertion_text` is LEFT EQUAL to the full
`claim_text` by construction -- the split mechanism there produces a LIST
(`assertion_spans = [bare_number_span, description_item]`), not one
contiguous clause, so `narrow_primary_hypothesis` alone never narrows these.
This module closes that gap. A scripted verifier records the exact
hypothesis it was handed, so each test asserts on what production actually
sends to the model -- no NLI model is loaded.
"""
from __future__ import annotations

from src import pipeline
from src.pipeline import _assertion_spans_hypothesis
from src.data_loader import EvidenceRecord
from src.verifier import VerificationResult, NOT_ENOUGH_INFORMATION

MURDER_TEXT = "Whoever commits murder shall be punished with death, or imprisonment for life."
HURT_TEXT = "Whoever voluntarily causes hurt shall be punished with imprisonment."


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


def _evidence(number: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        dataset_citation_key=f"Section {number} in The Indian Penal Code, 1860",
        act="The Indian Penal Code, 1860", provision_type="Section",
        provision_number=number, subsection=None, canonical_text=text,
        source_url="http://example.com", audit_verdict="VERIFIED_EXACT",
        act_norm="indian penal code 1860",
    )


def _respectively_claim_record(number: str, evidence_text: str, description_item: str,
                                claim_text: str) -> dict:
    ev = _evidence(number, evidence_text)
    return {
        "claim_id": f"c{number}",
        "claim_text": claim_text,
        "assertion_text": claim_text,  # unnarrowed by design for respectively claims
        "assertion_spans": [number, description_item],
        "citation_extracted": {"provision_type": "Section", "provision_number": number,
                               "subsection": None, "act_raw": "the Indian Penal Code, 1860",
                               "act_norm": "indian penal code 1860"},
        "evidence_id": ev.dataset_citation_key,
        "evidence_text": ev.canonical_text,
        "evidence_match_method": "exact_normalized",
        "_evidence_provision": {"provision_type": ev.provision_type,
                                "provision_number": ev.provision_number, "act": ev.act},
        "verdict": None, "confidence": None, "sub_reason": None, "verifier_model": None,
    }


BUNDLED_TEXT = ("Sections 302 and 323 of the Indian Penal Code, 1860, which respectively "
                "deal with murder and voluntarily causing hurt.")


class TestAssertionSpansHypothesisFunction:
    def test_builds_provision_labeled_hypothesis_from_two_spans(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        result = _assertion_spans_hypothesis(rec)
        assert result == "Section 302 murder"

    def test_returns_none_when_spans_count_is_not_two(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["assertion_spans"] = ["302"]  # only one fragment
        assert _assertion_spans_hypothesis(rec) is None
        rec["assertion_spans"] = ["302", "murder", "extra"]  # three fragments
        assert _assertion_spans_hypothesis(rec) is None

    def test_returns_none_when_first_span_is_not_the_claims_own_provision_number(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["assertion_spans"] = ["999", "murder"]  # doesn't match citation_extracted's 302
        assert _assertion_spans_hypothesis(rec) is None

    def test_returns_none_when_no_evidence_provision_available(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["_evidence_provision"] = None
        assert _assertion_spans_hypothesis(rec) is None

    def test_returns_none_when_description_item_is_empty(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["assertion_spans"] = ["302", ""]
        assert _assertion_spans_hypothesis(rec) is None

    def test_never_invents_words_beyond_the_two_verbatim_fragments(self):
        # Every token in the output must trace to either the provision
        # label (type+number, already used verbatim for labeled premise
        # framing elsewhere) or assertion_spans[1] itself.
        rec = _respectively_claim_record(
            "323", HURT_TEXT, "voluntarily causing hurt", BUNDLED_TEXT
        )
        result = _assertion_spans_hypothesis(rec)
        assert result == "Section 323 voluntarily causing hurt"
        for word in result.split():
            assert word in ("Section", "323") or word in "voluntarily causing hurt".split()


class TestApplyVerificationWiring:
    def test_disabled_by_default_falls_back_to_claim_text(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        baseline = {"claims": [rec]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=True, assertion_span_primary_hypothesis=False,
        )
        assert v.hypotheses == [BUNDLED_TEXT]

    def test_enabled_uses_span_based_hypothesis_for_respectively_claims(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        baseline = {"claims": [rec]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=True, assertion_span_primary_hypothesis=True,
        )
        assert v.hypotheses == ["Section 302 murder"]

    def test_requires_narrow_primary_hypothesis_also_enabled(self):
        # assertion_span_primary_hypothesis alone (narrow_primary_hypothesis
        # False) must NOT activate -- it is documented as an EXTENSION of
        # narrow_primary_hypothesis, not an independent switch.
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        baseline = {"claims": [rec]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=False, assertion_span_primary_hypothesis=True,
        )
        assert v.hypotheses == [BUNDLED_TEXT]

    def test_assertion_text_narrowing_takes_priority_when_both_apply(self):
        # A claim with a genuinely narrower assertion_text (not a
        # respectively claim) must use assertion_text, never fall through
        # to span-based construction even if assertion_span_primary_hypothesis
        # is also enabled.
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["assertion_text"] = "Section 302 prescribes the punishment for murder"
        baseline = {"claims": [rec]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=True, assertion_span_primary_hypothesis=True,
        )
        assert v.hypotheses == ["Section 302 prescribes the punishment for murder"]

    def test_non_respectively_claim_with_default_spans_is_unaffected(self):
        # A normal (non-respectively) claim's assertion_spans defaults to
        # [assertion_text] (one element) -- _assertion_spans_hypothesis must
        # decline (len != 2) and the full claim_text is used, matching
        # narrow_primary_hypothesis's own existing behavior.
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["assertion_spans"] = [BUNDLED_TEXT]  # degenerate single-element default
        baseline = {"claims": [rec]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=True, assertion_span_primary_hypothesis=True,
        )
        assert v.hypotheses == [BUNDLED_TEXT]

    def test_no_evidence_claims_never_reach_the_verifier(self):
        rec = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec["evidence_text"] = None
        rec["verdict"] = "NO_EVIDENCE"
        baseline = {"claims": [rec]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=True, assertion_span_primary_hypothesis=True,
        )
        assert v.hypotheses == []

    def test_multiple_respectively_claims_each_get_their_own_hypothesis(self):
        rec1 = _respectively_claim_record("302", MURDER_TEXT, "murder", BUNDLED_TEXT)
        rec2 = _respectively_claim_record("323", HURT_TEXT, "voluntarily causing hurt", BUNDLED_TEXT)
        baseline = {"claims": [rec1, rec2]}
        v = RecordingVerifier()
        pipeline.apply_verification(
            baseline, v, narrow_primary_hypothesis=True, assertion_span_primary_hypothesis=True,
        )
        assert v.hypotheses == ["Section 302 murder", "Section 323 voluntarily causing hurt"]


def test_run_case_reads_assertion_span_primary_hypothesis_from_config():
    from src.data_loader import Case
    from src.generator import GenerationMetadata

    class _FakeGenerator:
        def __init__(self, text: str):
            self._text = text

        def generate(self, case_text: str):
            meta = GenerationMetadata(
                model_id="mock-generator", quantization={"load_in_4bit": True},
                max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42,
            )
            return self._text, meta

    bundled = ("Sections 302 and 323 of the Indian Penal Code, 1860, which respectively "
               "deal with murder and voluntarily causing hurt.")
    ev1 = _evidence("302", MURDER_TEXT)
    ev2 = _evidence("323", HURT_TEXT)
    all_usable = [ev1, ev2]
    exact_index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in all_usable}
    case = Case(document_id="doc-1", case_text="facts", raw_citation_keys=[])
    config = {
        "seed": 42,
        "generation": {"model_id": "mock-generator", "quantization": {"load_in_4bit": True}},
        "verification": {
            "model_id": "mock-verifier", "confidence_threshold": 0.70,
            "premise_framing": "bare", "narrow_primary_hypothesis": True,
            "assertion_span_primary_hypothesis": True,
        },
        "evidence_matching": {"fuzzy_token_overlap_threshold": 0.8},
        "correction": {},
    }

    record = pipeline.run_case(
        case, "B", _FakeGenerator(bundled), RecordingVerifier(), None,
        exact_index, all_usable, config,
    )
    murder_claim = next(c for c in record["claims"] if c["citation_extracted"]["provision_number"] == "302")
    assert murder_claim["verified_hypothesis"] == "Section 302 murder"
    assert record["reproducibility"]["assertion_span_primary_hypothesis"] is True


class TestEndToEndAdversarialCoverage:
    """End-to-end (real claim_parser.extract_claims(), not hand-built claim
    dicts) adversarial coverage added during the 2026-09-11 recovery pass's
    audit of the assertion-span mechanism -- negation, modality/exceptions,
    multi-citation, and fail-closed-on-ambiguity, per that pass's explicit
    request to verify the implementation rather than just trust the n=6
    benchmark's aggregate numbers."""

    def test_negation_in_second_respectively_item_is_preserved_not_dropped(self):
        from src.claim_parser import extract_claims

        text = ("Sections 302 and 304 of the Indian Penal Code, 1860, which respectively "
                "require proof of intent and do not require proof of premeditation.")
        claims = {c.citation_extracted.provision_number: c for c in extract_claims(text)}
        # The negation "do not" must survive verbatim in the 304 span -- a
        # dropped negation here would silently invert what's being verified.
        assert "do not require" in claims["304"].assertion_spans[1]
        assert claims["304"].assertion_spans[1] == "do not require proof of premeditation"

    def test_modal_and_exception_clauses_preserved_in_respectively_items(self):
        from src.claim_parser import extract_claims

        text = ("Sections 100 and 105 of the Indian Penal Code, 1860, which respectively "
                "permit the use of force unless the accused had time to seek help and "
                "prohibit retaliation after the threat has ceased.")
        claims = {c.citation_extracted.provision_number: c for c in extract_claims(text)}
        assert "unless the accused had time to seek help" in claims["100"].assertion_spans[1]
        assert "after the threat has ceased" in claims["105"].assertion_spans[1]

    def test_three_citation_respectively_all_correctly_paired(self):
        from src.claim_parser import extract_claims

        text = ("Sections 302, 304, and 306 of the Indian Penal Code, 1860, which "
                "respectively deal with murder, culpable homicide, and abetment of suicide.")
        claims = {c.citation_extracted.provision_number: c for c in extract_claims(text)}
        assert claims["302"].assertion_spans == ["302", "murder"]
        assert claims["304"].assertion_spans == ["304", "culpable homicide"]
        assert claims["306"].assertion_spans == ["306", "abetment of suicide"]

    def test_structurally_ambiguous_sentence_fails_closed_not_garbage(self):
        # A malformed/irregular "respectively" sentence (citation count and
        # clause structure don't cleanly match the 2-shape grammar
        # _assign_respectively_spans requires) must never produce a
        # 2-element assertion_spans list that _assertion_spans_hypothesis
        # would then build a hypothesis from -- it must fail closed to the
        # existing (safe) 1-element degenerate default instead.
        from src.claim_parser import extract_claims

        text = ("Sections 302 and 304 of the Indian Penal Code, 1860, and Section 34, "
                "which respectively deal with murder, culpable homicide, and common intention.")
        for claim in extract_claims(text):
            rec = {
                "claim_text": claim.claim_text,
                "assertion_text": claim.assertion_text,
                "assertion_spans": list(claim.assertion_spans),
                "citation_extracted": claim.citation_extracted.as_dict(),
                "_evidence_provision": {
                    "provision_type": claim.citation_extracted.provision_type,
                    "provision_number": claim.citation_extracted.provision_number,
                    "act": "irrelevant",
                },
            }
            # Either the 2-shape pattern matched cleanly (spans has exactly
            # 2 elements, first == own provision number) or it must decline
            # entirely -- never a malformed/wrong 2-element list.
            if len(rec["assertion_spans"]) == 2:
                assert rec["assertion_spans"][0] == claim.citation_extracted.provision_number
            else:
                assert _assertion_spans_hypothesis(rec) is None

    def test_verb_prefix_stripping_only_ever_applies_to_the_first_list_item(self):
        """ADVERSARIAL FINDING (2026-09-11 recovery-pass audit, understood
        behavior, NOT a bug -- see FINAL_PRODUCTION_CONFIG.md sec.5a's audit
        note): `_KNOWN_VERB_PREFIX_RE` strips a SHARED leading verb phrase
        from the FRONT of the whole items-zone in shape #1 ("which
        respectively deal with X and Y" -> the "deal with" implicitly
        governs both X and Y, so stripping it once and splitting is
        correct, not a loss). It can therefore only ever strip the FIRST
        item's own text; if a LATER item in the same list has its own
        distinct verb ("...deal with murder and require proof of
        premeditation"), that verb is part of THAT item's genuine content,
        not a strippable shared prefix, and is correctly preserved. Shape
        #2 ("which X, Y, respectively") never strips anything, since its
        items sit before "respectively" and are used as-is. Locked in here
        so a future change to this shared logic (also used by the
        safety-critical scope-check) is a deliberate, noticed decision --
        not because either behavior is wrong.
        """
        from src.claim_parser import extract_claims

        shape1 = ("Sections 302 and 304 of the Indian Penal Code, 1860, which respectively "
                  "deal with murder and require proof of premeditation.")
        shape2 = ("Sections 302 and 304 of the Indian Penal Code, 1860, which require proof "
                  "of intent and require proof of premeditation, respectively.")
        shape1_claims = {c.citation_extracted.provision_number: c for c in extract_claims(shape1)}
        shape2_claims = {c.citation_extracted.provision_number: c for c in extract_claims(shape2)}
        # Shape #1: only the FIRST item ("deal with murder") had its shared
        # verb phrase stripped; the second item's own distinct verb
        # ("require") is genuine content, correctly preserved.
        assert shape1_claims["302"].assertion_spans[1] == "murder"
        assert shape1_claims["304"].assertion_spans[1] == "require proof of premeditation"
        # Shape #2: no stripping at all, items used as-is.
        assert shape2_claims["302"].assertion_spans[1] == "require proof of intent"
        assert shape2_claims["304"].assertion_spans[1] == "require proof of premeditation"
