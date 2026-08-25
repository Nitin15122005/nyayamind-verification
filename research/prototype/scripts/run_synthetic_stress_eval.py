#!/usr/bin/env python
"""
Run synthetic contradiction stress test over the 59 canonical statutes.
Evaluates detection recall, false positives, correction trigger rate,
real Qwen correction success rate, and safety scope enforcement.
Outputs: outputs/run_synthetic_stress.jsonl
"""
from __future__ import annotations

import copy
import datetime
import json
import sys
import time
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml
from src.data_loader import load_usable_evidence, Case
from src.synthetic_stress import build_synthetic_stress_claims, SYNTHETIC_STRESS_TEST
from src.generator import StatuteGroundingGenerator
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.evidence_matcher import match_evidence, NO_EVIDENCE
from src.corrector import SelectiveCorrector
from src import pipeline, claim_parser


def run_synthetic_case(synth_claim, generator, verifier, corrector, exact_index, all_usable, config):
    # Construct a synthetic case environment for this claim
    case_id = f"synth_{synth_claim.claim_id}_{synth_claim.provision_number}"
    case_text = (
        f"Synthetic Stress Case for {synth_claim.act_raw} {synth_claim.provision_type} "
        f"{synth_claim.provision_number}. Case involves statutory compliance."
    )
    case_obj = Case(document_id=case_id, case_text=case_text, raw_citation_keys=[])

    # Construct the original synthetic paragraph (incorporating the synthetic claim)
    # To test scope violation protection, we include a second, valid unflagged claim
    unflagged_sentence = "Article 14 of the Constitution of India guarantees equality before the law."
    full_paragraph = f"{synth_claim.claim_text} {unflagged_sentence}"

    # Parse claims from paragraph
    extracted_claims = claim_parser.extract_claims(full_paragraph)

    claim_records = []
    for c in extracted_claims:
        citation_dict = c.citation_extracted.as_dict() if c.citation_extracted else None
        match = (
            match_evidence(c.citation_extracted, exact_index, all_usable, config["evidence_matching"]["fuzzy_token_overlap_threshold"])
            if c.citation_extracted
            else match_evidence(claim_parser.ExtractedCitation("", "", None, None, ""), exact_index, all_usable)
        )
        claim_records.append({
            "claim_id": c.claim_id,
            "claim_text": c.claim_text,
            "citation_extracted": citation_dict,
            "evidence_id": match.evidence.dataset_citation_key if match.evidence else None,
            "evidence_text": match.evidence.canonical_text if match.evidence else None,
            "evidence_match_method": match.match_method,
            "verdict": NO_EVIDENCE if not match.matched else NOT_ENOUGH_INFORMATION,
            "confidence": None,
            "sub_reason": None,
            "verifier_model": None,
        })

    baseline = {
        "document_id": case_id,
        "case_text": case_text,
        "generated_field": {
            "text": full_paragraph,
            "model": "SYNTHETIC_STRESS_TEST_TRANSFORMATION",
            "quantization": {},
            "generation_params": {"transform_rule": synth_claim.transform_rule},
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "claims": claim_records,
        "claim_source": SYNTHETIC_STRESS_TEST,
        "_exact_index": exact_index,
        "_all_usable": all_usable,
        "_verifier": verifier,
    }

    # Condition A: Original generated synthetic claim (no verification)
    rec_A = copy.deepcopy(baseline)

    # Condition B: Verification only
    rec_B = copy.deepcopy(baseline)
    pipeline.apply_verification(rec_B, verifier)

    # Condition C: Verification + Selective Correction with Real Qwen
    rec_C = copy.deepcopy(baseline)
    pipeline.apply_verification(rec_C, verifier)
    correction_summary = pipeline.apply_selective_correction(rec_C, case_obj, corrector, config)

    final_field = {"text": rec_C["generated_field"]["text"], "source": "original"}
    if correction_summary["status"] == "corrected":
        final_field = {"text": correction_summary["regenerated_text"], "source": "corrected"}
    elif correction_summary["status"] == "correction_failed":
        final_field = {"text": rec_C["generated_field"]["text"], "source": "correction_failed"}
    elif correction_summary["status"] == "correction_scope_violation":
        final_field = {"text": rec_C["generated_field"]["text"], "source": "correction_scope_violation"}

    verifier_model_id = getattr(verifier, "model_id", None)
    summary_record = {
        "synthetic_claim_id": synth_claim.claim_id,
        "transform_rule": synth_claim.transform_rule,
        "evidence_id": synth_claim.evidence.dataset_citation_key,
        "canonical_evidence_text": synth_claim.evidence.canonical_text,
        "original_synthetic_text": synth_claim.claim_text,
        "condition_A": {
            "text": full_paragraph,
            "claims": rec_A["claims"],
        },
        "condition_B": {
            "text": full_paragraph,
            "claims": rec_B["claims"],
            "verification_summary": pipeline._summarize_verification(
                rec_B["claims"], "B", verifier_model_id, config["verification"]["confidence_threshold"]
            ),
        },
        "condition_C": {
            "final_text": final_field["text"],
            "source": final_field["source"],
            "correction": {k: v for k, v in correction_summary.items() if not k.startswith("_")},
            "claims": rec_C["claims"],
            "verification_summary": pipeline._summarize_verification(
                rec_C["claims"], "C", verifier_model_id, config["verification"]["confidence_threshold"]
            ),
        },
        "reproducibility": {
            "claim_source": SYNTHETIC_STRESS_TEST,
            "seed": config["seed"],
            "generation_model": config["generation"]["model_id"],
            "verification_model": config["verification"]["model_id"],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "software_versions": pipeline._software_versions(),
        },
    }
    return summary_record


def main() -> int:
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    exact_index, all_usable = load_usable_evidence(
        canonical_path, audit_path, set(config["usable_evidence_verdicts"])
    )
    print(f"Loaded {len(all_usable)} usable evidence records.")

    synth_claims = build_synthetic_stress_claims(all_usable)
    print(f"Generated {len(synth_claims)} synthetic stress claims.")

    print(f"Loading generator ({config['generation']['model_id']}, 4-bit, CUDA)...")
    gen = StatuteGroundingGenerator(
        model_id=config["generation"]["model_id"],
        quantization=config["generation"]["quantization"],
        device_map=config["generation"]["device_map"],
        max_new_tokens=config["generation"]["max_new_tokens"],
        do_sample=config["generation"]["do_sample"],
        temperature=config["generation"]["temperature"],
        top_p=config["generation"]["top_p"],
        system_prompt=config["generation"]["system_prompt"],
        user_prompt_template=config["generation"]["user_prompt_template"],
        seed=config["seed"],
    )
    gen.load()

    print(f"Loading verifier ({config['verification']['model_id']})...")
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    verifier.load()

    corrector = SelectiveCorrector(
        generator=gen,
        max_new_tokens=config["correction"]["max_new_tokens"],
        do_sample=config["correction"]["do_sample"],
        system_prompt=config["correction"]["system_prompt"],
    )

    output_dir = _PROTOTYPE_ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "run_synthetic_stress.jsonl"

    results = []
    t_start = time.time()
    with output_path.open("w", encoding="utf-8") as f_out:
        for i, sc in enumerate(synth_claims, start=1):
            print(f"[{i}/{len(synth_claims)}] Processing synthetic claim {sc.claim_id} ({sc.transform_rule})...")
            t0 = time.time()
            rec = run_synthetic_case(sc, gen, verifier, corrector, exact_index, all_usable, config)
            elapsed = time.time() - t0
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f_out.flush()
            results.append(rec)
            status = rec["condition_C"]["correction"]["status"]
            b_verdict = rec["condition_B"]["claims"][0]["verdict"] if rec["condition_B"]["claims"] else "N/A"
            print(f"  Done in {elapsed:.1f}s — Verdict: {b_verdict}, Correction Status: {status}")

    total_time = time.time() - t_start
    print(f"\nWrote {len(results)} synthetic stress evaluation records to {output_path} in {total_time:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
