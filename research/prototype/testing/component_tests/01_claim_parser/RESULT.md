# RESULT — 01 Claim Parser (STEP 5)

**Also see** `README.md` (STEP 3's stage-first mapping) and `../../inputs/behavior/README.md`
(the classification-first view of the same tests).

## Execution

`research/.venv/Scripts/python.exe -m pytest test_claim_parser_and_evidence_matcher.py test_claim_parser_bugfixes.py test_respectively_claims.py test_final_pass_adversarial.py test_adversarial_citations.py -v`

**111 executed, 111 passed, 0 failed, 0 skipped.** Full log:
`../../actual_outputs/step5_components/01_claim_parser/pytest_execution.log`.

## Representative input → actual output

Source: `../../actual_outputs/step5_components/01_claim_parser/demo_examples.json`
(produced by re-running `src/claim_parser.extract_citations`/`extract_claims` directly —
not a new test, a concrete demonstration using the exact sentence
`tests/test_claim_parser_bugfixes.py::_BUG1_SENTENCE` already uses, copied verbatim from
real Qwen-generated output, `gold_annotation.jsonl` document_id `2007_1517`).

**Input** (one real generated sentence):
> "The case is grounded in the United Commercial Bank (Conduct and Discipline and
> Appeal) Regulation, 1976, specifically Regulation 15(2), and the Manual on
> Disciplinary Action and Related Matters of UCO Bank, particularly Clause 22 thereof,
> as well as Sections 120-B, 471, and 477 of the Indian Penal Code and Section 5(2) read
> with Section 1(d) of the Prevention of Corruption Act, 1947, which pertain to the
> criminal charges and the prevention of corruption respectively."

**Actual output**: `extract_citations()` correctly separates the IPC citations
(120-B/471/477, act_norm `"indian penal code"`) from the trailing Prevention of
Corruption Act clause, and recovers Section 1(d) of the POCA as its own, independent
citation — neither act's name pollutes the other's.

**Expected behavior source**:
`tests/test_claim_parser_bugfixes.py::test_bug1_ipc_sections_do_not_merge_with_poca_act_name`,
`::test_bug1_poca_citation_recovered_not_lost` — exact software assertions, pinned
against a real, previously-found bug.

**Result: PASS** (Category A — SOFTWARE BEHAVIOR PASS; see `COMPONENT_TEST_SUMMARY.md`).

## Known config/code drift affecting this component (unchanged from STEP 1/3)

None fixed or touched in this step — see `../README.md`'s drift list (items 1-6).
