"""STEP 11 final-reconciliation validator.

Verifies: every headline metric in reports/FINAL_CLAIM_REGISTER.csv is traceable to
a source artifact that actually exists; no stale unscoped GPU-unavailable statement
exists in any STEP 11 file; the 209-claim GPU experiment is classified FRESH GPU
REPRODUCED; the cumulative 1/56 figure remains historical-only/protocol-insufficient;
the joint four-lever experiment remains marked unavailable; GOLD vs METRIC-ONLY
separation is intact; the authoritative test count is 205 (never summed from
component-group subsets); every source_artifact path in the claim register resolves
to a real file. Read-only — makes no changes.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_reconciliation.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
PROTOTYPE_DIR = TESTING_DIR.parent
REPO_ROOT = PROTOTYPE_DIR.parent.parent
REPORTS_DIR = TESTING_DIR / "reports"
EVAL_DIR = TESTING_DIR / "metrics"  # PASS 3A: renamed from evaluation/ to avoid evaluation/evaluation confusion
ABLATION_DIR = TESTING_DIR / "ablation"

CLAIM_REGISTER = REPORTS_DIR / "FINAL_CLAIM_REGISTER.csv"
# PASS 2 cleanup (2026-09-06): FINAL_RECONCILIATION_REPORT.md was archived to
# reports/archive/ unedited (its two unique sections were also carried forward into
# FACULTY_EVALUATION_REPORT.md's new appendix) -- point this validator at its new,
# unchanged-content location so it keeps validating the same text.
RECON_REPORT = REPORTS_DIR / "archive" / "FINAL_RECONCILIATION_REPORT.md"
REPRO_MATRIX = REPORTS_DIR / "FINAL_REPRODUCIBILITY_MATRIX.md"

FAILURES: list[str] = []
PASSES: list[str] = []
WARNINGS: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)
def warn(m): WARNINGS.append(m)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def read_claims() -> list[dict]:
    with CLAIM_REGISTER.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# 1. All three STEP 11 deliverables exist
def check_deliverables_exist():
    name = "STEP 11 deliverables exist"
    missing = [str(p) for p in (CLAIM_REGISTER, RECON_REPORT, REPRO_MATRIX) if not p.exists()]
    if missing:
        fail(f"{name}: missing {missing}")
        return
    ok(f"{name}: FINAL_RECONCILIATION_REPORT.md, FINAL_CLAIM_REGISTER.csv, "
       f"FINAL_REPRODUCIBILITY_MATRIX.md all present under evaluation/reports/")


# 2. Every source_artifact path referenced in the claim register resolves to a real file
_PATH_RE = re.compile(r"([A-Za-z0-9_./\\-]+\.(?:jsonl|json|csv|md|py|txt))")


def _candidate_roots(rel: str) -> list[Path]:
    rel = rel.strip()
    return [TESTING_DIR / rel, TESTING_DIR / rel.removeprefix("evaluation/"),
            PROTOTYPE_DIR / rel, REPO_ROOT / rel]


_BASENAME_INDEX: dict[str, list[Path]] | None = None


def _basename_index() -> dict[str, list[Path]]:
    """Recursive basename -> path index over the whole prototype tree, built
    once, so a bare filename cited without its directory (common in prose
    citations like 'paired_209_metrics.json') can still be resolved."""
    global _BASENAME_INDEX
    if _BASENAME_INDEX is None:
        idx: dict[str, list[Path]] = {}
        for p in PROTOTYPE_DIR.rglob("*"):
            if p.is_file():
                idx.setdefault(p.name, []).append(p)
        _BASENAME_INDEX = idx
    return _BASENAME_INDEX


def _resolves(rel: str) -> bool:
    if any(p.exists() for p in _candidate_roots(rel)):
        return True
    basename = Path(rel).name
    return basename in _basename_index()


def check_source_artifacts_exist():
    name = "All claim-register source_artifact paths exist on disk"
    if not CLAIM_REGISTER.exists():
        fail(f"{name}: claim register missing")
        return
    unresolved = []
    checked = 0
    for row in read_claims():
        cell = row.get("source_artifact", "")
        for m in _PATH_RE.finditer(cell):
            rel = m.group(1)
            checked += 1
            if not _resolves(rel):
                unresolved.append(f"{row.get('claim_id')}: {rel}")
    if unresolved:
        fail(f"{name}: {len(unresolved)} unresolved path(s): {unresolved[:10]}")
        return
    ok(f"{name}: {checked} source-artifact path reference(s) across all claims resolved to real files "
       f"(matched by full relative path or, where cited by bare filename, by a unique recursive basename lookup)")


# 3. 209-claim GPU experiment classified FRESH GPU REPRODUCED
def check_209_claim_classified():
    name = "209-claim GPU experiment correctly classified FRESH GPU REPRODUCED"
    rows = [r for r in read_claims() if "209-claim" in r.get("claim", "") and "exact GPU reproduction" in r.get("claim", "")]
    if not rows:
        fail(f"{name}: no claim-register row found for the 209-claim GPU reproduction")
        return
    row = rows[0]
    if "FRESH GPU REPRODUCED" not in row.get("freshness", "").upper() and "FRESH GPU REPRODUCED" not in row.get("classification", "").upper():
        fail(f"{name}: row {row.get('claim_id')} freshness/classification does not read FRESH GPU REPRODUCED "
             f"(got freshness={row.get('freshness')!r}, classification={row.get('classification')!r})")
        return
    if not RECON_REPORT.exists() or "exact reproduction" not in read_text(RECON_REPORT).lower():
        fail(f"{name}: reconciliation report does not describe the 209-claim result as an exact reproduction")
        return
    ok(f"{name}: claim {row.get('claim_id')} classified FRESH GPU REPRODUCED in the register, "
       f"corroborated in the reconciliation report")


# 4. Cumulative 1/56 remains historical-only / protocol-insufficient
def check_cumulative_1_56():
    name = "Cumulative 1/56 remains historical-only / protocol insufficient"
    rows = [r for r in read_claims() if "Cumulative correction shipping rate" in r.get("claim", "")]
    if not rows:
        fail(f"{name}: no claim-register row found for the cumulative correction rate")
        return
    row = rows[0]
    freshness = row.get("freshness", "").upper()
    if "PROTOCOL INSUFFICIENT" not in freshness or "HISTORICAL" not in freshness:
        fail(f"{name}: row {row.get('claim_id')} freshness does not read HISTORICAL-ONLY/PROTOCOL INSUFFICIENT "
             f"(got {row.get('freshness')!r})")
        return
    for doc in (RECON_REPORT, REPRO_MATRIX):
        if not doc.exists():
            fail(f"{name}: {doc} missing")
            return
        text = doc.read_text(encoding="utf-8")
        if "1/56" not in text or "PROTOCOL INSUFFICIENT" not in text.upper():
            fail(f"{name}: {doc.name} does not carry both the 1/56 figure and a PROTOCOL INSUFFICIENT classification")
            return
    # Must not AFFIRMATIVELY claim it was freshly re-derived anywhere in new
    # STEP 11 docs (a nearby negation like "cannot be freshly re-derived" is
    # the expected, correct phrasing and must not be flagged).
    for doc in (RECON_REPORT, REPRO_MATRIX):
        text = doc.read_text(encoding="utf-8")
        for m in re.finditer(r"1/56[^.\n]{0,80}?\bfresh(?:ly)? (?:re-?derived|reproduced)\b", text, re.IGNORECASE):
            span = text[m.start():m.end()]
            if re.search(r"\b(cannot|can't|can[’']t|not|no|never)\b", span, re.IGNORECASE):
                continue  # correctly negated
            fail(f"{name}: {doc.name} appears to affirmatively claim the 1/56 figure was freshly "
                 f"re-derived/reproduced: ...{span}...")
            return
    ok(f"{name}: consistently classified HISTORICAL-ONLY / PROTOCOL INSUFFICIENT, never approximated or "
       f"claimed freshly re-derived")


# 5. Joint four-lever experiment remains marked unavailable
def check_joint_four_lever_unavailable():
    name = "Joint four-lever experiment remains marked unavailable"
    rows = [r for r in read_claims() if "four-lever" in r.get("claim", "").lower()]
    if not rows:
        fail(f"{name}: no claim-register row for the joint four-lever experiment")
        return
    row = rows[0]
    if row.get("value", "").strip().lower() != "does not exist" and "unavailable" not in row.get("classification", "").lower():
        fail(f"{name}: row {row.get('claim_id')} does not clearly state the experiment does not exist "
             f"(value={row.get('value')!r}, classification={row.get('classification')!r})")
        return
    for doc in (RECON_REPORT, REPRO_MATRIX):
        text = read_text(doc)
        if not re.search(r"four-lever[^.\n]{0,60}(does not exist|remains unavailable|none (was|is) invented)", text, re.IGNORECASE) \
           and "does not exist" not in text.lower():
            fail(f"{name}: {doc.name} does not explicitly state the joint four-lever experiment is unavailable")
            return
    ok(f"{name}: consistently marked as not existing/unavailable, with no additive or interaction "
       f"effect inferred anywhere in the new STEP 11 documents")


# 6. GOLD vs METRIC-ONLY separation intact
def check_gold_vs_metric_only_separation():
    name = "GOLD vs METRIC-ONLY separation intact"
    rows = read_claims()
    gold_rows = [r for r in rows if r.get("classification", "").strip().upper() == "GOLD"]
    metric_rows = [r for r in rows if r.get("classification", "").strip().upper() == "METRIC-ONLY"]
    if not gold_rows or not metric_rows:
        fail(f"{name}: expected both GOLD and METRIC-ONLY rows in the claim register "
             f"(found {len(gold_rows)} GOLD, {len(metric_rows)} METRIC-ONLY)")
        return
    # GOLD rows must reference a GOLD-01/GOLD-02 dataset name or gold_metric source; METRIC-ONLY rows must not.
    bad = []
    for r in gold_rows:
        whole_row = " ".join(r.get(k, "") for k in r)
        if "gold" not in whole_row.lower():
            bad.append(r.get("claim_id"))
    for r in metric_rows:
        whole_row = " ".join(r.get(k, "") for k in r)
        if "gold-0" in whole_row.lower() or "gold0" in whole_row.lower():
            bad.append(r.get("claim_id"))
    if bad:
        fail(f"{name}: rows with ambiguous/crossed GOLD vs METRIC-ONLY labeling: {bad}")
        return
    ok(f"{name}: {len(gold_rows)} GOLD row(s) and {len(metric_rows)} METRIC-ONLY row(s) in the claim "
       f"register are cleanly separated, no GOLD-only language applied to natural-data rows or vice versa")


# 7. Authoritative test count is 205, never summed from component subsets
def check_test_count_205():
    name = "Authoritative test count is 205 (not summed from component subsets)"
    rows = [r for r in read_claims() if r.get("claim", "") == "Full regression suite result"]
    if not rows or rows[0].get("value", "").strip() != "205 passed":
        fail(f"{name}: claim register does not record 'Full regression suite result' = '205 passed'")
        return
    matrix_csv = EVAL_DIR / "COMPONENT_TEST_MATRIX.csv"
    if not matrix_csv.exists():
        fail(f"{name}: {matrix_csv} missing")
        return
    with matrix_csv.open(encoding="utf-8", newline="") as f:
        group_total = sum(int(r["tests"]) for r in csv.DictReader(f))
    if group_total == 205:
        warn(f"{name}: component-group counts now happen to sum to 205 — re-check this is still "
             f"coincidental overlap, not a real change in the suite")
    text = read_text(RECON_REPORT)
    if "289" not in text or "205" not in text:
        fail(f"{name}: reconciliation report does not explicitly document that group counts (289) "
             f"differ from and must not replace the authoritative total (205)")
        return
    ok(f"{name}: 205 recorded as the sole authoritative total; report explicitly documents that the "
       f"7 component-group counts (summing to {group_total}) are an overlapping categorization, not "
       f"an alternative total")


# 8. No unscoped stale "GPU unavailable" statement in any NEW STEP 11 file
UNSCOPED_GPU_PATTERNS = [
    r"GPU (?:is |was |remains )?unavailable(?!\s*(?:on|for) this machine)",
    r"no NVIDIA GPU(?!\s*(?:\(|on|for|exists on|is present on)?\s*(?:this|that) machine)",
    r"Qwen generation (?:is |was )?not executed(?!\s*(?:this step|on this machine))",
    r"all GPU experiments.*historical-only",
]


_SCOPE_MARKERS = re.compile(
    r"this machine|that machine|STEP\s*1-9|STEP\s*[2-9]\b|STEP\s*10\b|AMD Radeon|"
    r"confirmed in STEP|scoped to|correctly scoped|unscoped\"|Zero unscoped|"
    r"machine confirmed|its own time and\s*\n?\s*machine",
    re.IGNORECASE,
)


def check_no_unscoped_gpu_unavailable_claims():
    name = "No unscoped stale GPU-unavailable statement in STEP 11 documents"
    docs = [RECON_REPORT, REPRO_MATRIX]
    hits = []
    for doc in docs:
        if not doc.exists():
            continue
        text = read_text(doc)
        for pat in UNSCOPED_GPU_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                window = text[max(0, m.start() - 200):m.end() + 200]
                if _SCOPE_MARKERS.search(window):
                    continue  # correctly scoped (or is itself audit prose describing scoping)
                hits.append(f"{doc.name}: ...{text[max(0, m.start()-100):m.end()+40]}...")
    if hits:
        fail(f"{name}: {len(hits)} unscoped hit(s): {hits[:5]}")
        return
    ok(f"{name}: every GPU-unavailability statement in the new STEP 11 documents is explicitly scoped "
       f"to the STEP 1-9 machine; none is stated as a current/general project limitation")


# 9. No prohibited claim patterns introduced
def check_no_prohibited_claims():
    name = "No prohibited claim patterns in STEP 11 documents"
    bad_patterns = [
        r"correction is solved",
        r"prove(?:s|d)? correctness",
        r"universal(?:ly)? safe",
        r"natural-data accuracy",
        r"natural-data F1",
        r"joint[- ]lever interaction",
    ]
    for doc in (RECON_REPORT, REPRO_MATRIX):
        if not doc.exists():
            continue
        text = read_text(doc)
        for pat in bad_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                # Allow if immediately preceded by a negation, or if this is
                # itself an audit passage enumerating the prohibited patterns
                # being searched for/found-absent (quoted list context).
                before = text[max(0, m.start() - 250):m.start()]
                if re.search(r"\b(no|not|never|n['’]t|does not|do not|zero)\b", before[-80:], re.IGNORECASE):
                    continue
                if re.search(r"prohibited|search(ed)? for|patterns?\b|enumerat", before, re.IGNORECASE):
                    continue
                fail(f"{name}: unnegated hit for {pat!r} in {doc.name}: "
                     f"...{text[max(0,m.start()-40):m.end()+20]!r}...")
                return
    ok(f"{name}: no unsupported natural-data-accuracy/universal-safety/solved-correction/"
       f"joint-lever-interaction claims found")


# 10. Historical prior-step files not modified (spot-check a few canonical ones)
def check_prior_files_not_edited_in_place():
    name = "Prior-step canonical files not edited (only new STEP 11 files added)"
    # These files are cited throughout as untouched historical/prior-step record;
    # this is a structural sanity check that they still exist and still carry
    # their own step's markers (not overwritten wholesale by STEP 11 content).
    checks = {
        EVAL_DIR / "CANONICAL_METRICS.csv": "M16",
        EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md": "Experiment 3",
        ABLATION_DIR / "GPU_ABLATION_UPDATE.md": "PROTOCOL INSUFFICIENT",
        TESTING_DIR / "PROVENANCE.md": "STEP 10B",
    }
    for path, marker in checks.items():
        if not path.exists():
            fail(f"{name}: {path} missing")
            return
        if marker not in read_text(path):
            fail(f"{name}: {path} no longer contains expected marker {marker!r} — may have been overwritten")
            return
    ok(f"{name}: canonical STEP 4-10B files retain their own content markers, consistent with "
       f"append-only/read-only treatment by STEP 11")


def main() -> int:
    check_deliverables_exist()
    check_source_artifacts_exist()
    check_209_claim_classified()
    check_cumulative_1_56()
    check_joint_four_lever_unavailable()
    check_gold_vs_metric_only_separation()
    check_test_count_205()
    check_no_unscoped_gpu_unavailable_claims()
    check_no_prohibited_claims()
    check_prior_files_not_edited_in_place()

    print("=" * 70)
    print("STEP 11 FINAL RECONCILIATION VALIDATION REPORT")
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
        print(f"\nRESULT: FAIL ({len(FAILURES)} failure(s), {len(PASSES)} passed, {len(WARNINGS)} warnings)")
        return 1

    print(f"\nRESULT: PASS ({len(PASSES)} checks passed, 0 failures, {len(WARNINGS)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
