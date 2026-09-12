# Architecture

Canonical source: `research/prototype/src/pipeline.py::run_case()` (orchestration),
`research/prototype/README.md` (detailed per-stage architecture diagram, kept close to
source — read that for full prose detail; this file gives the map and the
production/experimental split).

## Baseline architecture (NyayaMind v0)

Identical code to the modified system below; only configuration differs (see
`01_PROJECT_BRAIN.md` §4-5, `05_MODELS_AND_CONFIGURATIONS.md`). Diagram:
`research/prototype/results_phase3/diagrams/01_system_architecture/D01_baseline_architecture_nyayamind_v0.png`.

## Modified (production) architecture

Diagram: `research/prototype/results_phase3/diagrams/01_system_architecture/D02_modified_architecture_nyayamind_production.png`.
Side-by-side: `.../D03_baseline_vs_modified_side_by_side.png`.

## Complete end-to-end pipeline

```
INPUT: Case (case_text, from NyayaRAG)
   |
   v
PROCESSING
  [1] StatuteGroundingGenerator.generate()          src/generator.py            PRODUCTION
      Qwen2.5-7B-Instruct, 4-bit NF4, greedy, fixed seed=42
   v
  [2] claim_parser.extract_claims()                 src/claim_parser.py         PRODUCTION
      deterministic regex citation extraction; assertion_text / assertion_spans
      narrowing (semicolon / " while " / citation-keyword-boundary / parenthetical-
      gloss / "respectively" splits); Art./Arts. abbreviation recognized
   v
  [3] evidence_matcher.match_evidence()              src/evidence_matcher.py    PRODUCTION
      exact (provision_type, provision_number, subsection, act_norm) lookup,
      then Jaccard fuzzy Act-name fallback, against the 136-record v0+v1 pool
      ALTERNATIVE (src/retrieval_signals.py): BM25 / embedding fuzzy scoring — EVALUATED, REJECTED (less safe)
   v
VERIFICATION (Mode B/C only)
  [4] NLIVerifier.verify()                           src/verifier.py            PRODUCTION
      MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
      premise = labeled evidence text; hypothesis = assertion_text when it narrows
      AND narrow_primary_hypothesis=true (PRODUCTION default)
      EXPERIMENTAL EXTENSION: assertion_span_primary_hypothesis (builds hypothesis
      from assertion_spans for "respectively" claims) — evaluated, OFF by default
   v
  [5] Verdict assignment + negation safety gate       src/pipeline.py            PRODUCTION
      ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION (low-confidence downgrade);
      a CONTRADICTED verdict matching a known negation pattern is excluded from
      the correction-trigger list (verdict itself stays visible, only auto-fix suppressed)
   v
CORRECTION (Mode C only, first flagged non-negation-caveated claim)
  [6a] SelectiveCorrector.correct()  (LEGACY)         src/corrector.py           PRODUCTION
       whole-paragraph LLM regeneration, asked to copy every other sentence verbatim
  [6b] SelectiveCorrector.correct_assertion_span()    src/corrector.py           EXPERIMENTAL
       (ASSERTION-AWARE, splice-based) rewrites ONLY the flagged claim's own
       assertion_spans content fragment (spans[-1]); see 03_COMPONENTS.md
   v
SAFETY GATES (apply_selective_correction / apply_selective_correction_assertion_aware, src/pipeline.py)
  - _scope_violation(): every unflagged claim's required text must survive           PRODUCTION (both paths)
  - Unauthorized-citation-addition check                                            PRODUCTION (both paths)
  - Ordinal-integrity check                                                         PRODUCTION (both paths)
  - Sibling-regression re-verification                                              PRODUCTION (legacy: opt-in: CURRENT; assertion-aware: UNCONDITIONAL)
  - Structural-span-preservation check + span-validity check                        EXPERIMENTAL (assertion-aware path only)
   v
  [7] Re-parse + re-match + re-verify the corrected sentence                        PRODUCTION
   v
OUTPUT: final_field
  original | corrected | correction_failed | correction_scope_violation |
  correction_sibling_regression | correction_ordinal_ambiguous |
  correction_unauthorized_addition | correction_splice_unavailable* |
  correction_structural_span_lost* | correction_span_invalid*
  (* assertion-aware path only)
```

## Experimental branches (config-gated, off by default)

| Lever | Config key | Default |
|---|---|---|
| Assertion-span-built verification hypothesis | `verification.assertion_span_primary_hypothesis` | `false` |
| Splice-based ("assertion-aware") correction | `correction.assertion_aware` | `false` |
| BM25 fuzzy evidence matching | `evidence_matching.fuzzy_method` | `"jaccard"` (BM25/embedding available, not selected) |

Flipping any of these does not change which modules exist — both the legacy and experimental
correction paths, and all three retrieval fuzzy methods, are live code, reachable by config
alone. No behavior is deleted when a lever is off; it is simply not the code path executed.

## Diagrams (canonical, do not duplicate)

All under `research/prototype/results_phase3/diagrams/`:

| Diagram | File |
|---|---|
| Complete end-to-end pipeline | `02_end_to_end_pipeline/D04_complete_pipeline.png` |
| Claim parsing stage | `03_verification/D05_stage_claim_parsing.png` |
| Evidence retrieval stage | `03_verification/D06_stage_evidence_retrieval.png` |
| NLI verification stage | `03_verification/D07_stage_nli_verification.png` |
| Verdict application stage | `03_verification/D08_stage_verdict_application.png` |
| Legacy correction + re-verification | `04_correction/D09_stage_correction_and_reverification.png` |
| Assertion-aware correction (splice-based) flow | `04_correction/assertion_aware_correction_splice_flow.png` |
| Scope + safety gate stage | `05_safety/D10_stage_scope_and_safety_gate.png` |
| Final answer assembly | `02_end_to_end_pipeline/D11_final_answer_assembly.png` |
| Full data flow | `02_end_to_end_pipeline/D12_full_data_flow.png` |
| Pipeline modes A/B/C | `02_end_to_end_pipeline/D13_pipeline_modes_a_b_c.png` |

No new stage exists beyond what is listed above — this file is confirmed against
`research/prototype/src/pipeline.py::run_case()` directly, not inferred from documentation.
