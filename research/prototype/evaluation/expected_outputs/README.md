# Expected Outputs

**Terminology note (read first):** "expected output" in this directory always means a
**statistical gold label**, independently derived from how a dataset was *constructed*,
never from a model or a human opinion about a real case. This is a narrower meaning than
"expected behavior" used in `../components/` (which means an exact code-level
assertion, e.g. "this malformed citation must resolve to NO_EVIDENCE") — the two are
related but not interchangeable, and neither should be described using the other's
vocabulary. If you are ever tempted to write "expected output" for a natural-data result,
stop — it belongs in `../evaluation/` instead, described as a metric (see
`../comparisons/README.md`'s PASS 1 correction on where this content actually lives).

This directory holds copies (immutable fixtures, hash-verified against their frozen
source in `MANIFEST.md`) of the **only two datasets in this project with genuinely
independent expected labels.**

---

## Category A — True / legitimate expected labels

### Controlled NLI benchmark (`controlled_benchmark_gold/`)
- 420 examples, each a (premise-source, hypothesis, condition) triple built from one of
  the 59 v0 usable evidence records.
- Expected label (`expected_label`: ENTAILED / CONTRADICTED / NEUTRAL) is assigned by a
  **deterministic construction rule** documented in `scripts/build_controlled_benchmark.py`
  — 8 conditions crossing verbatim/paraphrase and attribution-present/absent, plus
  negated and neutral conditions. No model or human judged these labels; they follow
  mechanically from how each example was built.
- **What this legitimately supports**: a genuine accuracy/F1 comparison of the verifier
  (or any verifier configuration) against a known-correct answer. This is the basis of
  the premise-framing decision's strongest evidence (macro F1 0.749→0.968 bare→labeled).
- **What it does not support**: any claim about accuracy on real, naturally-generated
  case text — the benchmark's hypotheses are mechanically constructed, not real model
  output, so it measures the verifier in isolation, not the full pipeline on real cases.

### Synthetic stress set (`synthetic_stress_gold/`)
- 59 examples, one per v0 usable evidence record, each a real statute sentence with one
  trigger phrase deterministically inverted (e.g. "shall" → "shall not").
- Expected verdict is CONTRADICTED **by construction** for every example — there are no
  ENTAILED or NEI examples in this set.
- **What this legitimately supports**: contradiction-recall measurement, and (when run
  through the full pipeline) correction-triggering and correction-quality measurement on
  cases where the correct fix is unambiguous by construction.
- **What it does not support**: ENTAILED-recall or NEI-calibration (use the 420-item
  benchmark for that), or any claim about natural-data behavior — synthetic contradictions
  are not representative of how real generated text actually fails.

---

## Category B — Unit/behavior expectations

These live in `../components/`, not here, and are a **different kind of thing**:
exact, hand-authored assertions about code behavior for a specific, often adversarial,
input — e.g.:
- a malformed or ambiguous citation must resolve to `NO_EVIDENCE`, never a guessed match
  (`tests/test_adversarial_citations.py`)
- an unflagged claim's required text must survive a correction verbatim, or the run must
  be flagged `correction_scope_violation` (`tests/test_pipeline_mock.py`)
- the shipped production config must exactly match the 2026-08-27 decision record
  (`tests/test_premise_framing_production.py`)

**What these legitimately support**: confidence that the *implementation* behaves exactly
as designed for known input shapes, including adversarial ones. **What they do not
support**: any statement about statistical accuracy on real, unconstrained input — a
component can pass every behavioral test and still make a well-calibrated-but-wrong
judgment call on a real case the tests never anticipated.

---

## Category C — Metric-only evaluations

Everything built from real ("natural") LLM-generated case text: the 588-claim aggregate,
the 209-claim paired evaluation, all four natural batches, and every correction/safety
dataset. **None of these carries an independently-derived correct answer.** They support
internal, comparative, and descriptive metrics (coverage %, verdict distributions,
paired McNemar-style comparisons between two configurations on identical cases,
correction-shipping rates) — never an accuracy-against-truth number. See
`../comparisons/README.md` for how these are to be reported (metric-based content
lives directly in `../evaluation/`, e.g. `NATURAL_DATA_REPORT.md`), and note in
particular:

- The correction-shipping-rate improvement (5→10 triggered, 0→1 shipped between old and
  new config) is **explicitly not statistically significant** at this sample size — the
  Step 0 audit found the confidence intervals overlap almost entirely. Never present this
  as a proven effect; present it as directional, n-limited evidence, exactly as
  `FINAL_BASELINE_COMPARISON.md` itself does.
- No single experiment in this project's history combines all four current production
  config levers (`use_evidence_v1`, `premise_framing`, `atomic_scope_check`,
  `narrow_reverification_hypothesis`) in one fresh generation pass — the strongest
  evidence is a 4-experiment chain on the same 50-case batch, not one combined run. This
  is a real, open gap, not something this workspace can retroactively close by
  reorganizing the existing data.

---

## What's physically in this directory right now

`controlled_benchmark_gold/` and `synthetic_stress_gold/` will contain a copied,
hash-verified snapshot of `controlled_verifier_benchmark.jsonl` and
`run_synthetic_stress.jsonl` respectively, plus a short `SOURCE.md` in each recording the
exact source path, SHA-256, and copy date. See `MANIFEST.md` for the hashes already
computed against the frozen originals.
