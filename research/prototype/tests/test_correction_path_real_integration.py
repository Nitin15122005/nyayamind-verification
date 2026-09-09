"""
Real-verifier integration test for the selective-correction path:
claim -> canonical evidence -> CONTRADICTED -> correction triggered ->
regenerated claim -> re-verification.

Unlike test_pipeline_mock.py (fully synthetic, scripted verifier — fast,
deterministic, checks orchestration wiring only), this file deliberately
uses the REAL, unmodified src.verifier.NLIVerifier against the REAL,
unmodified 59-record usable evidence pool (research/data/evidence/, read
only) so that "CONTRADICTED" and "re-verification" are genuine model
outputs, not asserted-by-construction. src.pipeline.run_case() and every
function it calls (apply_verification, apply_selective_correction,
_scope_violation) run completely unmodified — nothing in src/ is touched
by this file.

Base real generated field: the generation stage is identical across modes
A/B/C (see pipeline.py's module docstring — "All three modes share the
exact same generation ... stage"), so a Mode-C output's generated_field is
exactly what a Mode-A run on that same case would have produced.
research/prototype/outputs/run_A_n1.jsonl's own stored claims have no
usable-evidence-pool overlap at all (its case cites Constitution Articles
1A/31A/31B/31C, which are outside the 59-record pool — see prior session
findings), so it cannot support a genuine claim -> evidence -> CONTRADICTED
demonstration. research/prototype/outputs/run_C_targeted_1994_495.jsonl's
generated_field DOES have real, exact-matched evidence (Section 302 and
Section 148 of the Indian Penal Code, 1860), so its real sentences are
reused here as the base for one deliberately corrupted claim.

The generator is a FakeGenerator (never calls the real 7B Qwen model —
we're supplying a real, pre-existing generated field directly, not asking
anything to generate one) and the corrector is a ScriptedCorrector (never
calls the real 7B Qwen model either) — both follow the exact pattern
already established in test_pipeline_mock.py. Loading the real Qwen
generator/corrector is unnecessary to exercise "the existing verification
+ selective-correction LOGIC" (pipeline.py's real, unmodified functions)
and would make this test slow/GPU-dependent for no benefit; the part that
must be real to mean anything — the NLI verifier's CONTRADICTED /
re-verification judgment against real canonical evidence text — IS real.

No corrupted data is added to research/data/evidence/ (read-only there,
as always). The one place this file writes a temporary file (to literally
exercise "create a temporary test-only corrupted version... delete it
afterward") uses pytest's tmp_path fixture, which pytest already isolates
outside the repo; the test also deletes it explicitly before returning.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.corrector import CorrectionMetadata
from src.data_loader import Case, load_usable_evidence_from_config
from src.generator import GenerationMetadata
from src.pipeline import run_case
from src.verifier import CONTRADICTED, ENTAILED, NOT_ENOUGH_INFORMATION, NLIVerifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROTOTYPE_ROOT = REPO_ROOT / "research" / "prototype"
CONFIG_PATH = PROTOTYPE_ROOT / "config" / "prototype.yaml"

# The real base: sentence 2 below is copied VERBATIM from the actual
# generated_field.text in research/prototype/outputs/run_C_targeted_1994_495.jsonl
# (document_id 1994_495) — untouched, used here as the "additional unflagged
# claim". Sentence 1 is a deliberately corrupted version of that same
# record's real Section-302 assertion: it now claims murder is "punishable
# only by a fine and never by death or imprisonment", directly contradicting
# the real canonical evidence text for Section 302 IPC ("...punished with
# death, or imprisonment for life, and shall also be liable to fine.").
_REAL_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with the unlawful assembly, which may be "
    "relevant if the prosecution can show that the accused acted as part of an "
    "unlawful assembly."
)
_CORRUPTED_FLAGGED_SENTENCE = (
    "The offense of murder under Section 302 of the Indian Penal Code, 1860 is "
    "punishable only by a fine and never by death or imprisonment."
)
_CORRECTED_FLAGGED_SENTENCE = (
    "Whoever commits murder under Section 302 of the Indian Penal Code, 1860 "
    "shall be punished with death, or imprisonment for life, and shall also be "
    "liable to fine."
)
_ALTERED_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with theft, which may be relevant if the "
    "prosecution can show that the accused acted alone."
)


@pytest.fixture(scope="module")
def real_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def real_evidence_pool(real_config):
    """Read-only load of the real, unmodified usable evidence pool — via
    `load_usable_evidence_from_config`, honoring `real_config`'s own
    `use_evidence_v1` setting exactly as production does, rather than a
    hardcoded v0-only call. (Fixed: this fixture previously always loaded
    only the 59-record v0 pool regardless of what `real_config` said,
    while `real_config` is the actual shipped `config/prototype.yaml`,
    whose production default is `use_evidence_v1: true` — a 136-record
    pool. Every "real integration" test in this file was therefore
    exercising the correction/reverification/scope-violation path against
    an evidence pool production never actually uses; a matching bug
    specific to the v1 supplement's records could have passed this entire
    file undetected.) Nothing is written to research/data/evidence/
    anywhere in this file."""
    exact_index, all_usable = load_usable_evidence_from_config(real_config, REPO_ROOT)
    return exact_index, all_usable


@pytest.fixture(scope="module")
def real_verifier(real_config):
    """The real, unmodified NLIVerifier — same model_id/threshold as
    production config. Loaded once per test module (small CPU-friendly
    model, not the 7B generator).

    Device is chosen explicitly rather than left to the default: this fixture
    only needs the ~184M NLI model with no generator co-resident, so it runs
    fine on CPU. The default "cuda" exists to stop the PIPELINE from silently
    falling back to CPU while sharing a 6GB card with the 4-bit 7B generator —
    a constraint that does not apply here, and which otherwise makes these
    tests error out on any machine without an NVIDIA GPU instead of running.
    """
    torch = pytest.importorskip("torch")
    v = NLIVerifier(
        model_id=real_config["verification"]["model_id"],
        confidence_threshold=real_config["verification"]["confidence_threshold"],
        max_sequence_length=real_config["verification"]["max_sequence_length"],
        device="cuda" if torch.cuda.is_available() else "cpu",
    )
    v.load()
    return v


class FakeGenerator:
    """Supplies a pre-existing real generated field directly — never
    invokes the real 7B model. Same pattern as test_pipeline_mock.py."""

    def __init__(self, text: str, model_id: str):
        self._text = text
        self._model_id = model_id

    def generate(self, case_text: str):
        meta = GenerationMetadata(
            model_id=self._model_id, quantization={"load_in_4bit": True},
            max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42,
        )
        return self._text, meta


class ScriptedCorrector:
    """Returns pre-authored 'corrected' text — never invokes the real 7B
    model. Only pipeline.py's REAL apply_selective_correction() logic
    (scope check, re-verification via the real verifier, status decision)
    is under test here, not the LLM's correction quality. Same pattern as
    test_pipeline_mock.py."""

    def __init__(self, corrected_text: str, model_id: str):
        self._corrected_text = corrected_text
        self._model_id = model_id
        self.calls = []

    def correct(self, case_text, original_field_text, flagged_claim_text, evidence_text):
        self.calls.append((flagged_claim_text, evidence_text))
        meta = CorrectionMetadata(
            model_id=self._model_id, max_new_tokens=220, do_sample=False, seed=42,
        )
        return self._corrected_text, meta


def _case() -> Case:
    return Case(document_id="1994_495", case_text="facts...", raw_citation_keys=[])


# ---------------------------------------------------------------------------
# Step 1: corrupted claim -> real matched evidence -> real CONTRADICTED
# ---------------------------------------------------------------------------

def test_corrupted_claim_reaches_contradicted_against_real_evidence(
    real_evidence_pool, real_verifier, real_config, tmp_path
):
    """Requirement 4, first half: prove the corrupted claim genuinely
    reaches CONTRADICTED via the real verifier against real canonical
    evidence — not asserted by construction."""
    exact_index, all_usable = real_evidence_pool
    corrupted_text = _CORRUPTED_FLAGGED_SENTENCE + " " + _REAL_UNFLAGGED_SENTENCE

    # Requirement 3: create a temporary, test-only corrupted artifact and
    # delete it afterward. Written under pytest's tmp_path (already outside
    # the repo / research/data/evidence), read back, then explicitly removed.
    corrupted_artifact = tmp_path / "corrupted_mode_a_output.jsonl"
    corrupted_artifact.write_text(
        json.dumps({"document_id": "1994_495", "generated_field": {"text": corrupted_text}}),
        encoding="utf-8",
    )
    loaded = json.loads(corrupted_artifact.read_text(encoding="utf-8"))
    assert loaded["generated_field"]["text"] == corrupted_text
    corrupted_artifact.unlink()
    assert not corrupted_artifact.exists()

    case = _case()
    generator = FakeGenerator(corrupted_text, real_config["generation"]["model_id"])
    record = run_case(
        case, "B", generator, real_verifier, corrector=None,
        exact_index=exact_index, all_usable=all_usable, config=real_config,
    )

    flagged = next(c for c in record["claims"] if c["citation_extracted"]["provision_number"] == "302")
    assert flagged["evidence_id"] == "Section 302 in The Indian Penal Code, 1860"
    assert flagged["evidence_text"] == (
        "Whoever commits murder shall be punished with death, or imprisonment "
        "for life, and shall also be liable to fine."
    )
    assert flagged["verdict"] == CONTRADICTED
    assert flagged["confidence"] > real_config["verification"]["confidence_threshold"]


# ---------------------------------------------------------------------------
# Steps 2-5: full correction path through the real, unmodified pipeline
# ---------------------------------------------------------------------------

def test_full_correction_path_triggers_and_reverifies_with_real_verifier(
    real_evidence_pool, real_verifier, real_config
):
    """Requirements 4-6: correction triggered, regenerated claim produced,
    real re-verification occurs, unflagged claim preserved, correction
    metadata preserved. The corrector is scripted (not the real 7B model —
    see module docstring), but the re-verification verdict is genuinely
    computed by the real verifier against the real canonical evidence text,
    not scripted."""
    exact_index, all_usable = real_evidence_pool
    corrupted_text = _CORRUPTED_FLAGGED_SENTENCE + " " + _REAL_UNFLAGGED_SENTENCE
    corrected_text = _CORRECTED_FLAGGED_SENTENCE + " " + _REAL_UNFLAGGED_SENTENCE

    case = _case()
    generator = FakeGenerator(corrupted_text, real_config["generation"]["model_id"])
    corrector = ScriptedCorrector(corrected_text, real_config["generation"]["model_id"])

    record = run_case(
        case, "C", generator, real_verifier, corrector,
        exact_index=exact_index, all_usable=all_usable, config=real_config,
    )

    claims_by_number = {c["citation_extracted"]["provision_number"]: c for c in record["claims"]}

    # claim -> canonical evidence -> CONTRADICTED
    assert claims_by_number["302"]["verdict"] == CONTRADICTED

    # requirement 5: the additional (unflagged) claim is untouched by the
    # corruption and correctly NOT flagged for correction.
    assert claims_by_number["148"]["claim_text"] == _REAL_UNFLAGGED_SENTENCE
    assert claims_by_number["148"]["verdict"] != CONTRADICTED
    assert claims_by_number["148"]["sub_reason"] != "low_confidence"

    # correction triggered, exactly for the flagged (302) claim
    assert record["correction"]["triggered_for_claim_id"] == claims_by_number["302"]["claim_id"]
    assert record["correction"]["attempts"] == 1
    assert len(corrector.calls) == 1
    assert corrector.calls[0][0] == _CORRUPTED_FLAGGED_SENTENCE  # flagged_claim_text passed through
    assert corrector.calls[0][1] == claims_by_number["302"]["evidence_text"]  # real evidence passed through

    # regenerated claim: the corrector's output is recorded
    assert record["correction"]["regenerated_text"] == corrected_text

    # re-verification: a REAL verdict was computed (not scripted) against
    # the real canonical evidence for the regenerated Section-302 sentence.
    reverification = record["correction"]["reverification"]
    assert reverification is not None
    assert reverification["claim_text"] == _CORRECTED_FLAGGED_SENTENCE
    assert reverification["evidence_id"] == "Section 302 in The Indian Penal Code, 1860"
    assert reverification["verdict"] in (CONTRADICTED, NOT_ENOUGH_INFORMATION, ENTAILED)

    # UPDATED 2026-08-27 for the production premise_framing default change
    # (bare -> labeled; see FINAL_PRODUCTION_CONFIG.md). Under the OLD bare
    # default, this small real NLI checkpoint judged the accurate,
    # evidence-matching regenerated sentence as NOT_ENOUGH_INFORMATION —
    # the exact "attributed claim, unlabeled premise" gap labeled framing
    # exists to close (see config/prototype.yaml's own comment on
    # premise_framing). Under the current "labeled" default, real_config is
    # loaded directly from the shipped prototype.yaml, so this genuinely
    # re-verifies under labeled framing — and the real, unmodified verifier
    # now correctly judges this accurate correction ENTAILED. This is not a
    # scripted/asserted-by-construction result: it is the same real model
    # call as before, against the same real evidence text, only the premise
    # framing changed. The safety net is exercised the OTHER direction by
    # test_scope_violation_protection_when_corrector_alters_unflagged_claim
    # below (an unsafe correction is still never shipped).
    assert reverification["verdict"] == ENTAILED
    assert record["correction"]["status"] == "corrected"
    assert record["final_field"]["source"] == "corrected"
    assert record["final_field"]["text"] == corrected_text  # the verified, shipped fix

    # requirement 5 (text level too): the unflagged sentence survives
    # verbatim in whatever text ships, regardless of correction outcome.
    assert _REAL_UNFLAGGED_SENTENCE in record["final_field"]["text"]

    # requirement 6: correction metadata preserved end-to-end.
    corr_meta = record["correction"]["corr_meta"]
    assert corr_meta["model"] == real_config["generation"]["model_id"]
    assert corr_meta["max_new_tokens"] == 220
    assert corr_meta["do_sample"] is False
    assert corr_meta["seed"] == 42
    assert "corrected_at" in corr_meta


# ---------------------------------------------------------------------------
# Step 7 (requirement): correction_scope_violation protection
# ---------------------------------------------------------------------------

def test_scope_violation_protection_when_corrector_alters_unflagged_claim(
    real_evidence_pool, real_verifier, real_config
):
    """Requirement 7: if the corrector rewrites the unflagged claim too
    (not just the flagged one), pipeline.py's real, unmodified
    _scope_violation() check must catch it BEFORE any re-verification call
    and refuse to ship the corrupted-scope text."""
    exact_index, all_usable = real_evidence_pool
    corrupted_text = _CORRUPTED_FLAGGED_SENTENCE + " " + _REAL_UNFLAGGED_SENTENCE
    bad_corrected_text = _CORRECTED_FLAGGED_SENTENCE + " " + _ALTERED_UNFLAGGED_SENTENCE

    case = _case()
    generator = FakeGenerator(corrupted_text, real_config["generation"]["model_id"])
    bad_corrector = ScriptedCorrector(bad_corrected_text, real_config["generation"]["model_id"])

    record = run_case(
        case, "C", generator, real_verifier, bad_corrector,
        exact_index=exact_index, all_usable=all_usable, config=real_config,
    )

    assert record["correction"]["status"] == "correction_scope_violation"
    assert record["correction"]["regenerated_text"] == bad_corrected_text
    # Caught BEFORE re-verification: no re-verification call was ever made.
    assert record["correction"]["reverification"] is None
    # The corrupted-scope text must never be shipped.
    assert record["final_field"]["source"] == "correction_scope_violation"
    assert record["final_field"]["text"] == corrupted_text
    assert _REAL_UNFLAGGED_SENTENCE in record["final_field"]["text"]
    assert _ALTERED_UNFLAGGED_SENTENCE not in record["final_field"]["text"]


# ---------------------------------------------------------------------------
# Truncation-detection instrumentation (measurement infrastructure, not live
# behavior) — must reflect the REAL tokenizer's actual truncation behavior,
# not an assumption about it.
# ---------------------------------------------------------------------------

def test_input_truncated_flag_false_for_a_normal_length_pair(real_verifier):
    """A realistic premise+hypothesis pair, well under
    max_sequence_length (512), must report input_truncated=False."""
    result = real_verifier.verify(
        premise="Whoever commits murder shall be punished with death, or imprisonment "
                "for life, and shall also be liable to fine.",
        hypothesis="Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder.",
    )
    assert result.input_truncated is False


def test_input_truncated_flag_true_when_pair_exceeds_max_sequence_length(real_verifier):
    """(real, reproduced instrumentation gap — fixed) Before this fix,
    NLIVerifier.verify() had no way to report that HF's pair-truncation
    silently cut content from the input — a verdict computed from a
    truncated premise looked identical, in the output record, to one
    computed from the full text. Uses the REAL cached DeBERTa tokenizer
    (via real_verifier, not a mock) so this proves actual truncation
    behavior, not an assumed one: a premise long enough that the combined
    pair genuinely exceeds max_sequence_length must report
    input_truncated=True. This is currently inert against the real 136
    -record evidence corpus (see verifier.py's VerificationResult
    docstring) — this test constructs the exceeding-length case directly
    rather than waiting for a future corpus record to happen to trigger it."""
    long_premise = (
        "Whoever commits murder shall be punished with death or life imprisonment. "
        * 50
    )
    result = real_verifier.verify(
        premise=long_premise,
        hypothesis="Section 302 of the Indian Penal Code, 1860 prescribes punishment for murder.",
    )
    assert result.input_truncated is True
    # Sanity check on the model call itself: it must still have run (never
    # skipped or errored just because truncation occurred) and produced a
    # normal, well-formed verdict.
    assert result.label in (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION)


# ---------------------------------------------------------------------------
# Negation safety gate: a negated claim must not silently drive an automatic
# "correction" into an affirmative rewrite, using the REAL verifier — not a
# scripted one — so the CONTRADICTED verdict driving this test is a genuine
# model output, not asserted by construction.
# ---------------------------------------------------------------------------

def test_negated_claim_reaches_contradicted_via_real_verifier_but_never_triggers_correction(
    real_evidence_pool, real_verifier, real_config
):
    """(real, reproduced cross-component safety gap — fixed) A negated claim
    ("Neither Section 302 nor Section 304 ... applies to this case.") reaches
    CONTRADICTED at very high confidence against the REAL DeBERTa verifier
    and real IPC evidence — empirically confirmed during this session's
    adversarial claim-parser audit, and reconfirmed here. Before the
    negation-safety gate, CONTRADICTED always triggered automatic
    correction, which could rewrite a claim that correctly, truthfully
    asserts a NEGATIVE legal conclusion into an affirmative one. A
    NoCallCorrector that raises if ever invoked proves the gate actually
    prevents the correction ATTEMPT (not just its outcome) — the claim's own
    CONTRADICTED verdict remains fully visible in the claim record for
    manual review; only the automatic rewrite is suppressed."""
    exact_index, all_usable = real_evidence_pool
    negated_text = (
        "Neither Section 302 nor Section 304 of the Indian Penal Code, 1860 "
        "applies to this case."
    )

    class NoCallCorrector:
        def correct(self, *args, **kwargs):
            raise AssertionError(
                "corrector.correct() must never be called for a negation-flagged claim"
            )

    case = _case()
    generator = FakeGenerator(negated_text, real_config["generation"]["model_id"])
    record = run_case(
        case, "C", generator, real_verifier, NoCallCorrector(),
        exact_index=exact_index, all_usable=all_usable, config=real_config,
    )

    claim = next(c for c in record["claims"] if c["citation_extracted"]["provision_number"] == "302")
    assert claim["verdict"] == CONTRADICTED  # genuine real-model verdict, unchanged
    assert claim["negation_contradiction_caveat"] is True
    assert record["correction"]["status"] == "not_triggered"
    assert record["correction"]["triggered_for_claim_id"] is None
    assert record["final_field"]["source"] == "original"
    assert record["final_field"]["text"] == negated_text
