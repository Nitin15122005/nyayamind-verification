# Component Tests

**Terminology note**: "expectation" in this directory always means an exact,
hand-authored **code-behavior assertion** (Category B in
`../expected_outputs/README.md`), never a statistical gold label (Category A, which lives
in `../expected_outputs/`). A component test passing tells you the implementation does
exactly what it was designed to do for a given input shape; it does not tell you the
design's judgment call was statistically the right one on unconstrained real data.

## Purpose

Map (not duplicate) the existing, frozen `research/prototype/tests/` suite onto the 8
pipeline stages identified in the Step 0 audit, so each stage's test coverage,
gaps, and adversarial cases can be reviewed independently and presented clearly. Every
subdirectory's `README.md` names the exact existing test file(s) and, where a file spans
multiple stages, exactly which functions/line ranges belong here versus elsewhere.

**No test code is copied or rewritten in this step.** These READMEs are an index, not a
new test suite. Running the tests still means running the originals:

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
```

## Known reproducibility gap

`research/.venv/` **does not exist in this checkout** (verified 2026-09-05) — only a
system Python 3.14 install is present, newer than the project's pinned
Python 3.11.9 / torch 2.2.2+cu121 / transformers 4.40.2 stack. Every command referenced
anywhere in this workspace that assumes `research/.venv/Scripts/python.exe` will fail
until that venv is created and `research/requirements.txt` installed into it. This is a
real, currently-unaddressed environment gap, not a documentation error — see
`../PROVENANCE.md` for the full caveat list and `../reports/README.md` (planned
Reproducibility Report) for where this should be tracked to resolution.

## Stage index

| Stage | Directory | Primary source file |
|---|---|---|
| 1. Claim parsing / citation extraction | `01_claim_parser/` | `src/claim_parser.py` |
| 2. Evidence retrieval | `02_evidence_retrieval/` | `src/evidence_matcher.py`, `src/data_loader.py` |
| 3. NLI verification | `03_nli_verification/` | `src/verifier.py` |
| 4. Verdict application | `04_verdict_application/` | `src/pipeline.py::apply_verification` |
| 5. Correction generation | `05_correction/` | `src/corrector.py` |
| 6. Scope / safety checks | `06_scope_safety/` | `src/pipeline.py::_scope_violation`, `_reverify_sibling_regressions`, `_citation_identity` |
| 7. Re-verification | `07_reverification/` | `src/pipeline.py::apply_selective_correction` (re-verify step) |
| 8. Final output assembly | `08_final_assembly/` | `src/pipeline.py::run_case` |

## Cross-cutting files not forced into one stage

- `tests/test_pipeline_mock.py` — the largest file (34 tests); its functions are
  distributed across stages 4-8 in each stage's own README rather than listed whole under
  one stage, since it covers orchestration broadly.
- `tests/test_correction_path_real_integration.py` — genuinely spans stages 5-8 together
  (it is this project's closest thing to a real multi-stage integration test, using a
  real DeBERTa verifier with a scripted generator/corrector) — listed under all four, with
  a note each time, and also referenced from `../integration_tests/README.md`.
- `tests/test_verifier_benchmark.py` — exercises `src/llm_verifier.py::QwenLLMVerifier`,
  an alternative verifier **never wired into the production pipeline**. Not mapped to any
  of the 8 stages; noted here as an experimental/non-production component only.
- `tests/test_candidate_selection.py` — tests `scripts/select_natural_candidates.py`'s
  scoring function, a batch-selection utility adjacent to but not part of the production
  pipeline. Referenced from `02_evidence_retrieval/` with this caveat.

## Known config/code drift affecting these stages (documented, not fixed, in this step)

1. `evidence_matching.top_k` is declared in `config/prototype.yaml` but never read by
   `src/evidence_matcher.py` — dead config (affects `02_evidence_retrieval/`).
2. `correction.model_id` is declared but never read — `corrector.py` always reuses the
   generator's own loaded model (affects `05_correction/`).
3. `correction.max_attempts` / `correction.max_reverifications` are declared but never
   read — "exactly one attempt, exactly one reverification" is hardcoded control flow,
   not config-driven (affects `05_correction/`, `07_reverification/`).
4. `atomic_scope_check: "assertion_spans"` sets two internal flags
   (`use_assertion_text`, `use_assertion_spans`), but branch order makes the first a
   no-op whenever the second is true — correct output, redundant plumbing (affects
   `06_scope_safety/`).
5. `verifier.py::format_premise()` silently falls back from `labeled` to `bare` framing
   if the matched evidence record's provision metadata is incomplete — documented only in
   a docstring, not in `FINAL_PRODUCTION_CONFIG.md` (affects `03_nli_verification/`).
6. `src/llm_verifier.py::QwenLLMVerifier` is a fully-built alternative verifier never
   wired into `pipeline.py` — easy to mistake for dead code if reading `src/` in
   isolation (affects `03_nli_verification/`, noted above).

None of these are fixed in this step — see `../PROVENANCE.md`.
