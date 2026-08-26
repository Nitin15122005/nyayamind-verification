"""
Regression tests for the controlled verifier benchmark (v2) and for the
premise-framing / device changes to NLIVerifier.

No model is loaded anywhere here: construction and framing are pure functions,
which is the point — the benchmark's gold labels must be derivable without ever
consulting a model.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.data_loader import EvidenceRecord
from src.verifier import (
    NLIVerifier,
    format_premise,
    PREMISE_FRAMING_BARE,
    PREMISE_FRAMING_LABELED,
)
from scripts.build_controlled_benchmark import (
    apply_negation,
    apply_paraphrase,
    build_controlled_benchmark,
    validate,
    _stable_id,
)

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent


def _rec(key="Section 302 in The Indian Penal Code, 1860",
         text="Whoever commits murder shall be punished with death, or imprisonment for life, "
              "and shall also be liable to fine.",
         act="The Indian Penal Code, 1860", ptype="Section", pnum="302") -> EvidenceRecord:
    return EvidenceRecord(
        dataset_citation_key=key, act=act, provision_type=ptype, provision_number=pnum,
        subsection=None, canonical_text=text, source_url="http://example.com",
        audit_verdict="VERIFIED_EXACT", act_norm="indian penal code 1860",
    )


# --------------------------------------------------------------------------
# premise framing
# --------------------------------------------------------------------------

def test_bare_framing_returns_statute_text_unchanged():
    assert format_premise("Whoever commits murder...", framing=PREMISE_FRAMING_BARE) == \
        "Whoever commits murder..."


def test_labeled_framing_prepends_provision_label_and_preserves_statute_text():
    out = format_premise(
        "Whoever commits murder shall be punished with death.",
        framing=PREMISE_FRAMING_LABELED,
        provision_type="Section", provision_number="302", act="The Indian Penal Code, 1860",
    )
    assert out == ("Section 302 of The Indian Penal Code, 1860: "
                   "Whoever commits murder shall be punished with death.")
    # The statute text itself must pass through untouched — the framing may only
    # ADD the label the audited record already carries, never edit the evidence.
    assert out.endswith("Whoever commits murder shall be punished with death.")


def test_labeled_framing_falls_back_to_bare_when_label_parts_missing():
    """A record with incomplete metadata must degrade to current behaviour
    rather than emit a malformed premise like ': Whoever commits murder...'."""
    for kwargs in (
        {"provision_type": None, "provision_number": "302", "act": "IPC"},
        {"provision_type": "Section", "provision_number": None, "act": "IPC"},
        {"provision_type": "Section", "provision_number": "302", "act": None},
    ):
        assert format_premise("text", framing=PREMISE_FRAMING_LABELED, **kwargs) == "text"


def test_unknown_framing_is_rejected():
    with pytest.raises(ValueError):
        format_premise("text", framing="fancy")


# --------------------------------------------------------------------------
# device opt-in
# --------------------------------------------------------------------------

def test_verifier_defaults_to_cuda_so_cpu_is_never_a_silent_fallback():
    assert NLIVerifier("m", 0.7).device == "cuda"


def test_verifier_rejects_unknown_device():
    with pytest.raises(ValueError):
        NLIVerifier("m", 0.7, device="tpu")


def test_verifier_accepts_explicit_cpu_optin():
    assert NLIVerifier("m", 0.7, device="cpu").device == "cpu"


# --------------------------------------------------------------------------
# paraphrase must preserve legal effect
# --------------------------------------------------------------------------

def test_paraphrase_changes_wording_and_reports_which_rules_fired():
    text = "Whoever commits murder shall be punished with death, or imprisonment for life."
    out, fired = apply_paraphrase(text)
    assert out != text
    assert fired
    assert "Any person who" in out


def test_paraphrase_never_introduces_or_removes_a_negation():
    """A 'paraphrase' that flips polarity would be a mislabelled contradiction
    sitting in the ENTAILED cell, silently corrupting the headline metric."""
    for text in [
        "Whoever commits murder shall be punished with death.",
        "The State shall not deny to any person equality before the law.",
        "Every High Court shall have power to issue directions.",
        "No person shall be deprived of his property save by authority of law.",
    ]:
        out, _ = apply_paraphrase(text)
        assert out.lower().count(" not ") == text.lower().count(" not "), text
        assert "not not" not in out.lower()


def test_paraphrase_reports_no_rules_when_nothing_matches():
    """Callers rely on an empty rule list to DROP the paraphrase conditions; if
    this silently returned the text unchanged with a non-empty list, E3/E4 would
    duplicate E1/E2 and the 2x2 would compare a cell against itself."""
    out, fired = apply_paraphrase("Zzz qqq wibble.")
    assert fired == []
    assert out == "Zzz qqq wibble."


# --------------------------------------------------------------------------
# negation must reverse legal effect, grammatically
# --------------------------------------------------------------------------

def test_negation_flips_prohibition_without_double_negating():
    """v1 shipped 'shall not' -> 'shall not not' by ordering a bare-'shall'
    rule ahead of the 'shall not' rule."""
    out, fired = apply_negation("The State shall not deny to any person equality before the law.")
    assert "not not" not in out
    assert fired == ["prohibition_lifted"]
    assert "shall deny" in out


def test_negation_never_produces_double_negation_on_any_corpus_shape():
    for text in [
        "Whoever commits murder shall be punished with death, and shall also be liable to fine.",
        "Every High Court shall have power to issue directions.",
        "The Court may at any time make such order as it thinks fit.",
        "The State shall not deny to any person equality before the law.",
        "Culpable homicide is murder if the act is done with the intention of causing death.",
        "'the State' includes the Government and Parliament of India.",
    ]:
        out, fired = apply_negation(text)
        assert fired, text
        assert "not not" not in out.lower(), text
        assert out != text, text


def test_negation_falls_back_to_sentential_negation_for_texts_with_no_modal():
    out, fired = apply_negation("Article 31 was deleted from Part III of the Constitution.")
    assert fired == ["sentential_negation_fallback"]
    assert out.startswith("It is not the case that ")


def test_punishment_negation_also_flips_the_trailing_fine_clause():
    """Negating only the main verb would leave the penalty clause asserting the
    opposite direction of the sentence, which is incoherent rather than false."""
    out, fired = apply_negation(
        "Whoever commits murder shall be punished with death, and shall also be liable to fine.")
    assert "shall not be punished with" in out
    assert "shall not be liable to any fine" in out
    assert "secondary_fine_negated" in fired


# --------------------------------------------------------------------------
# benchmark assembly
# --------------------------------------------------------------------------

def test_ids_are_stable_across_processes():
    """v1 used Python's hash(), which is salted per interpreter, so benchmark
    ids changed on every run and results could not be joined back to items."""
    code = ("import sys; sys.path.insert(0, r'%s'); "
            "from scripts.build_controlled_benchmark import _stable_id; "
            "print(_stable_id('Section 302 in The Indian Penal Code, 1860'))" % _PROTOTYPE_ROOT)
    seen = set()
    for _ in range(2):
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             cwd=str(_PROTOTYPE_ROOT))
        assert out.returncode == 0, out.stderr
        seen.add(out.stdout.strip())
    assert len(seen) == 1
    assert seen.pop() == _stable_id("Section 302 in The Indian Penal Code, 1860")


def test_build_emits_the_full_2x2_plus_contradiction_and_nei_conditions():
    records = [_rec(), _rec(key="Article 14 in Constitution of India",
                           text="The State shall not deny to any person equality before the law "
                                "or the equal protection of the laws within the territory of India.",
                           act="Constitution of India", ptype="Article", pnum="14")]
    items, _ = build_controlled_benchmark(records)
    conds = {i["condition"] for i in items}
    assert {"E1_verbatim", "E2_verbatim_attributed", "E3_paraphrase_bare",
            "E4_paraphrase_attributed", "C1_negated_bare", "C2_negated_attributed",
            "N1_other_provision", "N2_procedural_addition"} <= conds


def test_factor_flags_match_the_actual_hypothesis_text():
    """The 2x2 is only meaningful if the factor columns describe the strings."""
    records = [_rec(), _rec(key="Article 14 in Constitution of India",
                           text="The State shall not deny to any person equality before the law.",
                           act="Constitution of India", ptype="Article", pnum="14")]
    items, _ = build_controlled_benchmark(records)
    for it in items:
        assert it["factor_attribution"] == it["hypothesis"].startswith("According to ")


def test_build_output_passes_its_own_validator():
    records = [_rec(), _rec(key="Article 14 in Constitution of India",
                           text="The State shall not deny to any person equality before the law.",
                           act="Constitution of India", ptype="Article", pnum="14")]
    items, _ = build_controlled_benchmark(records)
    assert validate(items) == []


def test_validator_rejects_a_paraphrase_that_is_identical_to_its_source():
    items, _ = build_controlled_benchmark([_rec()])
    e3 = next(i for i in items if i["condition"] == "E3_paraphrase_bare")
    e3["hypothesis"] = e3["evidence_text"]
    assert any("identical to source" in e for e in validate(items))


def test_validator_rejects_double_negation_artifacts():
    items, _ = build_controlled_benchmark([_rec()])
    items[0]["hypothesis"] = "Whoever commits murder shall not not be punished with death."
    assert any("double-negation" in e for e in validate(items))


def test_validator_rejects_mislabelled_attribution_factor():
    items, _ = build_controlled_benchmark([_rec()])
    e1 = next(i for i in items if i["condition"] == "E1_verbatim")
    e1["factor_attribution"] = True
    assert any("factor_attribution" in e for e in validate(items))


def test_neutral_pairing_never_selects_the_same_provision():
    records = [_rec(), _rec(key="Article 14 in Constitution of India",
                           text="The State shall not deny to any person equality before the law.",
                           act="Constitution of India", ptype="Article", pnum="14")]
    items, _ = build_controlled_benchmark(records)
    for it in [i for i in items if i["condition"] == "N1_other_provision"]:
        assert it["hypothesis"] != it["evidence_text"]


def test_shipped_benchmark_file_is_present_and_valid():
    """Guards the committed artifact itself, not just the builder."""
    import json
    path = _PROTOTYPE_ROOT / "outputs" / "controlled_verifier_benchmark.jsonl"
    if not path.exists():
        pytest.skip("benchmark not built in this checkout")
    items = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert items
    assert validate(items) == []
    assert all(i["benchmark_tag"] == "CONTROLLED_VERIFIER_BENCHMARK" for i in items)
    # Gold labels must never have come from a model.
    assert all(i["construction_rules"] for i in items)
