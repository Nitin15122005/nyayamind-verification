# Input Manifest

Reviewer-friendly inventory of every dataset used, or documented as deliberately
excluded, by this testing workspace's input layer. IDs match `../MANIFEST.md` where the
same artifact appears there (that file also tracks non-input artifacts such as ablation
replays and config files; this one is scoped to genuine pipeline **inputs**).

All record counts, hashes, and classifications below were independently verified in
STEP 0/1/2 (line counts, JSON parsing, live loader runs, direct field inspection) — not
copied from prior documentation without checking.

| ID | Dataset | Source | Records | Format | Classification | Independent labels? | Pipeline stage | Testing role |
|---|---|---|---|---|---|---|---|---|
| IN-01 | v0 evidence corpus | `research/data/evidence/canonical_statutes.jsonl`+`evidence_audit.jsonl` | 63 raw / 59 usable | JSONL | N/A (input corpus) | N/A | Evidence retrieval | Referenced, not copied — see `evidence/SOURCE.md` |
| IN-02 | v1 evidence supplement | `research/data/evidence/canonical_statutes_v1.jsonl`+`evidence_audit_v1.jsonl` | 82+82 | JSONL | N/A (input corpus) | N/A | Evidence retrieval | Referenced, not copied |
| IN-03 | Merged production evidence pool | derived (v0+v1) | 136 (live-verified) | N/A (loader output) | N/A (input corpus) | N/A | Evidence retrieval | Reproducible via `load_usable_evidence_from_config` |
| GOLD-01 | Controlled NLI benchmark | `expected_outputs/controlled_benchmark_gold/` (copied fixture) | 420 | JSONL | **GOLD** | **Yes — deterministic construction rule** | NLI verification | Copied, hash-verified; see `gold/README.md` |
| GOLD-02 | Synthetic stress set | `expected_outputs/synthetic_stress_gold/` (copied fixture) | 59 | JSONL | **GOLD** | **Yes — deterministic construction** (contradiction only) | NLI verification, correction | Copied, hash-verified; see `gold/README.md` |
| MET-01 | Natural 588-claim aggregate | derived (recomputed from 133 generated texts across `outputs/`) | 588 (re-derived) | derived, not a file | METRIC-ONLY | No | Claim parsing → evidence retrieval | Referenced, recomputable, not copied; see `metric_only/README.md` |
| MET-02 | 209-claim paired evaluation | `outputs/final_gpu_validation_A.jsonl`/`_B.jsonl` | 209/arm (2 arms) | JSONL | METRIC-ONLY | No — **not ground truth** | Full pipeline (paired comparison) | Referenced, not copied |
| NAT-01 | Natural batch n=30 | `outputs/run_{A,B,C}_n30.jsonl` | 30 | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| NAT-02 | Natural batch1 (n=50) | `outputs/natural_candidates_50_gpu_*.jsonl` | 50 | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| NAT-03 | Natural batch2 (n=50) | `outputs/natural_candidates_batch2_gpu_*.jsonl` | 50 | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| NAT-04 | Final validation batch (n=50) | = MET-02 | 50 cases | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| CASE-01 | NyayaRAG case source | `research/data/nyayarag/CaseText_Statutes/*.json` | 4,930 + 4,962 | JSON (array) | N/A (input corpus) | N/A | Generation (pre-stage 1) | Referenced only — 27MB each, not copied; GPU-blocked on this machine |
| ADV-01 | Adversarial citation cases | `tests/test_adversarial_citations.py` (inline) | 15 test functions | Python fixtures | **BEHAVIOR** | Yes — exact code-behavior assertion | Claim parsing, evidence retrieval | Referenced, not duplicated; see `behavior/README.md` |
| ADV-02 | Final-pass adversarial cases | `tests/test_final_pass_adversarial.py` (inline) | 10 test functions | Python fixtures | **BEHAVIOR** | Yes | Claim parsing | Referenced, not duplicated |
| ADV-03 | Respectively-claims structural tests | `tests/test_respectively_claims.py` (inline) | 16 test functions | Python fixtures | **BEHAVIOR** | Yes | Claim parsing | Referenced, not duplicated |
| ADV-04 | Claim-parser bugfix regressions | `tests/test_claim_parser_bugfixes.py` (inline, real sentences) | 20 test functions | Python fixtures | **BEHAVIOR** | Yes | Claim parsing | Referenced, not duplicated |
| COR-01 | Correction/sibling-safety detail (final_gpu_validation) | `outputs/final_gpu_validation_corrections_detail.jsonl` | 10 | JSONL | METRIC-ONLY | No | Correction, scope/safety | Referenced, not copied |
| COR-02 | Correction/sibling-safety detail (labeled validation) | `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` | 10 | JSONL | METRIC-ONLY | No | Correction, scope/safety | Referenced, not copied |
| COR-03 | Correction/sibling-safety detail (batch1) | `outputs/natural_candidates_50_gpu_corrections_detail.jsonl` | 21 | JSONL | METRIC-ONLY | No | Correction, scope/safety | Referenced, not copied |
| PROV-01 | Provisional annotations | `outputs/gold_annotation.jsonl`, `lawyer_annotation.jsonl`, `assumption_annotation.jsonl` | 88+88+88 | JSONL | **PROVISIONAL** | Self-tagged NOT independently verified | N/A (post-hoc annotation, not a pipeline stage) | Referenced, never copied into `gold/`; see `provisional/README.md` |
| HIST-01 | final_demo_pack example compilations | `final_demo_pack/examples/{candidate_pool,cases}.json` | 8+8 | JSON | HISTORICAL-ONLY | N/A | N/A (presentation layer) | Referenced only; see `historical_reference/README.md` |
| HIST-02 | final_comparison config/tables | `final_comparison/comparison_config.json`, `tables/*.csv` | N/A | JSON/CSV | HISTORICAL-ONLY | N/A | N/A (presentation layer) | Referenced only |

## 1. TRUE GOLD INPUTS
GOLD-01 (n=420), GOLD-02 (n=59). Nothing else. See `gold/README.md`.

## 2. BEHAVIOR INPUTS
ADV-01 through ADV-04 (all inline test fixtures, no standalone data files). See
`behavior/README.md`.

## 3. METRIC-ONLY INPUTS
MET-01, MET-02, NAT-01 through NAT-04, COR-01 through COR-03. See `metric_only/README.md`.

## 4. PROVISIONAL INPUTS
PROV-01. See `provisional/README.md`.

## 5. HISTORICAL-ONLY ARTIFACTS
HIST-01, HIST-02 (and, more broadly, everything in `research/prototype/outputs/`'s
non-selected-batch files — status reports, ablation replays, etc. — which are inputs to
*ablation/evaluation reproduction*, not to a fresh pipeline run; see `../ablation/README.md`
and `../evaluation/README.md`). See `historical_reference/README.md`.

## Not classified above: evidence corpora and case sources (IN-01/02/03, CASE-01)

These are deliberately **not** forced into one of the four GOLD/BEHAVIOR/METRIC-ONLY/
PROVISIONAL buckets — they are retrieval/generation input corpora, not labeled test sets.
Forcing a classification onto them would be inaccurate: `audit_verdict` in the evidence
corpus labels the evidence record's own sourcing trustworthiness, not any claim's
entailment status, and NyayaRAG case text carries no verdict at all until it passes
through the (GPU-blocked, on this machine) generation stage. See `evidence/SOURCE.md` and
`cases/SOURCE.md`.

---

## Why these are inputs

An **input**, in this workspace, is an artifact intentionally fed into a component or the
full pipeline for a test or evaluation — something a function genuinely reads as an
argument: a case's `case_text`, an evidence pool passed to `match_evidence`, a
benchmark's `evidence_text`/`hypothesis` passed to `verify()`, or a hand-constructed
citation string passed to `extract_citation`. A **historical output** is not automatically
an input simply because it is stored as JSON or JSONL — most of `research/prototype/outputs/`
is the *result* of a previous run, sitting downstream of the pipeline, and only becomes a
legitimate input again in the narrow, explicit sense of "reused already-generated text to
avoid a redundant GPU call" (the pattern this project's own CPU-only scripts use
throughout, e.g. `compare_final_validation_labeled_cpu.py` re-verifying `final_gpu_validation_B.jsonl`'s
existing claims under a different framing). Every row above marked METRIC-ONLY or
HISTORICAL-ONLY is exactly that kind of already-downstream artifact; only GOLD-01,
GOLD-02, the evidence corpora, the case sources, and the inline BEHAVIOR fixtures are
genuinely upstream, first-fed-into-the-system inputs in the strict sense.
