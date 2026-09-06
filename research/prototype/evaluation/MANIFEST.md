# Manifest

**STEP 1 historical snapshot.** For the current, complete deliverable-by-deliverable
inventory (through STEP 13 / PASS 3B), see `reports/FINAL_WORKSPACE_MANIFEST.md` instead.
This file is kept unedited as the original workspace-design record.

Machine-readable-style inventory of every testing artifact referenced by this workspace.
Counts and hashes below were independently verified 2026-09-05 (line counts, JSON
parsing, `sha256sum`, or a live evidence-loader run) — not copied from prior
documentation without checking.

**Ground-Truth Status** (added beyond the requested columns, per this workspace's design
review — makes the Category A/B/C distinction from `expected_outputs/README.md`
unambiguous per-row): `GOLD` (Category A, independently-derived), `BEHAVIOR` (Category B,
exact code-behavior expectation), `METRIC-ONLY` (Category C, no independent label),
`PROVISIONAL` (self-tagged not-lawyer-verified, never usable as gold), `N/A` (not a
labeled dataset — e.g. a config file or a corpus used only as retrieval input).

| ID | Artifact | Location | Type | Source | Records | Frozen? | Ground-Truth Status | Expected-vs-Actual? | Metric Eval? | Ablation? | GPU Required? | Reproducible? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IN-01 | v0 evidence corpus | `research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl` | input corpus | curated, IndianKanoon.org | 63 raw / 59 usable | Yes | N/A | No | No | No | No | Yes (static file) | SHA-256 in `inputs/README.md` §1 |
| IN-02 | v1 evidence supplement | `research/data/evidence/canonical_statutes_v1.jsonl` + `evidence_audit_v1.jsonl` | input corpus | curated, IndianKanoon.org | 82 + 82 | Yes | N/A | No | No | No | No | Data yes, build script no (`build_evidence_v1.py` dead scratch path) | SHA-256 in `inputs/README.md` §2 |
| IN-03 | Merged production evidence pool | derived (v0+v1 via `load_usable_evidence_from_config`) | input corpus (derived) | IN-01 + IN-02 | 136 (live-verified) | Yes (deterministic fn of frozen inputs) | N/A | No | No | No | No | Yes, CPU-only | Production default (`use_evidence_v1: true`) |
| GOLD-01 | Controlled NLI benchmark | `expected_outputs/controlled_benchmark_gold/controlled_verifier_benchmark.jsonl` | gold dataset | deterministic construction, `scripts/build_controlled_benchmark.py` | 420 | Yes (copied fixture) | **GOLD** | **Yes** | No | Indirectly (threshold sweep replays against it) | No | Yes, CPU-only | SHA-256 `aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec` |
| GOLD-02 | Synthetic stress set | `expected_outputs/synthetic_stress_gold/run_synthetic_stress.jsonl` | gold dataset | deterministic mechanical inversion, `src/synthetic_stress.py` | 59 | Yes (copied fixture) | **GOLD** | **Yes** (contradiction-recall only) | No | No | No | Yes, CPU-only | SHA-256 `717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5` |
| MET-01 | Natural 588-claim aggregate | derived (recomputed from all natural generated texts) | metric-only, derived aggregate | 133 distinct generated texts across all natural batches | 588 (re-derived) | Underlying texts frozen; aggregate recomputed | METRIC-ONLY | No | Yes | No | No | Yes, CPU-only, no new generation | `scripts/measure_evidence_coverage_v0_vs_v1.py` |
| MET-02 | 209-claim paired evaluation | `research/prototype/outputs/final_gpu_validation_A.jsonl` / `_B.jsonl` | metric-only, paired natural eval | 50 real generated cases, 2 arms | 209 claims/arm | Yes | METRIC-ONLY | **No — not ground truth** | Yes (McNemar paired) | No | Full regen: yes; re-analysis: no | Regen: yes, ~34 min GPU | Basis of χ²=13.07, p≈0.0003 evidence-coverage result |
| NAT-01 | Natural batch n=30 | `outputs/run_{A,B,C}_n30.jsonl` | metric-only, natural | real generation | 30 cases | Yes | METRIC-ONLY | No | Yes | No | Regen: yes | Regen: yes, GPU | Subset of batch1 |
| NAT-02 | Natural batch1 (n=50) | `outputs/natural_candidates_50_gpu_{bare,labeled}.jsonl` | metric-only, natural | real generation | 50 cases | Yes | METRIC-ONLY | No | Yes | No | Regen: yes | Regen: yes, GPU | Disjoint from batch2/final_validation (verified by ID intersection) |
| NAT-03 | Natural batch2 (n=50) | `outputs/natural_candidates_batch2_gpu_{bare,labeled}.jsonl` | metric-only, natural | real generation | 50 cases | Yes | METRIC-ONLY | No | Yes | No | Regen: yes | Regen: yes, GPU | Disjoint (verified) |
| NAT-04 | Final validation batch (n=50) | see MET-02 | metric-only, natural | real generation | 50 cases / 209 claims | Yes | METRIC-ONLY | No | Yes | No | Regen: yes | Regen: yes, GPU | Disjoint (verified) |
| ADV-01 | Adversarial citation cases | `research/prototype/tests/test_adversarial_citations.py` | behavioral test, inline fixtures | hand-constructed | 15 test functions | Yes | BEHAVIOR | No (Cat. B, not Cat. A) | No | No | No | Yes, `pytest` | 7 adversarial categories |
| ADV-02 | Final-pass adversarial cases | `research/prototype/tests/test_final_pass_adversarial.py` | behavioral test, inline fixtures | hand-constructed + 1 real defect regression | 10 test functions | Yes | BEHAVIOR | No | No | No | No | Yes, `pytest` | |
| ADV-03 | Respectively-claims structural tests | `research/prototype/tests/test_respectively_claims.py` | behavioral test, inline fixtures | hand-constructed | 16 test functions | Yes | BEHAVIOR | No | No | No | No | Yes, `pytest` | |
| COR-01 | Correction/sibling-safety detail (final_gpu_validation) | `outputs/final_gpu_validation_corrections_detail.jsonl` | metric-only, natural | real corrections | 10 | Yes | METRIC-ONLY | No | Yes | No | Regen: yes | Regen: yes, GPU | 0 sibling regressions recorded |
| COR-02 | Correction/sibling-safety detail (labeled validation) | `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl` | metric-only, natural | real corrections | 10 | Yes | METRIC-ONLY | No | Yes | No | Regen: yes, ~2 min | Regen: yes, GPU | 0 sibling regressions recorded |
| COR-03 | Correction/sibling-safety detail (batch1) | `outputs/natural_candidates_50_gpu_corrections_detail.jsonl` | metric-only, natural | real corrections | 21 | Yes | METRIC-ONLY | No | Yes | No | Regen: yes | Regen: yes, GPU | Source of the 4/6-unblocked scope-check finding |
| ABL-01 | Threshold-sensitivity sweep | `outputs/threshold_sensitivity_analysis.json`/`.md` | ablation, deterministic replay | replays GOLD-01's stored softmax | N/A (sweep over 420) | Yes | derived from GOLD (indirect) | Indirect | No | **Yes** | No | Yes, CPU-only, no re-inference | `scripts/analyze_threshold_sensitivity.py` |
| ABL-02 | Scope-check-mode replay (3-stage) | `outputs/atomic_scope_check_replay.json` → `_v2` → `_final_replay.json` | ablation, deterministic replay | replays COR-01/COR-03 | N/A | Yes | METRIC-ONLY | No | No | **Yes** | No | Yes, CPU-only, no re-inference | Final-stage finding is weak/inconclusive (1/11 vs 4/6, unreconciled) |
| CFG-01 | Production config | `research/prototype/config/prototype.yaml` | config | hand-authored, evidence-cited | N/A | Yes | N/A | No | No | No | No | Yes (static file) | SHA-256 `dcbc1dc6525659d871bb911f474337f06e88d99d08ef42d1c97ee7d49c73b630`; locked by `tests/test_premise_framing_production.py` |
| PROV-01 | Provisional annotations (excluded) | `outputs/gold_annotation.jsonl`, `lawyer_annotation.jsonl`, `assumption_annotation.jsonl` | provisional, excluded | Claude-generated | 88 + 88 + 88 | Yes | **PROVISIONAL — never gold** | No | No (never as accuracy) | No | No | Yes (static files) | Self-tagged `NOT_LAWYER_VERIFIED`; deliberately excluded from `expected_outputs/`, see `inputs/README.md` |

## Selection-file hashes (natural-batch disjointness fixtures)

| File | SHA-256 |
|---|---|
| `outputs/natural_candidate_selected_ids_30.json` | `182b45703c8efdf1d871d8be2fb2ff4222b6cb72f90b0bf6a0f54fc329d4f3cb` |
| `outputs/natural_candidate_selected_ids_50.json` | `ba0458778b2e76a50df54cc2d78f04ba5a25fc41fa2921ad78d363b3da3d3d09` |
| `outputs/natural_candidate_selected_ids_50_batch2.json` | `4e65d310fefd9f458546f1bc50c99dc85026d4b51a343c747ef7f05ee4ff7828` |
| `outputs/natural_candidate_selected_ids_50_final_validation.json` | `954380e7695ceead984d67e7029186074a9ffd95130f02d17b01ea08d9877f9a` |
| `research/prototype/config/prototype.yaml` | `dcbc1dc6525659d871bb911f474337f06e88d99d08ef42d1c97ee7d49c73b630` |

Large generated-output files (`final_gpu_validation_A/B.jsonl` at ~440KB each, the
natural-batch `*_gpu_*.jsonl` files) and all model weights are intentionally **not**
hashed here — per this step's instruction to hash small immutable fixtures only, not
large files. Their identity is tracked by git, not by this manifest.

## Test-file inventory (see `components/README.md` for per-stage mapping)

11 files, `research/prototype/tests/`: `conftest.py` (no tests, path setup),
`test_adversarial_citations.py` (15), `test_candidate_selection.py` (7),
`test_claim_parser_and_evidence_matcher.py` (50),
`test_claim_parser_bugfixes.py` (20), `test_controlled_benchmark.py` (23),
`test_correction_path_real_integration.py` (3, real DeBERTa model),
`test_final_pass_adversarial.py` (10), `test_pipeline_mock.py` (34),
`test_premise_framing_production.py` (17), `test_respectively_claims.py` (16),
`test_verifier_benchmark.py` (2, unittest-style). Raw `def test_` count ≈197; documented
205-passed count includes parametrized cases counted separately by pytest.
