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
from .verifier import ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION

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
                "citation_extracted": claim.citation_extracted.as_dict()
                if claim.citation_extracted
                else None,
                "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
                "evidence_text": match.evidence.canonical_text if match.matched else None,
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


def apply_verification(baseline: dict, verifier) -> None:
    """Mutates baseline['claims'] in place, filling verdict/confidence for
    every claim that has matched evidence. Claims with no evidence keep
    their NO_EVIDENCE verdict untouched — the verifier is never called for
    them, by design (an NLI verdict would be meaningless without a
    premise)."""
    for rec in baseline["claims"]:
        if rec["evidence_text"] is None:
            continue  # already NO_EVIDENCE, verifier not invoked
        result = verifier.verify(premise=rec["evidence_text"], hypothesis=rec["claim_text"])
        rec["verdict"] = result.label
        rec["confidence"] = result.confidence
        rec["sub_reason"] = result.sub_reason
        rec["verifier_model"] = result.verifier_model


def _scope_violation(baseline_claims: list[dict], target_claim_id: str, corrected_text: str) -> bool:
    """Programmatic enforcement of selective correction's contract: every
    UNFLAGGED claim (a citation-bearing sentence extracted from the
    original field, other than the one being corrected) must reappear
    verbatim in the corrected text. The correction prompt already asks the
    model for this ("copy verbatim/unchanged"), but a prompt is not an
    enforcement mechanism — this is the actual gate. Returns True
    (violation) if any unflagged claim's exact original sentence text is
    no longer present in the corrected text.

    Deliberately claim-scoped, not whole-paragraph-sentence-scoped: the
    corrector is only constrained w.r.t. the claims this pipeline already
    tracks. Non-claim prose or newly introduced sentences elsewhere in the
    paragraph are outside what "unflagged claims must remain unchanged"
    covers here."""
    for rec in baseline_claims:
        if rec["claim_id"] == target_claim_id:
            continue
        if rec["claim_text"] not in corrected_text:
            return True
    return False


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

    if _scope_violation(baseline["claims"], target["claim_id"], corrected_text):
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
    reverify_claims = claim_parser.extract_claims(corrected_text)
    orig_citation = target["citation_extracted"]
    replacement = None
    for c in reverify_claims:
        if c.citation_extracted is None or orig_citation is None:
            continue
        if (
            c.citation_extracted.provision_type == orig_citation["provision_type"]
            and c.citation_extracted.provision_number == orig_citation["provision_number"]
            and c.citation_extracted.act_norm == orig_citation["act_norm"]
        ):
            replacement = c
            break

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
            result = baseline["_verifier"].verify(
                premise=match.evidence.canonical_text, hypothesis=replacement.claim_text
            )
            reverification = {
                "claim_text": replacement.claim_text,
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

    return {
        "triggered_for_claim_id": target["claim_id"],
        "attempts": 1,
        "status": status,
        "regenerated_text": corrected_text,
        "original_field_text": original_field_text,
        "reverification": reverification,
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
        apply_verification(baseline, verifier)

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
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "software_versions": _software_versions(),
        },
    }
    return record
