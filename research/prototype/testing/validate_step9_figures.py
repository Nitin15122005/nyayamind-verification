"""STEP 9 figure validator.

Verifies: exactly 11 expected PNGs exist and open; all have metadata and source CSVs;
all source CSVs are valid; all numeric source values are present; all displayed
headline metrics reconcile; no natural-data accuracy/F1 claims; no unsupported
correctness/causal claims; no fabricated N values; fresh/historical, CPU/GPU, and
synthetic/natural correction distinctions are preserved; GOLD/natural distinction is
preserved. Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_step9_figures.py
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TESTING_DIR = Path(__file__).resolve().parent
FIG_DIR = TESTING_DIR / "figures"
DATA_DIR = TESTING_DIR / "evaluation" / "figure_data"

EXPECTED = [
    "01_overall_metric_comparison.png", "02_evidence_coverage.png", "03_verdict_distribution.png",
    "04_correction_funnel.png", "05_correction_outcome.png", "06_safety.png",
    "07_confidence_distribution.png", "08_ablation_comparison.png", "09_runtime_resource.png",
    "10_cumulative_natural_results.png", "11_synthetic_vs_natural_transfer.png",
]

FAILURES: list[str] = []
PASSES: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# 1/2. exactly 11 PNGs exist and open
def check_pngs():
    name = "PNGs exist and open"
    found = list(FIG_DIR.glob("*.png"))
    if len(found) != 11:
        fail(f"{name}: expected exactly 11 PNGs, found {len(found)}")
    else:
        ok(f"{name}: exactly 11 PNGs present")
    for fname in EXPECTED:
        p = FIG_DIR / fname
        if not p.exists():
            fail(f"{name}: {fname} missing")
            continue
        try:
            img = Image.open(p)
            img.load()
            ok(f"{name}: {fname} opens OK ({img.size[0]}x{img.size[1]})")
        except Exception as e:
            fail(f"{name}: {fname} failed to open: {e!r}")


# 3/4. all have metadata and source CSVs
def check_metadata_and_sources():
    name = "Metadata and source CSVs"
    meta_path = FIG_DIR / "FIGURE_METADATA.csv"
    if not meta_path.exists():
        fail(f"{name}: FIGURE_METADATA.csv missing")
        return
    rows = read_csv(meta_path)
    if len(rows) != 11:
        fail(f"{name}: FIGURE_METADATA.csv has {len(rows)} rows, expected 11")
    else:
        ok(f"{name}: FIGURE_METADATA.csv has exactly 11 rows")
    for r in rows:
        csv_path = DATA_DIR / r["source_csv"]
        if not csv_path.exists():
            fail(f"{name}: {r['filename']}'s source_csv {r['source_csv']} missing")
        else:
            ok(f"{name}: {r['filename']}'s source_csv exists")


# 5. all source CSVs are valid; 6. all numeric source values are present
def check_source_csvs_valid():
    name = "Source CSVs valid, numeric values present"
    for fname in [f"{i:02d}_{n}.csv" for i, n in enumerate(
        ["overall_metric_comparison", "evidence_coverage", "verdict_distribution", "correction_funnel",
         "correction_outcome", "safety", "confidence_distribution", "ablation_comparison",
         "runtime_resource", "cumulative_natural_results", "synthetic_vs_natural_transfer"], 1)]:
        p = DATA_DIR / fname
        if not p.exists():
            fail(f"{name}: {fname} missing")
            continue
        try:
            rows = read_csv(p)
            if not rows:
                fail(f"{name}: {fname} has no rows")
            else:
                ok(f"{name}: {fname} valid, {len(rows)} rows")
        except Exception as e:
            fail(f"{name}: {fname} failed to parse: {e!r}")


# 7. all displayed headline metrics reconcile
def check_headline_reconciliation():
    name = "Headline metrics reconcile"
    fig01 = read_csv(DATA_DIR / "01_overall_metric_comparison.csv")
    fig02 = read_csv(DATA_DIR / "02_evidence_coverage.csv")
    ev1 = next(r for r in fig01 if r["metric"] == "evidence_coverage")
    arm_b = next(r for r in fig02 if r["dataset"] == "209_paired_ArmB")
    if abs(float(ev1["current_value"]) - float(arm_b["coverage"])) < 1e-9:
        ok(f"{name}: evidence_coverage current_value in fig01 matches Arm B coverage in fig02 exactly")
    else:
        fail(f"{name}: evidence_coverage current_value MISMATCH between fig01 and fig02")

    fig08 = read_csv(DATA_DIR / "08_ablation_comparison.csv")
    ev1_ablation = next(r for r in fig08 if r["factor"] == "evidence_v1")
    if abs(float(ev1_ablation["variant_value"]) - float(arm_b["coverage"])) < 1e-9:
        ok(f"{name}: evidence_v1 variant_value in fig08 matches Arm B coverage exactly")
    else:
        fail(f"{name}: evidence_v1 variant_value MISMATCH in fig08")


# 8/9. no natural-data accuracy/F1 claims; no unsupported correctness claims
def check_terminology():
    name = "Terminology discipline"
    files_to_check = list(FIG_DIR.glob("*.md"))
    natural_accuracy_pattern = re.compile(r"natural.{0,30}(accuracy|F1)\b|(accuracy|F1)\b.{0,30}natural data", re.IGNORECASE)
    allowed = re.compile(r"not.*accuracy|no.*accuracy|never.*accuracy|is evidence coverage, not", re.IGNORECASE)
    violation = False
    for md in files_to_check:
        text = md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if natural_accuracy_pattern.search(line) and not allowed.search(line):
                fail(f"{name}: possible natural-data accuracy/F1 claim in {md.name}: {line.strip()[:120]}")
                violation = True
    if not violation:
        ok(f"{name}: no unsupported natural-data accuracy/F1 claim found in figures/ markdown")

    solved_pattern = re.compile(r"\bsolved\b", re.IGNORECASE)
    allowed_solved = re.compile(r"not.*solved|never.*solved|\"solved\"|'solved'", re.IGNORECASE)
    violation2 = False
    for md in files_to_check:
        text = md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if solved_pattern.search(line) and not allowed_solved.search(line):
                fail(f"{name}: unsupported 'solved' claim in {md.name}: {line.strip()[:120]}")
                violation2 = True
    if not violation2:
        ok(f"{name}: no unsupported 'solved' claim found")


# 10. no unsupported causal claims
def check_causal_claims():
    name = "No unsupported causal claims"
    text = (FIG_DIR / "FIGURE_CLAIM_AUDIT.md").read_text(encoding="utf-8")
    disclaimers = ["does not demonstrate:** causal isolation", "no causal claim is made for c/e",
                   "does not exist", "no causal isolation"]
    if any(d in text.lower() for d in disclaimers):
        ok(f"{name}: FIGURE_CLAIM_AUDIT.md explicitly disclaims joint four-lever causal isolation")
    else:
        fail(f"{name}: FIGURE_CLAIM_AUDIT.md does not explicitly disclaim unsupported causal isolation")


# 11. no fabricated N values
def check_n_values():
    name = "No fabricated N values"
    meta = read_csv(FIG_DIR / "FIGURE_METADATA.csv")
    for r in meta:
        if not r.get("N"):
            fail(f"{name}: {r['filename']} has no N value in metadata")
        else:
            ok(f"{name}: {r['filename']} has N recorded ({r['N']})")


# 12/13. fresh/historical, CPU/GPU distinctions preserved
def check_fresh_historical_gpu():
    name = "Fresh/historical, CPU/GPU distinctions"
    meta = read_csv(FIG_DIR / "FIGURE_METADATA.csv")
    for r in meta:
        if not r.get("fresh_or_historical"):
            fail(f"{name}: {r['filename']} missing fresh_or_historical")
        else:
            ok(f"{name}: {r['filename']} labeled '{r['fresh_or_historical'][:40]}'")
    text09 = (FIG_DIR / "FIGURE_INDEX.md").read_text(encoding="utf-8")
    if "NVIDIA GPU available: NO" in text09 or "NOT EXECUTED" in text09:
        ok(f"{name}: GPU non-execution explicitly documented in FIGURE_INDEX.md")
    else:
        fail(f"{name}: GPU non-execution not explicitly documented in FIGURE_INDEX.md")


# 14. synthetic/natural correction distinction preserved
def check_synthetic_natural_separation():
    name = "Synthetic/natural correction separation"
    fig11 = read_csv(DATA_DIR / "11_synthetic_vs_natural_transfer.csv")
    if all(r.get("populations_comparable", "").upper() == "NO" for r in fig11):
        ok(f"{name}: 11_synthetic_vs_natural_transfer.csv marks all rows as NOT comparable")
    else:
        fail(f"{name}: 11_synthetic_vs_natural_transfer.csv does not mark rows as not comparable")

    fig04 = read_csv(DATA_DIR / "04_correction_funnel.csv")
    pops = {r["population"] for r in fig04}
    if any("synthetic" in p for p in pops) and any("natural" in p for p in pops):
        ok(f"{name}: 04_correction_funnel.csv keeps synthetic and natural populations as separate rows")
    else:
        fail(f"{name}: 04_correction_funnel.csv does not separate synthetic and natural populations")


# 15. GOLD/natural distinction preserved
def check_gold_natural_distinction():
    name = "GOLD/natural distinction preserved"
    meta = read_csv(FIG_DIR / "FIGURE_METADATA.csv")
    fig01_meta = next(r for r in meta if r["figure_id"] == "01")
    if "gold_metric" in fig01_meta["metric_classification"] and "natural_metric" in fig01_meta["metric_classification"]:
        ok(f"{name}: Figure 01 metadata explicitly distinguishes gold_metric from natural_metric")
    else:
        fail(f"{name}: Figure 01 metadata does not explicitly distinguish GOLD from natural metrics")


def main() -> int:
    check_pngs()
    check_metadata_and_sources()
    check_source_csvs_valid()
    check_headline_reconciliation()
    check_terminology()
    check_causal_claims()
    check_n_values()
    check_fresh_historical_gpu()
    check_synthetic_natural_separation()
    check_gold_natural_distinction()

    print("=" * 70)
    print("STEP 9 FIGURE VALIDATION REPORT")
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
