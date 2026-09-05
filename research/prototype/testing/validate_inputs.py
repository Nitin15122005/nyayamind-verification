"""STEP 3 input-layer validator.

Loads every testing input this workspace intends to use, validates structure/required
fields/record counts, checks for duplicate IDs, verifies the two GOLD fixture hashes,
and confirms no provisional annotation file has been promoted into a GOLD/expected_output
location. Read-only: never writes to any source dataset. Uses only the standard library
so it runs in the exact pinned venv with no extra dependencies.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_inputs.py
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

FAILURES: list[str] = []
WARNINGS: list[str] = []
PASSES: list[str] = []


def ok(msg: str) -> None:
    PASSES.append(msg)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                fail(f"{path}: line {i} is not valid JSON ({e})")
    return records


def check_duplicate_ids(records: list[dict], id_field: str, dataset_name: str) -> None:
    ids = [r.get(id_field) for r in records if id_field in r]
    if len(ids) != len(records):
        warn(f"{dataset_name}: {len(records) - len(ids)} record(s) missing '{id_field}'")
    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        fail(f"{dataset_name}: duplicate '{id_field}' values found: {sorted(dupes)[:10]}")
    else:
        ok(f"{dataset_name}: no duplicate '{id_field}' values among {len(ids)} IDs")


def require_fields(records: list[dict], fields: list[str], dataset_name: str) -> None:
    missing_counts = {f: 0 for f in fields}
    for r in records:
        for f in fields:
            if f not in r:
                missing_counts[f] += 1
    any_missing = False
    for f, count in missing_counts.items():
        if count:
            fail(f"{dataset_name}: field '{f}' missing on {count}/{len(records)} records")
            any_missing = True
    if not any_missing:
        ok(f"{dataset_name}: all {len(fields)} required fields present on all {len(records)} records")


# ---------------------------------------------------------------------------
# 1. GOLD-01: Controlled NLI benchmark (n=420)
# ---------------------------------------------------------------------------

def check_gold_01() -> None:
    name = "GOLD-01 (controlled_verifier_benchmark.jsonl)"
    fixture = TESTING_DIR / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl"
    source = RESEARCH_DIR / "prototype" / "outputs" / "controlled_verifier_benchmark.jsonl"
    expected_hash = "962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99"

    if not fixture.exists():
        fail(f"{name}: fixture missing at {fixture}")
        return
    if not source.exists():
        fail(f"{name}: frozen source missing at {source}")
        return

    fixture_hash = sha256_of(fixture)
    source_hash = sha256_of(source)

    if fixture_hash != expected_hash:
        fail(f"{name}: fixture hash {fixture_hash} != recorded hash {expected_hash}")
    else:
        ok(f"{name}: fixture hash matches recorded hash ({expected_hash[:16]}...)")

    if fixture_hash != source_hash:
        fail(f"{name}: fixture is NOT byte-identical to frozen source (fixture={fixture_hash[:16]}..., source={source_hash[:16]}...)")
    else:
        ok(f"{name}: fixture is byte-identical to frozen source")

    records = load_jsonl(fixture)
    if len(records) != 420:
        fail(f"{name}: expected 420 records, found {len(records)}")
    else:
        ok(f"{name}: record count == 420")

    require_fields(
        records,
        ["benchmark_id", "expected_label", "evidence_text", "hypothesis", "condition"],
        name,
    )
    check_duplicate_ids(records, "benchmark_id", name)

    valid_labels = {"ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION", "NEUTRAL"}
    bad_labels = {r.get("expected_label") for r in records} - valid_labels
    if bad_labels:
        warn(f"{name}: unexpected expected_label values found: {bad_labels}")
    else:
        ok(f"{name}: all expected_label values are within the known label set")


# ---------------------------------------------------------------------------
# 2. GOLD-02: Synthetic stress set (n=59)
# ---------------------------------------------------------------------------

def check_gold_02() -> None:
    name = "GOLD-02 (run_synthetic_stress.jsonl)"
    fixture = TESTING_DIR / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl"
    source = RESEARCH_DIR / "prototype" / "outputs" / "run_synthetic_stress.jsonl"
    expected_hash = "2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516"

    if not fixture.exists():
        fail(f"{name}: fixture missing at {fixture}")
        return
    if not source.exists():
        fail(f"{name}: frozen source missing at {source}")
        return

    fixture_hash = sha256_of(fixture)
    source_hash = sha256_of(source)

    if fixture_hash != expected_hash:
        fail(f"{name}: fixture hash {fixture_hash} != recorded hash {expected_hash}")
    else:
        ok(f"{name}: fixture hash matches recorded hash ({expected_hash[:16]}...)")

    if fixture_hash != source_hash:
        fail(f"{name}: fixture is NOT byte-identical to frozen source")
    else:
        ok(f"{name}: fixture is byte-identical to frozen source")

    records = load_jsonl(fixture)
    if len(records) != 59:
        fail(f"{name}: expected 59 records, found {len(records)}")
    else:
        ok(f"{name}: record count == 59")

    require_fields(
        records,
        ["synthetic_claim_id", "evidence_id", "canonical_evidence_text", "original_synthetic_text", "transform_rule"],
        name,
    )
    check_duplicate_ids(records, "synthetic_claim_id", name)


# ---------------------------------------------------------------------------
# 3. Evidence corpus (referenced in place, v0 + v1 + merged pool)
# ---------------------------------------------------------------------------

def check_evidence_corpus() -> None:
    name = "Evidence corpus (v0/v1, referenced in place)"
    v0 = RESEARCH_DIR / "data" / "evidence" / "canonical_statutes.jsonl"
    v0_audit = RESEARCH_DIR / "data" / "evidence" / "evidence_audit.jsonl"
    v1 = RESEARCH_DIR / "data" / "evidence" / "canonical_statutes_v1.jsonl"
    v1_audit = RESEARCH_DIR / "data" / "evidence" / "evidence_audit_v1.jsonl"

    for path, expected_count in [(v0, 63), (v0_audit, 63), (v1, 82), (v1_audit, 82)]:
        if not path.exists():
            fail(f"{name}: missing {path}")
            continue
        records = load_jsonl(path)
        if len(records) != expected_count:
            fail(f"{name}: {path.name} expected {expected_count} records, found {len(records)}")
        else:
            ok(f"{name}: {path.name} record count == {expected_count}")
        check_duplicate_ids(records, "dataset_citation_key", f"{name}/{path.name}")

    # Verify the merged, production usable-evidence pool via the real loader (no source modified).
    sys.path.insert(0, str(PROTOTYPE_DIR))
    try:
        import yaml  # noqa: WPS433 (local import, optional dependency check)
        from src.data_loader import load_usable_evidence_from_config  # noqa: WPS433

        config_path = PROTOTYPE_DIR / "config" / "prototype.yaml"
        cfg = yaml.safe_load(open(config_path, encoding="utf-8"))
        _, pool = load_usable_evidence_from_config(cfg, str(REPO_ROOT))
        if len(pool) != 136:
            fail(f"{name}: merged usable pool expected 136 records, loader returned {len(pool)}")
        else:
            ok(f"{name}: merged usable evidence pool (v0+v1) == 136 records, confirmed via live loader")
    except Exception as e:  # pragma: no cover - defensive, reported not swallowed
        fail(f"{name}: could not run load_usable_evidence_from_config: {e!r}")


# ---------------------------------------------------------------------------
# 4. No provisional label promoted to GOLD
# ---------------------------------------------------------------------------

def check_no_provisional_promotion() -> None:
    name = "Provisional-promotion guard"
    forbidden_basenames = {
        "gold_annotation.jsonl",
        "lawyer_annotation.jsonl",
        "assumption_annotation.jsonl",
    }
    forbidden_tag = "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"

    scan_dirs = [
        TESTING_DIR / "expected_outputs",
        TESTING_DIR / "inputs" / "gold",
    ]
    violation_found = False
    for d in scan_dirs:
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if not path.is_file():
                continue
            if path.name in forbidden_basenames:
                fail(f"{name}: forbidden provisional file '{path.name}' found under {d}")
                violation_found = True
            if path.suffix == ".jsonl":
                try:
                    with open(path, encoding="utf-8") as f:
                        first_line = f.readline()
                    if forbidden_tag in first_line:
                        fail(f"{name}: provisional annotation tag found inside {path} (under a GOLD directory)")
                        violation_found = True
                except Exception:
                    pass
    if not violation_found:
        ok(f"{name}: no provisional annotation file or tag found under expected_outputs/ or inputs/gold/")


# ---------------------------------------------------------------------------
# 5. Structural check of referenced METRIC-ONLY / BEHAVIOR sources (existence only,
#    no copying, no promotion of any label)
# ---------------------------------------------------------------------------

def check_referenced_metric_only_sources() -> None:
    name = "Referenced METRIC-ONLY sources (existence + count only)"
    outputs_dir = RESEARCH_DIR / "prototype" / "outputs"
    expected = {
        "final_gpu_validation_A.jsonl": 50,
        "final_gpu_validation_B.jsonl": 50,
        "run_A_n30.jsonl": 30,
        "run_B_n30.jsonl": 30,
        "run_C_n30.jsonl": 30,
        "natural_candidates_50_gpu_bare.jsonl": 50,
        "natural_candidates_batch2_gpu_bare.jsonl": 50,
        "final_gpu_validation_corrections_detail.jsonl": 10,
        "labeled_correction_validation_gpu_corrections_detail.jsonl": 10,
        "natural_candidates_50_gpu_corrections_detail.jsonl": 21,
    }
    for fname, expected_count in expected.items():
        path = outputs_dir / fname
        if not path.exists():
            fail(f"{name}: missing referenced file {path}")
            continue
        records = load_jsonl(path)
        if len(records) != expected_count:
            fail(f"{name}: {fname} expected {expected_count} records, found {len(records)}")
        else:
            ok(f"{name}: {fname} record count == {expected_count}")

    provisional = {
        "gold_annotation.jsonl": 88,
        "lawyer_annotation.jsonl": 88,
        "assumption_annotation.jsonl": 88,
    }
    for fname, expected_count in provisional.items():
        path = outputs_dir / fname
        if not path.exists():
            fail(f"Provisional source check: missing {path}")
            continue
        records = load_jsonl(path)
        if len(records) != expected_count:
            fail(f"Provisional source check: {fname} expected {expected_count} records, found {len(records)}")
        else:
            ok(f"Provisional source check: {fname} record count == {expected_count} (remains PROVISIONAL, not copied)")


# ---------------------------------------------------------------------------
# 6. BEHAVIOR inputs: confirm the cited test files exist and are unmodified in shape
#    (existence + a lightweight sanity count of test functions; never rewrites tests)
# ---------------------------------------------------------------------------

def check_behavior_inputs() -> None:
    name = "BEHAVIOR inputs (test file existence only, no modification)"
    tests_dir = RESEARCH_DIR / "prototype" / "tests"
    expected_min_tests = {
        "test_adversarial_citations.py": 15,
        "test_final_pass_adversarial.py": 10,
        "test_respectively_claims.py": 16,
        "test_claim_parser_bugfixes.py": 20,
    }
    for fname, expected_min in expected_min_tests.items():
        path = tests_dir / fname
        if not path.exists():
            fail(f"{name}: missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        count = text.count("\ndef test_")
        if count < expected_min:
            fail(f"{name}: {fname} has {count} test functions, expected at least {expected_min}")
        else:
            ok(f"{name}: {fname} has {count} test functions (>= {expected_min} expected)")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def main() -> int:
    check_gold_01()
    check_gold_02()
    check_evidence_corpus()
    check_no_provisional_promotion()
    check_referenced_metric_only_sources()
    check_behavior_inputs()

    print("=" * 70)
    print("STEP 3 INPUT VALIDATION REPORT")
    print("=" * 70)
    print(f"\nPASSED ({len(PASSES)}):")
    for p in PASSES:
        print(f"  [PASS] {p}")
    if WARNINGS:
        print(f"\nWARNINGS ({len(WARNINGS)}):")
        for w in WARNINGS:
            print(f"  [WARN] {w}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  [FAIL] {f}")
        print(f"\nRESULT: FAIL ({len(FAILURES)} failure(s), {len(WARNINGS)} warning(s), {len(PASSES)} passed)")
        return 1

    print(f"\nRESULT: PASS ({len(PASSES)} checks passed, {len(WARNINGS)} warning(s), 0 failures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
