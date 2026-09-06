#!/usr/bin/env python3
"""STEP 6 Phase 4 -- 588-claim natural aggregate, fresh CPU-safe evaluation.

Reuses the EXACT source-file list and text-deduplication logic from
scripts/measure_evidence_coverage_v0_vs_v1.py (not a substitute dataset) to identify
the same 588-claim / 133-distinct-text universe, then extends it with a real DeBERTa
verification pass (CPU) under the current production config -- something the original
script does not do (it only measures evidence coverage). No Qwen generation or
correction is invoked anywhere: every generated_field.text here is already-existing,
historical text from a prior GPU session; only claim parsing, evidence matching, and
NLI verification (all CPU-safe, deterministic-or-real-small-model) are freshly computed.

METRIC-ONLY: no independent correctness label exists for any of these 588 claims.
See evaluation/METRIC_DEFINITIONS.md for exactly what each reported number means and
does not mean.

Writes only under research/prototype/evaluation/.

Usage:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/run_natural_588_evaluation.py
"""
from __future__ import annotations

import datetime
import json
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"

sys.path.insert(0, str(PROTOTYPE_DIR))

import yaml  # noqa: E402
from src import claim_parser  # noqa: E402
from src.data_loader import load_usable_evidence_from_config  # noqa: E402
from src.evidence_matcher import match_evidence, NO_EVIDENCE  # noqa: E402
from src.verifier import NLIVerifier, format_premise  # noqa: E402

OUT_DIR = TESTING_DIR / "actual_outputs" / "natural_data_runs" / "588_claims"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# EXACT same source list as scripts/measure_evidence_coverage_v0_vs_v1.py -- not substituted.
SOURCES = [
    ("run_A_n30.jsonl", None),
    ("run_natural_targeted.jsonl", "mode_B"),
    ("natural_candidates_50_gpu_bare.jsonl", None),
    ("natural_candidates_batch2_gpu_bare.jsonl", None),
]


def iter_generated_texts():
    for fname, sub in SOURCES:
        path = OUTPUTS / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            block = rec[sub] if sub else rec
            yield fname, rec["document_id"], block["generated_field"]["text"]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    except Exception as e:
        return f"UNKNOWN ({e!r})"


def main() -> int:
    log_lines = []

    def log(msg):
        print(msg, flush=True)
        log_lines.append(msg)

    log("=" * 70)
    log("STEP 6 Phase 4 -- 588-claim natural aggregate evaluation")
    log("=" * 70)

    config = yaml.safe_load((PROTOTYPE_DIR / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root_for_loader = PROTOTYPE_DIR.parent.parent
    exact_index, all_usable = load_usable_evidence_from_config(config, repo_root_for_loader)
    log(f"Current production evidence pool loaded: {len(all_usable)} usable records "
        f"(use_evidence_v1={config['use_evidence_v1']})")

    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]
    premise_framing = config["verification"]["premise_framing"]
    log(f"Production premise_framing: {premise_framing}")

    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except Exception:
        cuda_available = False
    log(f"NVIDIA GPU available = {'YES' if cuda_available else 'NO'}")

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device="cpu",
    )
    log("Loading real DeBERTa verifier on device=cpu ...")
    t_load = time.time()
    verifier.load()
    log(f"Loaded in {time.time() - t_load:.1f}s")

    seen_texts = set()
    n_texts = 0
    rows = []
    t0 = time.time()

    for fname, doc_id, text in iter_generated_texts():
        if text in seen_texts:
            continue
        seen_texts.add(text)
        n_texts += 1
        for claim in claim_parser.extract_claims(text):
            cit = claim.citation_extracted
            match = (
                match_evidence(cit, exact_index, all_usable, fuzzy_threshold)
                if cit else match_evidence(claim_parser.ExtractedCitation("", "", None, None, ""), exact_index, all_usable)
            )
            row = {
                "input_id": f"{fname}::{doc_id}::{claim.claim_id}",
                "source_file": fname,
                "document_id": doc_id,
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "citation_extracted": cit.as_dict() if cit else None,
                "evidence_found": match.matched,
                "evidence_match_method": match.match_method,
                "evidence_id": match.evidence.dataset_citation_key if match.evidence else None,
                "verdict": None,
                "confidence": None,
                "sub_reason": None,
                "execution_status": "not_verified_no_evidence" if not match.matched else None,
                "failure_reason": None,
            }
            if match.matched:
                try:
                    premise = format_premise(
                        match.evidence.canonical_text, framing=premise_framing,
                        provision_type=match.evidence.provision_type,
                        provision_number=match.evidence.provision_number,
                        act=match.evidence.act,
                    )
                    r = verifier.verify(premise, claim.claim_text)
                    row["verdict"] = r.label
                    row["confidence"] = r.confidence
                    row["sub_reason"] = r.sub_reason
                    row["execution_status"] = "verified"
                except Exception as e:
                    row["execution_status"] = "verification_error"
                    row["failure_reason"] = repr(e)
            else:
                row["verdict"] = NO_EVIDENCE
            rows.append(row)

    elapsed = time.time() - t0
    n_claims = len(rows)
    log(f"\nDistinct generated texts scanned: {n_texts}")
    log(f"Total claims: {n_claims}")

    pred_path = OUT_DIR / "claims_588_results.jsonl"
    with pred_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"Wrote {pred_path}")

    # ---- Legitimate metrics only (per METRIC_DEFINITIONS.md) ----
    n_matched = sum(1 for r in rows if r["evidence_found"])
    coverage = n_matched / n_claims if n_claims else 0.0
    no_evidence_rate = 1 - coverage

    verdict_counts = Counter(r["verdict"] for r in rows)
    n_errors = sum(1 for r in rows if r["execution_status"] == "verification_error")

    confidences_all = [r["confidence"] for r in rows if r["confidence"] is not None]
    confidences_by_verdict = {}
    for v in ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"):
        vals = [r["confidence"] for r in rows if r["verdict"] == v and r["confidence"] is not None]
        if vals:
            confidences_by_verdict[v] = {
                "n": len(vals), "mean": statistics.mean(vals), "median": statistics.median(vals),
                "min": min(vals), "max": max(vals),
            }

    metrics = {
        "dataset_tag": "588_claim_natural_aggregate",
        "classification": "METRIC-ONLY -- no independent correctness labels",
        "n_distinct_texts": n_texts,
        "n_claims": n_claims,
        "n_evidence_matched": n_matched,
        "evidence_coverage": coverage,
        "no_evidence_rate": no_evidence_rate,
        "verdict_distribution": dict(verdict_counts),
        "n_verification_errors": n_errors,
        "confidence_overall": {
            "n": len(confidences_all),
            "mean": statistics.mean(confidences_all) if confidences_all else None,
            "median": statistics.median(confidences_all) if confidences_all else None,
        } if confidences_all else None,
        "confidence_by_verdict": confidences_by_verdict,
        "config": {
            "use_evidence_v1": config["use_evidence_v1"],
            "premise_framing": premise_framing,
            "confidence_threshold": config["verification"]["confidence_threshold"],
            "evidence_pool_size": len(all_usable),
        },
        "elapsed_seconds": elapsed,
        "gpu_execution_claimed": False,
        "qwen_generation_or_correction_invoked": False,
        "device": "cpu",
        "cuda_available": cuda_available,
    }
    (OUT_DIR / "claims_588_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"Wrote {OUT_DIR / 'claims_588_metrics.json'}")

    log(f"\nEvidence coverage: {coverage:.4f} ({n_matched}/{n_claims})")
    log(f"Verdict distribution: {dict(verdict_counts)}")

    run_meta = {
        "produced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repo_commit": git_commit(),
        "python_version": platform.python_version(),
        "command_executed": "research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/run_natural_588_evaluation.py",
        "source_files": [f for f, _ in SOURCES],
        "config_path": "research/prototype/config/prototype.yaml",
        "nvidia_gpu_available": False,
        "cuda_available_per_torch": cuda_available,
        "qwen_generation_or_correction_invoked": False,
        "model_identifier": config["verification"]["model_id"],
        "result_classification": "FRESH TESTING RESULT (claim parsing, evidence matching, and NLI verification freshly computed this run; underlying generated text is historical, from a prior GPU session)",
    }
    (OUT_DIR / "run_metadata.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Wrote {OUT_DIR / 'run_metadata.json'}")

    (OUT_DIR / "execution_log.txt").write_text("\n".join(log_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
