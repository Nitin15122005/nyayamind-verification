# Cleanup History

Process ledgers from this workspace's own PASS 1 / PASS 1.5 cleanup (2026-09-05),
archived here during PASS 2 (2026-09-06) because their job — recording what those two
passes did — is complete and is now also reflected in the live file structure they
describe. Neither file was edited when moved here.

| File | What it recorded |
|---|---|
| `CLEANUP_PASS1_MANIFEST.md` | The exact move/merge/delete ledger for PASS 1 (`component_tests/` → `components/`, `inputs/` consolidation, log deletions, `ablation/` reunification) |
| `HASH_RECONCILIATION_REPORT.md` | The `validate_step4_outputs.py` code change that separated GOLD-fixture integrity checks from historical-metadata staleness warnings |

**Not archived here**: `../../PASS1_5_VERIFICATION_REPORT.md` remains at the top of
`evaluation/` permanently (renamed from `testing/` in PASS 3A) — it holds the complete git-archaeology evidentiary trail behind
the GOLD hash reconciliation (commit-by-commit hash proof), which is reproducibility
material, not process narration, and was deliberately kept out of this archive.
