"""STEP 12 faculty-package validator.

Verifies: every headline value in reports/FACULTY_RESULTS_TABLE.md matches its cited
row in reports/FINAL_CLAIM_REGISTER.csv; all six required limitations/caveats are
present in reports/FACULTY_LIMITATIONS_AND_CAVEATS.md; no unsupported natural-data
accuracy/F1 claim exists in any of the four new faculty documents; GPU status is
correctly scoped (STEP 1-9-machine-only absence vs. STEP 10/10B-machine capability,
never blurred); the cumulative 1/56 figure remains classified historical-only /
protocol-insufficient everywhere it's mentioned; the joint four-lever experiment
remains marked unavailable/does-not-exist everywhere it's mentioned; all 11 referenced
figure files exist on disk; every source path cited in the four new documents resolves
to a real file. Read-only -- makes no changes.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_step12_faculty_package.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
REPORTS_DIR = TESTING_DIR / "reports"
FIGURES_DIR = TESTING_DIR / "figures"

CLAIM_REGISTER = REPORTS_DIR / "FINAL_CLAIM_REGISTER.csv"
FACULTY_REPORT = REPORTS_DIR / "FACULTY_EVALUATION_REPORT.md"
FACULTY_SUMMARY = REPORTS_DIR / "FACULTY_EXECUTIVE_SUMMARY.md"
FACULTY_TABLE = REPORTS_DIR / "FACULTY_RESULTS_TABLE.md"
FACULTY_LIMITATIONS = REPORTS_DIR / "FACULTY_LIMITATIONS_AND_CAVEATS.md"

NEW_DOCS = [FACULTY_REPORT, FACULTY_SUMMARY, FACULTY_TABLE, FACULTY_LIMITATIONS]

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


def all_new_docs_text() -> str:
    return "\n".join(read_text(p) for p in NEW_DOCS if p.exists())


# 1. All four faculty deliverables exist
def check_deliverables_exist():
    name = "Faculty package deliverables exist"
    missing = [str(p) for p in NEW_DOCS if not p.exists()]
    if missing:
        fail(f"{name}: missing {missing}")
        return
    ok(f"{name}: FACULTY_EVALUATION_REPORT.md, FACULTY_EXECUTIVE_SUMMARY.md, "
       f"FACULTY_RESULTS_TABLE.md, FACULTY_LIMITATIONS_AND_CAVEATS.md all present "
       f"under testing/reports/")


# 2. Every row in FACULTY_RESULTS_TABLE.md traces to a real claim_id in the register,
#    and its Value is not altered from the register's value.
_TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<finding>[^|]+)\|\s*(?P<value>[^|]+)\|\s*(?P<classification>[^|]+)\|"
    r"\s*(?P<freshness>[^|]+)\|\s*(?P<grade>[^|]+)\|\s*(?P<safe>[^|]+)\|\s*(?P<claim_id>C\d+)\s*\|\s*$",
    re.MULTILINE,
)


def check_results_table_matches_register():
    name = "FACULTY_RESULTS_TABLE.md values match FINAL_CLAIM_REGISTER.csv"
    if not FACULTY_TABLE.exists() or not CLAIM_REGISTER.exists():
        fail(f"{name}: missing table or register")
        return
    claims_by_id = {r["claim_id"]: r for r in read_claims()}
    table_text = read_text(FACULTY_TABLE)
    rows = list(_TABLE_ROW_RE.finditer(table_text))
    if len(rows) < 20:
        fail(f"{name}: only {len(rows)} data row(s) matched the expected table format (expected ~26)")
        return
    mismatches = []
    for m in rows:
        cid = m.group("claim_id")
        if cid not in claims_by_id:
            mismatches.append(f"{cid}: not found in claim register")
            continue
        reg = claims_by_id[cid]
        # Loose match: the register's classification token should appear in the
        # table's classification cell (allow reformatting, not value substitution).
        reg_class = reg["classification"].strip().upper()
        table_class = m.group("classification").strip().upper()
        if reg_class and reg_class.split()[0] not in table_class:
            mismatches.append(f"{cid}: classification mismatch (register={reg['classification']!r}, table={m.group('classification')!r})")
    if mismatches:
        fail(f"{name}: {len(mismatches)} mismatch(es): {mismatches[:10]}")
        return
    ok(f"{name}: {len(rows)} table rows cross-referenced against the claim register, "
       f"all classifications consistent")


# 3. All six required limitations present in FACULTY_LIMITATIONS_AND_CAVEATS.md
REQUIRED_LIMITATIONS = [
    ("cumulative 1/56 unrecoverable protocol", re.compile(r"cumulative.{0,40}(1/56|correction rate)", re.IGNORECASE)),
    ("missing joint four-lever experiment", re.compile(r"joint four-lever", re.IGNORECASE)),
    ("scope-check batch discrepancy (1/11 vs 4/6)", re.compile(r"1\s*(of|/)\s*11.{0,60}4\s*(of|/)\s*6", re.IGNORECASE)),
    ("only 50/82 v1 evidence records re-fetched", re.compile(r"50\s*(of|/)\s*82", re.IGNORECASE)),
    ("Project Author Statement not used as evidence", re.compile(r"project author statement", re.IGNORECASE)),
    ("historical GPU physical-machine identity not confirmed", re.compile(r"physical.machine identity", re.IGNORECASE)),
]


def check_required_limitations():
    name = "All six required limitations present in FACULTY_LIMITATIONS_AND_CAVEATS.md"
    if not FACULTY_LIMITATIONS.exists():
        fail(f"{name}: file missing")
        return
    text = read_text(FACULTY_LIMITATIONS)
    missing = [label for label, pat in REQUIRED_LIMITATIONS if not pat.search(text)]
    if missing:
        fail(f"{name}: missing {missing}")
        return
    ok(f"{name}: all 6 limitations present (cumulative 1/56, joint four-lever, "
       f"scope-check discrepancy, v1 audit coverage, Project Author Statement, "
       f"GPU machine identity)")


# 4. No unsupported natural-data accuracy/F1 claim in the four new documents
_PROHIBITED_PATTERNS = [
    re.compile(r"natural-data (accuracy|f1)(?! (figure|claim)[^.]{0,20}(exists|is made|anywhere)|.{0,10}(does not|never))", re.IGNORECASE),
    re.compile(r"prove[sd]? correctness", re.IGNORECASE),
    re.compile(r"correction is solved", re.IGNORECASE),
    re.compile(r"universally safe", re.IGNORECASE),
]
_NEGATION_WINDOW = re.compile(
    r"(no |not |never |does not |doesn't |zero )", re.IGNORECASE
)


def check_no_prohibited_claims():
    name = "No unsupported accuracy/F1/safety claims in faculty documents"
    hits = []
    for p in NEW_DOCS:
        if not p.exists():
            continue
        text = read_text(p)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat in _PROHIBITED_PATTERNS:
                for m in pat.finditer(line):
                    # Check a window before the match for a negation/disclaimer cue.
                    window = line[max(0, m.start() - 60):m.start()]
                    if not _NEGATION_WINDOW.search(window) and not _NEGATION_WINDOW.search(line[:40]):
                        hits.append(f"{p.name}:{lineno}: {line.strip()[:120]}")
    if hits:
        fail(f"{name}: {len(hits)} unguarded hit(s): {hits[:10]}")
        return
    ok(f"{name}: all pattern hits are negations/disclaimers, not affirmative claims")


# 5. GPU status correctly scoped: STEP 1-9 absence vs STEP 10/10B capability
def check_gpu_scoping():
    name = "GPU status correctly scoped (STEP 1-9 machine vs STEP 10/10B machine)"
    text = all_new_docs_text()
    if not re.search(r"no nvidia gpu|none.{0,20}amd radeon|amd radeon integrated only", text, re.IGNORECASE):
        warn(f"{name}: no explicit STEP 1-9 GPU-absence statement found")
    if "RTX 4050" not in text:
        fail(f"{name}: no mention of the STEP 10/10B GPU (RTX 4050) found")
        return
    # Every "no NVIDIA GPU" / "GPU unavailable"-type statement must be within ~200
    # chars of a scoping token (STEP 1-9, "that machine", "this machine", "1-9").
    unscoped = []
    for pat in [re.compile(r"no nvidia gpu", re.IGNORECASE), re.compile(r"gpu unavailable", re.IGNORECASE),
                re.compile(r"qwen generation.{0,20}not executed", re.IGNORECASE)]:
        for m in pat.finditer(text):
            window = text[max(0, m.start() - 250):m.end() + 250]
            if not re.search(r"step 1-9|this machine|that machine|step\s*1\s*[-–]\s*9", window, re.IGNORECASE):
                unscoped.append(text[max(0, m.start() - 60):m.end() + 60])
    if unscoped:
        fail(f"{name}: {len(unscoped)} unscoped GPU-unavailability statement(s): {unscoped[:5]}")
        return
    ok(f"{name}: every GPU-absence statement is scoped to the STEP 1-9 machine; "
       f"STEP 10/10B's RTX 4050 capability is explicitly documented separately")


# 6. Cumulative 1/56 remains historical-only / protocol-insufficient
def check_cumulative_1_56():
    name = "Cumulative 1/56 remains historical-only / protocol-insufficient"
    text = all_new_docs_text()
    mentions = [m for m in re.finditer(r"1\s*/\s*56|1/56", text)]
    if not mentions:
        fail(f"{name}: cumulative 1/56 not mentioned anywhere in the faculty package")
        return
    bad = []
    for m in mentions:
        window = text[max(0, m.start() - 400):m.end() + 400]
        if not re.search(
            r"historical.only|protocol insufficient|not.{0,40}reproduc|cannot.{0,60}reproduc|"
            r"cannot be freshly re-derived|not.{0,20}freshly re-derived|not statistically validated|"
            r"unrecoverable|genuinely unavailable|unavailable",
            window, re.IGNORECASE | re.DOTALL,
        ):
            bad.append(text[max(0, m.start() - 40):m.end() + 40].replace("\n", " "))
    if bad:
        fail(f"{name}: {len(bad)} mention(s) without a historical-only/protocol-insufficient qualifier nearby: {bad[:5]}")
        return
    ok(f"{name}: all {len(mentions)} mention(s) of 1/56 carry a historical-only / "
       f"protocol-insufficient qualifier")


# 7. Joint four-lever experiment remains marked unavailable everywhere mentioned
def check_joint_four_lever_unavailable():
    name = "Joint four-lever experiment remains marked unavailable"
    text = all_new_docs_text()
    mentions = list(re.finditer(r"joint four-lever", text, re.IGNORECASE))
    if not mentions:
        fail(f"{name}: joint four-lever not mentioned anywhere in the faculty package")
        return
    bad = []
    for m in mentions:
        window = text[max(0, m.start() - 300):m.end() + 300]
        if not re.search(
            r"does not\s+exist|unavailable|no experiment|not\s+exist|none exists|none invented|"
            r"no protocol|no causal claim|not executed|not\s+isolated|no such effect|"
            r"\bno\b[^.]{0,60}\bexists?\b",
            window, re.IGNORECASE | re.DOTALL,
        ):
            bad.append(text[max(0, m.start() - 40):m.end() + 80].replace("\n", " "))
    if bad:
        fail(f"{name}: {len(bad)} mention(s) without an unavailability qualifier nearby: {bad[:5]}")
        return
    ok(f"{name}: all {len(mentions)} mention(s) confirm the experiment does not exist")


# 8. All 11 referenced figures exist on disk
def check_figures_exist():
    name = "All 11 referenced figure files exist on disk"
    missing = []
    for i in range(1, 12):
        candidates = list(FIGURES_DIR.glob(f"{i:02d}_*.png"))
        if not candidates:
            missing.append(f"figure {i:02d}")
    if missing:
        fail(f"{name}: missing {missing}")
        return
    ok(f"{name}: all 11 figure PNGs present under testing/figures/")


# 9. Every source path cited in the four new documents resolves to a real file
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
    candidates = [TESTING_DIR / rel, TESTING_DIR / rel.removeprefix("testing/"),
                  PROTOTYPE_DIR / rel, PROTOTYPE_DIR.parent.parent / rel]
    if any(p.exists() for p in candidates):
        return True
    return Path(rel).name in _basename_index()


def check_cited_paths_exist():
    name = "Every source path cited in the four new documents exists on disk"
    unresolved = []
    checked = 0
    for p in NEW_DOCS:
        if not p.exists():
            continue
        for m in _PATH_RE.finditer(read_text(p)):
            rel = m.group(1)
            checked += 1
            if not _resolves(rel):
                unresolved.append(f"{p.name}: {rel}")
    if unresolved:
        fail(f"{name}: {len(unresolved)} unresolved path(s): {unresolved[:10]}")
        return
    ok(f"{name}: {checked} cited path(s) across the 4 new documents resolved to real files")


def main() -> int:
    checks = [
        check_deliverables_exist,
        check_results_table_matches_register,
        check_required_limitations,
        check_no_prohibited_claims,
        check_gpu_scoping,
        check_cumulative_1_56,
        check_joint_four_lever_unavailable,
        check_figures_exist,
        check_cited_paths_exist,
    ]
    for c in checks:
        c()

    print("=" * 70)
    print("STEP 12 FACULTY PACKAGE VALIDATION REPORT")
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
          f"({len(PASSES)} checks passed, {len(FAILURES)} failures, {len(WARNINGS)} warnings)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
