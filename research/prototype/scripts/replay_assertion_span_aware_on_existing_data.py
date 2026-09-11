#!/usr/bin/env python3
"""
Replays the properly-integrated assertion-SPAN-aware correction
(apply_selective_correction_assertion_aware(), now consuming the real
parser-produced `assertion_spans` list via `_correction_target_spans`,
not just `assertion_text` -- see the 2026-09-12 continuation session)
against the ALREADY-COLLECTED n=10 real natural-data batch
(outputs/assertion_aware_correction_experiment_{OLD,CURRENT}.jsonl),
WITHOUT any fresh Qwen call.

Why this is valid (per this task's explicit "reuse existing data first,
do not rerun Qwen unless necessary" instruction): the corrector's OUTPUT
for a given input fragment is a fixed, already-recorded fact for each of
these 10 cases (`corrected_fragment` in the existing JSONL). This script
verifies WHAT WOULD HAVE BEEN ASKED (the correction target -- confirmed
below to be byte-identical between the old assertion_text-only code and
the new assertion_spans-aware code for every one of these 10 real cases,
since none of them has a genuine multi-element assertion_spans -- see the
printed audit) and re-runs the REAL, live DeBERTa verifier (a ~184M-param
model, safe to load without any Qwen/GPU-memory concern) against the
REAL evidence pool to reproduce the full safety-gate chain exactly as the
new code would execute it.

This is a verification step, not a new experiment: it does not claim to
produce new natural-data evidence beyond what outputs/assertion_aware_correction_experiment_report.md
already reports -- it exists to CONFIRM the architecture refactor (Phase
1-3 of the "integrate assertion-span-aware correction" task) did not
silently change behavior on real data, by construction.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src import claim_parser, pipeline
from src.data_loader import load_usable_evidence_from_config
from src.corrector import CorrectionMetadata
from src.verifier import NLIVerifier

ARMS = ("OLD", "CURRENT")


class ReplayCorrector:
    """Returns the EXACT already-recorded `corrected_fragment` for one
    (document_id, arm) pair -- no model call. Records what target_span it
    was actually asked to correct, so the audit below can confirm it
    matches the ORIGINAL run's target (proving the refactor changed
    nothing about WHAT was targeted for these 10 real cases)."""

    def __init__(self, fragment: str):
        self._fragment = fragment
        self.calls = []

    def correct_assertion_span(self, case_text, target_span, evidence_text,
                                assertion_span_system_prompt, max_new_tokens):
        self.calls.append(target_span)
        meta = CorrectionMetadata(model_id="Qwen/Qwen2.5-7B-Instruct (replayed, not re-run)",
                                   max_new_tokens=max_new_tokens, do_sample=False, seed=42)
        return self._fragment, meta


def main() -> int:
    base_config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    exact_index, all_usable = load_usable_evidence_from_config(base_config, repo_root)

    verifier = NLIVerifier(
        model_id=base_config["verification"]["model_id"],
        confidence_threshold=base_config["verification"]["confidence_threshold"],
        max_sequence_length=base_config["verification"]["max_sequence_length"],
        device="cpu",
    )
    print("Loading real DeBERTa verifier on CPU (no GPU/Qwen memory involved)...")
    verifier.load()
    print("Loaded.\n")

    rows = []
    for arm in ARMS:
        path = outputs / f"assertion_aware_correction_experiment_{arm}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            old_rec = json.loads(line)
            doc_id = old_rec["document_id"]
            old_corr = old_rec["correction"]
            if old_corr["status"] == "not_triggered":
                continue

            generated_text = old_rec["generated_field"]["text"]
            case = type("Case", (), {"document_id": doc_id, "case_text": "(replay: case_text not needed by ReplayCorrector)"})()

            baseline = {
                "document_id": doc_id,
                "generated_field": old_rec["generated_field"],
                "claims": old_rec["claims"],
                "_exact_index": exact_index,
                "_all_usable": all_usable,
                "_verifier": verifier,
            }

            arm_config = dict(base_config)
            arm_config["verification"] = dict(base_config["verification"])
            arm_config["verification"]["narrow_primary_hypothesis"] = (arm == "CURRENT")
            arm_config["correction"] = dict(base_config["correction"])
            arm_config["correction"]["assertion_aware"] = True

            old_target_fragment = old_corr.get("target_content_fragment") or old_corr.get("target_assertion_text")
            old_fragment = old_corr.get("corrected_fragment")
            if old_fragment is None and old_target_fragment and old_corr.get("regenerated_text"):
                # A few of the earliest committed records predate the fix
                # that surfaced `corrected_fragment` on every early-return
                # branch (the background GPU process had already started
                # with the pre-fix module loaded in memory when that fix
                # landed -- see outputs/assertion_span_aware_integration_replay.json's
                # notes). Reconstruct it exactly from the splice's own
                # guarantee: regenerated_text == prefix + corrected_fragment
                # + suffix, where prefix/suffix are the text immediately
                # around target_assertion_text's one occurrence in
                # original_field_text.
                orig = old_corr["original_field_text"]
                pos = orig.find(old_target_fragment)
                if pos != -1 and orig.count(old_target_fragment) == 1:
                    prefix, suffix = orig[:pos], orig[pos + len(old_target_fragment):]
                    regen = old_corr["regenerated_text"]
                    if regen.startswith(prefix) and regen.endswith(suffix):
                        old_fragment = regen[len(prefix): len(regen) - len(suffix)]
            replay_corrector = ReplayCorrector(old_fragment or "")

            new_summary = pipeline.apply_selective_correction_assertion_aware(
                baseline, case, replay_corrector, arm_config
            )

            new_target_fragment = new_summary.get("target_content_fragment")
            target_matches = (new_target_fragment == old_target_fragment)
            outcome_matches = (new_summary["status"] == old_corr["status"])

            rows.append({
                "document_id": doc_id, "arm": arm,
                "old_status": old_corr["status"], "new_status": new_summary["status"],
                "old_target_fragment": old_target_fragment, "new_target_fragment": new_target_fragment,
                "target_matches": target_matches, "outcome_matches": outcome_matches,
                "new_assertion_spans": new_summary.get("target_assertion_spans"),
            })

            print(f"{doc_id:10s} {arm:8s} old={old_corr['status']:32s} new={new_summary['status']:32s} "
                  f"target_match={target_matches} outcome_match={outcome_matches} "
                  f"spans={new_summary.get('target_assertion_spans')}")

    n_target_mismatch = sum(1 for r in rows if not r["target_matches"])
    n_outcome_mismatch = sum(1 for r in rows if not r["outcome_matches"])
    print(f"\n{len(rows)} paired attempts replayed.")
    print(f"Target-fragment mismatches (old assertion_text-only vs new assertion_spans-aware): {n_target_mismatch}")
    print(f"Outcome mismatches: {n_outcome_mismatch}")

    out_path = outputs / "assertion_span_aware_integration_replay.json"
    out_path.write_text(json.dumps({"rows": rows, "n_target_mismatch": n_target_mismatch,
                                     "n_outcome_mismatch": n_outcome_mismatch}, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
