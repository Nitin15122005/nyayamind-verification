# Stage 2 — Evidence Retrieval

**Source**: `research/prototype/src/evidence_matcher.py::match_evidence` +
`research/prototype/src/data_loader.py::load_usable_evidence[_from_config]`
(deterministic, no model, no GPU).

## Existing tests mapped here

| Test file | Scope here | Notes |
|---|---|---|
| `test_claim_parser_and_evidence_matcher.py` | evidence-matching half (roughly the file's second half) | includes a dedicated "real data" sub-suite that loads the actual `canonical_statutes.jsonl`+`evidence_audit.jsonl` and confirms `SOURCE_ONLY`/`INVALID`/`UNRESOLVED` records are correctly excluded from the usable pool — the file's own docstring calls this "the single most safety-critical property of the whole pipeline" |
| `test_adversarial_citations.py` | overlaps with `01_claim_parser/`; full results also in `CITATION_ADVERSARIAL_RESULT.md` below | wrong-Act/same-number-different-Act/alias/range/multi-Act-bundling/field-wide-ambiguity cases exercise `match_evidence` directly, confirming fail-safe behavior (unresolved → `NO_EVIDENCE`, never a guessed match); 2 of its 7 categories pin real audit near-misses (CrPC-vs-CPC §100 confusion; a "Mysore Land Acquisition Act" near-miss) confirmed NOT defects |
| `test_candidate_selection.py` | adjacent, not production retrieval | tests `scripts/select_natural_candidates.py::score_case` (an evidence-overlap scoring utility for batch selection) — included here with this caveat, not treated as a retrieval-correctness test |

## What this stage's tests legitimately establish

Exact-key lookup correctness, the fuzzy act-name-token-overlap fallback, and — most
importantly — that the usable-evidence-verdict filter genuinely excludes
`SOURCE_ONLY`/`INVALID`/`UNRESOLVED` records from ever being used as a verifier premise.
All Category B (behavioral). Coverage *rate* on real data (588-claim NO_EVIDENCE
taxonomy, 63.2%→70.3% v0-vs-v1 gain) is a separate, metric-only measurement — see
`../../evaluation/NATURAL_DATA_REPORT.md` and `EVIDENCE_STRENGTH_MATRIX.md` — not
established by these tests.

## Known config/code drift affecting this stage

`evidence_matching.top_k: 1` is declared in `config/prototype.yaml` but **never read** by
`src/evidence_matcher.py` — the actual behavior is a single-best-match loop, not a
parameterized top-k selection. See `../README.md` for the full drift list.

## Relevant scripts

- `scripts/measure_evidence_coverage_v0_vs_v1.py` — v0-vs-v1 coverage measurement (feeds
  `../../evaluation/`'s natural-data reports, not a test itself).
- `scripts/audit_no_evidence_taxonomy_v2.py` — NO_EVIDENCE root-cause taxonomy.
- `scripts/select_natural_candidates.py` — batch-selection utility, see caveat above.

## Run the existing tests

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/test_claim_parser_and_evidence_matcher.py research/prototype/tests/test_adversarial_citations.py research/prototype/tests/test_candidate_selection.py -v
```
