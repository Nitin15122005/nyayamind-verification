# RESULT — 02 Evidence Matcher (STEP 5)

**Also see** `../02_evidence_retrieval/README.md` (STEP 3's stage-first mapping of the
same tests). This directory name matches STEP 5's own instructions.

## Execution

`research/.venv/Scripts/python.exe -m pytest test_claim_parser_and_evidence_matcher.py test_adversarial_citations.py test_candidate_selection.py -v`

**72 executed, 72 passed, 0 failed, 0 skipped.** Full log:
`../../actual_outputs/step5_components/02_evidence_matcher/pytest_execution.log`.

## Representative input → actual output

Source: `../../actual_outputs/step5_components/02_evidence_matcher/demo_examples.json`.

### Case A — real production evidence pool, exact match

**Input**: citation `Section 302 of the Indian Penal Code, 1860` against the real,
unmodified `research/data/evidence/` pool (same record
`tests/test_correction_path_real_integration.py` uses).

**Actual output**: matched, method=exact, `evidence_id = "Section 302 in The Indian Penal
Code, 1860"`, text = "Whoever commits murder shall be punished with death, or
imprisonment for life, and shall also be liable to fine."

**Expected behavior**: exact-key lookup resolves correctly against the real corpus.
**Result: PASS.**

### Case B — same section number, three different Acts (adversarial safety)

Verbatim fixture from
`tests/test_adversarial_citations.py::test_same_section_number_three_way_split_across_acts`
— Section 34 exists under IPC, the Arbitration Act 1940, and the Arbitration and
Conciliation Act 1996, with completely unrelated meanings.

| Act cited | Actual matched text | Expected text | Correct? |
|---|---|---|---|
| Indian Penal Code, 1860 | "Common intention text." | same | Yes |
| Arbitration Act, 1940 | "1940-Act text (repealed 1996)." | same | Yes |
| Arbitration and Conciliation Act, 1996 | "Setting aside an arbitral award text." | same | Yes |

**Expected behavior source**: `test_adversarial_citations.py::test_same_section_number_three_way_split_across_acts`.
**Result: PASS** — no cross-matching occurred despite an identical provision number.

## Important distinction preserved

A citation-identity failure (e.g. Case A's CrPC-vs-CPC counterpart, demonstrated in
`05_citation_adversarial/RESULT.md`) is described here as a **retrieval/matching behavior
issue**, not a legal-reasoning failure — consistent with STEP 5's explicit instruction.

**Result classification: PASS (Category A — SOFTWARE BEHAVIOR PASS)** for both cases.
