#!/usr/bin/env python3
"""Generates ppt_assets/FIGURE_INDEX.md and DIAGRAM_INDEX.md from the provenance files."""
from __future__ import annotations

import json
from pathlib import Path

_V2 = Path(__file__).resolve().parent.parent
F = _V2 / "figures"
D = _V2 / "diagrams"
P = _V2 / "ppt_assets"
P.mkdir(parents=True, exist_ok=True)


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


core = json.loads((F / "figure_provenance_core.json").read_text(encoding="utf-8"))
hist = json.loads((F / "figure_provenance_historical.json").read_text(encoding="utf-8"))

L = ["# FIGURE INDEX", "",
     "Every figure in the package, with its source artifact, evidence grade, n and caveat.",
     "",
     "`V2 FRESH` figures were regenerated on this machine for this package. `HISTORICAL` figures",
     "come from committed artifacts that could not be rerun (no GPU / Qwen uncached / missing packages).",
     ""]
for title, rows, tag in (("V2 FRESH figures", core, "V2 FRESH"),
                         ("HISTORICAL-evidence figures", hist, "HISTORICAL")):
    L += [f"## {title} ({len(rows)})", "",
          "| figure | grade | n | source artifact | caveat |",
          "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: x["figure"]):
        L.append(f"| `{esc(r['figure'])}` | {esc(r['evidence_grade'])} | {esc(r['n'])} | "
                 f"`{esc(r['source_artifact'])}` | {esc(r['caveat'])} |")
    L.append("")
L += ["## Deliberately absent", "",
      "- `figures/09_runtime/` contains **no chart**. A runtime comparison is not possible from this",
      "  session (historical numbers are GPU; fresh ones are CPU under a different major version).",
      "  See `figures/09_runtime/README.md` and `NOT_GENERATED_REGISTER.md` §4.", ""]
(P / "FIGURE_INDEX.md").write_text("\n".join(L), encoding="utf-8")
print(f"FIGURE_INDEX.md  ({len(core)} fresh + {len(hist)} historical)")

di = json.loads((D / "diagram_index.json").read_text(encoding="utf-8"))
L = ["# DIAGRAM INDEX", "",
     "All 14 diagrams are **structural**: they carry no performance numbers. Every stage name,",
     "function reference and gate name comes from the audited source at HEAD `fb4e98f` or the",
     "original codebase at root commit `0e37525`.", "",
     "| diagram | title | arm | what it shows | source of truth |",
     "|---|---|---|---|---|"]
for d in di:
    L.append(f"| `{esc(d['diagram_file'])}` | {esc(d['title'])} | {esc(d['original_or_latest_or_both'])} | "
             f"{esc(d['what_it_shows'])} | `{esc(d['source_of_truth'])}` |")
L += ["", "## Colour conventions (consistent across the whole package)", "",
      "| colour | meaning |", "|---|---|",
      "| grey `#8C8C8C` | ORIGINAL NyayaMind |",
      "| blue `#2A6099` | LATEST NyayaMind |",
      "| green `#3F8F4F` | component new or changed since ORIGINAL / production status |",
      "| red `#C44E52` | fail-closed safety gate |",
      "| amber `#DDA63A` | EXPERIMENTAL, built but OFF in production |",
      "| light grey `#9E9E9E` | EVALUATED AND REJECTED |", ""]
(P / "DIAGRAM_INDEX.md").write_text("\n".join(L), encoding="utf-8")
print(f"DIAGRAM_INDEX.md  ({len(di)} diagrams)")
