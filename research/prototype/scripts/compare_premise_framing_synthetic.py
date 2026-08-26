#!/usr/bin/env python3
"""
Production-path bare-vs-labeled comparison on the synthetic stress dataset.

Runs the REAL wired pipeline code (`pipeline.apply_verification`, the same
function run_case/run_eval_30/run_synthetic_stress_eval call) over the same
59 synthetic stress claims, once per premise framing.

VERIFICATION-ONLY BY DEFAULT. The three metrics below are decided entirely by
verdicts and need no generation:

  * contradiction recall   — c1 (the corrupted claim) verdict == CONTRADICTED
  * false-positive rate    — c2 (the unflagged true claim) wrongly CONTRADICTED
  * correction trigger count — CONTRADICTED, or NEI reached via the confidence
                               downgrade; the same trigger condition production uses

The remaining four metrics from the original synthetic run — correction success
after re-verification, correction_failed, correction_scope_violation, unsafe
corrections shipped — require the Qwen corrector to actually rewrite text, so
they are NOT produced here and are NOT estimated. Run this on the GPU machine
with `--with-correction` for those.

Validity gate: the bare-framing arm must reproduce the verdicts committed in
run_synthetic_stress.jsonl. If it does not, this script's case construction has
drifted from the original run and the comparison is void — it says so and exits
non-zero rather than reporting a comparison against a different baseline.

Nothing in outputs/ is overwritten; results go to new files.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src import claim_parser, pipeline
from src.data_loader import Case, load_usable_evidence
from src.evidence_matcher import match_evidence, NO_EVIDENCE
from src.synthetic_stress import build_synthetic_stress_claims
from src.verifier import (
    NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
    PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED,
)

UNFLAGGED_SENTENCE = ("Article 14 of the Constitution of India guarantees equality "
                      "before the law.")


def build_baseline(synth_claim, exact_index, all_usable, config) -> dict:
    """Mirrors run_synthetic_stress_eval.run_synthetic_case()'s construction of
    the paragraph and claim records. The bare-arm reproduction check below is
    what proves this has not drifted from that script."""
    case_id = f"synth_{synth_claim.claim_id}_{synth_claim.provision_number}"
    full_paragraph = f"{synth_claim.claim_text} {UNFLAGGED_SENTENCE}"

    claim_records = []
    for c in claim_parser.extract_claims(full_paragraph):
        citation_dict = c.citation_extracted.as_dict() if c.citation_extracted else None
        match = (
            match_evidence(c.citation_extracted, exact_index, all_usable,
                           config["evidence_matching"]["fuzzy_token_overlap_threshold"])
            if c.citation_extracted
            else match_evidence(claim_parser.ExtractedCitation("", "", None, None, ""),
                                exact_index, all_usable)
        )
        claim_records.append({
            "claim_id": c.claim_id,
            "claim_text": c.claim_text,
            "citation_extracted": citation_dict,
            "evidence_id": match.evidence.dataset_citation_key if match.evidence else None,
            "evidence_text": match.evidence.canonical_text if match.evidence else None,
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
        "document_id": case_id,
        "case_text": f"Synthetic Stress Case for {synth_claim.provision_number}.",
        "generated_field": {"text": full_paragraph},
        "claims": claim_records,
    }


def triggers_correction(rec: dict) -> bool:
    """The pipeline's own trigger condition: a contradicted claim, or one pushed
    to NEI only by the confidence downgrade."""
    return rec["verdict"] == CONTRADICTED or rec.get("sub_reason") == "low_confidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--limit", type=int, default=None,
                    help="deterministic first-N subset (cases are in a fixed order)")
    ap.add_argument("--with-correction", action="store_true",
                    help="GPU only: also run the real Qwen corrector and re-verification")
    ap.add_argument("--out-prefix", default="framing_comparison_synthetic")
    args = ap.parse_args()

    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    exact_index, all_usable = load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )
    synth_claims = build_synthetic_stress_claims(all_usable)
    if args.limit:
        synth_claims = synth_claims[: args.limit]
    print(f"Synthetic stress claims: {len(synth_claims)}", flush=True)

    generator = corrector = None
    if args.with_correction:
        import torch
        if not torch.cuda.is_available():
            print("ERROR: --with-correction requires CUDA. Refusing to run the 7B "
                  "corrector on CPU.", file=sys.stderr)
            return 2
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
    rows: list[dict] = []

    for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
        # Config is copied per arm so the ONLY thing differing between the two
        # runs is premise_framing — threshold, model and every other knob are
        # taken from the same committed config.
        arm_config = copy.deepcopy(config)
        arm_config["verification"]["premise_framing"] = framing

        c1_verdicts, c2_verdicts = Counter(), Counter()
        c1_with_evidence = 0
        triggers = 0
        corr_status = Counter()
        reverif = Counter()
        unsafe_shipped = 0

        for sc in synth_claims:
            baseline = build_baseline(sc, exact_index, all_usable, arm_config)
            # The real, wired production function.
            pipeline.apply_verification(
                baseline, verifier, pipeline.resolve_premise_framing(arm_config)
            )

            by_id = {c["claim_id"]: c for c in baseline["claims"]}
            c1 = by_id.get("c1")
            c2 = by_id.get("c2")

            if c1 is not None:
                c1_verdicts[c1["verdict"]] += 1
                if c1["evidence_text"]:
                    c1_with_evidence += 1
                if triggers_correction(c1):
                    triggers += 1
            if c2 is not None:
                c2_verdicts[c2["verdict"]] += 1

            row = {
                "framing": framing,
                "synthetic_claim_id": sc.claim_id,
                "transform_rule": sc.transform_rule,
                "evidence_id": sc.evidence.dataset_citation_key,
                "c1_verdict": c1["verdict"] if c1 else None,
                "c1_confidence": c1["confidence"] if c1 else None,
                "c1_sub_reason": c1.get("sub_reason") if c1 else None,
                "c1_has_evidence": bool(c1 and c1["evidence_text"]),
                "c2_verdict": c2["verdict"] if c2 else None,
                "c2_confidence": c2["confidence"] if c2 else None,
            }

            if args.with_correction and c1 is not None and triggers_correction(c1):
                case_obj = Case(document_id=baseline["document_id"],
                                case_text=baseline["case_text"], raw_citation_keys=[])
                baseline["_exact_index"] = exact_index
                baseline["_all_usable"] = all_usable
                baseline["_verifier"] = verifier
                summary = pipeline.apply_selective_correction(
                    baseline, case_obj, corrector, arm_config
                )
                corr_status[summary["status"]] += 1
                rv = summary.get("reverification") or {}
                if rv.get("verdict"):
                    reverif[rv["verdict"]] += 1
                # A correction is unsafe if it shipped while not ENTAILED.
                if summary["status"] == "corrected" and rv.get("verdict") != ENTAILED:
                    unsafe_shipped += 1
                row["correction_status"] = summary["status"]
                row["reverification_verdict"] = rv.get("verdict")
                row["corrected_claim"] = rv.get("claim_text")
            rows.append(row)

        n = len(synth_claims)
        per_framing[framing] = {
            "n_cases": n,
            "c1_verdicts": dict(c1_verdicts),
            "c2_verdicts": dict(c2_verdicts),
            "c1_with_evidence": c1_with_evidence,
            "contradiction_recall_overall": c1_verdicts.get(CONTRADICTED, 0) / n if n else 0.0,
            "contradiction_recall_with_evidence": (
                c1_verdicts.get(CONTRADICTED, 0) / c1_with_evidence if c1_with_evidence else 0.0),
            "false_positive_rate_c2": c2_verdicts.get(CONTRADICTED, 0) / n if n else 0.0,
            "correction_triggers": triggers,
            "correction_statuses": dict(corr_status),
            "reverification_verdicts": dict(reverif),
            "unsafe_corrections_shipped": unsafe_shipped,
            "correction_ran": args.with_correction,
        }
        print(f"[{framing}] c1={dict(c1_verdicts)} c2={dict(c2_verdicts)} triggers={triggers}",
              flush=True)

    # ---- validity gate: bare arm must reproduce the committed run -----------
    committed = outputs / "run_synthetic_stress.jsonl"
    reproduction = {"checked": False}
    if committed.exists() and not args.limit:
        recorded = {}
        for line in committed.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            claims = rec["condition_B"]["claims"]
            c1 = next((c for c in claims if c["claim_id"] == "c1"), None)
            if c1:
                recorded[rec["synthetic_claim_id"]] = c1
        bare_rows = {r["synthetic_claim_id"]: r for r in rows if r["framing"] == PREMISE_FRAMING_BARE}
        common = sorted(set(recorded) & set(bare_rows))
        agree = sum(1 for k in common if recorded[k]["verdict"] == bare_rows[k]["c1_verdict"])

        # sub_reason is tracked separately from the verdict. The committed run
        # scored fp16 on GPU; this may be fp32 on CPU. Probabilities agree to
        # ~3dp, but a claim whose confidence sits within that margin of the 0.70
        # threshold can land on either side of the low-confidence downgrade and
        # so change the correction TRIGGER count without changing any verdict.
        # That is a numeric artifact of dtype, not construction drift, so it is
        # reported rather than treated as a failure.
        sub_mismatch = [
            {"id": k,
             "committed_confidence": recorded[k]["confidence"],
             "committed_sub_reason": recorded[k].get("sub_reason"),
             "this_run_confidence": bare_rows[k]["c1_confidence"],
             "this_run_sub_reason": bare_rows[k]["c1_sub_reason"]}
            for k in common
            if (recorded[k].get("sub_reason") or None) != (bare_rows[k]["c1_sub_reason"] or None)
        ]
        drifts = [abs(recorded[k]["confidence"] - bare_rows[k]["c1_confidence"])
                  for k in common
                  if recorded[k]["confidence"] is not None
                  and bare_rows[k]["c1_confidence"] is not None]
        reproduction = {
            "checked": True, "compared": len(common), "agree": agree,
            "match": agree == len(common) and len(common) > 0,
            "sub_reason_mismatches": sub_mismatch,
            "max_confidence_drift": max(drifts) if drifts else None,
            "mean_confidence_drift": (sum(drifts) / len(drifts)) if drifts else None,
        }
        print(f"\nBare-arm reproduction of run_synthetic_stress.jsonl: "
              f"verdicts {agree}/{len(common)}, "
              f"sub_reason mismatches {len(sub_mismatch)} "
              f"(max confidence drift {max(drifts) if drifts else 0:.6f})", flush=True)

    result = {
        "experiment": "premise_framing_ablation_synthetic",
        "data": "SYNTHETIC — deliberately corrupted statutory claims, not natural NyayaRAG",
        "verifier_model": verifier.model_id,
        "confidence_threshold": verifier.confidence_threshold,
        "device": args.device,
        "correction_ran": args.with_correction,
        "n_cases": len(synth_claims),
        "seed": config["seed"],
        "bare_arm_reproduction": reproduction,
        "per_framing": per_framing,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (outputs / f"{args.out_prefix}_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    with (outputs / f"{args.out_prefix}_results.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    b, l = per_framing[PREMISE_FRAMING_BARE], per_framing[PREMISE_FRAMING_LABELED]
    print("\n" + "=" * 68)
    print(f"{'metric':<40}{'bare':>12}{'labeled':>14}")
    print("-" * 68)
    print(f"{'contradiction recall (all)':<40}"
          f"{b['contradiction_recall_overall']:>11.1%}{l['contradiction_recall_overall']:>14.1%}")
    print(f"{'contradiction recall (with evidence)':<40}"
          f"{b['contradiction_recall_with_evidence']:>11.1%}"
          f"{l['contradiction_recall_with_evidence']:>14.1%}")
    print(f"{'false-positive rate (c2)':<40}"
          f"{b['false_positive_rate_c2']:>11.1%}{l['false_positive_rate_c2']:>14.1%}")
    print(f"{'correction triggers':<40}{b['correction_triggers']:>12}{l['correction_triggers']:>14}")
    if args.with_correction:
        print(f"{'corrections shipped':<40}"
              f"{b['correction_statuses'].get('corrected', 0):>12}"
              f"{l['correction_statuses'].get('corrected', 0):>14}")
        print(f"{'correction_failed':<40}"
              f"{b['correction_statuses'].get('correction_failed', 0):>12}"
              f"{l['correction_statuses'].get('correction_failed', 0):>14}")
        print(f"{'correction_scope_violation':<40}"
              f"{b['correction_statuses'].get('correction_scope_violation', 0):>12}"
              f"{l['correction_statuses'].get('correction_scope_violation', 0):>14}")
        print(f"{'unsafe corrections shipped':<40}"
              f"{b['unsafe_corrections_shipped']:>12}{l['unsafe_corrections_shipped']:>14}")
    else:
        print("\ncorrection metrics NOT measured (requires --with-correction on a CUDA machine)")
    print("=" * 68)
    print(f"\nWrote {outputs / (args.out_prefix + '_metrics.json')}")
    print(f"Wrote {outputs / (args.out_prefix + '_results.jsonl')}")

    if reproduction.get("checked") and not reproduction.get("match"):
        print("\nERROR: bare arm did not reproduce the committed synthetic run; "
              "case construction has drifted and this comparison is void.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
