#!/usr/bin/env python3
"""
Bare-vs-labeled natural-data comparison, POST claim-extraction bugfixes,
POST the correction-reverification ordinal-matching fix.

This SUPERSEDES compare_premise_framing_natural.py's claim-loading step
without touching that script, its outputs, or the committed
run_A/B/C_n30.jsonl / run_natural_targeted.jsonl files (all read-only
here, never written).

Why a new script instead of editing compare_premise_framing_natural.py:
investigation for this task found that the committed natural n=30/targeted
runs were parsed by an OLDER version of src/claim_parser.py.
`scripts/reparse_n30_with_fixed_parser.py` (pre-existing) proves the
CURRENT parser resolves substantially more evidence on the exact SAME
generated text (38/88 -> 57/93 claims matched, after this task's two
additional parser fixes on top of ones already in the codebase — see
research_phase_next_status.md). Reusing the stale `claims` list from the
committed files (as compare_premise_framing_natural.py's first version
does) would silently keep diagnosing a parser that source code has since
moved past. This script re-derives claims from the SAME generated_field.text
using the CURRENT claim_parser.extract_claims() + evidence_matcher — no
regeneration, no new cases, no corpus change — then runs the identical
bare-vs-labeled verification + genuine GPU correction comparison as
compare_premise_framing_natural.py.

Nothing in outputs/ is overwritten; results go to new, separately-prefixed
files (default: framing_comparison_natural_reparsed).
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
import time
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src import claim_parser, pipeline
from src.data_loader import Case, load_usable_evidence
from src.verifier import (
    NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
    PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED,
)
from src.evidence_matcher import match_evidence, NO_EVIDENCE

SOURCES = [
    ("run_B_n30.jsonl", "n30", None),
    ("run_natural_targeted.jsonl", "targeted_n11", "mode_B"),
]


def load_documents(outputs: Path) -> list[dict]:
    """Same source files/pooling as compare_premise_framing_natural.py, but
    only case_text + generated_field.text are taken from the committed
    record — claims are re-derived fresh below, not reused."""
    docs = []
    for fname, tag, sub in SOURCES:
        path = outputs / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            block = rec[sub] if sub else rec
            docs.append({
                "source": tag,
                "document_id": rec["document_id"],
                "case_text": block["case_text"],
                "generated_field_text": block["generated_field"]["text"],
            })
    return docs


def build_baseline(doc: dict, exact_index: dict, all_usable: list, fuzzy_threshold: float) -> dict:
    """Re-derives claims from generated_field_text with the CURRENT
    claim_parser + evidence_matcher — mirrors pipeline.generate_and_parse()'s
    claim-building loop exactly (same fields, same _evidence_provision
    convention), just fed a pre-existing generated text instead of a fresh
    generator call."""
    claims = claim_parser.extract_claims(doc["generated_field_text"])
    claim_records = []
    for claim in claims:
        match = match_evidence(claim.citation_extracted, exact_index, all_usable, fuzzy_threshold)
        claim_records.append({
            "claim_id": claim.claim_id,
            "claim_text": claim.claim_text,
            "citation_extracted": claim.citation_extracted.as_dict() if claim.citation_extracted else None,
            "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
            "evidence_text": match.evidence.canonical_text if match.matched else None,
            "evidence_match_method": match.match_method,
            "_evidence_provision": {
                "provision_type": match.evidence.provision_type,
                "provision_number": match.evidence.provision_number,
                "act": match.evidence.act,
            } if match.matched else None,
            "verdict": NO_EVIDENCE if not match.matched else NOT_ENOUGH_INFORMATION,
            "confidence": None, "sub_reason": None, "verifier_model": None,
        })
    return {
        "document_id": doc["document_id"],
        "case_text": doc["case_text"],
        "generated_field": {"text": doc["generated_field_text"]},
        "claims": claim_records,
    }


def triggers_correction(rec: dict) -> bool:
    return rec["verdict"] == CONTRADICTED or rec.get("sub_reason") == "low_confidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--with-correction", action="store_true")
    ap.add_argument("--out-prefix", default="framing_comparison_natural_reparsed")
    args = ap.parse_args()

    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    exact_index, all_usable = load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )

    documents = load_documents(outputs)
    # Pre-compute claim counts once (framing-independent: claim extraction +
    # evidence matching do not depend on premise_framing at all).
    pre_baselines = {d["document_id"] + "|" + d["source"]: build_baseline(d, exact_index, all_usable, fuzzy_threshold)
                      for d in documents}
    n_claims = sum(len(b["claims"]) for b in pre_baselines.values())
    n_matched = sum(1 for b in pre_baselines.values() for c in b["claims"] if c["evidence_text"])
    print(f"Natural documents: {len(documents)}  (claims: {n_claims}, evidence-matched: {n_matched}, "
          f"current parser)", flush=True)

    generator = corrector = None
    vram_available = False
    if args.with_correction:
        import torch
        if not torch.cuda.is_available():
            print("ERROR: --with-correction requires CUDA.", file=sys.stderr)
            return 2
        vram_available = True
        torch.cuda.reset_peak_memory_stats()
        from src.generator import StatuteGroundingGenerator
        from src.corrector import SelectiveCorrector
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
        generator.load()
        corrector = SelectiveCorrector(
            generator=generator,
            max_new_tokens=config["correction"]["max_new_tokens"],
            do_sample=config["correction"]["do_sample"],
            system_prompt=config["correction"]["system_prompt"],
        )

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=args.device,
    )
    verifier.load()
    print(f"Loaded {verifier.model_id} on {args.device}", flush=True)

    per_framing: dict[str, dict] = {}
    claim_rows: list[dict] = []
    correction_rows: list[dict] = []

    for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
        arm_config = copy.deepcopy(config)
        arm_config["verification"]["premise_framing"] = framing

        verdicts = Counter()
        triggers = 0
        corr_status = Counter()
        reverif = Counter()
        unsafe_shipped = 0
        unflagged_preserved = 0
        unflagged_checked = 0
        verification_seconds = 0.0
        correction_seconds = 0.0
        arm_t0 = time.time()

        for doc in documents:
            key = doc["document_id"] + "|" + doc["source"]
            baseline = copy.deepcopy(pre_baselines[key])
            baseline["_exact_index"] = exact_index
            baseline["_all_usable"] = all_usable
            baseline["_verifier"] = verifier

            t_v0 = time.time()
            pipeline.apply_verification(baseline, verifier, framing)
            verification_seconds += time.time() - t_v0

            doc_triggered = False
            for rec in baseline["claims"]:
                verdicts[rec["verdict"]] += 1
                claim_rows.append({
                    "framing": framing, "source": doc["source"],
                    "document_id": doc["document_id"], "claim_id": rec["claim_id"],
                    "claim_text": rec["claim_text"], "evidence_id": rec["evidence_id"],
                    "evidence_text": rec["evidence_text"],
                    "verdict": rec["verdict"], "confidence": rec["confidence"],
                    "sub_reason": rec["sub_reason"],
                })
                if rec["evidence_text"] is not None and triggers_correction(rec):
                    doc_triggered = True

            if doc_triggered:
                triggers += 1

            if args.with_correction and doc_triggered:
                case_obj = Case(document_id=doc["document_id"], case_text=doc["case_text"], raw_citation_keys=[])
                t_c0 = time.time()
                summary = pipeline.apply_selective_correction(baseline, case_obj, corrector, arm_config)
                correction_seconds += time.time() - t_c0
                corr_status[summary["status"]] += 1
                rv = summary.get("reverification") or {}
                if rv.get("verdict"):
                    reverif[rv["verdict"]] += 1
                if summary["status"] == "corrected" and rv.get("verdict") != ENTAILED:
                    unsafe_shipped += 1

                target_id = summary["triggered_for_claim_id"]
                if summary.get("regenerated_text") is not None:
                    for rec in baseline["claims"]:
                        if rec["claim_id"] == target_id:
                            continue
                        unflagged_checked += 1
                        if rec["claim_text"] in summary["regenerated_text"]:
                            unflagged_preserved += 1

                correction_rows.append({
                    "framing": framing, "source": doc["source"], "document_id": doc["document_id"],
                    "triggered_for_claim_id": target_id, "status": summary["status"],
                    "original_field_text": summary["original_field_text"],
                    "regenerated_text": summary["regenerated_text"],
                    "reverification": rv,
                })

        arm_elapsed = time.time() - arm_t0
        arm_peak_vram_mib = None
        if vram_available:
            import torch
            torch.cuda.synchronize()
            arm_peak_vram_mib = torch.cuda.max_memory_allocated() // (1024 * 1024)

        correction_attempts = sum(corr_status.values())
        per_framing[framing] = {
            "n_documents": len(documents), "n_claims": n_claims, "n_claims_evidence_matched": n_matched,
            "verdict_counts": dict(verdicts), "documents_with_trigger": triggers,
            "correction_attempts": correction_attempts, "correction_statuses": dict(corr_status),
            "corrections_shipped_success": corr_status.get("corrected", 0),
            "correction_failed": corr_status.get("correction_failed", 0),
            "correction_scope_violation": corr_status.get("correction_scope_violation", 0),
            "reverification_verdicts": dict(reverif), "unsafe_corrections_shipped": unsafe_shipped,
            "unflagged_claim_checked": unflagged_checked, "unflagged_claim_preserved": unflagged_preserved,
            "correction_ran": args.with_correction,
            "runtime_seconds_total_arm": arm_elapsed, "runtime_seconds_verification": verification_seconds,
            "runtime_seconds_correction": correction_seconds, "peak_vram_mib_cumulative": arm_peak_vram_mib,
        }
        print(f"[{framing}] verdicts={dict(verdicts)} doc_triggers={triggers} "
              f"correction_attempts={correction_attempts} elapsed={arm_elapsed:.1f}s "
              f"peak_vram={arm_peak_vram_mib}MiB", flush=True)

    result = {
        "experiment": "premise_framing_ablation_natural_reparsed",
        "data": "NATURAL NyayaRAG generations, claims RE-DERIVED with the current claim_parser "
                "from run_B_n30.jsonl + run_natural_targeted.jsonl generated_field.text (verbatim, "
                "not regenerated)",
        "verifier_model": verifier.model_id, "confidence_threshold": verifier.confidence_threshold,
        "device": args.device, "correction_ran": args.with_correction,
        "n_documents": len(documents), "n_claims": n_claims, "n_claims_evidence_matched": n_matched,
        "seed": config["seed"], "per_framing": per_framing,
        "overall_peak_vram_mib": (
            per_framing[PREMISE_FRAMING_LABELED]["peak_vram_mib_cumulative"] if vram_available else None
        ),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (outputs / f"{args.out_prefix}_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (outputs / f"{args.out_prefix}_claims_results.jsonl").open("w", encoding="utf-8") as f:
        for r in claim_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (outputs / f"{args.out_prefix}_corrections_results.jsonl").open("w", encoding="utf-8") as f:
        for r in correction_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    b, l = per_framing[PREMISE_FRAMING_BARE], per_framing[PREMISE_FRAMING_LABELED]
    print("\n" + "=" * 68)
    print(f"{'metric':<40}{'bare':>12}{'labeled':>14}")
    print("-" * 68)
    print(f"{'verdict counts':<40}{str(b['verdict_counts']):>12}{str(l['verdict_counts']):>14}")
    print(f"{'documents with correction trigger':<40}{b['documents_with_trigger']:>12}{l['documents_with_trigger']:>14}")
    if args.with_correction:
        print(f"{'correction attempts':<40}{b['correction_attempts']:>12}{l['correction_attempts']:>14}")
        print(f"{'corrections shipped (SUCCESS)':<40}{b['corrections_shipped_success']:>12}{l['corrections_shipped_success']:>14}")
        print(f"{'correction_failed':<40}{b['correction_failed']:>12}{l['correction_failed']:>14}")
        print(f"{'correction_scope_violation':<40}{b['correction_scope_violation']:>12}{l['correction_scope_violation']:>14}")
        print(f"{'unsafe corrections shipped':<40}{b['unsafe_corrections_shipped']:>12}{l['unsafe_corrections_shipped']:>14}")
        print(f"{'unflagged-claim preserved/checked':<40}"
              f"{str(b['unflagged_claim_preserved'])+'/'+str(b['unflagged_claim_checked']):>12}"
              f"{str(l['unflagged_claim_preserved'])+'/'+str(l['unflagged_claim_checked']):>14}")
        print(f"{'peak VRAM MiB (cumulative)':<40}{str(b['peak_vram_mib_cumulative']):>12}{str(l['peak_vram_mib_cumulative']):>14}")
    print("=" * 68)
    print(f"\nWrote {outputs / (args.out_prefix + '_metrics.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
