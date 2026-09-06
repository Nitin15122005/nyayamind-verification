# Figure Index (STEP 9)

Full metadata: `FIGURE_METADATA.csv`. Every figure below is generated from a locked
STEP 8 CSV contract — no experimental value was computed or altered in this step.

### Figure 01 — Original vs. Current: Strongest Comparable Metrics

**Purpose:** Show the strongest original-vs-current quantitative comparisons across
heterogeneous metric types on one shared 0-1 scale, visually distinguished by category.
**Input:** `evaluation/figure_data/01_overall_metric_comparison.csv`
**Dataset:** 209-claim paired natural (evidence coverage); GOLD-01 (macro F1, accuracy); GOLD-02 (contradiction recall)
**N:** 209 / 420 / 420 / 59
**Key values:** Evidence coverage 0.632→0.703; Macro F1 0.749→0.968; Accuracy 0.733→0.971; Contradiction recall 0.356→0.458
**Interpretation:** Magnitude of improvement per metric, each a distinct kind of measurement.
**What it does NOT establish:** That natural evidence coverage is verifier accuracy, or that these four metrics are interchangeable.
**Source:** STEP 4 (`gold01_metrics.json`, `gold02_metrics.json`), STEP 6 (`paired_209_metrics.json`)

### Figure 02 — Observed Evidence Coverage

**Purpose:** Show the 209-paired and 588-claim evidence-coverage headline result with the paired McNemar test.
**Input:** `02_evidence_coverage.csv`
**Dataset:** 209-claim paired natural; 588-claim aggregate
**N:** 209, 209, 588
**Key values:** 63.2% → 70.3% (paired); 66.3% (588 aggregate); gained=15, lost=0, unchanged=194; McNemar p=0.000301
**Interpretation:** Evidence-v1 increased observed retrieval coverage on real paired claims with zero regressions.
**What it does NOT establish:** Accuracy, correctness, or legal validity of the evidence found.
**Source:** STEP 6 (`paired_209_metrics.json`, `claims_588_metrics.json`)

### Figure 03 — Verdict Distribution, N=588 Natural Claims

**Purpose:** Visualize the observed verifier-verdict counts on the 588-claim natural aggregate.
**Input:** `03_verdict_distribution.csv` (588-claim subset)
**Dataset:** 588-claim natural aggregate
**N:** 588
**Key values:** NOT_ENOUGH_INFORMATION=364, NO_EVIDENCE=198, ENTAILED=21, CONTRADICTED=5
**Interpretation:** Descriptive distribution of the verifier's own statistical judgments on real claims.
**What it does NOT establish:** That these counts are correctness labels — no independent ground truth exists for this data.
**Source:** STEP 6 (`claims_588_metrics.json`)

### Figure 04 — Correction Funnel

**Purpose:** Show correction pipeline stage counts for 5 distinct populations, never merged.
**Input:** `04_correction_funnel.csv`
**Dataset:** synthetic bare/labeled; natural targeted bare/labeled; natural cumulative
**N:** 30, 36, 5, 10, 56 (triggered per population)
**Key values:** Synthetic labeled shipped 26/36; natural targeted labeled shipped 1/10; natural cumulative shipped 1/56
**Interpretation:** Stage-by-stage funnel counts, each population reported independently.
**What it does NOT establish:** A single combined correction success rate — synthetic and natural populations are structurally different.
**Source:** `outputs/final_metrics.json`, `outputs/final_gpu_validation_metrics.json`, `outputs/labeled_correction_validation_gpu_metrics.json`

### Figure 05 — Correction Outcomes by Population

**Purpose:** Show shipped / failed / scope-violation breakdown per population.
**Input:** `05_correction_outcome.csv`
**Dataset:** Same 5 populations as Figure 04
**N:** Same as Figure 04
**Key values:** 0/5 → 1/10 (targeted, isolated by design); 1/56 = 1.8% (cumulative); 0 unsafe
**Interpretation:** Directional, isolated-by-design shift; too small a sample for statistical support.
**What it does NOT establish:** That 1/10 or 1/56 is a statistically validated success rate.
**Source:** Same as Figure 04

### Figure 06 — Safety: Unsafe Corrections Observed

**Purpose:** Show observed safety-mechanism counts across the tested correction history.
**Input:** `06_safety.csv`
**Dataset:** All tested correction attempts, project history
**N:** 122 (56 natural + 66 synthetic)
**Key values:** 0 unsafe corrections shipped; 18 scope-gate rejections; 0 sibling-regression rejections (Arm B); 37 re-verification-not-ENTAILED rejections
**Interpretation:** 0 unsafe corrections observed in the tested correction history.
**What it does NOT establish:** That unsafe corrections are impossible at any scale.
**Source:** `outputs/final_metrics.json`, `outputs/final_gpu_validation_metrics.json`

### Figure 07 — Confidence Distribution, 588-Claim Aggregate

**Purpose:** Show mean/median verifier confidence per verdict category.
**Input:** `07_confidence_distribution.csv`
**Dataset:** 588-claim natural aggregate, current production config, labeled framing
**N:** 21 (ENTAILED), 5 (CONTRADICTED), 364 (NEI), 390 (ALL evidence-matched)
**Key values:** Mean confidence 0.85-0.88 across verdicts; median 0.80-0.94
**Interpretation:** The verifier's own statistical certainty per verdict category.
**What it does NOT establish:** That higher confidence means the verdict is legally correct.
**Source:** STEP 6 (`claims_588_metrics.json`)

### Figure 08 — Ablation Evidence Strength by Grade

**Purpose:** Communicate evidence-strength grade (A-E) for all 8 ablation factors — grade, not effect size.
**Input:** `08_ablation_comparison.csv`
**Dataset:** 8 named ablation factors (see `ABLATION_SUMMARY.json`)
**N:** Varies per factor (209, 420, 30, 11, 3, 420, 5-10, N/A)
**Key values:** Evidence-v1 (A, p=3.01e-04); Premise framing (A, p=4.16e-23); Claim parser (B, p=3.12e-02); Confidence threshold (B); Atomic scope check (C); Narrow re-verification (C); Correction levers (C); Joint four-lever (E, not executed)
**Interpretation:** Grades A/B/C/E are visually distinct; no causal claim is made for Grade E.
**What it does NOT establish:** Causal isolation of the four-lever interaction — that experiment does not exist.
**Source:** STEP 7 (`ABLATION_SUMMARY.json`)

### Figure 09 — Runtime / Resource

**Purpose:** Show historical GPU runtime/VRAM alongside the one fresh CPU arm, clearly distinguished.
**Input:** `09_runtime_resource.csv`
**Dataset:** 4 historical GPU arms + 1 fresh CPU arm
**N:** 50, 50, 59, 59, 420
**Key values:** GPU arms 645s-2041s; fresh CPU arm (GOLD-01 labeled) 154s
**Interpretation:** Historical GPU results are clearly separated from the one fresh CPU result.
**What it does NOT establish:** That the GPU results were reproduced on this machine — explicitly annotated "NVIDIA GPU available: NO. Qwen generation/correction executed: NOT EXECUTED."
**Source:** `outputs/final_gpu_validation_metrics.json`, `outputs/final_metrics.json`, STEP 4 (`gold01_metrics.json`)

### Figure 10 — Cumulative Natural-Data Results

**Purpose:** Show observed evidence coverage across all 11 natural-data regimes side by side.
**Input:** `10_cumulative_natural_results.csv`
**Dataset:** 209-paired (2 arms) + 588-claim aggregate + 8 batch regimes
**N:** 29-588 per regime
**Key values:** Range 43.2%-70.3% across regimes
**Interpretation:** Each regime reported separately, per this project's own "never pooled" methodology.
**What it does NOT establish:** An accuracy measure, or a trend not present in the underlying CSV.
**Source:** STEP 6 (`paired_209_metrics.json`, `claims_588_metrics.json`, `batches_analysis.json`)

### Figure 11 — Synthetic vs. Natural Correction Shipping

**Purpose:** Explicitly show the non-equivalence between synthetic and natural correction shipping rates.
**Input:** `11_synthetic_vs_natural_transfer.csv`
**Dataset:** GOLD-02-derived synthetic correction attempts vs. natural cumulative
**N:** 36 (synthetic), 56 (natural)
**Key values:** 26/36 = 72.2% (synthetic) vs. 1/56 = 1.8% (natural)
**Interpretation:** Two disjoint populations with different base rates by construction.
**What it does NOT establish:** That either rate predicts or transfers to the other — explicitly annotated "Different evaluation populations; not directly equivalent."
**Source:** `outputs/final_metrics.json`

## Statistical significance shown, and its justification (Phase 12 cross-reference)

Every p-value displayed in Figures 02 and 08 was computed in STEP 6/7 from real paired
data using McNemar's test or an exact sign test, and is reproduced here unchanged — see
`FIGURE_CLAIM_AUDIT.md` for the explicit per-figure justification.
