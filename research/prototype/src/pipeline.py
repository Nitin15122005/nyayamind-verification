"""
Orchestrates one case through: generate -> extract claims -> match evidence
-> [verify] -> [selective correction] -> re-verify -> output record.

Modes:
  A = generation only
  B = generation + verification (diagnostic only; final_field is always the
      original generated text — verification never changes the output in
      mode B, only records what it found)
  C = generation + verification + selective correction

All three modes share the exact same generation + claim-extraction +
evidence-matching stage (run once, independent of mode) so that comparing
A vs B vs C is a paired comparison against an identical baseline, not three
different generations.

Known v0 simplification (documented, not hidden): if a field has more than
one flagged claim, only the FIRST flagged claim drives the single
correction attempt (see corrector.py — the correction prompt targets one
flagged sentence). Multi-claim-per-field correction is out of scope for
this prototype.
"""
from __future__ import annotations

import datetime
import re
import sys
from typing import Optional

from . import claim_parser
from .evidence_matcher import match_evidence, classify_no_evidence, NO_EVIDENCE
from .verifier import (
    ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
    format_premise, PREMISE_FRAMINGS, PREMISE_FRAMING_BARE,
)


def resolve_premise_framing(config: dict) -> str:
    """Read verification.premise_framing from config, defaulting to "bare".

    Validated here rather than at the point of use so a typo in prototype.yaml
    fails immediately with the offending value named, instead of silently
    falling through to bare framing and producing a run that looks like a
    labeled-framing ablation but is not one.
    """
    framing = (config.get("verification") or {}).get("premise_framing", PREMISE_FRAMING_BARE)
    if framing not in PREMISE_FRAMINGS:
        raise ValueError(
            f"verification.premise_framing must be one of {list(PREMISE_FRAMINGS)}, "
            f"got {framing!r}"
        )
    return framing


def _premise_for_claim(rec: dict, framing: str) -> str:
    """Build the NLI premise for one matched claim record.

    The provision label comes from `_evidence_provision`, which carries the
    MATCHED EVIDENCE RECORD's own identity — deliberately not the claim's
    `citation_extracted`, which is what the generator wrote and may be wrong or
    fuzzily matched. The premise must describe the evidence being used as the
    premise, otherwise a mis-cited claim would be handed a premise labeled with
    its own error.
    """
    prov = rec.get("_evidence_provision") or {}
    return format_premise(
        rec["evidence_text"],
        framing=framing,
        provision_type=prov.get("provision_type"),
        provision_number=prov.get("provision_number"),
        act=prov.get("act"),
    )

MODES = ("A", "B", "C")

# Default system prompt for ASSERTION-AWARE correction (correction.
# assertion_aware: true — see apply_selective_correction_assertion_aware()).
# Deliberately asks for ONE fragment, not a sentence or paragraph — the
# narrower scope is the entire point of this correction mode (see that
# function's docstring). Overridable via correction.assertion_span_system_prompt
# in config, same pattern as the legacy correction.system_prompt.
_DEFAULT_ASSERTION_SPAN_SYSTEM_PROMPT = (
    "You are correcting one short factual fragment inside a sentence about "
    "an Indian statute, in the \"Statutory Grounding\" section of a court "
    "judgment summary. You will be given the case facts, the flagged "
    "fragment (unsupported or contradicted by the cited law), and (if "
    "available) the actual text of the relevant statute. Rewrite ONLY the "
    "fragment so it is consistent with the statute text. Do not add a "
    "citation, section number, or Act name that is not already present in "
    "the fragment you were given. Output ONLY the corrected fragment as "
    "plain text — no quotation marks, no surrounding sentence, no "
    "explanation, nothing else."
)


def _should_trigger_correction(claim_record: dict) -> bool:
    """Per the approved design: trigger for CONTRADICTED (regardless of
    confidence), or for NOT_ENOUGH_INFORMATION specifically when it's the
    low-confidence downgrade (sub_reason == "low_confidence") — NOT for a
    genuine high-confidence "neutral" NLI prediction, which is a legitimate
    NEI verdict on its own, not a flagged failure. NO_EVIDENCE never
    triggers, regardless of this function (callers only pass claims that
    already have evidence).

    Deliberately does NOT also check `negation_contradiction_caveat` (see
    apply_verification) — this function answers "was this claim already a
    problem in the baseline," which is also reused by
    _reverify_sibling_regressions() to identify pre-existing failures to
    exclude from its own, separate check. Whether a negation-flagged
    CONTRADICTED verdict is trusted enough to actually ATTEMPT an automatic
    correction on is a narrower, different question, applied only at the
    one call site in apply_selective_correction() that builds the
    correction-trigger list."""
    verdict = claim_record["verdict"]
    if verdict == CONTRADICTED:
        return True
    if verdict == NOT_ENOUGH_INFORMATION and claim_record.get("sub_reason") == "low_confidence":
        return True
    return False


# A claim asserting that a provision does NOT apply/is not applicable
# ("Neither Section 302 nor Section 304 ... applies to this case.") is
# empirically confirmed (real MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli,
# real IPC Section 302 evidence text) to reach CONTRADICTED at very high
# confidence (0.998) purely from the grammatical negation — the same
# underlying legal content phrased affirmatively ("Section 302 ... applies
# to this case.") reaches ENTAILED (0.896) against the identical premise.
# This is a well-documented general NLI weakness (models learning that
# negation words in the hypothesis correlate with "contradiction" in
# training data, independent of genuine logical entailment), not something
# any premise-construction or code fix can repair in a fixed pretrained
# model's weights. It matters here specifically because CONTRADICTED always
# triggers automatic correction (_should_trigger_correction above): without
# this carve-out, the pipeline could "fix" a claim that correctly, truthfully
# asserts a NEGATIVE legal conclusion (e.g. explaining why a LESSER charge
# applies instead) by rewriting it into an affirmative statement — which, if
# the rewrite happens to re-verify ENTAILED, would ship a claim asserting
# the OPPOSITE of what may have been a true statement, discovered and
# confirmed during this session's adversarial claim-parser audit.
#
# Deliberately narrow and lexical (matching this project's established
# "never guess, prefer declining" style elsewhere in claim_parser.py):
# catches the clear-cut, unambiguous negation shapes actually demonstrated,
# not a general negation detector. A claim matching none of these patterns
# is unaffected — this only ever REMOVES a claim from automatic correction,
# it never adds, loosens, or changes what counts as CONTRADICTED, ENTAILED,
# or NO_EVIDENCE; the claim's own verdict/confidence/sub_reason are
# untouched and remain fully visible for manual review.
_NEGATION_MARKER_RE = re.compile(
    r"\bneither\b.{0,200}?\bnor\b"
    r"|\b(?:does|do|did)\s+not\s+apply\b"
    r"|\b(?:is|are|was|were)\s+not\s+applicable\b"
    r"|\bno\s+longer\s+appli(?:es|cable)\b"
    r"|\bnot\s+applicable\b",
    re.IGNORECASE,
)


def _negation_marker_present(text: str) -> bool:
    return bool(_NEGATION_MARKER_RE.search(text))


def _software_versions() -> dict:
    versions = {"python": sys.version.split()[0]}
    for pkg in ("torch", "transformers", "accelerate", "bitsandbytes", "peft"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not_installed"
    return versions


def generate_and_parse(case, generator, exact_index, all_usable, fuzzy_threshold: float) -> dict:
    """Shared stage 1: generate the field once, extract claims, match
    evidence for each claim. Independent of mode."""
    generated_text, gen_meta = generator.generate(case.case_text)
    claims = claim_parser.extract_claims(generated_text)

    claim_records = []
    for claim in claims:
        match = match_evidence(
            claim.citation_extracted, exact_index, all_usable, fuzzy_threshold
        )
        claim_records.append(
            {
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                # Additive field, not read by verification/correction by
                # default (apply_verification's hypothesis is still
                # claim_text — see claim_parser.py's Claim docstring). A
                # conservative, per-citation sub-span of claim_text for
                # bundled multi-citation sentences where one is safely
                # identifiable (e.g. "Section 302 prescribes X, while
                # Section 34 prescribes Y" -> each gets its own clause);
                # equals claim_text whenever no safe split was found.
                "assertion_text": claim.assertion_text,
                # Additive, structured generalization of assertion_text: a
                # list of independently-required VERBATIM fragments (never
                # concatenated/reordered/synthesized — see claim_parser.py's
                # Claim.assertion_spans docstring). Degenerates to
                # [assertion_text] whenever no richer (e.g. "respectively")
                # pattern applies, so this is a no-op for every claim not
                # touched by that new mechanism.
                "assertion_spans": list(claim.assertion_spans),
                "citation_extracted": claim.citation_extracted.as_dict()
                if claim.citation_extracted
                else None,
                "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
                "evidence_text": match.evidence.canonical_text if match.matched else None,
                # Underscore-prefixed: internal bookkeeping consumed by
                # _premise_for_claim() and stripped before output, so enabling
                # labeled framing does not change the output record schema and
                # new runs stay diffable against the committed A/B/C baselines.
                "_evidence_provision": {
                    "provision_type": match.evidence.provision_type,
                    "provision_number": match.evidence.provision_number,
                    "act": match.evidence.act,
                } if match.matched else None,
                # NOT underscore-prefixed: this is legitimate reproducibility
                # metadata (how the evidence was matched: exact/fuzzy/none)
                # and must survive into the output record's claims list, not
                # be stripped by run_case()'s internal-bookkeeping filter.
                "evidence_match_method": match.match_method,
                # Additive field (measurement/ablation infrastructure, not
                # live behavior — never read by any verification/correction
                # decision): WHY this claim is NO_EVIDENCE, using the exact
                # same taxonomy already established and validated project-
                # wide by scripts/audit_no_evidence_taxonomy_v2.py (see
                # evidence_matcher.classify_no_evidence's docstring for the
                # four categories). None for any claim that DID match
                # evidence — there is nothing to explain. Distinguishing
                # "parser couldn't resolve the act" from "corpus genuinely
                # lacks this provision" from "a different Act/edition
                # exists" from "a possible normalization gap worth review"
                # was previously only derivable by re-running that
                # standalone script over already-produced outputs.
                "no_evidence_category": (
                    classify_no_evidence(claim.citation_extracted, all_usable, fuzzy_threshold)
                    if not match.matched else None
                ),
                "verdict": None,          # filled by apply_verification (mode B/C)
                "confidence": None,
                "sub_reason": None,
                "verifier_model": None,
                # Additive field (measurement infrastructure, not live
                # behavior): the verifier's FULL raw label distribution
                # (all three of entailment/neutral/contradiction, not just
                # the argmax `confidence`), filled by apply_verification.
                # Without this, a low-confidence downgrade to
                # NOT_ENOUGH_INFORMATION (sub_reason="low_confidence")
                # permanently discards which raw label was actually the
                # argmax and how close the other two were — recomputing
                # verdicts under a different confidence_threshold, or
                # measuring calibration, would otherwise require re-running
                # the model rather than being derivable from the committed
                # output record. Never read by any live decision (verdict/
                # sub_reason/confidence remain the single source of truth
                # for pipeline behavior) — purely additive, for post-hoc
                # analysis and future ablation/threshold-sensitivity work.
                "raw_scores": None,
                # Additive field (measurement infrastructure, not live
                # behavior): whether the verifier's premise+hypothesis pair
                # exceeded max_sequence_length and was silently truncated
                # (see verifier.VerificationResult.input_truncated's
                # docstring) before this verdict was computed. None for any
                # claim never verified (NO_EVIDENCE) — there is nothing to
                # report. Never read by any live decision.
                "input_truncated": None,
                # Additive field (measurement/safety infrastructure): set by
                # apply_verification once verified, to a bool — True only
                # when the verdict is CONTRADICTED AND the claim's own text
                # matches a known negation pattern (see _NEGATION_MARKER_RE
                # above _should_trigger_correction). None until verified.
                # When True, this SPECIFIC claim is excluded from
                # apply_selective_correction's automatic-correction trigger
                # list (never auto-"fixed"), because a negation-driven
                # CONTRADICTED verdict is empirically confirmed unreliable —
                # the verdict/confidence themselves are left untouched and
                # fully visible for manual review.
                "negation_contradiction_caveat": None,
            }
        )
        if not match.matched:
            claim_records[-1]["verdict"] = NO_EVIDENCE  # NO_EVIDENCE is fixed regardless of mode

    return {
        "document_id": case.document_id,
        "case_text": case.case_text,
        "generated_field": {
            "text": generated_text,
            "model": gen_meta.model_id,
            "quantization": gen_meta.quantization,
            "generation_params": {
                "max_new_tokens": gen_meta.max_new_tokens,
                "do_sample": gen_meta.do_sample,
                "temperature": gen_meta.temperature,
                "top_p": gen_meta.top_p,
                "seed": gen_meta.seed,
            },
            "generated_at": gen_meta.generated_at,
        },
        "claims": claim_records,
    }


def _assertion_spans_hypothesis(rec: dict) -> Optional[str]:
    """Builds a narrower hypothesis from `assertion_spans` for the ONE case
    `assertion_text` alone cannot narrow: a "respectively" claim (see
    claim_parser.py's `_assign_respectively_spans`), where `assertion_text`
    is left equal to the full `claim_text` by design (the split mechanism is
    structurally different — a LIST of two independently-required verbatim
    fragments, `[bare_number_span, description_item]`, not one contiguous
    clause) but `assertion_spans` genuinely narrows to just this citation's
    own provision number and its own paired description.

    Returns None (caller falls back to claim_text/assertion_text) unless
    ALL of: assertion_spans has exactly 2 fragments, the first is exactly
    this claim's own provision number (confirms it's the respectively
    shape, not some other future assertion_spans producer), and evidence
    was matched (so `_evidence_provision` — the provision LABEL, not
    invented — is available).

    Construction: "<provision_type> <provision_number> <description_item>"
    — e.g. "Section 302 murder". Every word is either the citation's own
    provision label (already used verbatim elsewhere for labeled premise
    framing) or `assertion_spans[-1]`, a genuine contiguous substring of
    the model's own generated text. No word is invented and no verb is
    synthesized — this is deliberately a plain juxtaposition, not a
    grammatically smoothed sentence, so its NLI behavior can be measured
    honestly rather than assumed (see
    outputs/assertion_spans_primary_hypothesis_benchmark_report.md)."""
    spans = rec.get("assertion_spans") or []
    citation = rec.get("citation_extracted") or {}
    provision = rec.get("_evidence_provision") or {}
    if len(spans) != 2:
        return None
    if not citation.get("provision_number") or spans[0] != citation["provision_number"]:
        return None
    if not provision.get("provision_type") or not provision.get("provision_number"):
        return None
    description = spans[1]
    if not description:
        return None
    return f"{provision['provision_type']} {provision['provision_number']} {description}"


def apply_verification(
    baseline: dict,
    verifier,
    premise_framing: str = PREMISE_FRAMING_BARE,
    narrow_primary_hypothesis: bool = False,
    assertion_span_primary_hypothesis: bool = False,
) -> None:
    """Mutates baseline['claims'] in place, filling verdict/confidence for
    every claim that has matched evidence. Claims with no evidence keep
    their NO_EVIDENCE verdict untouched — the verifier is never called for
    them, by design (an NLI verdict would be meaningless without a
    premise).

    `premise_framing` defaults to bare so that any caller not yet passing it
    keeps the exact behaviour that produced the committed outputs; callers opt
    into the ablation by threading resolve_premise_framing(config) through.

    `narrow_primary_hypothesis` (production default since 2026-09-09; see
    outputs/narrow_primary_hypothesis_benchmark_report.md for the measured
    comparison this default is based on): when True, and a claim has its
    own narrower `assertion_text` (a verbatim, non-fabricated per-citation
    clause/gloss — see claim_parser.py's `_assign_assertion_texts`), verify
    THAT instead of the full `claim_text`. This is the exact same technique
    `narrow_reverification_hypothesis` already applies during correction
    re-verification (see apply_selective_correction below), extended here
    to the PRIMARY verification pass. Never widens what counts as
    evidence-consistent — assertion_text is always a genuine substring of
    the model's own generated text, never synthesized.

    `assertion_span_primary_hypothesis` (opt-in, default False —
    EXPERIMENTAL, not yet the production default; see
    outputs/assertion_spans_primary_hypothesis_benchmark_report.md for the
    measured comparison this default is based on): extends the above to
    "respectively" claims, the one case `assertion_text` alone leaves
    unnarrowed. Only takes effect when `narrow_primary_hypothesis` is also
    True and `assertion_text` did not already narrow the claim. See
    `_assertion_spans_hypothesis()` above for exactly how the hypothesis is
    built and why it never synthesizes content.
    """
    if premise_framing not in PREMISE_FRAMINGS:
        raise ValueError(
            f"premise_framing must be one of {list(PREMISE_FRAMINGS)}, got {premise_framing!r}"
        )
    for rec in baseline["claims"]:
        if rec["evidence_text"] is None:
            continue  # already NO_EVIDENCE, verifier not invoked
        hypothesis = rec["claim_text"]
        used_assertion_text = False
        if narrow_primary_hypothesis and rec.get("assertion_text") and rec["assertion_text"] != rec["claim_text"]:
            hypothesis = rec["assertion_text"]
            used_assertion_text = True
        if (
            narrow_primary_hypothesis
            and assertion_span_primary_hypothesis
            and not used_assertion_text
        ):
            span_hypothesis = _assertion_spans_hypothesis(rec)
            if span_hypothesis is not None:
                hypothesis = span_hypothesis
        result = verifier.verify(
            premise=_premise_for_claim(rec, premise_framing), hypothesis=hypothesis
        )
        rec["verdict"] = result.label
        rec["confidence"] = result.confidence
        rec["sub_reason"] = result.sub_reason
        rec["verifier_model"] = result.verifier_model
        rec["raw_scores"] = result.raw_scores
        rec["input_truncated"] = result.input_truncated
        rec["verified_hypothesis"] = hypothesis
        rec["negation_contradiction_caveat"] = (
            result.label == CONTRADICTED and _negation_marker_present(rec["claim_text"])
        )


def _fragment_present(fragment: str, text: str) -> bool:
    """True if `fragment` is present in `text` as itself, not merely as a
    substring embedded inside a larger token.

    Real, reproduced gap this closes: plain Python `in` containment (the
    prior check) treats the bare provision number "34" (see
    claim_parser.py's `_bare_number_span`, used in `assertion_spans` for
    the "respectively" pattern — e.g. "sections 302, 149, 323, and 34 ...,
    which respectively deal with ...") as "present" even when the
    corrected text instead says "Section 134" — a genuinely different
    provision. "34" is trivially a substring of "134", so a corrector that
    silently changed an unflagged sibling claim's OWN section number could
    ship undetected: this is the production-default `atomic_scope_check:
    "assertion_spans"` path, and the independent `_reverify_sibling_
    regressions` safety net does not catch it either, since it explicitly
    skips a sibling whose citation no longer re-extracts at all, assuming
    (this function's job) already rejected the case.

    A `\\b` word-boundary is anchored at whichever end of `fragment` is
    itself a word character — never forced onto a non-word edge (e.g. the
    trailing ")" of a parenthetical-gloss fragment like "34 (common
    intention)", where a trailing `\\b` would be meaningless). This only
    TIGHTENS the check: a fragment that is a genuine verbatim copy of the
    original text always already sits at a real word/punctuation boundary
    at its true occurrence (sentences, clauses, and parenthetical glosses
    are all extracted at real delimiters — see claim_parser.py), so this
    can only turn a false "present" into a correct "absent", never the
    reverse — no legitimate, honestly-preserved fragment can fail this
    that would have passed the old check."""
    if not fragment:
        return False
    pattern = re.escape(fragment)
    if fragment[0].isalnum() or fragment[0] == "_":
        pattern = r"\b" + pattern
    if fragment[-1].isalnum() or fragment[-1] == "_":
        pattern = pattern + r"\b"
    return re.search(pattern, text) is not None


def _scope_violation(
    baseline_claims: list[dict],
    target_claim_id: str,
    corrected_text: str,
    use_assertion_text: bool = False,
    use_assertion_spans: bool = False,
) -> bool:
    """Programmatic enforcement of selective correction's contract: every
    UNFLAGGED claim (a citation-bearing sentence extracted from the
    original field, other than the one being corrected) must reappear
    verbatim in the corrected text. The correction prompt already asks the
    model for this ("copy verbatim/unchanged"), but a prompt is not an
    enforcement mechanism — this is the actual gate. Returns True
    (violation) if any unflagged claim's required text is no longer
    present in the corrected text.

    Deliberately claim-scoped, not whole-paragraph-sentence-scoped: the
    corrector is only constrained w.r.t. the claims this pipeline already
    tracks. Non-claim prose or newly introduced sentences elsewhere in the
    paragraph are outside what "unflagged claims must remain unchanged"
    covers here.

    `use_assertion_text` (opt-in, default False — legacy behaviour,
    byte-identical to every prior committed run): when True, an unflagged
    claim is checked against its own `assertion_text` — a conservative,
    verbatim, per-citation sub-span of `claim_text` (see
    claim_parser.py's `_assign_assertion_texts`) that narrows to just this
    claim's own clause/gloss when one of several safe patterns is found,
    and falls back to the FULL `claim_text` (identical to legacy) whenever
    no safe split applies. This directly targets the dominant real
    scope-violation cause on natural data: many claims sharing one long,
    bundled multi-citation sentence as their `claim_text`, so any edit
    ANYWHERE in that sentence — even one confined to the flagged citation's
    own portion — breaks every other claim's byte-for-byte preservation
    check under the legacy (claim_text-only) rule. `assertion_text` is
    never required to exist on a claim record (`.get(...) or claim_text`
    falls back safely for any baseline built by code that predates this
    field), so this is safe against any caller, old or new.

    `use_assertion_spans` (opt-in, default False, independent of
    `use_assertion_text`): checks a LIST of independently-required
    VERBATIM fragments (`assertion_spans` — see claim_parser.py's Claim
    docstring) instead of one string — ALL fragments must be present, not
    just one. This is strictly a superset check compared to
    `assertion_text` alone: it exists for claims (the "respectively"
    pattern) whose relevant content is not one contiguous span at all —
    e.g. a citation's own provision number lives in one place and its
    paired description lives elsewhere in the same sentence — so no single
    verbatim substring can represent "this claim's content" without either
    dragging in unrelated sibling content (the legacy/assertion_text
    behaviour) or fabricating a combined sentence (never done anywhere in
    this codebase). Falls back to `[assertion_text or claim_text]` when
    `assertion_spans` is absent (any caller/claim predating this field),
    so this degrades safely to the assertion_text (or legacy) check rather
    than ever silently passing."""
    for rec in baseline_claims:
        if rec["claim_id"] == target_claim_id:
            continue
        if use_assertion_spans:
            fragments = rec.get("assertion_spans") or [rec.get("assertion_text") or rec.get("claim_text")]
            if not all(f and _fragment_present(f, corrected_text) for f in fragments):
                return True
            continue
        check_text = rec.get("claim_text")
        if use_assertion_text:
            check_text = rec.get("assertion_text") or check_text
        if not _fragment_present(check_text, corrected_text):
            return True
    return False


def _splice_assertion_correction(
    original_field_text: str,
    target_claim_text: str,
    target_span: str,
    corrected_fragment: str,
) -> Optional[str]:
    """Deterministic string splice used by ASSERTION-AWARE correction (see
    apply_selective_correction_assertion_aware()) — NOT an LLM regeneration
    step. Replaces `target_span` inside `target_claim_text`, then
    replaces the resulting corrected claim text inside `original_field_text`,
    both via a single exact-substring `.replace(..., 1)`.

    `target_span` is the CONTENT fragment being corrected — for an ordinary
    claim this is `assertion_text` (== `assertion_spans[-1]`, since
    `assertion_spans` defaults to `[assertion_text]`); for a "respectively"
    claim with a genuine 2-element `assertion_spans`
    (`[bare_number_span, description_item]`, see claim_parser.py's
    `_assign_respectively_spans`) this is `assertion_spans[-1]` — the
    description item, never the bare number (a citation identifier, not
    correctable content; see `apply_selective_correction_assertion_aware`'s
    separate structural-span preservation check for that element).

    Fails closed (returns None) rather than guessing whenever a `.replace`
    would be ambiguous or impossible:
      - `corrected_fragment` empty (the corrector returned nothing usable —
        a real, observed LLM failure mode for a narrow "just the fragment"
        instruction, distinct from a genuine no-op edit, which returns the
        UNCHANGED fragment, not an empty one).
      - `target_span` does not occur in `target_claim_text`
        EXACTLY ONCE (should be structurally guaranteed by claim_parser.py,
        which always defines assertion_text/assertion_spans elements as
        genuine substrings of claim_text — checked explicitly anyway rather
        than assumed, per this project's "a prompt/invariant is not an
        enforcement mechanism" convention).
      - the resulting corrected claim text does not occur, or occurs more
        than once, inside `original_field_text` — guards against a
        duplicate-sentence edge case where blind replacement could silently
        edit the wrong occurrence.

    A `.replace(..., 1)` on a non-unique match edits only the FIRST
    occurrence silently, which would be worse than failing here — a
    caller trusting the returned text as "only the target span changed"
    when a different, unintended occurrence was actually spliced."""
    if not corrected_fragment:
        return None
    if target_claim_text.count(target_span) != 1:
        return None
    corrected_claim_text = target_claim_text.replace(target_span, corrected_fragment, 1)
    if original_field_text.count(target_claim_text) != 1:
        return None
    return original_field_text.replace(target_claim_text, corrected_claim_text, 1)


def _citation_identity(citation) -> Optional[tuple]:
    """(provision_type, provision_number, act_norm) — the same three fields
    the replacement-matching logic below always required, extracted once so
    both the baseline claim dicts (plain dicts) and freshly re-parsed
    claim_parser objects (ExtractedCitation instances) can be compared with
    the same function. Returns None if there is no citation at all (never
    matches anything, by design — an uncited claim cannot be safely
    re-verified)."""
    if citation is None:
        return None
    if isinstance(citation, dict):
        return (citation.get("provision_type"), citation.get("provision_number"), citation.get("act_norm"))
    return (citation.provision_type, citation.provision_number, citation.act_norm)


def _reverify_sibling_regressions(
    baseline: dict, corrected_text: str, target_claim_id: str, config: dict,
) -> list[dict]:
    """Independent safety net for the (opt-in) assertion_text/assertion_spans
    scope checks: those checks only require a NARROWER, per-citation
    fragment to survive verbatim, which is deliberately weaker than the
    legacy full-sentence requirement. That gap could in principle let a
    correction ship even though it altered a sibling claim's wording enough
    to change what it entails — the sibling's own required fragment
    survived, but the sentence around it did not.

    This re-parses the corrected text, finds each OTHER evidence-matched
    claim's own counterpart (same ordinal-position-among-same-citation-
    identity technique `apply_selective_correction` already uses for the
    target), and genuinely re-verifies it against its OWN evidence —
    exactly as if it were itself being checked. Returns the list of
    siblings that come back CONTRADICTED (a real, independently-confirmed
    regression) — empty if none, which is the expected, common case
    (byte-for-byte preserved siblings can never change verdict, since
    verification is a deterministic function of premise+hypothesis; this
    only ever finds something when the sibling's SURROUNDING text, not its
    required fragment, actually changed).

    Never used to loosen anything — only ever a reason to REJECT a
    correction that the scope check alone would have allowed.

    Excludes a sibling whose OWN baseline verdict was ALREADY flagged
    (`_should_trigger_correction` — CONTRADICTED, or low-confidence NEI)
    ONLY when it is ALSO genuinely untouched by this edit (its full
    original `claim_text` still appears verbatim in `corrected_text`) — in
    that case re-verifying it is a proven no-op (byte-for-byte preserved
    siblings can never change verdict, since verification is a
    deterministic function of premise+hypothesis) and re-flagging it here
    would conflate "my edit broke something" with "something else was
    already broken, and I never touched it," corrupting failure-category
    attribution. That sibling's own pre-existing CONTRADICTED/NEI verdict
    already remains fully visible in its own claim record — nothing is
    hidden by excluding it here, only mislabeled here.

    Deliberately does NOT skip an already-flagged sibling whose full
    `claim_text` was NOT preserved verbatim (its own required
    assertion_text/span fragment may still have survived, satisfying the
    scope check, while text elsewhere in its SAME sentence changed) — a
    real, confirmed gap this narrower condition closes: an unqualified
    "already flagged -> always skip" rule let a sibling whose surrounding
    context genuinely changed ship unexamined, silently discarding exactly
    the kind of regression this safety net exists to catch."""
    regressions = []
    reverify_claims = claim_parser.extract_claims(corrected_text)
    for rec in baseline["claims"]:
        if rec["claim_id"] == target_claim_id:
            continue
        if _should_trigger_correction(rec) and rec["claim_text"] in corrected_text:
            continue  # pre-existing failure, AND genuinely untouched by this edit
        if rec["evidence_text"] is None:
            continue  # NO_EVIDENCE claim: nothing to re-verify against
        identity = _citation_identity(rec["citation_extracted"])
        if identity is None:
            continue
        same_identity_baseline = [
            r for r in baseline["claims"] if _citation_identity(r["citation_extracted"]) == identity
        ]
        ordinal = next(i for i, r in enumerate(same_identity_baseline) if r is rec)
        same_identity_reextracted = [
            c for c in reverify_claims if _citation_identity(c.citation_extracted) == identity
        ]
        if ordinal >= len(same_identity_reextracted):
            continue  # structurally missing post-edit; the scope check already rejects this case
        counterpart = same_identity_reextracted[ordinal]
        match = match_evidence(
            counterpart.citation_extracted, baseline["_exact_index"], baseline["_all_usable"],
            config["evidence_matching"]["fuzzy_token_overlap_threshold"],
        )
        if not match.matched:
            continue
        result = baseline["_verifier"].verify(
            premise=format_premise(
                match.evidence.canonical_text,
                framing=resolve_premise_framing(config),
                provision_type=match.evidence.provision_type,
                provision_number=match.evidence.provision_number,
                act=match.evidence.act,
            ),
            hypothesis=counterpart.claim_text,
        )
        if result.label == CONTRADICTED:
            regressions.append({
                "claim_id": rec["claim_id"], "claim_text": counterpart.claim_text,
                "evidence_id": match.evidence.dataset_citation_key,
                "verdict": result.label, "confidence": result.confidence,
                "raw_scores": result.raw_scores,  # see generate_and_parse's raw_scores comment
                "input_truncated": result.input_truncated,
            })
    return regressions


def apply_selective_correction(baseline: dict, case, corrector, config: dict) -> dict:
    """Returns a correction summary dict. Triggers at most once, for the
    FIRST claim whose verdict is CONTRADICTED or NOT_ENOUGH_INFORMATION
    (any sub_reason) — never for NO_EVIDENCE. Re-verifies once afterward.

    Enforces the selective-correction scope programmatically: if the
    corrector changes any sentence other than the flagged one, the
    corrected text is never shipped — status is set to
    "correction_scope_violation" and both the original and regenerated
    texts are retained in the output for inspection.

    Excludes any claim with `negation_contradiction_caveat` True — a
    negation-driven CONTRADICTED verdict is empirically confirmed
    unreliable (see `_NEGATION_MARKER_RE`'s docstring) and must never
    automatically drive a rewrite; its own verdict stays visible in the
    claim record for manual review, it is simply never auto-"fixed"."""
    flagged = [
        rec for rec in baseline["claims"]
        if _should_trigger_correction(rec) and not rec.get("negation_contradiction_caveat")
    ]
    original_field_text = baseline["generated_field"]["text"]
    if not flagged:
        return {
            "triggered_for_claim_id": None,
            "attempts": 0,
            "status": "not_triggered",
            "regenerated_text": None,
            "original_field_text": original_field_text,
            "reverification": None,
        }

    target = flagged[0]
    corrected_text, corr_meta = corrector.correct(
        case_text=case.case_text,
        original_field_text=original_field_text,
        flagged_claim_text=target["claim_text"],
        evidence_text=target["evidence_text"],  # may be None (contradicted-with-no-evidence is impossible by construction, but kept defensive)
    )
    corr_meta_dict = {
        "model": corr_meta.model_id,
        "max_new_tokens": corr_meta.max_new_tokens,
        "do_sample": corr_meta.do_sample,
        "seed": corr_meta.seed,
        "corrected_at": corr_meta.corrected_at,
    }

    # atomic_scope_check: false (legacy) | true (assertion_text) |
    # "assertion_spans" (structured, multi-fragment — see _scope_violation).
    # Both truthy values enable the assertion_text check; only the string
    # form additionally enables assertion_spans.
    atomic_scope_check_mode = (config.get("correction") or {}).get("atomic_scope_check", False)
    use_assertion_text = bool(atomic_scope_check_mode)
    use_assertion_spans = atomic_scope_check_mode == "assertion_spans"
    if _scope_violation(
        baseline["claims"], target["claim_id"], corrected_text,
        use_assertion_text, use_assertion_spans,
    ):
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 1,
            "status": "correction_scope_violation",
            "regenerated_text": corrected_text,
            "original_field_text": original_field_text,
            "reverification": None,
            "corr_meta": corr_meta_dict,
        }

    # Unauthorized-content-injection check. _scope_violation() above only
    # verifies that every EXISTING unflagged claim's own text survives — it
    # has no concept of "no NEW citation may be introduced." A corrector
    # that correctly fixes the flagged claim but ALSO hallucinates an extra,
    # never-requested citation elsewhere in the paragraph (a real, plausible
    # LLM failure mode — the correction prompt asks for one targeted edit,
    # not "add nothing else") would pass the scope check outright: the new
    # sentence is not extracted as a baseline claim, so nothing requires it
    # to be absent. Reject before any ordinal-matching/re-verification work,
    # same priority as a scope violation, since this is scope enforcement
    # too — just for additions rather than alterations/removals.
    reverify_claims = claim_parser.extract_claims(corrected_text)
    baseline_identities = {
        _citation_identity(rec["citation_extracted"]) for rec in baseline["claims"]
    }
    baseline_identities.discard(None)
    if any(
        _citation_identity(c.citation_extracted) is not None
        and _citation_identity(c.citation_extracted) not in baseline_identities
        for c in reverify_claims
    ):
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 1,
            "status": "correction_unauthorized_addition",
            "regenerated_text": corrected_text,
            "original_field_text": original_field_text,
            "reverification": None,
            "corr_meta": corr_meta_dict,
        }

    # Re-parse + re-match + re-verify ONLY the previously-flagged claim's
    # replacement sentence, by finding the sentence in the corrected text
    # whose citation matches the originally-flagged claim's citation.
    #
    # A document can contain MULTIPLE claims that cite the exact same
    # provision (e.g. one sentence lists "sections 406 and 420", and a
    # later sentence separately asserts something specific about "Section
    # 420") — citation identity alone is then ambiguous between them.
    # Matching by ORDINAL POSITION among same-citation claims resolves
    # this deterministically: `target` is the Nth claim (in document
    # extraction order) that cites this exact provision, and — because the
    # scope-violation check above already guarantees every OTHER claim's
    # text reappears verbatim, in the same order, in the corrected text —
    # the Nth same-citation claim re-extracted from the corrected text is
    # the same claim slot, whether or not the corrector actually changed
    # anything in it.
    target_identity = _citation_identity(target["citation_extracted"])
    target_ordinal = None
    if target_identity is not None:
        same_identity_baseline = [
            rec for rec in baseline["claims"]
            if _citation_identity(rec["citation_extracted"]) == target_identity
        ]
        target_ordinal = next(i for i, rec in enumerate(same_identity_baseline) if rec is target)

    replacement = None
    if target_identity is not None:
        same_identity_reextracted = [
            c for c in reverify_claims if _citation_identity(c.citation_extracted) == target_identity
        ]
        if target_ordinal < len(same_identity_reextracted):
            replacement = same_identity_reextracted[target_ordinal]

    # Ordinal-position integrity check. The ordinal-matching scheme above
    # relies on an invariant _scope_violation() does NOT actually enforce:
    # that same-citation-identity siblings keep their RELATIVE ORDER in the
    # corrected text, not just their presence somewhere in it. If the
    # corrector's output reorders two same-identity claims (e.g. moves the
    # newly-corrected sentence ahead of an unflagged sibling that shares its
    # citation), every unflagged claim's exact text still appears — the
    # scope check passes — but "the Nth same-identity claim in reading
    # order" no longer denotes the same claim slot it did in the baseline.
    # `replacement` can then silently BE an untouched sibling's own original
    # sentence, re-verified as if it were the actual edit: this would ship
    # `status="corrected"` carrying a genuine-looking ENTAILED confirmation
    # that was never computed against the real correction at all — a
    # fabricated safety confirmation, worse than any honest rejection.
    #
    # Detected here by a direct, checkable signal: if what ordinal-matching
    # selected as "the replacement" is BYTE-IDENTICAL to some OTHER
    # same-identity claim's own ORIGINAL (baseline) text, the ordinal slot
    # cannot be trusted — a genuine correction of the flagged claim does
    # not, except by a bizarre coincidence, reproduce a completely
    # different sibling claim's own original sentence verbatim. Fails
    # closed (new, distinct status — never silently reclassified as
    # "corrected" or "correction_failed", since neither means what actually
    # happened here) rather than trust the ordinal lookup further.
    if replacement is not None and target_identity is not None:
        other_original_texts = {
            rec["claim_text"] for rec in same_identity_baseline
            if rec["claim_id"] != target["claim_id"]
        }
        if replacement.claim_text in other_original_texts:
            return {
                "triggered_for_claim_id": target["claim_id"],
                "attempts": 1,
                "status": "correction_ordinal_ambiguous",
                "regenerated_text": corrected_text,
                "original_field_text": original_field_text,
                "reverification": None,
                "corr_meta": corr_meta_dict,
            }

    reverification = None
    status = "correction_failed"
    if replacement is not None:
        match = match_evidence(
            replacement.citation_extracted,
            baseline["_exact_index"],
            baseline["_all_usable"],
            config["evidence_matching"]["fuzzy_token_overlap_threshold"],
        )
        if match.matched:
            # Re-verification must use the SAME premise framing as the original
            # verdict. Verifying under one framing and re-verifying under
            # another would compare a correction against a different standard
            # than the one that flagged it.
            #
            # `narrow_reverification_hypothesis` (opt-in, default False):
            # when True, and the re-extracted replacement claim has its own
            # narrower `assertion_text` (a verbatim, non-fabricated
            # per-citation clause/gloss — see claim_parser.py), verify THAT
            # instead of the full `claim_text`. On a bundled sentence, the
            # full sentence dilutes the hypothesis with sibling citations'
            # unrelated content, which can keep a genuinely correct,
            # narrowly-targeted fix from reaching ENTAILED even though it
            # is accurate — see outputs/research_completion_report.md §16a
            # for a real, measured example (0.54 NEI on the full sentence
            # vs 0.999 ENTAILED on the narrow fragment, same evidence, same
            # corrected text). This never widens what is accepted as
            # evidence-consistent — assertion_text is always a genuine
            # substring of the model's own corrected output, never
            # synthesized — it only asks a more precisely-targeted
            # question about the SAME text.
            narrow_reverification = bool((config.get("correction") or {}).get(
                "narrow_reverification_hypothesis", False
            ))
            reverify_hypothesis = replacement.claim_text
            if narrow_reverification and replacement.assertion_text != replacement.claim_text:
                reverify_hypothesis = replacement.assertion_text

            result = baseline["_verifier"].verify(
                premise=format_premise(
                    match.evidence.canonical_text,
                    framing=resolve_premise_framing(config),
                    provision_type=match.evidence.provision_type,
                    provision_number=match.evidence.provision_number,
                    act=match.evidence.act,
                ),
                hypothesis=reverify_hypothesis,
            )
            reverification = {
                "claim_text": replacement.claim_text,
                "reverified_hypothesis": reverify_hypothesis,
                "evidence_id": match.evidence.dataset_citation_key,
                "evidence_match_method": match.match_method,
                "verdict": result.label,
                "confidence": result.confidence,
                "sub_reason": result.sub_reason,
                "raw_scores": result.raw_scores,  # see generate_and_parse's raw_scores comment
                "input_truncated": result.input_truncated,
            }
            if result.label == ENTAILED:
                status = "corrected"
        else:
            reverification = {
                "claim_text": replacement.claim_text,
                "evidence_id": None,
                "evidence_match_method": match.match_method,
                "verdict": NO_EVIDENCE,
                "confidence": None,
                "sub_reason": None,
                "raw_scores": None,
                "input_truncated": None,
            }

    # Independent sibling-regression safety net (opt-in, only meaningful
    # when the scope check itself was relaxed below full-sentence
    # byte-for-byte preservation — see _reverify_sibling_regressions()).
    # Runs ONLY when the correction otherwise would ship, and can only ever
    # turn a "corrected" into a rejection, never the reverse.
    sibling_regressions: list[dict] = []
    if status == "corrected" and (use_assertion_text or use_assertion_spans):
        sibling_regressions = _reverify_sibling_regressions(
            baseline, corrected_text, target["claim_id"], config
        )
        if sibling_regressions:
            status = "correction_sibling_regression"

    return {
        "triggered_for_claim_id": target["claim_id"],
        "attempts": 1,
        "status": status,
        "regenerated_text": corrected_text,
        "original_field_text": original_field_text,
        "reverification": reverification,
        "sibling_regressions": sibling_regressions,
        # NOT underscore-prefixed: run_case()'s underscore-strip is for
        # internal bookkeeping (e.g. baseline["_exact_index"]) only. This is
        # genuine reproducibility data and must survive into the output
        # record's "correction" block.
        "corr_meta": corr_meta_dict,
    }


def _correction_target_spans(rec: dict) -> Optional[tuple[list[str], str]]:
    """Resolves a flagged claim's `assertion_spans` into (spans,
    content_fragment) for ASSERTION-AWARE correction, or None (fail closed)
    if the representation is missing or malformed.

    `spans` is the claim's full `assertion_spans` list, falling back safely
    to `[assertion_text or claim_text]` for any caller/claim predating this
    field (same fallback convention as `_scope_violation`'s
    `use_assertion_spans` path). `content_fragment` is ALWAYS `spans[-1]`:

      - For an ordinary claim (the overwhelming majority — any claim not
        produced by a "respectively" sentence), `assertion_spans` is a
        1-element list equal to `[assertion_text]` (claim_parser.py's
        `Claim.__post_init__` default, re-synced by `_assign_assertion_texts`
        after narrowing) — so `spans[-1] == assertion_text`, identical to
        this mechanism's original (pre-2026-09-12-continuation) behavior.
      - For a "respectively" claim with a genuine 2-element
        `assertion_spans` (`claim_parser.py`'s `_assign_respectively_spans`
        constructs it as exactly `[bare_number_span, description_item]`,
        in that order — verified directly against that function's source),
        `spans[-1]` is the description item: the actual legal content this
        claim asserts. `spans[0]` (the bare number) is a citation
        IDENTIFIER, not correctable content — this pipeline already treats
        any citation-identity change as `correction_unauthorized_addition`
        elsewhere, so correcting the number itself is never in scope here;
        the caller is responsible for verifying `spans[:-1]` (any
        structural/identifier elements) survive the edit unchanged (see
        `apply_selective_correction_assertion_aware`'s structural-span
        check) — this function only resolves WHAT to correct, not whether
        the surrounding structure survived.

    Fails closed (returns None) if `spans` is empty or any element is
    falsy/empty — a malformed representation must never be guessed at."""
    spans = rec.get("assertion_spans") or [rec.get("assertion_text") or rec.get("claim_text")]
    if not spans or any(not s for s in spans):
        return None
    return spans, spans[-1]


def apply_selective_correction_assertion_aware(baseline: dict, case, corrector, config: dict) -> dict:
    """ASSERTION-AWARE correction (added 2026-09-12; extended 2026-09-12
    continuation to consume the full parser-produced `assertion_spans`
    representation, not just `assertion_text` — see `_correction_target_spans`).
    Config-gated via correction.assertion_aware, default False — see
    apply_selective_correction() above for the still-default LEGACY
    whole-paragraph-regeneration path, preserved unmodified for controlled
    ablation comparison, per this project's explicit rule to never delete a
    still-relevant correction mechanism.

    Instead of asking the LLM to regenerate the entire paragraph and then
    CHECKING afterward that every unflagged sentence survived byte-for-byte,
    this path asks the LLM to rewrite ONLY the flagged claim's own CONTENT
    fragment — `assertion_spans[-1]`, a verbatim, non-fabricated sub-span of
    `claim_text` (claim_parser.py's `_assign_assertion_texts` /
    `_assign_respectively_spans`) — and SPLICES that fragment back via
    deterministic, exact-substring Python string replacement
    (`_splice_assertion_correction` — no LLM involved in the splice itself).
    Every character of the paragraph outside the replaced span is therefore
    GUARANTEED byte-identical to the original by construction, not merely
    verified after the fact. For a multi-element `assertion_spans` (the
    "respectively" pattern), the STRUCTURAL elements (`spans[:-1]` — e.g.
    the citation's own bare provision number) are additionally verified to
    survive the edit unchanged (see the dedicated check below) — a genuinely
    new safety property the earlier `assertion_text`-only version of this
    function could not express, because it never saw the structural element
    at all.

    This directly targets a real, documented failure mode: document
    `1955_32` (see outputs/16gb_final_execution_report.md), where Qwen
    produced a substantively CORRECT fix (a hallucinated "fourteen years"
    corrected to the real statute's "ten years") under the legacy path in
    BOTH ablation arms, but the fix was rejected — once by the scope check,
    once by the independent sibling-regression check — purely because the
    corrector's own whole-sentence regeneration did not reproduce an
    unrelated sibling clause byte-for-byte. A splice-based edit to just the
    "fourteen years" -> "ten years" span structurally cannot disturb that
    sibling clause at all. (A real n=10 natural-data replay of this exact
    mechanism, `outputs/assertion_aware_correction_experiment_report.md`,
    found the splice DOES work exactly as designed on this case — but it
    still did not ship, because the untouched sibling in that specific
    sentence was ALSO independently wrong, a separate error this mechanism
    was never meant to fix. See that report for the full, honest analysis.)

    Still runs the SAME defensive safety-gate chain as the legacy path
    (scope check, unauthorized-citation-injection check, ordinal-integrity
    check, re-verification, sibling-regression check) — the splice's
    structural guarantee is not treated as a substitute for verifying it,
    matching this project's "a prompt/invariant is not an enforcement
    mechanism" convention. The sibling-regression check in particular is
    run UNCONDITIONALLY here (unlike the legacy path, which only runs it
    when the scope check was itself relaxed) precisely because "this should
    be safe by construction" is exactly the kind of claim this project's
    own convention says to verify, not trust.

    Fails closed with status `correction_span_invalid` when the claim's
    `assertion_spans` representation is missing/malformed,
    `correction_splice_unavailable` when the splice cannot be performed
    unambiguously (see `_splice_assertion_correction`'s docstring), and
    `correction_structural_span_lost` when a multi-element claim's
    structural (non-content) span(s) do not survive the edit."""
    flagged = [
        rec for rec in baseline["claims"]
        if _should_trigger_correction(rec) and not rec.get("negation_contradiction_caveat")
    ]
    original_field_text = baseline["generated_field"]["text"]
    if not flagged:
        return {
            "triggered_for_claim_id": None,
            "attempts": 0,
            "status": "not_triggered",
            "regenerated_text": None,
            "original_field_text": original_field_text,
            "reverification": None,
            "correction_mode": "assertion_aware",
        }

    target = flagged[0]
    resolved = _correction_target_spans(target)
    if resolved is None:
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 0,
            "status": "correction_span_invalid",
            "regenerated_text": None,
            "original_field_text": original_field_text,
            "reverification": None,
            "correction_mode": "assertion_aware",
        }
    target_spans, target_content_fragment = resolved
    structural_spans = target_spans[:-1]  # e.g. a "respectively" claim's own bare number; [] for ordinary claims

    corr_config = config.get("correction") or {}
    assertion_span_prompt = corr_config.get(
        "assertion_span_system_prompt", _DEFAULT_ASSERTION_SPAN_SYSTEM_PROMPT
    )
    assertion_span_max_new_tokens = int(corr_config.get("assertion_span_max_new_tokens", 60))

    corrected_fragment, corr_meta = corrector.correct_assertion_span(
        case_text=case.case_text,
        target_span=target_content_fragment,
        evidence_text=target["evidence_text"],
        assertion_span_system_prompt=assertion_span_prompt,
        max_new_tokens=assertion_span_max_new_tokens,
    )
    corr_meta_dict = {
        "model": corr_meta.model_id,
        "max_new_tokens": corr_meta.max_new_tokens,
        "do_sample": corr_meta.do_sample,
        "seed": corr_meta.seed,
        "corrected_at": corr_meta.corrected_at,
    }

    corrected_text = _splice_assertion_correction(
        original_field_text, target["claim_text"], target_content_fragment, corrected_fragment,
    )
    if corrected_text is None:
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 1,
            "status": "correction_splice_unavailable",
            "regenerated_text": corrected_fragment,
            "original_field_text": original_field_text,
            "reverification": None,
            "corr_meta": corr_meta_dict,
            "correction_mode": "assertion_aware",
            "target_assertion_spans": target_spans,
            "target_content_fragment": target_content_fragment,
        }

    # Structural-span preservation check — NEW, only meaningful for a
    # multi-element assertion_spans (the "respectively" pattern): the
    # citation's own bare number (or any other non-content element) must
    # survive the edit unchanged, word-boundary-safe (see _fragment_present's
    # own docstring for why plain `in` containment is unsafe here — the
    # same "34" vs "134" gap that motivated that helper applies equally to
    # a structural span). For an ordinary (1-element) claim, structural_spans
    # is empty and this check trivially passes -- no behavior change there.
    if structural_spans and not all(_fragment_present(s, corrected_text) for s in structural_spans):
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 1,
            "status": "correction_structural_span_lost",
            "regenerated_text": corrected_text,
            "original_field_text": original_field_text,
            "reverification": None,
            "corr_meta": corr_meta_dict,
            "correction_mode": "assertion_aware",
            "target_assertion_spans": target_spans,
            "target_content_fragment": target_content_fragment,
            "corrected_fragment": corrected_fragment,
        }

    # Defensive scope check — see this function's docstring: the splice
    # already guarantees this structurally, but this is the actual
    # enforcement mechanism, not the construction alone.
    atomic_scope_check_mode = corr_config.get("atomic_scope_check", False)
    use_assertion_text = bool(atomic_scope_check_mode)
    use_assertion_spans = atomic_scope_check_mode == "assertion_spans"
    if _scope_violation(
        baseline["claims"], target["claim_id"], corrected_text,
        use_assertion_text, use_assertion_spans,
    ):
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 1,
            "status": "correction_scope_violation",
            "regenerated_text": corrected_text,
            "original_field_text": original_field_text,
            "reverification": None,
            "corr_meta": corr_meta_dict,
            "correction_mode": "assertion_aware",
            "target_assertion_spans": target_spans,
            "target_content_fragment": target_content_fragment,
            "corrected_fragment": corrected_fragment,
        }

    # Unauthorized-content-injection check — same rationale as the legacy
    # path (see apply_selective_correction): the scope check above only
    # verifies existing unflagged claims survive; it does not forbid a NEW
    # hallucinated citation appearing inside the corrected fragment itself.
    reverify_claims = claim_parser.extract_claims(corrected_text)
    baseline_identities = {
        _citation_identity(rec["citation_extracted"]) for rec in baseline["claims"]
    }
    baseline_identities.discard(None)
    if any(
        _citation_identity(c.citation_extracted) is not None
        and _citation_identity(c.citation_extracted) not in baseline_identities
        for c in reverify_claims
    ):
        return {
            "triggered_for_claim_id": target["claim_id"],
            "attempts": 1,
            "status": "correction_unauthorized_addition",
            "regenerated_text": corrected_text,
            "original_field_text": original_field_text,
            "reverification": None,
            "corr_meta": corr_meta_dict,
            "correction_mode": "assertion_aware",
            "target_assertion_spans": target_spans,
            "target_content_fragment": target_content_fragment,
            "corrected_fragment": corrected_fragment,
        }

    # Ordinal-position matching + integrity check — identical technique to
    # apply_selective_correction (see its comments for the full rationale).
    target_identity = _citation_identity(target["citation_extracted"])
    target_ordinal = None
    same_identity_baseline: list[dict] = []
    if target_identity is not None:
        same_identity_baseline = [
            rec for rec in baseline["claims"]
            if _citation_identity(rec["citation_extracted"]) == target_identity
        ]
        target_ordinal = next(i for i, rec in enumerate(same_identity_baseline) if rec is target)

    replacement = None
    if target_identity is not None:
        same_identity_reextracted = [
            c for c in reverify_claims if _citation_identity(c.citation_extracted) == target_identity
        ]
        if target_ordinal < len(same_identity_reextracted):
            replacement = same_identity_reextracted[target_ordinal]

    if replacement is not None and target_identity is not None:
        other_original_texts = {
            rec["claim_text"] for rec in same_identity_baseline
            if rec["claim_id"] != target["claim_id"]
        }
        if replacement.claim_text in other_original_texts:
            return {
                "triggered_for_claim_id": target["claim_id"],
                "attempts": 1,
                "status": "correction_ordinal_ambiguous",
                "regenerated_text": corrected_text,
                "original_field_text": original_field_text,
                "reverification": None,
                "corr_meta": corr_meta_dict,
                "correction_mode": "assertion_aware",
                "target_assertion_spans": target_spans,
                "target_content_fragment": target_content_fragment,
                "corrected_fragment": corrected_fragment,
            }

    reverification = None
    status = "correction_failed"
    if replacement is not None:
        match = match_evidence(
            replacement.citation_extracted,
            baseline["_exact_index"],
            baseline["_all_usable"],
            config["evidence_matching"]["fuzzy_token_overlap_threshold"],
        )
        if match.matched:
            narrow_reverification = bool(corr_config.get("narrow_reverification_hypothesis", False))
            reverify_hypothesis = replacement.claim_text
            if narrow_reverification and replacement.assertion_text != replacement.claim_text:
                reverify_hypothesis = replacement.assertion_text

            result = baseline["_verifier"].verify(
                premise=format_premise(
                    match.evidence.canonical_text,
                    framing=resolve_premise_framing(config),
                    provision_type=match.evidence.provision_type,
                    provision_number=match.evidence.provision_number,
                    act=match.evidence.act,
                ),
                hypothesis=reverify_hypothesis,
            )
            reverification = {
                "claim_text": replacement.claim_text,
                "reverified_hypothesis": reverify_hypothesis,
                "evidence_id": match.evidence.dataset_citation_key,
                "evidence_match_method": match.match_method,
                "verdict": result.label,
                "confidence": result.confidence,
                "sub_reason": result.sub_reason,
                "raw_scores": result.raw_scores,
                "input_truncated": result.input_truncated,
            }
            if result.label == ENTAILED:
                status = "corrected"
        else:
            reverification = {
                "claim_text": replacement.claim_text,
                "evidence_id": None,
                "evidence_match_method": match.match_method,
                "verdict": NO_EVIDENCE,
                "confidence": None,
                "sub_reason": None,
                "raw_scores": None,
                "input_truncated": None,
            }

    # Independent sibling-regression safety net — run UNCONDITIONALLY here
    # (see this function's docstring for why, unlike the legacy path).
    sibling_regressions: list[dict] = []
    if status == "corrected":
        sibling_regressions = _reverify_sibling_regressions(
            baseline, corrected_text, target["claim_id"], config
        )
        if sibling_regressions:
            status = "correction_sibling_regression"

    return {
        "triggered_for_claim_id": target["claim_id"],
        "attempts": 1,
        "status": status,
        "regenerated_text": corrected_text,
        "original_field_text": original_field_text,
        "reverification": reverification,
        "sibling_regressions": sibling_regressions,
        "corr_meta": corr_meta_dict,
        "correction_mode": "assertion_aware",
        "target_assertion_spans": target_spans,
        "target_content_fragment": target_content_fragment,
        "corrected_fragment": corrected_fragment,
    }


def _summarize_evidence(claims: list[dict], usable_pool_size: int) -> dict:
    with_evidence = sum(1 for c in claims if c["evidence_text"] is not None)
    return {
        "total_claims": len(claims),
        "claims_with_evidence": with_evidence,
        "claims_no_evidence": len(claims) - with_evidence,
        "usable_evidence_pool_size": usable_pool_size,
    }


def _summarize_verification(claims: list[dict], mode: str, verifier_model: Optional[str], threshold: float) -> dict:
    counts = {ENTAILED: 0, CONTRADICTED: 0, NOT_ENOUGH_INFORMATION: 0, NO_EVIDENCE: 0}
    for c in claims:
        if c["verdict"] in counts:
            counts[c["verdict"]] += 1
    return {
        "mode": mode,
        "verifier_model": verifier_model if mode in ("B", "C") else None,
        "confidence_threshold": threshold if mode in ("B", "C") else None,
        "counts": counts,
        "disclaimer": (
            "Verdicts reflect a small public NLI model's statistical confidence "
            "against a 59-record, third-party-sourced evidence corpus. Not a "
            "legal-correctness determination; verifier accuracy is not yet "
            "established (no gold evaluation has been run)."
        ),
    }


def run_case(
    case,
    mode: str,
    generator,
    verifier,
    corrector,
    exact_index: dict,
    all_usable: list,
    config: dict,
) -> dict:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    baseline = generate_and_parse(
        case, generator, exact_index, all_usable,
        config["evidence_matching"]["fuzzy_token_overlap_threshold"],
    )
    baseline["_exact_index"] = exact_index
    baseline["_all_usable"] = all_usable
    baseline["_verifier"] = verifier

    if mode in ("B", "C"):
        narrow_primary = bool((config.get("verification") or {}).get("narrow_primary_hypothesis", False))
        span_primary = bool((config.get("verification") or {}).get("assertion_span_primary_hypothesis", False))
        apply_verification(baseline, verifier, resolve_premise_framing(config), narrow_primary, span_primary)

    correction_summary = {
        "triggered_for_claim_id": None,
        "attempts": 0,
        "status": "not_applicable_mode_" + mode,
        "regenerated_text": None,
        "original_field_text": baseline["generated_field"]["text"],
        "reverification": None,
    }
    final_field = {"text": baseline["generated_field"]["text"], "source": "original"}

    if mode == "C":
        assertion_aware_correction = bool((config.get("correction") or {}).get("assertion_aware", False))
        if assertion_aware_correction:
            correction_summary = apply_selective_correction_assertion_aware(baseline, case, corrector, config)
        else:
            correction_summary = apply_selective_correction(baseline, case, corrector, config)
        if correction_summary["status"] == "corrected":
            final_field = {"text": correction_summary["regenerated_text"], "source": "corrected"}
        elif correction_summary["status"] == "correction_failed":
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_failed"}
        elif correction_summary["status"] == "correction_scope_violation":
            # Never ship a correction that touched unflagged sentences —
            # both texts are retained in correction_summary for inspection,
            # but the shipped field falls back to the original.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_scope_violation"}
        elif correction_summary["status"] == "correction_sibling_regression":
            # The target's own re-verification passed, but an independent
            # re-check found a sibling claim's counterpart in the corrected
            # text now genuinely CONTRADICTED its own evidence — a regression
            # the (opt-in, relaxed) scope check alone would have missed.
            # Never ship; both texts retained in correction_summary for
            # inspection, same as scope_violation.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_sibling_regression"}
        elif correction_summary["status"] == "correction_ordinal_ambiguous":
            # The ordinal-position replacement lookup could not trust which
            # re-extracted claim was actually the correction (see
            # apply_selective_correction's ordinal-integrity check) — never
            # ship a "confirmation" that may have been computed against the
            # wrong (untouched) sibling's text instead of the real edit.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_ordinal_ambiguous"}
        elif correction_summary["status"] == "correction_unauthorized_addition":
            # The corrected text contains a citation identity with no
            # counterpart anywhere in the original field — either a brand
            # new, hallucinated citation introduced alongside the flagged
            # claim's own fix, or the flagged claim's own citation swapped
            # for a different provision instead of being fixed. Never ship
            # either way; both texts retained in correction_summary for
            # inspection.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_unauthorized_addition"}
        elif correction_summary["status"] == "correction_splice_unavailable":
            # ASSERTION-AWARE mode only: the deterministic splice could not
            # be performed unambiguously (see _splice_assertion_correction).
            # Never ship a text this pipeline did not itself construct
            # unambiguously; both the flagged fragment and the corrector's
            # raw output are retained in correction_summary for inspection.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_splice_unavailable"}
        elif correction_summary["status"] == "correction_span_invalid":
            # ASSERTION-AWARE mode only: the flagged claim's assertion_spans
            # representation was missing/malformed (see
            # _correction_target_spans) — never guess at what to correct.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_span_invalid"}
        elif correction_summary["status"] == "correction_structural_span_lost":
            # ASSERTION-AWARE mode only, multi-element assertion_spans (the
            # "respectively" pattern): a structural (non-content) span —
            # e.g. the citation's own bare provision number — did not
            # survive the edit. Never ship a correction that silently drops
            # part of the citation's own identity.
            final_field = {"text": baseline["generated_field"]["text"], "source": "correction_structural_span_lost"}
        # "not_triggered": final_field stays as original (already set above)

    verifier_model_id = getattr(verifier, "model_id", None) if verifier is not None else None

    record = {
        "document_id": baseline["document_id"],
        "case_text": baseline["case_text"],
        "generated_field": baseline["generated_field"],
        "claims": [
            {k: v for k, v in c.items() if not k.startswith("_")}
            for c in baseline["claims"]
        ],
        "evidence": _summarize_evidence(baseline["claims"], len(all_usable)),
        "verification": _summarize_verification(
            baseline["claims"], mode, verifier_model_id,
            config["verification"]["confidence_threshold"],
        ),
        "correction": {k: v for k, v in correction_summary.items() if not k.startswith("_")},
        "final_field": final_field,
        "reproducibility": {
            "mode": mode,
            "seed": config["seed"],
            "generation_model": config["generation"]["model_id"],
            "verification_model": config["verification"]["model_id"] if mode in ("B", "C") else None,
            "quantization": config["generation"]["quantization"],
            "confidence_threshold": config["verification"]["confidence_threshold"],
            # Which premise framing produced these verdicts. Without this a run
            # cannot be attributed to a framing after the fact, and the bare vs
            # labeled ablation becomes uninterpretable.
            "premise_framing": resolve_premise_framing(config) if mode in ("B", "C") else None,
            # Additive: the other three config-level ablation knobs this
            # project already treats as baseline/treatment pairs (see
            # FINAL_PRODUCTION_CONFIG.md), recorded the same way
            # premise_framing already was. Without these, a future ablation
            # reading only a committed output record — without also
            # archiving the exact config.yaml used for that specific run —
            # could not attribute a given `evidence.usable_evidence_pool_size`
            # or `correction.status` (e.g. a `correction_scope_violation` or
            # `correction_ordinal_ambiguous`) to which scope-check mode or
            # evidence pool actually produced it.
            "use_evidence_v1": bool(config.get("use_evidence_v1", False)),
            "atomic_scope_check": (config.get("correction") or {}).get("atomic_scope_check", False) if mode == "C" else None,
            "narrow_reverification_hypothesis": bool((config.get("correction") or {}).get(
                "narrow_reverification_hypothesis", False
            )) if mode == "C" else None,
            "narrow_primary_hypothesis": bool((config.get("verification") or {}).get(
                "narrow_primary_hypothesis", False
            )) if mode in ("B", "C") else None,
            "assertion_span_primary_hypothesis": bool((config.get("verification") or {}).get(
                "assertion_span_primary_hypothesis", False
            )) if mode in ("B", "C") else None,
            "assertion_aware_correction": bool((config.get("correction") or {}).get(
                "assertion_aware", False
            )) if mode == "C" else None,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "software_versions": _software_versions(),
        },
    }
    return record
