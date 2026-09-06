#!/usr/bin/env python3
"""STEP 4 -- GOLD-02 (synthetic stress set, n=59) expected-vs-actual run.

Unlike GOLD-01's evaluation script, scripts/compare_premise_framing_synthetic.py DOES
import cleanly under this project's pinned Python 3.11.9 (verified). This runner
therefore reuses it directly: `build_baseline()` (the exact real claim_parser +
evidence_matcher construction) and `triggers_correction()` are imported unmodified from
that script. Verification itself goes through `src.pipeline.apply_verification` -- the
real, unmodified production function -- exactly as that script does. Only the I/O
destination differs: outputs go under evaluation/, never overwriting
research/prototype/outputs/ (that script's own default write target).

IMPORTANT, DOCUMENTED DEVIATION FROM THE LITERAL STEP 4 PHASE 2 WORDING:
run_synthetic_stress.jsonl (GOLD-02) has NO literal `expected_label` field (unlike
GOLD-01). Its expected label is CONTRADICTED-by-construction for every record, per
src/synthetic_stress.py's own module docstring ("one synthetic claim per usable evidence
record ... asserts something that deterministically, mechanically inverts a specific
phrase actually present in that record's canonical_text"). This runner therefore:
  (a) does NOT invent or read a field that does not exist, and
  (b) instead performs a STRONGER integrity check than a literal field lookup would give:
      it deterministically re-derives the 59 synthetic claims from the v0 evidence pool
      via the same build_synthetic_stress_claims() function that built the committed
      fixture, and confirms every re-derived claim's text/transform_rule/evidence
      identity matches the frozen fixture's own stored fields exactly, before treating
      "CONTRADICTED" as the expected label for scoring.

No production config value, threshold, model, or tokenization is changed. No GPU is
used. No Qwen generation or correction is invoked. Writes ONLY under
research/prototype/evaluation/.

Usage:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/run_gold02_evaluation.py
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent

sys.path.insert(0, str(PROTOTYPE_DIR))
sys.path.insert(0, str(TESTING_DIR))
sys.path.insert(0, str(PROTOTYPE_DIR / "scripts"))

import yaml  # noqa: E402
from src import pipeline  # noqa: E402
from src.data_loader import load_usable_evidence  # noqa: E402
from src.synthetic_stress import build_synthetic_stress_claims  # noqa: E402
from src.verifier import NLIVerifier, CONTRADICTED  # noqa: E402
from compare_premise_framing_synthetic import build_baseline, triggers_correction  # noqa: E402
from gold_benchmark_common import compute_metrics, confusion_matrix_rows  # noqa: E402

FIXTURE = TESTING_DIR / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl"
EXPECTED_HASH = "717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5"
EXPECTED_COUNT = 59

RUN_DIR = TESTING_DIR / "actual_outputs" / "gold_benchmark_runs"
OUT_DIR = RUN_DIR / "gold02_synthetic"
META_DIR = RUN_DIR / "run_metadata"
LOG_DIR = RUN_DIR / "logs"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True
        ).strip()
    except Exception as e:
        return f"UNKNOWN ({e!r})"


def main() -> int:
    for d in (OUT_DIR, META_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        log_lines.append(msg)

    log("=" * 70)
    log("STEP 4 -- GOLD-02 synthetic stress set run")
    log("=" * 70)

    # ---- Phase 2: verify GOLD input before running inference ----
    if not FIXTURE.exists():
        log(f"BLOCKER: fixture not found at {FIXTURE}")
        (LOG_DIR / "gold02_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2

    fixture_hash = sha256_of(FIXTURE)
    if fixture_hash != EXPECTED_HASH:
        log(f"BLOCKER: hash mismatch. fixture={fixture_hash} expected={EXPECTED_HASH}")
        (LOG_DIR / "gold02_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2
    log(f"Hash verified: {fixture_hash} (matches STEP 3 recorded hash)")

    fixture_records = [json.loads(l) for l in FIXTURE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(fixture_records) != EXPECTED_COUNT:
        log(f"BLOCKER: record count mismatch. found={len(fixture_records)} expected={EXPECTED_COUNT}")
        (LOG_DIR / "gold02_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2
    log(f"Record count verified: {len(fixture_records)}")
    log("NOTE: GOLD-02 has no literal 'expected_label' field (unlike GOLD-01). "
        "Expected label is CONTRADICTED-by-construction for every record -- see this "
        "file's module docstring for the documented reasoning.")

    # ---- Environment / GPU status ----
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        torch_version = torch.__version__
    except Exception as e:
        cuda_available = False
        torch_version = f"IMPORT FAILED: {e!r}"
    log(f"NVIDIA GPU available = {'YES' if cuda_available else 'NO'}")

    config = yaml.safe_load((PROTOTYPE_DIR / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    model_id = config["verification"]["model_id"]
    confidence_threshold = config["verification"]["confidence_threshold"]
    production_framing = config["verification"]["premise_framing"]

    # ---- Re-derive the 59 synthetic claims and confirm they match the frozen fixture ----
    repo_root_for_loader = PROTOTYPE_DIR.parent.parent
    exact_index, all_usable = load_usable_evidence(
        repo_root_for_loader / config["paths"]["canonical_statutes"],
        repo_root_for_loader / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )
    synth_claims = build_synthetic_stress_claims(all_usable)
    log(f"Re-derived {len(synth_claims)} synthetic claims from the v0 evidence pool "
        f"(same construction used to build the frozen fixture)")

    if len(synth_claims) != EXPECTED_COUNT:
        log(f"BLOCKER: re-derived claim count ({len(synth_claims)}) != expected ({EXPECTED_COUNT})")
        (LOG_DIR / "gold02_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2

    fixture_by_id = {r["synthetic_claim_id"]: r for r in fixture_records}
    mismatches = []
    for sc in synth_claims:
        fr = fixture_by_id.get(sc.claim_id)
        if fr is None:
            mismatches.append(f"{sc.claim_id}: not found in fixture")
            continue
        if fr["original_synthetic_text"] != sc.claim_text:
            mismatches.append(f"{sc.claim_id}: claim_text differs from fixture's original_synthetic_text")
        if fr["transform_rule"] != sc.transform_rule:
            mismatches.append(f"{sc.claim_id}: transform_rule differs")
        if fr["evidence_id"] != sc.evidence.dataset_citation_key:
            mismatches.append(f"{sc.claim_id}: evidence_id differs")
        if fr["canonical_evidence_text"] != sc.evidence.canonical_text:
            mismatches.append(f"{sc.claim_id}: canonical_evidence_text differs")

    if mismatches:
        log(f"BLOCKER: {len(mismatches)} reproduction mismatch(es) found between the "
            f"current codebase's deterministic construction and the frozen GOLD-02 fixture:")
        for m in mismatches[:20]:
            log(f"  - {m}")
        log("STOPPING per rule 15 -- this dataset can no longer be trusted as reproducible "
            "from the current code; not proceeding to inference.")
        (LOG_DIR / "gold02_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2
    log("CONFIRMED: all 59 re-derived synthetic claims exactly match the frozen fixture's "
        "own stored fields (claim text, transform rule, evidence identity, canonical text). "
        "The dataset is reproducible from the current codebase.")

    verifier = NLIVerifier(
        model_id=model_id,
        confidence_threshold=confidence_threshold,
        max_sequence_length=config["verification"]["max_sequence_length"],
        device="cpu",
    )
    log(f"\nLoading {model_id} on device=cpu ...")
    t_load = time.time()
    verifier.load()
    load_seconds = time.time() - t_load
    log(f"Loaded in {load_seconds:.1f}s")

    all_framing_metrics = {}

    for framing in ("labeled", "bare"):
        log(f"\n--- Running framing={framing} ---")
        arm_config = copy.deepcopy(config)
        arm_config["verification"]["premise_framing"] = framing

        results = []
        t0 = time.time()
        for sc in synth_claims:
            baseline = build_baseline(sc, exact_index, all_usable, arm_config)
            pipeline.apply_verification(baseline, verifier, pipeline.resolve_premise_framing(arm_config))
            by_id = {c["claim_id"]: c for c in baseline["claims"]}
            c1 = by_id.get("c1")  # the synthetic corrupted claim -- the GOLD record
            c2 = by_id.get("c2")  # the fixed, unrelated real sibling claim -- diagnostic only, no gold label

            predicted_label = c1["verdict"] if c1 else None
            results.append({
                "id": sc.claim_id,
                "transform_rule": sc.transform_rule,
                "evidence_id": sc.evidence.dataset_citation_key,
                "premise": c1["evidence_text"] if c1 else None,
                "hypothesis": sc.claim_text,
                "expected_label": CONTRADICTED,  # by construction -- see module docstring
                "predicted_label": predicted_label,
                "match": predicted_label == CONTRADICTED,
                "confidence": c1["confidence"] if c1 else None,
                "sub_reason": c1.get("sub_reason") if c1 else None,
                "has_evidence": bool(c1 and c1["evidence_text"]),
                "premise_framing": framing,
                "would_trigger_correction": triggers_correction(c1) if c1 else False,
                "sibling_c2_verdict_diagnostic_only": c2["verdict"] if c2 else None,
            })
        elapsed = time.time() - t0

        pred_path = OUT_DIR / f"gold02_predictions_{framing}.jsonl"
        with pred_path.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        log(f"Wrote {pred_path} ({len(results)} records)")

        expected = [r["expected_label"] for r in results]
        predicted = [r["predicted_label"] for r in results]
        cm, per_class, macro_f1 = compute_metrics(expected, predicted)
        accuracy = sum(r["match"] for r in results) / len(results)
        n_no_evidence = sum(1 for r in results if not r["has_evidence"])

        log(f"Contradiction recall (== accuracy, only gold class is CONTRADICTED): {accuracy:.4f}")
        log(f"  (macro F1 = {macro_f1:.4f} -- degenerate/less meaningful here since only one "
            f"gold class is present in this dataset, per its documented narrower scope)")
        log(f"  no-evidence (predicted_label unreachable, no premise matched): {n_no_evidence}")
        for line in confusion_matrix_rows(cm):
            log("  " + line)

        all_framing_metrics[framing] = {
            "n_items": len(results),
            "n_no_evidence": n_no_evidence,
            "elapsed_seconds": elapsed,
            "contradiction_recall": accuracy,
            "macro_f1_degenerate_single_class": macro_f1,
            "confusion_matrix": cm,
            "per_class": per_class,
        }

    metrics = {
        "benchmark_tag": "GOLD-02_synthetic_stress_set",
        "n_items": EXPECTED_COUNT,
        "dataset_sha256": fixture_hash,
        "expected_label_note": "No literal 'expected_label' field in this dataset -- CONTRADICTED-by-construction for all records, per src/synthetic_stress.py's module docstring. Reproducibility of this claim was independently verified this run (see log).",
        "verifier_model": model_id,
        "confidence_threshold": confidence_threshold,
        "device": "cpu",
        "production_premise_framing": production_framing,
        "framings_run": ["labeled", "bare"],
        "primary_framing": "labeled",
        "results_by_framing": all_framing_metrics,
        "model_load_seconds": load_seconds,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch_version,
            "cuda_available": cuda_available,
        },
    }
    (OUT_DIR / "gold02_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"\nWrote {OUT_DIR / 'gold02_metrics.json'}")

    report_lines = [
        "GOLD-02 -- Synthetic Stress Set (n=59) -- STEP 4 Evaluation",
        f"Model: {model_id}",
        "Device: cpu (no NVIDIA GPU present on this machine)",
        f"Confidence threshold: {confidence_threshold} (unchanged from production config)",
        f"Production premise_framing: {production_framing}",
        "Expected label: CONTRADICTED for all 59 records (by construction, no literal field -- see metadata)",
        "",
    ]
    for framing in ("labeled", "bare"):
        m = all_framing_metrics[framing]
        report_lines.append(f"=== framing={framing} {'(PRIMARY / production)' if framing == production_framing else '(secondary reference)'} ===")
        report_lines.append(f"contradiction_recall={m['contradiction_recall']:.4f}  elapsed={m['elapsed_seconds']:.1f}s")
        report_lines += confusion_matrix_rows(m["confusion_matrix"])
        report_lines.append("")
    (OUT_DIR / "gold02_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    log(f"Wrote {OUT_DIR / 'gold02_report.txt'}")

    run_meta = {
        "produced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operating_system": platform.platform(),
        "python_version": platform.python_version(),
        "venv_path": "research/.venv",
        "package_versions": {"torch": torch_version},
        "model_identifier": model_id,
        "model_checkpoint": "as pulled from Hugging Face Hub at first load (no revision= pin -- pre-existing project limitation)",
        "config_path": "research/prototype/config/prototype.yaml",
        "dataset_path": str(FIXTURE.relative_to(REPO_ROOT)),
        "dataset_sha256": fixture_hash,
        "record_count": EXPECTED_COUNT,
        "command_executed": "research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/run_gold02_evaluation.py",
        "git_commit": git_commit(),
        "nvidia_gpu_available": False,
        "cuda_available_per_torch": cuda_available,
        "gpu_execution_claimed": False,
        "qwen_generation_or_correction_invoked": False,
        "existing_evaluation_code_reused": "scripts/compare_premise_framing_synthetic.py::build_baseline, triggers_correction (imported directly, unmodified); src/pipeline.py::apply_verification, resolve_premise_framing (real production functions, unmodified)",
        "reproducibility_check": "PASSED -- all 59 re-derived synthetic claims exactly matched the frozen fixture's stored fields before inference was run",
    }
    run_meta["cpu_info"] = platform.processor() or "not available via stdlib platform.processor()"
    (META_DIR / "gold02_run.meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Wrote {META_DIR / 'gold02_run.meta.json'}")

    (LOG_DIR / "gold02_run.log").write_text("\n".join(log_lines), encoding="utf-8")
    log("\nGOLD-02 run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
