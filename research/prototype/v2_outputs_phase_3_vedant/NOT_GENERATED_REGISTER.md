# NOT-GENERATED REGISTER — V2 package

Everything the V2 brief asked for that this package does **not** contain, and exactly why.
Nothing in this file is a placeholder or a stub: if a result is listed here, no figure, table
or metric claiming it exists anywhere in the package.

Generated 2026-09-18. Scope: `research/prototype/v2_outputs_phase_3_vedant/`.

---

## 1. The hard environment constraint that drives most of this register

The machine this package was generated on **has no GPU** and **no longer has the project's
pinned environment**:

| | This session | The environment every historical GPU result was produced in |
|---|---|---|
| Python | 3.13.1 | 3.11.9 |
| torch | 2.13.0+**cpu** | 2.2.2+**cu121** |
| transformers | 5.15.1 | 4.40.2 |
| CUDA available | **False** | True (RTX 4050, 6 GB) |
| `research/.venv` | **does not exist** | present |

Model availability on this machine:

| Model | Role | Cached locally? | Usable here? |
|---|---|---|---|
| `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | NLI verification | **Yes** | **Yes — verified working on CPU** |
| `Qwen/Qwen2.5-7B-Instruct` | generation **and** correction | **No** | **No** — not cached, and 4-bit inference needs the GPU that is absent |
| `sentence-transformers/all-MiniLM-L6-v2` | embedding retrieval experiment | **No** | **No** — `sentence_transformers` not installed either |

Missing Python packages: `rank_bm25`, `sentence_transformers`, `accelerate`, `bitsandbytes`.

**Consequence:** every experiment that needs Qwen text generation or Qwen correction is
**RERUN_INFEASIBLE** here, and every BM25/embedding retrieval arm is **RERUN_INFEASIBLE**.
Verification-only re-analysis of already-generated text is CPU-feasible, and that is exactly
what this package's fresh experiments do.

No package was installed and no dependency was added to produce this package. Installing
`rank_bm25` (a small pure-Python package) would unblock item 3.1 below; that was deliberately
**not** done, because changing the user's environment was outside the brief.

---

## 2. Experiments NOT rerun — and why

### 2.1 Anything requiring Qwen generation or Qwen correction — RERUN_INFEASIBLE

Not rerun: the correction funnel, correction-outcome and correction-safety experiments, the
`narrow_primary_hypothesis` GPU batch (n=62), the assertion-aware correction paired replay
(n=10), the labeled-correction GPU validation, the `final_gpu_validation` paired arms, and
every natural-data batch that involved generating or rewriting text.

- **Why:** requires `Qwen/Qwen2.5-7B-Instruct` (uncached, ~15 GB download) **and** a CUDA GPU
  (absent). `src/generator.py` and `src/corrector.py` deliberately raise rather than falling
  back to CPU — a design decision documented in the source, not a bug.
- **What the package does instead:** these results are reported as **HISTORICAL / REUSED**,
  always labelled as such, always with their original artifact path, n, and date. They are
  never presented as fresh V2 measurements.
- **Consequence for the research narrative:** the ORIGINAL→LATEST comparison in this package is
  **fully fresh for the deterministic and verification-side subsystems** (parser, evidence
  matching, evidence pool, NLI verification, verdict assignment, threshold behaviour) and
  **historical-only for the correction and end-to-end generation subsystems**. That split is
  stated on every affected table and figure.

### 2.2 BM25 and sentence-embedding retrieval comparison — RERUN_INFEASIBLE

- **Why:** `rank_bm25` and `sentence_transformers` are not installed, and the MiniLM checkpoint
  is not cached.
- **Historical result, reused and labelled HISTORICAL:** on a 30-case pre-registered set
  (21 should-match + **9** adversarial near-miss Act names), correct-reject rate was
  Jaccard **9/9**, BM25 **3/9**, embedding **2/9**. Both alternatives were
  **EVALUATED_AND_REJECTED**; Jaccard remains the default.
- **Note the widely-repeated description is wrong:** several repo documents describe this as
  "30 adversarial cases". It is 30 pre-registered cases of which **9** are adversarial. The
  9/9, 3/9, 2/9 rates are over the 9, not the 30. This package uses the corrected description.
- **Additional finding that makes the rerun less important than it looks:** the LATEST audit
  found that `evidence_matching.fuzzy_method` is **never read by any call site** — all four
  `match_evidence()` calls in `pipeline.py` pass positional arguments, so `"jaccard"` comes from
  the function default. BM25/embedding retrieval is therefore **unreachable from production
  regardless of the config value**. See `CHANGE_IMPACT_AUDIT.md` discrepancy D1.

### 2.3 Joint four-/five-lever ORIGINAL→LATEST ablation — NOT_EXECUTED (and not executable here)

- **Status:** this experiment does not exist anywhere in the project's history, and it cannot be
  created here.
- **Why not here:** varying all production levers from one common baseline in a single run
  requires end-to-end runs with Qwen generation **and** correction. See 2.1.
- **Why it matters:** four levers (`premise_framing`, `use_evidence_v1`, `atomic_scope_check`,
  `narrow_reverification_hypothesis`) were flipped in a **single commit** (`100e263`), so their
  joint effect is **confounded** in every artifact that postdates it.
- **Therefore:** this package reports **single-lever** effects and says so on every figure and
  table. **No additive or interaction effect between levers is claimed anywhere**, and the
  headline figure `F01` carries an explicit warning that its five panels are five separate
  experiments and must not be averaged or read as one system score.

### 2.4 A true end-to-end ORIGINAL-codebase run — NOT_EXECUTED

- **What would be ideal:** running commit `0e37525` end-to-end (generate → parse → retrieve →
  verify → correct) against HEAD end-to-end on the same cases.
- **Why not:** generation and correction are Qwen-dependent (2.1).
- **What was done instead, and it is a genuine partial substitute:** the **deterministic front
  half** of the original codebase *was* re-executed. `scripts/rerun_parser_original_vs_latest.py`
  extracts `claim_parser.py`, `evidence_matcher.py` and `data_loader.py` from commit `0e37525`
  via `git show` at runtime and runs them, in-process, against the LATEST modules over identical
  already-generated text. That is a real original-codebase execution, not a reconstruction from
  stored artifacts — but it covers parsing and retrieval only, **not** generation, correction or
  re-verification.

### 2.5 Docker reproducibility — ENVIRONMENT_BLOCKED (inherited)

- Not attempted. The repository already records Docker as environment-blocked on the development
  machine and explicitly does not claim it passes. This package does not re-test it and makes no
  Docker claim.

---

## 3. Figures requested by the brief that were NOT generated

| # | Requested figure | Status | Reason |
|---|---|---|---|
| 12 | Retrieval safety (Jaccard vs BM25 vs embedding) | **Historical only, no fresh figure** | Cannot be rerun (2.2). Reported as a table with a HISTORICAL label rather than a figure implying fresh measurement. |
| 13 | Verdict distributions | **Partial** | Fresh verdict distributions exist for GOLD-02 (all four 2×2 cells). Natural-data verdict distributions are Qwen-dependent and remain historical. |
| 14 | Premise framing | **Generated** (F03, F09, F11) | — |
| 15 | Confidence distributions | **Generated from fresh data** | Per-item softmax distributions were stored by the fresh GOLD-01 run. |
| 17 | Correction funnel | **Historical only** | Qwen-dependent (2.1). |
| 18 | Correction outcomes | **Historical only** | Qwen-dependent (2.1). |
| 19 | Correction safety | **Historical only** | Qwen-dependent (2.1). |
| 20 | Ablation results | **Single-lever only** | The joint ablation does not exist (2.3). |
| 21 | Runtime / resources | **Severely limited — see §4** | |
| 25 | Re-verification outcomes | **Historical only** | Qwen-dependent (2.1). |

Every figure that *was* generated is listed with its source artifact and fields in
`figures/figure_provenance_core.json` and `validation/figure_traceability.csv`.

---

## 4. Runtime / resource comparison — NOT COMPARABLE, deliberately not charted as one

A meaningful ORIGINAL-vs-LATEST runtime comparison **cannot** be made from this session:

- The historical runtime and VRAM numbers were measured on a CUDA GPU with 4-bit Qwen loaded.
  Nothing equivalent can be measured here.
- The fresh timings this package *does* have are **CPU-only NLI timings under a different
  torch/transformers major version**, and they are not comparable to the historical ones.
- Worse, they are not even internally comparable between arms in the way a reader would assume:
  in the fresh GOLD-01 run the `labeled` arm took 471.5 s against the `bare` arm's 112.7 s — but
  that difference is dominated by longer premise strings and by CPU thermal/scheduling variation
  on a shared machine, **not** by a meaningful algorithmic cost difference. Charting it as a
  "LATEST is 4× slower" result would be actively misleading.

**Therefore:** raw timings are recorded in the metric JSONs for completeness, and the runtime
figure directory contains a `README` stating this, but **no runtime comparison chart is
produced** and no runtime claim is made.

---

## 5. Things that do not exist in the project at all

| Item | Status |
|---|---|
| Lawyer-validated ground truth | **Does not exist anywhere in this project.** No accuracy claim in this package is a legal-correctness claim. |
| Gold labels for claim *extraction* | **Do not exist.** The parser results are coverage/retrieval outcomes ("did the extracted citation resolve to an audited evidence record"), never precision/recall of extraction. |
| Gold labels for any natural (unlabeled) batch | **Do not exist.** Only GOLD-01 (n=420) and GOLD-02 (n=59) carry construction-rule gold labels. |
| A formal 15-category red-team safety evaluation | **Never performed.** |
| An HF `revision=` pin for any model | **Absent** at both ORIGINAL and LATEST — no `from_pretrained()` call pins a checkpoint SHA, so exact model-weight identity is `UNDETERMINED` for every historical result. |
| Any pre-`0e37525` system state | **Unrecoverable.** `0e37525` is the sole root commit, and it is a squashed import of an already-mature prototype. |

---

## 6. Known open discrepancies carried, not resolved

These are recorded rather than fixed, because fixing them would mean altering frozen research
artifacts, which this package does not do.

| ID | Discrepancy | Where |
|---|---|---|
| P-1 | Re-executing the **committed** `223eb9d` parser yields **54** claims resolving to evidence where the artifact committed at that same commit records **51**. Component isolation rules out the matcher and loader; the counting rule is identical. Most likely the artifact was generated from a working tree that differed slightly from the committed source. **Both endpoints (38 and 57) reproduce their committed artifacts exactly**, so no ORIGINAL→LATEST conclusion depends on this. | `metrics/parser_original_vs_latest_v2.json` → `reconciliation_against_committed_artifacts` |
| E-1 | `config/prototype.yaml` describes the evidence expansion as "78 new + the 59 v0 records" = 137, but the true merged total is **136**. Correct decomposition: 59 + 75 new-usable + 2 promoted-from-unusable. | `metrics/evidence_pool_composition_v2.json` |
| D-1 | `evidence_matching.fuzzy_method` (and three sibling keys) are **never read**; BM25/embedding retrieval is unreachable from production. | `CHANGE_IMPACT_AUDIT.md` |
| D-3 | `pipeline.py:1353` hardcodes a "59-record" corpus disclaimer while the live pool is **136**, so every output record contradicts its own `usable_evidence_pool_size` field. | `CHANGE_IMPACT_AUDIT.md` |
| C-1 | The repository's five-lever "NyayaMind v0" baseline is described as exactly reproducing pre-2026-08-27 behaviour. It **does not** at HEAD: the negation gate, year-conflict veto, injection guard and ordinal guard are unconditional and are **not** lever-controllable. O-CFG is strictly more gated than the real pre-2026-09-09 system. | `SYSTEM_COMPARISON.md` |
| C-2 | Under O-CFG the sibling-regression gate is **silently inactive** (gated on truthy `atomic_scope_check`) while four newer gates stay on. | `SYSTEM_COMPARISON.md` |

---

## 7. Test-suite status — reconciled, not refuted

The repository documents **302/302 tests passing**. Observed at HEAD in this session:
**290 passed, 1 skipped, 0 failed, 0 errors**.

These agree. The single "skip" is the whole of `tests/test_retrieval_signals.py` (**12 tests**),
skipped at module level by `pytest.importorskip("rank_bm25")` because `rank_bm25` is not
installed here. **290 + 12 = 302.** There is no regression; the difference is entirely the
missing optional dependency described in §1.
