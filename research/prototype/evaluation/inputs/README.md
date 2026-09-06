# Inputs Inventory

Everything the production pipeline consumes *before* it produces a result. Nothing in
this directory is generated text, a verdict, or a correction — those are outputs (see
`../expected_outputs/README.md`, `../actual_outputs/README.md`).

All counts below were independently verified (line counts / JSON parsing / a live
evidence-loader run), not copied from documentation. Hashes are SHA-256 over the exact
committed file bytes, computed 2026-09-05.

**PASS 1 cleanup note (2026-09-05)**: this file consolidates what were originally 11
separate files across 8 directories (`INPUT_MANIFEST.md`, `INPUT_SUMMARY.md`,
`INPUT_TO_COMPONENT_MAP.md`, and 7 classification/source subdirectories — `gold/`,
`behavior/`, `historical_reference/`, `metric_only/`, `provisional/`, `cases/`,
`evidence/` — each of which held only a single README.md/SOURCE.md and no data files).
No content was removed; every section below is the full text of one of those files,
retitled as a section. See `../archive/cleanup_history/CLEANUP_PASS1_MANIFEST.md` for the exact move record.

**Column legend** (Master Input Reference table below)
- **Workspace treatment**: **A**=reference source in place (never copied), **B**=copy as
  an immutable fixture into this workspace, **C**=regenerate later (not yet done).
- **Expected-vs-Actual legitimate?**: whether this dataset's own labels are an
  independently-derived gold standard suitable for `comparisons/expected_vs_actual/`.
  "No — metric only" means it can still be evaluated, just not against a known-correct
  answer (see `../evaluation/`'s metric-based reports, e.g. `NATURAL_DATA_REPORT.md`,
  `EVIDENCE_STRENGTH_MATRIX.md`).

---

## Master Input Reference

### 1. v0 evidence corpus

| | |
|---|---|
| Source path | `research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl` |
| Frozen? | Yes |
| Record count | 63 raw / **59 usable** (`VERIFIED_EXACT`+`VERIFIED_CONTENT` only) |
| One record represents | One statute/citation key's independently-sourced canonical text, plus a separate audit verdict record keyed the same way |
| Schema (`canonical_statutes.jsonl`) | `dataset_citation_key, act, provision_type, provision_number, subsection, canonical_text, source_name, source_url, authority_level, retrieval_date, historical_status, text_provenance, confidence, citation_frequency_in_top100_files, nyayarag_dataset_text_deterministic_category, nyayarag_dataset_text_raw` |
| Schema (`evidence_audit.jsonl`) | `dataset_citation_key, act, provision_type, provision_number, audit_verdict, audit_method, audit_note, audit_date, source_url, stored_historical_status` |
| Format | JSONL, one record per line |
| Nature | Curated, third-party-sourced (IndianKanoon.org — India Code returned HTTP 403 on every attempt) |
| Labels exist? | Yes — `audit_verdict` (VERIFIED_EXACT / VERIFIED_CONTENT / SOURCE_ONLY / INVALID / UNRESOLVED) |
| Label provenance | Independent human-style re-fetch-and-compare audit, no LLM adjudication |
| Legitimate for expected-vs-actual? | No — this is an **input** corpus, not a verifier-output label set. (The audit_verdict labels the evidence record's own trustworthiness, not a claim's entailment status.) |
| Suitable for metric evaluation? | N/A (input) |
| Reproducible? | Files are committed and static; the *build* is not re-runnable (see item 3) |
| GPU required? | No |
| Workspace treatment | **A** — reference in place |
| SHA-256 | `canonical_statutes.jsonl`: `cdef4eee5ed4d7a7e300d7b2907f2c8a1eca23653d76f92edd116b095b22c44a`; `evidence_audit.jsonl`: `fef822cf8a4afe17280793771f9a2854e3fda66fb31d016d0c1cb383a6c97353` |
| Notes | See `research/data/evidence/README.md` for the full audit methodology and the 4 excluded/flagged records. |

### 2. v1 evidence supplement

| | |
|---|---|
| Source path | `research/data/evidence/canonical_statutes_v1.jsonl` + `evidence_audit_v1.jsonl` |
| Frozen? | Yes |
| Record count | 82 + 82 (3 correct existing v0 records on merge, 79 genuinely new) |
| One record represents | Same shape as v0, plus a `v1_supersedes_v0_record` flag on the 3 correction records |
| Format | JSONL |
| Nature | Curated, third-party-sourced, additive supplement (never merged into v0 files themselves) |
| Labels exist? | Yes — same `audit_verdict` scheme; v1's audit is narrower in coverage than v0's (mechanical rule + 50% independently re-fetched per the 2026-08-27 addendum, vs. v0's 100%) |
| Legitimate for expected-vs-actual? | No — input corpus |
| Reproducible? | Files are committed and static; the *build script* (`scripts/build_evidence_v1.py`) is **not** re-runnable — it reads a hardcoded, no-longer-existing scratch path |
| GPU required? | No |
| Workspace treatment | **A** — reference in place |
| SHA-256 | `canonical_statutes_v1.jsonl`: `2330919cc0bc3091ff9d6b986b317707405bd6b3902d353d299d5c7d36df7e63`; `evidence_audit_v1.jsonl`: `0e73715e511df48fd2a4b9da251bb701d481256db38f0fdef26ff2778cae4d4a` |
| Notes | See `research/data/evidence/README_v1.md`, including the 2026-08-27 independent-audit addendum (2 defects found and fixed in place, net usable count 137→136). |

### 3. Merged production evidence pool

| | |
|---|---|
| Source | v0 (59 usable) + v1 (79 new usable + 3 corrections − 1 downgrade), merged at load time |
| Frozen? | Yes (the two source file pairs above are frozen; the merge is a pure function of them) |
| Record count | **136**, confirmed live: `src.data_loader.load_usable_evidence_from_config(cfg, '.')` with `use_evidence_v1: true` (Step 0 audit re-ran this loader directly and got 136) |
| Produced by | `src/data_loader.py::load_usable_evidence_from_config`, controlled by `config/prototype.yaml`'s `use_evidence_v1: true` |
| Legitimate for expected-vs-actual? | No — input corpus, not a label set |
| Reproducible? | Yes, fully — CPU-only, no model |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; not a physical file, a config+loader combination |
| Notes | This is the pool every current-production evaluation should use. Historical outputs committed before 2026-08-27 used the 59-record v0-only pool — do not conflate the two when comparing old and new results. |

### 4. Controlled NLI benchmark (420 examples) — GOLD-01

| | |
|---|---|
| Source path | `research/prototype/outputs/controlled_verifier_benchmark.jsonl` |
| Frozen? | Yes |
| Record count | **420, confirmed** (`wc -l`) |
| One record represents | One (premise-source, hypothesis, condition) triple built mechanically from one of the 59 v0 usable evidence records, labeled with its construction-rule-assigned expected NLI verdict |
| Schema | `benchmark_id, benchmark_version, benchmark_tag, evidence_key, provision_type, provision_number, act_name, evidence_text, hypothesis, condition, expected_label, construction_rules, factor_attribution, factor_paraphrase, audit_verdict` |
| Format | JSONL |
| Nature | **Controlled** — 8 conditions (verbatim/paraphrase × attribution present/absent, negated, neutral) built deterministically, no LLM involved in labeling |
| Labels exist? | Yes — `expected_label` |
| Label provenance | **Deterministic construction rule**, documented in `scripts/build_controlled_benchmark.py`. Not a model output, not a human judgment. |
| Legitimate for expected-vs-actual? | **Yes — this is one of only two true-gold datasets in the project.** |
| Reproducible? | Yes, fully, CPU-only, from `scripts/build_controlled_benchmark.py` |
| GPU required? | No (build); verifying against it needs DeBERTa, CPU-capable |
| Workspace treatment | **B** — copied as an immutable fixture into `../expected_outputs/controlled_benchmark_gold/` |
| SHA-256 | `aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec` |
| Notes | Model predictions against this set already exist at `outputs/controlled_benchmark_deberta*_results.jsonl` (bare and labeled framing) — these are **actual outputs**, not part of the gold fixture; see `../actual_outputs/README.md`. |

**As an input**: `evidence_text` (premise) + `hypothesis` fields, fed directly to
`src/verifier.py::NLIVerifier.verify(premise, hypothesis)`. **As an expected output**:
`expected_label` (ENTAILED / CONTRADICTED / NEUTRAL). **Not legitimate**: any claim about
accuracy on real, naturally-generated case text (hypotheses here are mechanically
constructed, not real model output).

### 5. Synthetic stress dataset (59 examples) — GOLD-02

| | |
|---|---|
| Source path | `research/prototype/outputs/run_synthetic_stress.jsonl` |
| Frozen? | Yes |
| Record count | **59, confirmed** (`wc -l`) — exactly 1:1 with the 59 v0 usable evidence records |
| One record represents | One real statute sentence with a single trigger phrase mechanically inverted (e.g. "shall" → "shall not", a penalty reversed) |
| Schema | `synthetic_claim_id, evidence_id, canonical_evidence_text, original_synthetic_text, transform_rule, condition_A, condition_B, condition_C, reproducibility` |
| Format | JSONL |
| Nature | **Synthetic** — built by `src/synthetic_stress.py::build_synthetic_stress_claims()`, fully deterministic, no randomness, no LLM |
| Labels exist? | Yes, implicitly — every record is CONTRADICTED by construction |
| Label provenance | Deterministic mechanical inversion of the record's own real canonical text |
| Legitimate for expected-vs-actual? | **Yes — the second of the two true-gold datasets.** Its scope is narrower: it only tests contradiction *recall*, since every example is CONTRADICTED by design (no ENTAILED/NEI examples here — that's what the 420-item benchmark is for). |
| Reproducible? | Yes, fully, CPU-only, deterministic, from `src/synthetic_stress.py` |
| GPU required? | No (build or verify); GPU only if re-running the correction stage on these |
| Workspace treatment | **B** — copied as an immutable fixture into `../expected_outputs/synthetic_stress_gold/` |
| SHA-256 | `717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5` |
| Notes | Never merged into or reported alongside natural-data evaluation — this project's own final report keeps synthetic and natural results in clearly separate sections, and this workspace preserves that separation. |

**As an input**: `canonical_evidence_text` (premise) + `original_synthetic_text` (the
corrupted claim, hypothesis), consumable by the same `verify()` call, or by the full
pipeline for correction-triggering tests. **As an expected output**: CONTRADICTED for
every record, by construction.

### 6. Natural 588-claim aggregate — METRIC-ONLY

| | |
|---|---|
| Source | **Not a standalone file.** It is a **derived aggregate**: every claim re-extracted from every real generated case text this project has ever produced (133 distinct generated texts, across every natural batch), re-parsed with the *current* parser and re-matched against the *current* evidence pool. |
| Frozen? | The underlying generated texts are frozen (they live inside various `outputs/*.jsonl` files); the aggregate itself is **recomputed fresh** each time by re-running the measurement script over them |
| Record count | 588 claims (confirmed by re-derivation), from 133 distinct generated texts |
| One record represents | One citation-bearing sentence's claim, extracted from one previously-generated case's statutory-grounding field |
| Nature | Natural (real LLM-generated case text), no independent gold label |
| Labels exist? | No independent gold. The 588-claim aggregate is used for a **NO_EVIDENCE taxonomy** (why did retrieval fail for this claim — genuinely absent, wrong-act, unresolved-act, or a parser/matcher defect), which is itself a re-derived classification, not a pre-existing label. |
| Legitimate for expected-vs-actual? | **No — metric only.** There is no independently correct "right answer" for what a real generated case's statutory grounding should say. |
| Suitable for metric evaluation? | Yes — coverage %, taxonomy category counts |
| Reproducible? | Yes, CPU-only, no GPU, no new generation — `scripts/measure_evidence_coverage_v0_vs_v1.py` re-parses/re-matches text already on disk |
| GPU required? | No |
| Workspace treatment | **C** — regenerated into `../evaluation/` (see `NATURAL_DATA_REPORT.md`) |
| Notes | Do not describe this as "588 claims we tested against ground truth." It is honestly a re-derived denominator for a coverage/taxonomy measurement, nothing more. |

### 7. 209-claim paired evaluation — METRIC-ONLY

| | |
|---|---|
| Source path | `research/prototype/outputs/final_gpu_validation_A.jsonl` (Arm A) and `_B.jsonl` (Arm B) |
| Frozen? | Yes |
| Record count | 50 cases per arm → **209 claims per arm, confirmed** |
| One record represents | One of 50 real generated cases (same 50 cases, same generation, in both arms), each carrying its own extracted claims, evidence matches, and verdicts under that arm's config (Arm A = pre-2026-08-27 baseline: v0-only evidence, bare framing, legacy scope check; Arm B = current production config) |
| Schema | `document_id, case_text, generated_field, claims[], correction, reproducibility` |
| Format | JSONL |
| Nature | Natural — **paired natural evaluation**, not a labeled dataset |
| Labels exist? | No independent gold. This is used for a **paired comparison** (e.g. McNemar's test) between two configurations run on identical underlying cases — it tells you whether Arm A and Arm B *behaved differently*, not whether either arm was *correct*. |
| Legitimate for expected-vs-actual? | **No — must not be called "ground truth."** It is explicitly a comparative-metrics dataset. |
| Suitable for metric evaluation? | Yes — this is the source of the headline evidence-coverage McNemar result (χ²=13.07, p≈0.0003, +7.1pp, 0 regressions) |
| Reproducible? | Full regeneration needs GPU (~34 min, `scripts/run_final_gpu_validation.py`); re-deriving metrics from the already-committed 209-claim files is CPU-only |
| GPU required? | Only for full regeneration, not for re-analysis |
| Workspace treatment | **A** — reference in place; a CPU-only recomputation of its paired metrics lives in `../evaluation/PAIRED_209_REPORT.md` |
| Notes | The 147 evidence-matched claims within this 209 are also the basis of the bare-vs-labeled CPU re-verification (`final_validation_bare_vs_labeled_cpu_*`). |

### 8. Natural evaluation batches — METRIC-ONLY

| Batch | Selection file | Cases | Generated/eval output |
|---|---|---|---|
| n=30 | `outputs/natural_candidate_selected_ids_30.json` | 30 (subset of batch1) | `outputs/run_{A,B,C}_n30.jsonl` |
| batch1 (n=50) | `outputs/natural_candidate_selected_ids_50.json` | 50 | `outputs/natural_candidates_50_gpu_{bare,labeled}.jsonl` |
| batch2 (n=50) | `outputs/natural_candidate_selected_ids_50_batch2.json` | 50 | `outputs/natural_candidates_batch2_gpu_{bare,labeled}.jsonl` |
| final_validation (n=50) | `outputs/natural_candidate_selected_ids_50_final_validation.json` | 50 | `outputs/final_gpu_validation_{A,B}.jsonl` (item 7 above) |
| targeted | — | 11 + 1 | `outputs/run_natural_targeted.jsonl`, `outputs/run_C_targeted_1994_495.jsonl` |

All four main batches were confirmed **disjoint by actual case-ID set intersection** in
Step 0 (not merely asserted by the docs). Selection is fully reproducible, CPU-only, from
`scripts/select_natural_candidates.py` (governed by the hand-maintained
`PREVIOUSLY_EVALUATED_SOURCES` exclusion list inside that script). Regenerating the
*generated text itself* requires GPU. None of these batches carries independent gold —
same status as items 6 and 7 (metric-only). Workspace treatment: **A** (reference in
place); selection-file hashes are recorded in `../MANIFEST.md`.

### 9. Adversarial citation test cases — BEHAVIOR

| | |
|---|---|
| Source | **No standalone data file.** Inline fixtures inside `research/prototype/tests/test_adversarial_citations.py` (7 categories: wrong-Act, same-number-different-Act, year/edition variants, aliases, numeric ranges, multi-Act bundling, field-wide ambiguity) and `test_final_pass_adversarial.py`, `test_respectively_claims.py` |
| Frozen? | Yes (part of the frozen `tests/` suite) |
| Record count | 15 + 10 + 16 test functions respectively |
| Nature | Adversarial/constructed |
| Labels exist? | Yes — exact expected code behavior (e.g. "must resolve to NO_EVIDENCE, never a guessed match") |
| Legitimate for expected-vs-actual? | This is **Category B** (exact behavioral expectation), not Category A (statistical gold label) — see `../expected_outputs/README.md`. Do not conflate the two. |
| Reproducible? | Yes, trivially — `pytest research/prototype/tests/test_adversarial_citations.py` |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; `../components/01_claim_parser/README.md` and `02_evidence_retrieval/README.md` point to these files rather than duplicating them |

### 10. Correction / sibling-safety datasets — METRIC-ONLY

| | |
|---|---|
| Source path | `outputs/final_gpu_validation_corrections_detail.jsonl` (10 records), `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` (10 records), `outputs/natural_candidates_50_gpu_corrections_detail.jsonl` (21 records) |
| Frozen? | Yes |
| One record represents | One real correction attempt on real generated text: original claim, flagged reason, corrected text, scope-check outcome, re-verification result, sibling-regression check result |
| Nature | Natural, no independent gold |
| Legitimate for expected-vs-actual? | No — metric only (0 sibling regressions / 0 unsafe shipments recorded across all of these, but "0 unsafe" is a safety-net outcome count, not a labeled accuracy figure) |
| Reproducible? | Full regeneration needs GPU; re-inspecting already-committed detail files is instant, CPU-only |
| GPU required? | Only for regeneration |
| Workspace treatment | **A** — reference in place |

### 11. Threshold-sensitivity data

| | |
|---|---|
| Source path | `outputs/threshold_sensitivity_analysis.json` / `.md` |
| Frozen? | Yes |
| Nature | **Deterministic replay** — sweeps the confidence threshold (0.50–0.95) against the *already-computed* softmax distributions stored in `controlled_benchmark_deberta*_results.jsonl`. No re-inference. |
| Legitimate for expected-vs-actual? | Indirectly — it replays decisions against the 420-item benchmark's own gold labels, so it inherits that benchmark's legitimacy, but its own artifact is an ablation/sensitivity result, not a fresh gold set |
| Reproducible? | Yes, fully, CPU-only, no model — `scripts/analyze_threshold_sensitivity.py` |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; `../ablation/README.md` documents this as the confidence-threshold ablation |
| SHA-256 | `9b2360bea33f5896049ffef5801cf0a21c8e50ea689e0a974c65f17a26f3d36a` |

### 12. Atomic-scope-check replay data

| | |
|---|---|
| Source path | `outputs/atomic_scope_check_replay.json` → `_replay_v2.json` → `_final_replay.json` (3 sequential iterations) |
| Frozen? | Yes |
| Nature | Deterministic replay of real, already-produced correction attempts through progressively extended scope-check logic — no GPU, no new Qwen/DeBERTa calls |
| Legitimate for expected-vs-actual? | No — ablation/metric only. This replay's own final-stage finding is explicitly **weak/inconclusive** (1/11 real scope violations unblocked vs. an earlier batch-1-only finding of 4/6 — not reconciled; see Step 0 audit / `../PROVENANCE.md`) |
| Reproducible? | Yes, fully, CPU-only — `scripts/replay_final_atomic_scope_check.py` (and its two predecessors) |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; `../ablation/README.md` documents this as the scope-check-mode ablation |

### Explicitly excluded from this inventory (and why)

`outputs/gold_annotation.jsonl` (88 records, template only, all fields empty),
`outputs/lawyer_annotation.jsonl` (88 records), and `outputs/assumption_annotation.jsonl`
(88 records) are **not included as inputs or as expected outputs anywhere in this
workspace.** Every record in the latter two is self-tagged
`annotation_source: "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"` — they are provisional,
LLM-generated guesses, not human or lawyer ground truth, and no report in this project
(historical or new) may treat them as gold. This is a **deliberate, documented exclusion**,
not an oversight: if a future step wants to display them (e.g. for methodology-transparency
purposes), they should be referenced directly from their frozen location in
`research/prototype/outputs/`, labeled unmistakably as provisional/unverified, and never
placed under `../expected_outputs/`. See "PROVISIONAL Inputs" below.

---

## Classification Index

IDs match `../MANIFEST.md` where the same artifact appears there (that file also tracks
non-input artifacts such as ablation replays and config files; this index is scoped to
genuine pipeline **inputs**).

| ID | Dataset | Source | Records | Format | Classification | Independent labels? | Pipeline stage | Testing role |
|---|---|---|---|---|---|---|---|---|
| IN-01 | v0 evidence corpus | `research/data/evidence/canonical_statutes.jsonl`+`evidence_audit.jsonl` | 63 raw / 59 usable | JSONL | N/A (input corpus) | N/A | Evidence retrieval | Referenced, not copied — see "Evidence Corpus" section below |
| IN-02 | v1 evidence supplement | `research/data/evidence/canonical_statutes_v1.jsonl`+`evidence_audit_v1.jsonl` | 82+82 | JSONL | N/A (input corpus) | N/A | Evidence retrieval | Referenced, not copied |
| IN-03 | Merged production evidence pool | derived (v0+v1) | 136 (live-verified) | N/A (loader output) | N/A (input corpus) | N/A | Evidence retrieval | Reproducible via `load_usable_evidence_from_config` |
| GOLD-01 | Controlled NLI benchmark | `../expected_outputs/controlled_benchmark_gold/` (copied fixture) | 420 | JSONL | **GOLD** | **Yes — deterministic construction rule** | NLI verification | Copied, hash-verified; see "GOLD Inputs" below |
| GOLD-02 | Synthetic stress set | `../expected_outputs/synthetic_stress_gold/` (copied fixture) | 59 | JSONL | **GOLD** | **Yes — deterministic construction** (contradiction only) | NLI verification, correction | Copied, hash-verified; see "GOLD Inputs" below |
| MET-01 | Natural 588-claim aggregate | derived (recomputed from 133 generated texts across `outputs/`) | 588 (re-derived) | derived, not a file | METRIC-ONLY | No | Claim parsing → evidence retrieval | Referenced, recomputable, not copied; see "METRIC-ONLY Inputs" below |
| MET-02 | 209-claim paired evaluation | `outputs/final_gpu_validation_A.jsonl`/`_B.jsonl` | 209/arm (2 arms) | JSONL | METRIC-ONLY | No — **not ground truth** | Full pipeline (paired comparison) | Referenced, not copied |
| NAT-01 | Natural batch n=30 | `outputs/run_{A,B,C}_n30.jsonl` | 30 | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| NAT-02 | Natural batch1 (n=50) | `outputs/natural_candidates_50_gpu_*.jsonl` | 50 | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| NAT-03 | Natural batch2 (n=50) | `outputs/natural_candidates_batch2_gpu_*.jsonl` | 50 | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| NAT-04 | Final validation batch (n=50) | = MET-02 | 50 cases | JSONL | METRIC-ONLY | No | Full pipeline | Referenced, not copied |
| CASE-01 | NyayaRAG case source | `research/data/nyayarag/CaseText_Statutes/*.json` | 4,930 + 4,962 | JSON (array) | N/A (input corpus) | N/A | Generation (pre-stage 1) | Referenced only — 27MB each, not copied; GPU-blocked on this machine |
| ADV-01 | Adversarial citation cases | `tests/test_adversarial_citations.py` (inline) | 15 test functions | Python fixtures | **BEHAVIOR** | Yes — exact code-behavior assertion | Claim parsing, evidence retrieval | Referenced, not duplicated; see "BEHAVIOR Inputs" below |
| ADV-02 | Final-pass adversarial cases | `tests/test_final_pass_adversarial.py` (inline) | 10 test functions | Python fixtures | **BEHAVIOR** | Yes | Claim parsing | Referenced, not duplicated |
| ADV-03 | Respectively-claims structural tests | `tests/test_respectively_claims.py` (inline) | 16 test functions | Python fixtures | **BEHAVIOR** | Yes | Claim parsing | Referenced, not duplicated |
| ADV-04 | Claim-parser bugfix regressions | `tests/test_claim_parser_bugfixes.py` (inline, real sentences) | 20 test functions | Python fixtures | **BEHAVIOR** | Yes | Claim parsing | Referenced, not duplicated |
| COR-01 | Correction/sibling-safety detail (final_gpu_validation) | `outputs/final_gpu_validation_corrections_detail.jsonl` | 10 | JSONL | METRIC-ONLY | No | Correction, scope/safety | Referenced, not copied |
| COR-02 | Correction/sibling-safety detail (labeled validation) | `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` | 10 | JSONL | METRIC-ONLY | No | Correction, scope/safety | Referenced, not copied |
| COR-03 | Correction/sibling-safety detail (batch1) | `outputs/natural_candidates_50_gpu_corrections_detail.jsonl` | 21 | JSONL | METRIC-ONLY | No | Correction, scope/safety | Referenced, not copied |
| PROV-01 | Provisional annotations | `outputs/gold_annotation.jsonl`, `lawyer_annotation.jsonl`, `assumption_annotation.jsonl` | 88+88+88 | JSONL | **PROVISIONAL** | Self-tagged NOT independently verified | N/A (post-hoc annotation, not a pipeline stage) | Referenced, never copied into `../expected_outputs/`; see "PROVISIONAL Inputs" below |
| HIST-01 | examples compilations (promoted to `evaluation/examples/` in PASS 3B) | `evaluation/examples/{candidate_pool,cases}.json` | 8+8 | JSON | HISTORICAL-ONLY | N/A | N/A (presentation layer) | Referenced only; see "Historical-Only Reference Artifacts" below |
| HIST-02 | final_comparison config/tables (archived in PASS 3B) | `archive/2026-08-27_presentation/final_comparison/comparison_config.json`, `tables/*.csv` | N/A | JSON/CSV | HISTORICAL-ONLY | N/A | N/A (presentation layer) | Referenced only |

**1. TRUE GOLD INPUTS**: GOLD-01 (n=420), GOLD-02 (n=59). Nothing else.
**2. BEHAVIOR INPUTS**: ADV-01 through ADV-04 (all inline test fixtures, no standalone data files).
**3. METRIC-ONLY INPUTS**: MET-01, MET-02, NAT-01 through NAT-04, COR-01 through COR-03.
**4. PROVISIONAL INPUTS**: PROV-01.
**5. HISTORICAL-ONLY ARTIFACTS**: HIST-01, HIST-02 (and, more broadly, everything in
`research/prototype/outputs/`'s non-selected-batch files — status reports, ablation
replays, etc. — which are inputs to *ablation/evaluation reproduction*, not to a fresh
pipeline run; see `../ablation/README.md` and `../evaluation/README.md`).

**Not classified above: evidence corpora and case sources (IN-01/02/03, CASE-01)** — these
are deliberately **not** forced into one of the four GOLD/BEHAVIOR/METRIC-ONLY/
PROVISIONAL buckets — they are retrieval/generation input corpora, not labeled test sets.
Forcing a classification onto them would be inaccurate: `audit_verdict` in the evidence
corpus labels the evidence record's own sourcing trustworthiness, not any claim's
entailment status, and NyayaRAG case text carries no verdict at all until it passes
through the (GPU-blocked, on this machine) generation stage.

**Why these are inputs**: An **input**, in this workspace, is an artifact intentionally
fed into a component or the full pipeline for a test or evaluation — something a function
genuinely reads as an argument: a case's `case_text`, an evidence pool passed to
`match_evidence`, a benchmark's `evidence_text`/`hypothesis` passed to `verify()`, or a
hand-constructed citation string passed to `extract_citation`. A **historical output** is
not automatically an input simply because it is stored as JSON or JSONL — most of
`research/prototype/outputs/` is the *result* of a previous run, sitting downstream of the
pipeline, and only becomes a legitimate input again in the narrow, explicit sense of
"reused already-generated text to avoid a redundant GPU call" (the pattern this project's
own CPU-only scripts use throughout, e.g. `compare_final_validation_labeled_cpu.py`
re-verifying `final_gpu_validation_B.jsonl`'s existing claims under a different framing).
Every row above marked METRIC-ONLY or HISTORICAL-ONLY is exactly that kind of
already-downstream artifact; only GOLD-01, GOLD-02, the evidence corpora, the case
sources, and the inline BEHAVIOR fixtures are genuinely upstream, first-fed-into-the-system
inputs in the strict sense.

---

## Plain-Language Summary

**What inputs are we using?** Two kinds, fundamentally: (a) two small,
mechanically-constructed benchmark datasets with genuine correct answers built into how
they were made, and (b) real statute text and real previously-generated case data with no
independent correct answer attached — useful for measurement and comparison, not for
scoring accuracy.

**Which are GOLD?** Only two: the 420-example controlled NLI benchmark, and the
59-example synthetic stress set. Nothing else in this project has an
independently-derived correct answer.

**Which are behavior-only?** The adversarial and edge-case citation-parsing test
fixtures (inline in `research/prototype/tests/`, ~61 test functions across 4 files).
These check that the *code* behaves exactly as designed for tricky inputs — not that any
legal conclusion is correct.

**Which are metric-only?** Everything built from real generated case text: the
588-claim aggregate, the 209-claim paired evaluation, all four natural batches, and the
correction/safety detail files. These support rates, distributions, and paired
comparisons — never an accuracy score.

**Which are provisional?** Three annotation files (`gold_annotation.jsonl`,
`lawyer_annotation.jsonl`, `assumption_annotation.jsonl`) — Claude-generated guesses,
explicitly self-tagged as not lawyer-verified. Never usable as gold, ever, under any
circumstance this workspace controls.

**Which inputs can be compared against expected outputs?** Only the two GOLD datasets.
Everything else in this project is measured, not scored against a known-correct answer.

**Which inputs require NVIDIA hardware later?** Only the raw NyayaRAG case-text input
(`CASE-01`), if used for **fresh generation** (stage 1) or **fresh correction** (stage
6). Every GOLD, BEHAVIOR, and evidence-retrieval input can be used today, on this
machine, with no GPU.

| Input | N | Status | Can compare expected output? | GPU required? |
|---|---|---|---|---|
| Controlled NLI benchmark | 420 | GOLD | **Yes** | No (DeBERTa runs CPU) |
| Synthetic stress set | 59 | GOLD | **Yes** (contradiction-recall only) | No |
| Adversarial citation fixtures | 15 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| Final-pass adversarial fixtures | 10 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| Respectively-claims fixtures | 16 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| Claim-parser bugfix fixtures | 20 tests | BEHAVIOR | Yes, at code-behavior level only | No |
| 588-claim natural aggregate | 588 (derived) | METRIC-ONLY | No | No (re-derivation is CPU-only) |
| 209-claim paired evaluation | 209/arm | METRIC-ONLY | No — not ground truth | Full regen: yes; re-analysis: no |
| Natural batch n=30 | 30 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Natural batch1 (n=50) | 50 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Natural batch2 (n=50) | 50 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Final validation batch (n=50) | 50 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Correction/safety detail (×3 files) | 10+10+21 | METRIC-ONLY | No | Full regen: yes; re-analysis: no |
| Evidence corpus (v0+v1 merged) | 136 usable | N/A (input corpus) | N/A | No |
| NyayaRAG case source | 4,930+4,962 | N/A (input corpus) | N/A | **Yes, for fresh generation** — blocked on this machine |
| Provisional annotations (×3 files) | 88+88+88 | PROVISIONAL | No, never | No |
| examples/final_comparison compilations (examples/ promoted to `evaluation/`, final_comparison archived, in PASS 3B) | N/A | HISTORICAL-ONLY | No | No |

---

## Pipeline Flow (Input → Component Mapping)

Every mapping below cites the exact function/class verified against `src/` in STEP 0's
pipeline trace — nothing here is an invented interface. "Expected-output comparison
legitimate?" follows strictly from the Classification Index above: only GOLD inputs
support it.

```
INPUT (case_text, from NyayaRAG or an already-generated field)
  |
  v
[1] GENERATION -- src/generator.py::StatuteGroundingGenerator.generate(case_text)
  |  Model: Qwen2.5-7B-Instruct, 4-bit. GPU required, no CPU fallback.
  |  BLOCKED on this machine (no NVIDIA GPU, confirmed STEP 2).
  v
generated_field.text
  |
  v
[2] CLAIM PARSER -- src/claim_parser.py::extract_claims(generated_text)
  |  Deterministic, no model.
  v
CLAIMS (list[Claim]: claim_text, citation_extracted, assertion_text, assertion_spans)
  |
  v
[3] EVIDENCE RETRIEVAL -- src/evidence_matcher.py::match_evidence(citation, exact_index, pool, threshold)
  |  Deterministic, no model. Pool from src/data_loader.py::load_usable_evidence_from_config
  |  (IN-01 + IN-02 -> IN-03, 136 records).
  v
MATCHED EVIDENCE (MatchResult: matched, evidence, match_method) | NO_EVIDENCE
  |
  v
[4] NLI VERIFIER -- src/verifier.py::NLIVerifier.verify(premise, hypothesis)
  |  Model: DeBERTa-v3-base-mnli-fever-anli. GPU by default, CPU opt-in exists (confirmed
  |  runnable on this machine, STEP 2).
  |  premise built by src/verifier.py::format_premise() (bare/labeled), threaded via
  |  src/pipeline.py::_premise_for_claim().
  v
VERDICT (VerificationResult: label, confidence, sub_reason, raw_scores)
  |
  v
[5] VERDICT APPLICATION -- src/pipeline.py::apply_verification (mutates claims[] in place)
  |
  v (Mode C only, first flagged claim: CONTRADICTED any confidence, or NEI+low_confidence)
  |
  v
[6] CORRECTOR -- src/corrector.py::SelectiveCorrector.correct()
  |  Reuses [1]'s loaded Qwen model. GPU required (inherits [1]).
  |  BLOCKED on this machine (no NVIDIA GPU).
  v
CANDIDATE CORRECTION (corrected_text, CorrectionMetadata)
  |
  v
[7] SCOPE / SAFETY CHECK -- src/pipeline.py::_scope_violation(), _reverify_sibling_regressions(), _citation_identity()
  |  Deterministic checks; sibling-regression re-verification re-invokes [4].
  v
SCOPE OK -> proceed | SCOPE VIOLATION -> correction_scope_violation, original text shipped
  |
  v
[8] RE-VERIFICATION -- src/pipeline.py::apply_selective_correction (re-verify step)
  |  Re-invokes [4] (DeBERTa) with the (optionally narrowed) hypothesis.
  v
SHIP / REJECT -- status = "corrected" iff result.label == ENTAILED; else "correction_failed"
  |
  v
[9] FINAL ASSEMBLY -- src/pipeline.py::run_case (final_field, reproducibility block)
  |
  v
FINAL OUTPUT
```

### Per-stage input/output/legitimacy table

| Stage | Input artifact | Exact loader/function | Component | Output artifact/object | Expected-output comparison legitimate? |
|---|---|---|---|---|---|
| 1. Generation | CASE-01 (case_text) | `src/generator.py::StatuteGroundingGenerator.generate` | Qwen2.5-7B-Instruct | `generated_field.text` | No — no independent gold exists for what a case's statutory grounding "should" say; **also currently unrunnable on this machine (no GPU)** |
| 2. Claim parsing | `generated_field.text` (fresh) OR any already-committed generated text (metric-only reuse) | `src/claim_parser.py::extract_claims` | deterministic, no model | `list[Claim]` | Category B only (ADV-01..04: exact parsing behavior for constructed/adversarial inputs) — not a statistical claim |
| 3. Evidence retrieval | `Claim.citation_extracted` + IN-03 (136-record pool) | `src/evidence_matcher.py::match_evidence` | deterministic, no model | `MatchResult` / `NO_EVIDENCE` | Category B only (ADV-01: fail-safe NO_EVIDENCE-on-ambiguity behavior) — coverage rate itself is METRIC-ONLY (MET-01) |
| 4. NLI verification | GOLD-01 (`evidence_text`, `hypothesis`) for gold evaluation; OR `MatchResult.evidence` + `Claim.claim_text` for real/metric use | `src/verifier.py::NLIVerifier.verify` (+ `format_premise`) | DeBERTa-v3-base-mnli-fever-anli | `VerificationResult` | **Yes, against GOLD-01 (n=420) — the only legitimate accuracy comparison in this project.** Also legitimate against GOLD-02 (n=59) for contradiction-recall specifically |
| 5. Verdict application | `VerificationResult` | `src/pipeline.py::apply_verification` | no model | mutated `claims[]` | No independent label; this stage applies stage 4's result verbatim |
| 6. Correction | flagged `Claim` + `MatchResult.evidence` | `src/corrector.py::SelectiveCorrector.correct` | reuses stage 1's Qwen model | `(corrected_text, CorrectionMetadata)` | No — no independent gold for "the correct fix"; **also currently unrunnable on this machine (no GPU)**. GOLD-02's by-construction CONTRADICTED labels make correction-*triggering* (not correction *content*) checkable |
| 7. Scope/safety | `corrected_text` + sibling `Claim`s | `src/pipeline.py::_scope_violation`, `_reverify_sibling_regressions`, `_citation_identity` | deterministic + re-invokes stage 4 | scope-ok/violation, sibling-regression flag | Category B only — exact behavioral guarantee ("unflagged claim's required text must survive verbatim"), not a statistical claim |
| 8. Re-verification | replacement `Claim.assertion_text`/`claim_text` + re-matched evidence | `apply_selective_correction` re-verify step | DeBERTa (stage 4 reused) | `status = "corrected" \| "correction_failed"` | No independent gold for real corrections; the unconditional ENTAILED-only gate itself is a Category B (code-behavior) guarantee, verified in `../components/07_reverification/` |
| 9. Final assembly | all of the above | `src/pipeline.py::run_case` | no model | final JSONL record | No — assembly-correctness is Category B (`../components/08_final_assembly/`), not a statistical claim |

---

## GOLD Inputs

**No files are duplicated here.** The two legitimate GOLD fixtures already exist, copied
and hash-verified, at `../expected_outputs/controlled_benchmark_gold/` and
`../expected_outputs/synthetic_stress_gold/` (built in STEP 1). This section documents
them from the **input** side of the same files — each record is simultaneously an input
(premise + hypothesis fed to the NLI verifier) and a gold label (its `expected_label` /
by-construction verdict) — rather than creating a second copy.

| | GOLD-01 — Controlled verifier benchmark (n=420) | GOLD-02 — Synthetic stress set (n=59) |
|---|---|---|
| Fixture | `../expected_outputs/controlled_benchmark_gold/controlled_verifier_benchmark.jsonl` | `../expected_outputs/synthetic_stress_gold/run_synthetic_stress.jsonl` |
| SHA-256 | `aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec` | `717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5` |
| Verified | STEP 1, re-verified STEP 2 | STEP 1, re-verified STEP 2 |
| Classification | **GOLD** | **GOLD** (narrower: contradiction-recall only) |
| Legitimate use | Genuine accuracy/F1 measurement of the verifier against a known-correct answer | Same, contradiction-recall specifically |
| Not legitimate | Any claim about accuracy on real, naturally-generated case text | Same |

**No other dataset may be promoted to GOLD.** Every other dataset referenced anywhere in
this workspace — the 588-claim aggregate, the 209-claim paired evaluation, every natural
batch, every correction/safety dataset, and all three provisional-annotation files —
remains METRIC-ONLY or PROVISIONAL. See "METRIC-ONLY Inputs" and "PROVISIONAL Inputs"
below.

---

## BEHAVIOR Inputs

**No new fixtures are created here.** These inputs already exist as hand-constructed,
inline Python fixtures inside the frozen `research/prototype/tests/` suite — there is no
separate data file to copy, and this workspace does not rewrite or duplicate test code.

**What "BEHAVIOR" means**: an exact, hand-authored input constructed specifically to
exercise one deterministic code path — most often an adversarial or edge-case
citation/claim shape — paired with an exact expected **code behavior** (e.g. "must
resolve to `NO_EVIDENCE`, never a guessed match"). This is a software-invariant
expectation, not a statistical or legal ground-truth claim. It answers "does the
implementation do what it was designed to do for this input shape?", never "is this
legally correct?".

| Source file | Inputs supplied | Behavior asserted | Component |
|---|---|---|---|
| `tests/test_adversarial_citations.py` (15 tests) | inline `_make_evidence()`/`_pool()` fixtures: wrong-Act, same-number-different-Act, year/edition variants, aliases, numeric ranges, multi-Act bundling, field-wide ambiguity | fail-safe: unresolved/ambiguous citations must resolve to `NO_EVIDENCE`, never a guessed match; 2 categories pin real audit near-misses (CrPC-vs-CPC §100 confusion; a "Mysore Land Acquisition Act" near-miss) confirmed NOT defects | `src/claim_parser.py` + `src/evidence_matcher.py` |
| `tests/test_final_pass_adversarial.py` (10 tests) | 1 real defect regression input (a "Section N, Part &lt;roman&gt;" act-pollution shape found via `audit_no_evidence_taxonomy_v2.py`) + constructed edge-case citation strings | fail-closed: these edge-case shapes must not silently produce a wrong match; proven absent from every real generated text this project has produced | `src/claim_parser.py` |
| `tests/test_respectively_claims.py` (16 tests) | constructed multi-citation "respectively" sentences (simple/multi-Act/multi-provision/ordering/malformed) | `assertion_spans` structural correctness — each fragment must be a genuine verbatim substring, never synthesized; malformed shapes must fail closed to the default (full-sentence) behavior | `src/claim_parser.py::_assign_respectively_spans` |
| `tests/test_claim_parser_bugfixes.py` (20 tests) | real, verbatim sentences copied from `outputs/gold_annotation.jsonl` (4 named document_ids) — real Qwen output, not invented | 5 named act-attribution bug patterns must not recur (multi-act run-on bleed, year-mistaken-for-provision-number, trim-heuristic failure, field-wide single-act-fallback override) | `src/claim_parser.py` |

**Why these are legitimate as software-invariant expectations**: every expected behavior
above is a **structural guarantee independent of legal content** — "never guess," "never
fabricate a span," "never let one bug pattern silently recur" — verifiable purely from
the input string and the output data structure, with no legal judgment involved. This is
categorically different from asserting a statute's legal meaning is correctly captured;
none of these tests make that claim.

**What must NOT be claimed from these**: that passing these tests establishes
statistical accuracy on unconstrained real input, or that any citation-matching or
claim-parsing decision here reflects verified legal correctness. See
`../components/01_claim_parser/README.md` and `02_evidence_retrieval/README.md` for the
full per-stage mapping (this section is a classification-first view of the same
underlying tests; those directories are a pipeline-stage-first view).

---

## METRIC-ONLY Inputs

**No files are copied here.** Every dataset below is frozen, already sizeable, and
already documented with hashes/counts in the Master Input Reference above and
`../MANIFEST.md` — this section references them and states, explicitly and without
exception, that none of them carries an independently established expected label.

**Non-negotiable rule this section exists to enforce**: no verdict, label, or "expected
output" may ever be attached to any dataset below merely because the production system
itself previously produced one. A historical verdict is the system's own output, not
ground truth about what the correct verdict should have been.

- **588-claim natural aggregate** — not a standalone file; a derived aggregate: every
  claim re-extracted (with the *current* parser, against the *current* evidence pool)
  from all 133 distinct generated texts this project has produced. Reproducible,
  CPU-only, no GPU: `scripts/measure_evidence_coverage_v0_vs_v1.py`. Used for: a
  NO_EVIDENCE root-cause taxonomy (genuinely-absent / wrong-act / unresolved-act /
  parser-defect-candidate) — itself a re-derived classification, not a pre-existing
  label. **Status: METRIC-ONLY.**
- **209-claim paired natural evaluation** — `outputs/final_gpu_validation_A.jsonl` /
  `_B.jsonl` — 50 real generated cases, same generation, evidence-matched independently
  under two configurations (Arm A = pre-2026-08-27 baseline, Arm B = current production
  config). Used for: a **paired comparison** (McNemar's test) of whether the two
  configurations *behaved differently* on identical underlying cases (χ²=13.07,
  p≈0.0003, +7.1pp evidence coverage, 0 regressions) — never a statement about which arm
  was *correct*. **Status: METRIC-ONLY, explicitly not ground truth.**
- **Natural evaluation batches** (n=30, batch1, batch2, final_validation, targeted) —
  `outputs/run_{A,B,C}_n30.jsonl`, `outputs/natural_candidates_50_gpu_*.jsonl`,
  `outputs/natural_candidates_batch2_gpu_*.jsonl`, `outputs/final_gpu_validation_*.jsonl`
  (same as 209-claim set above), `outputs/run_natural_targeted.jsonl`. Confirmed disjoint
  by direct case-ID intersection (STEP 0). **Status: METRIC-ONLY.**
- **Correction / sibling-safety datasets** —
  `outputs/final_gpu_validation_corrections_detail.jsonl` (10),
  `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` (10),
  `outputs/natural_candidates_50_gpu_corrections_detail.jsonl` (21). **Status:
  METRIC-ONLY.** "0 sibling regressions / 0 unsafe shipments" is a real, countable
  safety-net outcome across these records — it is not a labeled accuracy figure, and
  must not be presented as one.

**What can legitimately be concluded**: descriptive statistics (rates, distributions,
funnel counts) and paired/comparative statistics between two configurations run on
identical underlying cases (which is exactly what makes the evidence-coverage McNemar
result meaningful — it compares the *same* 209 claims under two configs, not against a
gold label).

**What must NOT be concluded**: any accuracy, precision, recall, or F1 number against a
"correct answer," for any of the datasets above. The only two datasets in this project
supporting that kind of number are GOLD-01 and GOLD-02 above.

**Known caveats that must travel with any report drawing on this data**:
1. The correction-shipping-rate improvement (5→10 triggered, 0→1 shipped) is **not
   statistically significant** at this sample size.
2. **No single experiment combines all four current production-config levers in one
   fresh generation pass** — see `../PROVENANCE.md`.
3. The scope-check-mode ablation is **unreconciled** (1/11 vs. an earlier 4/6 unblocked
   finding) — see `../ablation/README.md`.

---

## PROVISIONAL Inputs

**No files are copied here, and none should ever be.** This section documents, by
reference only, the three datasets in this project that carry provisional,
non-independently-verified labels — specifically so a future contributor has a positive,
documented place to look and finds an explicit warning, rather than silently
rediscovering these files unlabeled somewhere in `outputs/`.

| File | Records | Self-tagged as |
|---|---|---|
| `research/prototype/outputs/gold_annotation.jsonl` | 88 | template only — annotation fields are empty strings, never filled in by anyone |
| `research/prototype/outputs/lawyer_annotation.jsonl` | 88 | `annotation_source: "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"` on every record |
| `research/prototype/outputs/assumption_annotation.jsonl` | 88 | same self-tag; same underlying claim_id sequence as `lawyer_annotation.jsonl` — a later iteration of the same batch, not new data |

Confirmed directly by reading the `annotation_source` field on real records, not by
trusting a doc's claim about them (STEP 0 dataset-inventory finding).

**Non-negotiable rule**: **No real lawyer or human ground truth exists anywhere in this
project.** These are Claude-generated provisional guesses about verdicts. They must
never be: copied into `../expected_outputs/`; described as "expected output," "ground
truth," or "validated" in any report; used as the denominator or reference in an accuracy
calculation; or silently relabeled if a future annotation pass fills in the empty
`gold_annotation.jsonl` template — even a completed version of that template would need
its own, separately documented provenance (who annotated it, when, under what protocol)
before it could be considered for GOLD status.

**What these files are legitimately useful for**: methodology/process transparency
(showing what a human-annotation protocol was designed to look like —
`outputs/lawyer_annotation_guide.md`), and — with explicit, repeated caveats — an
*agreement* measurement against the automated verifier's own verdicts
(`outputs/assumption_gold_bare_vs_labeled_metrics.json`: labeled framing agrees
*slightly less*, 47.4% vs. bare's 52.6%, the opposite direction from every other
convergent finding in this project — reported honestly, not suppressed, in
`FINAL_PRODUCTION_CONFIG.md`). This is an agreement-with-a-guess number, not an accuracy
number.

**Classification: PROVISIONAL**, permanently, unless and until a real,
independently-documented human annotation process produces a genuinely new artifact.

---

## Historical-Only Reference Artifacts

**Not inputs.** These are artifacts that contain JSON/CSV data and are referenced
throughout this project's documentation, but are not intentionally fed into any pipeline
component or test as an input — they are *compilations built from* historical results,
for presentation purposes. Listed here explicitly so their status is unambiguous: they
are evidence/reference material, never a fresh testing input, and never re-derived or
altered by this workspace.

**Why an input is different from "any file with data in it"**: an **input** is an
artifact intentionally fed into a component or the pipeline for a test/evaluation —
something a function actually reads as its argument (a case's `case_text`, an evidence
pool, a benchmark's `evidence_text`/`hypothesis`). A **historical output** is something
the system (or a presentation-layer script built on top of the system's historical
outputs) already produced. The fact that a historical output happens to be stored as
JSON does not make it an input to anything in this workspace — it is already downstream
of the pipeline, not upstream of it.

| Artifact | What it is | Why it's historical-only, not an input |
|---|---|---|
| `evaluation/examples/candidate_pool.json` (8 categories, promoted from `final_demo_pack/examples/` in PASS 3B) | A curated pool of illustrative real cases (contradicted catches, shipped corrections, scope violations, etc.), selected by `find_candidates.py` from already-committed natural outputs | It is a *selection of historical outputs for presentation*, not new data — feeding it back into a component would just re-run something already recorded |
| `evaluation/examples/cases.json` (8 worked cases, promoted from `final_demo_pack/examples/` in PASS 3B) | Hand-written narrative case studies built from the above pool by `build_cases_json.py` | Same — a presentation compilation of historical results, not a pipeline input |
| `archive/2026-08-27_presentation/final_comparison/comparison_config.json` | A hand-authored, machine-readable definition of what "ORIGINAL" vs. "CURRENT" config means, plus 7 named isolated A/B experiment pairs, each citing exact `outputs/` source files | A configuration/definition document for a comparison analysis, not something any pipeline component consumes as input |
| `archive/2026-08-27_presentation/final_comparison/tables/*.csv`, `archive/2026-08-27_presentation/final_demo_pack/tables/*.csv` | Computed tables built by `build_comparison_data.py`/`generate_tables.py` from `outputs/*` | Downstream computed results, not inputs |
| The `outputs/` status-report chain (`pre_gpu_readiness_report.md` → ... → `research_completion_report.md` → `research_phase_next_status.md`) | Sequential project-history checkpoints | Narrative history, not machine-readable input to any component |

**What this workspace does with these**: references them directly at their frozen paths
when a report needs to cite them — never copies, re-derives, or treats any of them as a
fresh testing input.

---

## Evidence Corpus — Source Detail

**This section documents a reference, not a copy.** The evidence corpus is already
clean, small, frozen, and directly usable at its original location — copying it would
create a second source of truth for no benefit.

The statute/citation evidence corpus consumed by
`src/evidence_matcher.py::match_evidence` (stage 3, evidence retrieval) — never
generated text, never a claim, never a verdict.

| | |
|---|---|
| v0 | `research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl` — 63 raw / 59 usable records |
| v1 | `research/data/evidence/canonical_statutes_v1.jsonl` + `evidence_audit_v1.jsonl` — 82 + 82 records |
| Merged (production) | v0+v1 via `src/data_loader.py::load_usable_evidence_from_config`, `use_evidence_v1: true` — **136 usable records**, live-verified in STEP 1/2 |

One record represents one statute/citation key's independently-sourced canonical text
(IndianKanoon.org, third-party — India Code returned HTTP 403 on every attempt), plus a
separately-keyed audit-verdict record. Consumed via exact-key lookup, then fuzzy
act-token-overlap fallback, against the pool returned by
`src/data_loader.py::load_usable_evidence[_from_config]`.

**Classification**: N/A / input corpus — not GOLD, BEHAVIOR, METRIC-ONLY, or
PROVISIONAL. It is a retrieval corpus, not a labeled test set: `audit_verdict` labels the
evidence record's own trustworthiness (was this citation's text correctly sourced?), not
any claim's entailment status.

**What can legitimately be measured from it**: coverage (what fraction of real claims
resolve to a match vs. `NO_EVIDENCE`), and comparative coverage between v0-only and v0+v1
pools (McNemar χ²=13.07, p≈0.0003, +7.1pp, n=209 — see `../evaluation/NATURAL_DATA_REPORT.md`).
**Not** a source of verifier ground truth by itself.

**What must NOT be claimed**: that this corpus is official/government-sourced (it is
third-party, IndianKanoon-derived, explicitly not India Code text), or that it is
complete (top-100/top-143 citation keys by frequency only, not the full ~8,100 distinct
NyayaRAG citations).

**Reference, not copy**: reference path `research/data/evidence/` (all 4 files), frozen,
SHA-256 recorded above and in `../MANIFEST.md`. Referenced rather than copied because the
files are already frozen, already read-only by design (`config/prototype.yaml`'s own
comment: "Evidence files are READ-ONLY inputs. Never write to these."), small, and
copying would create a second, driftable source of truth for the same data.

---

## Case Inputs — Source Detail

**This section documents a reference, not a copy.** The NyayaRAG source case files are
large (~27MB each) and already frozen at their original location — copying them would
duplicate a large dataset unnecessarily.

Real Indian Supreme Court case text (`case_text` / `summarized_text`) that would be fed
as `case_text` into `src/generator.py::StatuteGroundingGenerator.generate()` (stage 1,
generation) to produce a fresh statutory-grounding field. **This machine has no NVIDIA
GPU** (see `../actual_outputs/step2_environment_setup/ENVIRONMENT_REPRODUCIBILITY_RESULT.md`),
so this input cannot currently be run through generation here — it is documented for
completeness and for any future GPU-capable environment.

| | |
|---|---|
| Source | `L-NLProc/NyayaRAG` on Hugging Face, `3.CaseText_Statutes.zip` |
| Files | `research/data/nyayarag/CaseText_Statutes/SCI_56k_multi_5k_summarised_w_sections.json` (4,930 records, 26.9 MB), `SCI_56k_single_5k_summarised_w_sections.json` (4,962 records, 27.7 MB) |
| Schema | one record: `{document_id, summarized_text, sections}` — `sections` is a dict of citation-key → NyayaRAG's own (unverified, never used as evidence) text |
| Provenance caveat | Populated by copying files already extracted in an earlier session's scratch space — **not reproducible from a clean checkout** without re-obtaining the zip from Hugging Face; no committed script downloads it automatically |

**Which cases have already been selected from this pool** (for reference, not fresh
selection): the natural-batch selection files record which `document_id`s were
previously drawn from this pool —
`outputs/natural_candidate_selected_ids_{30,50,50_batch2,50_final_validation}.json` —
confirmed disjoint by direct ID-set intersection in STEP 0. Their hashes are recorded in
`../MANIFEST.md`.

**Which component consumes it**: `src/generator.py::StatuteGroundingGenerator.generate(case_text)`
— only `case_text` (or `summarized_text`) and the case's own citation **keys** are read;
NyayaRAG's own `sections` free-text values are never treated as evidence anywhere in this
pipeline.

**Classification**: N/A / input corpus — pre-generation raw case text, not a labeled
dataset. Selecting a disjoint new batch from it is possible via
`scripts/select_natural_candidates.py` (CPU-only, deterministic, no GPU) even on this
machine; only the subsequent *generation* step requires a GPU this machine does not have.

**What can legitimately be measured from it**: nothing directly — it is raw input.
Selection scoring (`score_case`) can run and be inspected here; no claim, verdict, or
correction exists until generation runs, which is blocked on this machine.
