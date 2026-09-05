# Inputs Inventory

**STEP 3 added three reviewer-facing master documents that sit above this file:**
`INPUT_MANIFEST.md` (the full classification table), `INPUT_TO_COMPONENT_MAP.md` (exact
input→function→output chain per pipeline stage), and `INPUT_SUMMARY.md` (plain-language
answers). Start there; this file remains the detailed, per-dataset reference they cite.
STEP 3 also added five classification subdirectories (`gold/`, `behavior/`,
`metric_only/`, `provisional/`, `historical_reference/`) that organize the same
underlying datasets by GOLD/BEHAVIOR/METRIC-ONLY/PROVISIONAL/historical status, alongside
this file's `evidence/` and `cases/` (which organize by pipeline role instead).

Everything the production pipeline consumes *before* it produces a result. Nothing in
this directory is generated text, a verdict, or a correction — those are outputs (see
`../expected_outputs/README.md`, `../actual_outputs/README.md`).

All counts below were independently verified (line counts / JSON parsing / a live
evidence-loader run), not copied from documentation. Hashes are SHA-256 over the exact
committed file bytes, computed 2026-09-05.

**Column legend**
- **Workspace treatment**: **A**=reference source in place (never copied), **B**=copy as
  an immutable fixture into this workspace, **C**=regenerate later (not yet done).
- **Expected-vs-Actual legitimate?**: whether this dataset's own labels are an
  independently-derived gold standard suitable for `comparisons/expected_vs_actual/`.
  "No — metric only" means it can still be evaluated, just not against a known-correct
  answer (see `comparisons/metric_based/`).

---

## 1. v0 evidence corpus

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

## 2. v1 evidence supplement

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

## 3. Merged production evidence pool

| | |
|---|---|
| Source | v0 (59 usable) + v1 (79 new usable + 3 corrections − 1 downgrade), merged at load time |
| Frozen? | Yes (the two source file pairs above are frozen; the merge is a pure function of them) |
| Record count | **136**, confirmed live: `src.data_loader.load_usable_evidence_from_config(cfg, '.')` with `use_evidence_v1: true` (Step 0 audit re-ran this loader directly and got 136) |
| Produced by | `src/data_loader.py::load_usable_evidence_from_config`, controlled by `config/prototype.yaml`'s `use_evidence_v1: true` |
| Legitimate for expected-vs-actual? | No — input corpus, not a label set |
| Reproducible? | Yes, fully — CPU-only, no model, see `evaluation/README.md`'s reproduction command for this |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; not a physical file, a config+loader combination |
| Notes | This is the pool every current-production evaluation should use. Historical outputs committed before 2026-08-27 used the 59-record v0-only pool — do not conflate the two when comparing old and new results. |

## 4. Controlled NLI benchmark (420 examples)

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
| Workspace treatment | **B** — copy as an immutable fixture into `expected_outputs/controlled_benchmark_gold/` |
| SHA-256 | `962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99` |
| Notes | Model predictions against this set already exist at `outputs/controlled_benchmark_deberta*_results.jsonl` (bare and labeled framing) — these are **actual outputs**, not part of the gold fixture; see `actual_outputs/README.md`. |

## 5. Synthetic stress dataset (59 examples)

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
| Workspace treatment | **B** — copy as an immutable fixture into `expected_outputs/synthetic_stress_gold/` |
| SHA-256 | `2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516` |
| Notes | Never merged into or reported alongside natural-data evaluation — this project's own final report keeps synthetic and natural results in clearly separate sections, and this workspace preserves that separation. |

## 6. Natural 588-claim aggregate

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
| Workspace treatment | **C** — regenerate later into `evaluation/` when this step's evaluation runs happen; not copied as a static file now |
| Notes | Do not describe this as "588 claims we tested against ground truth." It is honestly a re-derived denominator for a coverage/taxonomy measurement, nothing more. |

## 7. 209-claim paired evaluation

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
| Workspace treatment | **A** — reference in place; a CPU-only recomputation of its paired metrics is a **C** (planned for `evaluation/`) |
| Notes | The 147 evidence-matched claims within this 209 are also the basis of the bare-vs-labeled CPU re-verification (`final_validation_bare_vs_labeled_cpu_*`). |

## 8. Natural evaluation batches

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
place); selection-file hashes are recorded in `MANIFEST.md`.

## 9. Adversarial citation test cases

| | |
|---|---|
| Source | **No standalone data file.** Inline fixtures inside `research/prototype/tests/test_adversarial_citations.py` (7 categories: wrong-Act, same-number-different-Act, year/edition variants, aliases, numeric ranges, multi-Act bundling, field-wide ambiguity) and `test_final_pass_adversarial.py`, `test_respectively_claims.py` |
| Frozen? | Yes (part of the frozen `tests/` suite) |
| Record count | 15 + 10 + 16 test functions respectively |
| Nature | Adversarial/constructed |
| Labels exist? | Yes — exact expected code behavior (e.g. "must resolve to NO_EVIDENCE, never a guessed match") |
| Legitimate for expected-vs-actual? | This is **Category B** (exact behavioral expectation), not Category A (statistical gold label) — see `expected_outputs/README.md`. Do not conflate the two. |
| Reproducible? | Yes, trivially — `pytest research/prototype/tests/test_adversarial_citations.py` |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; `component_tests/01_claim_parser/README.md` and `02_evidence_retrieval/README.md` point to these files rather than duplicating them |

## 10. Correction / sibling-safety datasets

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

## 11. Threshold-sensitivity data

| | |
|---|---|
| Source path | `outputs/threshold_sensitivity_analysis.json` / `.md` |
| Frozen? | Yes |
| Nature | **Deterministic replay** — sweeps the confidence threshold (0.50–0.95) against the *already-computed* softmax distributions stored in `controlled_benchmark_deberta*_results.jsonl`. No re-inference. |
| Legitimate for expected-vs-actual? | Indirectly — it replays decisions against the 420-item benchmark's own gold labels, so it inherits that benchmark's legitimacy, but its own artifact is an ablation/sensitivity result, not a fresh gold set |
| Reproducible? | Yes, fully, CPU-only, no model — `scripts/analyze_threshold_sensitivity.py` |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; `ablation/README.md` documents this as the confidence-threshold ablation |
| SHA-256 | `9b2360bea33f5896049ffef5801cf0a21c8e50ea689e0a974c65f17a26f3d36a` |

## 12. Atomic-scope-check replay data

| | |
|---|---|
| Source path | `outputs/atomic_scope_check_replay.json` → `_replay_v2.json` → `_final_replay.json` (3 sequential iterations) |
| Frozen? | Yes |
| Nature | Deterministic replay of real, already-produced correction attempts through progressively extended scope-check logic — no GPU, no new Qwen/DeBERTa calls |
| Legitimate for expected-vs-actual? | No — ablation/metric only. This replay's own final-stage finding is explicitly **weak/inconclusive** (1/11 real scope violations unblocked vs. an earlier batch-1-only finding of 4/6 — not reconciled; see Step 0 audit / `PROVENANCE.md`) |
| Reproducible? | Yes, fully, CPU-only — `scripts/replay_final_atomic_scope_check.py` (and its two predecessors) |
| GPU required? | No |
| Workspace treatment | **A** — reference in place; `ablation/README.md` documents this as the scope-check-mode ablation |

---

## Explicitly excluded from this inventory (and why)

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
placed under `expected_outputs/`.
