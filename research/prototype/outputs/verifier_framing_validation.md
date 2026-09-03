# Premise-Framing Validation — production-path wiring

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. Follows `verifier_correction_diagnosis.md`.

> **Scope of every verdict below.** These are outputs of a small public NLI model
> (DeBERTa-v3-base-mnli-fever-anli) scored against a 59-record, third-party-sourced
> evidence corpus. They are **not** legal-correctness determinations. No lawyer ground
> truth exists, and the Claude assumption annotations in this repository are not ground
> truth and were not used.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

---

## 1. Existing bare-framing benchmark results

From `controlled_benchmark_deberta_metrics.json` — 420 controlled items over the 59 usable
statute records, unchanged by this work.

| metric | value |
|---|---|
| Accuracy | 0.733 |
| Macro F1 | 0.749 |
| ENTAILED P / R / F1 | 0.979 / **0.500** / 0.662 |
| CONTRADICTED P / R / F1 | 0.954 / 0.873 / 0.912 |
| NEI P / R / F1 | **0.518** / 0.958 / 0.673 |

All 92 ENTAILED errors were attributed items (E2 + E4); zero were bare.

## 2. Labeled-framing benchmark results

From `controlled_benchmark_deberta_labeled_metrics.json`. Same model, same 0.70 threshold,
same 420 items — only the premise differs.

| metric | bare | labeled |
|---|---|---|
| Accuracy | 0.733 | **0.971** |
| Macro F1 | 0.749 | **0.968** |
| ENTAILED P / R / F1 | 0.979 / 0.500 / 0.662 | 0.974 / **1.000** / **0.987** |
| CONTRADICTED P / R / F1 | 0.954 / 0.873 / 0.912 | 0.965 / **0.932** / **0.948** |
| NEI P / R / F1 | 0.518 / 0.958 / 0.673 | **0.974** / 0.966 / **0.970** |

No per-condition regression. `N2_procedural_addition` — the credulity check — stays at
59/59 correct NEI, so labeling did not make the model accept claims carrying extraneous
conditions the statute does not state.

---

## 3. Code and configuration changes

The change is an **isolated ablation**: premise construction only. The NLI model, the 0.70
confidence threshold, claim extraction, evidence matching, correction logic and all
generation settings are untouched.

### `config/prototype.yaml`

```yaml
verification:
  premise_framing: "bare"      # bare | labeled
```

**The default is deliberately `bare`**, because every committed output in `outputs/`
(`run_A/B/C_n30`, `run_natural_targeted`, `run_synthetic_stress`) was produced under it.
Flipping the default would silently make new runs non-comparable with those baselines,
which is exactly the reproducibility invalidation the brief warns against.

### `src/verifier.py`

`format_premise(evidence_text, framing, provision_type, provision_number, act)` — a pure
function, already present from the diagnosis phase. `labeled` emits
`"<Provision> <N> of <Act>: <statute text>"`, adding only the label the audited evidence
record already carries. Statute text passes through untouched; no legal content is invented.
Missing label metadata falls back to bare rather than emitting `": Whoever commits murder…"`.

The `NLIVerifier` class itself is **not** given framing behaviour — it remains a pure
premise/hypothesis scorer, so the framing decision stays in configuration and the pipeline
rather than hard-coded in the verifier.

### `src/pipeline.py`

- `resolve_premise_framing(config)` — reads `verification.premise_framing`, defaults to
  `bare` when absent, and raises `ValueError` naming the offending value otherwise. It fails
  loudly rather than falling through, so a typo cannot produce a run that is labelled an
  ablation but silently is not one.
- `_premise_for_claim(rec, framing)` — builds the premise from `_evidence_provision`, which
  carries the **matched evidence record's** identity, deliberately *not* the claim's
  `citation_extracted`. A mis-cited claim must not be handed a premise labeled with its own
  error.
- `generate_and_parse()` stashes `_evidence_provision` on each matched claim. It is
  underscore-prefixed, so the existing strip at output time removes it and **the emitted
  record schema is unchanged** — new runs stay diffable against the committed baselines.
- `apply_verification(baseline, verifier, premise_framing=PREMISE_FRAMING_BARE)` — the new
  argument defaults to bare, so any caller not passing it keeps exactly the behaviour that
  produced the committed outputs.
- The re-verification premise inside `apply_selective_correction()` uses the same configured
  framing. Verifying under one framing and re-verifying under another would judge a
  correction against a different standard than the one that flagged it.
- `reproducibility.premise_framing` is now recorded on every B/C record. Without it a run
  cannot be attributed to a framing after the fact.

### Scripts

`run_eval_30.py`, `run_natural_targeted_eval.py` and `run_synthetic_stress_eval.py` thread
`pipeline.resolve_premise_framing(config)` into `apply_verification` and record the framing in
their reproducibility blocks. `run_synthetic_stress_eval.py` additionally now strips
underscore-prefixed keys before serialising claims, matching the convention `run_case()` and
`run_eval_30.py` already used; its emitted schema is unchanged because it previously had no
such keys.

### New

`scripts/compare_premise_framing_synthetic.py` — the bare-vs-labeled ablation harness
(§5), CPU-safe by default, with `--with-correction` for the GPU machine.

---

## 4. Test results

**119 passed, 0 failed, 0 errors** (was 95 before this phase, 68 before the diagnosis phase).
`tests/test_premise_framing_production.py` adds 24 tests using a `RecordingVerifier` that
captures the exact premise string production hands the model:

| requirement | covered by |
|---|---|
| 1. bare framing unchanged | premise is byte-identical to evidence text; `apply_verification` defaults to bare; NO_EVIDENCE claims still never reach the verifier |
| 2. labeled contains the provision identifier | prefix `"Section 302 of The Indian Penal Code, 1860: "`, statute text preserved verbatim, label taken from matched evidence not the claim's citation |
| 3. framing passed through production | `run_case()` parametrised over both framings; `reproducibility.premise_framing` recorded; internal `_evidence_provision` stripped from output |
| 4. invalid config fails clearly | `ValueError` naming the bad value; 8 invalid inputs incl. `None` (a bare `premise_framing:` line in YAML) and wrong-case `"Labeled"`; never silently degrades to bare |
| 5. existing tests unaffected | full suite green, including all parser, matcher, correction and mock-pipeline tests |

A guard test also pins the shipped config: default `bare`, threshold `0.70`, model unchanged —
so the ablation cannot later be "achieved" by moving the threshold instead.

---

## 5. Synthetic comparison actually run (CPU, verification-only)

`scripts/compare_premise_framing_synthetic.py --device cpu` over the same 59 synthetic stress
claims, driving the **real wired `pipeline.apply_verification`**.
Outputs: `framing_comparison_synthetic_{metrics.json,results.jsonl}`.

**Validity gate passed.** The bare arm reproduced the committed `run_synthetic_stress.jsonl`
verdicts **59/59**, and reproduces the previously reported figures exactly (21 CONTRADICTED,
35.6% overall, 47.7% with evidence, 0% false positives). The newly wired production path is
behaviour-identical under bare framing.

| metric | bare | labeled |
|---|---|---|
| contradiction recall (all 59) | 21/59 = **35.6%** | 27/59 = **45.8%** |
| contradiction recall (44 with evidence) | 21/44 = **47.7%** | 27/44 = **61.4%** |
| false-positive rate (c2, unflagged true claim) | **0.0%** | **0.0%** |
| correction triggers | 31 | 36 |
| corrections shipped | *not measured* | *not measured* |
| correction_failed | *not measured* | *not measured* |
| correction_scope_violation | *not measured* | *not measured* |
| unsafe corrections shipped | *not measured* | *not measured* |

Contradiction detection improves materially with **no** increase in false positives. The 15
NO_EVIDENCE cases are unchanged in both arms — that is the known claim-parser/`act_norm`
limitation, not a verifier effect.

Under labeled framing the unflagged true claim c2 ("Article 14 … guarantees equality before
the law") moves from NEI to ENTAILED in all 59 cases. That is the correct reading — it is a
faithful statement of Article 14 — and it is *not* a false positive, which is measured as
wrongly flagging c2 as CONTRADICTED and remains 0/59.

### One reconciliation, reported rather than smoothed over

The bare arm shows **31** correction triggers where the committed GPU run recorded **30**.
Cause: claim `s45` has confidence **0.700195** under GPU fp16 (just above the 0.70 threshold,
no downgrade) and **0.699710** under CPU fp32 (just below, downgraded to `low_confidence`).
Mean |fp16−fp32| confidence drift across the set is 0.0004, max 0.0025 — the two agree to
about three decimal places, and only this knife-edge case crosses the threshold. No verdict
label differs. This is a dtype numeric artifact, not a wiring difference, and the harness now
reports `sub_reason_mismatches` and drift statistics in its metrics file so it stays visible.

### What was NOT measured, and why

The four correction metrics require the Qwen2.5-7B corrector to actually rewrite text.
**CUDA is not available on this machine** (`torch.cuda.is_available() == False`, CPU-only
torch 2.13.0+cpu, Intel Iris Xe only, no `bitsandbytes`). Per the brief, no Qwen run was
attempted, no model was downloaded, and no GPU numbers are estimated or fabricated. The
`--with-correction` path refuses to run and exits non-zero if CUDA is absent.

### Exact command for the RTX 4050 machine

From `research/prototype/`, with the existing GPU environment:

```bash
# 1. deterministic 12-case subset first (as the brief prefers)
python scripts/compare_premise_framing_synthetic.py \
    --device cuda --with-correction --limit 12 \
    --out-prefix framing_comparison_gpu_n12

# 2. only if the subset is clean and useful, the full 59
python scripts/compare_premise_framing_synthetic.py \
    --device cuda --with-correction \
    --out-prefix framing_comparison_gpu_n59
```

`--limit` takes a deterministic first-N of a fixed-order case list; the seed stays 42 and
config is unmodified. Both arms run inside one invocation, so bare and labeled see identical
cases, model and threshold. Nothing in `outputs/` is overwritten — results land under the
given prefix. Note that `--limit` skips the committed-run reproduction gate (that check needs
all 59), so run step 2 before drawing conclusions about the full set.

Expected from the diagnosis phase, for comparison against whatever the GPU run produces:
re-scoring the 30 stored real Qwen corrections gave 0/30 shipped under bare and 23/30 (76.7%)
under labeled, with the 7 refusals being genuinely bad corrections.

---

## 6. Is labeled framing ready to become the production default?

**Not yet.** The evidence supports keeping it as an explicit, tested, non-default option.

In favour:
- Controlled benchmark: macro F1 0.749 → 0.968, ENTAILED recall 0.500 → 1.000, no
  per-condition regression.
- Production-path synthetic: contradiction recall 47.7% → 61.4% with evidence, false
  positives still 0%.
- Re-scoring stored real corrections: 0/30 → 23/30 would ship.
- Wiring is covered by 24 tests; bare behaviour is byte-identical and output schema unchanged.

Against, for now:
- **The correction path has never actually executed under labeled framing.** The 76.7% figure
  comes from re-scoring corrections that Qwen produced under *bare*-framing flagging. Under
  labeled framing 36 claims trigger instead of 31, and 6 newly-detected contradictions have
  never been sent to the corrector at all. Their behaviour, and the resulting
  `correction_failed` / `correction_scope_violation` / unsafe-shipment counts, are unmeasured.
- **No natural-data benefit is demonstrated.** Re-verification of the 52 evidence-matched
  natural claims moved only 3, and at least 2 of those look spurious (a multi-citation
  sentence "entailed" by a single section's text). Making labeled the default would change
  production behaviour on real cases for a benefit that has not been shown there.
- Flipping the default breaks comparability with every committed baseline.

**Recommended sequence:** run the GPU command in §5 → if correction success and safety hold
(corrections shipped up materially, scope violations 0, unsafe shipments 0) → promote
`labeled` to default in the same commit that records the GPU comparison, and re-run the A/B/C
baselines under it as a new, separately-named set rather than overwriting the existing ones.

---

## 7. What remains before claiming natural-data improvement

Nothing here supports a claim of improved legal correctness, and the controlled benchmark
cannot support one on its own — its items are rule-generated and lexically close to canonical
text, making 0.968 macro F1 a **ceiling**, not an expected field accuracy.

Outstanding, in dependency order:

1. **GPU correction validation** — the §5 command. Until it runs, the correction half of the
   pipeline is unvalidated under labeled framing.
2. **Claim granularity** — now the dominant natural-data bottleneck. Real NyayaRAG sentences
   bundle several citations, metalinguistic description ("which define the offence of
   murder") and case-level assertions into one claim unit, then get verified against a single
   provision. Labeling the premise cannot fix a claim that is not a restatement of that
   provision. This needs claim segmentation, not a better verifier.
3. **Precision guard for labeled framing on natural text** — the 3 natural flips include
   shallow entailments. Before labeled framing is trusted on real cases, this needs measuring
   on more than 3 examples.
4. **Evidence coverage** — 50/88 natural claims in n=30 still have NO_EVIDENCE, and 15/59
   synthetic claims fail `act_norm` matching. Unchanged by this work.
5. **Lawyer ground truth** — still the only thing that can convert any NLI verdict into a
   statement about legal correctness. Until it exists, every number in this document
   describes model behaviour, not law.
