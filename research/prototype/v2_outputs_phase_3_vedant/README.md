# NyayaMind V2 — ORIGINAL vs LATEST evaluation package

**Generated 2026-09-18 · repository `nyayamind-verification` · HEAD `fb4e98f` · nothing committed**

A self-contained, publication- and presentation-ready comparison of the **original** NyayaMind
system against the **latest** one, with every number traced to an artifact and every gap stated.

---

## Start here

| If you want… | Read |
|---|---|
| The whole story in one document | **`SYSTEM_COMPARISON.md`** |
| What changed, one row per change (47 of them) | **`CHANGE_IMPACT_AUDIT.md`** |
| What this package could **not** produce, and why | **`NOT_GENERATED_REGISTER.md`** |
| Whether a specific number is trustworthy | **`validation/metric_traceability.csv`** |
| Whether the package is internally consistent | **`validation/VALIDATION_REPORT.md`** |
| Slides | **`ppt_assets/SLIDE_GUIDE.md`** |

---

## The three things to know before quoting anything

### 1. "ORIGINAL" has two distinct meanings and they are not interchangeable

- **O-CODE** — the original *codebase*, root commit `0e37525` (2026-08-13). A real system that
  really ran. **Exactly one** experiment measures it: the claim-parser comparison.
- **O-CFG** — "NyayaMind v0", a *configuration* baseline: HEAD code with five levers at their
  defaults. **Essentially every other experiment** measures this. It is a legitimate ablation
  arm but **not a historical snapshot** — the five levers never coexisted at their defaults in
  any real production state.

Quoting O-CODE's 43.2% evidence coverage next to O-CFG's 63.2% as if they described the same
system is a category error. Every table and figure in this package states which one it means.

### 2. The models never changed

Generation and correction are the same `Qwen/Qwen2.5-7B-Instruct` (one loaded instance reused for
both); verification is the same `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`. **Every measured
difference in this package is attributable to system, pipeline and configuration changes — not to
a different or better underlying model.**

### 3. The headline verifier result carries a required caveat

GOLD-01 macro F1 moves 0.749 → 0.968, and that reproduces exactly. But **99 of the 100 items the
latest framing fixes lie in the benchmark's *attributed* conditions**, where the original premise
was *constructed* to omit the identifier the hypothesis asserts. On the other 269 items the two
arms are statistically indistinguishable (sign test p = 1.0).

So it evidences **a fixed premise/hypothesis mismatch**, not a general improvement in legal
reasoning. It still matters — real generated claims *are* overwhelmingly attributed — but the
number must always be quoted with the split. See `figures/02_verifier/F11_*.png`.

---

## What was measured fresh for this package

Five experiments were re-executed from scratch on this machine. All are CPU-only, DeBERTa-only,
and deterministic (greedy argmax — no sampling, so no inference seed exists and the runs are
exactly repeatable).

| Experiment | n | Grade | Headline |
|---|---|---|---|
| GOLD-01 verifier, bare vs labeled | 420 | GOLD | acc 0.7333→0.9714, macro F1 0.7487→0.9684, McNemar exact p=1.58e-30 (100 fixed, **0 broken**) |
| GOLD-01 stratified by condition | 420 | GOLD | **99/100 of the gain is in attributed conditions**; non-attributed p=1.0 |
| GOLD-02 contradiction, 2×2 factorial | 59 | DETERMINISTIC_SYNTHETIC | recall 0.3559→0.4576, p=0.0312; **`narrow_primary_hypothesis` effect exactly zero** |
| Parser, 3 real commits re-executed from git | 30 docs | DETERMINISTIC_SYNTHETIC | claims resolving to evidence **38 → 54 → 57**; ORIGINAL→LATEST p=0.0020; INTERMEDIATE→LATEST p=0.25 (**n.s.**) |
| Evidence pool composition | structural | DETERMINISTIC_SYNTHETIC | 59→136 usable records, 10→22 Acts |
| Threshold sensitivity sweep | 420 | GOLD-derived | LATEST leads at **every** threshold 0.34–0.99 |

**Cross-stack reproduction is itself a result.** These runs reproduced the historical numbers
*exactly* — identical accuracy, macro F1 and confusion matrices — on Python 3.13.1 /
torch 2.13.0+cpu / transformers 5.15.1, against historical runs made on Python 3.11.9 /
torch 2.2.2+cu121 / transformers 4.40.2. The parser arms likewise reproduce their committed
artifacts exactly at both endpoints.

---

## What could NOT be measured here

**This machine has no GPU, and `Qwen/Qwen2.5-7B-Instruct` is not cached.** Therefore every
experiment needing text generation or correction — the whole correction and end-to-end
subsystem — is **RERUN_INFEASIBLE** and is reported as **HISTORICAL / REUSED**, always labelled.
`rank_bm25` and `sentence_transformers` are also absent, so the BM25/embedding retrieval arms
could not be rerun either.

**The split is therefore:** fresh evidence for the deterministic and verification-side subsystems
(parsing, retrieval, verification, verdict assignment, thresholds); historical-only evidence for
generation and correction. Full detail and consequences: `NOT_GENERATED_REGISTER.md`.

No package was installed and no dependency added to build this package.

---

## Layout

```
v2_outputs_phase_3_vedant/
├── README.md                     this file
├── SYSTEM_COMPARISON.md          the narrative: original → flaws → changes → latest → evidence
├── CHANGE_IMPACT_AUDIT.md        47 changes, one row each, with evidence grade and limitation
├── NOT_GENERATED_REGISTER.md     everything absent, and exactly why
├── metrics/                      fresh metric artifacts (JSON/CSV) + both system manifests
├── figures/                      01_overview … 10_natural_data
├── diagrams/                     01_original_architecture … 14_flaw_fix_behavior
├── tables/                       headline, verifier, evidence, parser, correction, safety,
│                                 ablation, reproducibility, limitations
├── ppt_assets/                   FIGURE_INDEX, DIAGRAM_INDEX, SLIDE_GUIDE
├── validation/                   VALIDATION_REPORT + metric/figure/table traceability CSVs
└── scripts/                      every generator; re-runnable
```

### Reproducing

Run from `research/prototype/`:

```bash
python v2_outputs_phase_3_vedant/scripts/rerun_gold01_verifier_original_vs_latest.py   # ~12 min CPU
python v2_outputs_phase_3_vedant/scripts/stratify_gold01_by_condition.py               # instant
python v2_outputs_phase_3_vedant/scripts/rerun_gold02_contradiction_original_vs_latest.py
python v2_outputs_phase_3_vedant/scripts/rerun_parser_original_vs_latest.py            # instant
python v2_outputs_phase_3_vedant/scripts/compute_evidence_pool_composition.py          # instant
python v2_outputs_phase_3_vedant/scripts/compute_threshold_sensitivity_v2.py           # instant
python v2_outputs_phase_3_vedant/scripts/build_v2_figures_core.py
python v2_outputs_phase_3_vedant/scripts/build_v2_diagrams.py
python v2_outputs_phase_3_vedant/scripts/build_change_impact_audit.py
python v2_outputs_phase_3_vedant/scripts/build_traceability.py
```

The parser script extracts the original modules from git **at runtime** via `git show` — nothing
is vendored, and the working tree is never checked out or modified.

---

## Rules this package follows

1. **No fabricated values.** Every number is read from a file. If it could not be sourced, it is
   in `NOT_GENERATED_REGISTER.md` instead — never a placeholder.
2. **"Accuracy", "precision", "recall", "F1" and "confusion matrix" are used only for the two
   gold-labelled sets** (GOLD-01 n=420; GOLD-02 n=59, single-class so only *recall* is defined).
   Everything else is coverage, distribution or behaviour — including the parser results, where
   "resolving to evidence" is a **retrieval outcome, not a correctness label**.
3. **Null results are preserved as null.** `narrow_primary_hypothesis` does nothing on GOLD-02;
   post-`223eb9d` parser work is not significant at n=30; assertion-aware correction ships 0/10,
   the same as legacy. None of these is reframed.
4. **Single-lever means single-lever.** Four levers were flipped in one commit, so their joint
   effect is confounded. **No additive or interaction effect between levers is claimed anywhere**,
   and the joint ablation is recorded as NOT EXECUTED.
5. **The old package was not touched.** The prior Phase-3 package lives at
   `research/prototype/archive/2026-09-06_output_phase_3_vedant/` and was read for methodology and
   visual convention only. It was not modified, renamed, deleted, or reused as if freshly
   generated. *(Note: the brief referred to it at `research/prototype/Output_phase_3_vedant/`; it
   had already been archived to that path on 2026-09-12.)*
6. **Nothing was committed**, and no file outside this directory was created or modified.

---

## Known open discrepancies

Recorded, not fixed — fixing them would mean altering frozen research artifacts.

| ID | Discrepancy |
|---|---|
| **D1** | `evidence_matching.fuzzy_method` is **never read** by any call site — BM25/embedding retrieval is unreachable from production whatever the config says. |
| **D3** | `pipeline.py:1353` hardcodes a "59-record" disclaimer while the live pool is **136**. |
| **C-1** | The config's claim that flipping five levers "exactly reproduces" pre-2026-08-27 behaviour is **false at HEAD** — four safety gates are unconditional and not lever-controllable. |
| **C-2** | Under the configuration baseline the sibling-regression gate is **silently inactive**. |
| **E-1** | The config's "59 + 78 = 136" arithmetic does not reconcile; the true decomposition is 59 + 75 + 2. |
| **P-1** | Re-executing the committed `223eb9d` parser yields 54 where the artifact committed at that commit records 51. Both *endpoints* reproduce exactly, so no conclusion depends on it. |

Full detail in `CHANGE_IMPACT_AUDIT.md` §4 and `NOT_GENERATED_REGISTER.md` §6.

---

## What this package does not claim

Never: lawyer-validated, guaranteed legal correctness, universally generalizable,
production-certified, or that a null result is an improvement. No lawyer-validated ground truth
exists anywhere in this project, and no accuracy figure here is a legal-correctness determination
— it is NLI agreement against audited statute text.
