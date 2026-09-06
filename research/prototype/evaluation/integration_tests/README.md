# Integration Tests

## Scope, and how this differs from `components/` and `evaluation/`

- `components/` (renamed from `component_tests/` in the PASS 1 cleanup, 2026-09-05) —
  one function/module in isolation, hand-constructed or mocked inputs, single-stage
  scope.
- **`integration_tests/` (this directory)** — several real stages wired together, using
  at least one real (small, CPU-capable) model, verifying that the *code paths* connect
  correctly — not a statistical accuracy claim, and not single-function scope.
- `evaluation/` — running a real evaluation over a full dataset (the 420-item benchmark,
  a natural batch) to produce dataset-level metrics — larger scale than an integration
  test, and its purpose is measurement, not code-path verification.

**Open design question, flagged rather than resolved in this step**: an independent
architecture review of this workspace noted that a run of the full pipeline over the
59-item synthetic-stress set (real code path, small model, exact expected verdicts) sits
ambiguously between this directory and `comparisons/expected_vs_actual/` — it is
simultaneously a code-path integration test and a legitimate accuracy comparison. This
step does not resolve that ambiguity; whichever directory ends up owning the actual run,
the other should link to it rather than duplicate it. Decide this explicitly in the next
step before both fill up independently.

## What already exists and is the strongest asset for this directory

`research/prototype/tests/test_correction_path_real_integration.py` (frozen, in the
existing test suite) is already exactly this kind of test: it uses a `FakeGenerator`/
`ScriptedCorrector` (so no 7B Qwen call) but a **real, unmodified DeBERTa verifier**
against the real 59-record v0 evidence pool, running the genuine
`pipeline.run_case` code path — trigger → correct → scope-check → sibling-regression →
re-verify → ship/reject. It requires no GPU (DeBERTa is CPU-capable) and no network
beyond the one-time model download. This is the template to build on, not replace.

`research/prototype/evaluation/live_demo/run_demo.py` (promoted here from
`final_demo_pack/live_demo/` in PASS 3B) is the other strong existing asset: a real,
GPU-free, code-path-verifying demo built for presentation purposes, against
already-generated text. It should be referenced (and, when this workspace is ready,
re-run and its output placed in `../actual_outputs/` with the required run metadata)
rather than copied.

## What is planned here (not yet built)

1. A thin wrapper that runs `pipeline.run_case` end-to-end with the real DeBERTa
   verifier and the real 59-record (or 136-record) evidence pool, over a small, fixed set
   of already-generated case texts pulled from `research/prototype/outputs/` — no fresh
   Qwen generation, matching the "reuse already-generated text" pattern used throughout
   this project's own CPU-only scripts.
2. A second wrapper, gated behind an explicit flag and a GPU-availability check (mirroring
   the pattern in `scripts/compare_premise_framing_natural.py`), for a genuine full
   generation→correction integration run when GPU time is available.

Neither is built in this step — see `../reports/README.md` for planned sequencing.
