# NOT_GENERATED_REGISTER — visuals deliberately withheld

Each entry below was considered for this package and is recorded here rather than
produced from data that does not support it.

| Requested / expected visual | Status | Why |
|---|---|---|
| Accuracy / precision / recall / F1 on natural NyayaRAG data | **NOT GENERATED — insufficient/unsupported source data** | No natural-data record in this project has an independent correctness label. `evaluation/metrics/METRIC_DEFINITIONS.md` defines every legitimate natural-data metric as descriptive or paired-comparative for exactly this reason. Producing an accuracy figure would require inventing labels. |
| Confusion matrix on natural data | **NOT GENERATED — insufficient/unsupported source data** | A confusion matrix needs a true label per item. Only GOLD-01 and GOLD-02 have one, and both are already plotted (F04, F05). |
| Quantitative comparison against the RhetoricLLaMA / LegalSeg baseline | **NOT GENERATED — not a comparable measurement** | Different task (sentence-level rhetorical-role classification), different dataset, different output space; only a one-row smoke test was ever executed (`research/baseline/BASELINE.md`), and `comparison_config.json` marks it `explicitly_out_of_scope`. The relationship is documented structurally instead, in diagram D14. |
| Joint four-lever ablation (all four production levers varied from one common baseline) | **NOT GENERATED — the experiment does not exist** | `evaluation/ablation/ABLATION_SUMMARY.json` classifies this factor NOT_ISOLABLE / NOT_EXECUTED. It is shown as Grade E in F16 and T03 rather than being estimated. |
| Verifier agreement against lawyer ground truth | **NOT GENERATED — no such data exists** | `REPOSITORY_MANIFEST.md` §6 records that `lawyer_annotation.jsonl` holds provisional, Claude-generated labels, not a lawyer's answers. Every agreement number computed against it (including the counter-signal in `final_metrics.json` section_E) is PROVISIONAL and is deliberately excluded from this package's figures. |
| A single pooled correction success rate across synthetic and natural populations | **NOT GENERATED — populations are not comparable** | Synthetic stress claims are contradictory by construction; natural claims have no comparable base rate. F19 exists specifically to show this gap rather than hide it. |
| Confidence intervals on the correction shipping rates | **NOT GENERATED — n too small to be meaningful** | 1/56 cumulative and 1/10 targeted. The project's own ablation record reports 'none performed -- sample too small for a meaningful test'; this package does not invent one. |
| Fresh GPU re-execution of any experiment for this package | **NOT PERFORMED — out of scope by instruction** | This package runs no experiments and no GPU work. The GPU rows it displays are the committed historical values plus the evaluation workspace's own STEP 10 / 10B reproductions, each labelled as such (F17, F22, T06a). |
| Per-claim evidence-coverage trend over time | **NOT GENERATED — the regimes are not a time series** | The eleven natural-data regimes in F18 differ in case selection and configuration. Plotting them as a trend would imply a comparison the sampling does not support. |
| Cumulative correction rate (1/56) as a reproducible experiment | **SHOWN, BUT MARKED HISTORICAL-ONLY** | `evaluation/metrics/GPU_REPRODUCTION_CROSSCHECK.md` classifies it PROTOCOL INSUFFICIENT: the pooled 56-attempt total has no recoverable single reproduction protocol. It appears in F13 / F14 / T05a with that status printed, and is never presented as a rate estimate. |

## What this means for the presentation

The strongest honest statement this package supports is:

> Against its own pre-2026-08-27 baseline, the modified NyayaMind (2026-08-27 production) configuration measurably improves **verifier benchmark performance on labelled GOLD data** (macro F1 0.749 → 0.968, n = 420, McNemar p = 4.16e-23) and **observed evidence-retrieval coverage on real natural claims** (63.2% → 70.3%, n = 209, McNemar p = 3.01e-04, zero regressions), while shipping **0 unsafe corrections in 122 tested correction attempts**.

It does **not** support any statement that the modified system is more legally accurate, because no legal ground truth exists anywhere in this project.

