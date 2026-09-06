# Source of this fixture

| | |
|---|---|
| File | `run_synthetic_stress.jsonl` |
| Copied from | `research/prototype/outputs/run_synthetic_stress.jsonl` (frozen, unmodified) |
| Copy date | 2026-09-05 |
| SHA-256 (canonical, current — this copy AND the source) | `717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5` |
| Record count | 59 |
| Built by | `research/prototype/src/synthetic_stress.py::build_synthetic_stress_claims()` |
| Label provenance | Deterministic mechanical inversion of real canonical statute text — every record is CONTRADICTED by construction |

This is a byte-for-byte copy. If this hash ever stops matching a fresh hash of the
original file, this fixture is stale and must be re-copied, not hand-edited.

**Hash reconciliation note (2026-09-06)**: this fixture's hash was originally recorded
incorrectly as `2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516` across
this workspace's documentation and validators (traced to a single error made at this
workspace's creation commit — see `PASS1_5_VERIFICATION_REPORT.md`). A dedicated
investigation confirmed via full git history that **no version of this file, source or
copy, has ever had that hash** — the value above (`717378e8...`) is the sole hash this
file has ever had, confirmed byte-identical between source and copy. Some frozen
historical run records (`actual_outputs/gold_benchmark_runs/gold02_synthetic/gold02_metrics.json`,
`.../run_metadata/gold02_run.meta.json`) still cite the old, incorrect value — those are
preserved unmodified as historical records, not corrected, per an explicit decision to
never rewrite frozen provenance. `scripts/validate_gold_benchmark_outputs.py` treats that specific,
known discrepancy as a labeled "HISTORICAL METADATA INCONSISTENCY" warning, never as a
fixture-integrity failure.
