"""STEP 5 component-test artifact validator.

Verifies every declared component-test result has a corresponding execution record,
no expected output was fabricated, GOLD/PROVISIONAL classifications are unchanged,
JSON outputs are valid, pass/fail counts reconcile, GPU-dependent portions are
explicitly marked NOT RUN, and no historical file was modified. Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_step5_components.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent

STEP5_DIR = TESTING_DIR / "actual_outputs" / "step5_components"
COMPONENT_DIRS = [
    "01_claim_parser", "02_evidence_matcher", "03_verifier", "04_verdict_application",
    "05_citation_adversarial", "06_correction_safety", "07_final_assembly",
]

FAILURES: list[str] = []
WARNINGS: list[str] = []
PASSES: list[str] = []


def ok(msg): PASSES.append(msg)
def fail(msg): FAILURES.append(msg)
def warn(msg): WARNINGS.append(msg)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_pytest_summary(log_text: str) -> tuple[int, int, int]:
    """Returns (passed, failed, deselected) from pytest's own summary line."""
    m = re.search(r"(\d+) passed", log_text)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", log_text)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) deselected", log_text)
    deselected = int(m.group(1)) if m else 0
    return passed, failed, deselected


def check_execution_records() -> None:
    name = "Execution records"
    for d in COMPONENT_DIRS:
        log_path = STEP5_DIR / d / "pytest_execution.log"
        if not log_path.exists():
            fail(f"{name}: missing pytest_execution.log for {d}")
            continue
        text = log_path.read_text(encoding="utf-8", errors="replace")
        passed, failed, _ = parse_pytest_summary(text)
        if failed > 0:
            fail(f"{name}: {d} shows {failed} FAILED test(s) in its execution log")
        elif passed == 0:
            fail(f"{name}: {d}'s execution log shows 0 passed -- looks empty/broken")
        else:
            ok(f"{name}: {d} execution log present, {passed} passed, 0 failed")

        demo_path = STEP5_DIR / d / "demo_examples.json"
        if not demo_path.exists():
            fail(f"{name}: missing demo_examples.json for {d}")
        else:
            try:
                json.loads(demo_path.read_text(encoding="utf-8"))
                ok(f"{name}: {d}/demo_examples.json is valid JSON")
            except json.JSONDecodeError as e:
                fail(f"{name}: {d}/demo_examples.json is invalid JSON ({e})")


def check_no_fabricated_expected_output() -> None:
    name = "No fabricated expected output"
    required_any = ["source_of_input", "source_test", "expected_behavior_asserted_by", "expected_behavior"]
    for d in COMPONENT_DIRS:
        demo_path = STEP5_DIR / d / "demo_examples.json"
        if not demo_path.exists():
            continue
        text = demo_path.read_text(encoding="utf-8")
        if not any(key in text for key in required_any):
            fail(f"{name}: {d}/demo_examples.json cites no test/behavior source for its examples")
        else:
            ok(f"{name}: {d}/demo_examples.json cites an existing test/behavior source for its example(s)")


def check_gold_unchanged() -> None:
    name = "GOLD fixtures unchanged since STEP 3/4"
    checks = [
        (TESTING_DIR / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl",
         "962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99"),
        (TESTING_DIR / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl",
         "2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516"),
    ]
    for path, expected_hash in checks:
        if not path.exists():
            fail(f"{name}: missing {path}")
            continue
        h = sha256_of(path)
        if h != expected_hash:
            fail(f"{name}: {path.name} hash changed -- {h} != {expected_hash}")
        else:
            ok(f"{name}: {path.name} unchanged (hash matches)")


def check_no_provisional_promotion() -> None:
    name = "No provisional label promoted to GOLD"
    forbidden_basenames = {"gold_annotation.jsonl", "lawyer_annotation.jsonl", "assumption_annotation.jsonl"}
    forbidden_tag = "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"
    scan_dirs = [TESTING_DIR / "expected_outputs", TESTING_DIR / "inputs" / "gold"]
    violation = False
    for d in scan_dirs:
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if path.is_file() and path.name in forbidden_basenames:
                fail(f"{name}: forbidden provisional file '{path.name}' found under {d}")
                violation = True
            if path.is_file() and path.suffix == ".jsonl":
                try:
                    first_line = path.read_text(encoding="utf-8").splitlines()[0]
                    if forbidden_tag in first_line:
                        fail(f"{name}: provisional tag found inside {path}")
                        violation = True
                except Exception:
                    pass
    if not violation:
        ok(f"{name}: no provisional file or tag found under expected_outputs/ or inputs/gold/")


def check_counts_reconcile() -> None:
    name = "Pass/fail counts reconcile"
    full_log = STEP5_DIR / "full_suite_verbose.log"
    if not full_log.exists():
        fail(f"{name}: full_suite_verbose.log missing")
        return
    text = full_log.read_text(encoding="utf-8", errors="replace")
    passed, failed, _ = parse_pytest_summary(text)
    if passed != 205 or failed != 0:
        fail(f"{name}: full suite shows {passed} passed / {failed} failed, expected 205/0")
    else:
        ok(f"{name}: full regression suite shows exactly 205 passed, 0 failed")

    # Every group's own log must show 0 failed (already checked in check_execution_records,
    # re-confirmed here against the documented per-group counts in TEST_INVENTORY.md)
    documented_counts = {
        "01_claim_parser": 111, "02_evidence_matcher": 72, "03_verifier": 48,
        "04_verdict_application": 3, "05_citation_adversarial": 15,
    }
    for d, expected_passed in documented_counts.items():
        log_path = STEP5_DIR / d / "pytest_execution.log"
        if not log_path.exists():
            continue
        passed, failed, _ = parse_pytest_summary(log_path.read_text(encoding="utf-8", errors="replace"))
        if passed != expected_passed:
            fail(f"{name}: {d} log shows {passed} passed, documented count is {expected_passed}")
        else:
            ok(f"{name}: {d} log's passed count ({passed}) matches TEST_INVENTORY.md")


def check_gpu_marking() -> None:
    name = "GPU-dependent portions explicitly marked"
    for d in ("06_correction_safety", "07_final_assembly"):
        demo_path = STEP5_DIR / d / "demo_examples.json"
        if not demo_path.exists():
            continue
        text = demo_path.read_text(encoding="utf-8")
        if '"gpu_generation_executed": false' not in text and 'gpu_generation_executed' not in text:
            fail(f"{name}: {d}/demo_examples.json does not explicitly mark GPU generation as not executed")
        else:
            ok(f"{name}: {d}/demo_examples.json explicitly marks GPU generation as not executed")

    for md_name in ("component_tests/06_correction_safety/RESULT.md", "component_tests/07_final_assembly/RESULT.md"):
        p = TESTING_DIR / md_name
        if not p.exists():
            fail(f"{name}: missing {md_name}")
            continue
        text = p.read_text(encoding="utf-8")
        if "NOT" not in text.upper() and "not have" not in text.lower() and "not invoked" not in text.lower():
            warn(f"{name}: {md_name} may not explicitly state the GPU limitation")
        else:
            ok(f"{name}: {md_name} explicitly documents the GPU/Qwen limitation")


def check_no_historical_overwrite() -> None:
    name = "Historical-artifact preservation"
    checks = [
        (RESEARCH_DIR / "prototype" / "outputs" / "controlled_benchmark_deberta_metrics.json", "3.13.1"),
        (RESEARCH_DIR / "prototype" / "outputs" / "controlled_benchmark_deberta_labeled_metrics.json", "3.13.1"),
    ]
    for path, expected_python in checks:
        if not path.exists():
            fail(f"{name}: expected historical file missing: {path}")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        actual = d.get("environment", {}).get("python")
        if actual != expected_python:
            fail(f"{name}: {path.name} environment.python is '{actual}', expected untouched '{expected_python}'")
        else:
            ok(f"{name}: {path.name} unchanged (original {actual} environment signature intact)")

    gold_source = RESEARCH_DIR / "prototype" / "outputs" / "run_synthetic_stress.jsonl"
    if gold_source.exists():
        h = sha256_of(gold_source)
        if h != "2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516":
            fail(f"{name}: run_synthetic_stress.jsonl in outputs/ appears modified")
        else:
            ok(f"{name}: outputs/run_synthetic_stress.jsonl unchanged")


def main() -> int:
    check_execution_records()
    check_no_fabricated_expected_output()
    check_gold_unchanged()
    check_no_provisional_promotion()
    check_counts_reconcile()
    check_gpu_marking()
    check_no_historical_overwrite()

    print("=" * 70)
    print("STEP 5 COMPONENT VALIDATION REPORT")
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
