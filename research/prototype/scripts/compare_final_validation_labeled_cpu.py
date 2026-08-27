#!/usr/bin/env python3
"""
Targeted CPU-only verification-only comparison: bare (already computed, Arm
B of final_gpu_validation) vs labeled framing, on the EXACT SAME 209 claims
/ v0+v1 evidence pool / atomic_scope_check="assertion_spans" config that
final_gpu_validation's Arm B already used. Reuses Arm B's already-generated
text and already-computed evidence matches -- NO new Qwen generation, NO
new GPU use. Only a second DeBERTa verification pass, under labeled
framing, on CPU.

Purpose: inform the premise_framing production-config decision (see
FINAL_PRODUCTION_CONFIG.md) with a same-cases, same-pool, same-scope-check
comparison -- something no prior experiment in this project has produced
(prior bare-vs-labeled comparisons predate the v1 evidence pool and the
assertion_spans scope check).

Scope, honestly stated: this is VERIFICATION-ONLY. It does not attempt new
Qwen correction calls under labeled framing (that needs the GPU and is out
of scope for "a final targeted CPU test" per this task's instructions) --
it measures evidence coverage (unchanged, shared with Arm B), verdict
distribution, and correction TRIGGER rate (a pure function of verdict) only.
Actual shipped-correction rate under labeled+all-improvements is NOT
measured here and is not claimed.

Nothing in outputs/ is overwritten -- new, distinctly-named output files.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.data_loader import load_usable_evidence_from_config
from src.verifier import NLIVerifier, format_premise, PREMISE_FRAMING_LABELED, CONTRADICTED, NOT_ENOUGH_INFORMATION


def triggers_correction(verdict: str, sub_reason) -> bool:
    return verdict == CONTRADICTED or (verdict == NOT_ENOUGH_INFORMATION and sub_reason == "low_confidence")


def main() -> int:
    outputs = _PROTOTYPE_ROOT / "outputs"
    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent

    config_v1 = dict(config)
    config_v1["use_evidence_v1"] = True
    exact_index, all_usable = load_usable_evidence_from_config(config_v1, repo_root)
    by_key = {e.dataset_citation_key: e for e in all_usable}
    print(f"v0+v1 usable pool: {len(all_usable)} records (post-audit-fix).", flush=True)

    rows = [json.loads(l) for l in (outputs / "final_gpu_validation_B.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Loaded {len(rows)} cases from final_gpu_validation_B.jsonl (Arm B, v1 pool, bare framing already computed).", flush=True)

    print("Loading DeBERTa verifier on CPU...", flush=True)
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=0.70,
        max_sequence_length=config["verification"]["max_sequence_length"],
        device="cpu",
    )
    verifier.load()

    bare_verdicts = Counter()
    labeled_verdicts = Counter()
    bare_triggers = 0
    labeled_triggers = 0
    flips = []
    n_verified = 0

    labeled_claims_out = []

    for rec in rows:
        for c in rec["claims"]:
            if c["evidence_text"] is None:
                continue  # NO_EVIDENCE, identical under any framing -- not re-verified
            bare_verdicts[c["verdict"]] += 1
            if triggers_correction(c["verdict"], c.get("sub_reason")):
                bare_triggers += 1

            ev = by_key.get(c["evidence_id"])
            if ev is None:
                # Should not happen (Arm B matched against this exact pool),
                # but never silently skip without recording it.
                print(f"  WARNING: evidence_id {c['evidence_id']!r} not found in current pool "
                      f"(document {rec['document_id']}, claim {c['claim_id']}) -- skipping re-verification.")
                continue

            premise = format_premise(
                ev.canonical_text, framing=PREMISE_FRAMING_LABELED,
                provision_type=ev.provision_type, provision_number=ev.provision_number, act=ev.act,
            )
            result = verifier.verify(premise=premise, hypothesis=c["claim_text"])
            n_verified += 1
            labeled_verdicts[result.label] += 1
            triggered = triggers_correction(result.label, result.sub_reason)
            if triggered:
                labeled_triggers += 1
            if result.label != c["verdict"]:
                flips.append({
                    "document_id": rec["document_id"], "claim_id": c["claim_id"],
                    "evidence_id": c["evidence_id"], "claim_text": c["claim_text"][:200],
                    "bare_verdict": c["verdict"], "bare_confidence": c["confidence"],
                    "labeled_verdict": result.label, "labeled_confidence": result.confidence,
                })
            labeled_claims_out.append({
                "document_id": rec["document_id"], "claim_id": c["claim_id"],
                "evidence_id": c["evidence_id"],
                "bare_verdict": c["verdict"], "bare_confidence": c["confidence"], "bare_sub_reason": c.get("sub_reason"),
                "labeled_verdict": result.label, "labeled_confidence": result.confidence, "labeled_sub_reason": result.sub_reason,
            })

    print(f"\nVerified {n_verified} claims under labeled framing (CPU).", flush=True)
    print(f"Bare verdicts:    {dict(bare_verdicts)}")
    print(f"Labeled verdicts: {dict(labeled_verdicts)}")
    print(f"Bare correction triggers:    {bare_triggers}")
    print(f"Labeled correction triggers: {labeled_triggers}")
    print(f"Verdict flips: {len(flips)}")

    result_out = {
        "experiment": "final_validation_bare_vs_labeled_cpu_verification_only",
        "scope": "VERIFICATION-ONLY. Reuses Arm B's already-generated text and already-matched "
                 "v0+v1 evidence (post-audit-fix, 136 records); only a second CPU DeBERTa "
                 "verification pass under labeled framing is new. No new Qwen generation or "
                 "correction; actual shipped-correction rate under labeled+all-improvements is "
                 "NOT measured here.",
        "n_claims_with_evidence": n_verified,
        "bare_verdict_counts": dict(bare_verdicts),
        "labeled_verdict_counts": dict(labeled_verdicts),
        "bare_correction_triggers": bare_triggers,
        "labeled_correction_triggers": labeled_triggers,
        "n_verdict_flips": len(flips),
        "flips": flips,
    }
    (outputs / "final_validation_bare_vs_labeled_cpu_metrics.json").write_text(
        json.dumps(result_out, indent=2), encoding="utf-8")
    with (outputs / "final_validation_bare_vs_labeled_cpu_claims.jsonl").open("w", encoding="utf-8") as f:
        for row in labeled_claims_out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nWrote {outputs / 'final_validation_bare_vs_labeled_cpu_metrics.json'}")
    print(f"Wrote {outputs / 'final_validation_bare_vs_labeled_cpu_claims.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
