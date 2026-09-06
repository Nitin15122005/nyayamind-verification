"""STEP 9 Phase 8 -- automated image audit.

Checks every PNG for: existence, that it opens, nonzero dimensions, appropriate
resolution, no completely blank image, no extreme clipping (a crude heuristic:
detects if >99% of pixels are a single uniform color, which would indicate a blank
or nearly-blank render), expected filename, a corresponding FIGURE_METADATA.csv row,
a corresponding source CSV, and that the declared source artifact exists on disk.

Read-only. Does not modify any PNG or CSV.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/evaluation/figures/audit_figures.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image

FIG_DIR = Path(__file__).resolve().parent
TESTING_DIR = FIG_DIR.parent
RESEARCH_DIR = TESTING_DIR.parent.parent
DATA_DIR = TESTING_DIR / "evaluation" / "figure_data"

EXPECTED = [
    "01_overall_metric_comparison.png", "02_evidence_coverage.png", "03_verdict_distribution.png",
    "04_correction_funnel.png", "05_correction_outcome.png", "06_safety.png",
    "07_confidence_distribution.png", "08_ablation_comparison.png", "09_runtime_resource.png",
    "10_cumulative_natural_results.png", "11_synthetic_vs_natural_transfer.png",
]

MIN_WIDTH_PX = 1200
MIN_HEIGHT_PX = 600

FAILURES: list[str] = []
PASSES: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)


def load_metadata() -> dict[str, dict]:
    with (FIG_DIR / "FIGURE_METADATA.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["filename"]: r for r in rows}


def is_nearly_blank(img: Image.Image) -> bool:
    """Crude heuristic: True if >99% of sampled pixels share the same color."""
    small = img.convert("RGB").resize((100, 100))
    pixels = list(small.getdata())
    if not pixels:
        return True
    from collections import Counter
    counts = Counter(pixels)
    most_common_count = counts.most_common(1)[0][1]
    return most_common_count / len(pixels) > 0.99


def main() -> int:
    metadata = load_metadata()

    for fname in EXPECTED:
        p = FIG_DIR / fname
        if not p.exists():
            fail(f"File exists: {fname} is MISSING")
            continue
        ok(f"File exists: {fname}")

        try:
            img = Image.open(p)
            img.load()
        except Exception as e:
            fail(f"Image opens: {fname} failed to open: {e!r}")
            continue
        ok(f"Image opens: {fname}")

        w, h = img.size
        if w == 0 or h == 0:
            fail(f"Nonzero dimensions: {fname} has zero width/height")
        else:
            ok(f"Nonzero dimensions: {fname} is {w}x{h}")

        if w < MIN_WIDTH_PX or h < MIN_HEIGHT_PX:
            fail(f"Resolution appropriate: {fname} is {w}x{h}, below minimum {MIN_WIDTH_PX}x{MIN_HEIGHT_PX}")
        else:
            ok(f"Resolution appropriate: {fname} is {w}x{h} (>= {MIN_WIDTH_PX}x{MIN_HEIGHT_PX})")

        if is_nearly_blank(img):
            fail(f"Not blank: {fname} appears to be >99% a single uniform color (likely blank)")
        else:
            ok(f"Not blank: {fname} has varied pixel content")

        # crude "extreme clipping" heuristic: check for a large solid block of pure white
        # or pure black covering the whole canvas edge-to-edge (would indicate a render error)
        corners = [img.convert("RGB").getpixel((0, 0)), img.convert("RGB").getpixel((w - 1, 0)),
                   img.convert("RGB").getpixel((0, h - 1)), img.convert("RGB").getpixel((w - 1, h - 1))]
        if len(set(corners)) == 1 and corners[0] in ((255, 255, 255), (0, 0, 0)) and is_nearly_blank(img):
            fail(f"No extreme clipping: {fname} looks like a solid-color render failure")
        else:
            ok(f"No extreme clipping (heuristic): {fname} corners/content look normal")

        if fname not in metadata:
            fail(f"Metadata row exists: {fname} has no row in FIGURE_METADATA.csv")
        else:
            ok(f"Metadata row exists: {fname}")
            row = metadata[fname]
            source_csv = row.get("source_csv", "")
            if source_csv and not (DATA_DIR / source_csv).exists():
                fail(f"Source CSV exists: {fname}'s declared source_csv '{source_csv}' not found")
            elif source_csv:
                ok(f"Source CSV exists: {fname} -> {source_csv}")

            source_artifact = row.get("source_artifact", "")
            if source_artifact:
                # source_artifact may list multiple files separated by ';'
                any_found = False
                for part in source_artifact.split(";"):
                    part = part.strip()
                    candidates = [
                        TESTING_DIR / "actual_outputs" / part.replace("step4/", "gold_benchmark_runs/").replace("step6/", "natural_data_runs/"),
                        RESEARCH_DIR / "prototype" / part,
                        TESTING_DIR / part,
                    ]
                    if any(c.exists() for c in candidates):
                        any_found = True
                if any_found:
                    ok(f"Source artifact exists: {fname}")
                else:
                    fail(f"Source artifact exists: {fname}'s declared source_artifact '{source_artifact}' could not be resolved to an existing file")

    print("=" * 70)
    print("STEP 9 AUTOMATED IMAGE AUDIT")
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
