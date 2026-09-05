# Final Release Audit — STEP 13

**Audit type**: independent, skeptical cross-check of the entire `research/prototype/testing/`
workspace (STEP 1 through STEP 12), performed before any Git commit is considered.
This audit re-derived answers from source files directly rather than trusting prior
steps' own self-reported PASS results — see "Method" below.

**Audited on**: 2026-09-05, commit `4e221ba` (working tree, uncommitted).

## Overall release status

**PASS.** All 12 audit phases completed. No genuine numerical inconsistency, orphan
claim, classification violation, unscoped GPU-unavailability statement, or weakened
caveat was found anywhere in the workspace. One documentation-completeness observation
was found (see "Audit check summary", Phase 8) — it is not a defect and does not block
release; it is reported for completeness, per this audit's own no-hiding-limitations
rule.

## Method

This audit did not simply re-run STEP 10/10B/11/12's own validators and accept their
PASS verdicts. It independently: parsed `FINAL_CLAIM_REGISTER.csv` and cross-checked a
sample of its rows against `FACULTY_RESULTS_TABLE.md`'s copied values; grepped every
occurrence of the highest-risk phrases (`1/56`, `joint four-lever`, `GPU unavailable`,
`accuracy`, `289`) across every reconciliation and faculty document and read the
surrounding context by hand for a representative subset before writing any automated
check; independently opened `outputs/final_metrics.json` to confirm the 56/1/0 and
30+36=66 correction-attempt arithmetic; and wrote a new validator
(`validate_step13_release_audit.py`) rather than re-running STEP 12's validator
unmodified. Three of that new validator's first-draft checks initially failed on
genuine false positives in its own regex windows (a self-referential audit sentence
quoting the phrase "GPU unavailable," and two limitation mentions using phrasing —
"no recoverable protocol," "confirmed absent," "never designed" — the first-draft
patterns didn't anticipate); each was individually confirmed by hand to be a validator
defect, not a content defect, before the pattern was widened. This is disclosed rather
than silently fixed, consistent with every prior step's own practice.

## Audit check summary (by phase)

| Phase | Result | Notes |
|---|---|---|
| 1. Workspace inventory | PASS | All 10 required directories present (`inputs/`, `expected_outputs/`, `actual_outputs/`, `comparisons/`, `component_tests/`, `integration_tests/`, `ablation/`, `evaluation/`, `figures/`, `reports/`). 46 distinct path-like references across the 3 STEP 11 documents plus the 4 STEP 12 documents all resolved on first correct check (two initial "unresolved" hits were the checker script's own missing `src/` → `research/prototype/src/` prefix handling, not broken references — confirmed by direct file listing). No duplicate/conflicting "canonical" document found: `CANONICAL_METRICS.csv` (STEP 8, per-metric) and `FINAL_CLAIM_REGISTER.csv` (STEP 11, faculty-claim-scoped) coexist as complementary, non-conflicting layers with agreeing values, not competing canonical sources. |
| 2. Traceability audit | PASS | Every row of `FACULTY_RESULTS_TABLE.md` (26/26) carries a `[Claim ID]` back to `FINAL_CLAIM_REGISTER.csv`; spot-checked 9 rows' Value fields against the register directly — all matched (allowing only display rounding, e.g. `0.7333` for `0.7333333333333333`). Sampled the main report's and executive summary's numeric claims for orphans — none found; all non-register numbers found (version strings, step numbers, GOLD-01/02 benchmark labels) are not claims requiring a register entry. |
| 3. Numerical consistency | PASS | Independently re-derived from `outputs/final_metrics.json`: synthetic correction attempts 30 (bare) + 36 (labeled) = 66; cumulative natural attempts 56; combined 122 — matches C22's "0 of 122 total attempts (56 natural + 66 synthetic)" exactly. GOLD-01/02, 209-claim, 588-claim, and GPU-reproduction figures all matched their cited source rows on direct comparison. No mismatch found. |
| 4. Classification audit | PASS | Every "accuracy" occurrence in the 4 faculty documents is either explicitly scoped to GOLD-01/02 (which have real ground truth) or is itself the disclaimer that no natural-data accuracy exists. GOLD classification (C01-C06) is applied only to the two controlled/synthetic-stress benchmarks; all natural-data rows (C07, C08, C14, C15, C17-C19, C24) are METRIC-ONLY. Cumulative 1/56, joint four-lever, and narrow re-verification classifications all confirmed unchanged and consistently applied (see Phase 5/6 below). |
| 5. GPU claim audit | PASS | No unqualified "GPU unavailable"/"no NVIDIA GPU" sentence found anywhere in `reports/` — every occurrence is explicitly scoped to the STEP 1-9 machine (by name, by "this machine"/"that machine," or by direct AMD Radeon contrast) or is itself a description of the audit check having found none. STEP 10/10B's RTX 4050 capability, real Qwen generation, real correction-pipeline execution, and the 209-claim exact GPU reproduction are all explicitly and separately stated. The physical-machine-identity caveat is present and reachable from the faculty package (`FACULTY_LIMITATIONS_AND_CAVEATS.md` §6). |
| 6. Limitation audit | PASS | All six required limitations are present in `FACULTY_LIMITATIONS_AND_CAVEATS.md`, each with its own headed subsection. Substance comparison against STEP 11's `FINAL_RECONCILIATION_REPORT.md` wording found no weakening — if anything, STEP 12's versions are more detailed (e.g. explicit "61% (50/82)" arithmetic added to the evidence-v1-coverage limitation) without changing the underlying claim. |
| 7. Figure audit | PASS | All 11 PNGs (`01_overall_metric_comparison.png` through `11_synthetic_vs_natural_transfer.png`) exist under `figures/`, and all 11 corresponding `figure_data/*.csv` source contracts exist. The faculty report's figure map cites all 11 filenames without typos. Figure 09's STEP-9-era "NVIDIA GPU available: NO / NOT EXECUTED" annotation is explicitly and directly qualified in the same table cell as "accurate for the STEP 1-9 machine... superseded, not contradicted, by STEP 10/10B" with a cross-reference to claims C11-C13 — a reader following the figure map from the faculty report cannot miss the correction. No figure was regenerated; none needed to be (STEP 10B reproduced identical, not different, numbers). |
| 8. Reproducibility audit | PASS, 1 observation | Canonical venv versions (Python 3.11.9, torch 2.2.2+cu121, transformers 4.40.2, accelerate 0.29.3, bitsandbytes 0.43.1) are documented consistently across STEP 10's PROVENANCE.md section and the faculty report's environment table. The CPU-machine (STEP 1-9) and GPU-machine (STEP 10/10B) identities are both stated with their distinguishing hardware facts. The 205-test regression result is asserted consistently everywhere it appears (never summed with the 289-count component-group breakdown without an explicit overlap disclaimer). No sentence claims reproducibility on "any machine" — the one "on any machine in this project's history" phrase in `FINAL_REPRODUCIBILITY_MATRIX.md` is a historical-scoping statement about STEP 8 (i.e., no machine *had* GPU capability at that time), not a forward-looking universality claim. **Observation** (not a failure): `PROVENANCE.md`'s step-by-step narrative has dedicated `## STEP N` sections through STEP 10B but none for STEP 11 or STEP 12 — those steps' work is fully documented in their own `reports/` deliverables instead, which is consistent with what STEP 11 and STEP 12 were actually asked to produce, but it means a reader who only reads `PROVENANCE.md` top-to-bottom (rather than also opening `reports/`) will not see STEP 11/12 logged there. This is a documentation-completeness gap worth closing in a future step if `PROVENANCE.md` is meant to be a complete single-file narrative, but it does not affect the correctness or traceability of any finding — every STEP 11/12 deliverable is independently readable and self-contained. |
| 9. Final validator | PASS | See below. |
| 10. Final pytest | PASS | See below. |
| 11. Git release safety | PASS | See below. |
| 12. Release manifest | Done | This document and `FINAL_WORKSPACE_MANIFEST.md`. |

## Traceability status

Every headline number checked in `FACULTY_EVALUATION_REPORT.md`, `FACULTY_EXECUTIVE_SUMMARY.md`,
and `FACULTY_RESULTS_TABLE.md` traces to a specific row of `FINAL_CLAIM_REGISTER.csv`
(C01-C26, contiguous, no gaps or duplicates) or to a directly cited canonical source file
that exists on disk. Zero orphan claims found.

## Numerical consistency

Zero discrepancies found between `FINAL_CLAIM_REGISTER.csv`, `evaluation/CANONICAL_METRICS.csv`,
`FINAL_RECONCILIATION_REPORT.md`, and the underlying raw artifacts (`outputs/final_metrics.json`,
`outputs/final_gpu_validation_metrics.json`, `testing/actual_outputs/step10b_gpu_experiments/step10b_final_gpu_validation_metrics.json`)
this audit independently re-opened and parsed.

## Classification integrity

GOLD / BEHAVIOR / METRIC-ONLY / HISTORICAL-ONLY / GPU-REPRODUCED / DIAGNOSTIC remain
strictly separated. No natural-data result carries accuracy/correctness language without
an explicit disclaimer in the same sentence or immediate context. No GOLD label is
applied to a natural or provisional dataset.

## GPU claim integrity

STEP 1-9 GPU absence is scoped to that machine everywhere it is mentioned. STEP 10/10B's
RTX 4050 GPU capability, real Qwen generation, real correction-pipeline execution, and
the exact 209-claim GPU reproduction are all stated plainly and are not conflated with
a claim that the *original* historical GPU runs were reproduced on the *identical
physical device* (the machine-identity caveat is preserved).

## Figure integrity

All 11 figures and their source contracts exist; all faculty-document figure references
are correct; Figure 09's stale-in-isolation annotation is contextually corrected at the
point of reference.

## Reproducibility status

Demonstrated on exactly two environments: the STEP 1-9 CPU-only machine (no NVIDIA GPU)
and the STEP 10/10B GPU machine (NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB VRAM, driver
592.82, CUDA 12.1 torch build). No claim of reproducibility beyond these two specific,
named environments was found anywhere in the audited documents.

## Known limitations (restated, unchanged)

1. Cumulative correction rate (1/56 = 1.8%) cannot be freshly reproduced — pooled
   rollup, no recoverable single script (confirmed non-reproducible by STEP 10B).
2. No joint four-lever experiment exists — never designed, none invented.
3. Scope-check-mode discrepancy (1/11 vs. 4/6) — different batches, unreconciled,
   neither number supersedes the other.
4. Evidence-v1 audit coverage is partial — only 50/82 records independently re-fetched.
5. The root-level "Project Author Statement" is not used as evidence anywhere.
6. Historical GPU runs' exact physical-machine identity is not independently confirmed
   — only GPU model/VRAM class matches.

None of these six is hidden, softened, or removed anywhere in the release package.

## Git safety status

`git status --short` confirms all changes are confined to `research/prototype/testing/`
(the full STEP 10 through STEP 13 addition set) plus the pre-existing, unrelated
`baseline/LegalSeg` submodule pointer diff (present before STEP 10 began, untouched by
this or any prior step in this sequence). Zero changes under `src/`, `tests/`,
`research/data/`, `research/prototype/outputs/`, `final_demo_pack/`, or
`final_comparison/`. Nothing has been committed.

## Conclusion

**FINAL RELEASE AUDIT PASSED — NyayaMind testing workspace is ready for review and Git commit.**
