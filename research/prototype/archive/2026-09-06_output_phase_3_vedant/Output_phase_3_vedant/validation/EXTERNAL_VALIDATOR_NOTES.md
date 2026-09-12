# External validator results and one pre-existing, non-defect failure

Ten existing repository validators under `research/prototype/evaluation/scripts/` were run
against the repository while building this package. Raw output for each is in
`external_validators/`.

| Validator | Result |
|---|---|
| `validate_figures.py` | PASS (66 checks) |
| `validate_figure_data.py` | PASS (54 checks) |
| `validate_natural_data.py` | PASS (33 checks) |
| `validate_release_audit.py` | PASS (11/11, 1 informational warning) |
| `validate_faculty_package.py` | PASS (9 checks) |
| `validate_reconciliation.py` | PASS (10 checks) |
| `validate_gpu_experiments.py` | PASS (13 checks) |
| `validate_inputs.py` | FAIL (2) — **pre-existing, see below** |
| `validate_metrics_consolidation.py` | FAIL (2) — **pre-existing, see below** |
| `validate_ablation.py` | FAIL (4) — **pre-existing, see below** |

Plus, run for this package:

| Check | Result |
|---|---|
| `pytest research/prototype/tests/ -q` | **205 passed**, 0 failed (`pytest_research_prototype_tests.txt`) |
| `python research/prototype/scripts/run_mvp.py --check` | **All checks passed**; 136 usable evidence records, `use_evidence_v1=True` (`run_mvp_check.txt`) |
| `scripts/validate_package.py` (this package's own QC) | **PASS**, 0 failures, 0 warnings (`VALIDATION_REPORT.txt`) |

---

## The three failures are one pre-existing checkout artifact, not a modified file

All eight failing assertions across the three validators are the same two files:

- `research/prototype/outputs/controlled_verifier_benchmark.jsonl` (and its GOLD fixture copy
  under `evaluation/expected_outputs/controlled_benchmark_gold/`)
- `research/prototype/outputs/run_synthetic_stress.jsonl` (and its GOLD fixture copy under
  `evaluation/expected_outputs/synthetic_stress_gold/`)

Each validator hard-codes a raw SHA-256 for these files and reports "hash changed" /
"GOLD fixture modified" when it does not match.

### Root cause

This Windows working copy has `core.autocrlf = true`. Git stores the blobs with **LF** line
endings and materialises them with **CRLF** on checkout, so the bytes on disk differ from the
bytes in the commit while the content is identical. The hard-coded constants are the LF-blob
hashes.

Demonstrated directly:

| File | SHA-256 as on disk (CRLF) | SHA-256 after CRLF→LF | Validator constant |
|---|---|---|---|
| `controlled_verifier_benchmark.jsonl` | `962de21e…4287f99` | `aad8018b…a632bfec` | `aad8018b…a632bfec` ✅ |
| `run_synthetic_stress.jsonl` | `2dba39cc…2b3e9b516` | `717378e8…36289237d5` | `717378e8…36289237d5` ✅ |

After line-ending normalisation the content hashes match the validator constants **exactly**, so
no byte of legal or experimental content differs.

### Independent confirmation that nothing was modified

1. `git status --porcelain` reports exactly one entry for the whole repository:
   `?? research/prototype/Output_phase_3_vedant/` — no tracked file is modified, added or deleted.
2. Both files' on-disk timestamps (`2026-09-06 17:38`) predate the start of this package's work.
3. This package never opens either file for writing; it reads only the derived
   `gold01_metrics.json` / `gold02_metrics.json`.
4. Those two metrics files independently record `dataset_sha256` values of `962de21e…` and
   `2dba39cc…` — the **CRLF** hashes — i.e. the evaluation workspace's own STEP 4 run was
   executed on a Windows checkout in the same state.

### Consequence for this package

None. The affected files are inputs to GOLD-01 and GOLD-02, whose metrics this package cites from
`gold01_metrics.json` / `gold02_metrics.json`. Those metrics files carry the CRLF hashes and are
therefore self-consistent with the fixtures as they exist here.

**No repository file was changed to make any validator pass.** The three failures are reported
here as-is, with the cause identified, rather than worked around.
