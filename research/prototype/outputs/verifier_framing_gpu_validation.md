# Premise-Framing GPU Validation — genuine end-to-end correction path

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. Follows `verifier_framing_validation.md` (CPU phase), which this
report's §5 command completes.

> **Scope of every verdict below.** These are outputs of a small public NLI model
> (DeBERTa-v3-base-mnli-fever-anli) and a 7B instruction model (Qwen2.5-7B-Instruct,
> 4-bit) run against a 59-record, deliberately corrupted SYNTHETIC stress set built over
> a third-party-sourced evidence corpus. They are **not** legal-correctness
> determinations. No lawyer ground truth exists. This is a controlled ablation of one
> config knob (`verification.premise_framing`), not a natural-data evaluation, and no
> natural 30-case evaluation was re-run for this report.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

---

## 0. Environment confirmed before running anything

| Check | Result |
|---|---|
| Git branch | `main`, up to date with `origin/main` |
| Git commit at start | `fe8b15b` ("pre-gpu correction validation, 23/30 or 76.7% Qwen correction passed under labeled framing") |
| Working tree | clean except `baseline/LegalSeg` submodule pointer (unrelated, pre-existing) |
| CUDA | System default Python (3.14, `C:\Program Files\Python314`) has **CPU-only** torch 2.10.0+cpu — no CUDA. The project's GPU environment is a separate venv, `research/.venv` (torch 2.2.2+cu121, `torch.cuda.is_available() == True`) |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6140 MiB dedicated VRAM (driver 592.82, CUDA 13.1) |
| Qwen2.5-7B-Instruct cache | Present, complete: `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct`, 4 safetensors shards + tokenizer, snapshot `a09a3545...` |
| DeBERTa-v3-base-mnli-fever-anli cache | Present, complete: `~/.cache/huggingface/hub/models--MoritzLaurer--DeBERTa-v3-base-mnli-fever-anli`, snapshot `6f5cf0a2...` |
| Pre-run test suite (`research/.venv`) | **119 passed, 0 failed** |

All inference in this report used `research/.venv`'s interpreter. All commands run from
`research/prototype/`.

---

## 1. What was already measured, and where (do not re-derive these)

| Result | Source | Hardware | What it measured |
|---|---|---|---|
| Controlled benchmark, bare | `controlled_benchmark_deberta_metrics.json` | CPU/GPU (pre-existing) | 420-item NLI accuracy, bare premise |
| Controlled benchmark, labeled | `controlled_benchmark_deberta_labeled_metrics.json` | pre-existing | same 420 items, labeled premise |
| Synthetic verification-only, bare vs labeled | `framing_comparison_synthetic_metrics.json` | **CPU** | contradiction recall, false-positive rate, correction *triggers* only — no Qwen involved |
| Stored-correction re-scoring, bare vs labeled | `correction_reverification_framing.jsonl/.md` | N/A (re-scoring only) | Re-verified the **30 corrections Qwen already produced under bare-framing flagging** (from the committed `run_synthetic_stress.jsonl`) against a labeled premise instead. **No new text was generated.** Result: 0/30 → 23/30 (76.7%) would-ship. |
| **This report** | `framing_comparison_gpu_n12_*`, `framing_comparison_gpu_n59_*` | **GPU (RTX 4050)** | Genuine end-to-end run: Qwen corrector actually invoked, actually regenerates text, and the regenerated text is actually re-verified — separately, and consistently, for each framing arm |

The distinction that matters: **§ of this document is the first time correction has
actually executed under labeled framing.** Everything upstream of this either used a
CPU-only verifier (no generation) or re-scored bare-framing corrections rather than
generating new ones under labeled framing.

---

## 2. GPU run — method

Both arms (bare, labeled) are produced in one process invocation of
`scripts/compare_premise_framing_synthetic.py --device cuda --with-correction`, so they
see **identical cases**, the same loaded Qwen2.5-7B-Instruct and DeBERTa instances, the
same 0.70 threshold, the same seed (42), and the same safety gate — only
`verification.premise_framing` differs between the two loop passes. The script was
extended (not the pipeline or verifier) to add:

- per-arm and cumulative peak-VRAM tracking (`torch.cuda.max_memory_allocated`, reset
  once before model load),
- per-arm wall-clock runtime, split into verification-only vs correction-only seconds,
- an explicit **unflagged-claim preservation** check (does the unflagged sentence — `c2`
  — reappear verbatim in whatever text the corrector produced, for every case an attempt
  was made on — independent of, though it should always agree with, the pipeline's own
  `correction_scope_violation` gate),
- separate per-arm output files (`..._bare_results.jsonl`, `..._labeled_results.jsonl`)
  in addition to the combined file the bare-arm reproduction gate reads.

No change was made to `src/pipeline.py`'s safety gate (`status = "corrected"` iff
re-verification == ENTAILED), `src/corrector.py`, or the 0.70 threshold. The bare arm's
verdicts were checked against the committed `run_synthetic_stress.jsonl` before trusting
either arm's numbers (§3).

Two runs were made, per the recommended sequence in `verifier_framing_validation.md`:

1. **Smoke test**, deterministic first-12-case subset (`--limit 12`), to confirm no
   crash / OOM / obviously wrong behaviour before committing to the full set.
2. **Full run**, all 59 synthetic cases — judged computationally reasonable after the
   smoke test (≈5 min for 12 cases including model load), so the full 59 was run rather
   than stopping at the subset.

---

## 3. Validity gate

The bare arm's `c1` verdicts must reproduce the committed `run_synthetic_stress.jsonl`
before any comparison is trusted.

**Full 59-case GPU run: 59/59 verdicts agree, 0 sub_reason mismatches, max confidence
drift 0.0034.** (The CPU comparison run earlier had reported 1 sub_reason mismatch from
an fp32-vs-fp16 knife-edge case; running on GPU under fp16 — the same precision the
original committed run used — reproduces it exactly, including that sub_reason.) Gate
passed; the comparison below is trusted.

---

## 4. Results — genuinely regenerated, full 59 cases

| # | metric | bare | labeled |
|---|---|---|---|
| 1 | contradiction recall (overall, 59) | 21/59 = **35.6%** | 27/59 = **45.8%** |
| 2 | contradiction recall (44 evidence-matched) | 21/44 = **47.7%** | 27/44 = **61.4%** |
| 3 | false-positive rate (c2 wrongly CONTRADICTED) | **0.0%** | **0.0%** |
| 4 | correction triggers | 30 | 36 |
| 5 | correction attempts | 30 | 36 |
| 6 | corrections that pass re-verification = SUCCESS | **0/30 = 0.0%** | **26/36 = 72.2%** |
| 7 | correction_failed | 30 | 10 |
| 8 | correction_scope_violation | **0** | **0** |
| 9 | unsafe corrections shipped (shipped but not ENTAILED) | **0** | **0** |
| 10 | unflagged-claim preservation | **30/30 = 100%** | **36/36 = 100%** |
| 11 | peak VRAM (cumulative, both models resident) | 7,502 MiB | 7,502 MiB (same process) |
| 12 | runtime (arm total / correction-only) | 572.9s / 569.5s | 670.1s / 667.8s |

Attempts == triggers in both arms, confirming the pipeline's "at most one correction
attempt, for the first flagged claim" behaviour held throughout — no case silently
skipped an attempt it should have made.

Reverification verdict breakdown:

| | ENTAILED | CONTRADICTED | NOT_ENOUGH_INFORMATION |
|---|---|---|---|
| bare (30 attempts) | 0 | 2 | 28 |
| labeled (36 attempts) | 26 | 5 | 5 |

12-case smoke subset (for reference, same method, `--limit 12`): bare 5 triggers / 0
shipped; labeled 6 triggers / 5 shipped — directionally identical to the full run.

**Peak VRAM note:** `torch.cuda.max_memory_allocated()` reported 7,502 MiB, which
exceeds the 6,140 MiB of *dedicated* VRAM `nvidia-smi` reports for this laptop GPU. This
machine runs WDDM with shared-GPU-memory fallback (system RAM backing GPU allocations
under pressure); the figure is reported as measured rather than clipped or adjusted, but
should be read as "peak allocated," not "peak dedicated VRAM headroom used." No OOM
occurred at any point in either run.

---

## 5. Bare vs labeled: genuinely regenerated vs re-scored historical

| | bare (production default) | labeled |
|---|---|---|
| **Re-scored historical** (`correction_reverification_framing.md`) — Qwen text generated once under bare-flagging, only the re-verification premise varied | 0/30 = 0.0% | 23/30 = 76.7% |
| **Genuinely regenerated, this report** — Qwen invoked separately per arm, flagging AND correction-prompt evidence AND re-verification all under the arm's own framing | 0/30 = 0.0% | 26/36 = 72.2% |

The two labeled-framing figures (76.7% vs 72.2%) are close but not identical, and they
should not be treated as the same measurement — the denominators differ (30 stored bare
corrections vs 36 genuinely-labeled-triggered cases; the labeled arm flags 6 more cases
than bare, including some that never had a stored bare correction to re-score in the
first place) and the *correction text itself* is now genuinely different, generated
independently by the model twice. That the two numbers land in the same range is
corroborating, not redundant — it shows the improvement is not an artifact of reusing
bare-arm-generated text, since here the text was regenerated too.

**Bare-framing correction success is exactly 0% in both the re-scored and the fully
regenerated measurement.** Under production's current default, the corrector is
triggered but its output is functionally never accepted by the safety gate — every
single one of 30 real Qwen corrections this run failed re-verification.

---

## 6. Safety

- **Scope violations: 0/30 (bare), 0/36 (labeled).** The corrector never touched the
  unflagged sentence in either arm, across 66 real generation calls.
- **Unsafe corrections shipped: 0/30 (bare), 0/36 (labeled).** By construction
  (`pipeline.py`: `status = "corrected"` iff `result.label == ENTAILED`), this is
  structurally impossible in the current gate, and the GPU run confirms no code path
  bypasses it — 26 shipped corrections all carry an ENTAILED reverification verdict.
- **Unflagged-claim preservation: 100%/100%.** Cross-checked independently of the
  pipeline's own scope-violation gate (§2), same result.
- **False positives: 0% in both arms.** Labeled framing's large recall gain (35.6% →
  45.8%) came with no new false CONTRADICTED verdicts on the untouched claim.

The safety gate was not modified, and no threshold was lowered, for this validation.

---

## 7. Test suite

- **Before GPU inference** (`research/.venv`, same commit): 119 passed, 0 failed.
- **After GPU inference**, same command: **119 passed, 0 failed.**

No regressions from the instrumentation added to
`scripts/compare_premise_framing_synthetic.py` (VRAM/runtime tracking, unflagged-claim
check, per-arm output files) — that script has no dedicated test file and is not
imported by `src/`, so it is outside the 119 but was smoke-tested separately: a CPU-only
verification-only rerun reproduced the committed synthetic baseline 59/59 before the
GPU run was trusted (§3).

---

## 8. Is labeled framing ready to become the production default?

**Not changed in this report — the config default remains `bare`,** per the brief. The
evidence for promotion is now materially stronger than at the CPU-only checkpoint:

In favour:
- Contradiction recall improves substantially with **zero** false-positive cost (§4,
  rows 1–3), reproducing the CPU-only finding under the identical GPU generation
  conditions production uses.
- **The previously open question — does the correction path actually work under
  labeled framing, not just re-scored — is now answered: yes.** 26/36 genuinely
  regenerated corrections pass re-verification (72.2%), against 0/30 (0%) for bare.
- Safety is unaffected: 0 scope violations, 0 unsafe shipments, 100% unflagged-claim
  preservation, in both arms, across 66 real Qwen generations.
- Bare framing's correction path is not merely worse — it is **measured at exactly 0%
  genuine end-to-end success** on this synthetic set. Every real correction bare
  currently ships to reverification fails it.

Against, still:
- This is SYNTHETIC data only — deliberately corrupted claims paired with their own
  correct evidence. No natural-data correction run has been executed under labeled
  framing (natural evaluation was explicitly out of scope for this task).
- Runtime roughly doubles per additional triggered case relative to bare purely because
  labeled framing triggers more corrections (36 vs 30) — expected, not a per-case
  slowdown, but worth noting for capacity planning if promoted.
- Flipping the default still breaks comparability with every committed A/B/C baseline;
  promotion should re-run those baselines under a new, separately-named set rather than
  silently reinterpreting the existing ones.

**Recommendation:** the synthetic, end-to-end case for labeled framing is now complete
and clean. Promotion should happen in a dedicated commit that (a) flips the default,
(b) re-runs A/B/C under it as new, separately-named outputs, and (c) is accompanied by a
natural-data correction run — not bundled into this validation report, per the brief's
explicit instruction not to promote the default here.

---

## Final summary

1. **CUDA/GPU** — `research/.venv` (torch 2.2.2+cu121) has CUDA; system Python does not.
   NVIDIA GeForce RTX 4050 Laptop GPU, 6,140 MiB dedicated VRAM. Both Qwen2.5-7B-Instruct
   and DeBERTa-v3-base-mnli-fever-anli were already fully cached locally; no downloads
   were needed.
2. **Cases/claims evaluated** — full 59-case synthetic stress set, both framing arms, in
   one process invocation (identical cases, models, seed=42, threshold=0.70 for both
   arms). A deterministic 12-case smoke subset was run first and was directionally
   consistent.
3. **Bare results** — contradiction recall 35.6% (47.7% with evidence), 0% false
   positives, 30 correction triggers/attempts, **0/30 (0.0%) corrections shipped**, 30
   correction_failed, 0 scope violations, 0 unsafe shipments, 30/30 unflagged-claim
   preservation.
4. **Labeled results** — contradiction recall 45.8% (61.4% with evidence), 0% false
   positives, 36 correction triggers/attempts, **26/36 (72.2%) corrections shipped**, 10
   correction_failed, 0 scope violations, 0 unsafe shipments, 36/36 unflagged-claim
   preservation.
5. **Correction success comparison** — bare 0.0% vs labeled 72.2%, genuinely regenerated
   end-to-end (not re-scored). Consistent with, and now supersedes, the earlier
   re-scored-historical figure of 0/30 vs 23/30 (76.7%).
6. **Safety comparison** — identical and clean in both arms: 0 scope violations, 0
   unsafe corrections shipped, 100% unflagged-claim preservation. The safety gate was
   not modified and no threshold was lowered.
7. **VRAM/runtime** — peak 7,502 MiB allocated (cumulative across both arms in one
   process; exceeds this laptop's 6,140 MiB dedicated VRAM via WDDM shared-memory
   fallback, no OOM). Runtime: bare arm 572.9s, labeled arm 670.1s (correction
   generation dominates both; labeled ran 6 more corrections than bare).
8. **Tests** — 119 passed / 0 failed before GPU inference, and 119 passed / 0 failed
   after, on `research/.venv`.
9. **Production default** — **not promoted in this report**, per instruction. The
   synthetic end-to-end case for promotion is now complete and materially in favour;
   `config/prototype.yaml` still defaults to `bare`.
10. **Natural evaluation** — **justified now, but not run here** (per instruction, no
    natural 30-case evaluation was executed in this task). The correction path has now
    been validated end-to-end on synthetic data under labeled framing with clean safety
    numbers; the next open question is whether the recall and correction-success gains
    hold on real NyayaRAG claims, which this report does not and cannot answer.
