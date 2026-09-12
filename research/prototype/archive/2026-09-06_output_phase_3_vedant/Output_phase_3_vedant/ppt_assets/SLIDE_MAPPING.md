# SLIDE_MAPPING — suggested faculty presentation order

A 25-slide skeleton (roughly a 20-minute talk with 5 minutes of questions). Every asset named below exists in this package; PPT-optimised 16:9 variants live under `ppt_assets/figures/` and `ppt_assets/diagrams/` with the same filename.

**Say the system names exactly:** baseline = *NyayaMind v0 (pre-2026-08-27 baseline)*, modified = *NyayaMind (2026-08-27 production)*. Both run Qwen/Qwen2.5-7B-Instruct and MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli; only the configuration differs.

| # | Slide | Assets | Speaker note |
|---|---|---|---|
| 1 | Title and framing | `—` | Name both systems exactly: baseline NyayaMind v0 (pre-2026-08-27) vs modified NyayaMind 2026-08-27 production. State up front that this is a configuration A/B on one codebase. |
| 2 | The problem | `diagrams/D14_reference_baseline_rhetoricllama_out_of_scope.png` | LLMs name statutes that sound plausible but are wrong. Use D14 to close the obvious question about the LegalSeg baseline before it is asked. |
| 3 | Baseline architecture | `diagrams/D01_baseline_architecture_nyayamind_v0.png` | Establish what the baseline actually is before showing any number. |
| 4 | Modified architecture | `diagrams/D02_modified_architecture_nyayamind_production.png` | The highlighted panels are the whole contribution; walk them left to right. |
| 5 | What changed — one slide | `diagrams/D03_baseline_vs_modified_side_by_side.png` | The single most useful slide in a faculty review. Six of ten stages differ, all by configuration. |
| 6 | Complete pipeline | `diagrams/D04_complete_pipeline.png`<br>`diagrams/D13_pipeline_modes_a_b_c.png` | Use D13 only if the audience asks about modes; it prevents confusing modes with systems. |
| 7 | Headline results | `figures/F01_headline_baseline_vs_modified.png` | State explicitly that the four bars are four different kinds of measurement. Do not read them as one score. |
| 8 | Verifier performance on labelled data | `figures/F02_gold01_accuracy_macro_f1.png`<br>`figures/F04_gold01_confusion_matrices.png` | This is the only place accuracy language is legitimate. The confusion matrices explain WHY: 92 true-ENTAILED items answered NEI under a bare premise. |
| 9 | Where the gain lands | `figures/F03_gold01_per_class_precision_recall_f1.png`<br>`diagrams/D07_stage_nli_verification.png` | ENTAILED recall 0.50 → 1.00. Pair with D07 so the mechanism is visible, not just the bar. |
| 10 | Evidence retrieval on real data | `figures/F06_evidence_coverage_209_paired.png`<br>`diagrams/D06_stage_evidence_retrieval.png` | The strongest natural-data result: +7.2 pp, McNemar p = 3.01e-04, zero regressions. Say 'coverage', never 'accuracy'. |
| 11 | Evidence corpus at scale | `figures/F07_evidence_coverage_588_corpus.png`<br>`figures/F24_evidence_pool_composition.png` | 59 → 136 usable records, and what that bought at the 588-claim scale. |
| 12 | What the verifier actually outputs | `figures/F08_verdict_distribution_natural.png`<br>`figures/F11_confidence_distribution_588.png` | Descriptive only. This is the honest picture of natural-data behaviour: NEI dominates. |
| 13 | Premise framing on natural data | `figures/F09_premise_framing_natural_batches.png`<br>`figures/F10_natural_147_framing_shift.png` | Retrieval is held constant, so the shift is attributable to framing alone. Say 'more decisive verdicts', not 'more correct claims'. |
| 14 | Why so many claims find no evidence | `figures/F20_no_evidence_taxonomy.png` | Pre-empts the obvious criticism: a ~140-provision corpus, not a parser defect. Zero confirmed parser/matcher defects across 797 claims. |
| 15 | Correction and the safety layer | `diagrams/D09_stage_correction_and_reverification.png`<br>`diagrams/D10_stage_scope_and_safety_gate.png` | Lead with the mechanism before the numbers — the gates are the contribution here. |
| 16 | Correction results, honestly | `figures/F13_correction_funnel.png`<br>`figures/F14_correction_outcomes.png` | Almost every attempt is stopped by a gate. Present 0/5 → 1/10 as directional only. |
| 17 | Safety observations | `figures/F15_safety_observations.png`<br>`figures/F25_scope_gate_replay.png` | 0 unsafe of 122 attempts — an observation on a finite history, not a guarantee. |
| 18 | The transfer gap | `figures/F19_synthetic_vs_natural_transfer.png` | Show it rather than let a reviewer find it. 72.2% synthetic vs 1.8% natural are not the same measurement. |
| 19 | Ablations and evidence strength | `figures/F16_ablation_evidence_strength.png`<br>`figures/F12_confidence_threshold_sensitivity.png` | Grade A through E, including the Grade E gap. The threshold was deliberately not tuned. |
| 20 | Reproducibility | `figures/F22_gpu_reproduction_crosscheck.png`<br>`figures/F23_component_test_coverage.png`<br>`figures/F17_runtime_resource.png` | Byte-identical reproduction on a second GPU machine; 205/205 tests; realistic runtimes. |
| 21 | Coverage across every regime | `figures/F18_natural_regimes_coverage.png` | The full spread, never pooled. Use if the audience pushes on generalisation. |
| 22 | Parser fix (code-level ablation) | `figures/F21_claim_parser_fix_n30.png`<br>`diagrams/D05_stage_claim_parsing.png` | Optional. Keep it separate from the four configuration levers. |
| 23 | Data flow and provenance | `diagrams/D12_full_data_flow.png`<br>`diagrams/D11_final_answer_assembly.png` | Answers 'how do we know these numbers are real?' — every artifact traces back. |
| 24 | Limitations | `figures/F19_synthetic_vs_natural_transfer.png` | Read NOT_GENERATED_REGISTER.md aloud if pressed. No lawyer ground truth exists; NLI verdict is not legal correctness; the corpus is ~140 provisions; correction n is tiny. |
| 25 | Backup / appendix | `figures/F05_gold02_synthetic_contradiction_detection.png`<br>`diagrams/D08_stage_verdict_application.png`<br>`tables/T02_baseline_vs_modified_comparison.md`<br>`tables/T03_ablation_results.md` | Hold in reserve for detailed questions. |

## Three sentences to rehearse verbatim

1. "Both systems are the same code and the same two models — Qwen/Qwen2.5-7B-Instruct for generation and MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli for verification. What changed is four configuration levers."
2. "The accuracy numbers are on a labelled 420-item benchmark. On real case data we report evidence coverage and verdict distributions, because no correctness label exists for that data anywhere in this project."
3. "Nothing here is a claim about legal correctness. The verifier reports a small public NLI model's statistical confidence, and the repository stamps that disclaimer on every result it produces."

## Questions to expect, and where the answer lives

| Likely question | Asset that answers it |
|---|---|
| "Why not compare against the LegalSeg / RhetoricLLaMA baseline?" | `diagrams/D14_reference_baseline_rhetoricllama_out_of_scope.png` |
| "Is 70% coverage good? What is the accuracy?" | `figures/F08_verdict_distribution_natural.png` + NOT_GENERATED_REGISTER.md |
| "Why do so many claims have no evidence?" | `figures/F20_no_evidence_taxonomy.png` |
| "Only one correction ever shipped?" | `figures/F13_correction_funnel.png`, `figures/F14_correction_outcomes.png` |
| "Did you tune the threshold to get these numbers?" | `figures/F12_confidence_threshold_sensitivity.png` |
| "Can anyone else reproduce this?" | `figures/F22_gpu_reproduction_crosscheck.png`, `tables/T06a_gpu_reproduction_status.md` |
| "Which of your four changes actually caused the improvement?" | `figures/F16_ablation_evidence_strength.png` — and say plainly that the joint four-lever experiment does not exist (Grade E) |

