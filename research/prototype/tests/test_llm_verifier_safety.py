"""Safety tests for the experimental generative verifier response parser."""
import pytest

from src.verifier import ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.llm_verifier import _parse_verdict


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("ENTAILED", ENTAILED),
        ("ENTAILED: supported by the statute", ENTAILED),
        ("contradicted", CONTRADICTED),
        ("NOT_ENOUGH_INFORMATION", NOT_ENOUGH_INFORMATION),
        ("NOT_ENOUGH_INFORMATION: evidence is incomplete", NOT_ENOUGH_INFORMATION),
        ("", NOT_ENOUGH_INFORMATION),
        ("The answer is ENTAILED", NOT_ENOUGH_INFORMATION),
        ("CONTRADICTED, but actually ENTAILED", NOT_ENOUGH_INFORMATION),
        ("ENTAILED/CONTRADICTED", NOT_ENOUGH_INFORMATION),
        ("ENTAILEDORCONTRADICTED", NOT_ENOUGH_INFORMATION),
        ("NEI", NOT_ENOUGH_INFORMATION),
        ("not enough information", NOT_ENOUGH_INFORMATION),
        ("The claim is not contradicted", NOT_ENOUGH_INFORMATION),
    ],
)
def test_verdict_parser_requires_unambiguous_leading_label(response, expected):
    assert _parse_verdict(response) == expected
