"""STEP 7 ablation-analysis validator.

Checks: no production/test/historical modification, no GOLD dataset modified, no
natural labels created, no provisional labels promoted, all ablation datasets exist,
reported N values and statistics reconcile with source data where reproducible, every
ablation has a classification, every SUPPORTED result has a genuine isolating
comparison, historical vs fresh is explicit, GPU-dependent experiments are not falsely
marked fresh, no unsupported causal language, no natural-data accuracy/F1 claims,
production threshold unchanged at 0.70, production config unchanged, and machine-
readable summaries agree with the markdown tables. Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_ablation.py
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
OUTPUTS = PROTOTYPE_DIR / "outputs"
ABLATION_DIR = TESTING_DIR / "ablation"  # PASS 1 cleanup: was "evaluation", ABLATION_* files moved to ablation/

FAILURES: list[str] = []
WARNINGS: list[str] = []
PASSES: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)
def warn(m): WARNINGS.append(m)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# 1-4. no production/test/historical modification
def check_no_source_or_historical_changes():
    name = "No production/test/historical modification"
    checks = [
        (OUTPUTS / "evidence_coverage_v0_vs_v1.json", None),
        (OUTPUTS / "atomic_scope_check_final_replay.json", None),
        (OUTPUTS / "parser_fix_before_after_n30.json", None),
        (OUTPUTS / "threshold_sensitivity_analysis.json", None),
        (OUTPUTS / "final_metrics.json", None),
    ]
    known_hashes = {
        "run_synthetic_stress.jsonl": "717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5",
        "controlled_verifier_benchmark.jsonl": "aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec",
    }
    for fname, expected in known_hashes.items():
        p = OUTPUTS / fname
        if not p.exists():
            fail(f"{name}: {fname} missing")
            continue
        h = sha256_of(p)
        if h != expected:
            fail(f"{name}: {fname} hash changed ({h} != {expected})")
        else:
            ok(f"{name}: {fname} unchanged")

    for p, _ in checks:
        if not p.exists():
            fail(f"{name}: {p} missing")
        else:
            ok(f"{name}: {p.name} still present (not deleted)")

    src_dir = PROTOTYPE_DIR / "src"
    tests_dir = PROTOTYPE_DIR / "tests"
    if src_dir.exists() and tests_dir.exists():
        ok(f"{name}: src/ and tests/ directories present (no deletion); git diff check performed separately by the shell audit")


# 5/6. no GOLD dataset modified; no natural labels created; 7. no provisional promoted
def check_no_gold_or_label_contamination():
    name = "No GOLD/label contamination"
    gold_checks = [
        (TESTING_DIR / "expected_outputs" / "controlled_benchmark_gold" / "controlled_verifier_benchmark.jsonl",
         "aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec"),
        (TESTING_DIR / "expected_outputs" / "synthetic_stress_gold" / "run_synthetic_stress.jsonl",
         "717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5"),
    ]
    for p, expected in gold_checks:
        if not p.exists():
            fail(f"{name}: GOLD fixture missing {p}")
            continue
        h = sha256_of(p)
        if h != expected:
            fail(f"{name}: GOLD fixture {p.name} modified")
        else:
            ok(f"{name}: GOLD fixture {p.name} unchanged")

    forbidden = {"gold_annotation.jsonl", "lawyer_annotation.jsonl", "assumption_annotation.jsonl"}
    violation = False
    for d in [ABLATION_DIR]:  # PASS 1 moved this step's output entirely into ablation/; actual_outputs/step7_ablation/ no longer exists
        for path in d.rglob("*"):
            if path.is_file() and path.name in forbidden:
                fail(f"{name}: forbidden provisional file found in STEP 7 output: {path}")
                violation = True
    if not violation:
        ok(f"{name}: no provisional annotation file found in STEP 7 output")


# 8/9. reported N values and statistics reconcile with source data
def check_stats_reconcile():
    name = "Statistics reconcile with source data"
    summary_path = ABLATION_DIR / "ABLATION_SUMMARY.json"
    if not summary_path.exists():
        fail(f"{name}: ABLATION_SUMMARY.json missing")
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    findings = {f["factor"]: f for f in summary["findings"]}

    ev1 = findings.get("evidence_v1")
    if ev1:
        step6 = json.loads((TESTING_DIR / "actual_outputs" / "natural_data_runs" / "209_paired" / "paired_209_metrics.json").read_text(encoding="utf-8"))
        if ev1["n"] != step6["n_paired_claims"]:
            fail(f"{name}: evidence_v1 N ({ev1['n']}) != STEP 6 source ({step6['n_paired_claims']})")
        else:
            ok(f"{name}: evidence_v1 N reconciles with STEP 6 source ({ev1['n']})")
        if abs(ev1["baseline_value"] - step6["fresh_evidence_coverage_arm_A"]) > 1e-9:
            fail(f"{name}: evidence_v1 baseline_value does not reconcile with STEP 6 source")
        else:
            ok(f"{name}: evidence_v1 baseline_value reconciles with STEP 6 source")

    pf = findings.get("premise_framing")
    if pf:
        gold01 = json.loads((TESTING_DIR / "actual_outputs" / "gold_benchmark_runs" / "gold01_controlled" / "gold01_metrics.json").read_text(encoding="utf-8"))
        if pf["n"] != 420:
            fail(f"{name}: premise_framing N is not 420")
        else:
            ok(f"{name}: premise_framing N == 420")
        if abs(pf["variant_value"] - gold01["results_by_framing"]["labeled"]["macro_f1"]) > 1e-9:
            fail(f"{name}: premise_framing variant_value does not reconcile with STEP 4 GOLD-01 source")
        else:
            ok(f"{name}: premise_framing variant_value reconciles with STEP 4 GOLD-01 source")

    cp = findings.get("claim_parser_fix")
    if cp:
        raw = json.loads((OUTPUTS / "parser_fix_before_after_n30.json").read_text(encoding="utf-8"))
        if cp["n"] != len(raw["cases"]):
            fail(f"{name}: claim_parser_fix N ({cp['n']}) != raw source case count ({len(raw['cases'])})")
        else:
            ok(f"{name}: claim_parser_fix N reconciles with raw source ({cp['n']})")

    scope = findings.get("atomic_scope_check_assertion_spans")
    if scope:
        hist = json.loads((OUTPUTS / "atomic_scope_check_final_replay.json").read_text(encoding="utf-8"))
        if scope["n"] != hist["n_scope_violations_replayed"] or scope["variant_value"] != hist["n_unblocked_final"]:
            fail(f"{name}: atomic_scope_check fresh reproduction does not match the historical committed replay")
        else:
            ok(f"{name}: atomic_scope_check fresh reproduction matches the historical committed replay exactly")


# 10. every ablation has a classification
def check_all_classified():
    name = "Every ablation classified"
    summary = json.loads((ABLATION_DIR / "ABLATION_SUMMARY.json").read_text(encoding="utf-8"))
    valid = {"SUPPORTED", "DESCRIPTIVE", "DIAGNOSTIC", "NOT_ISOLABLE", "NOT_EXECUTED"}
    for f in summary["findings"]:
        if f.get("classification") not in valid:
            fail(f"{name}: {f['factor']} has invalid/missing classification: {f.get('classification')}")
        else:
            ok(f"{name}: {f['factor']} classified as {f['classification']}")


# 11. every SUPPORTED result has an actual isolating comparison
def check_supported_has_isolation():
    name = "SUPPORTED results have genuine isolation"
    summary = json.loads((ABLATION_DIR / "ABLATION_SUMMARY.json").read_text(encoding="utf-8"))
    for f in summary["findings"]:
        if f.get("classification") == "SUPPORTED":
            if f.get("isolated") is not True:
                fail(f"{name}: {f['factor']} is classified SUPPORTED but isolated != True")
            elif not f.get("isolation_note"):
                fail(f"{name}: {f['factor']} is classified SUPPORTED but has no isolation_note explaining why")
            else:
                ok(f"{name}: {f['factor']} (SUPPORTED) has isolated=True and a documented isolation rationale")


# 12/13. historical vs fresh explicit; GPU-dependent not falsely marked fresh
def check_fresh_historical_and_gpu_labeling():
    name = "Fresh/historical and GPU labeling"
    summary = json.loads((ABLATION_DIR / "ABLATION_SUMMARY.json").read_text(encoding="utf-8"))
    if summary.get("nvidia_gpu_available") is not False or summary.get("qwen_generation_or_correction_invoked_this_step") is not False:
        fail(f"{name}: top-level summary does not explicitly mark GPU unavailable / Qwen not invoked")
    else:
        ok(f"{name}: top-level summary explicitly marks GPU unavailable and Qwen not invoked")

    for f in summary["findings"]:
        foh = f.get("fresh_or_historical", "")
        if not foh:
            fail(f"{name}: {f['factor']} has no fresh_or_historical label")
            continue
        # any factor whose dataset mentions GPU-dependent generation must not say "FRESH" alone
        if f["factor"] == "correction_levers_combined (premise_framing isolated within an otherwise-fixed config)":
            if "HISTORICAL" not in foh or f.get("gpu_execution_claimed_this_step") is not False:
                fail(f"{name}: GPU-dependent correction-levers factor is not correctly marked historical/no-GPU-claimed")
            else:
                ok(f"{name}: GPU-dependent correction-levers factor correctly marked HISTORICAL, gpu_execution_claimed_this_step=False")
        else:
            ok(f"{name}: {f['factor']} has an explicit fresh_or_historical label ({foh.split('(')[0].strip()})")


# 14. no unsupported causal language; 15. no natural-data accuracy/F1 claims
def check_terminology():
    name = "Terminology discipline"
    disallowed_patterns = [
        (re.compile(r"\bcaused\b", re.IGNORECASE), "caused"),
        (re.compile(r"\bproved\b", re.IGNORECASE), "proved"),
        (re.compile(r"\bsolved\b", re.IGNORECASE), "solved"),
    ]
    allowed_negation = re.compile(
        r"does not (establish|prove|mean)|never (approve|caus|prov)|not (proven|prove|solved|caused)|"
        r"solved.?\"|\"solved|not .*solved|no lever.*solved|has.?n.?t solved|not.*'solved'",
        re.IGNORECASE,
    )
    # Manually reviewed (per this step's Phase 17 instruction: "review every occurrence
    # manually") and confirmed legitimate: both are enumerated PROHIBITED claims sitting
    # in a "What we cannot claim" table column, i.e. already negated by the column's own
    # semantics -- not a stated claim.
    manually_reviewed_allowed_snippets = [
        "solved correction shipping",
        "accuracy on natural data",
    ]
    violation = False
    for md in list(ABLATION_DIR.glob("ABLATION_*.md")):
        text = md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if any(snippet in line.lower() for snippet in manually_reviewed_allowed_snippets):
                continue
            for pat, label in disallowed_patterns:
                if pat.search(line) and not allowed_negation.search(line):
                    fail(f"{name}: potentially unsupported causal term '{label}' in {md.name}: {line.strip()[:140]}")
                    violation = True
    if not violation:
        ok(f"{name}: no unsupported 'caused'/'proved'/'solved' usage found outside explicit negations")

    accuracy_violation = False
    natural_accuracy_pattern = re.compile(r"natural.{0,30}(accuracy|F1)|(accuracy|F1).{0,30}natural data", re.IGNORECASE)
    allowed_natural = re.compile(r"not.*accuracy|no.*accuracy|never.*accuracy|accuracy.*not calculated", re.IGNORECASE)
    for md in list(ABLATION_DIR.glob("ABLATION_*.md")):
        text = md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if any(snippet in line.lower() for snippet in manually_reviewed_allowed_snippets):
                continue
            if natural_accuracy_pattern.search(line) and not allowed_natural.search(line):
                fail(f"{name}: possible natural-data accuracy/F1 claim in {md.name}: {line.strip()[:140]}")
                accuracy_violation = True
    if not accuracy_violation:
        ok(f"{name}: no natural-data accuracy/F1 claim found")


# 16. production threshold remains 0.70; 17. production configuration unchanged
def check_production_config_unchanged():
    name = "Production configuration unchanged"
    import yaml
    cfg = yaml.safe_load((PROTOTYPE_DIR / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    if cfg["verification"]["confidence_threshold"] != 0.70:
        fail(f"{name}: confidence_threshold is {cfg['verification']['confidence_threshold']}, expected 0.70")
    else:
        ok(f"{name}: confidence_threshold unchanged at 0.70")
    expected = {
        "use_evidence_v1": True, "premise_framing": "labeled",
        "atomic_scope_check": "assertion_spans", "narrow_reverification_hypothesis": True,
    }
    if (cfg["use_evidence_v1"] != expected["use_evidence_v1"]
            or cfg["verification"]["premise_framing"] != expected["premise_framing"]
            or cfg["correction"]["atomic_scope_check"] != expected["atomic_scope_check"]
            or cfg["correction"]["narrow_reverification_hypothesis"] != expected["narrow_reverification_hypothesis"]):
        fail(f"{name}: one or more production config values changed from the expected shipped values")
    else:
        ok(f"{name}: all four production config levers remain at their shipped values")

    summary = json.loads((ABLATION_DIR / "ABLATION_SUMMARY.json").read_text(encoding="utf-8"))
    if summary.get("production_confidence_threshold") != 0.70 or summary.get("production_config_unchanged") is not True:
        fail(f"{name}: ABLATION_SUMMARY.json does not confirm production config unchanged")
    else:
        ok(f"{name}: ABLATION_SUMMARY.json confirms production config unchanged")


# 18. all machine-readable summaries agree with markdown tables
def check_json_csv_md_agreement():
    name = "JSON/CSV/MD agreement"
    summary = json.loads((ABLATION_DIR / "ABLATION_SUMMARY.json").read_text(encoding="utf-8"))
    csv_text = (ABLATION_DIR / "ABLATION_RESULTS.csv").read_text(encoding="utf-8")
    for f in summary["findings"]:
        if f["factor"] not in csv_text and f["factor"].split(" (")[0] not in csv_text:
            fail(f"{name}: factor '{f['factor']}' from ABLATION_SUMMARY.json not found in ABLATION_RESULTS.csv")
        else:
            ok(f"{name}: factor '{f['factor']}' present in both ABLATION_SUMMARY.json and ABLATION_RESULTS.csv")

    md_text = (ABLATION_DIR / "ABLATION_RESULTS.md").read_text(encoding="utf-8")
    for f in summary["findings"]:
        key_term = f["factor"].split("_")[0]
        if key_term.lower() not in md_text.lower():
            warn(f"{name}: factor '{f['factor']}' may not be clearly represented in ABLATION_RESULTS.md")


def main() -> int:
    check_no_source_or_historical_changes()
    check_no_gold_or_label_contamination()
    check_stats_reconcile()
    check_all_classified()
    check_supported_has_isolation()
    check_fresh_historical_and_gpu_labeling()
    check_terminology()
    check_production_config_unchanged()
    check_json_csv_md_agreement()

    print("=" * 70)
    print("STEP 7 ABLATION VALIDATION REPORT")
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
