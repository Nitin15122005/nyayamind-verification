# Stage 1 — Claim Parsing / Citation Extraction

**Source**: `research/prototype/src/claim_parser.py` (deterministic, no model, no GPU).
**Key functions**: `extract_claims`, `extract_citation(s)`, `normalize_act`,
`_assign_assertion_texts`, `_assign_respectively_spans`.

## Existing tests mapped here

| Test file | Scope here | Notes |
|---|---|---|
| `test_claim_parser_and_evidence_matcher.py` | citation/sentence-parsing half only (parsing-specific tests, roughly the file's first half) | the evidence-matching half of this same file belongs to `../02_evidence_retrieval/` — see that stage's README |
| `test_claim_parser_bugfixes.py` | all 20 tests | regression fixtures for 5 real act-attribution bug patterns found via the provisional assumption-annotation pass; every sentence is copied verbatim from real Qwen-generated output already on disk (not invented) |
| `test_respectively_claims.py` | all 16 tests | `_assign_respectively_spans` / `Claim.assertion_spans` structural correctness (simple/multi-Act/multi-provision/ordering/malformed/fail-closed cases) |
| `test_final_pass_adversarial.py` | all 10 tests | 1 real defect regression (a "Section N, Part <roman>" act-pollution bug found via `audit_no_evidence_taxonomy_v2.py`) + fail-closed safety-net cases proven safe against every real generated text this project has produced |
| `test_adversarial_citations.py` | overlaps with `02_evidence_retrieval/` | its wrong-Act/alias/range/multi-Act cases exercise both `extract_citation(s)` (this stage) and `match_evidence` (stage 2) — listed under both |

## What this stage's tests legitimately establish

Exact, deterministic behavior of citation-regex extraction, sentence splitting, act-name
normalization/trimming, per-citation claim expansion (one `Claim` per citation in a
multi-citation sentence), and the two span-narrowing passes that produce `assertion_text`
/ `assertion_spans` — all of which are Category B (behavioral) expectations, not
statistical gold labels. No claim about statistical accuracy on unconstrained real text
follows from these tests alone; that is measured downstream (see `../02_evidence_retrieval/`
and `../../evaluation/`'s NO_EVIDENCE-taxonomy documents, e.g. `NATURAL_DATA_REPORT.md`).

## Relevant scripts (reproduction/diagnostic tools, not test files)

- `scripts/reparse_n30_with_fixed_parser.py` — re-parses already-generated text with the
  current parser and diffs against the stale on-disk result (before/after audit trail).
- `scripts/select_natural_candidates.py` — uses `normalize_act` for batch-selection
  scoring; not itself a parser test.

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_claim_parser_bugfixes.py research/prototype/tests/test_respectively_claims.py research/prototype/tests/test_final_pass_adversarial.py -v
```

(Requires the venv to be created first — see `../README.md`'s "Known reproducibility gap.")
