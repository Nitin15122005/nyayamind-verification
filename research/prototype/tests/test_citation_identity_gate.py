from __future__ import annotations

from types import SimpleNamespace

from src.pipeline import _citation_identity_sequence


def _claim(number: str, act: str = "indian penal code") -> dict:
    return {
        "citation_extracted": {
            "provision_type": "Section",
            "provision_number": number,
            "subsection": None,
            "act_norm": act,
        }
    }


def test_identity_sequence_preserves_order_and_occurrences():
    baseline = [_claim("302"), _claim("420"), _claim("302")]
    assert _citation_identity_sequence(baseline) == [
        ("Section", "302", None, "indian penal code"),
        ("Section", "420", None, "indian penal code"),
        ("Section", "302", None, "indian penal code"),
    ]


def test_identity_sequence_detects_deleted_citation():
    assert _citation_identity_sequence([_claim("302"), _claim("420")]) != (
        _citation_identity_sequence([_claim("302")])
    )


def test_identity_sequence_detects_duplicate_citation_injection():
    baseline = [_claim("302"), _claim("420")]
    corrected = [_claim("302"), _claim("420"), _claim("302")]
    assert _citation_identity_sequence(baseline) != _citation_identity_sequence(corrected)


def test_identity_sequence_detects_reordering_even_when_set_is_unchanged():
    baseline = [_claim("302"), _claim("420")]
    corrected = [_claim("420"), _claim("302")]
    assert _citation_identity_sequence(baseline) != _citation_identity_sequence(corrected)


def test_identity_sequence_accepts_identical_dict_and_parser_object_shapes():
    parser_like = SimpleNamespace(
        citation_extracted=SimpleNamespace(
            provision_type="Section",
            provision_number="302",
            subsection=None,
            act_norm="indian penal code",
        )
    )
    assert _citation_identity_sequence([_claim("302")]) == (
        _citation_identity_sequence([parser_like])
    )
