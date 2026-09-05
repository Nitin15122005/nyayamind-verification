# Historical-Only Reference Artifacts

**Not inputs.** These are artifacts that contain JSON/CSV data and are referenced
throughout this project's documentation, but are not intentionally fed into any pipeline
component or test as an input — they are *compilations built from* historical results,
for presentation purposes. Listed here explicitly so their status is unambiguous: they
are evidence/reference material, never a fresh testing input, and never re-derived or
altered by this workspace.

## Why an input is different from "any file with data in it"

An **input** is an artifact intentionally fed into a component or the pipeline for a
test/evaluation — something a function actually reads as its argument (a case's
`case_text`, an evidence pool, a benchmark's `evidence_text`/`hypothesis`). A **historical
output** is something the system (or a presentation-layer script built on top of the
system's historical outputs) already produced. The fact that a historical output happens
to be stored as JSON does not make it an input to anything in this workspace — it is
already downstream of the pipeline, not upstream of it.

## Inventory

| Artifact | What it is | Why it's historical-only, not an input |
|---|---|---|
| `final_demo_pack/examples/candidate_pool.json` (8 categories) | A curated pool of illustrative real cases (contradicted catches, shipped corrections, scope violations, etc.), selected by `find_candidates.py` from already-committed natural outputs | It is a *selection of historical outputs for presentation*, not new data — feeding it back into a component would just re-run something already recorded |
| `final_demo_pack/examples/cases.json` (8 worked cases) | Hand-written narrative case studies built from the above pool by `build_cases_json.py` | Same — a presentation compilation of historical results, not a pipeline input |
| `final_comparison/comparison_config.json` | A hand-authored, machine-readable definition of what "ORIGINAL" vs. "CURRENT" config means, plus 7 named isolated A/B experiment pairs, each citing exact `outputs/` source files | A configuration/definition document for a comparison analysis, not something any pipeline component consumes as input |
| `final_comparison/tables/*.csv`, `final_demo_pack/tables/*.csv` | Computed tables built by `build_comparison_data.py`/`generate_tables.py` from `outputs/*` | Downstream computed results, not inputs |
| The `outputs/` status-report chain (`pre_gpu_readiness_report.md` → ... → `research_completion_report.md` → `research_phase_next_status.md`) | Sequential project-history checkpoints | Narrative history, not machine-readable input to any component |

## What this workspace does with these

References them directly at their frozen paths when a report needs to cite them (e.g.
`../../reports/README.md`'s planned Input/Output Walkthrough will draw on
`final_demo_pack/examples/cases.json`'s 8 worked cases as illustrative material) — never
copies, re-derives, or treats any of them as a fresh testing input.
