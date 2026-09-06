# GOLD Hash Reconciliation — Report

**Date**: 2026-09-06. **Scope**: narrow reconciliation only, per your decision — no PASS 2,
no reorganization, no modification of frozen historical run-metadata JSON files. Follows
`PASS1_5_VERIFICATION_REPORT.md`, which established the root cause.

## Decision implemented

The historical incorrect GOLD hashes (`962de21e...` for GOLD-01, `2dba39cc...` for
GOLD-02) remain **permanently preserved, unmodified**, in:
- `actual_outputs/step4_gold_verifier/gold01_controlled/gold01_metrics.json`
- `actual_outputs/step4_gold_verifier/run_metadata/gold01_run.meta.json`
- `actual_outputs/step4_gold_verifier/gold02_synthetic/gold02_metrics.json`
- `actual_outputs/step4_gold_verifier/run_metadata/gold02_run.meta.json`

Nothing in this pass wrote to any of these four files. Verified by `git diff --stat` (see
§ "Confirmations" below).

## `validate_step4_outputs.py` — what changed

Added a three-way classification, applied identically to both the metrics JSON and the
run-metadata JSON for each GOLD dataset:

1. **Fixture integrity** (unchanged behavior, now using the corrected canonical hash from PASS 1.5): `sha256_of(fixture)` compared directly against the canonical hash. A mismatch here is still a hard **FAILURE** — this is the one check that can legitimately mean the live file is corrupted or tampered with, so it was never weakened.
2. **Historical metadata — known, explained inconsistency**: if a frozen record's `dataset_sha256` equals the *specific, already-investigated* stale value (not just "anything different from canonical"), it's now reported as a **WARNING** labeled `HISTORICAL METADATA INCONSISTENCY (not a fixture-integrity failure)`, with the canonical hash, the file path, and a pointer to `PASS1_5_VERIFICATION_REPORT.md` all stated inline.
3. **Anything else — unexplained**: a `dataset_sha256` that matches *neither* the canonical hash *nor* the known stale value is still a hard **FAILURE**, since that would be a genuinely new, uninvestigated discrepancy, not the one already accounted for.

This satisfies all five of your requirements: (1) fixture integrity is validated against
the corrected canonical hash, (2) the historical inconsistency is detected and reported
under its own distinct label, (3) it is classified as a warning, never as fixture
corruption, (4) the discrepancy stays fully visible in the printed report (file path,
both hash values, and explanation, for all 4 occurrences), and (5) nothing was
suppressed or rewritten — the check runs and reports every time.

A `WARNINGS` list/`warn()` function was added to the script (matching the pattern
already used in `validate_step7_ablation.py` elsewhere in this workspace), and the final
report format now prints a `WARNINGS (n):` section between `PASSED` and `FAILURES`,
consistent with that existing convention.

## Documentation updated

`expected_outputs/controlled_benchmark_gold/SOURCE.md` and
`expected_outputs/synthetic_stress_gold/SOURCE.md` — each now states, in one place, all
three values your instruction asked to distinguish:
- the **canonical current hash** (labeled explicitly as "canonical, current — this copy AND the source"),
- **confirmation of byte identity** between source and copy (already stated; unchanged),
- the **stale historical recorded hash**, with an explanation of where it came from, which files still carry it, and why they're left unmodified.

No other documentation file was changed in this pass — `MANIFEST.md`, `inputs/README.md`,
and `PROVENANCE.md` already carry the corrected canonical hash and (for `PROVENANCE.md`)
an explanatory annotation from PASS 1.5; re-editing them was not necessary to satisfy
your distinguishing requirement, since the two `SOURCE.md` files are this project's
designated per-fixture provenance record.

## Validators run

| Validator | Result |
|---|---|
| `validate_step4_outputs.py` | **PASS** — 36 passed, **4 warnings** (2 per GOLD dataset: metrics JSON + run-metadata JSON), 0 failures |
| `validate_inputs.py` | PASS — 38 passed, 0 warnings, 0 failures |
| `validate_step7_ablation.py` | PASS — 50 passed, 0 warnings, 0 failures |
| `validate_step8_consolidation.py` | PASS — 75 passed, 0 warnings, 0 failures |
| `validate_figure_data.py` | PASS — 54 passed, 0 warnings, 0 failures |
| `pytest research/prototype/tests/ -q` | **205 passed**, 1 unrelated deprecation warning, unaffected |

## Confirmations

- **GOLD files unchanged**: `git diff --stat` against HEAD for both GOLD fixtures (source in `outputs/` and copy in `expected_outputs/`) is empty — zero bytes touched.
- **Historical metadata unchanged**: `git diff --stat` against HEAD for `gold01_metrics.json`, `gold02_metrics.json`, `gold01_run.meta.json`, `gold02_run.meta.json` is empty — zero bytes touched.
- **No production files modified**: `git status --short` for `research/prototype/src/`, `research/prototype/tests/`, `research/prototype/config/`, `research/data/`, `research/prototype/final_demo_pack/`, `research/prototype/final_comparison/` is empty.
- **Files actually changed this turn** (3 total): `validate_step4_outputs.py`, `expected_outputs/controlled_benchmark_gold/SOURCE.md`, `expected_outputs/synthetic_stress_gold/SOURCE.md`.

## Net effect

The open item from `PASS1_5_VERIFICATION_REPORT.md` §L is now resolved without touching
any historical record: `validate_step4_outputs.py` reports **PASS** (not FAIL) end to
end, the historical inconsistency remains fully visible as 4 labeled warnings rather than
being hidden or miscategorized as data corruption, and the frozen provenance records are
byte-for-byte exactly as they were.

---

**STOPPING per your instruction. Not starting PASS 2.**
