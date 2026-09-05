# Provenance

**Workspace created**: 2026-09-05
**Repository commit at creation**: `ccbe73f3c6c504c4f7d84cd8e8c9c128397f56a3` ("Readme updated")
**Created by**: STEP 1 of a two-step process — STEP 0 was a read-only deep technical
audit of the repository (pipeline trace, dataset inventory, test/script inventory,
figures/reports audit); this workspace operationalizes STEP 0's findings into a
presentable, reproducible structure without altering anything STEP 0 examined.

## Lineage

```
Original NyayaMind pipeline design (approved v0 design doc)
    |
    v
Historical implementation + data
    (research/data/evidence/ v0 corpus, first natural-batch runs,
     pre-2026-08-27 default config: use_evidence_v1=false, premise_framing=bare,
     atomic_scope_check=false, narrow_reverification_hypothesis=false)
    |
    v
Current production implementation
    (research/prototype/src/, research/prototype/config/prototype.yaml
     as of 2026-08-27: use_evidence_v1=true, premise_framing=labeled,
     atomic_scope_check="assertion_spans", narrow_reverification_hypothesis=true —
     see FINAL_PRODUCTION_CONFIG.md for the full decision record)
    |
    v
final_demo_pack/ + final_comparison/
    (presentation and within-project original-vs-current comparison layers,
     built 2026-08-27, both frozen)
    |
    v
research/prototype/testing/  <-- this workspace
    (a new evaluation/presentation layer, built 2026-09-05, referencing everything
     above rather than replacing it)
```

## What this workspace is not

It is **not** a replacement for `research/prototype/outputs/`,
`research/prototype/final_demo_pack/`, or `research/prototype/final_comparison/`. Those
remain the authoritative historical record and are frozen (read-only) sources for
everything built here. Where this workspace reproduces a number, it reproduces it from
those sources and says so; it never invents a new number that cannot be traced back to
one of them, a fresh run's own metadata, or one of the two true-gold datasets in
`expected_outputs/`.

## Historical outputs are intentionally preserved

No file under `research/data/`, `research/prototype/outputs/`,
`research/prototype/final_demo_pack/`, `research/prototype/final_comparison/`,
`research/prototype/tests/`, `research/prototype/src/`, or
`research/prototype/config/prototype.yaml` was modified, deleted, or moved while building
this workspace. See the final validation section of the STEP 1 completion report (in the
conversation, and reproducible via the `git status`/`git diff --stat` commands below) for
direct confirmation.

## Known limitations carried forward from STEP 0 (first-class, not buried)

1. **No single experiment combines all four current production-config levers
   (`use_evidence_v1`, `premise_framing`, `atomic_scope_check`,
   `narrow_reverification_hypothesis`) in one fresh generation pass.** The strongest
   existing evidence for "current beats original" is a 4-experiment chain on the same
   50-case batch, not one joint run.
2. **The correction-shipping-rate improvement (5→10 triggered, 0→1 shipped) is not
   statistically significant** at this sample size (Wilson confidence intervals overlap
   almost entirely) — report it as directional only, never as a proven effect.
3. **The scope-check-mode ablation is unreconciled**: the final, most complete replay
   found only 1 of 11 real scope violations unblocked by `assertion_spans`, contradicting
   an earlier, batch-1-only finding of 4/6 unblocked. Both numbers are real; neither
   supersedes the other in the existing record.
4. **v1 evidence audit coverage is partial**: 50% of the 82 v1 records were independently
   re-fetched as of the 2026-08-27 audit addendum (up from the original build's 10%); the
   remaining 32/82 rest on build-time provenance only.
5. **No human/lawyer ground truth exists anywhere in this project.** `gold_annotation.jsonl`,
   `lawyer_annotation.jsonl`, and `assumption_annotation.jsonl` are Claude-generated,
   self-tagged provisional labels — see `inputs/README.md`'s exclusion note.
6. **Discovered in STEP 1, resolved (partially) in STEP 2**: `research/.venv/` did not
   exist in this checkout. STEP 2 found that Python 3.11.9 (the exact pinned version) was
   already present on this machine at a non-default path, created the venv with it, and
   installed `research/requirements.txt` with **zero version substitutions** — full
   success, exit code 0, and the complete test suite subsequently passed **205/205**, an
   exact match to `REPRODUCIBILITY.md`'s documented result. See
   `actual_outputs/step2_environment_setup/ENVIRONMENT_REPRODUCIBILITY_RESULT.md` for the
   full evidence. **However, STEP 2 also found a deeper, hardware-level blocker that
   remains unresolved and cannot be worked around**: this machine has no NVIDIA GPU (an
   AMD Radeon integrated GPU only, confirmed via Windows WMI and independently via
   `torch.cuda.is_available() == False`). `src/generator.py` and `src/corrector.py`
   hard-require CUDA with no CPU fallback by design, so **no real Qwen-7B generation or
   correction can run on this machine at all**, regardless of environment setup quality.
   Every CPU-only claim in this project (tests, controlled-benchmark verification,
   threshold sweeps, scope-check replays, CPU-only re-verification scripts) is now
   independently, freshly confirmed reproducible on this machine; every GPU-only claim is
   not reproducible here and would require different hardware.
7. **A root-level "Project Author Statement — 2026-09-03"** (referenced from every
   `final_demo_pack` document) claims professional legal review was "incorporated," with
   no reviewer identities or records included in the repository. This is an unverifiable,
   out-of-band annotation layered on top of the otherwise rigorously-sourced research —
   this workspace treats it as exactly that, never as evaluable data, and does not cite
   it as evidence anywhere.

## STEP 3 — Input layer built and validated (2026-09-05)

**Environment used**: the exact venv established in STEP 2 —
`research/.venv/Scripts/python.exe`, Python 3.11.9, all packages at their pinned versions.

**Datasets inspected** (Phase 1 of STEP 3): the two GOLD fixtures; the v0/v1/merged
evidence corpus; the 588-claim derived aggregate; the 209-claim paired evaluation; all
four natural batches; three correction/safety detail files; four BEHAVIOR test-fixture
files; three PROVISIONAL annotation files; the NyayaRAG case source; and
`final_demo_pack`/`final_comparison`'s example/config compilations. Full detail in
`inputs/INPUT_MANIFEST.md`.

**Datasets selected as fresh testing inputs**: only the two already-copied GOLD fixtures
(no new copies made). Everything else is referenced in place — evidence corpus,
NyayaRAG source, all natural/metric-only batches, all BEHAVIOR test fixtures, and all
PROVISIONAL annotation files — per this step's explicit instruction to prefer referencing
over duplicating already-clean, already-frozen data.

**Datasets excluded from GOLD status, and why**: every natural-data artifact (588
aggregate, 209 paired, all natural batches, correction/safety detail files) — none has an
independently-derived label, only the system's own historical output. The three
provisional annotation files — self-tagged `CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED`,
explicitly excluded per this step's rule 7. No new ground truth was created, inferred, or
manufactured for any of these, per this step's rule 5.

**Record counts and hashes**: see `inputs/INPUT_MANIFEST.md` and
`actual_outputs/step3_input_validation/validate_inputs_report.txt` for the full,
independently-verified set (38 checks, all passed): GOLD-01 = 420 (hash
`962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99`, byte-identical to
source), GOLD-02 = 59 (hash
`2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516`, byte-identical to
source), v0 evidence = 63/63, v1 evidence = 82/82, merged usable pool = 136 (live-verified
via `load_usable_evidence_from_config`), all referenced natural/correction files at their
documented counts, all four BEHAVIOR test files at or above their documented test-function
counts, and — critically — zero provisional-annotation files or tags found anywhere under
`expected_outputs/` or `inputs/gold/`.

**Classifications**: GOLD (2 datasets, n=420 + n=59), BEHAVIOR (4 test files, ~61 test
functions), METRIC-ONLY (588 aggregate, 209 paired, 4 natural batches, 3 correction/safety
files), PROVISIONAL (3 annotation files, 88 records each), HISTORICAL-ONLY
(`final_demo_pack`/`final_comparison` example/config compilations), and N/A-input-corpus
(evidence corpus, NyayaRAG case source — genuinely unlabeled retrieval/generation inputs,
not forced into one of the four classifications). None of the four preserved
classifications from STEP 1 was weakened, removed, or reclassified.

**Validation command**:
```
research/.venv/Scripts/python.exe research/prototype/testing/validate_inputs.py
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
```

**Validation result**: `validate_inputs.py` — 38/38 checks passed, 0 warnings, 0
failures. `pytest` regression check — **205 passed**, identical to STEP 2's result, no
test modified, no regression.

**Timestamp**: 2026-09-05.

**Unresolved ambiguity carried forward**: none newly introduced by STEP 3. The
`evaluation/` vs. `comparisons/metric_based/` ownership question and the synthetic-set
integration-test placement question (both flagged in STEP 1) remain open and are
unaffected by this step, which built and validated inputs only — no evaluation, ablation,
or comparison was run.

## STEP 4 — First expected-vs-actual comparison run (2026-09-05)

**What was executed**: the real, unmodified `src/verifier.py::NLIVerifier`
(MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli, `device="cpu"`) against both GOLD
fixtures, under both `premise_framing` values (`labeled` = actual production config;
`bare` = secondary reference arm). No Qwen generation or correction was invoked — this
machine has no NVIDIA GPU (STEP 2). Two new runner scripts
(`testing/run_gold01_evaluation.py`, `testing/run_gold02_evaluation.py`) call the real
verifier/pipeline functions directly; a shared helper (`testing/step4_common.py`)
reimplements only the generic confusion-matrix arithmetic.

**A genuine blocker was found and is documented, not hidden**:
`scripts/run_controlled_benchmark.py` — this project's own existing GOLD-01 evaluation
script — **cannot be imported under this project's own pinned Python 3.11.9**
(`SyntaxError: f-string expression part cannot include a backslash`, a Python
3.12+-only construct at its `fmt_confusion()` function; confirmed via direct `py_compile`
under both 3.11.9 and 3.14). This is independently corroborated by the historical
results themselves: `outputs/controlled_benchmark_deberta_metrics.json`'s own recorded
`environment` field reads `{"python": "3.13.1", "torch": "2.13.0+cpu", "transformers":
"5.15.1"}` — **the historical GOLD-01 results were never actually produced under this
project's documented Python 3.11.9 / torch==2.2.2+cu121 pin at all**, contrary to what
`REPRODUCIBILITY.md` states. This is a genuine, pre-existing project reproducibility gap
that STEP 4 did not introduce and is not authorized to fix (doing so would mean modifying
`scripts/run_controlled_benchmark.py`, outside `testing/`). See
`step4_common.py`'s module docstring for the full technical detail and the resolution
adopted (call the real verifier/premise-construction functions directly; reimplement
only the confusion-matrix arithmetic, which is standard tp/fp/fn math, not model logic).
`scripts/compare_premise_framing_synthetic.py` (GOLD-02's existing evaluation script) has
no such issue and was imported and reused directly, unmodified.

**Exact inputs and hashes**: GOLD-01 = `controlled_verifier_benchmark.jsonl`, n=420, sha256
`962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99` (re-verified before
inference, matching STEP 3's recorded hash exactly). GOLD-02 =
`run_synthetic_stress.jsonl`, n=59, sha256
`2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516` (re-verified before
inference, matching STEP 3's recorded hash exactly). GOLD-02 additionally underwent a
full re-derivation check: the 59
synthetic claims were freshly rebuilt from the v0 evidence pool via
`build_synthetic_stress_claims()` and confirmed to match the frozen fixture's stored
fields exactly, before any inference was run.

**Model / configuration**: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`,
`confidence_threshold=0.70`, `max_sequence_length=512` — all read unmodified from
`config/prototype.yaml`. No threshold, model, or preprocessing was changed.

**Results (fresh, mechanically computed — see `comparisons/expected_vs_actual/` for full detail)**:

| Dataset | Framing | N | Accuracy / Contradiction Recall | Macro F1 |
|---|---|---|---|---|
| GOLD-01 | labeled (production) | 420 | 0.9714 | 0.9684 |
| GOLD-01 | bare | 420 | 0.7333 | 0.7487 |
| GOLD-02 | labeled (production) | 59 | 0.4576 | 0.2535 (all-3-label) / 0.6279 (CONTRADICTED-only) |
| GOLD-02 | bare | 59 | 0.3559 | 0.2154 (all-3-label) / 0.5250 (CONTRADICTED-only) |

**Historical cross-check**: GOLD-01 reproduced **bit-for-bit identically** (both
confusion matrices, both framings) despite the environment discrepancy noted above.
GOLD-02 reproduced the historical overall and evidence-matched contradiction-recall
percentages (35.6%/45.8% overall, 47.7%/61.4% evidence-matched) to the historical
report's own stated precision. Full detail in
`comparisons/expected_vs_actual/HISTORICAL_CROSSCHECK.md`.

**Actual output locations**: `testing/actual_outputs/step4_gold_verifier/gold01_controlled/`,
`.../gold02_synthetic/`, `.../run_metadata/`, `.../logs/`.
**Expected-output locations**: unchanged from STEP 1/3 —
`testing/expected_outputs/controlled_benchmark_gold/`,
`testing/expected_outputs/synthetic_stress_gold/`.
**Comparison artifacts**: `testing/comparisons/expected_vs_actual/{gold01,gold02}_expected_vs_actual.csv`,
`gold_verifier_summary.csv`, `EXPECTED_VS_ACTUAL_REPORT.md`, `HISTORICAL_CROSSCHECK.md`.

**Validation**: `testing/validate_step4_outputs.py` — **38/38 checks passed**, including
an explicit check that the two historical `controlled_benchmark_deberta*_metrics.json`
files still show their original (`3.13.1`) environment signature (i.e. were not
overwritten by this step's runs) and that `run_synthetic_stress.jsonl`'s hash is
unchanged in `research/prototype/outputs/`.

**Regression check**: `pytest research/prototype/tests/ -q` — **205 passed**, identical
to STEP 2/3, no test modified, no regression.

**Hardware limitation**: NVIDIA GPU available = **NO** (unchanged from STEP 2), recorded
explicitly and machine-readably in both `gold01_run.meta.json` and
`gold02_run.meta.json`. No GPU execution is claimed anywhere in this step's artifacts.

**Deviation from the literal STEP 4 Phase 2 wording, documented rather than silently
worked around**: GOLD-02 (`run_synthetic_stress.jsonl`) has no literal `expected_label`
field (unlike GOLD-01). Its expected label is CONTRADICTED-by-construction for every
record, per `src/synthetic_stress.py`'s own module docstring. This runner verified this
claim's reproducibility directly (re-deriving all 59 claims from source and confirming
an exact field-for-field match against the frozen fixture) rather than inventing or
reading a field that does not exist.

**Timestamp**: 2026-09-05. **Environment**: `research/.venv`, Python 3.11.9 (unchanged
from STEP 2). **Git commit at run time**: `ccbe73f3c6c504c4f7d84cd8e8c9c128397f56a3`.

## STEP 5 — Component-level testing and behavior verification (2026-09-05)

**Test groups executed** (7, mapped to the pipeline stages from STEP 0/3): claim parser,
evidence matcher, verifier, verdict application, citation identity/adversarial safety,
correction scope/safety gates, final assembly/integration. Every test executed is a
**pre-existing, unmodified** test from `research/prototype/tests/` — no new test cases
were added; see `component_tests/TEST_INVENTORY.md` for the exact file/test-name mapping.

**Source test files**: `test_claim_parser_and_evidence_matcher.py`,
`test_claim_parser_bugfixes.py`, `test_respectively_claims.py`,
`test_final_pass_adversarial.py`, `test_adversarial_citations.py`,
`test_candidate_selection.py`, `test_controlled_benchmark.py`,
`test_premise_framing_production.py`, `test_pipeline_mock.py`,
`test_correction_path_real_integration.py` (all 11 files in the suite except
`test_verifier_benchmark.py`, which tests the non-production `llm_verifier.py`).

**Inputs**: hand-constructed adversarial fixtures, real verbatim Qwen-output sentences
(`gold_annotation.jsonl`), the real v0/v1 evidence corpus, and — for the concrete
representative demonstrations — the exact same `FakeGenerator`/`ScriptedCorrector`
fixtures `test_correction_path_real_integration.py` already uses. A new script,
`testing/run_step5_component_demos.py`, re-runs these same real functions (never new
logic) to capture concrete input/output pairs for the faculty-review question; it is a
demonstration script, not a new test suite.

**Expected-behavior source**: exclusively existing unit/integration test assertions and
documented software invariants (Category B per `expected_outputs/README.md`) — no new
legal ground-truth label was created, and no BEHAVIOR/METRIC-ONLY/PROVISIONAL artifact
was promoted to GOLD (verified by the validator below).

**Actual output locations**: `testing/actual_outputs/step5_components/0N_*/`
(`pytest_execution.log`, `demo_examples.json`) and `full_suite_verbose.log`
(single source of truth for all pass/fail counts).

**Environment / model**: `research/.venv`, Python 3.11.9, unchanged from STEP 2-4. Real
model used where applicable: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`,
`device="cpu"`. **No Qwen generation or correction was invoked anywhere in this step** —
`nvidia_gpu_available: false` recorded explicitly in
`actual_outputs/step5_components/run_metadata.json`.

**Results**: 205/205 full-suite regression (identical to STEP 2-4, no change). Per-group:
01=111/111, 02=72/72, 03=48/48, 04=3/3, 05=15/15, 06=35/35 (32 mocked + 3 real-model),
07=5/5 (2 mocked + 3 real-model) — **0 failures anywhere**, so no component-specific
divergence from the overall suite result needed investigation.

**Skipped GPU-dependent work**: real Qwen generation (pipeline stage 1) and real Qwen
correction-text generation (part of stage 6) — both require an NVIDIA GPU this machine
does not have. Substituted by `FakeGenerator`/`ScriptedCorrector` exactly as
`test_correction_path_real_integration.py` already does; explicitly marked
`gpu_generation_executed: false` in every relevant artifact.

**Validation**: `testing/validate_step5_components.py` — **37/37 checks passed**,
including confirmation that both GOLD fixtures are unchanged since STEP 3/4, no
provisional annotation file or tag appears under any GOLD-designated location, and the
two historical `controlled_benchmark_deberta*_metrics.json` files still show their
original (unmodified) `3.13.1` environment signature.

**Regression result**: `pytest research/prototype/tests/ -q` — **205 passed**, identical
to STEP 2-4, no test modified.

**Unresolved ambiguity carried forward**: none newly introduced. The `evaluation/` vs.
`comparisons/metric_based/` ownership question (STEP 1) remains open and is unaffected
by this step, which performed component-level testing only.

## STEP 6 — Natural-data metric-only evaluation (2026-09-05)

**Datasets used** (no substitution — exact datasets from `inputs/INPUT_MANIFEST.md`):
588-claim natural aggregate (133 distinct texts from the same 4 source files
`scripts/measure_evidence_coverage_v0_vs_v1.py` uses), the 209-claim paired set
(`outputs/final_gpu_validation_{A,B}.jsonl`), and 8 natural-batch regimes (n=30,
targeted, batch1 bare/labeled, batch2 bare/labeled, final_validation Arm A/B as
originally stored). Full inventory: `evaluation/NATURAL_DATA_INVENTORY.md`.

**Input hashes / record counts**: verified before any inference via
`testing/verify_step6_input_integrity.py` — **zero discrepancies found** across 12
source files (4 with hashes carried over from STEP 3, matching exactly; 8 new baselines
recorded fresh this step). Full report: `evaluation/input_integrity/hash_report.json`.

**Exact commands**:
```
research/.venv/Scripts/python.exe research/prototype/testing/verify_step6_input_integrity.py
research/.venv/Scripts/python.exe research/prototype/testing/run_step6_588_evaluation.py
research/.venv/Scripts/python.exe research/prototype/testing/run_step6_209_paired_evaluation.py
research/.venv/Scripts/python.exe research/prototype/testing/analyze_step6_natural_batches.py
research/.venv/Scripts/python.exe research/prototype/testing/validate_step6_natural_data.py
```

**Configuration**: current production config (`config/prototype.yaml`) used throughout
for all fresh work, per this step's rule 15 — `premise_framing=labeled`,
`use_evidence_v1=true` (136-record pool), `confidence_threshold=0.70`, all unchanged.
Where a comparison explicitly required the original configuration (the 209-claim Arm A
vs. Arm B comparison), both configurations are recorded explicitly in
`NATURAL_DATA_INVENTORY.md` and every output file's own metadata — never silently mixed.

**Model**: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, `device="cpu"`, real,
unmodified. No Qwen generation or correction was invoked anywhere in this step.

**Fresh execution stages**: claim parsing + evidence matching (current v0+v1 pool) + real
DeBERTa verification for all 588 claims; evidence re-matching (Arm A against its own
original v0-only pool, Arm B against the current v0+v1 pool) + real DeBERTa
re-verification (current labeled framing) for all 209×2 paired claims.

**Historical-only stages**: all 8 natural-batch regimes' verdicts (tabulated, not
re-derived); the 209-pair's `historical_*` columns (as originally stored, Arm B under
bare framing).

**GPU limitation**: NVIDIA GPU available = NO (unchanged). Full detail, including the
explicit A/B/C stage separation this step's rules require:
`evaluation/GPU_LIMITATIONS.md`.

**Metrics**: 588-claim evidence coverage 66.3% (390/588) — **exact bit-for-bit
reproduction** of the historical `outputs/evidence_coverage_v0_vs_v1.json` figure.
209-claim paired evidence coverage 63.2%→70.3%, McNemar χ²=13.0667, p=0.000301 — **exact
reproduction** of the historical `outputs/final_gpu_validation.md` figures (χ²=13.07,
p≈0.0003), freshly recomputed this run, not merely cited. Arm B's fresh
labeled-framing verdict distribution (131 NEI / 13 ENTAILED / 3 CONTRADICTED, of 147
evidence-matched claims) **exactly matches** `outputs/final_validation_bare_vs_labeled_cpu_metrics.json`'s
`labeled_verdict_counts` field, bit-for-bit. Full cross-check:
`evaluation/HISTORICAL_CROSSCHECK_NATURAL.md`.

**Paired analysis**: `evaluation/paired_209_analysis.csv`,
`evaluation/PAIRED_209_REPORT.md` — evidence gained (15), lost (0), unchanged (194);
verdict changes strictly confined to the 15 evidence-gained claims; zero verdict changes
among claims that already had evidence in Arm A.

**Terminology audit**: performed across every new STEP 6 report (Phase 11) — no
unsupported "accuracy"/"precision"/"recall"/"F1"/"ground truth"/"correctness" usage
found; every match was a legitimate negation/disclaimer, confirmed by the validator's
own automated check (with two of my own regex false-positives caught and fixed before
finalizing — see PROBLEMS section of this step's final report to the user).

**Validation**: `testing/validate_step6_natural_data.py` — **33/33 checks passed**,
including confirmation that all source hashes are unchanged, no GOLD/provisional
contamination occurred, aggregate metrics reconcile with row-level data, the 209-pairing
is correctly aligned, and no record was silently dropped.

**Regression result**: `pytest research/prototype/tests/ -q` — **205 passed**, identical
to STEP 2-5, no test modified.

**Deviations**: none from the assigned methodology. Two self-caught, self-fixed issues
in my own validator script (a regex false-positive on "stated precision," and a Windows
console Unicode encoding crash on a χ character) were found and corrected before
finalizing — neither affected any reported natural-data metric.

## STEP 7 — Ablation analysis and causal contribution (2026-09-05)

**Experiments inspected**: every ablation-relevant artifact in `research/prototype/`,
`testing/`, `final_comparison/`, `final_demo_pack/`, `tests/`, and `src/` for 8 factor
groups (evidence v0-vs-v1, premise framing, claim parser fix, atomic scope check, narrow
re-verification, confidence threshold, correction levers, joint four-lever isolation).
Full inventory: `evaluation/ABLATION_INVENTORY.md`.

**Experiments freshly reproduced this step**:
1. Evidence v0-vs-v1 (209-claim paired) — cited unchanged from STEP 6's own fresh result.
2. Premise framing (GOLD-01, n=420) — both arms cited from STEP 4; a **new** McNemar
   test (χ²=98.01, p=4.16e-23) and exact sign test (p=1.5777e-30) computed fresh this
   step directly from the paired per-item predictions — the sign test exactly matches
   `final_comparison/tables/statistical_tests.csv`'s independently-computed 1.58e-30.
3. Atomic scope check (assertion_spans) — the scope-check replay logic was **re-executed
   fresh** this step via the real, unmodified `pipeline._scope_violation` and
   `claim_parser.extract_claims`, output written to
   `testing/actual_outputs/step7_ablation/scope_check_replay_fresh.json`, and confirmed
   to match the historical committed replay (`outputs/atomic_scope_check_final_replay.json`)
   exactly (11 replayed, 1 unblocked).
4. Claim parser fix sign test (6 improved/0 worsened/24 unchanged, p=0.03125) —
   recomputed fresh this step directly from the raw per-case data in
   `outputs/parser_fix_before_after_n30.json`, exactly matching
   `final_comparison/tables/statistical_tests.csv`'s independently-reported figures.
5. Confidence threshold peak-vs-production analysis — recomputed fresh this step
   directly from `outputs/threshold_sensitivity_analysis.json`'s stored sweep (no
   re-inference).

**Historical-only experiments** (not re-executed, explicitly marked): narrow
re-verification (cited from `FINAL_PRODUCTION_CONFIG.md` §4 and
`outputs/research_completion_report.md` §17c — narrative only, not re-derivable from raw
per-case data without ambiguity); correction levers targeted comparison
(`outputs/labeled_correction_validation_gpu_metrics.json` — GPU-dependent, real Qwen
correction calls, not reproducible on this machine); the cumulative 1/56 (1.8%)
correction rate (`outputs/final_metrics.json`).

**Datasets**: GOLD-01 controlled benchmark (n=420), 209-claim paired natural set,
n=30 parser reparse, n=11 scope-violation replay, n=3 narrow-reverification cases —
none promoted or demoted in classification; GOLD/BEHAVIOR/METRIC-ONLY/HISTORICAL/
PROVISIONAL distinctions from STEP 1 preserved throughout.

**Configuration**: production config unchanged throughout —
`confidence_threshold=0.70`, `use_evidence_v1=true`, `premise_framing=labeled`,
`atomic_scope_check="assertion_spans"`, `narrow_reverification_hypothesis=true` — no
value was retuned or changed at any point in this step, confirmed by the validator.

**Exact commands**:
```
research/.venv/Scripts/python.exe research/prototype/testing/build_step7_ablation_analysis.py
research/.venv/Scripts/python.exe research/prototype/testing/validate_step7_ablation.py
```

**Statistical tests** (test, null hypothesis, n, paired, statistic, p-value — full detail
in `evaluation/ABLATION_SUMMARY.json`):
- Evidence v1: McNemar χ²=13.067 p=0.000301; exact sign test p=6.10e-05. n=209, paired.
- Premise framing: McNemar χ²=98.01 p=4.16e-23; exact sign test p=1.58e-30. n=420, paired.
- Claim parser: exact sign test p=0.03125. n=30, paired (document-level).
- No test performed for atomic scope check (n=11, descriptive), narrow re-verification
  (n=3, descriptive), confidence threshold (descriptive sweep, not a hypothesis test),
  or correction levers (n too small). No multiple-comparison correction was applied
  anywhere — each test is a single, pre-specified, non-exploratory comparison
  reproducing this project's own existing methodology.

**Classification of every lever**: evidence v1 = SUPPORTED (grade A); premise framing
(controlled benchmark) = SUPPORTED (grade A); premise framing (natural, 147-claim) =
grade B; claim parser fix = SUPPORTED (grade B); confidence threshold = DESCRIPTIVE
(grade B); atomic scope check = DIAGNOSTIC (grade C); narrow re-verification =
DIAGNOSTIC (grade C); correction levers (targeted) = DIAGNOSTIC (grade C); joint
four-lever isolation = NOT_ISOLABLE (grade E, does not exist). Full detail:
`evaluation/ABLATION_EVIDENCE_GRADES.md`, `evaluation/ABLATION_RESULTS.md`.

**Limitations**: joint four-lever causal isolation was not performed anywhere in this
project's history, including this step — stated prominently, per this step's explicit
requirement, in `evaluation/ABLATION_RESULTS.md` and `ABLATION_FACULTY_SUMMARY.md`. No
additive or interaction effect between the four current production levers can be
inferred from the available data.

**GPU limitation**: NVIDIA GPU available = NO (unchanged). No Qwen generation or
correction was invoked in this step; the one GPU-dependent historical experiment
touched (targeted correction-levers comparison) is explicitly marked HISTORICAL with
`gpu_execution_claimed_this_step: false`, never described as fresh.

**Terminology audit**: every occurrence of "caused"/"proved"/"correctness"/"accuracy"/
"ground truth"/"lawyer"/"legal accuracy"/"solved"/"significant"/"improvement" across all
new STEP 7 files was manually reviewed (Phase 17); all 14 occurrences found were
legitimate (GOLD-benchmark-scoped accuracy language, rubric definitions, or explicit
negations inside "what we cannot claim" columns) — none required correction. Two
false-positives in the automated validator's own regex (a "solved"/"cannot claim"
table-column collision) were found and fixed before finalizing.

**Validation**: `testing/validate_step7_ablation.py` — **50/50 checks passed**,
including confirmation that every SUPPORTED classification has a genuine, documented
isolating comparison, the production configuration and threshold are unchanged, no
GOLD/provisional contamination occurred, and all machine-readable summaries agree with
the markdown tables.

**Regression result**: `pytest research/prototype/tests/ -q` — **205 passed**, identical
to STEP 2-6, no test modified.

## STEP 8 — Consolidated evaluation and figure-ready results (2026-09-05)

**Not a new experiment.** This step introduced no new methodology, tuning, label,
dataset, model, hyperparameter, or ablation condition — it consolidates STEP 4-7's
already-validated results into one cross-referenced, figure-ready package.

**Canonical sources** (9 files, read-only, never modified): STEP 4's
`gold01_metrics.json`/`gold02_metrics.json`; STEP 6's `claims_588_metrics.json`,
`paired_209_metrics.json`, `batches_analysis.json`; STEP 7's `ABLATION_SUMMARY.json`;
and 3 historical project artifacts inspected (not modified) —
`outputs/final_metrics.json`, `outputs/labeled_correction_validation_gpu_metrics.json`,
`outputs/final_gpu_validation_metrics.json`, `outputs/final_validation_bare_vs_labeled_cpu_metrics.json`.
`research/prototype/final_comparison/` and `final_demo_pack/` were inspected only as
reference/cross-check sources, never modified and never used as a primary source for
any new number. Full map: `evaluation/CONSOLIDATION_SOURCE_MAP.md`.

**Metrics consolidated**: 16 canonical metrics (`CANONICAL_METRICS.{json,csv}`), 7
original-vs-current rows, 9 evidence-strength-graded conclusions, 3 statistical test
results, a 3-population correction funnel (synthetic/natural-targeted/natural-cumulative,
kept strictly separate), a 5-row safety summary, and a 7-group component test matrix.

**Figure-data files** (11, Phase 11, no PNGs generated): `evaluation/figure_data/01_overall_metric_comparison.csv`
through `11_synthetic_vs_natural_transfer.csv` — every row source-declared, every numeric
value traced to a STEP 4-7 or historical-project artifact, verified by
`validate_figure_data.py`.

**Validation commands and results**:
```
research/.venv/Scripts/python.exe research/prototype/testing/build_step8_consolidation.py
research/.venv/Scripts/python.exe research/prototype/testing/validate_step8_consolidation.py   -> PASS, 75/75 checks
research/.venv/Scripts/python.exe research/prototype/testing/validate_figure_data.py           -> PASS, 54/54 checks
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q                        -> 205 passed
```

**Discrepancies found**: **none.** All 26 specific headline values named in this step's
instructions (63.2%, 70.3%, 15 gains, 0 losses, χ²=13.0667, p=0.000301, 0.7487, 0.9684,
0.7333, 0.9714, 98.01, 4.16e-23, 1.5777e-30, 6/30, 0/30, p=0.03125, 66.3%, 390/588, 364
NEI, 198 NO_EVIDENCE, 21 ENTAILED, 5 CONTRADICTED, 0/5→1/10, 1/56, 0 unsafe, 205/205)
were mechanically reconciled exactly against their canonical source artifacts — see
`evaluation/CONSOLIDATED_CONSISTENCY_REPORT.md` for the full reconciliation table. Two
minor gaps in my own first-draft figure-data files (missing `source` columns on two of
the eleven CSVs) were found by `validate_figure_data.py` and fixed before finalizing —
neither affected any numeric value.

**Limitations**: identical to STEP 7's — no joint four-lever causal isolation exists;
narrow re-verification and the targeted correction-levers comparison remain diagnostic;
no legal ground truth exists anywhere in this project; this machine has no NVIDIA GPU
and no Qwen generation/correction was invoked at any point in this workspace.

**No methodology change**: production config, confidence threshold (0.70), and every
GOLD/BEHAVIOR/METRIC-ONLY/PROVISIONAL classification remain exactly as established in
STEP 1-7 — confirmed explicitly by `validate_step8_consolidation.py`.

## STEP 9 — Final figure generation and visual audit (2026-09-05)

**Not a new experiment.** No numerical result was computed, changed, or reinterpreted
in this step — every plotted value is read directly from STEP 8's locked
`evaluation/figure_data/*.csv` contracts.

**New dependency installed**: `matplotlib==3.11.1` (matching `final_demo_pack`'s own
pinned version) and `Pillow` (for the image audit), installed into the same
`research/.venv` established in STEP 2 — neither was in the base `requirements.txt`,
which `final_demo_pack/RUNBOOK.md` had already flagged as a pre-existing gap.

**Figure-data sources**: all 11 `evaluation/figure_data/*.csv` files, re-verified via a
fresh run of `validate_figure_data.py` (54/54 PASS) before any PNG was generated, plus
an independent cross-check against `CANONICAL_METRICS.csv`, `ORIGINAL_VS_CURRENT.csv`,
`STATISTICAL_RESULTS.csv`, `ABLATION_RESULTS.csv`, `CORRECTION_FUNNEL.csv`, and
`SAFETY_SUMMARY.csv` — **zero discrepancies found**.

**Plotting script**: `testing/figures/generate_figures.py` — matplotlib only (no
seaborn), deterministic, every experimental value read from CSV (no hardcoded
experimental numbers).

**Figure filenames** (11, exact names as specified): `01_overall_metric_comparison.png`
through `11_synthetic_vs_natural_transfer.png`, all under `testing/figures/`.

**Image dimensions/resolution**: all 11 PNGs between 1373x992 and 3980x1127 pixels at
200 DPI — all well above the minimum 1200x600 threshold checked by `audit_figures.py`.

**Visual audit result**: all 11 figures were individually viewed. **4 genuine layout
defects were found and fixed** (not data changes): Figure 01's x-axis tick labels
overlapped each other and the caption; Figure 02's legend box overlapped the McNemar
annotation (truncating "Paired" to "red"); Figure 07's n= annotations collided with
tick labels and the legend; Figure 10's legend overlapped the last bar's data label.
All four were fixed by repositioning legends/annotations and adjusting margins in
`generate_figures.py`, then all 11 figures were regenerated and re-inspected —
confirmed clean on the second pass.

**Numeric audit result**: `figures/FIGURE_NUMERIC_AUDIT.md` — every displayed value on
every figure traced to its exact source CSV cell; one explicit documented exception
(Figure 02's McNemar annotation text is a fixed string sourced from STEP 6's
`paired_209_metrics.json`, not parsed from `02_evidence_coverage.csv` itself, since
that CSV does not carry paired-change columns — flagged transparently, not hidden).

**Validator results**: `testing/figures/audit_figures.py` — **PASS, 99/99 checks**
(automated: existence, opens, dimensions, resolution, blank/clipping heuristics,
metadata/source linkage). `testing/validate_step9_figures.py` — **PASS, 66/66 checks**
(one of my own validator's regex patterns for the causal-isolation disclaimer was too
narrow and produced a false failure on first run; the underlying document was already
correct — the check pattern was fixed, not the document).

**Regression result**: `pytest research/prototype/tests/ -q` — **205 passed**, identical
to STEP 2-8, no test modified.

**Corrections to plotting code**: the 4 layout fixes above. **No underlying CSV, JSON,
or experimental result was altered anywhere in this step.**

**Confirmation**: no underlying experimental data changed. Every figure is a faithful
visualization of a number that already existed, unchanged, in a STEP 4-8 artifact.

## STEP 10 — GPU execution validation (2026-09-05)

**Machine role**: GPU validation machine (a **different** physical machine from
STEP 1-9, which had no NVIDIA GPU at all — AMD Radeon integrated only). Repo
clone location on this machine: `D:\Programs\nyayamind-verification` (STEP 1-9's
own "Verifying this provenance yourself" commands below cite
`D:\nyaymind\nyayamind-verification`, that machine's own clone path — noted as
an environmental difference between machines, not a discrepancy in this repo's
content; both paths point at the same git history, confirmed via identical
`HEAD` and `git log`).

**Hardware**: Windows 11 Home Single Language 10.0.26200; Intel Core
i7-13620H (10 cores / 16 logical processors); ~15.7 GiB RAM; **NVIDIA GeForce
RTX 4050 Laptop GPU**, 6141 MiB VRAM per `nvidia-smi`, driver 592.82, CUDA
(driver-reported) 13.1. `nvidia-smi` succeeded on the first attempt — full
output captured during this step. This matches the GPU model
`src/generator.py`'s own docstring names ("already validated on this RTX 4050
6GB machine") — no claim is made that this is the *same physical unit*, only
that it is the same GPU model/VRAM class the production code was written for.

**Python environment**: `research/.venv` already existed on this machine and
matched the canonical spec in `research/requirements.txt` exactly — no
environment creation was needed. Versions confirmed: Python 3.11.9, pip
(venv's own), torch 2.2.2+cu121, transformers 4.40.2, accelerate 0.29.3,
bitsandbytes 0.43.1, peft 0.10.0, trl 0.8.6, sentencepiece 0.2.2, pytest
9.1.1 — matching the "previously validated" versions this step was asked to
verify (not assume).

**PyTorch/CUDA validation**: `torch.cuda.is_available()` → `True`,
`torch.cuda.device_count()` → `1`, `torch.cuda.get_device_name(0)` →
`"NVIDIA GeForce RTX 4050 Laptop GPU"`, `torch.version.cuda` → `"12.1"`. A
real 2048×2048 matmul was allocated on `cuda:0`, executed, and its result
transferred back to CPU successfully (0 → 58,851,328 bytes allocated during
the operation, no errors/warnings). This directly overturns STEP 1-9's
recorded `torch.cuda.is_available() == False` — on **this** machine, not
retroactively on the STEP 1-9 machine, which remains unchanged and
GPU-less.

**Regression baseline (before GPU experiments)**: `pytest research/prototype/tests/ -q`
→ **205 passed**, identical to every prior step, no test modified.

**Model access**: both models the production config names were already fully
cached locally (`~/.cache/huggingface/hub/`), so no network download was
required or performed: `Qwen/Qwen2.5-7B-Instruct` (snapshot
`a09a35458c702b33eeacc393d103063234e8bc28`, ~15 GB, all 4 safetensors shards
present) and `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (~363 MB). Neither
model ID nor any quantization/config value was changed from
`config/prototype.yaml`.

**Model load result**: `StatuteGroundingGenerator.load()` (real production
class, real config) succeeded in 19.57s, landing on `cuda:0`, first-parameter
dtype `torch.float16` (bitsandbytes 4-bit nf4 quantized per config).
`NLIVerifier.load()` (default `device="cuda"`) succeeded in 3.86s alongside
the already-loaded generator. GPU memory (`torch.cuda.memory_allocated`/
`memory_reserved`, device 0): 0 MiB before any load; 5018.9 MiB
allocated / 5182.0 MiB reserved after the generator load; peak 7151.4 MiB
allocated (7736.0 MiB reserved) during one generation; 5393.1 MiB allocated
after also loading the verifier. **Observation, not a claim of failure**:
peak reserved memory (7736 MiB) exceeded `nvidia-smi`'s reported 6141 MiB
dedicated VRAM without a CUDA OOM error — consistent with Windows WDDM's
shared-GPU-memory spillover into system RAM (this driver model was shown as
`WDDM` in the `nvidia-smi` header), not investigated further this step.
Full data: `actual_outputs/step10_gpu_validation/gpu_memory_probe_result.json`.

**Real Qwen generation**: exactly one minimal generation (mode A, 1 case,
document `1975_58`, real NyayaRAG case text, real chat template, real
`model.generate()`, greedy/deterministic, seed 42) via the unmodified
production entry point `scripts/run_mvp.py --mode A --num-cases 1`. Output:
`actual_outputs/step10_gpu_validation/run_modeA_n1.jsonl`.
`gpu_generation_executed: true` (recorded in the record's own
`reproducibility.software_versions` block and this PROVENANCE entry — no
separate flag file was introduced for this since `run_mvp.py`'s own output
record already carries full generation metadata, model id, quantization,
and software versions).

**Real correction pipeline smoke test**: mode C, 5 real cases
(`1975_58`, `1996_129`, `1994_495`, `1979_295`, `1973_257`), same production
entry point, real generator + real verifier + real corrector + real scope
check + real re-verification. 4/5 cases had no CONTRADICTED/low-confidence
claim (`not_triggered`); 1/5 (`1996_129`, claim `c2`) triggered a real Qwen
correction call, which was **correctly rejected** by the programmatic scope
gate (`correction_scope_violation` — the correction altered text outside the
flagged sentence) and never shipped. Output:
`actual_outputs/step10_gpu_validation/run_modeC_n5.jsonl`. Full per-case
detail: `evaluation/GPU_CORRECTION_SAFETY_STEP10.md`.

**GPU-dependent historical experiment reproduced**: the targeted
labeled-framing correction validation
(`scripts/run_labeled_correction_validation_gpu.py`, historical result in
`outputs/labeled_correction_validation_gpu_metrics.json`, 2026-08-27) was
freshly re-executed via a byte-for-byte copy of that script with only its
output paths redirected
(`actual_outputs/step10_gpu_experiments/rerun_labeled_correction_validation_gpu.py`).
**Exact reproduction**: same 10 triggering cases in the same order, identical
`status_counts` (`{correction_scope_violation: 3, correction_failed: 6,
corrected: 1}`), identical shipped count (1), identical unsafe-shipped count
(0), and **byte-for-byte identical `regenerated_text` for all 10 cases**
(verified programmatically). Runtime 104.8s fresh vs. 84.9s historical
(+23%, hardware/timing variance, not investigated further). Full detail:
`evaluation/GPU_REPRODUCTION_CROSSCHECK.md`.

**GPU-dependent historical experiment NOT reproduced this step**: the
209-claim paired evidence-v0-vs-v1 generation experiment
(`outputs/final_gpu_validation_{A,B}.jsonl`, historical χ²=13.07, p≈0.0003)
was not regenerated from scratch — doing so would require ~100+ fresh Qwen
generations across two arms, judged out of scope for a GPU-execution-
*validation* step. Remains HISTORICAL ONLY, explicitly not attempted (not
blocked by any failure).

**Ablation status**: `ablation/GPU_ABLATION_UPDATE.md` — exactly one STEP 7
finding (targeted correction levers) is annotated as freshly, exactly
reproduced on GPU this step; every other STEP 7 finding is unaffected
(either not GPU-dependent, or HISTORICAL ONLY / NOT EXECUTED, unchanged). No
evidence grade was upgraded.

**Joint four-lever experiment**: re-checked (`grep` across `research/` for
"four-lever"/"joint lever") — no protocol exists anywhere in the repository
beyond STEP 7's own conclusion that it is `NOT_ISOLABLE`. **Joint four-lever
experiment remains unavailable.** None was invented this step.

**Validation**: `testing/validate_step10_gpu.py` — see this step's final
report for the exact PASS/FAIL count (run once, immediately after all fresh
files above were written, no retroactive edits to already-validated content).

**Regression result (after GPU experiments)**: `pytest research/prototype/tests/ -q`
→ **205 passed**, identical to every prior step — no file under `src/` or
`tests/` was touched by this step.

**Files added this step** (all new, nothing overwritten):
`evaluation/GPU_EXECUTION_INVENTORY.md`, `evaluation/GPU_REPRODUCTION_CROSSCHECK.md`,
`evaluation/GPU_CORRECTION_SAFETY_STEP10.md`, `ablation/GPU_ABLATION_UPDATE.md`,
`validate_step10_gpu.py`, `actual_outputs/step10_gpu_validation/*`,
`actual_outputs/step10_gpu_experiments/*`, and this PROVENANCE.md section.
No file under `research/data/`, `final_demo_pack/`, `final_comparison/`,
`src/`, `tests/`, `expected_outputs/`, or any pre-existing `actual_outputs/step{1..9}_*`
directory was modified.

**Limitations carried forward, unchanged**: no legal ground truth exists
anywhere in this project; joint four-lever causal isolation does not exist;
narrow re-verification and the general correction-levers finding remain
DIAGNOSTIC; the cumulative 1/56 correction rate was not re-derived this step;
the 209-claim generation experiment was not reproduced this step (see above,
explicitly not attempted rather than failed).

## STEP 10B — Remaining GPU experiment reproduction (2026-09-05)

**Machine role**: same GPU validation machine as STEP 10, same session
continuing directly afterward. No environment change from STEP 10 — same
`research/.venv`, same GPU, same cached model weights.

**Objective**: close the one remaining GPU-experiment gap STEP 10 left
explicitly open (the 209-claim generation experiment), and determine whether
the historical cumulative "1/56" correction figure can be freshly
reproduced.

**Distinguishing the 209-claim GPU experiment from STEP 6**: confirmed by
reading `testing/run_step6_209_paired_evaluation.py`'s own docstring — that
script performs fresh CPU-only re-evidence-matching and DeBERTa
re-verification against the ORIGINALLY-STORED `final_gpu_validation_A.jsonl`/
`_B.jsonl` verdicts ("No Qwen generation or correction is invoked"). The
GPU-dependent work STEP 6 never touched is the original generation run that
*produced* those two files: `scripts/run_final_gpu_validation.py` (50 real
Qwen generations shared across two arms, plus up to 10 real Qwen correction
calls). This is the experiment STEP 10B reproduces — genuinely distinct from,
and never overlapping with, STEP 6's CPU-only work.

**Fresh reproduction executed**: `testing/run_step10b_209_gpu_generation.py`
— a copy of the unmodified production script `scripts/run_final_gpu_validation.py`
with exactly two changes: fresh-output redirection to
`testing/actual_outputs/step10b_gpu_experiments/` (never touching
`research/prototype/outputs/`), and an added `reproducibility_metadata` block
(git commit `4e221ba3426baa2e592b44d04c10ba092703b202`, torch 2.2.2+cu121,
CUDA 12.1, driver 592.82, GPU `NVIDIA GeForce RTX 4050 Laptop GPU`, SHA-256 of
every input dataset file, exact command, wall-clock start/end). Same 50-case
candidate file, same seed (42), same Arm A/B configs, same models
(`Qwen/Qwen2.5-7B-Instruct` 4-bit nf4, `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`),
`do_sample=false`.

**Result: exact reproduction.** `n_claims_shared_generation`=209 (both runs);
Arm A 132/209 evidence-matched, Arm B 147/209 (both runs, identical
`evidence_match_method_counts` and `verdict_counts`); confidence summary
statistics identical to all stored digits in both arms; 5/5 correction
triggers in both arms with identical `correction_failed`(3)/
`correction_scope_violation`(2) split, 0 shipped, 0 unsafe — all matching
the 2026-08-27 historical run exactly. Programmatic byte-for-byte comparison
of all 50 cases' generated text: **0 mismatches**. `peak_vram_mib`: 7547 in
both the historical run and this fresh run (identical figure). Runtime: this
run's total was 1539.2s (25.7 min, faster than historical's 2040.9s/34.0
min) — runtime direction reversed from STEP 10's Experiment 1 (+23% slower
there), reinforcing that wall-clock time is a hardware/load measure, not a
correctness measure, and is not used as a reproduction criterion. Historical
files (`outputs/final_gpu_validation_metrics.json`, `_A.jsonl`, `_B.jsonl`,
`_corrections_detail.jsonl`) verified untouched (mtimes and SHA-256 hashes
unchanged from before this run). Full comparison:
`evaluation/GPU_REPRODUCTION_CROSSCHECK.md`, Experiment 3.

**Cumulative correction rate (1/56): PROTOCOL INSUFFICIENT, not attempted.**
Investigated `outputs/final_metrics.json`'s `section_D_correction_safety_cumulative`
and found it is a pooled rollup across the project's entire historical
correction-experiment population, computed (per its own `provenance` field)
by an ad-hoc, never-committed "build_final_metrics analysis" script that
does not exist anywhere in this repository (confirmed by repository-wide
search) and carries no per-constituent breakdown. Reconstructing it honestly
would require freshly re-running every GPU-dependent correction experiment
in the project's history and re-summing — not a bounded task, and out of
scope for this step. Documented, not attempted, not treated as failed.

**Ablation status update**: `ablation/GPU_ABLATION_UPDATE.md` updated —
the evidence-v0-vs-v1 (209-claim) row now records the underlying generation
as freshly, exactly reproduced on GPU (evidence GRADE unchanged, still
SUPPORTED — this confirms reproducibility of the generation step, not new
statistical evidence); the cumulative-1/56 row now records the STEP 10B
PROTOCOL INSUFFICIENT finding in place of STEP 10's "not re-derived."

**Regression result**: `pytest research/prototype/tests/ -q` → **205 passed**,
identical to every prior step — no file under `src/` or `tests/` touched.

**Validation**: `testing/validate_step10b_gpu.py` — see this step's final
report for the exact PASS/FAIL count.

**Files added this step** (all new, nothing overwritten):
`testing/run_step10b_209_gpu_generation.py`,
`actual_outputs/step10b_gpu_experiments/*` (fresh metrics/JSONL/console log),
`validate_step10b_gpu.py`, and this PROVENANCE.md section. **Files extended
(append-only, no prior content removed)**:
`evaluation/GPU_REPRODUCTION_CROSSCHECK.md`, `ablation/GPU_ABLATION_UPDATE.md`.
No file under `research/data/`, `final_demo_pack/`, `final_comparison/`,
`src/`, `tests/`, `expected_outputs/`, or `research/prototype/outputs/` was
modified — `outputs/final_gpu_validation_*` in particular was read-only for
this step (candidate-ID list only) and never written to.

**Limitations carried forward, unchanged**: no legal ground truth exists
anywhere in this project; joint four-lever causal isolation does not exist
(re-checked this step, still absent, none invented); narrow re-verification
remains DIAGNOSTIC; the cumulative 1/56 correction rate remains
un-reconstructable from a single protocol (PROTOCOL INSUFFICIENT, this
step's own finding, not merely "not re-derived").

## Verifying this provenance yourself

```
git -C D:/nyaymind/nyayamind-verification rev-parse HEAD
git -C D:/nyaymind/nyayamind-verification log -1 --format="%H %ad %s"
git -C D:/nyaymind/nyayamind-verification status --short
```

Every path cited anywhere in this workspace (`inputs/README.md`, `MANIFEST.md`, every
`component_tests/0N_*/README.md`) points at a file that exists in this exact commit —
spot-checked during this step's creation, not assumed from earlier documentation.
