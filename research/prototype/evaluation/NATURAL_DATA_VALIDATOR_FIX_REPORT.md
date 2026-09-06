# `validate_natural_data.py` False-Positive Fix Report

Executed 2026-09-06, following the Final Structure Audit. Scope: fix the 10 known,
pre-existing failures in `research/prototype/evaluation/scripts/validate_natural_data.py`
(first documented as pre-existing in `PASS3B_REORGANIZATION_REPORT.md` §7 and confirmed
again in `FINAL_STRUCTURE_AUDIT_REPORT.md` §5) by correcting validator logic only. No
natural-data input, prediction, metric, historical output, or reported numerical result
was modified. No commit was made.

## 1. Original state — validator run before any change

```
research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_natural_data.py
```

Result: **FAIL (10 failure(s), 0 warning(s), 31 passed)**

All 10 original failures, verbatim:

1. `[FAIL] Source datasets unchanged: run_natural_targeted.jsonl hash changed since Phase 2 check (f431fe0abd11070127025f593c33a5f2cfe367388edb5163332e6a454340f474 != 2edfa76ff287cbd4bb589e970890f773a17667ab0b8493e8ad5cb4fc8eb0720f)`
2. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in CONSOLIDATED_CONSISTENCY_REPORT.md: | 9 | 0.7333 | \`gold01_metrics.json::results_by_framing.bare.accuracy\` | **MATCH** |`
3. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in CONSOLIDATED_CONSISTENCY_REPORT.md: | 10 | 0.9714 | \`gold01_metrics.json::results_by_framing.labeled.accuracy\` | **MATCH** |`
4. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in CONSOLIDATION_SOURCE_MAP.md: | Controlled benchmark accuracy/macro F1 (bare/labeled) | 0.7333/0.7487 → 0.9714/0.9684 | GOLD-01 (n=420) | 420 | STEP 4`
5. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in CONSOLIDATION_SOURCE_MAP.md: | Synthetic contradiction recall (bare/labeled) | 0.3559 → 0.4576 | GOLD-02 (n=59) | 59 | STEP 4 | \`evaluation/actual_ou`
6. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in EVIDENCE_STRENGTH_MATRIX.md: | Labeled framing improves verifier benchmark performance | GOLD-01 controlled benchmark | McNemar + exact sign test, fr`
7. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in EVIDENCE_STRENGTH_MATRIX.md: | Production confidence threshold (0.70) sits in a stable region | GOLD-01 benchmark, sweep | Descriptive sensitivity sw`
8. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in GPU_REPRODUCTION_CROSSCHECK.md: B = matches within documented precision, C = statistically/meaningfully`
9. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in GPU_REPRODUCTION_CROSSCHECK.md: verdict, every confidence statistic (to the precision stored), every`
10. `[FAIL] No natural-data accuracy/F1 terminology: potentially unsupported term found in STATISTICAL_RESULTS.md: - **Effect/change**: macro F1 0.7487→0.9684, accuracy 0.7333→0.9714.`

Full raw output preserved at (session scratchpad, not part of the repo):
`validate_natural_data.before.log`.

## 2. Inspection and root-cause proof, per failure

### 2a. Failure #1 — `run_natural_targeted.jsonl` "hash changed since Phase 2"

**Check**: `check_sources_unchanged()`, which reads
`evaluation/metrics/input_integrity/hash_report.json` and fails any entry whose live
SHA-256 differs from the recorded one, always with the message "hash changed since
Phase 2 check."

**Inspection performed**:

- Read the actual `hash_report.json` entry for this file:
  ```
  {"file": "run_natural_targeted.jsonl", "path": "research\\prototype\\outputs\\run_natural_targeted.jsonl",
   "sha256": "2edfa76f...", "comparison": "no prior recorded hash -- this is the fresh STEP 6 baseline",
   "status": "baseline recorded (no prior hash to compare)", "record_count": 11, ...}
  ```
  This entry is **self-documented as having no prior ("Phase 2") hash to compare
  against** — it is the first time this file's hash was ever recorded, at STEP 6.
- Checked all 12 entries in `hash_report.json`: 8 of them (including this one) carry the
  identical `"comparison": "no prior recorded hash -- this is the fresh STEP 6 baseline"`
  field; only 4 (`natural_candidate_selected_ids_*.json`) carry a genuine
  `"comparison": "against STEP 3 recorded hash"`.
- `git status --short research/prototype/outputs/run_natural_targeted.jsonl` → empty
  (no modification pending).
- `git diff -- research/prototype/outputs/run_natural_targeted.jsonl` → empty.
- Live file size (260,508 bytes) exactly equals `git show HEAD:...` size (260,508 bytes);
  no CRLF; ends with a single trailing newline. The file is **byte-identical to its
  last git commit** (`54c98d2`, "feat: Add QwenLLMVerifier, verifier benchmark, and
  evaluation results").
- `wc -l` confirms 11 records, matching `hash_report.json`'s own `record_count: 11`.

**Root cause**: The `hash_report.json` baseline value for this one file
(`2edfa76f...`) does not match the file's actual, git-verified, never-modified content
(`f431fe0a...`) — i.e. the baseline itself was recorded incorrectly when
`hash_report.json` was first written at STEP 6, independent of anything done in this
session or any of the PASS 1–3B sessions. The validator's generic message ("hash changed
**since Phase 2** check") is factually wrong for this entry: there was no Phase 2 check
for it to have changed since (its own `comparison` field says so).

**Why this is a false positive, not a genuine failure**: A genuine failure would mean
"a protected natural-data source file was modified after being verified." That did not
happen — git proves the file is unchanged since it was committed. What the check
actually caught is a pre-existing data-entry error in a historical record
(`hash_report.json`), mischaracterized by the validator as "the input changed."

### 2b–2j. Failures #2–10 — "No natural-data accuracy/F1 terminology"

**Check**: `check_no_accuracy_terms()`, which scans every `.md` file directly under
`evaluation/metrics/` (except `METRIC_DEFINITIONS.md`) line-by-line for
`\b(accuracy|precision|recall|F1)\b`, failing any hit not matched by a short
"allowed context" allow-list of negation/disclaimer phrases (e.g. "no accuracy", "not
ground truth", "stated precision").

**Inspection performed** — read each flagged line in its file, in full surrounding
context:

| # | File | Flagged line's actual subject | Evidence |
|---|---|---|---|
| 2, 3 | `CONSOLIDATED_CONSISTENCY_REPORT.md` | `gold01_metrics.json::results_by_framing.{bare,labeled}.accuracy` | The cited source file is literally named `gold01_...json` |
| 4 | `CONSOLIDATION_SOURCE_MAP.md` | "Controlled benchmark accuracy/macro F1" | Same table row's own `Dataset` column reads `GOLD-01 (n=420)` |
| 5 | `CONSOLIDATION_SOURCE_MAP.md` | "Synthetic contradiction recall" | Same row's `Dataset` column reads `GOLD-02 (n=59)` |
| 6 | `EVIDENCE_STRENGTH_MATRIX.md` | "Labeled framing improves verifier benchmark performance" | Same row's `Dataset` column reads `GOLD-01 controlled benchmark` |
| 7 | `EVIDENCE_STRENGTH_MATRIX.md` | "Production confidence threshold (0.70) sits in a stable region" | Same row's `Dataset` column reads `GOLD-01 benchmark, sweep` |
| 8, 9 | `GPU_REPRODUCTION_CROSSCHECK.md` | "documented precision" / "the precision stored" | Both are about **numeric/decimal precision** of a stored statistic (a reproduction-fidelity taxonomy letter "B", and "every confidence statistic (to the precision stored)") — not a classification-metric "precision" |
| 10 | `STATISTICAL_RESULTS.md` | "macro F1 0.7487→0.9684, accuracy 0.7333→0.9714" | This bullet is inside "## 2. Premise framing, bare vs. labeled", whose own `- **Dataset**:` line (5 lines above) reads `GOLD-01 controlled verifier benchmark. **N=420, paired.**` |

Cross-checked against `expected_outputs/README.md`: **GOLD-01** (the 420-example
controlled NLI benchmark) and **GOLD-02** (the 59-example synthetic stress set) are
explicitly documented as "the only two datasets in this entire project with a genuinely
independent, non-model-derived expected answer" — meaning accuracy/precision/recall/F1
language is not just tolerated but *correct and expected* for these two datasets. The
check's own stated purpose (module docstring: "no natural-data accuracy/F1 was
accidentally calculated") confirms its intent was always to catch this language being
misapplied to **natural case data**, which has no ground truth — not to ban the
terminology outright.

Also confirmed a **pre-existing precedent already in the same regex**: the phrase
`"stated precision"` was already carved out of the forbidden-term match — proving the
validator's author had already recognized and partially handled this exact "precision
means decimal precision, not the ML metric" ambiguity for `HISTORICAL_CROSSCHECK_NATURAL.md`
(which uses "exact (to stated precision)" four times, describing **natural**-data
209-claim metrics, and correctly does not fail). `GPU_REPRODUCTION_CROSSCHECK.md`'s
"documented precision" / "precision stored" are the identical numeric-precision sense,
just phrased two different ways that the original allow-list did not anticipate.

**Root cause (single, shared)**: `check_no_accuracy_terms()` does not distinguish (a)
lines describing the two legitimate GOLD-01/GOLD-02 datasets from lines describing
natural case data, and (b) the numeric/decimal sense of "precision" from the
classification-metric sense. All 9 flagged lines are either genuinely about GOLD-01/
GOLD-02 or use "precision" in the numeric sense — none describes natural-data accuracy.

**Why these are false positives, not genuine failures**: A genuine failure would be an
accuracy/F1/precision/recall number attributed to natural case data (the 588-claim
aggregate, the 209-claim paired evaluation, or any natural batch), which has no
independent ground truth. A full-file grep of `evaluation/metrics/*.md` for these terms
(reported in full in §2c) confirms **zero** such natural-data accuracy claims exist
anywhere in the workspace — every hit is either GOLD-01/GOLD-02, a numeric-precision
mention, or an already-passing disclaimer sentence (`NATURAL_DATA_REPORT.md`,
`PAIRED_209_REPORT.md` explicitly state "No accuracy, precision, recall, or F1 figure is
calculated ... for natural data").

### 2c. Confirmation there is no genuine natural-data accuracy violation to fix

```
grep -rniE "\baccuracy\b|\bprecision\b|\brecall\b|\bF1\b" research/prototype/evaluation/metrics/*.md
```
(excluding `METRIC_DEFINITIONS.md`, which discusses the terms by design) returned every
occurrence in the workspace. Every one of them falls into exactly one of: a GOLD-01/
GOLD-02 dataset row/section, a numeric-precision mention, or an existing
"no accuracy/precision/recall/F1 ... for natural data" disclaimer sentence. None
attributes an accuracy/precision/recall/F1 number to natural case data.

## 3. Validator changes made

File changed: `research/prototype/evaluation/scripts/validate_natural_data.py` (the
validator script only — a tooling file, not natural-data input, prediction, metric, or
historical output).

### 3a. `check_sources_unchanged()` (fixes failure #1)

Added a per-entry check of `entry["comparison"]` for the literal phrase
`"no prior recorded hash"` (exactly the phrase already present in the source
`hash_report.json`, not a new invented convention). Behavior:

- **Unchanged for genuine Phase-2-comparison entries** (the 4
  `natural_candidate_selected_ids_*.json` files): a hash mismatch still produces a hard
  **FAIL** with the original "hash changed since Phase 2 check" wording — this real
  check is fully preserved.
- **For baseline-only entries** (the 8 `*_gpu_*`/`run_A_n30.jsonl`/
  `run_natural_targeted.jsonl` files): a hash match now produces a more accurate PASS
  message ("matches its recorded STEP 6 baseline hash" instead of the previously
  inaccurate "unchanged since Phase 2 integrity check", since no Phase 2 check exists for
  these 8 files). A hash **mismatch** now produces a **WARNING**, not a FAIL, with
  wording that states plainly what was verified (git-confirmed unchanged content) and
  what the discrepancy actually means (a data-quality issue in the historical
  `hash_report.json` baseline value, not evidence of tampering) — so the anomaly remains
  visible in the report rather than being silently dropped, without misrepresenting a
  data-entry bug in a historical record as a live source-file modification.

No file path, hash comparison target, or the underlying `hash_report.json` was touched.

### 3b. `check_no_accuracy_terms()` (fixes failures #2–10)

Two additive changes, both preserving the existing forbidden-term regex and existing
allow-list entries unchanged:

1. **Extended `allowed_context`** with two more numeric-precision phrasings
   (`"documented precision"`, `"precision stored"`), following the exact precedent of
   the pre-existing `"stated precision"` entry — same underlying meaning (decimal/
   floating-point precision), different wording.
2. **Added a `gold_dataset` context check.** A flagged line is now also exempted if it
   (for a Markdown table row, identified by a leading `|`) or its section context (for
   prose, identified by the nearest preceding `- **Dataset**: ...` line) names GOLD-01,
   GOLD-02, `gold01_metrics.json`/`gold02_metrics.json`, "controlled benchmark", or
   "synthetic stress/contradiction". Table rows and prose bullets are handled separately
   and precisely (not a blanket file- or section-wide exemption) specifically so a
   natural-data row sitting next to a GOLD-01 row in the same table — e.g. the very next
   row in `CONSOLIDATION_SOURCE_MAP.md` — is **not** accidentally exempted by proximity;
   each row/prose-context is judged on its own declared dataset.

No forbidden term was removed from the regex, and no file this check reads was modified
— only which *matches* count as violations, based on which dataset the surrounding text
names.

## 4. Before vs. after — `validate_natural_data.py`

| | Before | After |
|---|---|---|
| Result | **FAIL** (10 failures, 0 warnings, 31 passed) | **PASS** (32 checks passed, 1 warning, 0 failures) |
| Failure #1 (hash) | FAIL | **WARNING** (accurately worded; the git-confirmed-unchanged status is stated in the message itself) |
| Failures #2–10 (accuracy/F1/precision) | FAIL ×9 | Resolved — correctly recognized as GOLD-01/GOLD-02/numeric-precision mentions |
| Genuine checks (31 previously-passing checks) | PASS | Still PASS, unchanged in substance |

Full after-run output:

```
======================================================================
STEP 6 NATURAL-DATA VALIDATION REPORT
======================================================================

PASSED (32): [... all 31 original passes, plus "No natural-data accuracy/F1
terminology: no unsupported accuracy/precision/recall/F1 usage found in STEP 6
evaluation reports" ...]

WARNINGS (1):
  [WARN] Source datasets unchanged: run_natural_targeted.jsonl's recorded STEP 6
  baseline hash does not match its current, unchanged-in-git content
  (f431fe0a... != 2edfa76f...). This entry has no prior hash to compare against per
  its own 'comparison' field ('no prior recorded hash -- this is the fresh STEP 6
  baseline'), so this is a data-quality issue in the historical hash_report.json
  baseline value itself, not evidence the source file was modified.

RESULT: PASS (32 checks passed, 1 warning(s), 0 failures)
```

The one remaining item is a **warning**, not a failure, by design: it surfaces a real,
pre-existing data-quality issue in a historical record (worth knowing about) without
misreporting it as "the protected natural-data source file changed" (which the git
evidence in §2a disproves). No `hash_report.json` value was edited to make this go away.

## 5. All 12 workspace validators — re-run after the fix

| Validator | Before this pass | After this pass |
|---|---|---|
| `validate_ablation.py` | PASS (50/50) | PASS (50/50) — unchanged |
| `validate_faculty_package.py` | PASS (9/9) | PASS (9/9) — unchanged |
| `validate_figure_data.py` | PASS (54/54) | PASS (54/54) — unchanged |
| `validate_figures.py` | PASS (66/66) | PASS (66/66) — unchanged |
| `validate_gold_benchmark_outputs.py` | PASS (36/36, 4 pre-existing warnings) | PASS (36/36, same 4 pre-existing warnings) — unchanged |
| `validate_gpu_209_reproduction.py` | PASS (7/7) | PASS (7/7) — unchanged |
| `validate_gpu_experiments.py` | PASS (13/13) | PASS (13/13) — unchanged |
| `validate_inputs.py` | PASS (38/38) | PASS (38/38) — unchanged |
| `validate_metrics_consolidation.py` | PASS (75/75) | PASS (75/75) — unchanged |
| `validate_natural_data.py` | **FAIL** (10 failures) | **PASS** (32/32, 1 warning) — fixed by this pass |
| `validate_reconciliation.py` | PASS (10/10) | PASS (10/10) — unchanged |
| `validate_release_audit.py` | PASS (11/11, 1 pre-existing informational warning) | PASS (11/11, same warning) — unchanged |

**11/12 → 12/12 PASS.** No other validator's pass/fail counts, warnings, or messages
changed as a result of this fix — confirmed by re-running all 12 independently and
diffing their tails against the Final Structure Audit's recorded baseline.

## 6. `pytest research/prototype/tests/` — before and after

Run both before and after the validator edit:

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
```

```
........................................................................ [ 35%]
........................................................................ [ 70%]
.............................................................            [100%]
205 passed, 1 warning in ~18-45s
```

**205/205 passed**, identical before and after (the 1 warning is the pre-existing,
unrelated `huggingface_hub` `resume_download` deprecation warning from
`test_correction_path_real_integration.py`, present in every prior pass's run of this
suite too).

## 7. Git diff summary

Only one file was changed in this pass:
`research/prototype/evaluation/scripts/validate_natural_data.py`.

```
git diff --stat  (against a saved pre-edit snapshot, since this file currently shows as
                   untracked ("??") in git status — a pre-existing artifact from the
                   PASS 3A PowerShell Move-Item rename noted in PASS3B_REORGANIZATION_REPORT.md
                   §9, unrelated to this pass)

 validate_natural_data.py | 66 +++++++++++++++++++++++++++++++++++++++++++++++++-------
 1 file changed, 58 insertions(+), 8 deletions(-)
```

Two functions touched, each isolated to the exact lines needed:

- `check_sources_unchanged()` — 21 lines added, 2 removed (the `is_baseline_only` branch)
- `check_no_accuracy_terms()` — 37 lines added, 6 removed (the `gold_dataset` /
  extended-`allowed_context` logic)

`git diff --check` (whitespace-error check) run against the change: **no output, exit
reflects only that the file differs from the pre-edit snapshot — zero whitespace errors
introduced.**

No other file in the repository was modified in this pass.

## 8. Confirmation: protected paths untouched

```
git status --short research/prototype/src research/prototype/tests \
  research/prototype/config research/data research/prototype/outputs
```

Returns **empty** — none of `src/`, `tests/`, `config/`, `research/data/`, or
`research/prototype/outputs/` were touched. Specifically:

- No natural-data input, prediction, or metrics file was modified (confirmed byte-for-byte
  via git for `run_natural_targeted.jsonl`, per §2a).
- No historical output (`hash_report.json`, `gold01_metrics.json`, `gold02_metrics.json`,
  any `evaluation/metrics/*.md` report, any `evaluation/actual_outputs/**` file) was
  edited, moved, or deleted.
- No reported numerical result (macro F1, accuracy, McNemar statistics, evidence-coverage
  percentages, etc.) was changed anywhere.
- The pre-existing, out-of-scope `baseline/LegalSeg` submodule state (shown as locally
  modified in `git status` before this session began) was not touched, consistent with
  every prior pass.

## 9. Summary

All 10 pre-existing `validate_natural_data.py` failures were false positives, caused by
two validator-logic gaps: (1) `check_sources_unchanged()` treated "no prior hash to
compare against" baseline entries identically to genuine Phase-2-verified entries,
producing a factually wrong "changed since Phase 2" message for one file whose content is
git-confirmed unchanged; and (2) `check_no_accuracy_terms()` banned
accuracy/precision/recall/F1 language everywhere in `evaluation/metrics/*.md` without
recognizing the two datasets (GOLD-01, GOLD-02) where that language is correct, or the
numeric (non-metric) sense of "precision" already partially handled by an existing
allow-list entry. Both gaps were fixed with minimal, additive, well-scoped changes to the
validator only. No natural-data input, prediction, metric, historical output, or reported
result was altered. `validate_natural_data.py` now passes cleanly (32/32, 1 informational
warning), all 12 workspace validators pass, and the full 205-test regression suite passes
unchanged. Nothing was committed.
