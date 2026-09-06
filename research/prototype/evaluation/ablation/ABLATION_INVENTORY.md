# Ablation Inventory (STEP 7)

Every already-existing comparison relevant to the 6 requested factor groups, located by
searching `research/prototype/`, `evaluation/`, `final_comparison/`, `final_demo_pack/`,
`tests/`, and `src/`. For each, verified from the actual artifact — not assumed —
whether the two configurations compared were genuinely executed under otherwise-identical
conditions.

| Factor | Baseline | Variant | Dataset | N | Fresh/Historical | Isolated? | Metric |
|---|---|---|---|---|---|---|---|
| A. Evidence v0 vs v0+v1 | `use_evidence_v1=false` (59 records) | `use_evidence_v1=true` (136 records) | 209-claim paired natural set (`final_gpu_validation_{A,B}.jsonl`) | 209 | **FRESH REPRODUCTION** (STEP 6; re-verified this step) | **Yes** — evidence matching depends only on the pool + citation, not on scope-check/narrow-reverify | evidence coverage |
| B. Premise framing | `premise_framing=bare` | `premise_framing=labeled` | GOLD-01 controlled benchmark | 420 | **FRESH** (STEP 4; McNemar/sign-test newly computed this step) | **Yes** — same 420 items, same model/threshold/device, only framing differs | macro F1, accuracy |
| B'. Premise framing (natural, secondary) | bare | labeled | 147 evidence-matched claims from final_validation Arm B | 147 | HISTORICAL (`outputs/final_validation_bare_vs_labeled_cpu_metrics.json`) | Yes, on this specific 147-claim subset | ENTAILED count |
| C. Atomic scope check | legacy (full-sentence) | `assertion_spans` | 11 real historical scope-violation attempts | 11 | **FRESH REPRODUCTION** (re-executed this step via real `pipeline._scope_violation`) | Yes, for the scope-gate decision only — NOT for downstream shipping | n_unblocked |
| D. Narrow re-verification | `narrow_reverification_hypothesis=false` | `=true` | 3 real `correction_failed` cases, final validation batch | 3 | HISTORICAL narrative (`FINAL_PRODUCTION_CONFIG.md` §4) | Not independently re-verified in this step; evaluated jointly with other config values in the source | verdict-decisiveness shift |
| E. Confidence threshold | N/A (sweep) | 0.50–0.95, 10 points | GOLD-01 controlled benchmark (stored softmax, no re-inference) | 420 | **FRESH** (recomputed this step from stored sweep data) | Yes — pure replay of the decision rule, no model involved | macro F1 vs threshold |
| F. Claim parser fix (commit `223eb9d`) | pre-fix parser | post-fix parser | Same 30 generated texts, re-parsed | 30 | HISTORICAL REPRODUCTION / NOT FRESH (sign test freshly recomputed from raw data this step) | Yes — same texts/evidence pool, only parser code differs | per-case evidence-matched count |
| G. Correction levers (framing, isolated) | bare, all else fixed | labeled, all else fixed | Final validation batch, targeted correction validation | 5 vs 10 triggered | HISTORICAL, GPU-dependent (NOT re-executed — no GPU on this machine) | Yes, by the source experiment's own design (only framing varies) | corrections shipped |
| H. Joint four-lever isolation | — | — | — | — | **NOT_EXECUTED** | No such experiment exists | — |

## What was verified, not assumed

- **Evidence v0-vs-v1 (A)**: confirmed via the 209-claim set's own `reproducibility`
  block in each arm's file — Arm A genuinely used `use_evidence_v1=false`, Arm B
  `=true`, with identical `generation_model`, `seed`, and `verification_model`. Only the
  evidence pool (and, for the originally-stored verdicts, other config values) differ.
- **Premise framing (B)**: confirmed both STEP 4 runs used identical `model_id`,
  `confidence_threshold`, `max_sequence_length`, and the identical 420-item file — only
  the `--premise-framing`-equivalent argument differed.
- **Atomic scope check (C)**: confirmed by re-executing `pipeline._scope_violation`
  directly on the same historical `original_field_text`/`regenerated_text` pairs under
  both modes in a single script run — genuinely isolates the check-mode logic.
- **Correction levers (G)**: confirmed via `labeled_correction_validation_gpu_metrics.json`'s
  own `comparison_bare_arm_b_original` field, which explicitly states "same 50 cases,
  same improved config except framing" — this is a real, verified isolation, not assumed
  from the fact that the numbers differ.
- **Narrow re-verification (D)**: **not independently re-verified this step** — the
  source document (`FINAL_PRODUCTION_CONFIG.md` §4) evaluates this lever already paired
  with the other three levers being on, so its isolation from those other levers is not
  established by the available evidence. Reported as historical narrative, not upgraded.
- **Joint four-lever (H)**: confirmed absent by direct inspection — no script, output
  file, or report anywhere in `research/prototype/outputs/`, `final_comparison/`, or
  `final_demo_pack/` varies all four levers one-at-a-time from one common baseline in a
  single fresh run.

Full machine-readable detail: `ABLATION_SUMMARY.json`, `ABLATION_MATRIX.csv`.
