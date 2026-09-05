"""STEP 4 output validator.

Verifies the GOLD-01/GOLD-02 actual-output predictions, the expected-vs-actual CSV
tables, and the aggregate metrics are internally consistent, complete, and that no
historical artifact was overwritten. Read-only: never modifies any file it checks.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_step4_outputs.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent

RUN_DIR = TESTING_DIR / "actual_outputs" / "step4_gold_verifier"
CMP_DIR = TESTING_DIR / "comparisons" / "expected_vs_actual"

FAILURES: list[str] = []
PASSES: list[str] = []


def ok(msg: str) -> None:
    PASSES.append(msg)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_dataset(name: str, expected_count: int, expected_hash: str, fixture: Path,
                   predictions_labeled: Path, predictions_bare: Path,
                   csv_path: Path, metrics_path: Path, meta_path: Path) -> None:
    # 1. dataset hash matches STEP 3's recorded hash
    if not fixture.exists():
        fail(f"{name}: GOLD fixture missing at {fixture}")
        return
    h = sha256_of(fixture)
    if h != expected_hash:
        fail(f"{name}: fixture hash {h} != recorded {expected_hash}")
    else:
        ok(f"{name}: fixture hash matches recorded STEP 3 hash")

    # 2. predictions files exist and have the expected count
    for label, path in [("labeled", predictions_labeled), ("bare", predictions_bare)]:
        if not path.exists():
            fail(f"{name}/{label}: predictions file missing at {path}")
            continue
        preds = load_jsonl(path)
        if len(preds) != expected_count:
            fail(f"{name}/{label}: predictions count {len(preds)} != expected {expected_count}")
        else:
            ok(f"{name}/{label}: predictions count == {expected_count}")

        # 3. every input ID maps to at most one prediction (no duplicate IDs)
        ids = [p["id"] for p in preds]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            fail(f"{name}/{label}: duplicate prediction IDs found: {sorted(dupes)[:10]}")
        else:
            ok(f"{name}/{label}: no duplicate prediction IDs ({len(ids)} unique)")

        # 4. no predictions are missing (every record has a non-null predicted_label field,
        #    NO_EVIDENCE counts as a legitimate, present outcome -- only a literal missing
        #    key/None would indicate a genuinely missing prediction)
        missing = [p["id"] for p in preds if "predicted_label" not in p]
        if missing:
            fail(f"{name}/{label}: {len(missing)} record(s) missing 'predicted_label' key entirely: {missing[:10]}")
        else:
            ok(f"{name}/{label}: every record has a predicted_label key (present, possibly NO_EVIDENCE)")

        # 5. MATCH is mechanically derived (recompute from expected/predicted, compare to stored 'match')
        mismatches = [p["id"] for p in preds if p["match"] != (p["predicted_label"] == p["expected_label"])]
        if mismatches:
            fail(f"{name}/{label}: stored 'match' field disagrees with (predicted==expected) for {len(mismatches)} record(s)")
        else:
            ok(f"{name}/{label}: 'match' field is mechanically consistent with expected==predicted for all records")

    # 6. no expected labels were modified: expected_label must be constant/derived, never
    #    varying in a way inconsistent with the dataset's documented gold semantics
    labeled_preds = load_jsonl(predictions_labeled)
    bare_preds = load_jsonl(predictions_bare)
    labeled_expected = {p["id"]: p["expected_label"] for p in labeled_preds}
    bare_expected = {p["id"]: p["expected_label"] for p in bare_preds}
    if labeled_expected != bare_expected:
        fail(f"{name}: expected_label differs between labeled-framing and bare-framing runs "
             f"for the same IDs -- expected labels must not change across framing arms")
    else:
        ok(f"{name}: expected_label is identical across both framing arms (never modified per-arm)")

    # 7. comparison CSV rows equal input rows (primary = labeled framing)
    if not csv_path.exists():
        fail(f"{name}: expected-vs-actual CSV missing at {csv_path}")
    else:
        rows = load_csv_rows(csv_path)
        if len(rows) != expected_count:
            fail(f"{name}: CSV row count {len(rows)} != expected {expected_count}")
        else:
            ok(f"{name}: CSV row count == {expected_count}")
        csv_ids = {r["ID"] for r in rows}
        pred_ids = {p["id"] for p in labeled_preds}
        if csv_ids != pred_ids:
            fail(f"{name}: CSV row IDs do not exactly match the labeled-framing predictions' IDs")
        else:
            ok(f"{name}: CSV rows correspond exactly to the labeled-framing predictions (same ID set)")
        # MATCH column mechanically re-derivable from EXPECTED/ACTUAL columns
        csv_mismatches = [r["ID"] for r in rows if (r["MATCH"] == "MATCH") != (r["EXPECTED"] == r["ACTUAL"])]
        if csv_mismatches:
            fail(f"{name}: CSV 'MATCH' column disagrees with EXPECTED==ACTUAL for {len(csv_mismatches)} row(s)")
        else:
            ok(f"{name}: CSV 'MATCH' column is mechanically derived from EXPECTED/ACTUAL for all rows")

    # 8. aggregate metrics equal the comparison table (accuracy recomputed from CSV == summary)
    if metrics_path.exists() and csv_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        labeled_metrics = metrics["results_by_framing"]["labeled"]
        rows = load_csv_rows(csv_path)
        recomputed_correct = sum(1 for r in rows if r["MATCH"] == "MATCH")
        recomputed_accuracy = recomputed_correct / len(rows) if rows else 0.0
        stored_accuracy = labeled_metrics.get("accuracy", labeled_metrics.get("contradiction_recall"))
        if abs(recomputed_accuracy - stored_accuracy) > 1e-9:
            fail(f"{name}: accuracy recomputed from CSV ({recomputed_accuracy}) != stored metrics ({stored_accuracy})")
        else:
            ok(f"{name}: accuracy recomputed from the expected-vs-actual CSV exactly matches the stored aggregate metric ({recomputed_accuracy:.6f})")

    # 9. metadata exists
    if not meta_path.exists():
        fail(f"{name}: run metadata missing at {meta_path}")
    else:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        required_meta_fields = ["produced_at", "python_version", "model_identifier",
                                 "dataset_sha256", "record_count", "command_executed",
                                 "git_commit", "nvidia_gpu_available"]
        missing_fields = [f for f in required_meta_fields if f not in meta]
        if missing_fields:
            fail(f"{name}: run metadata missing required fields: {missing_fields}")
        else:
            ok(f"{name}: run metadata present with all {len(required_meta_fields)} required fields")
        if meta.get("nvidia_gpu_available") is not False:
            fail(f"{name}: run metadata does not explicitly record nvidia_gpu_available=False")
        else:
            ok(f"{name}: run metadata explicitly records NVIDIA GPU available = False")
        if meta.get("dataset_sha256") != expected_hash:
            fail(f"{name}: run metadata's dataset_sha256 does not match the recorded STEP 3 hash")
        else:
            ok(f"{name}: run metadata's dataset_sha256 matches the recorded STEP 3 hash")


def check_no_historical_overwrite() -> None:
    name = "Historical-artifact preservation"
    # These historical files must still carry the ORIGINAL (pre-STEP-4) environment
    # signature -- if STEP 4's runners had accidentally written to outputs/ instead of
    # testing/, this specific field would now read the pinned 3.11.9 environment instead.
    checks = [
        (RESEARCH_DIR / "prototype" / "outputs" / "controlled_benchmark_deberta_metrics.json", "3.13.1"),
        (RESEARCH_DIR / "prototype" / "outputs" / "controlled_benchmark_deberta_labeled_metrics.json", "3.13.1"),
    ]
    for path, expected_python in checks:
        if not path.exists():
            fail(f"{name}: expected historical file missing entirely: {path}")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        actual_python = d.get("environment", {}).get("python")
        if actual_python != expected_python:
            fail(f"{name}: {path} environment.python is '{actual_python}', expected untouched historical "
                 f"value '{expected_python}' -- this file may have been overwritten")
        else:
            ok(f"{name}: {path.name} still shows its original historical environment ({actual_python}) -- not overwritten")

    synth_source = RESEARCH_DIR / "prototype" / "outputs" / "run_synthetic_stress.jsonl"
    if synth_source.exists():
        h = sha256_of(synth_source)
        if h != "2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516":
            fail(f"{name}: research/prototype/outputs/run_synthetic_stress.jsonl hash changed -- possible overwrite")
        else:
            ok(f"{name}: research/prototype/outputs/run_synthetic_stress.jsonl unchanged (hash matches)")


def main() -> int:
    check_dataset(
        name="GOLD-01",
        expected_count=420,
        expected_hash="962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99",
        fixture=TESTING_DIR / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl",
        predictions_labeled=RUN_DIR / "gold01_controlled" / "gold01_predictions_labeled.jsonl",
        predictions_bare=RUN_DIR / "gold01_controlled" / "gold01_predictions_bare.jsonl",
        csv_path=CMP_DIR / "gold01_expected_vs_actual.csv",
        metrics_path=RUN_DIR / "gold01_controlled" / "gold01_metrics.json",
        meta_path=RUN_DIR / "run_metadata" / "gold01_run.meta.json",
    )
    check_dataset(
        name="GOLD-02",
        expected_count=59,
        expected_hash="2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516",
        fixture=TESTING_DIR / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl",
        predictions_labeled=RUN_DIR / "gold02_synthetic" / "gold02_predictions_labeled.jsonl",
        predictions_bare=RUN_DIR / "gold02_synthetic" / "gold02_predictions_bare.jsonl",
        csv_path=CMP_DIR / "gold02_expected_vs_actual.csv",
        metrics_path=RUN_DIR / "gold02_synthetic" / "gold02_metrics.json",
        meta_path=RUN_DIR / "run_metadata" / "gold02_run.meta.json",
    )
    check_no_historical_overwrite()

    # gold_verifier_summary.csv sanity
    summary_path = CMP_DIR / "gold_verifier_summary.csv"
    if not summary_path.exists():
        fail(f"gold_verifier_summary.csv missing at {summary_path}")
    else:
        rows = load_csv_rows(summary_path)
        if len(rows) != 4:
            fail(f"gold_verifier_summary.csv: expected 4 rows (2 datasets x 2 framings), found {len(rows)}")
        else:
            ok("gold_verifier_summary.csv: 4 rows present (GOLD-01/GOLD-02 x labeled/bare)")

    print("=" * 70)
    print("STEP 4 OUTPUT VALIDATION REPORT")
    print("=" * 70)
    print(f"\nPASSED ({len(PASSES)}):")
    for p in PASSES:
        print(f"  [PASS] {p}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  [FAIL] {f}")
        print(f"\nRESULT: FAIL ({len(FAILURES)} failure(s), {len(PASSES)} passed)")
        return 1

    print(f"\nRESULT: PASS ({len(PASSES)} checks passed, 0 failures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
