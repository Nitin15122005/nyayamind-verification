# RESULT — Citation Identity and Adversarial Safety (STEP 5)

**Moved here in PASS 1 cleanup** from the old `component_tests/05_citation_adversarial/`
(a STEP-5-only numbering artifact). This test group belongs to the evidence-retrieval
stage — it exercises `match_evidence`'s citation-identity safety directly — not to the
`05_correction` stage it was numbered alongside during STEP 5; see `../05_correction/README.md`
for confirmation these are genuinely different concerns.

The project previously identified citation identity as safety-critical (STEP 0 audit).
This group verifies the system never *incorrectly accepts* a wrong-Act, wrong-year,
wrong-alias, or ambiguous citation as a match.

## Execution

`research/.venv/Scripts/python.exe -m pytest test_adversarial_citations.py -v`

**Total cases: 15. Passed: 15. Failed: 0.** All 15 existing adversarial cases were run
— this is the current, complete test set (confirmed by direct count; no cases were
added in this step). (Raw log removed in PASS 1 cleanup, see `RESULT.md`'s note.)

## Categories (7, all covered, all passing)

| Category | Test(s) | Result |
|---|---|---|
| Wrong Act | `test_wrong_act_crpc_vs_cpc_section_100_never_cross_matches`, `test_wrong_act_high_but_subthreshold_overlap_does_not_match` | PASS (2/2) |
| Same section number, different Act | `test_same_section_number_three_way_split_across_acts` | PASS (1/1) |
| Year / edition variants | `test_year_edition_income_tax_act_1961_vs_hypothetical_2025_act`, `test_year_edition_land_acquisition_act_central_vs_state_variant` | PASS (2/2) |
| Aliases | `test_aliases_crpc_and_cpc_are_distinct_and_each_resolves_correctly`, `test_aliases_id_act_resolves_to_industrial_disputes_act`, `test_aliases_evidence_act_short_form_matches_full_indian_evidence_act`, `test_aliases_parenthetical_abbreviation_never_redirects_to_wrong_act` | PASS (4/4) |
| Numeric ranges | `test_range_hyphenated_span_is_never_silently_expanded_or_mismatched`, `test_range_legitimate_suffixed_provision_120b_is_not_treated_as_a_range` | PASS (2/2) |
| Multi-Act bundling | `test_multi_act_three_acts_in_one_sentence_stay_independently_resolved`, `test_multi_act_claims_each_get_independent_evidence_lookup` | PASS (2/2) |
| Ambiguous / field-wide | `test_ambiguous_same_number_two_different_acts_in_field_stays_unresolved`, `test_ambiguous_unresolved_citation_never_reaches_match_evidence_as_a_false_match` | PASS (2/2) |

**Exact failure category: none.** 0 failures across all 15 cases.

## Representative examples (concrete input → actual output)

Source: `citation_adversarial_demo_examples.json` in this directory.

### Wrong Act (CrPC vs. CPC, Section 100)

- **Input claim/reference**: citation "Section 100 of the Code of Criminal Procedure (CrPC)".
- **Available evidence**: only a Section 100 record under *The Code of Civil Procedure, 1908* exists in the pool.
- **Retrieved result**: `matched=False`, `match_method="no_evidence"`.
- **Expected software behavior**: must never cross-match CrPC to the CPC record despite sharing "code"/"procedure" tokens (2 of 3, below the 0.8 fuzzy threshold).
- **Actual behavior**: matches expected exactly.
- **PASS/FAIL: PASS.**
- **Framing note (per STEP 5's explicit instruction)**: this is a retrieval/matching
  behavior finding — the corpus genuinely lacks a CrPC Section 100 record — not a legal
  reasoning failure. The matcher correctly refuses to guess rather than incorrectly
  accepting a wrong-Act match.

### Aliases (CrPC / CPC distinctness)

- **Input**: `normalize_act("CrPC")`, `normalize_act("CPC")`.
- **Actual output**: `"code of criminal procedure 1973"` and `"code of civil procedure 1908"` respectively — distinct.
- **Expected behavior**: these two common abbreviations must never normalize to the same act.
- **PASS/FAIL: PASS.**

**Result classification for this entire group: PASS (Category A — SOFTWARE BEHAVIOR PASS).**
No legal-correctness claim is made anywhere in this group — every assertion is about
retrieval/matching safety behavior only.
