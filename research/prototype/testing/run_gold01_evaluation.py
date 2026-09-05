#!/usr/bin/env python3
"""STEP 4 — GOLD-01 (controlled verifier benchmark, n=420) expected-vs-actual run.

Uses the real, unmodified src/verifier.py::NLIVerifier and format_premise — the exact
same functions research/prototype/scripts/run_controlled_benchmark.py calls internally.
See step4_common.py's module docstring for why that script itself cannot be imported
under this project's pinned Python 3.11.9, and why this runner reimplements only the
generic confusion-matrix arithmetic (not any model/verifier/inference logic).

Runs BOTH premise framings:
  - "labeled" — the actual shipped production value (config/prototype.yaml:
    verification.premise_framing). This is the PRIMARY result.
  - "bare"    — the evaluation script's own historical default, kept as a secondary,
    directly comparable reference arm (historical committed results exist for both).

No production config value, threshold, model, or tokenization is changed. No GPU is
used (device="cpu", the documented, code-supported opt-in for verifier-only runs).
Writes ONLY under research/prototype/testing/ — never to research/prototype/outputs/.

Usage:
    research/.venv/Scripts/python.exe research/prototype/testing/run_gold01_evaluation.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent

sys.path.insert(0, str(PROTOTYPE_DIR))
sys.path.insert(0, str(TESTING_DIR))

from src.verifier import NLIVerifier, format_premise, PREMISE_FRAMINGS  # noqa: E402
from step4_common import compute_metrics, confusion_matrix_rows  # noqa: E402

FIXTURE = TESTING_DIR / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl"
EXPECTED_HASH = "962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99"
EXPECTED_COUNT = 420

RUN_DIR = TESTING_DIR / "actual_outputs" / "step4_gold_verifier"
OUT_DIR = RUN_DIR / "gold01_controlled"
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
    log("STEP 4 -- GOLD-01 controlled verifier benchmark run")
    log("=" * 70)

    # ---- Phase 2: verify GOLD input before running inference ----
    if not FIXTURE.exists():
        log(f"BLOCKER: fixture not found at {FIXTURE}")
        (LOG_DIR / "gold01_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2

    fixture_hash = sha256_of(FIXTURE)
    if fixture_hash != EXPECTED_HASH:
        log(f"BLOCKER: hash mismatch. fixture={fixture_hash} expected={EXPECTED_HASH}")
        log("STOPPING per STEP 4 Phase 2 rule -- discrepancy must be reported, not run through.")
        (LOG_DIR / "gold01_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2
    log(f"Hash verified: {fixture_hash} (matches STEP 3 recorded hash)")

    items = [json.loads(l) for l in FIXTURE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(items) != EXPECTED_COUNT:
        log(f"BLOCKER: record count mismatch. found={len(items)} expected={EXPECTED_COUNT}")
        (LOG_DIR / "gold01_run.log").write_text("\n".join(log_lines), encoding="utf-8")
        return 2
    log(f"Record count verified: {len(items)}")

    for it in items:
        if "expected_label" not in it:
            log(f"BLOCKER: record {it.get('benchmark_id')} missing 'expected_label' field")
            (LOG_DIR / "gold01_run.log").write_text("\n".join(log_lines), encoding="utf-8")
            return 2
    log("Confirmed: expected_label field present on all 420 records")

    # ---- Environment / GPU status (recorded honestly, per rule 13) ----
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        torch_version = torch.__version__
    except Exception as e:
        cuda_available = False
        torch_version = f"IMPORT FAILED: {e!r}"
    log(f"NVIDIA GPU available = {'YES' if cuda_available else 'NO'}")
    log(f"torch version: {torch_version}")

    import yaml
    config = yaml.safe_load((PROTOTYPE_DIR / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    model_id = config["verification"]["model_id"]
    confidence_threshold = config["verification"]["confidence_threshold"]
    max_sequence_length = config["verification"]["max_sequence_length"]
    production_framing = config["verification"]["premise_framing"]
    log(f"Model: {model_id}")
    log(f"confidence_threshold: {confidence_threshold} (unchanged from config/prototype.yaml)")
    log(f"Production premise_framing (config/prototype.yaml): {production_framing}")

    verifier = NLIVerifier(
        model_id=model_id,
        confidence_threshold=confidence_threshold,
        max_sequence_length=max_sequence_length,
        device="cpu",  # explicit, documented opt-in in src/verifier.py -- no GPU on this machine
    )
    log("Loading NLIVerifier on device=cpu ...")
    t_load = time.time()
    verifier.load()
    load_seconds = time.time() - t_load
    log(f"Loaded in {load_seconds:.1f}s")

    all_framing_metrics = {}

    for framing in ("labeled", "bare"):  # labeled = production; bare = secondary reference arm
        log(f"\n--- Running framing={framing} ---")
        results = []
        t0 = time.time()
        for i, it in enumerate(items, 1):
            premise = format_premise(
                it["evidence_text"],
                framing=framing,
                provision_type=it.get("provision_type"),
                provision_number=it.get("provision_number"),
                act=it.get("act_name"),
            )
            r = verifier.verify(premise, it["hypothesis"])
            results.append({
                "id": it["benchmark_id"],
                "evidence_key": it["evidence_key"],
                "condition": it["condition"],
                "premise": premise,
                "hypothesis": it["hypothesis"],
                "expected_label": it["expected_label"],
                "predicted_label": r.label,
                "match": r.label == it["expected_label"],
                "confidence": r.confidence,
                "sub_reason": r.sub_reason,
                "raw_scores": r.raw_scores,
                "verifier_model": r.verifier_model,
                "premise_framing": framing,
            })
            if i % 100 == 0 or i == len(items):
                log(f"  {i}/{len(items)}")
        elapsed = time.time() - t0

        pred_path = OUT_DIR / f"gold01_predictions_{framing}.jsonl"
        with pred_path.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        log(f"Wrote {pred_path} ({len(results)} records)")

        expected = [r["expected_label"] for r in results]
        predicted = [r["predicted_label"] for r in results]
        cm, per_class, macro_f1 = compute_metrics(expected, predicted)
        accuracy = sum(r["match"] for r in results) / len(results)
        n_failures = sum(1 for r in results if r["predicted_label"] is None)

        log(f"Overall accuracy: {accuracy:.4f}   Macro F1: {macro_f1:.4f}")
        for line in confusion_matrix_rows(cm):
            log("  " + line)

        all_framing_metrics[framing] = {
            "n_items": len(results),
            "n_inference_failures": n_failures,
            "elapsed_seconds": elapsed,
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "confusion_matrix": cm,
            "per_class": per_class,
        }

    metrics = {
        "benchmark_tag": "GOLD-01_controlled_verifier_benchmark",
        "n_items": EXPECTED_COUNT,
        "dataset_sha256": fixture_hash,
        "verifier_model": model_id,
        "confidence_threshold": confidence_threshold,
        "max_sequence_length": max_sequence_length,
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
    (OUT_DIR / "gold01_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"\nWrote {OUT_DIR / 'gold01_metrics.json'}")

    report_lines = [
        "GOLD-01 -- Controlled Verifier Benchmark (n=420) -- STEP 4 Evaluation",
        f"Model: {model_id}",
        f"Device: cpu (no NVIDIA GPU present on this machine)",
        f"Confidence threshold: {confidence_threshold} (unchanged from production config)",
        f"Production premise_framing: {production_framing}",
        "",
    ]
    for framing in ("labeled", "bare"):
        m = all_framing_metrics[framing]
        report_lines.append(f"=== framing={framing} {'(PRIMARY / production)' if framing == production_framing else '(secondary reference)'} ===")
        report_lines.append(f"accuracy={m['accuracy']:.4f}  macro_f1={m['macro_f1']:.4f}  elapsed={m['elapsed_seconds']:.1f}s")
        report_lines += confusion_matrix_rows(m["confusion_matrix"])
        report_lines.append("")
    (OUT_DIR / "gold01_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    log(f"Wrote {OUT_DIR / 'gold01_report.txt'}")

    # ---- Phase 9: reproducibility metadata ----
    run_meta = {
        "produced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operating_system": platform.platform(),
        "python_version": platform.python_version(),
        "venv_path": "research/.venv",
        "package_versions": {"torch": torch_version},
        "model_identifier": model_id,
        "model_checkpoint": "as pulled from Hugging Face Hub at first load (no revision= pin in src/verifier.py -- documented, pre-existing project limitation, not introduced by STEP 4)",
        "config_path": "research/prototype/config/prototype.yaml",
        "dataset_path": str(FIXTURE.relative_to(REPO_ROOT)),
        "dataset_sha256": fixture_hash,
        "record_count": EXPECTED_COUNT,
        "command_executed": "research/.venv/Scripts/python.exe research/prototype/testing/run_gold01_evaluation.py",
        "git_commit": git_commit(),
        "nvidia_gpu_available": False,
        "cuda_available_per_torch": cuda_available,
        "gpu_execution_claimed": False,
        "known_blocker_documented": "scripts/run_controlled_benchmark.py cannot be imported under this project's pinned Python 3.11.9 (Python 3.12+-only f-string syntax) -- see step4_common.py module docstring. This runner calls the real NLIVerifier/format_premise directly instead and reimplements only the confusion-matrix arithmetic.",
    }
    try:
        import cpuinfo  # optional, likely absent -- not a pinned dependency
        run_meta["cpu_info"] = cpuinfo.get_cpu_info().get("brand_raw")
    except Exception:
        run_meta["cpu_info"] = platform.processor() or "not available via stdlib platform.processor()"

    (META_DIR / "gold01_run.meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Wrote {META_DIR / 'gold01_run.meta.json'}")

    (LOG_DIR / "gold01_run.log").write_text("\n".join(log_lines), encoding="utf-8")
    log("\nGOLD-01 run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
