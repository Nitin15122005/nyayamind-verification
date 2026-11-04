#!/usr/bin/env python
"""Paired natural-data evaluation of legacy vs sequential multi-claim correction.

Each case is generated and initially verified once. Both correction arms receive
independent shallow copies of that exact baseline, so the comparison is paired.
This script is experimental and never changes the production config.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))


def _fork_baseline(baseline: dict) -> dict:
    """Copy mutable per-case state while retaining shared loaded model/index refs."""
    fork = dict(baseline)
    fork["generated_field"] = dict(baseline["generated_field"])
    fork["claims"] = [dict(claim) for claim in baseline["claims"]]
    return fork


def _flagged_claims(baseline: dict) -> list[dict]:
    from src.pipeline import _should_trigger_correction
    return [
        claim for claim in baseline["claims"]
        if _should_trigger_correction(claim)
        and not claim.get("negation_contradiction_caveat")
    ]


def _arm_result(name: str, baseline: dict, correction: dict, config: dict) -> dict:
    from src.pipeline import _rebuild_verified_baseline

    status = correction.get("status")
    original = baseline["generated_field"]["text"]
    candidate = correction.get("regenerated_text")
    if status == "multi_claim_limit_reached":
        candidate = correction.get("candidate_text_rolled_back")

    candidate_audit = None
    if isinstance(candidate, str) and candidate != original:
        refreshed = _rebuild_verified_baseline(baseline, candidate, config)
        candidate_audit = {
            "claim_count": len(refreshed["claims"]),
            "remaining_flagged_claims": len(_flagged_claims(refreshed)),
            "verdict_counts": _verdict_counts(refreshed["claims"]),
        }

    shipped = status == "corrected"
    return {
        "arm": name,
        "status": status,
        "attempts": correction.get("attempts", 0),
        "shipped_candidate": shipped,
        "shipped_text": candidate if shipped else original,
        "candidate_audit": candidate_audit,
        "remaining_flagged_claims_in_shipped_text": (
            candidate_audit["remaining_flagged_claims"]
            if shipped and candidate_audit else len(_flagged_claims(baseline))
        ),
        "correction_summary": {
            key: value for key, value in correction.items()
            if not key.startswith("_")
        },
    }


def _verdict_counts(claims: list[dict]) -> dict:
    counts = {}
    for claim in claims:
        verdict = claim.get("verdict") or "UNSCORED"
        counts[verdict] = counts.get(verdict, 0) + 1
    return counts


def evaluate_case(case, generator, verifier, corrector, exact_index, all_usable, config):
    from src.pipeline import (
        generate_and_parse,
        apply_verification,
        apply_selective_correction,
        apply_multi_claim_correction,
        resolve_premise_framing,
    )

    baseline = generate_and_parse(
        case, generator, exact_index, all_usable,
        config["evidence_matching"]["fuzzy_token_overlap_threshold"],
    )
    baseline["_exact_index"] = exact_index
    baseline["_all_usable"] = all_usable
    baseline["_verifier"] = verifier
    apply_verification(
        baseline,
        verifier,
        resolve_premise_framing(config),
        bool((config.get("verification") or {}).get("narrow_primary_hypothesis", False)),
        bool((config.get("verification") or {}).get("assertion_span_primary_hypothesis", False)),
    )

    initial_flagged = len(_flagged_claims(baseline))
    if initial_flagged < 2:
        return None

    legacy_config = copy.deepcopy(config)
    legacy_config.setdefault("correction", {})["multi_claim_enabled"] = False
    multi_config = copy.deepcopy(config)
    multi_config.setdefault("correction", {})["multi_claim_enabled"] = True
    multi_config["correction"]["assertion_aware"] = False

    legacy_baseline = _fork_baseline(baseline)
    multi_baseline = _fork_baseline(baseline)

    legacy_correction = apply_selective_correction(
        legacy_baseline, case, corrector, legacy_config
    )
    multi_correction = apply_multi_claim_correction(
        multi_baseline, case, corrector, multi_config
    )

    return {
        "document_id": baseline["document_id"],
        "initial_claim_count": len(baseline["claims"]),
        "initial_flagged_claim_count": initial_flagged,
        "initial_verdict_counts": _verdict_counts(baseline["claims"]),
        "initial_generated_text": baseline["generated_field"]["text"],
        "legacy": _arm_result("legacy_single_claim", legacy_baseline, legacy_correction, legacy_config),
        "multi_claim": _arm_result("sequential_multi_claim", multi_baseline, multi_correction, multi_config),
        "pairing": {
            "same_initial_text": (
                legacy_baseline["generated_field"]["text"]
                == multi_baseline["generated_field"]["text"]
                == baseline["generated_field"]["text"]
            ),
            "same_initial_claims": (
                len(legacy_baseline["claims"]) == len(multi_baseline["claims"])
                == len(baseline["claims"])
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-cases", type=int, default=3,
                        help="Number of eligible cases with at least two flagged claims (max 5).")
    parser.add_argument("--max-cases-to-scan", type=int, default=20,
                        help="Maximum evidence-overlap cases to generate while finding eligible cases.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    if not 1 <= args.num_cases <= 5:
        parser.error("--num-cases must be between 1 and 5")
    if args.max_cases_to_scan < args.num_cases:
        parser.error("--max-cases-to-scan must be >= --num-cases")

    import yaml
    from src.data_loader import (
        load_usable_evidence_from_config, load_nyayarag_cases,
        select_cases_with_evidence_overlap,
    )
    from src.generator import StatuteGroundingGenerator
    from src.verifier import NLIVerifier
    from src.corrector import SelectiveCorrector

    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = Path(args.config) if args.config else _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if (config.get("correction") or {}).get("assertion_aware", False):
        parser.error("Paired multi-claim evaluation requires correction.assertion_aware=false")

    exact_index, all_usable = load_usable_evidence_from_config(config, repo_root)
    case_paths = [repo_root / path for path in config["paths"]["nyayarag_case_files"]]
    cases = load_nyayarag_cases(case_paths)
    selected = select_cases_with_evidence_overlap(cases, exact_index, min_overlap=1)
    scan = selected[:args.max_cases_to_scan]

    generator = StatuteGroundingGenerator(
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
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    generator.load()
    verifier.load()
    corrector = SelectiveCorrector(
        generator=generator,
        max_new_tokens=config["correction"]["max_new_tokens"],
        do_sample=config["correction"]["do_sample"],
        system_prompt=config["correction"]["system_prompt"],
    )

    results = []
    scanned = 0
    try:
        for case in scan:
            scanned += 1
            print(f"[{scanned}/{len(scan)}] Evaluating {case.document_id} ...", flush=True)
            result = evaluate_case(
                case, generator, verifier, corrector, exact_index, all_usable, config
            )
            if result is None:
                print("  skipped: fewer than two initially flagged claims", flush=True)
                continue
            results.append(result)
            print(
                f"  legacy={result['legacy']['status']} "
                f"multi={result['multi_claim']['status']}",
                flush=True,
            )
            if len(results) >= args.num_cases:
                break
    finally:
        # Release large model references before process exit.
        del corrector, verifier, generator

    output_path = Path(args.output) if args.output else (
        _PROTOTYPE_ROOT / "outputs" / "multi_claim_paired_natural_evaluation.jsonl"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for result in results:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()
        temporary.replace(output_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    print(f"Eligible paired cases: {len(results)}; scanned: {scanned}")
    print(f"Results: {output_path}")
    if not results:
        print("No eligible cases found; increase --max-cases-to-scan.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
