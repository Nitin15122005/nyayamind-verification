# Models and Configurations

Canonical source: `research/prototype/config/prototype.yaml` (every value has a dated,
evidence-cited comment directly in the file). This document summarizes and points there — the
YAML file is authoritative if this document and it ever disagree.

## Models

| Role | Model | Precision | Notes |
|---|---|---|---|
| Generation | `Qwen/Qwen2.5-7B-Instruct` | 4-bit NF4 (bitsandbytes, double quant, bfloat16 compute) | greedy (`do_sample=False`), `max_new_tokens=200` |
| Correction | `Qwen/Qwen2.5-7B-Instruct` | same as generation | reuses the already-loaded generation model instance, not a second model; `max_new_tokens=220` (legacy) / `60` (assertion-aware fragment-only) |
| Verification (NLI) | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | fp16 | `confidence_threshold=0.70`; label order read from the model's own `config.id2label`, never hardcoded |
| Retrieval (evaluated, not selected) | BM25 (`Bm25ActIndex`), sentence-transformer embeddings (`EmbeddingActIndex`) | n/a | `research/prototype/src/retrieval_signals.py` |
| Baseline reference (different task, out of scope for comparison) | `meta-llama/Llama-2-7b-chat-hf` + `L-NLProc/LegalSeg_RhetoricLLaMA` LoRA | — | `research/baseline/` |

**Not hash-pinned**: neither Qwen nor DeBERTa has a `revision=` pin — both are pulled at
whatever HF Hub revision is current on first load. Not a problem observed in practice, but not
guaranteed byte-identical across time.

## Current production configuration (`config/prototype.yaml`)

| Setting | Value | Since | Decision record |
|---|---|---|---|
| `verification.premise_framing` | `labeled` | 2026-08-27 | `FINAL_PRODUCTION_CONFIG.md` §1 |
| `use_evidence_v1` | `true` (136-record pool) | 2026-08-27 | §2 |
| `correction.atomic_scope_check` | `"assertion_spans"` | 2026-08-27 | §3 |
| `correction.narrow_reverification_hypothesis` | `true` | 2026-08-27 | §4 |
| `verification.narrow_primary_hypothesis` | `true` | 2026-09-09 | §5 |
| `verification.confidence_threshold` | `0.70` (unchanged) | — | §6 |
| `evidence_matching.fuzzy_method` | `"jaccard"` | always | — |

## EVALUATED, not adopted (both implemented, both off)

| Setting | Value | Decision record |
|---|---|---|
| `verification.assertion_span_primary_hypothesis` | `false` | `FINAL_PRODUCTION_CONFIG.md` §5a |
| `correction.assertion_aware` | `false` | `FINAL_PRODUCTION_CONFIG.md` §5b |

## REJECTED for production (implemented, actively not selected for a safety reason)

| Setting | Rejected value(s) | Why |
|---|---|---|
| `evidence_matching.fuzzy_method` | `"bm25"`, `"embedding"` | Materially less safe than Jaccard on adversarial near-miss Act names — see `results_phase3/tables/detailed_metrics/retrieval_metrics.csv` |

## HISTORICAL (pre-2026-08-27 baseline values, still reproducible)

To reproduce any pre-2026-08-27 committed result byte-for-byte, set:
`use_evidence_v1: false`, `premise_framing: "bare"`, `atomic_scope_check: false`,
`narrow_reverification_hypothesis: false`, `narrow_primary_hypothesis: false` (this key did
not exist before 2026-09-09 — simply absent/inert for older configs). Every historical output
in `outputs/` was produced under exactly this combination; pinned by
`tests/test_premise_framing_production.py::test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`.

## Deterministic parameters

| | Value |
|---|---|
| Global seed | `42` |
| Generation | greedy, `max_new_tokens=200` |
| Correction (legacy) | greedy, `max_new_tokens=220` |
| Correction (assertion-aware) | greedy, `max_new_tokens=60` |

Full detail on every setting: `research/prototype/REPRODUCIBILITY.md` §5,
`config/prototype.yaml`'s own inline comments (the single most authoritative source for
"why this value").
