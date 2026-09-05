# NyayaMind Prototype — Faculty Evaluation Report

**Status: STEP 12 faculty-facing assembly, built exclusively from STEP 11's reconciled
claim register and STEP 1-10B's own artifacts. No new experiment was run to produce
this document.** Every number below carries a citation to a specific source file;
`reports/FINAL_CLAIM_REGISTER.csv` gives the machine-readable version of the same
citations (claim IDs C01-C26 are referenced throughout as `[C##]`).

## 1. Project evaluation methodology

This prototype (a field-level statutory-grounding verification + selective-correction
layer over Qwen2.5-7B-Instruct generation and a DeBERTa-v3 NLI verifier) was evaluated
in twelve sequential steps: workspace/provenance setup (1), environment validation (2),
input inventory (3), a controlled GOLD benchmark evaluation (4), component/unit testing
(5), a natural-data METRIC-ONLY evaluation (6), an ablation analysis (7), metric
consolidation (8), figure generation (9), GPU execution validation (10), GPU experiment
reproduction (10B), and final reconciliation (11) — this report is the product of step
12. Every step's raw outputs live under `research/prototype/testing/actual_outputs/`;
nothing in this report is computed fresh — it is a synthesis layer.

## 2. Evidence classification taxonomy

Every finding in this project carries exactly one of the following labels, applied
consistently and never collapsed into another:

- **GOLD** — measured against an independently-constructed or by-construction label
  (a controlled benchmark or deliberately-corrupted stress set). Supports an accuracy/F1
  claim *on that benchmark only*.
- **METRIC-ONLY** — a real, descriptive measurement on natural (uncurated) legal text,
  with **no independent correctness label**. Never an accuracy or F1 claim.
- **SOFTWARE BEHAVIOR** — a fact about what the code does (e.g., test pass counts,
  which code paths require a GPU), not a claim about legal or statistical correctness.
- **HISTORICAL-ONLY** — a result that exists only from a prior run and cannot currently
  be freshly reproduced, for a documented structural reason.
- **GPU-REPRODUCED** — an experiment that has now been freshly re-executed on a
  GPU-equipped machine (STEP 10/10B), with an explicit comparison to any prior result.
- **DIAGNOSTIC** — evidence exists but is too small in sample, too narrowly isolated,
  or too indirect to support a general claim; useful as a signal, not as proof.

## 3. Environment and reproducibility

Two distinct machines were used across this project's evaluation, and their
capabilities must never be conflated:

| | STEP 1-9 machine | STEP 10/10B machine |
|---|---|---|
| GPU | **None** (AMD Radeon integrated only) | NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB VRAM |
| `torch.cuda.is_available()` | `False` | `True` |
| Qwen generation / correction | Not executable (`src/generator.py`/`src/corrector.py` hard-require CUDA by design, no CPU fallback) | Executes successfully |
| Python / torch / transformers / accelerate / bitsandbytes | 3.11.9 / 2.2.2+cu121 / 4.40.2 / 0.29.3 / 0.43.1 (canonical, pinned in `research/requirements.txt`) | Identical — `research/.venv` on this machine already matched the canonical spec exactly, zero version substitutions |
| Regression suite | 205/205 passed | 205/205 passed |

**The STEP 1-9 machine's GPU absence is a fact about that specific machine, not a
permanent project limitation.** [C11] It remains true and unchanged as the historical
record of STEP 1-9. It does not describe the project's current GPU capability, which
STEP 10/10B independently demonstrates.

## 4. Component testing

The full regression suite — **205 tests, 205 passing** — is the sole authoritative test
count, unchanged across every step from STEP 2 through STEP 12 (re-run and confirmed at
each step, most recently after STEP 10B's GPU experiments and again for this report).
`[C23]` Zero of the 205 tests require CUDA or Qwen to pass — GPU-dependent code paths are
exercised in tests via `FakeGenerator`/`ScriptedCorrector` fixtures, not the real model
`[C26]` — which is exactly why the suite produces an identical 205/205 result on both the
CPU-only and GPU-equipped machines. STEP 5's 7 component-test groups (counts: 111, 72,
48, 3, 15, 35, 5) sum to 289, **not** 205, because they are overlapping categorizations
of the same 205 tests by pipeline stage — group counts are never an alternative total.

## 5. Controlled GOLD benchmark results

**GOLD-01** (n=420, controlled verifier benchmark): accuracy 0.7333 (bare) → 0.9714
(labeled) `[C01, C02]`; macro F1 0.7487 (bare) → 0.9684 (labeled) `[C03, C04]`. McNemar
χ²=98.01, p=4.16×10⁻²³; independently-matching exact sign test p=1.58×10⁻³⁰. Evidence
grade **A** — the single strongest statistical result in this project. **This is a
curated benchmark with mechanically-constructed hypotheses, not real generated text; it
does not establish a natural-data accuracy figure.**

**GOLD-02** (n=59, synthetic stress set, deliberately corrupted by construction):
contradiction recall 0.3559 (bare) → 0.4576 (labeled) `[C05, C06]`. Evidence grade **A**
as a by-construction-labeled set. Every record here is contradictory by design — this
figure does not generalize to naturally-occurring claims.

## 6. Natural-data observations (METRIC-ONLY — no accuracy or F1 claim)

- **209-claim paired natural set** (same 209 claims, evidence pool varied):
  evidence coverage 63.2% (v0 pool) → 70.3% (v0+v1 pool) `[C07, C08]`. McNemar
  χ²=13.0667, p=0.00030060; exact sign test p=6.10×10⁻⁵; 15 claims gained evidence,
  0 lost, 194 unchanged. Evidence grade **A**, classification **SUPPORTED** — this is a
  coverage-mechanism finding, not a correctness or accuracy finding.
- **588-claim natural aggregate**: 66.3% evidence coverage (390/588) `[C14]`; verdict
  distribution NOT_ENOUGH_INFORMATION=364, NO_EVIDENCE=198, ENTAILED=21,
  CONTRADICTED=5 `[C15]`. Purely descriptive — no independent label exists for any of
  these 588 claims; ENTAILED/CONTRADICTED are model verdicts, not validated facts.
- **147-claim evidence-matched subset** (bare→labeled): ENTAILED reached 0→13 `[C17]`;
  CONTRADICTED unchanged 3→3 `[C18]`. Evidence grade **B**. Before/after counts on the
  same claims, not an accuracy comparison (no ground truth exists to score against).

## 7. Evidence-v1 findings

Evidence-v1 (expanding the usable evidence pool from 59 to 137 records) is, per
`ABLATION_FACULTY_SUMMARY.md` §2, **the strongest result specifically on real natural
data**: +7.1 percentage points evidence coverage on the 209-claim paired set, McNemar
p=0.0003, zero regressions (no claim ever lost evidence it previously had). This finding
is now corroborated two ways: STEP 6's CPU-only fresh re-verification (unchanged since
STEP 6/7/8) **and** STEP 10B's exact GPU re-execution of the underlying Qwen generation
itself (§9 below). The GPU reproduction confirms the generation step is exactly
repeatable — it does not add new statistical evidence beyond STEP 6's already-supported
finding, and does not raise M05's evidence grade beyond its existing A. `[C09]`

## 8. Ablation findings and evidence grades

Per `evaluation/ABLATION_EVIDENCE_GRADES.md` and `evaluation/ABLATION_FACULTY_SUMMARY.md`,
9 levers were graded A-E:

| Factor | Grade | Basis |
|---|---|---|
| Premise framing (GOLD-01) | A | McNemar p=4.16e-23, curated benchmark |
| Evidence v1 (209-claim paired) | A | McNemar p=3.01e-04, real natural data, zero regressions |
| Premise framing (natural 147-subset) | B | Real data, smaller scale, no independent test |
| Claim parser fix | B | n=30, sign test p=0.03125, 0 cases worsened |
| Confidence threshold (0.70) | B | Flat/non-fragile region, not proven optimal |
| Atomic scope check | C | n=11, 1 unblocked, no downstream shipping verified |
| Narrow re-verification | C | n=3, confidence-calibration shift only, DIAGNOSTIC/HISTORICAL-ONLY |
| Correction levers (targeted) | C | n=5 vs 10 triggered, too small for significance |
| Joint four-lever isolation | E | **Does not exist** — no protocol, none invented |

**No grade was changed by STEP 10, STEP 10B, or this reconciliation.** STEP 10/10B only
added "freshly reproduced on GPU" annotations to two already-graded findings (evidence
v1's generation step; correction levers targeted) — reproducibility confirmation, not a
grade upgrade.

## 9. GPU validation and reproduction (STEP 10/10B)

STEP 10 validated a real, GPU-equipped second machine (NVIDIA GeForce RTX 4050 Laptop
GPU, 6 GB VRAM, driver 592.82, CUDA 12.1 torch build) `[C11]` and, on it:

- Verified `torch.cuda.is_available()==True`; ran a real CUDA matmul + CPU round-trip.
- Loaded the real production `StatuteGroundingGenerator` (Qwen2.5-7B-Instruct, 4-bit
  nf4 quantization) and `NLIVerifier` (DeBERTa) successfully.
- Executed one real minimal Qwen generation `[C12]` and a real 5-case correction-pipeline
  smoke test `[C13]` via the unmodified production entry point `scripts/run_mvp.py`.
- **Exactly reproduced** the historical 10-case targeted labeled-framing
  correction-validation experiment — byte-identical corrected text for all 10 cases,
  identical status counts, identical shipped/unsafe counts. `[C10]`

STEP 10B then closed the one gap STEP 10 left open: the 209-claim, 50-case, two-arm
evidence-v0-vs-v1 **generation** experiment behind `outputs/final_gpu_validation_{A,B}.jsonl`.
This is genuinely distinct from STEP 6's prior work — STEP 6 only ever re-read
already-stored verdicts and did CPU-only re-verification (confirmed from
`run_step6_209_paired_evaluation.py`'s own docstring: "No Qwen generation or correction
is invoked"). STEP 10B re-ran the actual Qwen generation itself, on GPU, and the result
was an **exact reproduction**: all 50/50 generated texts byte-for-byte identical to the
2026-08-27 historical run, every per-arm metric identical (claims=209, evidence-matched
132/147, verdict counts, correction triggers 5/5, shipped 0/0, unsafe 0/0), identical
peak VRAM (7547 MiB). `[C09]` Classification: **FRESH GPU REPRODUCED**.

**Explicit, permanent distinction**:
- *CPU-only machine limitation*: applies only to the STEP 1-9 machine. Permanent fact
  about that machine; does not change.
- *GPU validation machine*: the separate STEP 10/10B machine, on which real Qwen
  generation and correction demonstrably execute.

No unscoped "GPU unavailable" statement survives anywhere in this workspace — every
occurrence found during STEP 11's audit already read "this machine," correctly
describing the STEP 1-9 machine at the time it was written.

## 10. Correction findings

Three populations, kept strictly separate (never pooled, except where the project's own
historical `outputs/final_metrics.json` already pools them — itself flagged as a
limitation, §12):

- **Synthetic** (GOLD-02-adjacent, n=59 cases): labeled framing 26/36 (72.2%) shipped;
  bare framing 0/30 shipped. `[C21]` HISTORICAL-ONLY.
- **Natural targeted** (framing-isolated comparison, same 50-case batch): bare 0/5 →
  labeled 1/10 shipped `[C19]`. Not statistically supported at this n. Evidence grade
  **C**. **Exactly reproduced on GPU** in STEP 10 (10-case run) and independently
  corroborated again inside STEP 10B's 209-claim re-run (5-trigger subset per arm, also
  exact).
- **Natural cumulative** (project's entire correction history): 1/56 shipped (1.8%),
  0 unsafe `[C20]`. Evidence grade **D**. **HISTORICAL-ONLY, PROTOCOL INSUFFICIENT for
  fresh reproduction** — see §12.

## 11. Safety observations

**0 unsafe corrections observed** across every correction attempt tested in this
project's history (56 natural + 66 synthetic = 122 total attempts) `[C22]` — an
**observed count in the tested population**, not a probabilistic guarantee and not a
universal safety claim. STEP 10/10B's fresh GPU reproductions (10-case targeted, 5-case
smoke test, 209-claim 5-trigger-per-arm set) add 0 further unsafe shipments to this
observed count — consistent with, not proof extending, the historical figure.

## 12. Figures index/reference

See `FACULTY_RESULTS_TABLE.md` for the headline-metric table and the figure map below
for the 11 STEP 9 figures (unchanged, not regenerated — see §14).

| # | Filename | Demonstrates | Source contract | Safe interpretation |
|---|---|---|---|---|
| 01 | `01_overall_metric_comparison.png` | Magnitude of original→current change across 4 distinct metric types | `evaluation/figure_data/01_overall_metric_comparison.csv` | Each metric is a distinct kind of measurement; do not compare bar heights across categories as equivalent |
| 02 | `02_evidence_coverage.png` | 209-paired + 588-claim evidence coverage, with McNemar test | `.../02_evidence_coverage.csv` | Evidence-v1 increased observed retrieval coverage on real paired claims with zero regressions; not accuracy |
| 03 | `03_verdict_distribution.png` | Observed verifier-verdict counts, 588 natural claims | `.../03_verdict_distribution.csv` | Descriptive distribution only; no independent ground truth exists for this data |
| 04 | `04_correction_funnel.png` | Correction pipeline stage counts, 5 populations, never merged | `.../04_correction_funnel.csv` | Per-population funnel counts; no single combined success rate. **Populations include the 209-claim/targeted-correction data since exactly GPU-reproduced in STEP 10/10B — see `[C09]`/`[C10]`; the plotted values themselves are unchanged (exact match).** |
| 05 | `05_correction_outcome.png` | Shipped/failed/scope-violation breakdown per population | `.../05_correction_outcome.csv` | Directional shift only; 1/10 and 1/56 are not statistically validated rates |
| 06 | `06_safety.png` | Observed safety-mechanism counts across tested correction history | `.../06_safety.csv` | 0 unsafe observed in tested history; not a guarantee at any scale |
| 07 | `07_confidence_distribution.png` | Mean/median verifier confidence per verdict, 588-claim aggregate | `.../07_confidence_distribution.csv` | Verifier's own certainty, not a correctness signal |
| 08 | `08_ablation_comparison.png` | Evidence-strength grade (A-E) per ablation factor | `.../08_ablation_comparison.csv` | Grade communicates evidence strength, not effect size; no causal claim for the Grade-E joint four-lever row |
| 09 | `09_runtime_resource.png` | Runtime/VRAM, historical GPU arms vs. one fresh CPU arm | `.../09_runtime_resource.csv` | **This figure's own annotation states "NVIDIA GPU available: NO. Qwen generation/correction executed: NOT EXECUTED" — accurate for the STEP 1-9 machine that produced it (unedited, correct historical record). Superseded, not contradicted, by STEP 10/10B's separate-machine results: `[C11]`-`[C13]` show real GPU execution now occurs on a second machine.** |
| 10 | `10_cumulative_natural_results.png` | Evidence coverage across all 11 natural-data regimes, side by side | `.../10_cumulative_natural_results.csv` | Regimes never pooled into one number; not an accuracy measure |
| 11 | `11_synthetic_vs_natural_transfer.png` | Non-equivalence of synthetic (72.2%) vs. natural cumulative (1.8%) shipping | `.../11_synthetic_vs_natural_transfer.csv` | Disjoint populations, different base rates by construction; neither rate predicts the other |

## 13. What was actually tested? (reviewer quick-reference)

1. **Software correctness/behavior**: 205 unit/integration tests, real code paths,
   deterministic fixtures for GPU-only stages — passes identically on both machines.
2. **Controlled benchmark accuracy** (GOLD-01/02): real verifier model, curated/labeled
   inputs, on GPU-free CPU inference — genuine accuracy/F1 figures, scoped to those
   benchmarks only.
3. **Natural-data behavior** (588-claim aggregate, 209-claim paired, 147-claim subset):
   real verifier model, real NyayaRAG case text, **no independent labels** — descriptive
   coverage/verdict/confidence statistics only.
4. **Real GPU generation and correction** (STEP 10/10B): the actual production Qwen
   model and correction pipeline, executed end-to-end on real GPU hardware, with two
   experiments exactly reproduced against 2026-08-27 historical runs.

## 14. Figures remain valid

STEP 9's 11 figures were built entirely from STEP 8's locked
`evaluation/figure_data/*.csv` contracts. STEP 10B's fresh GPU reproduction of the
209-claim experiment produced numbers **identical** to the historical data those figures
already plot — so no figure's displayed data is stale or wrong.

**FIGURES REMAIN VALID — NO REGENERATION REQUIRED.**

## 15. Limitations

See `FACULTY_LIMITATIONS_AND_CAVEATS.md` for the complete, standalone treatment. In
summary: (1) the cumulative 1/56 correction rate cannot be freshly re-derived from any
single recoverable protocol; (2) no joint four-lever causal-isolation experiment exists;
(3) a scope-check-mode discrepancy (1/11 vs. an earlier batch-1-only 4/6) remains
unreconciled across two different batches; (4) only 50/82 evidence-v1 audit records were
independently re-fetched; (5) a root-level "Project Author Statement" claiming
professional legal review is unverifiable and is not used as evidence anywhere in this
package; (6) historical GPU runs' exact physical-machine identity is not independently
confirmed beyond matching GPU model/VRAM class. None of these limitations is hidden or
minimized; all six are restated in full in the standalone limitations document.

## 16. Conclusions

- The verifier shows a strong, well-supported accuracy improvement under labeled premise
  framing **on the controlled GOLD-01 benchmark** (grade A) — this does not establish an
  equivalent improvement on natural legal text.
- Evidence-v1 materially and reproducibly increases observed evidence coverage on real
  natural claims, with zero regressions (grade A, natural-data METRIC-ONLY) — this is a
  retrieval/coverage finding, not a correctness finding.
- Real Qwen generation and the full generation→correction→scope-check→re-verification→
  ship/reject pipeline now demonstrably execute on GPU hardware, with two historical
  experiments (10-case targeted correction; 209-claim two-arm generation) **exactly**
  reproduced byte-for-byte.
- The correction mechanism ships very rarely on natural data (1/56 cumulative,
  historical-only) and this rate cannot currently be freshly re-derived; it should not
  be read as a stable success-rate estimate at this sample size.
- Zero unsafe corrections have been observed across 122 tested attempts project-wide —
  an observed-population fact, not a safety guarantee.
- No legal-correctness claim is made or supported anywhere in this project: no
  independent lawyer/human ground truth exists for any natural-data result.
- No joint four-lever interaction claim is made or supported: that experiment does not
  exist, and none of its effect can be inferred from the separate single-lever findings.
