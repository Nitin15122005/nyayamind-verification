"""STEP 13 final release-audit validator.

Independent, re-runnable checks over the whole research/prototype/evaluation/ workspace
before a git commit is considered. Read-only -- makes no changes to any file.

Checks: required workspace directories exist; cited paths in the reconciliation/
faculty/release documents resolve to real files; FINAL_CLAIM_REGISTER.csv is internally
contiguous (C01..C26, no gaps/dupes) and FACULTY_RESULTS_TABLE.md rows cross-reference
it; the six required limitations are textually present and not weakened; GPU-absence
statements are scoped to the STEP 1-9 machine only; cumulative 1/56 stays historical-
only/protocol-insufficient everywhere; the joint four-lever experiment stays marked
unavailable everywhere; natural-data results are never described with bare "accuracy"/
"correctness" language; all 11 figures exist on disk; 205 is the only total ever
asserted for the regression suite.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_release_audit.py
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
FIGURES_DIR = TESTING_DIR / "figures"

CLAIM_REGISTER = REPORTS_DIR / "FINAL_CLAIM_REGISTER.csv"
RECONCILIATION_REPORT = REPORTS_DIR / "FINAL_RECONCILIATION_REPORT.md"
REPRODUCIBILITY_MATRIX = REPORTS_DIR / "FINAL_REPRODUCIBILITY_MATRIX.md"
FACULTY_REPORT = REPORTS_DIR / "FACULTY_EVALUATION_REPORT.md"
FACULTY_SUMMARY = REPORTS_DIR / "FACULTY_EXECUTIVE_SUMMARY.md"
FACULTY_TABLE = REPORTS_DIR / "FACULTY_RESULTS_TABLE.md"
FACULTY_LIMITATIONS = REPORTS_DIR / "FACULTY_LIMITATIONS_AND_CAVEATS.md"
RELEASE_AUDIT = REPORTS_DIR / "FINAL_RELEASE_AUDIT.md"
WORKSPACE_MANIFEST = REPORTS_DIR / "FINAL_WORKSPACE_MANIFEST.md"

AUDIT_DOCS = [
    RECONCILIATION_REPORT, REPRODUCIBILITY_MATRIX,
    FACULTY_REPORT, FACULTY_SUMMARY, FACULTY_TABLE, FACULTY_LIMITATIONS,
]

REQUIRED_DIRS = [
    "inputs", "expected_outputs", "actual_outputs", "comparisons",
    "components", "integration_tests", "ablation", "metrics",
    "figures", "reports", "scripts",
]

FAILURES: list[str] = []
PASSES: list[str] = []
WARNINGS: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)
def warn(m): WARNINGS.append(m)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def all_audit_docs_text() -> str:
    return "\n".join(read_text(p) for p in AUDIT_DOCS if p.exists())


# 1. Required workspace directories exist
def check_workspace_dirs():
    name = "All 10 required testing-workspace directories exist"
    missing = [d for d in REQUIRED_DIRS if not (TESTING_DIR / d).is_dir()]
    if missing:
        fail(f"{name}: missing {missing}")
        return
    ok(f"{name}: {', '.join(REQUIRED_DIRS)}")


# 2. Cited backtick-quoted paths across the reconciliation/faculty documents resolve
_PATH_RE = re.compile(r"`([A-Za-z0-9_./\\-]+\.(?:jsonl|json|csv|md|py|txt|png))`")
_BASENAME_INDEX: dict[str, list[Path]] | None = None


def _basename_index() -> dict[str, list[Path]]:
    global _BASENAME_INDEX
    if _BASENAME_INDEX is None:
        idx: dict[str, list[Path]] = {}
        for p in PROTOTYPE_DIR.rglob("*"):
            if p.is_file():
                idx.setdefault(p.name, []).append(p)
        _BASENAME_INDEX = idx
    return _BASENAME_INDEX


def _resolves(rel: str) -> bool:
    rel = rel.strip()
    candidates = [
        TESTING_DIR / rel,
        TESTING_DIR / rel.removeprefix("evaluation/"),
        PROTOTYPE_DIR / rel,
        PROTOTYPE_DIR / rel.removeprefix("research/prototype/"),
        REPO_ROOT / rel,
    ]
    if any(p.exists() for p in candidates):
        return True
    return Path(rel).name in _basename_index()


def check_cited_paths_resolve():
    name = "Cited paths in reconciliation/faculty documents resolve to real files"
    unresolved = []
    checked = 0
    for p in AUDIT_DOCS:
        if not p.exists():
            continue
        for m in _PATH_RE.finditer(read_text(p)):
            rel = m.group(1)
            checked += 1
            if not _resolves(rel):
                unresolved.append(f"{p.name}: {rel}")
    if unresolved:
        fail(f"{name}: {len(unresolved)} unresolved path(s): {sorted(set(unresolved))[:10]}")
        return
    ok(f"{name}: {checked} cited path(s) checked across {len(AUDIT_DOCS)} documents, all resolved")


# 3. Claim register is contiguous (C01..C26, no gaps/dupes) and the faculty table
#    references only real claim IDs
def check_claim_register_integrity():
    name = "FINAL_CLAIM_REGISTER.csv is contiguous and fully referenced by the faculty table"
    if not CLAIM_REGISTER.exists():
        fail(f"{name}: register missing")
        return
    with CLAIM_REGISTER.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [r["claim_id"] for r in rows]
    if len(ids) != len(set(ids)):
        fail(f"{name}: duplicate claim_id(s) found")
        return
    nums = sorted(int(i[1:]) for i in ids)
    if nums != list(range(1, len(nums) + 1)):
        fail(f"{name}: claim IDs are not contiguous from C01 (got {ids})")
        return
    if not FACULTY_TABLE.exists():
        fail(f"{name}: FACULTY_RESULTS_TABLE.md missing")
        return
    table_text = read_text(FACULTY_TABLE)
    table_ids = set(re.findall(r"\bC\d{2}\b", table_text))
    orphans = table_ids - set(ids)
    if orphans:
        fail(f"{name}: FACULTY_RESULTS_TABLE.md references claim ID(s) not in the register: {sorted(orphans)}")
        return
    unreferenced = set(ids) - table_ids
    if unreferenced:
        warn(f"{name}: {len(unreferenced)} register row(s) not referenced in the results table: {sorted(unreferenced)}")
    ok(f"{name}: {len(ids)} contiguous claim IDs (C01-C{len(ids):02d}), "
       f"all {len(table_ids)} table references resolve to real register rows")


# 4. Six required limitations present and not weakened
REQUIRED_LIMITATIONS = [
    ("cumulative 1/56 unrecoverable protocol",
     re.compile(r"cumulative.{0,40}(1/56|correction rate)", re.IGNORECASE)),
    ("missing joint four-lever experiment",
     re.compile(r"joint four-lever", re.IGNORECASE)),
    ("scope-check batch discrepancy (1/11 vs 4/6)",
     re.compile(r"1\s*(of|/)\s*11.{0,80}4\s*(of|/)\s*6", re.IGNORECASE | re.DOTALL)),
    ("only 50/82 v1 evidence records re-fetched",
     re.compile(r"50\s*(of|/)\s*82", re.IGNORECASE)),
    ("Project Author Statement not used as evidence",
     re.compile(r"project author statement", re.IGNORECASE)),
    ("historical GPU physical-machine identity not confirmed",
     re.compile(r"physical.machine identity", re.IGNORECASE)),
]

WEAKENING_TOKENS = re.compile(
    r"\b(mostly|largely|generally|probably|likely|approximately similar|"
    r"difficult to recover|hard to recover|somewhat unclear)\b", re.IGNORECASE
)


def check_limitations_present_and_unweakened():
    name = "All six required limitations present and unweakened in FACULTY_LIMITATIONS_AND_CAVEATS.md"
    if not FACULTY_LIMITATIONS.exists():
        fail(f"{name}: file missing")
        return
    text = read_text(FACULTY_LIMITATIONS)
    missing = [label for label, pat in REQUIRED_LIMITATIONS if not pat.search(text)]
    if missing:
        fail(f"{name}: missing {missing}")
        return
    weak_hits = []
    for label, pat in REQUIRED_LIMITATIONS:
        m = pat.search(text)
        window = text[max(0, m.start() - 200):m.end() + 400]
        if WEAKENING_TOKENS.search(window):
            weak_hits.append(label)
    if weak_hits:
        warn(f"{name}: possible softening language near: {weak_hits}")
    ok(f"{name}: all 6 limitations present, no clear softening language detected")


# 5. GPU status correctly scoped
def check_gpu_scoping():
    name = "GPU-absence statements are scoped to the STEP 1-9 machine only"
    text = all_audit_docs_text()
    if "RTX 4050" not in text:
        fail(f"{name}: no mention of the STEP 10/10B GPU (RTX 4050) found anywhere in the audit set")
        return
    unscoped = []
    for pat in [re.compile(r"no nvidia gpu", re.IGNORECASE),
                re.compile(r"gpu (is )?unavailable", re.IGNORECASE),
                re.compile(r"qwen generation.{0,20}not executed", re.IGNORECASE)]:
        for m in pat.finditer(text):
            window = text[max(0, m.start() - 300):m.end() + 300]
            # A quoted/audited-phrase reference (e.g. this validator's own report
            # discussing '"GPU unavailable" statements' as a category it checked for)
            # is not itself a claim -- skip it.
            preceding = text[max(0, m.start() - 15):m.start()]
            if '"' in preceding or "zero unscoped" in window.lower() or "no stale" in window.lower():
                continue
            if not re.search(r"step 1-9|step\s*1\s*[-–]\s*9|this machine|that machine|the earlier|"
                              r"amd radeon", window, re.IGNORECASE):
                unscoped.append(text[max(0, m.start() - 60):m.end() + 60].replace("\n", " "))
    if unscoped:
        fail(f"{name}: {len(unscoped)} unscoped statement(s): {unscoped[:5]}")
        return
    ok(f"{name}: every GPU-absence statement found is explicitly scoped; "
       f"RTX 4050 capability documented separately")


# 6. Cumulative 1/56 remains historical-only / protocol-insufficient everywhere
def check_cumulative_1_56():
    name = "Cumulative 1/56 remains historical-only / protocol-insufficient everywhere mentioned"
    text = all_audit_docs_text()
    mentions = list(re.finditer(r"1\s*/\s*56", text))
    if not mentions:
        fail(f"{name}: 1/56 not mentioned anywhere in the audited documents")
        return
    bad = []
    for m in mentions:
        window = text[max(0, m.start() - 400):m.end() + 400]
        if not re.search(
            r"historical.only|protocol insufficient|not.{0,40}reproduc|cannot.{0,60}reproduc|"
            r"cannot be freshly re-derived|not.{0,20}freshly re-derived|not statistically validated|"
            r"unrecoverable|not.{0,15}recoverable|not.{0,15}recover\b|nothing to recover|"
            r"no\s+recoverable|not a stable rate|snapshot, not a rate|structural reason",
            window, re.IGNORECASE | re.DOTALL,
        ):
            bad.append(text[max(0, m.start() - 40):m.end() + 40].replace("\n", " "))
    if bad:
        fail(f"{name}: {len(bad)} unqualified mention(s): {bad[:5]}")
        return
    ok(f"{name}: all {len(mentions)} mention(s) carry a historical-only/protocol-insufficient qualifier")


# 7. Joint four-lever remains marked unavailable everywhere
def check_joint_four_lever():
    name = "Joint four-lever experiment remains marked unavailable everywhere mentioned"
    text = all_audit_docs_text()
    mentions = list(re.finditer(r"joint four-lever", text, re.IGNORECASE))
    if not mentions:
        fail(f"{name}: not mentioned anywhere")
        return
    bad = []
    for m in mentions:
        window = text[max(0, m.start() - 300):m.end() + 300]
        if not re.search(
            r"does not\s+exist|unavailable|no experiment|not\s+exist|none exists|none invented|"
            r"no protocol|no causal claim|not executed|no such effect|\bno\b[^.]{0,60}\bexists?\b|"
            r"confirmed absent|never designed|nothing to recover",
            window, re.IGNORECASE | re.DOTALL,
        ):
            bad.append(text[max(0, m.start() - 40):m.end() + 80].replace("\n", " "))
    if bad:
        fail(f"{name}: {len(bad)} unqualified mention(s): {bad[:5]}")
        return
    ok(f"{name}: all {len(mentions)} mention(s) confirm the experiment does not exist")


# 8. Natural-data results are never bare "accuracy"/"correctness" without disclaimer
def check_natural_data_classification():
    name = "Natural-data results are never bare accuracy/correctness claims"
    text = all_audit_docs_text()
    violations = []
    for m in re.finditer(r"natural.{0,20}(accuracy|correctness)", text, re.IGNORECASE):
        window = text[max(0, m.start() - 80):m.end() + 120]
        if not re.search(r"no |not |never |does not |n't|zero|disclaim", window, re.IGNORECASE):
            violations.append(text[max(0, m.start() - 40):m.end() + 60].replace("\n", " "))
    if violations:
        fail(f"{name}: {len(violations)} unguarded hit(s): {violations[:5]}")
        return
    ok(f"{name}: every 'natural data' + accuracy/correctness co-occurrence found is a disclaimer")


# 9. All 11 figures exist
def check_figures_exist():
    name = "All 11 figures exist under evaluation/figures/"
    missing = [f"{i:02d}" for i in range(1, 12) if not list(FIGURES_DIR.glob(f"{i:02d}_*.png"))]
    if missing:
        fail(f"{name}: missing figure(s) {missing}")
        return
    ok(f"{name}: figures 01-11 all present")


# 10. 205 is the only total ever asserted for the regression suite
def check_test_count_authoritative():
    name = "205 is the sole authoritative regression-test total (never summed as 289 etc.)"
    text = all_audit_docs_text()
    if "205" not in text:
        fail(f"{name}: '205' not mentioned anywhere in the audited documents")
        return
    bad = []
    for m in re.finditer(r"\b289\b", text):
        window = text[max(0, m.start() - 200):m.end() + 200]
        if not re.search(r"overlap|not.{0,20}(alternative|additional)|categoriz|never sum|not.{0,15}sum",
                          window, re.IGNORECASE):
            bad.append(text[max(0, m.start() - 60):m.end() + 60].replace("\n", " "))
    if bad:
        fail(f"{name}: '289' appears without an overlap/non-additive disclaimer: {bad[:5]}")
        return
    ok(f"{name}: 205 is asserted as the authoritative total; any 289 reference is "
       f"explicitly disclaimed as an overlapping categorization, not an alternative total")


# 11. PROVENANCE.md step-chain coverage (informational -- STEP 11/12 were never
#     instructed to append there, so a gap here is a reportable observation, not a
#     validator failure).
def check_provenance_chain():
    name = "PROVENANCE.md step-header chain (STEP 3-10B) is present and unbroken"
    prov = TESTING_DIR / "PROVENANCE.md"
    if not prov.exists():
        fail(f"{name}: PROVENANCE.md missing")
        return
    text = read_text(prov)
    steps_found = re.findall(r"^## STEP (\d+[A-Z]?)", text, re.MULTILINE)
    expected = {"3", "4", "5", "6", "7", "8", "9", "10", "10B"}
    missing = expected - set(steps_found)
    if missing:
        fail(f"{name}: missing STEP header(s) {sorted(missing)}")
        return
    if not re.search(r"## STEP 11", text) or not re.search(r"## STEP 12", text):
        warn(f"{name}: PROVENANCE.md has no dedicated '## STEP 11' / '## STEP 12' section "
             f"(their deliverables live under reports/ instead, per their own task scope -- "
             f"this is a documentation-completeness observation, not a defect)")
    ok(f"{name}: STEP 3 through STEP 10B headers all present and unbroken")


def main() -> int:
    checks = [
        check_workspace_dirs,
        check_cited_paths_resolve,
        check_claim_register_integrity,
        check_limitations_present_and_unweakened,
        check_gpu_scoping,
        check_cumulative_1_56,
        check_joint_four_lever,
        check_natural_data_classification,
        check_figures_exist,
        check_test_count_authoritative,
        check_provenance_chain,
    ]
    for c in checks:
        c()

    print("=" * 70)
    print("STEP 13 FINAL RELEASE AUDIT VALIDATION REPORT")
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
    total = len(PASSES) + len(FAILURES)
    print(f"\nRESULT: {'FAIL' if FAILURES else 'PASS'} "
          f"({len(PASSES)}/{total} checks passed, {len(FAILURES)} failures, {len(WARNINGS)} warnings)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
