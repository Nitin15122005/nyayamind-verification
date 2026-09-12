# NyayaMind Final Results

_Package generated 2026-09-12. See `README.md` for navigation and `sources/RESULT_INDEX.csv` /
`sources/SOURCE_MAP.csv` for full traceability of every number below._

## 1. Executive Summary

NyayaMind is a statutory-grounding verification and correction layer for AI-generated legal
case summaries. This package reports every legitimate experimental result produced across
this project's history, comparing **NyayaMind v0 (baseline)** against **NyayaMind (current
production)** — the same pipeline code, five configuration levers changed based on evidence.

Headline, evidence-graded:

- **Verifier (controlled, GOLD-01, n=420, labels exist):** macro F1 0.749 → 0.968, accuracy
  0.733 → 0.971 (McNemar p=4.16e-23). **GRADE A.**
- **Evidence coverage (paired natural, n=209, no labels — coverage, not accuracy):** 63.2% →
  70.3% (McNemar χ²=13.07, p=0.0003). **GRADE A.**
- **Claim parser (n=30 reparse):** 6/30 documents improved, 0 worsened (sign test p=0.03).
  **GRADE B.**
- **Correction shipping (cumulative project history, natural data):** 1/56 (1.8%), 0 unsafe.
  **GRADE B/C** (safety A, shipping rate small-n).
- **Two mechanisms evaluated and NOT promoted**, honestly reported as negative/inconclusive:
  `assertion_span_primary_hypothesis` (n=6) and `correction.assertion_aware` (0/10 shipped,
  same as legacy).
- **Retrieval alternatives (BM25, embeddings) evaluated and REJECTED** for production —
  materially less safe than Jaccard on adversarial near-miss Act names.

## 2. Baseline vs Modified System

See `README.md`'s table and `tables/headline_results/T07_model_and_configuration_comparison.md`
for the complete, exact configuration diff. Both systems run identical pipeline code; only
configuration differs. Figure: `figures/01_overview/F01_headline_baseline_vs_modified.png`.

## 3. Complete Architecture

- Baseline architecture: `diagrams/01_system_architecture/D01_baseline_architecture_nyayamind_v0.png`
- Modified architecture: `diagrams/01_system_architecture/D02_modified_architecture_nyayamind_production.png`
- Side-by-side: `diagrams/01_system_architecture/D03_baseline_vs_modified_side_by_side.png`
- Complete end-to-end pipeline: `diagrams/02_end_to_end_pipeline/D04_complete_pipeline.png`
- Full data flow: `diagrams/02_end_to_end_pipeline/D12_full_data_flow.png`
- Pipeline modes A/B/C: `diagrams/02_end_to_end_pipeline/D13_pipeline_modes_a_b_c.png`
- Out-of-scope reference baseline (RhetoricLLaMA/LegalSeg, different task/dataset, one-row
  smoke test only, no quantitative comparison made): `diagrams/01_system_architecture/D14_reference_baseline_rhetoricllama_out_of_scope.png`

## 4. Verifier Results

**Controlled benchmark, GOLD-01, n=420 real per-item labels** (`figures/02_verifier/`):

| Metric | Baseline (bare) | Modified (labeled) |
|---|---|---|
| Accuracy | 0.7333 | 0.9714 |
| Macro F1 | 0.7487 | 0.9684 |

Statistical test: McNemar (continuity-corrected), p=4.16e-23; exact sign test p=1.58e-30.
**GRADE A, SUPPORTED.**

- Per-class precision/recall/F1: `figures/02_verifier/F03_gold01_per_class_precision_recall_f1.png`,
  `tables/detailed_metrics/verifier_per_class_metrics.csv`
- Confusion matrices (3×3, ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION): `figures/02_verifier/F04_gold01_confusion_matrices.png`,
  `tables/detailed_metrics/confusion_matrices.csv`
- Confidence distribution / threshold sensitivity: `figures/02_verifier/F11_confidence_distribution_588.png`,
  `F12_confidence_threshold_sensitivity.png` — production threshold (0.70) sits within 0.0022
  (bare) / 0.0000 (labeled) macro-F1 of the empirical optimum, in a flat non-fragile plateau.

**Synthetic stress (GOLD-02, n=59, contradiction detection):** recall 0.356 (21/59) → 0.458
(27/59), no statistical test performed (source did not report one). `figures/02_verifier/F05_gold02_synthetic_contradiction_detection.png`.
**GRADE B.**

**NEW — assertion_span_primary_hypothesis (n=6 real "respectively" claims, CPU DeBERTa):**
4/6 claims changed verdict when verified against an `assertion_spans`-built hypothesis instead
of the full sentence (3 NEI→ENTAILED, 1 NEI→CONTRADICTED — a real generation error the diluted
hypothesis had masked). Zero ENTAILED↔CONTRADICTED reversals. `figures/02_verifier/assertion_span_verification_shift.png`,
`tables/detailed_metrics/assertion_span_verification_metrics.csv`. **EVALUATED, NOT PROMOTED**
(n too small) — **GRADE C.**

**NEW — narrow_primary_hypothesis (n=62 fresh GPU batch):** verdict distribution shift toward
more decisive verdicts (ENTAILED 5→9, CONTRADICTED 1→2, NEI 26→21 out of 32 evidence-matched
claims/arm); not independently significant at this n. `figures/08_natural_data/narrow_primary_hypothesis_verdict_shift.png`.
**PROMOTED (production default)** based on this plus prior smaller-n evidence — **GRADE B.**

## 5. Evidence and Retrieval

**Evidence coverage, 209-claim paired natural evaluation** — two distinct, clearly separated
analyses of the SAME source file (`evaluation/actual_outputs/natural_data_runs/209_paired/paired_209_metrics.json`):

| | Arm A (v0 pool) | Arm B (v1 pool) | Note |
|---|---|---|---|
| HISTORICAL (as originally recorded) | coverage n/a in this cell; CONTRADICTED=3 | CONTRADICTED=3 | both arms' own historical run |
| FRESH (re-verified this analysis pass, both under current labeled framing) | 63.16% coverage, CONTRADICTED=2 | 70.33% coverage, CONTRADICTED=3 | McNemar χ²=13.07, p=0.0003 on the coverage event |

**These are not the same number and must not be conflated** — see `sources/RESULT_INDEX.csv`
R01/R02 for the exact distinction. `figures/03_evidence_retrieval/F06_evidence_coverage_209_paired.png`.
**GRADE A, SUPPORTED.**

**Evidence coverage, 588-record corpus:** 60.2% (354/588) → 66.3% (390/588), +36 newly
covered. `figures/03_evidence_retrieval/F07_evidence_coverage_588_corpus.png`. NO_EVIDENCE
taxonomy: `figures/03_evidence_retrieval/F20_no_evidence_taxonomy.png` (wrong-act/edition 78,
provision-absent 140, unresolved-act 40, parser-defect-candidate 2, of 260 of 797).

**NEW — Retrieval fuzzy-method safety comparison** (136-record pool, 21 should-match + 9
adversarial should-NOT-match pre-registered cases): `figures/03_evidence_retrieval/retrieval_method_safety_comparison.png`,
`tables/detailed_metrics/retrieval_metrics.csv`.

| Method | Correct-accept | Correct-reject (adversarial) | Status |
|---|---|---|---|
| Jaccard | 19/21 (90.5%) | **9/9 (100%)** | **PRODUCTION** |
| BM25 | 21/21 (100%) | 3/9 (33.3%) | EVALUATED, REJECTED |
| Embedding | 21/21 (100%) | 2/9 (22.2%) | EVALUATED, REJECTED |

BM25/embedding accept every real match but are materially less safe on near-miss Act names
(e.g. Civil↔Criminal Procedure Code, Arbitration Act 1940↔1996, Income Tax Act↔Rules) at
production thresholds, and BM25 never reaches 100% safety across the full threshold sweep
(0.5–1.0); embedding reaches it only at threshold≥0.8, where correct-accept collapses to
16/21 (76%). Jaccard remains the sole production `fuzzy_method` **for this reason, not because
alternatives were untested.** **GRADE B, REJECTED for production.**

## 6. Parser Results

Commit `223eb9d` fix (claim parsing, acronym normalization, evidence matching) plus the later
Art./Arts. abbreviation fix (`c250a0e`): n=30 reparse, 6/30 documents improved (more claims
resolve to usable evidence), 0 worsened, exact sign test p=0.03125. `figures/04_parser/F21_claim_parser_fix_n30.png`,
`tables/detailed_metrics/parser_metrics.csv`. **GRADE B, SUPPORTED.**

Known real limitation (not a bug, confirmed root cause): two bundled-sentence shapes never
narrow via `assertion_text`/`assertion_spans` — a bare "Sections X and Y" listing with no
per-citation clause, and a "respectively" pattern followed by a trailing " while " clause
(the while-split's success blocks the respectively-split from applying to the earlier
citations). Confirmed directly against real documents (1953_10, 1955_16) in the n=10
assertion-aware correction replay — see §9 and `LIMITATIONS.md`.

## 7. Premise Framing

Bare → labeled: see §4 (GOLD-01, the controlled benchmark this lever was evaluated on).
Natural-data observation (147 claims, framing shift, HISTORICAL): ENTAILED 0/147 → 13/147,
CONTRADICTED 3/147 → 3/147. `figures/08_natural_data/F10_natural_147_framing_shift.png`. This
is a **BEHAVIORAL natural-data observation**, not restated as the same accuracy figure as the
GOLD-01 controlled result — they measure different things on different data.

## 8. Correction

**Complete funnel** (`tables/correction_safety/correction_funnel.csv`, `figures/05_correction/`):

| Population | Triggered | Scope-rejected | Not-ENTAILED | Shipped | Unsafe |
|---|---|---|---|---|---|
| Synthetic — baseline (bare) | 30/59 | 0 | 30 | 0 | 0 |
| Synthetic — modified (labeled) | 36/59 | 0 | 10 | 26 | 0 |
| Natural targeted — baseline (bare) | 5/209 | 2 | 3 | 0 | 0 |
| Natural targeted — modified (labeled) | 10/209 | 3 | 6 | 1 | 0 |
| Natural cumulative — project history | 56 | 18 | 37 | **1 (1.8%)** | 0 |
| **NEW** Fresh n=62 — OLD arm | 4/62 | — | 4 | 0 | 0 |
| **NEW** Fresh n=62 — CURRENT arm (production) | 5/62 | — | 5 | 0 | 0 |
| **NEW** Paired n=10 replay — LEGACY | 10 | 4 | 4 (incl. 2 sibling-regression*) | 0 | 0 |
| **NEW** Paired n=10 replay — ASSERTION-AWARE | 10 | 5 | 2 (+2 sibling-regression) | 0 | 0 |

\* Legacy sibling-regression counted within its own gate category; see `error_propagation_matrix.csv`
for the exact per-case first-failure-stage attribution of the assertion-aware row.

**Safety, all 132 project-wide correction attempts (122 historical + 10 new):** `tables/correction_safety/safety_results.csv`.
**Unsafe corrections shipped: 0 / 132.** `figures/06_safety/F15_safety_observations.png`.

## 9. Assertion-Span Mechanism

Treated as five separate, honestly distinguished pieces of evidence:

**A. Assertion-span VERIFICATION experiment** (n=6, §4/§9): evaluated, NOT promoted (n too
small — not because a defect was found).

**B. Assertion-span-AWARE CORRECTION architecture**: implemented 2026-09-12, then extended the
same day to consume the real parser-produced `assertion_spans` list (not just `assertion_text`)
— see `diagrams/04_correction/assertion_aware_correction_splice_flow.png`. 26 dedicated
deterministic tests (no GPU) confirm the splice, the new structural-span-preservation check,
and the new fail-closed `correction_span_invalid`/`correction_structural_span_lost` statuses
all behave correctly, including a real "respectively" claim
(`assertion_spans=['302','theft']`) confirmed against actual parser output.

**C. Parser-produced assertion_spans integration**: verified empirically, not just by
inspection — replaying the new code against all 9 real triggered attempts from the n=10 batch
(using the already-recorded corrector outputs, no fresh Qwen call) produced **0
target-fragment mismatches, 0 outcome mismatches** (`outputs/assertion_span_aware_integration_replay.json`).
Every one of these 10 real cases happens to have a 1-element `assertion_spans`, so this is a
genuine architecture completion with zero behavior change on existing data — the multi-span
path is verified via tests and a real-corpus-derived fixture, not yet by a natural GPU batch
that happens to contain a genuine multi-span correction case.

**D. Real correction evaluation** (n=10 paired, the exact 5 documents that triggered legacy
correction in the n=62 batch): **0/10 shipped under assertion-aware, identical to legacy's
0/10 on the same cases.** `figures/05_correction/assertion_aware_vs_legacy_correction_funnel.png`,
`figures/05_correction/error_propagation_first_failure_stage.png`. Investigated case-by-case,
not left unexplained:
- 2 documents hit a NEW scope violation legacy did not, because their `assertion_spans` never
  narrowed (the parser limitation in §6).
- The case that specifically motivated this mechanism (`1955_32`, real IPC evidence confirms
  Section 392=robbery, Section 395=dacoity/ten years) spliced correctly — a clean, isolated
  fix, sibling clause byte-identical — but was still blocked by the sibling-regression safety
  gate, because the SAME bundled sentence has a SECOND, independent, genuinely wrong claim
  that was never the target. This is the safety design substantively working, not a mechanism
  failure.

**E. Safety observations**: 0 unsafe shipments; the new structural-span and sibling-regression
checks are confirmed (via tests) to catch exactly the failure modes they were built for.

**F. Production status: EXPERIMENTAL.** `correction.assertion_aware` stays `false`.
Architecturally complete and correct; no demonstrated shipping-rate improvement.

## 10. Safety

Full safety table: `tables/correction_safety/safety_results.csv`. Covers: unsafe corrections
shipped (0/132), scope-gate rejections, sibling-regression rejections (both the historical
209-paired check and the new unconditional assertion-aware check), the two NEW fail-closed
checks (`correction_structural_span_lost`, `correction_span_invalid` — 0 occurrences in real
data, exercised only by tests), and retrieval adversarial wrong-accepts by method (§5).
**No formal 15-category red-team safety evaluation exists** — see `LIMITATIONS.md`.

## 11. Ablations

Complete table, every lever ever evaluated (13 rows): `tables/ablation/ablation_results.md`.
`figures/07_ablation/F16_ablation_evidence_strength.png` (pre-2026-09-06 levers only — the
figure was not regenerated to add 5 new rows since the underlying visualization would need a
redesign to stay legible at 13 rows; the complete data is in the table). Evidence grades A
(evidence_v1, premise_framing) through E (joint four-lever isolation — **NOT_ISOLABLE,
NOT_EXECUTED**, never inflated to look otherwise).

## 12. Controlled Benchmark

GOLD-01 (n=420) and GOLD-02 (n=59) are this project's only labeled datasets, both
deterministically constructed (not hand-labeled) — see `evaluation/MANIFEST.md` for their
SHA-256-hashed provenance. Every accuracy/precision/recall/F1/confusion-matrix number in this
package comes from one of these two datasets. See §4.

## 13. Natural Data

Never called "accuracy." Reported as evidence coverage, verdict distribution, paired outcome
shift, and correction-shipping counts — see §5, §7, §8, §9. `figures/08_natural_data/`.

## 14. Transfer Observations

The 147-claim natural framing shift (§7) is the clearest controlled→natural transfer signal
this project has: labeled framing's controlled-benchmark improvement (§4) is directionally
consistent with, but not the same measurement as, its natural-data ENTAILED-recovery
observation. No broad generalization claim is made — see `figures/08_natural_data/F19_synthetic_vs_natural_transfer.png`.

## 15. Failure Analysis

- Correction: dominant historical failure mode is no-op edits (generation-quality limitation)
  and claim-bundling scope violations (37 + 18 of 56 cumulative attempts).
- Assertion-aware correction (n=10): see the error-propagation breakdown in §9/§8 —
  `outputs/error_propagation_analysis.md` for the full narrative.
- Parser: two confirmed bundled-sentence shapes that never narrow (§6).

## 16. Resource / Runtime

MEASURED (not fabricated): 209-claim experiment 2040.9s/1539.2s (STEP10B), 7547 MiB VRAM
(RTX 4050, 6GB class); synthetic correction 644.5s (bare)/1412.8s (labeled), 7502 MiB.
`figures/01_overview/F17_runtime_resource.png`. **ENVIRONMENTAL OBSERVATION, not a formal
benchmark suite** — this machine's specific hardware and concurrent load at the time.

## 17. Overall Findings

NyayaMind's promoted production levers all have real, sourced, evidence-graded support. Two
mechanisms were built to a high engineering standard and evaluated honestly, and neither is
promoted because the evidence doesn't yet support it — this is reported as a legitimate
research outcome, not concealed or spun.

## 18. Limitations

See `LIMITATIONS.md`.

## 19. Final Research Status

See `RESEARCH_CLAIMS.md`'s closing section and `LIMITATIONS.md`.

---

## Visual QC (performed on every figure/diagram newly produced in this package)

Two real issues were found and fixed before finalizing:
1. `narrow_primary_hypothesis_verdict_shift.png` — the tallest bar's value label was clipped
   behind the legend box. Fixed by increasing the y-axis headroom and repositioning the
   legend.
2. `assertion_aware_vs_legacy_correction_funnel.png` — the y-axis label collided with the
   two-line title, and a "0" annotation collided with the x-tick labels. Fixed by splitting
   the title into a `suptitle`+subtitle pair, shortening the y-label, and removing the
   redundant "0" annotation (already stated in the caption and legend).
3. `assertion_aware_correction_splice_flow.png` (diagram) — an edge label ("regression
   found") overlapped the destination box's text. Fixed by increasing the label's vertical
   offset to clear the box.
All five new figures and one new diagram were re-inspected after fixes and confirmed clean.
The 25 reused figures and 14 reused diagrams were validated by the archived package's own
`validate_package.py` (PASS, 0 failures) and were not re-generated, only re-inspected for
correct placement in the new folder structure (not re-QC'd pixel-by-pixel, since their pixel
content is unchanged from the already-validated archived package).

## Duplication check

No PNG/CSV/diagram exists in more than one canonical location within this package. The `ppt/`
directory contains only three index markdown files (no image copies). Verified by directory
listing (30 figures across 8 topic folders, 15 diagrams across 5 topic folders, each filename
unique).

## Protected-file audit

`git status` before and after building this package shows only: `research/prototype/Output_phase_3_vedant/`
moved (via `git mv`) to `research/prototype/archive/2026-09-06_output_phase_3_vedant/`, and
new files created under `research/prototype/results_phase3/` plus the four small build
scripts under `research/prototype/scripts/`. No production source (`src/`), test, config, or
`research/data/` file was modified. `baseline/LegalSeg` remains untouched (pre-existing
modified-content artifact, present at the start of every session in this project).
