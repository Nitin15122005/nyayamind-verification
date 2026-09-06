# DIAGRAM_INDEX — system and flow diagrams

Each diagram exists twice: `diagrams/<name>.png` and
`ppt_assets/diagrams/<name>.png` (16:9 landscape, presentation type sizes).
Every component name, model id, config key and outcome label is read from the
repository's own source; no stage is invented.

### D01 — Baseline architecture — NyayaMind v0 (pre-2026-08-27 production configuration)

- **File:** `D01_baseline_architecture_nyayamind_v0.png`
- **Purpose:** Establish exactly what the baseline system is before any comparison
- **Systems shown:** Baseline: NyayaMind v0
- **Source:** config/prototype.yaml; comparison_config.json (ORIGINAL); src/*.py
- **Note:** Configuration A/B, not a code fork.

### D02 — Modified architecture — NyayaMind 2026-08-27 shipped production configuration

- **File:** `D02_modified_architecture_nyayamind_production.png`
- **Purpose:** Show exactly where the modified system adds functionality
- **Systems shown:** Modified: NyayaMind production
- **Source:** config/prototype.yaml; FINAL_PRODUCTION_CONFIG.md; src/*.py
- **Note:** Highlighted panels are the added/changed parts.

### D03 — Baseline vs modified NyayaMind — stage-by-stage component comparison

- **File:** `D03_baseline_vs_modified_side_by_side.png`
- **Purpose:** The single slide that answers 'what actually changed?'
- **Systems shown:** Baseline vs Modified
- **Source:** config/prototype.yaml; comparison_config.json; src/*.py
- **Note:** Configuration differences only, plus the parser fix.

### D04 — Complete NyayaMind pipeline -- seven stages, production configuration

- **File:** `D04_complete_pipeline.png`
- **Purpose:** One-slide view of the whole system
- **Systems shown:** Modified: NyayaMind production
- **Source:** src/pipeline.py; src/*.py
- **Note:** Stage numbering follows the repository README's own architecture block.

### D05 — Stage 2 — Claim parsing

- **File:** `D05_stage_claim_parsing.png`
- **Purpose:** Explain atomic claim decomposition and why claims can share a sentence
- **Systems shown:** Shared stage; assertion_spans used only by the modified system
- **Source:** src/claim_parser.py
- **Note:** Deterministic regex, no LLM involved at this stage.

### D06 — Stage 3 — Evidence retrieval

- **File:** `D06_stage_evidence_retrieval.png`
- **Purpose:** Show the deterministic match cascade and where the pool size matters
- **Systems shown:** Shared stage; evidence pool size differs between systems
- **Source:** src/evidence_matcher.py; src/data_loader.py
- **Note:** NO_EVIDENCE reflects a corpus limit, not a detected citation error.

### D07 — Stage 4 — NLI verification

- **File:** `D07_stage_nli_verification.png`
- **Purpose:** Explain the premise-framing lever, the project's largest measured effect
- **Systems shown:** Baseline vs Modified premise framing
- **Source:** src/verifier.py; src/pipeline.py
- **Note:** NLI confidence is not a legal-correctness determination.

### D08 — Stage 4b — Verdict application and correction triggering

- **File:** `D08_stage_verdict_application.png`
- **Purpose:** Show which verdicts do and do not cause a correction attempt
- **Systems shown:** Shared stage (identical rules in both systems)
- **Source:** src/pipeline.py
- **Note:** First-flagged-claim-only correction is a documented v0 simplification.

### D09 — Stages 5 and 7 — Selective correction and re-verification

- **File:** `D09_stage_correction_and_reverification.png`
- **Purpose:** Show the ENTAILED-only shipping gate and the narrow-hypothesis change
- **Systems shown:** Baseline vs Modified re-verification hypothesis
- **Source:** src/corrector.py; src/pipeline.py
- **Note:** Only the first flagged claim is ever corrected, once.

### D10 — Stage 6 — Scope and safety gate

- **File:** `D10_stage_scope_and_safety_gate.png`
- **Purpose:** Show that the safety layer is programmatic and reject-only
- **Systems shown:** Baseline vs Modified scope rule
- **Source:** src/pipeline.py; FINAL_PRODUCTION_CONFIG.md
- **Note:** Gates can only reject, never approve.

### D11 — Final answer assembly — pipeline.run_case()

- **File:** `D11_final_answer_assembly.png`
- **Purpose:** Show the five terminal states and the reproducibility record
- **Systems shown:** Baseline reaches 4 states; Modified reaches 5
- **Source:** src/pipeline.py
- **Note:** Only 'corrected' ever ships regenerated text.

### D12 — Full data flow — case input to mentor-facing artifact

- **File:** `D12_full_data_flow.png`
- **Purpose:** Trace provenance end to end, including this package's own read-only position
- **Systems shown:** Both systems
- **Source:** scripts/run_mvp.py; src/pipeline.py; evaluation/
- **Note:** This package writes only into Output_phase_3_vedant/.

### D13 — Pipeline modes A / B / C

- **File:** `D13_pipeline_modes_a_b_c.png`
- **Purpose:** Prevent the common confusion between modes and system configurations
- **Systems shown:** Both systems
- **Source:** src/pipeline.py; scripts/run_mvp.py
- **Note:** Mode is orthogonal to the baseline/modified configuration difference.

### D14 — Reference baseline context — RhetoricLLaMA / LegalSeg is a different task

- **File:** `D14_reference_baseline_rhetoricllama_out_of_scope.png`
- **Purpose:** Pre-empt the natural mentor question 'why not compare against the LegalSeg baseline?'
- **Systems shown:** Out-of-scope reference (not compared)
- **Source:** research/baseline/BASELINE.md; comparison_config.json
- **Note:** No quantitative comparison is made; only a one-row smoke test was ever run.

