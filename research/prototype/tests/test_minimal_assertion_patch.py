from src.pipeline import _splice_assertion_patch


def test_minimal_patch_changes_only_the_exact_target_phrase():
    original = (
        "Section 302 of the Indian Penal Code prescribes a fine only. "
        "Section 34 addresses common intention."
    )
    claim = "Section 302 of the Indian Penal Code prescribes a fine only."
    result = _splice_assertion_patch(
        original, claim, claim,
        "a fine only", "imprisonment for life or death, and a fine",
    )
    assert result == (
        "Section 302 of the Indian Penal Code prescribes imprisonment for life "
        "or death, and a fine. Section 34 addresses common intention."
    )


def test_patch_rejects_non_unique_original_span():
    claim = "Here the act causes harm and the act causes harm."
    assert _splice_assertion_patch(
        claim, claim, claim, "the act", "the conduct"
    ) is None


def test_patch_rejects_whole_assertion_rewrite():
    claim = "Section 302 prescribes a fine only."
    assert _splice_assertion_patch(
        claim, claim, claim, claim, "Whoever commits murder is punished."
    ) is None


def test_patch_rejects_citation_changes_or_injection():
    claim = "Section 302 prescribes a fine only."
    assert _splice_assertion_patch(
        claim, claim, claim, "a fine only", "Section 304 prescribes imprisonment"
    ) is None


def test_patch_rejects_ambiguous_target_sentence():
    claim = "The same sentence. The same sentence."
    assert _splice_assertion_patch(
        claim, "The same sentence.", "The same sentence.",
        "same", "different",
    ) is None


def test_patch_rejects_empty_or_overlong_patch():
    claim = "The provision prescribes a fine only."
    assert _splice_assertion_patch(
        claim, claim, claim, "", "imprisonment"
    ) is None
    assert _splice_assertion_patch(
        claim, claim, claim, "a fine only", "x" * 241
    ) is None
