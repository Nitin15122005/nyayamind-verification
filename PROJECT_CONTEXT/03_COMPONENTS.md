# Components

Detailed per-component comparison table (Baseline/Modified/Purpose/Observed Effect/Evidence/
Production Status/Limitation): `research/prototype/results_phase3/tables/component_results/component_comparison.md`.
This file gives the same components in narrative form with implementation locations.

## Generator

- **Purpose**: generates the Statutory Grounding paragraph from case facts.
- **Location**: `research/prototype/src/generator.py` (`StatuteGroundingGenerator`).
- **Model**: `Qwen/Qwen2.5-7B-Instruct`, 4-bit NF4, greedy decoding, `max_new_tokens=200`.
- **Inputs**: `case_text`. **Outputs**: `generated_field.text` + reproducibility metadata.
- **Status**: PRODUCTION. Identical in baseline and modified systems — isolates every other
  lever.
- **Limitation**: no CPU fallback by design; not hash-pinned to a specific HF revision.

## Claim parser

- **Purpose**: extracts one `Claim` per citation-bearing sentence; narrows each claim's own
  verifiable content via `assertion_text`/`assertion_spans` when a safe split pattern exists.
- **Location**: `research/prototype/src/claim_parser.py`.
- **Model**: none — deterministic regex, no LLM.
- **Inputs**: generated field text. **Outputs**: `list[Claim]`.
- **Status**: PRODUCTION (includes the Art./Arts. abbreviation fix, commit `c250a0e`).
- **Experiments**: n=30 reparse (commit `223eb9d` + Art./Arts. fix) — 6/30 documents improved,
  0 worsened, sign test p=0.03. See `research/prototype/results_phase3/tables/detailed_metrics/parser_metrics.csv`.
- **Limitation**: two confirmed bundled-sentence shapes never narrow — a bare "Sections X and
  Y" listing with no per-citation clause, and a "respectively" pattern followed by a trailing
  " while " clause (the while-split blocks the respectively-split on the same sentence).
  Confirmed via the n=10 assertion-aware correction replay (documents `1953_10`, `1955_16`).

## Evidence retrieval / evidence pool

- **Purpose**: matches a claim's citation to canonical statute text.
- **Location**: `research/prototype/src/evidence_matcher.py` (production), `src/retrieval_signals.py`
  (evaluated alternatives).
- **Model**: none for exact/Jaccard (lexical); BM25 (`Bm25ActIndex`) and sentence-transformer
  embeddings (`EmbeddingActIndex`) are implemented but not selected.
- **Inputs**: `ExtractedCitation` + the usable evidence pool. **Outputs**: `evidence_text` or
  `NO_EVIDENCE`.
- **Status**: PRODUCTION (`evidence_matching.fuzzy_method: jaccard`, `use_evidence_v1: true`,
  136-record pool). BM25/embedding: EVALUATED, REJECTED.
- **Experiments**: evidence coverage 63.2%→70.3% (n=209, McNemar p=0.0003); retrieval safety
  comparison (n=30 pre-registered adversarial cases) — Jaccard 9/9 correct-reject vs BM25 3/9,
  embedding 2/9. See `research/prototype/results_phase3/tables/detailed_metrics/retrieval_metrics.csv`.
- **Limitation**: bounded by a 136-record evidence pool; a genuinely absent provision correctly
  returns NO_EVIDENCE, not a retrieval bug.

## Premise framing

- **Purpose**: formats the NLI premise handed to the verifier.
- **Location**: `research/prototype/src/verifier.py` (`format_premise`, `PREMISE_FRAMING_BARE`/`_LABELED`).
- **Status**: PRODUCTION (`labeled`).
- **Experiments**: controlled benchmark (GOLD-01, n=420) macro F1 0.749→0.968.

## NLI verifier

- **Purpose**: classifies ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION for a claim against its
  evidence.
- **Location**: `research/prototype/src/verifier.py` (`NLIVerifier`).
- **Model**: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, fp16, `confidence_threshold=0.70`.
- **Status**: PRODUCTION, with `narrow_primary_hypothesis=true`.
  `assertion_span_primary_hypothesis`: EXPERIMENTAL, off.
- **Experiments**: see `04_EXPERIMENTS_AND_RESULTS.md`.
- **Limitation**: no formal negation-understanding guarantee (a documented exclusion rule
  exists instead); no legal-correctness oracle.

## Assertion spans

- **Purpose**: a claim's own narrower, verbatim, non-fabricated content fragment(s) within a
  bundled sentence — `assertion_text` (single fragment) for semicolon/while/keyword-boundary/
  parenthetical splits; `assertion_spans` (list, `[bare_number_span, description_item]`) for
  the "respectively" pattern.
- **Location**: `research/prototype/src/claim_parser.py` (`_assign_assertion_texts`,
  `_assign_respectively_spans`).
- **Status**: PRODUCTION as a data structure (always populated); consumed by
  `narrow_primary_hypothesis` (production), `assertion_span_primary_hypothesis` (experimental),
  `atomic_scope_check="assertion_spans"` (production), and assertion-aware correction
  (experimental).

## Selective correction (legacy)

- **Purpose**: rewrites a flagged sentence via the generator model, ships only if every safety
  gate passes.
- **Location**: `research/prototype/src/corrector.py` (`SelectiveCorrector.correct`),
  `research/prototype/src/pipeline.py` (`apply_selective_correction`).
- **Status**: PRODUCTION — this is what Mode C uses by default.
- **Experiments**: cumulative natural history 1/56 (1.8%) shipped, 0 unsafe.
- **Limitation**: dominant failure is generation-quality (no-op/inadequate edits), not a
  pipeline defect.

## Selective correction (assertion-aware, NEW)

- **Purpose**: rewrites ONLY the flagged claim's own `assertion_spans[-1]` content fragment,
  splices it back via deterministic string replacement — everything outside the target span is
  byte-identical to the original by construction.
- **Location**: `research/prototype/src/corrector.py` (`correct_assertion_span`),
  `research/prototype/src/pipeline.py` (`apply_selective_correction_assertion_aware`,
  `_correction_target_spans`, `_splice_assertion_correction`).
- **Status**: EXPERIMENTAL (`correction.assertion_aware: false`).
- **Experiments**: n=10 paired real replay against the exact 5 documents that triggered legacy
  correction in the n=62 batch — 0/10 shipped, identical to legacy's 0/10 on the same cases.
  Architecture verified against real parser `assertion_spans` output (0 mismatches on replay).
  See `research/prototype/results_phase3/FINAL_RESULTS.md` §9.
- **Limitation**: no real natural-data multi-span (`assertion_spans` length > 1)
  correction-triggering case has been observed yet; the multi-span path is verified via
  deterministic tests and a real-corpus-derived fixture only.

## Safety gates

- **Purpose**: prevent shipping a correction that alters unflagged content, injects a new
  citation, or leaves an independently-wrong sibling claim standing.
- **Location**: `research/prototype/src/pipeline.py` (`_scope_violation`,
  `_reverify_sibling_regressions`, the ordinal-integrity and unauthorized-addition checks
  inline in `apply_selective_correction*`).
- **Status**: PRODUCTION. New (experimental-path-only) checks: structural-span preservation,
  span validity.
- **Experiments**: 0/132 unsafe shipments across every correction attempt in project history
  (122 historical + 10 new).

## Final answer assembly

- **Purpose**: decides the final `generated_field` text returned by the pipeline.
- **Location**: `research/prototype/src/pipeline.py::run_case()`.
- **Status**: PRODUCTION. Every rejection path has its own labeled `final_field.source` value,
  including the two new experimental-path statuses (`correction_structural_span_lost`,
  `correction_span_invalid`).
