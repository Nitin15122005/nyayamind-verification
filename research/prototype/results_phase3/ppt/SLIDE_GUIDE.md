# Slide Guide — suggested mentor/faculty presentation order

References canonical figures/diagrams — build slides by embedding these files directly, never
by copying them into a new location.

| Slide | Topic | Primary asset(s) |
|---|---|---|
| 1 | Problem / motivation | (narrative — no figure required) |
| 2 | Why the existing pipeline is insufficient | `figures/01_overview/F01_headline_baseline_vs_modified.png` |
| 3 | Baseline architecture | `diagrams/01_system_architecture/D01_baseline_architecture_nyayamind_v0.png` |
| 4 | Modified NyayaMind architecture | `diagrams/01_system_architecture/D02_modified_architecture_nyayamind_production.png` |
| 5 | End-to-end pipeline | `diagrams/02_end_to_end_pipeline/D04_complete_pipeline.png` |
| 6 | Verifier results | `figures/02_verifier/F02_gold01_accuracy_macro_f1.png`, `F04_gold01_confusion_matrices.png` |
| 7 | Evidence / retrieval | `figures/03_evidence_retrieval/F06_evidence_coverage_209_paired.png`, `retrieval_method_safety_comparison.png` |
| 8 | Parser / premise framing | `figures/04_parser/F21_claim_parser_fix_n30.png`, `figures/02_verifier/F12_confidence_threshold_sensitivity.png` |
| 9 | Correction | `figures/05_correction/F13_correction_funnel.png`, `diagrams/04_correction/D09_stage_correction_and_reverification.png` |
| 10 | NEW: assertion-span-aware correction | `diagrams/04_correction/assertion_aware_correction_splice_flow.png`, `figures/05_correction/assertion_aware_vs_legacy_correction_funnel.png` |
| 11 | Safety | `figures/06_safety/F15_safety_observations.png`, `diagrams/05_safety/D10_stage_scope_and_safety_gate.png` |
| 12 | Ablation | `tables/ablation/ablation_results.md` (table, not a single figure — 13 rows) |
| 13 | Natural data | `figures/08_natural_data/F10_natural_147_framing_shift.png`, `narrow_primary_hypothesis_verdict_shift.png` |
| 14 | Failure analysis | `figures/05_correction/error_propagation_first_failure_stage.png` |
| 15 | Final findings | `README.md`'s "What can we claim?" section |
| 16 | Limitations / future work | `LIMITATIONS.md` |

## Notes for the presenter

- Slide 10 is the newest, most likely to draw questions. The honest headline is **"0/10
  shipped, same as legacy — but the mechanism is architecturally correct and safe."** Do not
  let this read as a failure slide; it demonstrates rigorous negative-result reporting, which
  is itself a research contribution.
- If asked "did you compare to another system," slide 3's out-of-scope note
  (`D14_reference_baseline_rhetoricllama_out_of_scope.png`) explains why RhetoricLLaMA/LegalSeg
  is not a quantitative baseline here (different task, different dataset).
- If asked about Docker: `ENVIRONMENT-BLOCKED` on the development machine, not attempted to be
  hidden or spun as passed.
