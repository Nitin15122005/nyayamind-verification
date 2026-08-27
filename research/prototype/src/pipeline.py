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
import sys
from typing import Optional

from . import claim_parser
from .evidence_matcher import match_evidence, NO_EVIDENCE
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


def _should_trigger_correction(claim_record: dict) -> bool:
    """Per the approved design: trigger for CONTRADICTED (regardless of
    confidence), or for NOT_ENOUGH_INFORMATION specifically when it's the
    low-confidence downgrade (sub_reason == "low_confidence") — NOT for a
    genuine high-confidence "neutral" NLI prediction, which is a legitimate
    NEI verdict on its own, not a flagged failure. NO_EVIDENCE never
    triggers, regardless of this function (callers only pass claims that
    already have evidence)."""
    verdict = claim_record["verdict"]
    if verdict == CONTRADICTED:
        return True
    if verdict == NOT_ENOUGH_INFORMATION and claim_record.get("sub_reason") == "low_confidence":
        return True
    return False


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
                "verdict": None,          # filled by apply_verification (mode B/C)
                "confidence": None,
                "sub_reason": None,
                "verifier_model": None,
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


def apply_verification(baseline: dict, verifier, premise_framing: str = PREMISE_FRAMING_BARE) -> None:
    """Mutates baseline['claims'] in place, filling verdict/confidence for
    every claim that has matched evidence. Claims with no evidence keep
    their NO_EVIDENCE verdict untouched — the verifier is never called for
    them, by design (an NLI verdict would be meaningless without a
    premise).

    `premise_framing` defaults to bare so that any caller not yet passing it
    keeps the exact behaviour that produced the committed outputs; callers opt
    into the ablation by threading resolve_premise_framing(config) through.
    """
    if premise_framing not in PREMISE_FRAMINGS:
        raise ValueError(
            f"premise_framing must be one of {list(PREMISE_FRAMINGS)}, got {premise_framing!r}"
        )
    for rec in baseline["claims"]:
        if rec["evidence_text"] is None:
            continue  # already NO_EVIDENCE, verifier not invoked
        result = verifier.verify(
            premise=_premise_for_claim(rec, premise_framing), hypothesis=rec["claim_text"]
        )
        rec["verdict"] = result.label
        rec["confidence"] = result.confidence
        rec["sub_reason"] = result.sub_reason
        rec["verifier_model"] = result.verifier_model


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
            if not all(f and f in corrected_text for f in fragments):
                return True
            continue
        check_text = rec.get("claim_text")
        if use_assertion_text:
            check_text = rec.get("assertion_text") or check_text
        if check_text not in corrected_text:
            return True
    return False


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
    correction that the scope check alone would have allowed."""
    regressions = []
    reverify_claims = claim_parser.extract_claims(corrected_text)
    for rec in baseline["claims"]:
        if rec["claim_id"] == target_claim_id:
            continue
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
    texts are retained in the output for inspection."""
    flagged = [rec for rec in baseline["claims"] if _should_trigger_correction(rec)]
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

    reverify_claims = claim_parser.extract_claims(corrected_text)
    replacement = None
    if target_identity is not None:
        same_identity_reextracted = [
            c for c in reverify_claims if _citation_identity(c.citation_extracted) == target_identity
        ]
        if target_ordinal < len(same_identity_reextracted):
            replacement = same_identity_reextracted[target_ordinal]

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
        apply_verification(baseline, verifier, resolve_premise_framing(config))

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
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "software_versions": _software_versions(),
        },
    }
    return record
