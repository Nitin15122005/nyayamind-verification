# Ablation

## Scope note on terminology

"Ablation" here follows this project's own established usage — a single-variable
sweep or replay isolating the effect of one setting — rather than the stricter classical
sense of removing a component entirely. Where the underlying artifact is a **sensitivity
sweep over an already-computed result** (no new inference) rather than a rerun with a
component removed, that distinction is called out explicitly per artifact below, per a
review flag raised during this workspace's design: don't let "ablation" quietly expand to
mean "any comparison," which is what `comparisons/` is for.

## Two ablations already exist, fully reproducible, CPU-only, no new inference

### 1. Confidence-threshold sensitivity
- Source: `research/prototype/outputs/threshold_sensitivity_analysis.json` / `.md`.
- What it is: a deterministic sweep of the confidence threshold (0.50–0.95) replayed
  against the **already-computed softmax distributions** stored in
  `controlled_benchmark_deberta*_results.jsonl` (the 420-item gold benchmark's model
  predictions) — no re-inference, no new model calls.
- Reproduction: `research/.venv/Scripts/python.exe research/prototype/scripts/analyze_threshold_sensitivity.py`
  (no CLI flags; confirmed no `argparse` in this script — reads inputs and writes outputs
  at fixed paths).
- Because this replays against the 420-item gold benchmark's own labels, its own
  optimum-plateau finding (0.70 within 0.002 macro-F1 of optimum under both framings) is
  gold-backed, even though the artifact itself lives here, not in `expected_outputs/`.

### 2. Scope-check-mode replay (3-stage lineage)
- Source: `outputs/atomic_scope_check_replay.json` → `_replay_v2.json` →
  `_final_replay.json`, each a later, more complete replay over real, already-produced
  correction attempts from the natural GPU batches — no GPU, no new Qwen/DeBERTa calls.
- Reproduction (final stage): `research/.venv/Scripts/python.exe research/prototype/scripts/replay_final_atomic_scope_check.py`
  (no CLI flags; confirmed no `argparse`).
- **This ablation's own finding is explicitly weak/inconclusive**: the final replay found
  only 1 of 11 real scope violations unblocked by the relaxed `assertion_spans` check,
  contradicting an earlier, batch-1-only finding of 4/6 unblocked — the two are **not
  reconciled** anywhere in this project. Any report drawing on this ablation must state
  this explicitly, not just cite the more favorable earlier number.

## What is not yet built here

A joint-lever ablation — varying `use_evidence_v1`, `premise_framing`,
`atomic_scope_check`, and `narrow_reverification_hypothesis` one at a time from a single
common baseline, on one fixed natural case set — does not exist anywhere in this
project's history (the closest existing evidence is a 4-experiment chain on the same
50-case batch, each step changing more than one lever at once). Building this cleanly is
the single most valuable ablation this workspace could add, and requires either careful
reuse of already-generated text (CPU-only, using the pattern in
`scripts/compare_premise_framing_natural.py`) or a fresh GPU run — see
`../reports/README.md` for planned sequencing. Not started in this step.
