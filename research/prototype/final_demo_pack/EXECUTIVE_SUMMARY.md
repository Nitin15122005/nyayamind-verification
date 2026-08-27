# Executive Summary — NyayaMind Statutory-Claim Verification (v0 Research Prototype)

Every number below traces to `research/prototype/final_demo_pack/metadata/computed_metrics.json`, itself built directly from the project's raw experiment artifacts under `research/prototype/outputs/` and `research/data/evidence/` (see `metadata/compute_metrics.py`). This is a **v0 research prototype**, not a production legal tool — see "What this is NOT" below before drawing conclusions.

## What the system does

Given a generated "Statutory Grounding" paragraph for an Indian court judgment summary, the pipeline runs seven stages:

```
NyayaRAG case text
  -> [1] Generate statutory-grounding paragraph (Qwen2.5-7B-Instruct, 4-bit, greedy)
  -> [2] Extract citation-bearing claims (deterministic regex, no LLM)
  -> [3] Match each claim to canonical evidence (exact key match, fuzzy fallback)
  -> [4] Verify each claim with NLI (DeBERTa-v3-base-mnli-fever-anli)
  -> [5] Selective correction of the first flagged claim (Mode C only, reuses the generation model)
  -> [6] Re-verify the corrected sentence
  -> [7] Programmatic scope-violation / safety gate (ship only if reverification == ENTAILED
         and no other claim's required text was disturbed)
```

Full architecture: `research/prototype/README.md`. Full config decision record: `FINAL_PRODUCTION_CONFIG.md`.

## Measured results (real data, not synthetic)

| Result | Value | Dataset | Source |
|---|---|---|---|
| Evidence coverage improvement, v0 -> v0+v1 | **63.2% -> 70.3%** (+7.1pp), McNemar chi2=13.07, **p ~ 0.0003**, 0 regressions | Paired arms, 50 held-out natural cases, 209 claims, same generation | `evidence_coverage_v0_v1`, `final_metrics_passthrough.section_B_natural_regimes` (final_A vs final_B) |
| Verifier detection improvement, bare -> labeled framing (controlled benchmark) | Macro F1 **0.749 -> 0.968**, ENTAILED recall 0.500 -> 1.000 | 420 curated real legal claim/evidence pairs (not synthetic corruption) | `controlled_benchmark_verifier` |
| Labeled framing detects more on natural data at scale | **8x** more ENTAILED-per-matched-claim (16/284 = 5.6% vs 2/454 = 0.4%) | 100 pooled natural cases (batch1+batch2), 2 disjoint sources | `final_metrics_passthrough.section_B_pooled_labeled_v0` vs `..._bare_v0` |
| Safety record | **0 unsafe shipments** across **122 total correction attempts** (56 natural + 66 synthetic) in this project's entire history | All historical correction attempts | `correction_safety_audit` |
| First genuine natural shipped correction | 1 case (`2003_760`/c3): replaced a sentence that stated IPC §302's *definition* with its actual *punishment* text, reverified ENTAILED at 0.995 confidence, 0 sibling regressions | Final production regime, targeted GPU validation, n=10 triggered | `final_metrics_passthrough.section_B_natural_regimes.final_labeled_v1_assertionspans_narrow_CORRECTION_GPU` |
| Parser/matcher defect rate | **0 confirmed defects** across 797 real claims spanning this project's entire natural-data history (2 candidates manually reviewed, both confirmed correct behavior) | All natural GPU experiments ever run | `final_metrics_passthrough.section_C_parser_retrieval` |

## Diagnostic-only results (do not extrapolate to production performance)

| Result | Value | Why it's diagnostic, not a production claim |
|---|---|---|
| Synthetic contradiction detection, bare -> labeled | Recall 35.6% -> 45.8% (overall), 47.7% -> 61.4% (evidence-matched) | Claims are deliberately corrupted (negated/altered), not naturally occurring — measures detection capability under a stress test, not real-world claim quality |
| Synthetic correction shipped rate | **72.2%** (26/36 triggered) under labeled framing, 0% under bare | Same synthetic-stress claims; this has **never transferred to natural data at anywhere near this magnitude** |
| Natural correction shipped rate (all historical regimes, pooled) | **1.8%** (1/56) | The real-world counterpart to the 72.2% synthetic number above |
| Natural correction shipped rate (final production regime only) | **10%** (1/10 triggered) | Best measured natural rate to date, but n=10 — a small sample, not yet a stable estimate |

The synthetic-vs-natural gap (72.2% vs 1.8%/10%) is the single most important number to present honestly: **synthetic stress-test performance does not predict natural-data correction-shipping performance in this system.**

## Metrics that require lawyer ground truth — MUST NOT be presented as established legal accuracy

**No lawyer or professional-legal ground-truth evaluation of verifier accuracy has ever been run in this project.** The only "gold"-adjacent artifact, `assumption_annotation.jsonl`, is **Claude-generated provisional labeling of 88 claims** — explicitly not lawyer-verified, and every report and the data file itself carry this disclaimer. Its agreement numbers (bare 52.6%, labeled 47.4% against these provisional labels — `assumption_gold_provisional`, `defensible: false`) describe **agreement between two machine-produced label sets**, nothing more, and the direction (labeled framing showing *worse* agreement here) actively **contradicts** the labeled-framing improvements measured elsewhere in this document — this is reported honestly as a genuine counter-signal, not suppressed (see `FINAL_PRODUCTION_CONFIG.md` §1 and `reports/verifier_analysis.md`).

Any verifier verdict (ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION) reported anywhere in this pack is a small public NLI model's statistical judgment against a third-party-sourced (IndianKanoon, not official India Code) evidence corpus — **never legal truth, never a lawyer's determination.**

## What this is NOT

- **Not lawyer-validated.** No professional legal review of verifier accuracy exists.
- **Not built on the official government law text.** India Code (`indiacode.nic.in`) returned HTTP 403 on every access attempt across this project's history; the evidence corpus is entirely third-party-sourced from IndianKanoon.org.
- **Not current law for IPC/CrPC-heavy citations.** The corpus reflects pre-2024-07-01 text (before the BNS/BNSS national supersession).
- **Not a production system.** Every threshold and generation parameter is a v0 design default (`research/prototype/config/prototype.yaml`), tuned only where explicitly noted in `FINAL_PRODUCTION_CONFIG.md`.
- **NO_EVIDENCE never means "legally unsupported."** It means only "not in our ~136-record corpus" — see `reports/retrieval_analysis.md`.

Full limitations statement: `research/prototype/outputs/final_limitations_and_future_scope.md`.
