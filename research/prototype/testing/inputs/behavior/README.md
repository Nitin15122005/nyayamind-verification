# BEHAVIOR Inputs

**No new fixtures are created here.** These inputs already exist as hand-constructed,
inline Python fixtures inside the frozen `research/prototype/tests/` suite — there is no
separate data file to copy, and this step does not rewrite or duplicate test code
(per this step's explicit instruction: "inventory and fixture preparation, not test
redesign").

## What "BEHAVIOR" means here

An exact, hand-authored input constructed specifically to exercise one deterministic code
path — most often an adversarial or edge-case citation/claim shape — paired with an exact
expected **code behavior** (e.g. "must resolve to `NO_EVIDENCE`, never a guessed match").
This is a software-invariant expectation, not a statistical or legal ground-truth claim.
It answers "does the implementation do what it was designed to do for this input shape?",
never "is this legally correct?".

## Inventory

| Source file | Inputs supplied | Behavior asserted | Component |
|---|---|---|---|
| `tests/test_adversarial_citations.py` (15 tests) | inline `_make_evidence()`/`_pool()` fixtures: wrong-Act, same-number-different-Act, year/edition variants, aliases, numeric ranges, multi-Act bundling, field-wide ambiguity | fail-safe: unresolved/ambiguous citations must resolve to `NO_EVIDENCE`, never a guessed match; 2 categories pin real audit near-misses (CrPC-vs-CPC §100 confusion; a "Mysore Land Acquisition Act" near-miss) confirmed NOT defects | `src/claim_parser.py` + `src/evidence_matcher.py` |
| `tests/test_final_pass_adversarial.py` (10 tests) | 1 real defect regression input (a "Section N, Part &lt;roman&gt;" act-pollution shape found via `audit_no_evidence_taxonomy_v2.py`) + constructed edge-case citation strings | fail-closed: these edge-case shapes must not silently produce a wrong match; proven absent from every real generated text this project has produced | `src/claim_parser.py` |
| `tests/test_respectively_claims.py` (16 tests) | constructed multi-citation "respectively" sentences (simple/multi-Act/multi-provision/ordering/malformed) | `assertion_spans` structural correctness — each fragment must be a genuine verbatim substring, never synthesized; malformed shapes must fail closed to the default (full-sentence) behavior | `src/claim_parser.py::_assign_respectively_spans` |
| `tests/test_claim_parser_bugfixes.py` (20 tests) | real, verbatim sentences copied from `outputs/gold_annotation.jsonl` (4 named document_ids) — real Qwen output, not invented | 5 named act-attribution bug patterns must not recur (multi-act run-on bleed, year-mistaken-for-provision-number, trim-heuristic failure, field-wide single-act-fallback override) | `src/claim_parser.py` |

## Why these are legitimate as software-invariant expectations

Every expected behavior above is a **structural guarantee independent of legal content**
— "never guess," "never fabricate a span," "never let one bug pattern silently recur" —
verifiable purely from the input string and the output data structure, with no legal
judgment involved. This is categorically different from asserting a statute's legal
meaning is correctly captured; none of these tests make that claim.

## What must NOT be claimed from these

That passing these tests establishes statistical accuracy on unconstrained real input, or
that any citation-matching or claim-parsing decision here reflects verified legal
correctness. See `../../component_tests/01_claim_parser/README.md` and
`02_evidence_retrieval/README.md` for the full per-stage mapping (this directory is a
classification-first view of the same underlying tests; those directories are a
pipeline-stage-first view).
