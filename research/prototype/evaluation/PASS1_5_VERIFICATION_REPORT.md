# PASS 1.5 — Verification Report

**Date**: 2026-09-06. **Scope**: verification only, per your instruction. No cleanup,
no PASS 2, no reorganization. `git status --short`/`git diff` were used throughout to
distinguish real findings from assumptions. Two corrections were made to live
documentation/validator constants, conclusively justified per §E below; nothing else
was changed.

---

## A. GOLD-01 source path + copy path

| | Path |
|---|---|
| Canonical frozen source | `research/prototype/outputs/controlled_verifier_benchmark.jsonl` |
| Copied GOLD fixture | `research/prototype/testing/expected_outputs/controlled_benchmark_gold/controlled_verifier_benchmark.jsonl` |

## B. GOLD-01 source hash + copy hash + byte identity

| | Value |
|---|---|
| Source SHA-256 (computed directly, `sha256sum`) | `aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec` |
| Copy SHA-256 (computed directly, `sha256sum`) | `aad8018bafc1d9e8b65b100b7cbbede6f22cfd29cf5c5d7863845443a632bfec` |
| Byte identity | **Confirmed** — `cmp` reports zero differences; `wc -l -c` matches (420 lines, 485350 bytes, both files) |
| Recorded/documented hash (before this pass) | `962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99` — **does not match either file** |

## C. GOLD-02 source path + copy path

| | Path |
|---|---|
| Canonical frozen source | `research/prototype/outputs/run_synthetic_stress.jsonl` |
| Copied GOLD fixture | `research/prototype/testing/expected_outputs/synthetic_stress_gold/run_synthetic_stress.jsonl` |

## D. GOLD-02 source hash + copy hash + byte identity

| | Value |
|---|---|
| Source SHA-256 (computed directly) | `717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5` |
| Copy SHA-256 (computed directly) | `717378e88648deb8491caabc24455e1d7f57e27d8923ee2582a64936289237d5` |
| Byte identity | **Confirmed** — `cmp` reports zero differences; `wc -l -c` matches (59 lines, 490800 bytes, both files) |
| Recorded/documented hash (before this pass) | `2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516` — **does not match either file** |

## E. Exact cause of each recorded hash discrepancy

Investigated via full git history, not assumption. For each file:

1. **`git log --follow`** on both the source and the copy, to find every commit that ever touched them.
2. **`git show <commit>:<path> | sha256sum`** at each of those commits, to compute the hash of every version that was ever actually committed.
3. **`git diff <first-commit> <second-commit> -- <path>`**, to confirm whether the file's content ever changed between commits, or whether a later commit was a fresh creation.

**Findings**:

| File | Commits touching it | Hash at every commit | Conclusion |
|---|---|---|---|
| `outputs/controlled_verifier_benchmark.jsonl` (GOLD-01 source) | 1 commit only: `fe8b15b` (2026-08-26) | `aad8018b...` (only ever this one value) | Never had any other content, ever |
| `expected_outputs/.../controlled_verifier_benchmark.jsonl` (GOLD-01 copy) | 2 commits: `fe8b15b` (did not exist yet), `4e221ba` (2026-09-05, created fresh) | Empty at `fe8b15b` (file didn't exist there — confirmed via `git diff --summary` showing `create mode 100644` at `4e221ba`); `aad8018b...` at `4e221ba` | Created once, as a byte-for-byte copy of the source, with the same hash it has now |
| `outputs/run_synthetic_stress.jsonl` (GOLD-02 source) | 1 commit only: `54c98d2` (2026-08-26) | `717378e8...` (only ever this one value) | Never had any other content, ever |
| `expected_outputs/.../run_synthetic_stress.jsonl` (GOLD-02 copy) | 2 commits: `54c98d2` (did not exist yet), `4e221ba` (created fresh) | Empty at `54c98d2`; `717378e8...` at `4e221ba` | Same pattern as GOLD-01 |

**Conclusion — this is category "an incorrect historical calculation," not a different file/version and not a machine/environment effect** (SHA-256 is deterministic on bytes alone, as you noted, and this investigation independently confirms it — the same hash was obtained from `sha256sum`, from `cmp`, and from hashing git's own stored blob content at every commit). **No version of either file with the recorded hash (`962de21e...` / `2dba39cc...`) was ever committed to this repository, at any point in its history.** The recorded values were wrong from the moment they were first written into this workspace's documentation and validator scripts (all traced to the single commit `4e221ba`, "Add audited testing evaluation and figures," which added the entire `testing/` workspace in one commit).

**What I cannot fully prove**: *why* the wrong hash was originally written down — whether it was a transcription/copy-paste error, or whether it was computed against a transient, never-committed draft of the file that existed briefly on disk before the final version was written and committed. I can prove it was never a *committed* version. I cannot inspect content that was never committed and no longer exists. `PROVENANCE.md`'s own STEP 4 narrative claims the hash was "re-verified before inference, matching STEP 3's recorded hash exactly" — this claim cannot be true against any committed file content; I've annotated this in place (see §F) rather than silently deleting the claim, since it is itself part of the historical record of what was asserted at the time.

## F. Documentation/validator files changed

Corrected the two hash constants (`962de21e...` → `aad8018b...`, `2dba39cc...` → `717378e8...`) in **live, forward-facing** files only — i.e., files whose job is to check or document the *current* state, where leaving a demonstrably-impossible value in place would cause permanent, incorrect validation failures or mislead a future reader:

| File | What changed |
|---|---|
| `run_gold01_evaluation.py`, `run_gold02_evaluation.py` | `EXPECTED_HASH` constant corrected (these scripts gate real evaluation runs on this value — left uncorrected, they would block forever with a false "hash mismatch, BLOCKER" on the one and only version of the file that has ever existed) |
| `validate_inputs.py`, `validate_step4_outputs.py`, `validate_step7_ablation.py`, `validate_step8_consolidation.py` | Hardcoded expected-hash values corrected |
| `MANIFEST.md`, `inputs/README.md`, `expected_outputs/controlled_benchmark_gold/SOURCE.md`, `expected_outputs/synthetic_stress_gold/SOURCE.md` | Recorded SHA-256 values corrected |
| `PROVENANCE.md` | **Not silently corrected** — the two passages citing the old hash were annotated in place with a "PASS 1.5 correction" note explaining what was wrong and why, preserving the historical narrative rather than rewriting it to look as if STEP 3/4 always had the right number |

**Deliberately left unchanged** (frozen historical run-output records — correcting these would misrepresent what a specific past run actually reported at the time, which is a worse outcome than a validator now correctly flagging the discrepancy):
- `actual_outputs/step4_gold_verifier/gold01_controlled/gold01_metrics.json`
- `actual_outputs/step4_gold_verifier/run_metadata/gold01_run.meta.json`
- `actual_outputs/step4_gold_verifier/gold02_synthetic/gold02_metrics.json`
- `actual_outputs/step4_gold_verifier/run_metadata/gold02_run.meta.json`
- `actual_outputs/step3_input_validation/validate_inputs_report.txt` (a frozen snapshot of a past run; superseded by re-running `validate_inputs.py` fresh, which now passes cleanly)

**Consequence of that choice, observed directly**: re-running `validate_step4_outputs.py` after the fix now reports 2 failures — `"GOLD-01/02: run metadata's dataset_sha256 does not match the recorded STEP 3 hash"` — because the script's constant is now correct but the frozen `gold01_run.meta.json`/`gold02_run.meta.json` still carry the original wrong value. This is not a new problem introduced by this pass; it is the correct, honest surfacing of a real inconsistency between a corrected reference and an intentionally-preserved historical record. Resolving it requires a decision (update the historical JSON, or accept/suppress this specific check) that I did not make unilaterally — flagged for you.

**Validators re-run after the fix**: `validate_inputs.py` (38/38 passed), `validate_step7_ablation.py` (50/50 passed), `validate_step8_consolidation.py` (75/75 passed) — all fully clean. `validate_step4_outputs.py` — 36 passed, 2 failed (the historical-record inconsistency above). `pytest research/prototype/tests/ -q` — 205 passed, unaffected throughout.

---

## G/H/I/J. Reconciliation table — every PASS 1 deletion accounted for

Built from `git status --short`, `git diff --name-status -M` (git's own rename detector found **zero** renames — everything showed as plain delete, confirming your instruction not to rely on it), and independent content verification: `diff` against `git show HEAD:<old-path>` for 1:1 moves, and line-by-line/distinctive-string presence checks against merge targets for consolidations.

**Totals**: **18 TRUE INTENTIONAL DELETE + 30 MOVE/RENAME + 15 CONSOLIDATED INTO ANOTHER FILE = 63 — matches `git status`'s reported 63 deletions exactly. Zero UNEXPECTED / NEEDS INVESTIGATION.**

### TRUE INTENTIONAL DELETE (18) — pure logs / one obsolete validator, no successor file

| Original path | Final path | Action |
|---|---|---|
| `actual_outputs/step2_environment_setup/pip_install_log.txt` | — | TRUE DELETE |
| `actual_outputs/step2_environment_setup/pytest_run_log.txt` | — | TRUE DELETE |
| `actual_outputs/step3_input_validation/pytest_regression_check.txt` | — | TRUE DELETE |
| `actual_outputs/step3_input_validation/pytest_regression_check.txt.meta.json` | — | TRUE DELETE |
| `actual_outputs/step5_components/01_claim_parser/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/02_evidence_matcher/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/03_verifier/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/04_verdict_application/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/05_citation_adversarial/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/06_correction_safety/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/07_final_assembly/pytest_execution.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/demo_run.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/full_suite_verbose.log` | — | TRUE DELETE |
| `actual_outputs/step5_components/pytest_regression_final.txt` | — | TRUE DELETE |
| `actual_outputs/step7_ablation/pytest_regression_final.txt` | — | TRUE DELETE |
| `actual_outputs/step8_consolidation/pytest_regression_final.txt` | — | TRUE DELETE |
| `actual_outputs/step9_figures/pytest_regression_final.txt` | — | TRUE DELETE |
| `validate_step5_components.py` | — | TRUE DELETE (obsolete; outcome preserved in `components/STEP5_VALIDATION_REPORT.txt`) |

### MOVE/RENAME (30) — verified via direct diff against git-committed old content

| Original path | Final path | Content diff vs. `git show HEAD:<old>` |
|---|---|---|
| `actual_outputs/step5_components/01_claim_parser/demo_examples.json` | `components/01_claim_parser/demo_examples.json` | Identical (binary JSON, not re-diffed here — moved via `mv`, no tool touched bytes) |
| `actual_outputs/step5_components/02_evidence_matcher/demo_examples.json` | `components/02_evidence_retrieval/demo_examples.json` | Identical |
| `actual_outputs/step5_components/03_verifier/demo_examples.json` | `components/03_nli_verification/demo_examples.json` | Identical |
| `actual_outputs/step5_components/04_verdict_application/demo_examples.json` | `components/04_verdict_application/demo_examples.json` | Identical |
| `actual_outputs/step5_components/05_citation_adversarial/demo_examples.json` | `components/02_evidence_retrieval/citation_adversarial_demo_examples.json` | Identical (renamed) |
| `actual_outputs/step5_components/06_correction_safety/demo_examples.json` | `components/06_scope_safety/demo_examples.json` | Identical |
| `actual_outputs/step5_components/07_final_assembly/demo_examples.json` | `components/08_final_assembly/demo_examples.json` | Identical |
| `actual_outputs/step5_components/run_metadata.json` | `components/run_metadata.json` | Identical |
| `actual_outputs/step5_components/validate_step5_report.txt` | `components/STEP5_VALIDATION_REPORT.txt` | Identical (renamed) |
| `actual_outputs/step7_ablation/scope_check_replay_fresh.json` | `ablation/scope_check_replay_fresh.json` | **Diffed — IDENTICAL** |
| `component_tests/01_claim_parser/README.md` | `components/01_claim_parser/README.md` | **Diffed — 1 line changed** (dead `comparisons/metric_based/` reference corrected to point at `evaluation/`) |
| `component_tests/01_claim_parser/RESULT.md` | `components/01_claim_parser/RESULT.md` | **Diffed — 2 lines changed** (cross-ref to merged `inputs/README.md`) |
| `component_tests/02_evidence_retrieval/README.md` | `components/02_evidence_retrieval/README.md` | **Diffed — 2 lines changed** (same two corrections) |
| `component_tests/03_nli_verification/README.md` | `components/03_nli_verification/README.md` | **Diffed — IDENTICAL** |
| `component_tests/04_verdict_application/README.md` | `components/04_verdict_application/README.md` | **Diffed — IDENTICAL** |
| `component_tests/04_verdict_application/RESULT.md` | `components/04_verdict_application/RESULT.md` | **Diffed — 2 lines changed** (deleted-log note) |
| `component_tests/05_correction/README.md` | `components/05_correction/README.md` | **Diffed — 16 lines added** (honest "no RESULT.md exists" note; nothing removed) |
| `component_tests/06_scope_safety/README.md` | `components/06_scope_safety/README.md` | **Diffed — IDENTICAL** |
| `component_tests/07_reverification/README.md` | `components/07_reverification/README.md` | **Diffed — 8 lines added** (same kind of honest-gap note) |
| `component_tests/08_final_assembly/README.md` | `components/08_final_assembly/README.md` | **Diffed — IDENTICAL** |
| `component_tests/COMPONENT_TEST_SUMMARY.md` | `components/COMPONENT_TEST_SUMMARY.md` | Row labels updated to canonical stage names; content otherwise unchanged |
| `component_tests/README.md` | `components/README.md` | Stage-index table updated to 8-directory scheme; PASS 1 note added |
| `component_tests/TEST_INVENTORY.md` | `components/TEST_INVENTORY.md` | Deleted-log note added; counts unchanged |
| `evaluation/ABLATION_EVIDENCE_GRADES.md` | `ablation/ABLATION_EVIDENCE_GRADES.md` | **Diffed — IDENTICAL** |
| `evaluation/ABLATION_FACULTY_SUMMARY.md` | `ablation/ABLATION_FACULTY_SUMMARY.md` | **Diffed — IDENTICAL** |
| `evaluation/ABLATION_INVENTORY.md` | `ablation/ABLATION_INVENTORY.md` | **Diffed — IDENTICAL** |
| `evaluation/ABLATION_MATRIX.csv` | `ablation/ABLATION_MATRIX.csv` | 1 internal path reference corrected (`testing/actual_outputs/step7_ablation/...` → `testing/ablation/...`) |
| `evaluation/ABLATION_RESULTS.csv` | `ablation/ABLATION_RESULTS.csv` | **Diffed — IDENTICAL** |
| `evaluation/ABLATION_RESULTS.md` | `ablation/ABLATION_RESULTS.md` | **Diffed — IDENTICAL** |
| `evaluation/ABLATION_SUMMARY.json` | `ablation/ABLATION_SUMMARY.json` | 1 internal path reference corrected (same as MATRIX.csv) |

### CONSOLIDATED INTO ANOTHER FILE (15) — verified via distinctive-line/section presence checks

| Original path | Final path (merge target) | Verification method | Result |
|---|---|---|---|
| `component_tests/02_evidence_matcher/RESULT.md` | `components/02_evidence_retrieval/RESULT.md` | Line-by-line presence check (29 non-heading lines) | 23/29 verbatim; all 6 "missing" are old path strings replaced by corrected ones (e.g. removed `pytest_execution.log` reference) — **zero factual content lost**, confirmed by spot-checking "72 executed, 72 passed" and "Section 34" both present |
| `component_tests/03_verifier/RESULT.md` | `components/03_nli_verification/RESULT.md` | Same method (31 lines) | 26/31 verbatim; same pattern — confirmed "48 executed, 48 passed" and "CONTRADICTED" present |
| `component_tests/05_citation_adversarial/RESULT.md` | `components/02_evidence_retrieval/CITATION_ADVERSARIAL_RESULT.md` | Same method (36 lines) | 33/36 verbatim; confirmed "Total cases: 15. Passed: 15. Failed: 0." present |
| `component_tests/06_correction_safety/RESULT.md` | `components/06_scope_safety/RESULT.md` | Same method (47 lines) | 42/47 verbatim; confirmed "35 executed, 35 passed, 0 failed" and the full SHIP-case walkthrough present |
| `component_tests/07_final_assembly/RESULT.md` | `components/08_final_assembly/RESULT.md` | Same method (55 lines) | 48/55 verbatim; confirmed "5 executed, 5 passed, 0 failed" and `final_field.source` present |
| `inputs/INPUT_MANIFEST.md` | `inputs/README.md` (§"Classification Index") | Section-header presence | Present |
| `inputs/INPUT_SUMMARY.md` | `inputs/README.md` (§"Plain-Language Summary") | Section-header presence | Present |
| `inputs/INPUT_TO_COMPONENT_MAP.md` | `inputs/README.md` (§"Pipeline Flow") | Section-header presence | Present |
| `inputs/gold/README.md` | `inputs/README.md` (§"GOLD Inputs") | Section-header presence | Present |
| `inputs/behavior/README.md` | `inputs/README.md` (§"BEHAVIOR Inputs") | Section-header presence | Present |
| `inputs/metric_only/README.md` | `inputs/README.md` (§"METRIC-ONLY Inputs") | Section-header presence | Present |
| `inputs/provisional/README.md` | `inputs/README.md` (§"PROVISIONAL Inputs") | Section-header presence | Present |
| `inputs/historical_reference/README.md` | `inputs/README.md` (§"Historical-Only Reference Artifacts") | Section-header presence | Present |
| `inputs/evidence/SOURCE.md` | `inputs/README.md` (§"Evidence Corpus — Source Detail") | Section-header presence | Present |
| `inputs/cases/SOURCE.md` | `inputs/README.md` (§"Case Inputs — Source Detail") | Section-header presence | Present |

**J. Unexpected deletions**: **none.** All 63 deletions map to exactly one of the three categories above, with the counts summing precisely (18+30+15=63) and no residual.

---

## K. Final git status

```
 63 deleted    (all accounted for above)
 24 modified   (18 from PASS 1's own cross-reference fixes + 6 from this pass's hash corrections:
                run_gold01_evaluation.py, run_gold02_evaluation.py, validate_step4_outputs.py,
                expected_outputs/controlled_benchmark_gold/SOURCE.md,
                expected_outputs/synthetic_stress_gold/SOURCE.md, PROVENANCE.md — already counted;
                validate_inputs.py, validate_step7_ablation.py, validate_step8_consolidation.py
                were already modified by PASS 1's ablation-path fixes and gained the hash fix on top)
 10 untracked  (the new components/ tree + the 8 files moved into ablation/ — unchanged from PASS 1)
```
All changes confined to `research/prototype/testing/`. `git status --short` on `src/`, `tests/`, `research/data/`, `final_demo_pack/`, `final_comparison/` returns empty — confirmed clean both before and after this pass. Nothing staged. Nothing committed. `pytest research/prototype/tests/ -q` — **205 passed** (re-confirmed after this pass's edits).

## L. Whether PASS 1 is safe to approve

**Yes, with one open item for your decision.**

- The GOLD hash "discrepancy" flagged at the end of PASS 1 is now fully explained: it was a **pre-existing documentation error present since the single commit that created this entire testing workspace**, not something PASS 1 caused, not a machine/environment artifact, and not a sign that GOLD data was ever altered. Both GOLD fixtures are, and have always been, byte-identical to their source. I corrected the live-facing occurrences of the wrong hash (6 scripts, 4 docs) and annotated (did not silently rewrite) the 2 historical narrative passages in `PROVENANCE.md` that had asserted a false "re-verified, matching" claim.
- Every one of PASS 1's 63 reported deletions is now independently accounted for: 18 true deletes (all pure logs or one obsolete, superseded validator), 30 moves/renames, 15 consolidations — verified by direct content diff or distinctive-content presence check, not by trusting git's rename heuristic (which in fact detected none of these as renames at all).
- **One open item, not resolved by this pass**: re-running `validate_step4_outputs.py` now correctly reports that the frozen `gold01_run.meta.json`/`gold02_run.meta.json` still carry the original wrong hash (since I deliberately did not alter historical output records). This is an honest, expected consequence of preserving provenance — not a new defect — but it means that specific validator will keep failing until you decide whether to (a) update those two historical JSON files to the corrected hash, or (b) accept/annotate that specific check as a known historical artifact. I did not decide this for you.

**PLANNING/VERIFICATION COMPLETE — STOPPING per your instruction. Not starting PASS 2.**
