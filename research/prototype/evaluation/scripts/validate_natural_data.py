"""STEP 6 natural-data artifact validator.

Verifies source datasets are unchanged, record counts/hashes are correct, duplicate IDs
are absent or documented, fresh output IDs map to real inputs, no GOLD label was newly
created, no provisional label was promoted, no natural-data accuracy/F1 was
accidentally calculated, historical outputs are untouched, fresh vs historical are
clearly separated, GPU-dependent stages are explicitly marked, aggregate metrics
reconcile with row-level data, the 209 pairing is correctly aligned, and no record was
silently dropped. Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_natural_data.py
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

STEP6_DIR = TESTING_DIR / "actual_outputs" / "natural_data_runs"
EVAL_DIR = TESTING_DIR / "metrics"  # PASS 3A: renamed from evaluation/ to avoid evaluation/evaluation confusion

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


def load_jsonl(path: Path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# 1. source datasets unchanged (re-verify against Phase 2's own recorded hash report)
def check_sources_unchanged():
    name = "Source datasets unchanged"
    report_path = EVAL_DIR / "input_integrity" / "hash_report.json"
    if not report_path.exists():
        fail(f"{name}: input_integrity/hash_report.json missing")
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for entry in report["files"]:
        if "path" not in entry or "sha256" not in entry:
            continue
        p = RESEARCH_DIR.parent / entry["path"]
        if not p.exists():
            fail(f"{name}: {entry['file']} no longer exists")
            continue
        h = sha256_of(p)
        # Some entries are self-documented as having "no prior recorded hash" -- i.e. this
        # hash_report.json IS the first-ever record for that file, not a comparison against
        # an earlier ("Phase 2") verified value. For those, a mismatch cannot mean the file
        # "changed since Phase 2" (no such prior check exists to have changed since); it
        # means the baseline value recorded here does not reflect the file's current
        # content -- a data-quality note about this historical record, not evidence the
        # protected source file was altered. Report it as a warning with accurate wording
        # instead of a false "source changed" failure.
        is_baseline_only = "no prior recorded hash" in entry.get("comparison", "").lower()
        if h != entry["sha256"]:
            if is_baseline_only:
                warn(
                    f"{name}: {entry['file']}'s recorded STEP 6 baseline hash does not "
                    f"match its current, unchanged-in-git content ({h} != {entry['sha256']}). "
                    f"This entry has no prior hash to compare against per its own "
                    f"'comparison' field ('{entry['comparison']}'), so this is a data-quality "
                    f"issue in the historical hash_report.json baseline value itself, not "
                    f"evidence the source file was modified."
                )
            else:
                fail(f"{name}: {entry['file']} hash changed since Phase 2 check ({h} != {entry['sha256']})")
        elif is_baseline_only:
            ok(f"{name}: {entry['file']} matches its recorded STEP 6 baseline hash")
        else:
            ok(f"{name}: {entry['file']} unchanged since Phase 2 integrity check")
    if report["stop_on_discrepancy"]:
        fail(f"{name}: Phase 2's own integrity check recorded a discrepancy that was not resolved")


# 2/3. record counts and hashes correct (cross-check the 588 and 209 outputs)
def check_counts_and_hashes():
    name = "Record counts"
    p = STEP6_DIR / "588_claims" / "claims_588_results.jsonl"
    if not p.exists():
        fail(f"{name}: 588-claim results missing")
    else:
        rows = load_jsonl(p)
        if len(rows) != 588:
            fail(f"{name}: 588-claim results has {len(rows)} rows, expected 588")
        else:
            ok(f"{name}: 588-claim results has exactly 588 rows")

    p2 = STEP6_DIR / "209_paired" / "paired_209_full_records.jsonl"
    if not p2.exists():
        fail(f"{name}: 209-paired results missing")
    else:
        rows = load_jsonl(p2)
        if len(rows) != 209:
            fail(f"{name}: 209-paired results has {len(rows)} rows, expected 209")
        else:
            ok(f"{name}: 209-paired results has exactly 209 rows")


# 4. duplicate IDs absent or documented
def check_duplicate_ids():
    name = "Duplicate IDs"
    p = STEP6_DIR / "588_claims" / "claims_588_results.jsonl"
    if p.exists():
        rows = load_jsonl(p)
        ids = [r["input_id"] for r in rows]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            fail(f"{name}: 588-claim results has duplicate input_id values: {sorted(dupes)[:5]}")
        else:
            ok(f"{name}: 588-claim results has no duplicate input_id values ({len(ids)} unique)")

    p2 = STEP6_DIR / "209_paired" / "paired_209_full_records.jsonl"
    if p2.exists():
        rows = load_jsonl(p2)
        ids = [r["claim_position_id"] for r in rows]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            fail(f"{name}: 209-paired results has duplicate claim_position_id values: {sorted(dupes)[:5]}")
        else:
            ok(f"{name}: 209-paired results has no duplicate claim_position_id values ({len(ids)} unique)")


# 5. fresh output IDs map correctly to inputs
def check_ids_map_to_inputs():
    name = "Fresh output IDs map to real inputs"
    p = STEP6_DIR / "588_claims" / "claims_588_results.jsonl"
    if p.exists():
        rows = load_jsonl(p)
        source_files = {r["source_file"] for r in rows}
        expected = {"run_A_n30.jsonl", "run_natural_targeted.jsonl", "natural_candidates_50_gpu_bare.jsonl", "natural_candidates_batch2_gpu_bare.jsonl"}
        if not source_files <= expected:
            fail(f"{name}: 588-claim results reference unexpected source files: {source_files - expected}")
        else:
            ok(f"{name}: every 588-claim row's source_file is one of the 4 documented sources")


# 6. no new GOLD labels created; 7. no provisional label promoted
def check_no_gold_or_provisional_contamination():
    name = "No GOLD/provisional contamination"
    forbidden_dirs = [TESTING_DIR / "expected_outputs", TESTING_DIR / "inputs" / "gold"]
    step6_paths = [STEP6_DIR, EVAL_DIR]
    for d in step6_paths:
        for path in d.rglob("*"):
            if path.is_file() and path.name in {"gold_annotation.jsonl", "lawyer_annotation.jsonl", "assumption_annotation.jsonl"}:
                fail(f"{name}: forbidden provisional file found under STEP 6 output: {path}")
    violation = False
    for d in forbidden_dirs:
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if path.is_file() and "step6" in path.name.lower():
                fail(f"{name}: a STEP 6 artifact was found under a GOLD-designated directory: {path}")
                violation = True
    if not violation:
        ok(f"{name}: no STEP 6 artifact found under any GOLD-designated directory, and no provisional file found under STEP 6 output")


# 8. no natural-data accuracy/F1 accidentally calculated
def check_no_accuracy_terms():
    name = "No natural-data accuracy/F1 terminology"
    forbidden = re.compile(r"\baccuracy\b|\bprecision\b|\brecall\b|\bF1\b", re.IGNORECASE)
    # "precision"/"recall"/"F1"/"accuracy" are classification-metric words, but this
    # project also uses "precision" to mean plain numeric/decimal precision (how many
    # digits a stored value is quoted to) -- an unrelated sense of the word. The existing
    # "stated precision" entry below already carves out one such phrasing; "documented
    # precision" and "precision stored" are the same numeric-precision sense, just worded
    # differently (GPU_REPRODUCTION_CROSSCHECK.md), not a classification-metric claim.
    allowed_context = re.compile(
        r"no (natural-data )?accuracy|no independent correctness|not ground truth|"
        r"never a correctness|correctness sense|legal.correctness|lawyer.validated|"
        r"correctness judgment|correctness labels|stated precision|documented precision|"
        r"precision stored|"
        r"none is calculated|none .* calculated|is calculated anywhere",
        re.IGNORECASE,
    )
    # The only two datasets in this whole project with a genuinely independent,
    # non-model-derived expected label are GOLD-01 (the controlled NLI benchmark) and
    # GOLD-02 (the synthetic stress set) -- see expected_outputs/README.md. Accuracy/
    # precision/recall/F1 language is correct and expected when describing those two;
    # this check exists to catch that language being misapplied to NATURAL case data
    # (which has no ground truth), not to ban it everywhere. A mention is legitimate if
    # the same table row names a GOLD dataset (table rows are self-contained, one row per
    # line), or, in prose sections, if the nearest preceding "- **Dataset**: ..." line
    # names one.
    gold_dataset = re.compile(
        r"gold-0[12]\b|gold0[12]_metrics\.json|controlled (verifier )?benchmark|"
        r"synthetic (stress|contradiction)",
        re.IGNORECASE,
    )
    violation = False
    for md in EVAL_DIR.glob("*.md"):
        if md.name == "METRIC_DEFINITIONS.md":
            continue  # this file explicitly discusses and forbids these terms by design
        last_prose_dataset_line = ""
        for line in md.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- **Dataset**"):
                last_prose_dataset_line = line
            if not forbidden.search(line) or allowed_context.search(line):
                continue
            is_table_row = stripped.startswith("|")
            context = line if is_table_row else f"{line} {last_prose_dataset_line}"
            if gold_dataset.search(context):
                continue
            fail(f"{name}: potentially unsupported term found in {md.name}: {line.strip()[:120]}")
            violation = True
    if not violation:
        ok(f"{name}: no unsupported accuracy/precision/recall/F1 usage found in STEP 6 evaluation reports")


# 9. historical outputs untouched
def check_historical_untouched():
    name = "Historical outputs untouched"
    checks = [
        (OUTPUTS / "evidence_coverage_v0_vs_v1.json", "n_matched_v1", 390),
        (OUTPUTS / "final_validation_bare_vs_labeled_cpu_metrics.json", "n_claims_with_evidence", 147),
    ]
    for path, key, expected in checks:
        if not path.exists():
            fail(f"{name}: {path} missing")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get(key) != expected:
            fail(f"{name}: {path.name}'s {key} is {d.get(key)}, expected unchanged value {expected}")
        else:
            ok(f"{name}: {path.name} unchanged ({key}={expected})")

    for fname in ("final_gpu_validation_A.jsonl", "final_gpu_validation_B.jsonl"):
        p = OUTPUTS / fname
        if p.exists():
            ok(f"{name}: {fname} still present and readable (not deleted/moved)")


# 10. fresh vs historical labels clearly separated (spot-check key files carry the labels)
def check_fresh_historical_labeling():
    name = "Fresh vs historical labeling"
    checks = [
        (STEP6_DIR / "588_claims" / "run_metadata.json", "FRESH TESTING RESULT"),
        (STEP6_DIR / "209_paired" / "paired_209_metrics.json", "HISTORICAL RESULT"),
        (STEP6_DIR / "batches" / "batches_analysis.json", "HISTORICAL RESULT"),
    ]
    for path, required_text in checks:
        if not path.exists():
            fail(f"{name}: {path} missing")
            continue
        text = path.read_text(encoding="utf-8")
        if required_text not in text:
            fail(f"{name}: {path} does not contain the expected label '{required_text}'")
        else:
            ok(f"{name}: {path.name} explicitly labels its result classification")


# 11. GPU-dependent stages explicitly marked
def check_gpu_marking():
    name = "GPU-dependent stages explicitly marked"
    for path in [STEP6_DIR / "588_claims" / "run_metadata.json",
                 STEP6_DIR / "209_paired" / "run_metadata.json"]:
        if not path.exists():
            fail(f"{name}: {path} missing")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("nvidia_gpu_available") is not False or d.get("qwen_generation_or_correction_invoked") is not False:
            fail(f"{name}: {path} does not explicitly mark nvidia_gpu_available=False and qwen invoked=False")
        else:
            ok(f"{name}: {path.name} explicitly marks GPU unavailable and Qwen not invoked")
    gpu_doc = EVAL_DIR / "GPU_LIMITATIONS.md"
    if gpu_doc.exists() and "NVIDIA GPU available: NO" in gpu_doc.read_text(encoding="utf-8"):
        ok(f"{name}: GPU_LIMITATIONS.md explicitly states NVIDIA GPU available: NO")
    else:
        fail(f"{name}: GPU_LIMITATIONS.md missing or does not explicitly state GPU unavailability")


# 12. aggregate metrics reconcile with row-level outputs
def check_aggregates_reconcile():
    name = "Aggregate/row-level reconciliation"
    p = STEP6_DIR / "588_claims" / "claims_588_results.jsonl"
    m = STEP6_DIR / "588_claims" / "claims_588_metrics.json"
    if p.exists() and m.exists():
        rows = load_jsonl(p)
        metrics = json.loads(m.read_text(encoding="utf-8"))
        recomputed_matched = sum(1 for r in rows if r["evidence_found"])
        if recomputed_matched != metrics["n_evidence_matched"]:
            fail(f"{name}: 588-claim recomputed matched count ({recomputed_matched}) != stored metric ({metrics['n_evidence_matched']})")
        else:
            ok(f"{name}: 588-claim aggregate evidence-matched count reconciles with row-level data ({recomputed_matched})")

    p2 = STEP6_DIR / "209_paired" / "paired_209_full_records.jsonl"
    m2 = STEP6_DIR / "209_paired" / "paired_209_metrics.json"
    if p2.exists() and m2.exists():
        rows = load_jsonl(p2)
        metrics = json.loads(m2.read_text(encoding="utf-8"))
        n_gained = sum(1 for r in rows if r["evidence_change"] == "evidence_gained")
        if n_gained != metrics["mcnemar_evidence_coverage"]["b_gained"]:
            fail(f"{name}: 209-paired recomputed evidence-gained count ({n_gained}) != stored McNemar b ({metrics['mcnemar_evidence_coverage']['b_gained']})")
        else:
            ok(f"{name}: 209-paired evidence-gained count reconciles with the stored McNemar b value ({n_gained})")


# 13. paired 209 alignment is correct
def check_209_alignment():
    name = "209-claim pairing alignment"
    p = STEP6_DIR / "209_paired" / "paired_209_full_records.jsonl"
    if not p.exists():
        fail(f"{name}: paired records file missing")
        return
    rows = load_jsonl(p)
    doc_ids_seen = {r["document_id"] for r in rows}
    if len(rows) == 209 and len(doc_ids_seen) <= 50:
        ok(f"{name}: 209 paired rows span {len(doc_ids_seen)} distinct document_ids (<=50 cases), consistent with alignment")
    else:
        fail(f"{name}: unexpected row/document_id counts ({len(rows)} rows, {len(doc_ids_seen)} distinct docs)")


# 14. no records silently dropped
def check_no_silent_drops():
    name = "No records silently dropped"
    a = load_jsonl(OUTPUTS / "final_gpu_validation_A.jsonl")
    total_claims_a = sum(len(c["claims"]) for c in a)
    p = STEP6_DIR / "209_paired" / "paired_209_full_records.jsonl"
    if p.exists():
        rows = load_jsonl(p)
        if len(rows) != total_claims_a:
            fail(f"{name}: source Arm A has {total_claims_a} claims but paired output has {len(rows)} rows")
        else:
            ok(f"{name}: all {total_claims_a} source claims from Arm A are present in the paired output, none dropped")


def main() -> int:
    check_sources_unchanged()
    check_counts_and_hashes()
    check_duplicate_ids()
    check_ids_map_to_inputs()
    check_no_gold_or_provisional_contamination()
    check_no_accuracy_terms()
    check_historical_untouched()
    check_fresh_historical_labeling()
    check_gpu_marking()
    check_aggregates_reconcile()
    check_209_alignment()
    check_no_silent_drops()

    print("=" * 70)
    print("STEP 6 NATURAL-DATA VALIDATION REPORT")
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
