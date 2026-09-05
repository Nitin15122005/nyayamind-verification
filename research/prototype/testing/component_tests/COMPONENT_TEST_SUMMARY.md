# Component Test Summary (STEP 5)

## Table 1 — Test execution counts

| Component | Tests | Passed | Failed | Skipped | CPU/GPU | Result |
|---|---|---|---|---|---|---|
| 01 Claim parser | 111 | 111 | 0 | 0 | CPU | PASS |
| 02 Evidence matcher | 72 | 72 | 0 | 0 | CPU | PASS |
| 03 Verifier | 48 | 48 | 0 | 0 | CPU (real DeBERTa) | PASS |
| 04 Verdict application | 3 | 3 | 0 | 0 | CPU | PASS |
| 05 Citation / adversarial safety | 15 | 15 | 0 | 0 | CPU | PASS |
| 06 Correction scope / safety gates | 35 (32 mocked + 3 real) | 35 | 0 | 0 | CPU (real DeBERTa for 3) | PASS |
| 07 Final assembly / integration | 5 (2 mocked + 3 real) | 5 | 0 | 0 | CPU (real DeBERTa for 3) | PASS |
| **Full regression suite** | **205** | **205** | **0** | **0** | CPU | **PASS** |

Per-group counts overlap where tests genuinely span multiple stages (documented in
`TEST_INVENTORY.md`); the 205 figure is the authoritative, non-duplicated total.

## Table 2 — Representative input → actual output → expected basis (for faculty review)

| Component | Representative input | Actual output | Expected behavior (source) | Result |
|---|---|---|---|---|
| Claim parser | Real Qwen sentence bundling IPC §120-B/471/477 + POCA §1(d) (`gold_annotation.jsonl`, doc 2007_1517) | IPC citations correctly separated from POCA; POCA §1(d) recovered as its own claim | `test_claim_parser_bugfixes.py::test_bug1_*` (software invariant) | PASS |
| Evidence matcher | Citation "Section 34" against 3 real-shaped records under IPC / Arbitration Act 1940 / Arbitration & Conciliation Act 1996 | Each resolves independently to its own Act's text; zero cross-matches | `test_adversarial_citations.py::test_same_section_number_three_way_split_across_acts` | PASS |
| Verifier | Premise = real Section 302 IPC text; hypothesis = deliberately corrupted ("fine only, never death") | CONTRADICTED, confidence above 0.70 threshold | `test_correction_path_real_integration.py::test_corrupted_claim_reaches_contradicted_against_real_evidence` (real DeBERTa) | PASS |
| Verdict application | Same corrupted claim, real matched evidence | `claim["verdict"]="CONTRADICTED"`, evidence identity preserved unchanged | `src/pipeline.py::apply_verification` software invariant | PASS |
| Citation / adversarial safety | Citation "Section 100, CrPC" against a pool containing only a CPC Section 100 record | `matched=False`, `match_method="no_evidence"` — never cross-matched | `test_adversarial_citations.py::test_wrong_act_crpc_vs_cpc_section_100_never_cross_matches` | PASS |
| Correction scope / safety | Corrected text where the corrector also altered the unflagged sibling sentence | `status="correction_scope_violation"`, re-verification never called, original text shipped | `test_correction_path_real_integration.py::test_scope_violation_protection_...` (real DeBERTa) | PASS |
| Final assembly | Full `run_case()` output for a genuine, safe correction | `final_field.source="corrected"`, reproducibility block present, internal keys stripped | Same real-integration test, full record | PASS |

Full JSON backing every row above: `../actual_outputs/step5_components/0N_*/demo_examples.json`.

## Three types of success, kept explicitly separate

### A. SOFTWARE BEHAVIOR PASS
**Every result in Table 1 and Table 2 above is this type.** The implementation satisfies
an explicit software invariant/unit-or-integration-test assertion. None of these claims
anything about statistical model accuracy or legal correctness — they claim the code does
exactly what it was designed to do for the given input, including on adversarial/edge
cases.

### B. GOLD EVALUATION PASS
**Not the subject of this step.** This category belongs exclusively to STEP 4's work
against the two true-gold datasets (`comparisons/expected_vs_actual/`): GOLD-01 (420-item
controlled benchmark, accuracy 0.9714 labeled / 0.7333 bare) and GOLD-02 (59-item
synthetic stress, contradiction recall 0.4576 labeled / 0.3559 bare). This step's one
verifier example (03_verifier) reuses a construction-guaranteed-contradictory hypothesis,
which is a software-behavior case (Category A), not a draw from the 420-item GOLD-01
benchmark — it is explicitly NOT double-counted as a Category B result.

### C. DESCRIPTIVE / METRIC RESULT
**Not produced in this step.** No natural or unlabeled data was evaluated for accuracy
here — that remains the domain of `comparisons/metric_based/` (588-claim aggregate,
209-claim paired evaluation, natural batches), none of which was touched in STEP 5.

**These three categories are never mixed anywhere in this step's artifacts.**
