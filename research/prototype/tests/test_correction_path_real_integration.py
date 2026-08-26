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
from src.data_loader import Case, load_usable_evidence
from src.generator import GenerationMetadata
from src.pipeline import run_case
from src.verifier import CONTRADICTED, NOT_ENOUGH_INFORMATION, NLIVerifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROTOTYPE_ROOT = REPO_ROOT / "research" / "prototype"
CONFIG_PATH = PROTOTYPE_ROOT / "config" / "prototype.yaml"
CANONICAL_PATH = REPO_ROOT / "research/data/evidence/canonical_statutes.jsonl"
AUDIT_PATH = REPO_ROOT / "research/data/evidence/evidence_audit.jsonl"

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
def real_evidence_pool():
    """Read-only load of the real, unmodified 59-record usable evidence
    pool. Nothing is written to research/data/evidence/ anywhere in this
    file."""
    exact_index, all_usable = load_usable_evidence(
        CANONICAL_PATH, AUDIT_PATH, {"VERIFIED_EXACT", "VERIFIED_CONTENT"}
    )
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
    assert reverification["verdict"] in (CONTRADICTED, NOT_ENOUGH_INFORMATION, "ENTAILED")

    # Empirically, this small real NLI checkpoint judges the (accurate,
    # evidence-matching) regenerated sentence as NOT_ENOUGH_INFORMATION
    # rather than ENTAILED once the citation phrase is present in the same
    # sentence (verified interactively before writing this test — see PR
    # discussion). That's a genuine, reproducible property of the real,
    # unmodified verifier — not a pipeline defect — so correction_failed is
    # the authentic outcome here, and the safety net (never ship an
    # unverified "fix") must still hold: final_field reverts to original.
    assert reverification["verdict"] == NOT_ENOUGH_INFORMATION
    assert record["correction"]["status"] == "correction_failed"
    assert record["final_field"]["source"] == "correction_failed"
    assert record["final_field"]["text"] == corrupted_text  # NOT the unverified regenerated text

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
