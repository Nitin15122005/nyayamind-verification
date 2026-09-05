# Component Test Inventory (STEP 5)

Built from a fresh, full execution of `research/prototype/tests/` (`pytest -v`, 205
passed — see `../actual_outputs/step5_components/full_suite_verbose.log`), cross-checked
against the STEP 3 component-to-stage mapping. Exact counts below are re-derived from
this run's own PASSED lines, not copied from earlier step reports without checking (some
counts differ slightly from STEP 0/3's estimates due to pytest parametrization — e.g.
`test_premise_framing_production.py` collects 25 items here, not the ~17 `def test_`
functions a grep would suggest).

| # | Component | Existing test file(s) | Test count (this run) | Input type | Expected behavior | CPU/GPU | Status |
|---|---|---|---|---|---|---|---|
| 1 | Claim parsing | `test_claim_parser_and_evidence_matcher.py` (parsing half), `test_claim_parser_bugfixes.py`, `test_respectively_claims.py`, `test_final_pass_adversarial.py`, `test_adversarial_citations.py` (parsing half) | 111 (combined run, some overlap with group 2/5) | hand-constructed + real verbatim Qwen-output sentences | exact citation/claim extraction, act-attribution correctness, span-narrowing correctness | CPU | **111/111 PASSED** |
| 2 | Evidence retrieval/matching | `test_claim_parser_and_evidence_matcher.py` (matcher half), `test_adversarial_citations.py`, `test_candidate_selection.py` | 72 (combined run, overlap with group 1/5) | synthetic pools + real v0/v1 evidence corpus | exact/fuzzy match correctness, usable-verdict filtering, fail-safe on ambiguity | CPU | **72/72 PASSED** |
| 3 | Verifier/NLI | `test_controlled_benchmark.py`, `test_premise_framing_production.py` | 48 | synthetic `EvidenceRecord`s, scripted verifier, real config | premise construction (bare/labeled), device guard, framing wiring | CPU | **48/48 PASSED** |
| 4 | Verdict application | `test_pipeline_mock.py` (`-k "mode_a or mode_b or no_evidence or apply_verification"`) | 3 | mocked pipeline objects | Mode A/B branching, NO_EVIDENCE never reaches verifier | CPU | **3/3 PASSED** |
| 5 | Citation identity / adversarial safety | `test_adversarial_citations.py` (full) | 15 | hand-constructed adversarial fixtures | fail-safe: never guess a match; 7 categories | CPU | **15/15 PASSED** |
| 6 | Correction scope / safety gates | `test_pipeline_mock.py` (`-k "scope or sibling or ordinal or assertion_spans or narrow_reverification or correction"`), `test_correction_path_real_integration.py` (full, 3 tests, real DeBERTa) | 32 (mocked) + 3 (real) = 35 total distinct executions in this group's run (32 passed + 5 deselected reported by pytest refers to the mocked-file filter only; the 3 real-integration tests are additionally included because "correction" matches their file name) | mocked + one real-model integration | scope-violation modes, sibling-regression net, ENTAILED-only shipping gate | CPU (real DeBERTa is CPU-capable) | **32/32 (mocked) + 3/3 (real) PASSED** |
| 7 | Final assembly / integration | `test_pipeline_mock.py` (`-k "reproducibility or assertion_text_surfaces"`), `test_correction_path_real_integration.py` (full, 3 tests, real DeBERTa) | 2 (mocked) + 3 (real) = 5 | mocked + real-model integration | final_field source selection, reproducibility block, stripped internal keys | CPU | **5/5 PASSED** |

**Note on overlap**: groups 1/2/5 all draw partly from `test_adversarial_citations.py` and
`test_claim_parser_and_evidence_matcher.py`, since those files genuinely exercise both
parsing and matching together (documented in STEP 3's `component_tests/01_claim_parser/README.md`
and `02_evidence_retrieval/README.md`). Groups 6/7 both include
`test_correction_path_real_integration.py` because it is this project's one real,
multi-stage, CPU-safe integration test spanning verdict application through final
assembly. No test was double-counted in the **overall regression total** (Phase 11's
205), which counts each test exactly once regardless of how many component groups cite it.

## Execution logs

Full per-group pytest output is saved at
`../actual_outputs/step5_components/0N_*/pytest_execution.log`, and the single full-suite
run (source of truth for all counts above) at
`../actual_outputs/step5_components/full_suite_verbose.log`.
