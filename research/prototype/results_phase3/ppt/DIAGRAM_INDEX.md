# Diagram Index

References canonical diagrams only — no copies exist in this directory.

| # | File | Purpose | Components shown | Presentation use |
|---|---|---|---|---|
| D01 | diagrams/01_system_architecture/D01_baseline_architecture_nyayamind_v0.png | Baseline architecture | Generator, parser (no assertion narrowing), retrieval (v0 pool), verifier (bare), legacy correction | Baseline architecture slide |
| D02 | diagrams/01_system_architecture/D02_modified_architecture_nyayamind_production.png | Modified (production) architecture | Same + v1 pool, labeled premise, assertion_spans scope check, narrow reverification/primary hypothesis | Modified architecture slide |
| D03 | diagrams/01_system_architecture/D03_baseline_vs_modified_side_by_side.png | Side-by-side comparison | Both systems | Baseline vs modified slide |
| D14 | diagrams/01_system_architecture/D14_reference_baseline_rhetoricllama_out_of_scope.png | Out-of-scope reference baseline | RhetoricLLaMA/LegalSeg (different task) | "Why not compare to X" slide, if asked |
| D04 | diagrams/02_end_to_end_pipeline/D04_complete_pipeline.png | Complete end-to-end pipeline | All stages, input to final answer | End-to-end pipeline slide |
| D11 | diagrams/02_end_to_end_pipeline/D11_final_answer_assembly.png | Final answer assembly | final_field construction | Pipeline deep-dive |
| D12 | diagrams/02_end_to_end_pipeline/D12_full_data_flow.png | Full data flow | All data structures | Pipeline deep-dive |
| D13 | diagrams/02_end_to_end_pipeline/D13_pipeline_modes_a_b_c.png | Pipeline modes A/B/C | Generation-only / +verification / +correction | Pipeline deep-dive |
| D05 | diagrams/03_verification/D05_stage_claim_parsing.png | Claim parsing stage | claim_parser.extract_claims | Verification flow slide |
| D06 | diagrams/03_verification/D06_stage_evidence_retrieval.png | Evidence retrieval stage | evidence_matcher.match_evidence | Verification flow slide |
| D07 | diagrams/03_verification/D07_stage_nli_verification.png | NLI verification stage | NLIVerifier, premise framing | Verification flow slide |
| D08 | diagrams/03_verification/D08_stage_verdict_application.png | Verdict application stage | apply_verification | Verification flow slide |
| D09 | diagrams/04_correction/D09_stage_correction_and_reverification.png | LEGACY correction + re-verification | SelectiveCorrector.correct, scope/safety gates, re-verify | Correction flow slide (legacy) |
| **NEW** | diagrams/04_correction/assertion_aware_correction_splice_flow.png | ASSERTION-AWARE (splice-based) correction flow | _correction_target_spans, correct_assertion_span, _splice_assertion_correction, structural-span check, unconditional sibling-regression check | Correction flow slide (experimental extension) |
| D10 | diagrams/05_safety/D10_stage_scope_and_safety_gate.png | Scope + safety gate stage | pipeline._scope_violation and related gates | Safety flow slide |

## End-to-end diagram for a single strong presentation slide

Use **D04 (complete_pipeline.png)** as the primary end-to-end diagram. If the assertion-aware
correction extension needs to be shown as part of the end-to-end story, follow it immediately
with the **NEW assertion_aware_correction_splice_flow.png**, clearly labeled "experimental
extension, not production default" (production still uses the D09 legacy flow).
