# Current Status

_Last updated at commit `9287051` (the F16 ablation-figure fix). Update this file's date/HEAD
reference when a future session makes a material change to production status, results, or
freeze state — do not let it silently go stale._

## Implementation status

**Complete and tested.** All pipeline stages (generation, claim parsing, evidence retrieval,
NLI verification, correction — both legacy and the newer assertion-aware path, safety gates,
final assembly) are implemented in `research/prototype/src/` and covered by
`research/prototype/tests/` (**302/302 passing**).

## Research status

Research-grade, end-to-end evaluated, with both controlled-benchmark and natural-data
evidence. Two mechanisms were built to full production-quality and honestly evaluated as NOT
promoted (see `08_RESEARCH_CLAIMS.md`) — this is a completed research finding, not pending
work.

## Results status

**`research/prototype/results_phase3/` is the single authoritative results package.** It
supersedes `research/prototype/archive/2026-09-06_output_phase_3_vedant/` (archived, not
deleted). Contains 30 figures, 15 diagrams, 18 tables, 4 narrative docs, PPT indices, and full
source traceability. Its own `FINAL_RESULTS.md` §Visual QC records that every figure was
visually inspected and real layout issues were found and fixed (not merely generated and
assumed correct).

## Phase-3 status

Done, including the ablation-figure completeness fix: `F16_ablation_evidence_strength.png` now
represents all 13 evaluated ablation levers (was 8, missing the 5 evaluated since 2026-09-06),
regenerated programmatically from the canonical `tables/ablation/ablation_results.csv`, visually
QC'd (margins fixed to scale with the taller 13-row figure).

## Tests / validation (current)

| Check | Result |
|---|---|
| `pytest research/prototype/tests/ -q` | 302/302 passing |
| `research/prototype/scripts/run_mvp.py --check` | clean, 136 usable evidence records |
| `validate_pack.py` (`archive/2026-08-27_presentation/final_demo_pack/metadata/`) | 25/25 |

## Demo

`research/prototype/evaluation/live_demo/run_demo.py` runs against the real production config
and prints it explicitly (including `correction.assertion_aware`, which stays `false` — the
demo's replay logic has not been extended to assertion-aware records, matching production
default behavior byte-for-byte).

## Docker

**ENVIRONMENT-BLOCKED**, not a research blocker. The Docker daemon has not been running across
every session that has checked it on the development machine (host resource constraints). A
2026-08-27 image (predating five later production levers) was smoke-tested as a structural
sanity check only — not evidence for current code. Never described as "passed" or "failed" —
it is an environment fact.

## Known gaps (real, stated, not hidden)

- No formal 15-category red-team safety evaluation.
- No natural-data GPU batch has yet produced a genuine multi-element `assertion_spans`
  correction-triggering case (the multi-span splice path is verified via deterministic tests
  and a real-corpus-derived fixture only).
- `results_phase3/figures/07_ablation/F16_*.png` shows all 13 levers now, but the archived
  package's F16 predecessor (8 levers) is not separately updated — it stays as historical
  record inside the archive.
- `README.md` (repo root) and `research/prototype/README.md` were not rewritten as part of
  this documentation-organization pass and may lag `PROJECT_CONTEXT/` on the very newest
  details — `PROJECT_CONTEXT/` is the fresher layer by design.

## Frozen components (do not casually change)

`research/data/evidence/` (canonical statute corpus), `research/prototype/outputs/` (lab
notebook — append, never rewrite), `research/prototype/archive/` (both archived packages),
`baseline/LegalSeg` (submodule, never touched).

## Experimental components (implemented, evaluated, off by default)

`verification.assertion_span_primary_hypothesis`, `correction.assertion_aware` — see
`05_MODELS_AND_CONFIGURATIONS.md`.

## Next legitimate work (not started, not claimed done)

- A larger natural-data GPU batch specifically hunting for a real multi-span "respectively"
  correction case, to give the assertion-aware architecture's multi-span path a genuine
  natural-data exercise (currently only tested/fixture-verified).
- Extending assertion-aware correction to attempt correcting more than one wrong claim in a
  bundled sentence (motivated directly by the `1955_32` case study).
- A formal, independently-designed adversarial safety evaluation beyond the categories that
  have arisen from real historical failures.
- Retrying Docker once the development machine has a running daemon and sufficient free
  memory headroom — no code change is needed to attempt this.

None of the above is currently in progress. Do not describe any of it as "pending" work
blocking a release — it is future-work, clearly separated from the frozen, complete current
state.
