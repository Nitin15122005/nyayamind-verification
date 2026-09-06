# NyayaMind Prototype — Testing & Evaluation Workspace

Created: 2026-09-05
Based on: repository commit `ccbe73f3c6c504c4f7d84cd8e8c9c128397f56a3` ("Readme updated")
Status: **Complete (STEP 1 through STEP 13, then cleanup PASS 1 through PASS 3B).** All
directories below have real content — fresh GPU/CPU runs, component/integration test
mappings, ablations, figures, and the faculty-facing final report package. Start at
`reports/README.md` for the finished deliverable, or `reports/FINAL_WORKSPACE_MANIFEST.md`
for a deliverable-by-deliverable index of the whole workspace as it now stands. (The
per-section STEP labels left throughout this document, and in `MANIFEST.md`, are frozen
provenance markers recording *when* each piece was built, not an indication that anything
is still in progress.)

This document is written for someone who has never seen this repository before.

---

## 1. What this folder is

`research/prototype/evaluation/` is a **new, separate presentation and evaluation layer**
sitting on top of the existing NyayaMind prototype. It does not contain a second
implementation of the pipeline, a second copy of the evidence corpus, or a second set of
"real" results. Everywhere it can, it **references** the existing, frozen research
artifacts instead of duplicating them, and it clearly labels the handful of places where a
small, exact copy ("immutable fixture") was made instead, and why.

## 2. Why it exists

The existing repository (`research/prototype/outputs/`, plus the presentation/comparison
layers now archived at `archive/2026-08-27_presentation/final_demo_pack/` and
`archive/2026-08-27_presentation/final_comparison/`) is a **lab notebook and a finished
paper's supporting material** —
accurate, thorough, and heavily cross-referenced, but organized chronologically and by
experiment, not by "here is exactly what the system was given, here is what we expected,
here is what it produced." This workspace exists to answer, in one place, for any
audience unfamiliar with the project's history:

- What does the system actually receive as input?
- Where do we have a real, independently-derived expected answer to check against?
- Where do we only have the system's own output, measured by internal metrics, with
  **no** independent ground truth?
- What exactly changed between the original/baseline pipeline configuration and the
  current one, and what evidence backs each change?

## 3. What counts as an input (`inputs/`)

Anything the pipeline consumes before producing a result: the statute evidence corpus
(v0, v1, merged), and the natural-language case texts drawn from the NyayaRAG corpus.
`inputs/` never contains generated text, verdicts, or corrections — only what goes in
before the pipeline runs. See `inputs/README.md` for the exact inventory.

## 4. What counts as an expected output (`expected_outputs/`)

**Only two datasets in this entire project have a genuinely independent, non-model-derived
expected answer**, and `expected_outputs/` contains nothing else:

- The **420-example controlled NLI benchmark** — each example's expected label
  (ENTAILED / CONTRADICTED / NEUTRAL) comes from a deterministic construction rule, not
  from a model or a human judgment call.
- The **59-example synthetic stress set** — each is a real statute sentence with one
  clause deliberately, mechanically inverted (e.g. "shall" → "shall not"), so the expected
  verdict (CONTRADICTED) follows from how the example was built, not from anyone's
  opinion about it.

Everything else the system produces on real, natural case data has **no independent
ground truth** — see §7 below and `expected_outputs/README.md`'s Category B/C.

## 5. What counts as an actual output (`actual_outputs/`)

Fresh output produced by *running the pipeline in this workspace* — never a copy of
historical files from `research/prototype/outputs/`. `actual_outputs/` now holds fresh
evidence from every later step that needed it (environment/GPU capability checks, the
GOLD-01/GOLD-02 benchmark reruns, the 209-claim GPU reproduction, natural-batch reruns,
and the per-step validator reports) — see `actual_outputs/README.md` for the current
inventory and `reports/FINAL_WORKSPACE_MANIFEST.md` for the authoritative per-artifact
status.

## 6. What "expected vs. actual" means here

It means, specifically and only: *a fresh actual output, compared against one of the two
true-gold datasets in §4.* `comparisons/expected_vs_actual/` is reserved for exactly
that. If you see a natural-data result (real generated case text) described as
"expected vs. actual," that is a labeling error — natural-data results belong in
`evaluation/` instead (described using metric language, e.g. `NATURAL_DATA_REPORT.md`),
because there is no independent expected answer to compare them to.

## 7. What metric-based evaluation means

Most of this project's real-world evidence is metric-based, not expected-vs-actual:
counts and rates measured on the system's own output (evidence-coverage %, verdict
distributions, correction-shipping rate, McNemar paired comparisons between two
configurations run on the *same* underlying cases). These are legitimate and often
statistically meaningful, but they answer "did configuration B behave differently from
configuration A on this data?", not "was the system's answer correct?". The
588-claim aggregate and the 209-claim paired evaluation (see `inputs/README.md`) are the
two most important examples — neither is a labeled dataset.

## 8. What ablation means

Re-running (or, where possible, deterministically *replaying without new inference*) the
pipeline or verifier under one changed setting at a time — e.g. the confidence-threshold
sweep, or the scope-check-mode replay — to isolate the effect of that one setting. See
`ablation/README.md`.

## 9. Component tests vs. integration tests

- **`components/`** (renamed from `component_tests/` in the PASS 1 cleanup,
  2026-09-05 — see `archive/cleanup_history/CLEANUP_PASS1_MANIFEST.md`) — one pipeline stage at a time, in
  isolation, using hand-constructed or mocked inputs. This is where exact
  code-behavior expectations live (Category B in `expected_outputs/README.md`),
  organized to mirror the 8 stages in §11 below. It maps to (does not duplicate) the
  existing suite in `research/prototype/tests/`.
- **`integration_tests/`** — the full pipeline, or a long real slice of it, wired
  together, with a real (but small, CPU-capable) model where feasible, verifying the
  *code paths* connect correctly end-to-end — not a statistical accuracy claim.

## 10. Where figures and final reports live

- `figures/` — 11 faculty-facing figures, generated from the locked `metrics/figure_data/`
  contracts (see `figures/README.md` and `figures/FIGURE_INDEX.md`).
- `reports/` — the finished faculty/reviewer-facing report package (see `reports/README.md`
  for reading order).

## 11. Conceptual pipeline (source of truth: the Step 0 audit)

```
INPUT CASE (case_text)
   |
   v
[1] GENERATION                  -- src/generator.py::StatuteGroundingGenerator
   |  model: Qwen2.5-7B-Instruct, 4-bit, greedy+seed   | GPU: required, no CPU fallback
   v
[2] CLAIM PARSING                -- src/claim_parser.py::extract_claims
   |  deterministic, no model                          | GPU: no
   v
[3] EVIDENCE RETRIEVAL            -- src/evidence_matcher.py::match_evidence
   |  deterministic exact + fuzzy lookup, no model      | GPU: no
   v
[4] NLI VERIFICATION              -- src/verifier.py::NLIVerifier
   |  model: DeBERTa-v3-base-mnli-fever-anli            | GPU: default, CPU opt-in exists
   v
[5] VERDICT                       -- src/pipeline.py::apply_verification
   |  no model (applies verifier's own result)          | GPU: inherits [4]
   v
[6] CORRECTION                    -- src/corrector.py::SelectiveCorrector
   |  reuses [1]'s loaded Qwen model                    | GPU: required (inherits [1])
   v
[7] SCOPE / SAFETY CHECK          -- src/pipeline.py::_scope_violation, _reverify_sibling_regressions
   |  deterministic + re-verification via [4]           | GPU: inherits [4]
   v
[8] RE-VERIFICATION               -- src/pipeline.py::apply_selective_correction (re-verify step)
   |  model: DeBERTa, same shipping gate: ENTAILED only | GPU: inherits [4]
   v
FINAL OUTPUT                      -- src/pipeline.py::run_case (assembly)
```

Full per-stage input/output schemas, exact config keys, and known doc/code drift are in
the Step 0 audit (see `PROVENANCE.md` for where that audit's findings live) and are
repeated where relevant in each `components/0N_*/README.md`.

## 12. What must NOT be modified

The following are **frozen, read-only sources** for this entire workspace. Nothing under
`evaluation/` writes to, deletes from, or rewrites any of these:

- `research/data/` (evidence corpora, NyayaRAG source case files)
- `research/prototype/outputs/` (122-file experimental record)
- `research/prototype/archive/2026-08-27_presentation/final_demo_pack/` (archived in
  PASS 3B; `live_demo/` and `examples/` were promoted into this workspace instead — see
  below)
- `research/prototype/archive/2026-08-27_presentation/final_comparison/` (archived in
  PASS 3B)
- `research/prototype/tests/` (existing test suite)
- `research/prototype/src/` (production implementation)
- `research/prototype/config/prototype.yaml` (production configuration)

`evaluation/live_demo/` and `evaluation/examples/` (promoted from `final_demo_pack/` in
PASS 3B) are part of this workspace, not frozen external sources, but they too only read
from `src/`, `config/`, and `outputs/` — they write nothing back into any of the above.

If a future step needs to *reproduce* something from these sources, it reads them and
writes its output under `evaluation/`, never back into them.

## 13. Index of this workspace

| File/dir | Purpose |
|---|---|
| `MANIFEST.md` | STEP 1 machine-readable-style inventory of every testing artifact (historical snapshot; see `reports/FINAL_WORKSPACE_MANIFEST.md` for the current, complete inventory) |
| `PROVENANCE.md` | Lineage from original pipeline → current production → this workspace |
| `inputs/` | Exact inventory of everything the pipeline consumes |
| `expected_outputs/` | The two true-gold datasets, and only those |
| `actual_outputs/` | Fresh run outputs (empty as of this step) |
| `comparisons/` | Expected-vs-actual (true gold only) vs. metric-based (everything else) |
| `components/` | Per-stage unit/behavioral test mapping (renamed from `component_tests/`) |
| `integration_tests/` | Full-pipeline, code-path-verifying runs |
| `ablation/` | Single-variable replays/sweeps |
| `metrics/` | Dataset-level evaluation runs and their metrics (renamed from the inner `evaluation/` in PASS 3A to avoid confusion with this now-renamed workspace itself) |
| `figures/` | Chart categories and their generation/audit scripts |
| `reports/` | Faculty/reviewer-facing final reports |
| `scripts/` | Every `run_*`/`build_*`/`validate_*` reproduction and validation script (moved here from the workspace root in PASS 3A) |
| `live_demo/` | Presentation-quality demo suite (11 independently-runnable, code-path-verifying scripts, one per pipeline stage plus 4 full-pipeline outcomes, all CPU-safe) built on `run_demo.py`, promoted from `final_demo_pack/live_demo/` in PASS 3B — see `live_demo/README.md` |
| `examples/` | 8 audited real-case worked examples plus their selection scripts, promoted from `final_demo_pack/examples/` in PASS 3B |
