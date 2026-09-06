# Source of this fixture

| | |
|---|---|
| File | `controlled_verifier_benchmark.jsonl` |
| Copied from | `research/prototype/outputs/controlled_verifier_benchmark.jsonl` (frozen, unmodified) |
| Copy date | 2026-09-05 |
| SHA-256 (canonical, current — this copy AND the source) | `aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec` |
| Record count | 420 |
| Built by | `research/prototype/scripts/build_controlled_benchmark.py` |
| Label provenance | Deterministic construction rule — not model or human generated |

This is a byte-for-byte copy. If this hash ever stops matching a fresh hash of the
original file, this fixture is stale and must be re-copied, not hand-edited.

**Hash reconciliation note (2026-09-06)**: this fixture's hash was originally recorded
incorrectly as `962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99` across
this workspace's documentation and validators (traced to a single error made at this
workspace's creation commit — see `PASS1_5_VERIFICATION_REPORT.md`). A dedicated
investigation confirmed via full git history that **no version of this file, source or
copy, has ever had that hash** — the value above (`aad8018b...`) is the sole hash this
file has ever had, confirmed byte-identical between source and copy. Some frozen
historical run records (`actual_outputs/gold_benchmark_runs/gold01_controlled/gold01_metrics.json`,
`.../run_metadata/gold01_run.meta.json`) still cite the old, incorrect value — those are
preserved unmodified as historical records, not corrected, per an explicit decision to
never rewrite frozen provenance. `scripts/validate_gold_benchmark_outputs.py` treats that specific,
known discrepancy as a labeled "HISTORICAL METADATA INCONSISTENCY" warning, never as a
fixture-integrity failure.
