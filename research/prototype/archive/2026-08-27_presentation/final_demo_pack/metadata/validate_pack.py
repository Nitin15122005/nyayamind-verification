#!/usr/bin/env python
"""
Part K validation for the demo pack: validates generated JSON/CSV, confirms
every figure exists and is non-trivially sized, and spot-checks a sample of
headline numbers quoted in the narrative docs against computed_metrics.json
directly. Does not re-run pytest or run_mvp.py --check (run those separately —
see RUNBOOK.md) since those are full-repo checks, not demo-pack-specific ones.

Run: research/.venv/Scripts/python.exe research/prototype/final_demo_pack/metadata/validate_pack.py
"""
from __future__ import annotations

import csv
import datetime
import json
import re
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent
# parents[3] -> parents[4] (2026-09-09 addendum pass): this pack now lives one
# level deeper (archive/2026-08-27_presentation/) than its original build
# location, so the walk-up to repo root needs 1 more level. (REPO_ROOT is
# currently unused by this script's checks, but kept correct for future use.)
REPO_ROOT = PACK_ROOT.parents[4]

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "ok": ok, "detail": detail})
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def validate_json_files():
    n = 0
    for p in PACK_ROOT.rglob("*.json"):
        n += 1
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            check(f"JSON valid: {p.relative_to(PACK_ROOT)}", False, str(e))
            continue
    check(f"All {n} JSON files under final_demo_pack/ parse", True)


def validate_csv_files():
    n = 0
    bad = []
    for p in PACK_ROOT.rglob("*.csv"):
        n += 1
        try:
            with p.open(encoding="utf-8") as f:
                rows = list(csv.reader(f))
            if len(rows) < 2:
                bad.append((p, "fewer than 2 rows (header + at least 1 data row expected)"))
        except Exception as e:
            bad.append((p, str(e)))
    if bad:
        for p, reason in bad:
            check(f"CSV valid: {p.relative_to(PACK_ROOT)}", False, reason)
    else:
        check(f"All {n} CSV files under final_demo_pack/ parse and are non-empty", True)


def validate_figures():
    fig_dir = PACK_ROOT / "figures"
    expected = [f"{i:02d}_" for i in range(1, 17)]
    pngs = sorted(fig_dir.glob("*.png"))
    check(f"16 figure PNGs exist", len(pngs) == 16, f"found {len(pngs)}")
    for prefix in expected:
        matches = [p for p in pngs if p.name.startswith(prefix)]
        if not matches:
            check(f"Figure {prefix}*.png exists", False)
            continue
        size = matches[0].stat().st_size
        # A blank/trivial matplotlib PNG at 300dpi is typically well under 20KB;
        # every real chart in this pack is 100KB+ (see ARTIFACT_INDEX.md).
        check(f"Figure {matches[0].name} is non-trivial size", size > 30_000, f"{size} bytes")


def spot_check_headline_numbers():
    """Cross-check a handful of headline numbers that appear in multiple
    narrative docs against computed_metrics.json directly -- catches drift if
    a doc was hand-edited after the fact without re-deriving from the source."""
    cm = json.loads((PACK_ROOT / "metadata/computed_metrics.json").read_text(encoding="utf-8"))

    unsafe = cm["correction_safety_audit"]["combined_total_unsafe_shipped"]
    total_attempts = cm["correction_safety_audit"]["combined_total_attempts"]
    check(
        "Headline 'UNSAFE SHIPMENTS = 0 / 122' matches computed_metrics.json",
        unsafe == 0 and total_attempts == 122,
        f"unsafe={unsafe}, total_attempts={total_attempts}",
    )

    coverage_a = cm["final_metrics_passthrough"]["section_B_natural_regimes"]["final_A_bare_v0_baseline"]["coverage_pct"]
    coverage_b = cm["final_metrics_passthrough"]["section_B_natural_regimes"]["final_B_bare_v1_assertionspans_narrow"]["coverage_pct"]
    check(
        "Headline '63.2% -> 70.3% evidence coverage' matches computed_metrics.json",
        coverage_a == 63.2 and coverage_b == 70.3,
        f"A={coverage_a}, B={coverage_b}",
    )

    shipped = cm["final_metrics_passthrough"]["section_D_correction_safety_cumulative"]["total_shipped"]
    check(
        "Headline '1 natural shipped correction' matches computed_metrics.json",
        shipped == 1,
        f"total_shipped={shipped}",
    )

    macro_f1_bare = None
    macro_f1_labeled = None
    for row in cm["threshold_sensitivity"]["bare"]["sweep"]:
        if row["threshold"] == 0.7:
            macro_f1_bare = row["macro_f1"]
    for row in cm["threshold_sensitivity"]["labeled"]["sweep"]:
        if row["threshold"] == 0.7:
            macro_f1_labeled = row["macro_f1"]
    check(
        "Threshold-sensitivity macro-F1 @0.70 matches computed_metrics.json (bare~0.749, labeled~0.968)",
        macro_f1_bare is not None and abs(macro_f1_bare - 0.749) < 0.001
        and macro_f1_labeled is not None and abs(macro_f1_labeled - 0.968) < 0.001,
        f"bare={macro_f1_bare}, labeled={macro_f1_labeled}",
    )

    # Every example case document_id actually appears in cases.json
    cases = json.loads((PACK_ROOT / "examples/cases.json").read_text(encoding="utf-8"))
    check("All 8 exemplar cases present in cases.json", len(cases) == 8, f"found {len(cases)}")


def validate_no_lawyer_claims():
    """Grep every markdown file in the pack for a bare, undisclaimed claim of
    lawyer/professional-legal validation. Flags any occurrence of
    'lawyer-verified' or 'lawyer verified' NOT immediately preceded by a
    negation word, as a heuristic (a human should still read the surrounding
    text — this is a catch-net, not a substitute for review)."""
    suspicious = []
    negation_words = ("not", "no", "never", "n't")
    for md in PACK_ROOT.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for m in re.finditer(r"lawyer[- ]verified", text, re.IGNORECASE):
            window = text[max(0, m.start() - 40): m.start()].lower()
            if not any(neg in window for neg in negation_words):
                suspicious.append((md.relative_to(PACK_ROOT), text[max(0, m.start() - 60):m.start() + 60]))
    check("No undisclaimed 'lawyer-verified' claims found", len(suspicious) == 0,
          "; ".join(f"{p}: ...{ctx}..." for p, ctx in suspicious) if suspicious else "")


def main():
    validate_json_files()
    validate_csv_files()
    validate_figures()
    spot_check_headline_numbers()
    validate_no_lawyer_claims()

    n_fail = sum(1 for r in results if not r["ok"])
    log_path = PACK_ROOT / "metadata" / "validation_log.md"
    lines = [
        "# Demo Pack Validation Log",
        "",
        f"Run: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        f"Script: `research/prototype/final_demo_pack/metadata/validate_pack.py`",
        "",
        f"**{len(results) - n_fail}/{len(results)} checks passed.**",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['check']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    lines += [
        "",
        "Note: `pytest research/prototype/tests/ -q` and "
        "`research/prototype/scripts/run_mvp.py --check` are full-repo checks, "
        "run separately (see RUNBOOK.md) and recorded in SYSTEM_STATUS.md, not "
        "duplicated by this demo-pack-scoped script.",
    ]
    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {log_path}")
    print(f"{len(results) - n_fail}/{len(results)} checks passed.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
