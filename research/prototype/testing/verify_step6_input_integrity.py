"""STEP 6 Phase 2 -- verify natural-data input integrity before running any inference.

Checks record counts, duplicate IDs, and SHA-256 hashes for every natural-data source
file in scope. Where a hash was already recorded in an earlier step (STEP 3's
MANIFEST.md / inputs/README.md), compares against it and STOPS (reports, does not
proceed silently) on any mismatch. For files never hashed before (the natural-batch
data files themselves -- STEP 3 explicitly did not hash these, only small fixtures),
records a fresh baseline hash for this step, clearly labeled as such rather than a
"comparison."

Read-only: modifies nothing.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/verify_step6_input_integrity.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"

OUT_DIR = TESTING_DIR / "evaluation" / "input_integrity"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Files with a hash already recorded in STEP 3 (testing/MANIFEST.md / inputs/README.md)
PREVIOUSLY_RECORDED_HASHES = {
    "natural_candidate_selected_ids_30.json": "182b45703c8efdf1d871d8be2fb2ff4222b6cb72f90b0bf6a0f54fc329d4f3cb",
    "natural_candidate_selected_ids_50.json": "ba0458778b2e76a50df54cc2d78f04ba5a25fc41fa2921ad78d363b3da3d3d09",
    "natural_candidate_selected_ids_50_batch2.json": "4e65d310fefd9f458546f1bc50c99dc85026d4b51a343c747ef7f05ee4ff7828",
    "natural_candidate_selected_ids_50_final_validation.json": "954380e7695ceead984d67e7029186074a9ffd95130f02d17b01ea08d9877f9a",
}

# Natural-data files in scope for STEP 6, with expected record counts (from STEP 0/1/3)
FILES_IN_SCOPE = {
    "run_A_n30.jsonl": 30,
    "run_natural_targeted.jsonl": 11,
    "natural_candidates_50_gpu_bare.jsonl": 50,
    "natural_candidates_50_gpu_labeled.jsonl": 50,
    "natural_candidates_batch2_gpu_bare.jsonl": 50,
    "natural_candidates_batch2_gpu_labeled.jsonl": 50,
    "final_gpu_validation_A.jsonl": 50,
    "final_gpu_validation_B.jsonl": 50,
    "natural_candidate_selected_ids_30.json": None,
    "natural_candidate_selected_ids_50.json": None,
    "natural_candidate_selected_ids_50_batch2.json": None,
    "natural_candidate_selected_ids_50_final_validation.json": None,
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_records(path: Path):
    if path.suffix == ".jsonl":
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    report = {"files": [], "stop_on_discrepancy": False, "discrepancies": []}
    log_lines = []

    def log(msg):
        print(msg, flush=True)
        log_lines.append(msg)

    log("=" * 70)
    log("STEP 6 Phase 2 -- natural-data input integrity check")
    log("=" * 70)

    for fname, expected_count in FILES_IN_SCOPE.items():
        path = OUTPUTS / fname
        entry = {"file": fname, "path": str(path.relative_to(REPO_ROOT))}
        if not path.exists():
            entry["status"] = "MISSING"
            log(f"[MISSING] {fname}")
            report["discrepancies"].append(f"{fname} is missing entirely")
            report["files"].append(entry)
            continue

        h = sha256_of(path)
        entry["sha256"] = h

        if fname in PREVIOUSLY_RECORDED_HASHES:
            expected_hash = PREVIOUSLY_RECORDED_HASHES[fname]
            entry["comparison"] = "against STEP 3 recorded hash"
            entry["expected_hash"] = expected_hash
            if h != expected_hash:
                entry["status"] = "HASH MISMATCH -- STOP"
                report["stop_on_discrepancy"] = True
                report["discrepancies"].append(f"{fname}: hash {h} != STEP 3 recorded {expected_hash}")
                log(f"[MISMATCH] {fname}: {h} != {expected_hash}")
            else:
                entry["status"] = "unchanged since STEP 3"
                log(f"[OK] {fname}: hash matches STEP 3 record")
        else:
            entry["comparison"] = "no prior recorded hash -- this is the fresh STEP 6 baseline"
            entry["status"] = "baseline recorded (no prior hash to compare)"
            log(f"[BASELINE] {fname}: {h} (no prior hash recorded in STEP 3 for this file)")

        # record count + duplicate-ID check
        try:
            records = load_records(path)
        except Exception as e:
            entry["status"] = f"UNREADABLE: {e!r}"
            report["discrepancies"].append(f"{fname}: failed to parse ({e!r})")
            report["files"].append(entry)
            continue

        n = len(records)
        entry["record_count"] = n
        if expected_count is not None and n != expected_count:
            entry["status"] = "RECORD COUNT MISMATCH -- STOP"
            report["stop_on_discrepancy"] = True
            report["discrepancies"].append(f"{fname}: {n} records, expected {expected_count}")
            log(f"[MISMATCH] {fname}: {n} records, expected {expected_count}")
        elif expected_count is not None:
            log(f"[OK] {fname}: {n} records (matches expected)")

        if isinstance(records, list) and records and isinstance(records[0], dict) and "document_id" in records[0]:
            ids = [r["document_id"] for r in records]
            dupes = {x for x in ids if ids.count(x) > 1}
            entry["duplicate_document_ids"] = sorted(dupes)
            if dupes:
                log(f"[WARN] {fname}: duplicate document_id values: {sorted(dupes)}")
            else:
                log(f"[OK] {fname}: no duplicate document_id values ({len(ids)} unique)")

        report["files"].append(entry)

    if report["stop_on_discrepancy"]:
        log("\nSTOP: one or more discrepancies found. Not proceeding to inference for the "
            "affected dataset(s). See 'discrepancies' in hash_report.json.")

    (OUT_DIR / "hash_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT_DIR / "validation_log.txt").write_text("\n".join(log_lines), encoding="utf-8")
    log(f"\nWrote {OUT_DIR / 'hash_report.json'}")
    log(f"Wrote {OUT_DIR / 'validation_log.txt'}")

    return 1 if report["stop_on_discrepancy"] else 0


if __name__ == "__main__":
    sys.exit(main())
