# Reports

The faculty/reviewer-facing final report package for this evaluation workspace, written
last (STEP 12-13), once `inputs/`, `expected_outputs/`, `components/`, `evaluation/`,
`ablation/`, and `figures/` all had real content to cite. Every number in these
documents carries a citation back to a specific source artifact — see
`FINAL_CLAIM_REGISTER.csv` for the machine-readable version of every citation.

## Reading order

| # | File | Audience / purpose |
|---|---|---|
| 1 | `FACULTY_EXECUTIVE_SUMMARY.md` | Someone with 5 minutes, unfamiliar with the project |
| 2 | `FACULTY_EVALUATION_REPORT.md` | The full narrative — 16 sections plus a technical appendix (STEP-by-STEP source inventory, claim-safety-audit methodology) |
| 3 | `FACULTY_RESULTS_TABLE.md` | 26-row compact metrics table for quick lookup, formatted from `FINAL_CLAIM_REGISTER.csv` |
| 4 | `FACULTY_LIMITATIONS_AND_CAVEATS.md` | Every material limitation, standalone, for a reviewer who wants only the caveats |
| — | `FINAL_CLAIM_REGISTER.csv` | Machine-parseable claim-to-source register (C01-C26), the citation target for every `[C##]` tag above |
| — | `FINAL_REPRODUCIBILITY_MATRIX.md` | Experiment-by-experiment reproduction grid (CPU/GPU, fresh/historical) |
| — | `FINAL_WORKSPACE_MANIFEST.md` | Full deliverable-by-deliverable index of the entire `evaluation/` workspace |
| — | `FINAL_RELEASE_AUDIT.md` | The independent STEP-13 meta-audit of this whole package (traceability, numerical consistency, classification discipline) |

These four numbered documents are genuinely audience-tiered, not duplicates of each
other — each was checked for overlap during the PASS 2 cleanup and found to serve a
distinct purpose (5-minute read vs. full narrative vs. quick-lookup table vs.
caveats-only reference).

## `archive/`

`FINAL_RECONCILIATION_REPORT.md` (STEP 11) was moved here during PASS 2 — ~70% of its
content duplicated `FACULTY_EVALUATION_REPORT.md` almost verbatim. Its two genuinely
unique sections (the STEP 1→10B canonical source inventory, and the STEP 11 claim
safety audit) were carried forward into `FACULTY_EVALUATION_REPORT.md`'s new "Appendix:
Technical reconciliation detail" section; the original file is preserved in `archive/`
for anyone who wants the complete STEP 11 document as originally written.

## Provenance note

This directory's own `README.md` was, until PASS 2, a STEP-1 planning stub that said
"No reports exist here yet" — left untouched by PASS 1 (which was scoped elsewhere) even
after all 10 files above already existed. See `../archive/cleanup_history/CLEANUP_PASS1_MANIFEST.md` and this
workspace's PASS 2 plan for the full history.
