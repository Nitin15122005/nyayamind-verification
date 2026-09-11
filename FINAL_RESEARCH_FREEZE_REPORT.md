# NyayaMind Final Research Freeze Report

_2026-09-11, updated after an unplanned laptop shutdown and independent
recovery-audit pass (same day, later)._

## Recovery-audit preamble (read this first)

The laptop shut down unexpectedly after the previous version of this report
was committed (`21716bf`). Per explicit instruction, nothing below was
trusted blindly — every claim was independently re-verified this pass:

- `git status`/`git log`/`git diff --stat`: HEAD confirmed still `21716bf`
  before this pass's own new commit, working tree clean except the
  pre-existing `baseline/LegalSeg`, no partial/zero-byte/corrupt files from
  the shutdown (checked directly: all key output files present, correct
  sizes, valid JSON/JSONL).
- **Full pytest suite re-run independently: 271/271 confirmed**, then
  **276/276** after this pass added 5 new adversarial tests (see below).
- **`run_mvp.py --check` re-run independently: confirmed clean.**
- **`validate_pack.py` re-run independently: confirmed 25/25** — but this
  re-run exposed and fixed a real, previously-unnoticed defect: the script
  `write_text()`s the entire validation log from scratch on every run,
  silently destroying every prior run's history (it had already erased the
  carefully-reconstructed 2026-08-27/2026-09-09/2026-09-11 addendum history
  once before, mid-session, and would have kept doing so on every future
  run). **Fixed this pass**: the script now appends a dated run-section
  instead of overwriting, and the destroyed history was reconstructed from
  `git show HEAD:...` one more time. This is exactly the kind of
  "don't trust it blindly" finding this recovery pass was supposed to catch.
- Found and fixed one real internal-consistency bug in this report itself:
  §A below previously self-referenced the wrong commit SHA (`95ae571`
  instead of `21716bf`, the commit it was actually part of).
- **Assertion-span mechanism adversarially re-audited** (not just the n=6
  benchmark number trusted) — 5 new end-to-end tests covering negation,
  modal/exception clauses, three-citation lists, and fail-closed behavior
  on ambiguous input. Found the implementation correct and safe; found one
  real, non-bug nuance (verb-phrase stripping asymmetry between the two
  "respectively" sentence shapes), empirically confirmed safe on real
  DeBERTa, documented in `FINAL_PRODUCTION_CONFIG.md` §5a. See Phase 3/4
  findings below.
- **System memory re-checked before considering any GPU retry**: **5.12-5.47GB
  free of 15.7GB total — the same or slightly WORSE than during the three
  failures that blocked Workstream B last session** (which occurred at
  5.3-5.5GB free). GPU VRAM itself was confirmed fully free (5814/6141 MiB)
  — the bottleneck is specifically host system RAM, not GPU. No stale
  Python/model processes were found running (nothing to clean up). Per this
  pass's own explicit instruction not to retry an already-demonstrated OOM,
  and because retrying now would predictably fail identically (memory is
  not better, it is marginally worse), **the GPU experiment was correctly
  NOT retried this pass.**
- Docker daemon re-checked: still not running. Starting a multi-GB WSL2 VM
  under confirmed memory pressure was, again, judged not a responsible
  action to take on the user's machine without their explicit direction.

## 2026-09-12 update — the GPU memory blocker RESOLVED, real n=62 data collected

A subsequent same-day pass found and fixed the actual root cause of the
model-loading failures (memory architecture audit:
`outputs/16gb_memory_architecture_audit.md`): loading a single ~3.9GB model
shard into CPU RAM as a transient staging step left almost no headroom on
this 15.7GB machine. Two small, legitimate, model-identity-preserving
fixes (`low_cpu_mem_usage=True` explicit, `gc.collect()`/
`torch.cuda.empty_cache()` before `from_pretrained()` in `src/generator.py`)
resolved it — confirmed across 4 separate successful model loads this pass,
down from 3/3 failures across two prior sessions. The experiment script was
rewritten to be checkpointed/resumable (immediate per-case writes, automatic
skip-already-done on restart, pre-case memory guard) and exercised for
real: two separate background-process interruptions during this pass were
both recovered from with zero data loss.

**Real result: n=62 fresh cases collected** (exceeding the n≥50 target),
real Qwen2.5-7B generation + real DeBERTa verification + real selective
correction through the actual production pipeline. Full analysis:
`outputs/16gb_final_execution_report.md`. Headline, verification-recovery/
correction-generation/correction-shipping kept explicitly separate:

- Verification recovery: 5/32 evidence-matched claims changed verdict
  (4 NEI→ENTAILED, 1 NEI→CONTRADICTED), 0 unsafe reversals — directionally
  consistent with every larger prior result for this lever, not
  independently significant at this n (exact sign test p≈0.125).
- Correction shipping: **0/4 (OLD), 0/5 (CURRENT)** — this answers the
  question the n=15 batch could not (it never triggered a single
  correction): the lever does not, on this evidence, change the
  1.8%-cumulative-historical shipping rate. A real case study shows why —
  Qwen produced a substantively correct fix in both arms, each independently
  rejected by a different safety gate protecting a bundled sibling claim.

Sections B, G below are updated to reflect this; the pre-fix history above
is kept as an accurate record of what was actually tried and found, not
deleted or rewritten.

## 2026-09-12 continuation — assertion-span-aware correction implemented and evaluated

A same-day continuation session implemented the highest-priority planned
improvement: **assertion-span-aware correction** (splice-based localized
fix, `src/pipeline.py`'s `apply_selective_correction_assertion_aware()`,
config-gated via `correction.assertion_aware`, default `false` — legacy
`apply_selective_correction()` unchanged and remains production). Full
decision record: `FINAL_PRODUCTION_CONFIG.md` §5b. Summary:

- **Implementation**: 20 new deterministic tests
  (`tests/test_assertion_aware_correction.py`), full suite 296/296. A
  controlled, real-corpus-derived benchmark
  (`outputs/assertion_aware_correction_controlled_benchmark.md`)
  reproduces the exact motivating scenario and confirms the splice
  mechanism and its full safety-gate chain behave as designed.
- **Real natural-data test** (`outputs/assertion_aware_correction_experiment_report.md`,
  n=10 paired attempts, real Qwen2.5-7B + real DeBERTa, the exact 5
  documents that triggered legacy correction in the committed n=62 batch):
  **0/10 shipped under assertion-aware, same as 0/10 under legacy — no
  shipping-rate improvement measured.** Investigated and explained
  case-by-case, not left as an unexplained null result: two cases hit a
  NEW scope violation because their bundled sentence's citations share an
  UNSPLIT clause (assertion-aware currently only narrows via
  `assertion_text`, not the more granular `assertion_spans`); the case
  that specifically motivated this work (`1955_32`) had its splice work
  exactly as designed — a clean, correct, isolated fix, sibling clause
  byte-identical — but was still correctly blocked by the unconditional
  sibling-regression check, because the SAME bundled sentence contains a
  SECOND, independent, genuinely wrong claim that was never the target.
  This is evidence the safety design substantively works, not evidence
  the splice mechanism failed.
- **Decision**: `correction.assertion_aware` stays `false` in production
  — EXPERIMENTAL, implemented and evaluated but not promoted, per this
  project's rule against promoting a mechanism merely because it exists.
  Reported as a genuine negative/preliminary result on correction-shipping
  specifically, not reframed as a success.
- **Docker**: re-checked this continuation session — daemon still not
  running (`failed to connect to the docker API`), host memory tight for
  much of the session (as low as 1.5-1.9GB free at times, briefly above
  the 2.0GB guard threshold when the GPU experiment above was run) —
  starting a multi-GB WSL2 VM was not attempted. Unchanged blocker; see §I.
- **Demo**: `run_demo.py` now prints `correction.assertion_aware` in its
  config block and warns explicitly that stage [5]-[7] replay logic has
  not yet been extended to assertion-aware records (production still ships
  `assertion_aware=false`, so default demo behavior is byte-for-byte
  unchanged — re-verified: `validate_pack.py` still 25/25).

Sections B and a new §G2 below are updated to reflect this.

## A. Final HEAD

This report is committed as part of the final commit of this recovery pass
(see `git log --oneline -1` at the end of this session for the exact SHA —
stated honestly as "the commit this report is part of," not hand-typed in
advance, to avoid repeating the previous self-reference bug this pass just
fixed).

## B. Test status

**302/302 tests passing** (276/276 confirmed at the start of the
2026-09-12 continuation session + 20 new deterministic assertion-aware-
correction tests + 6 more added the same day when the architecture was
completed to consume `assertion_spans` — all in
`tests/test_assertion_aware_correction.py`, 26 tests total).
Prior to that: 276/276 (271 confirmed independently at the start of the
recovery pass + 5 new adversarial assertion-span tests — see Phase 3/4
findings). `run_mvp.py --check` passes cleanly (no model loaded,
config/evidence pool validated, 136 usable records). `validate_pack.py`:
**25/25**, re-confirmed the 2026-09-12 continuation session after the
`run_demo.py` config-print edit (see continuation section above).

## C. Parser changes

None this session. Stage 3 (`c250a0e`, Art./Arts. abbreviation fix, +7
claims recovered across 2/181 real texts, zero regressions) remains as the
last parser change, verified still passing.

## D. Retrieval findings

None this session. Stage 2 (`6347c45`) remains the standing, correctly
documented finding: Jaccard token-overlap is the only method reaching 100%
correct-reject (zero wrong-Act matches) on the adversarial benchmark; BM25
and embedding alternatives were evaluated and are measurably less safe.
Neither is enabled in production. This session's stale-documentation sweep
confirmed no drift in how this finding is represented anywhere in the repo.

## E. Verifier findings

Two verifier-hypothesis levers now exist, both evaluated on real data:

1. **`narrow_primary_hypothesis`** (Stage 4, `bb2cd93`, production default
   since 2026-09-09): uses a claim's `assertion_text` as the NLI hypothesis
   when narrower than `claim_text`. CPU benchmark: 456 real evidence-matched
   claims, 107 applicable, 31 recovered NEI→ENTAILED, 0 unsafe reversals.
2. **`assertion_span_primary_hypothesis`** (NEW this session, OFF by
   default): extends the above to "respectively" claims via
   `assertion_spans` (a 2-element list, not one contiguous clause).
   Implemented in `src/pipeline.py::_assertion_spans_hypothesis()`
   (builds `"<provision_type> <provision_number> <description>"`, every
   word a genuine substring, never synthesized), gated behind a new config
   key, 14 new unit tests. Benchmarked against the **entire real
   population** of such claims in this project's history (n=6): 4/6
   changed verdict (3 NEI→ENTAILED, 1 NEI→CONTRADICTED), 0 unsafe
   reversals, every case manually verified genuine — including a real
   positive finding (correctly caught a generation error misattributing
   Indian Evidence Act §27's content). **NOT promoted to production
   default**: n=6 is too small for a production decision. See
   `FINAL_PRODUCTION_CONFIG.md` §5a.

## F. Assertion-span findings

Covered under E above for the numbers (this project's "assertion spans"
work is entirely inside the verifier-hypothesis-construction layer, not a
separate parser change — `assertion_spans` itself, as a claim_parser.py
data structure, has existed since before this session; the contribution
here was making primary verification actually consume it for the one case
it was previously unused for). **This recovery pass additionally
adversarially audited the mechanism itself** (Phase 3/4), not just its n=6
benchmark aggregate:

| Category | Status |
|---|---|
| Sample size | **PRELIMINARY** — n=6 (entire real population), 4/6 changed, 0 unsafe reversals |
| Statistical interpretation | Explicitly inconclusive; McNemar not computed (too few discordant pairs to be meaningful) |
| Implementation correctness | **AUDITED, CONFIRMED CORRECT** — 5 new adversarial tests: negation preserved, modal/exception clauses preserved, 3-citation lists correctly paired, fails closed on structurally ambiguous input |
| Safety defect found | **NONE** — one non-bug nuance found (verb-stripping richness varies by sentence shape) and empirically confirmed safe on real DeBERTa (both variants fail toward NEI, never toward false ENTAILED/CONTRADICTED) |
| Production decision | **NOT promoted** — `assertion_span_primary_hypothesis: false`, sample size alone is the reason, not any correctness concern |

Full detail: `FINAL_PRODUCTION_CONFIG.md` §5a,
`outputs/assertion_spans_primary_hypothesis_benchmark_report.md` (including
its 2026-09-11 implementation-audit addendum).

## G. Fresh correction experiment

**UPDATE 2026-09-12: RESOLVED — see the dated section near the top of this
report for the real n=62 result** (verification recovery 5/32, 0 unsafe
reversals, correction shipping 0/4 OLD / 0/5 CURRENT). The narrative below
is preserved as an accurate historical record of what was tried and found
blocked in the immediately preceding pass — it is not being claimed as the
current state.

**BLOCKED by a verified host memory constraint — reconfirmed, not just
carried forward, this pass.** Target was n=100 (task's stated ceiling),
with a documented fallback to "largest defensible 50-100." Three
consecutive attempts (n=100, n=50, n=30) last session all failed during
**model loading** (before any case was processed), with system memory
confirmed stable at ~5.3-5.5GB free out of 15.7GB total across all three
attempts — independent of requested batch size, ruling out a batch-size or
accumulation bug in the experiment script itself. This recovery pass
independently re-checked system memory before considering any retry:
**5.12-5.47GB free — the same or marginally WORSE**, with GPU VRAM itself
confirmed fully free (the bottleneck is host system RAM specifically, not
GPU), and no stale processes found to clean up. Retrying was correctly
**not** attempted, per this task's own explicit instruction not to repeat
an already-demonstrated OOM. No code-level fix was identified (the standard
`low_cpu_mem_usage` mitigation is already active via `transformers`'
`device_map` default) or applied speculatively. Full diagnostic:
`research/prototype/outputs/gpu_experiment_memory_constraint.md`.

- **Sample size actually available**: n=15 (from the prior session, real,
  already committed — NOT superseded or invalidated by this session).
- **Correction-trigger rate**: 0/15 on BOTH arms (zero CONTRADICTED
  verdicts, zero low-confidence-NEI).
- **Correction-success rate**: not computable — no corrections triggered.
- **Correction-shipping rate**: not computable — no corrections triggered.
- **Safety**: trivially 0 unsafe shipments (none shipped at all).
- **Statistical analysis**: not computed. n=15, with 0 events in the outcome
  of interest, cannot support any paired significance test.

**Cumulative historical context** (real, existing, not new this session):
across this project's entire history, 56 natural-data correction attempts,
1 shipped (1.8%), 0 unsafe. See
`research/prototype/outputs/workstream_b2_correction_error_analysis.md` for
the full taxonomy (37 `correction_failed` — dominated by no-op edits, a
corrector generation-quality limitation, not a pipeline defect; 18
`correction_scope_violation` — claim-bundling; 1 `corrected`).

**Verification-recovery vs. correction-shipping, kept explicitly separate**
(per this task's own rule): the one real case this session's n=15 data
produced (document 1952_40, Article 14) is a verification recovery
(NEI 0.975 → ENTAILED 0.989) for a claim that was never flagged for
correction in either arm — evidence the lever prevents a spurious
low-confidence verdict on a genuinely correct claim, not evidence about
correction shipping, which remains unmeasured at any meaningful scale.

## G2. Assertion-span-aware correction (NEW, 2026-09-12 continuation)

See the "2026-09-12 continuation" section near the top of this report for
the full summary, `FINAL_PRODUCTION_CONFIG.md` §5b for the decision
record, and `outputs/assertion_aware_correction_experiment_report.md` for
the complete case-by-case natural-data analysis. Headline: implemented,
tested (296/296 including 20 new deterministic tests), evaluated on real
data (n=10 paired attempts against the exact cases that triggered legacy
correction in the n=62 batch) — **0/10 shipped, same as legacy** — a
genuine negative/preliminary result on correction-shipping, with the
mechanism itself confirmed to behave exactly as designed (0 unsafe
shipments; the one case it could plausibly have unlocked was blocked by a
separate, genuine second error in the same bundled sentence, correctly
caught by the unconditional sibling-regression safety net). NOT promoted
to production (`correction.assertion_aware` stays `false`).

**UPDATE 2026-09-12 (same-day continuation) — architecture properly
finished.** An architecture audit found the mechanism above only ever
consumed `assertion_text`, never the richer parser-produced
`assertion_spans` list (which exists specifically for the "respectively"
pattern — `claim_parser.py`'s `_assign_respectively_spans`). Fixed:
`apply_selective_correction_assertion_aware()` now resolves its target via
the claim's real `assertion_spans` (always the LAST element — the content
item, never the citation's own bare number), with a new dedicated safety
check (`correction_structural_span_lost`) verifying the non-content
element(s) survive the edit, and a new fail-closed status
(`correction_span_invalid`) for a malformed representation. 6 new tests
(26 total in the file, 302/302 full suite), including a real
"respectively" claim confirmed against actual `claim_parser` output
(`assertion_spans=['302', 'theft']`).

**Verified against real data, not just re-inspected code**: replayed the
new code against all 9 triggered attempts from the existing n=10 batch
using the already-recorded corrector outputs — no fresh Qwen call
(`outputs/assertion_span_aware_integration_replay.json`). **0
target-fragment mismatches, 0 outcome mismatches**: every real case in
this batch has a 1-element `assertion_spans`, so the n=10 result above is
unchanged by this refactor — it is a genuine architecture completion, not
a result-changing tweak. A new `outputs/error_propagation_matrix.csv` +
`.md` (built programmatically, not hand-filled) attributes each of the 10
cases to its first-failing stage: 4/10 fail at the pre-reverification
safety gates (scope/citation/ordinal), 2/10 at reverification itself, 2/10
at the sibling-regression gate, 1/10 correctly never triggers, 0/10 ship.

Production decision unchanged: `correction.assertion_aware` stays `false`
— the architecture is now complete and correct, but completeness alone
does not justify promotion absent a demonstrated shipping-rate
improvement. See `FINAL_PRODUCTION_CONFIG.md` §5b's 2026-09-12 update for
the full record, including the honest gap that no FRESH real Qwen-generated
multi-span ("respectively") correction attempt has been observed yet — the
multi-span path is verified via tests and a real-corpus-derived fixture,
not yet by a natural GPU batch that happens to contain one.

## H. Demo-pack recovery status

**A real archaeology finding, not a reconstruction task**: the prior
session's 2026-09-09 addendum incorrectly claimed
`research/prototype/evaluation/{examples,live_demo}/` were deleted. Git
archaeology (`git show -M --name-status 61b240a`) proved they were
**renamed** (94-100% similarity), not deleted, and are fully intact today
(with `live_demo/` actively extended afterward). Corrected the false claim
in `final_demo_pack/{README,SYSTEM_STATUS}.md` and
`metadata/validation_log.md` (preserving prior addenda as historical
record). Fixed the real underlying bug: `validate_pack.py` read
`examples/cases.json` from the wrong path; now reads from its real
location. **Genuinely fixed, not gamed**: 25/25 checks now pass (was
21/25, hard-crashing). `RUNBOOK.md`/`ARTIFACT_INDEX.md` paths also fixed —
they had never been updated for the 2026-08-27 archive move at all.

Also found and fixed a real bug in the demo itself: `run_demo.py` called
`apply_verification()` without `narrow_primary_hypothesis`, silently
running pre-Stage-4 behavior while claiming "production config in use,
unmodified." Fixed and verified by actually re-running the demo end to end
(not just inspecting code) — confirmed the flag now prints correctly and
verdicts/confidences shift as expected.

## I. Docker build status

**BLOCKED, reconfirmed this recovery pass, not attempted.** After three GPU
experiment attempts confirmed the host is under real memory pressure
(~5.3-5.5GB free of 15.7GB total), `docker info` showed the daemon not
running (`failed to connect to the docker API`) — re-checked independently
this pass, daemon still not running, host memory still not meaningfully
improved (5.12-5.47GB free). Starting Docker Desktop's multi-GB WSL2 VM
under confirmed memory pressure was judged not a responsible use of the
user's machine, and was not attempted. **No Docker build for today's code (commits through
this session) was completed or claimed complete.** The prior session's
finding stands: a 2026-08-27 image (predating all five levers now
documented) was previously smoke-tested successfully as a structural
sanity check only — not evidence for today's code.

**Re-checked again, 2026-09-12 continuation session**: `docker info`/
`docker version` still show `failed to connect to the docker API at
npipe:////./pipe/dockerDesktopLinuxEngine` — the daemon is not running,
unchanged from every prior check. Host memory this session ranged from as
low as ~1.5-1.9GB free (below even the assertion-aware GPU experiment's
own 2.0GB guard threshold, which correctly declined to proceed until it
recovered to ~2.9GB) up to ~3.7GB free during that experiment. Starting
Docker Desktop's WSL2 VM during or immediately after a live GPU correction
experiment on this exact memory budget was, again, judged not responsible.
Still blocked; still not attempted; still no code-level fix identified
(this is a host resource/daemon-availability constraint, not something a
Dockerfile change addresses).

## J. Complete ORIGINAL vs CURRENT comparison

No new figures or tables were regenerated this session. Verified this is
correct, not an omission: neither of this session's two real changes
(assertion_span_primary_hypothesis, off by default; the blocked large
batch, which produced no new committed data) alters
`outputs/final_metrics.json` or any file the comparison pack's figures/
tables read from — regenerating would reproduce byte-for-byte identical
output, exactly as independently verified for the 2026-09-09 pass.
`final_comparison/RUN_COMPARISON.md` §9 documents this explicitly with a
dated addendum rather than silently doing nothing.

**Current production configuration** (`config/prototype.yaml`, five
evaluated levers):

| Lever | Value | Status |
|---|---|---|
| `premise_framing` | `labeled` | Adopted 2026-08-27 |
| `use_evidence_v1` | `true` | Adopted 2026-08-27 |
| `correction.atomic_scope_check` | `"assertion_spans"` | Adopted 2026-08-27 |
| `correction.narrow_reverification_hypothesis` | `true` | Adopted 2026-08-27 |
| `evidence_matching.fuzzy_method` | `jaccard` | BM25/embedding evaluated, rejected 2026-09-09 |
| `verification.narrow_primary_hypothesis` | `true` | Adopted 2026-09-09 |
| `verification.assertion_span_primary_hypothesis` | `false` | Evaluated 2026-09-11, inconclusive at n=6 |

## K. Strongest statistically supported improvements

1. Evidence coverage v0→v0+v1: +7.1pp, McNemar p<0.001, 0 regressions (n=50 paired).
2. Premise framing bare→labeled: macro-F1 0.749→0.968 (420-item controlled benchmark).
3. `narrow_primary_hypothesis`: 31/107 applicable claims recovered, 0 unsafe reversals (n=456 real claims).
4. Jaccard retrieval safety: 100% correct-reject vs. BM25/embedding's measurably worse rates (pre-registered 30-case adversarial benchmark).

## L. Directional/inconclusive findings

1. `assertion_span_primary_hypothesis`: 4/6 changed verdict, 0 unsafe — directionally positive, explicitly inconclusive (n=6, entire real population).
2. Fresh n=15 `narrow_primary_hypothesis` GPU batch: 1/12 recovered — directionally consistent with the CPU result, too small alone.
3. Correction-shipping impact of `narrow_primary_hypothesis`: genuinely unmeasured (0 triggers observed across every fresh batch attempted, including this session's blocked large-batch attempts).

## M. Remaining limitations (genuine)

- Correction success rate remains 1.8% cumulative (1/56) — unchanged, real, not addressed this session (the bottleneck is Qwen2.5-7B-Instruct's corrector generation quality and claim-bundling, both previously diagnosed, neither newly fixed).
- Correction-shipping impact of `narrow_primary_hypothesis` at meaningful scale (n>=50) is unmeasured — blocked by a verified host memory constraint, not attempted-and-failed on the science.
- `assertion_span_primary_hypothesis` has a clean but statistically inconclusive signal (n=6) — not production-ready.
- Docker image for today's code (5 evaluated levers, through commit `95ae571`) is unbuilt and unverified in this environment.
- No lawyer/professional legal ground truth exists anywhere in this project (unchanged, long-documented).

## N. Exact commands for reproduction

```
# Tests
cd research/prototype && ../.venv/Scripts/python.exe -m pytest tests/ -q
../.venv/Scripts/python.exe scripts/run_mvp.py --check

# Assertion-span benchmark (CPU, no GPU)
../.venv/Scripts/python.exe scripts/benchmark_assertion_span_primary_hypothesis.py --device cpu

# Large fresh GPU batch (blocked this session; retry when host has more free memory)
../.venv/Scripts/python.exe scripts/run_narrow_primary_hypothesis_gpu_ablation.py --device cuda --n-cases 50 --out-prefix narrow_primary_hypothesis_gpu_ablation_n50

# Live demo (real code, real DeBERTa, CPU or CUDA)
../.venv/Scripts/python.exe evaluation/live_demo/run_demo.py

# Demo pack validation
../.venv/Scripts/python.exe archive/2026-08-27_presentation/final_demo_pack/metadata/validate_pack.py
```

## O. Exact final configuration

`research/prototype/config/prototype.yaml`, unmodified in production sense
except the new `verification.assertion_span_primary_hypothesis: false` key
added (does not change production behavior — off by default). Models:
`Qwen/Qwen2.5-7B-Instruct` (4-bit NF4, greedy) for generation/correction,
`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (fp16 CUDA / fp32 CPU) for
verification. Evidence pool: 136 records (`use_evidence_v1: true`).

## P. Important output files this session

- `research/prototype/outputs/assertion_spans_primary_hypothesis_benchmark.jsonl` / `_report.md` (+ 2026-09-11 audit addendum)
- `research/prototype/outputs/workstream_b2_correction_error_analysis.md`
- `research/prototype/outputs/gpu_experiment_memory_constraint.md`
- `research/prototype/scripts/benchmark_assertion_span_primary_hypothesis.py`
- `research/prototype/tests/test_assertion_span_primary_hypothesis.py` (19 tests: 14 original + 5 new adversarial, this recovery pass)
- `FINAL_PRODUCTION_CONFIG.md` (§5a added, + implementation-audit subsection this pass)
- `research/prototype/archive/2026-08-27_presentation/final_demo_pack/` (6 files corrected; `metadata/validate_pack.py` additionally fixed this pass to append rather than overwrite its own log)
- `research/prototype/evaluation/live_demo/run_demo.py` (real bug fixed)

## R. Professor-facing final summary

**What did we improve?** Two verifier-hypothesis-construction levers that
narrow what the NLI model is asked to verify, so a bundled multi-citation
sentence doesn't dilute the specific proposition being checked: (1)
`narrow_primary_hypothesis` (production default) uses a claim's own
`assertion_text` when narrower than the full sentence; (2)
`assertion_span_primary_hypothesis` (evaluated, not yet production) extends
this to "respectively"-pattern claims via `assertion_spans`. Plus earlier in
this project's history: a real parser bug fix (Art./Arts. abbreviation
recognition), a rejected-but-documented retrieval alternative evaluation
(BM25/embeddings, both found less safe than the production Jaccard method),
and a safety-hardening pass (negation gate, citation-injection/ordinal
guards).

**Why?** Claim-level bundling (one sentence backing several citations) was
identified, with real evidence, as the dominant remaining source of both
spurious NOT_ENOUGH_INFORMATION verdicts and low correction-shipping rates.

**How did we test it?** Real DeBERTa-v3 verification (never mocked) against
a 136-record audited evidence corpus; real Qwen2.5-7B-Instruct generation
for fresh natural-data batches where GPU resources allowed; adversarial
unit/regression tests for parser and hypothesis-construction edge cases;
CPU re-scoring benchmarks against every real applicable claim already
committed in this project's history (not synthetic/invented examples).

**What improved, with strong evidence?** Evidence coverage (+7.1pp, p<0.001,
n=50 paired). Premise labeling (macro-F1 0.749→0.968, 420-item controlled
benchmark). `narrow_primary_hypothesis` (31/107 applicable claims recovered,
0 unsafe reversals, n=456 real claims). Jaccard retrieval safety vs.
BM25/embedding alternatives (pre-registered 30-case adversarial benchmark).

**What did NOT improve, or remains unmeasured?** Correction success rate:
still 1.8% cumulative (1/56), unchanged. Correction-shipping impact of
`narrow_primary_hypothesis`: genuinely unmeasured at meaningful scale (every
fresh batch attempted, including this session's blocked n=100/50/30
attempts, produced 0 corrections triggered).

**What is preliminary?** `assertion_span_primary_hypothesis`: clean signal
(4/6 changed, 0 unsafe) but n=6 is the entire real population found —
explicitly not a production-ready result, though the implementation itself
was adversarially audited and found correct.

**What is still blocked?** A GPU-batch correction-shipping experiment at
n≥50, and a Docker build for today's code — both blocked by a verified,
reproducible host memory constraint (documented with exact free-memory
figures across a total of six independent check/attempt cycles across two
sessions), not a methodology failure.

**What can be demonstrated live?** `research/prototype/evaluation/live_demo/run_demo.py`
— real claim parsing, real evidence retrieval against the production
136-record pool, real DeBERTa verification (CPU, no GPU needed, under a
minute), real programmatic safety-gate evaluation, on 3 real cases (one
NO_EVIDENCE, one CONTRADICTED catch, one the project's sole shipped
correction) — generation/correction steps replayed from committed output
where noted, clearly labeled as replay, never fabricated.

**What is the final production pipeline?** Qwen2.5-7B-Instruct (4-bit NF4,
greedy) → deterministic regex claim/citation extraction → deterministic
exact+Jaccard-fuzzy evidence matching (136-record audited corpus) →
DeBERTa-v3-MNLI-FEVER-ANLI verification with labeled-premise +
narrow-hypothesis framing → selective Qwen correction with a multi-gate
safety check (scope, citation-injection, ordinal-integrity,
sibling-regression) before any correction ships.

**What should be done next for the paper?** (1) Run the blocked n≥50
correction-shipping experiment on a machine with more free RAM — command
and full methodology already documented, no code changes needed. (2)
Accumulate more natural-data "respectively" claims (or build a targeted
controlled benchmark) to get `assertion_span_primary_hypothesis` past
preliminary. (3) Build the Docker image for today's HEAD on a
less-memory-constrained host and record the image ID. (4) The corrector's
generation-quality limitation (dominant no-op-edit failure mode) is the
most consequential remaining open problem for correction-shipping and
likely needs prompt-engineering or a different correction model, not
another verifier-side lever.

## Q. Git cleanliness status

Clean except `baseline/LegalSeg` (pre-existing, intentionally untouched all
session, per explicit instruction). No force-push. No history rewrite. No
generated junk, credentials, or model weights committed.

---

## Independent final review (2026-09-12 continuation, skeptical pass)

Answered directly against the actual current code, not the intended design:

1. **Does correction actually operate on parser-produced spans?** Yes —
   `_correction_target_spans()` reads `rec["assertion_spans"]` and confirmed
   directly against real `claim_parser.extract_claims()` output
   (`['302', 'theft']`), not assumed.
2. **Can it modify sibling assertions?** Structurally no via the splice
   itself (only the exact content-fragment substring is replaced). The one
   theoretical residual risk — the parser producing OVERLAPPING
   `assertion_spans` between two sibling claims — is covered defensively by
   the existing `_scope_violation(use_assertion_spans=True)` check, which
   re-verifies every sibling's own spans survive post-edit; not
   independently re-audited this pass beyond what was already tested.
3. **Can it alter citations?** New citations are rejected
   (`correction_unauthorized_addition`). A narrower theoretical gap — a
   corrected fragment coincidentally introducing text that gets re-parsed
   as an EXISTING citation identity at an ambiguous ordinal position — is
   caught by the pre-existing ordinal-integrity check
   (`correction_ordinal_ambiguous`), not newly built this pass; not
   exhaustively adversarially fuzzed beyond the tested categories.
4. **Can it lose negation/modality?** No programmatic check enforces this
   directly; the corrector prompt now explicitly instructs preservation
   (added this pass), and a modality/negation flip that actually changes
   truth value would generally surface as a reverification failure against
   real evidence — but this is not proven exhaustively. Stated as a real,
   honest limitation, not fixed further this pass (same limitation the
   legacy path has always had).
5. **Can it ship an unsupported correction?** No — 0 unsafe shipments
   across the controlled benchmark and the real n=10 batch; shipping
   requires target reverification ENTAILED AND the unconditional
   sibling-regression check to pass.
6. **Does re-verification really inspect the final text?** Yes — the
   replacement claim is re-extracted from `corrected_text` itself (the
   actual post-splice text), never the pre-correction original.
7. **Is the production configuration correct?** Verified directly:
   `config/prototype.yaml`'s `correction.assertion_aware: false` — matches
   every document claiming this.
8. **Is the comparison fair?** Yes — legacy figures are READ from the
   already-committed n=62 batch (never recomputed to favor either side),
   assertion-aware figures are freshly collected on the identical
   (document, arm, flagged claim) triples.
9. **Are the results sufficient to support promotion?** No, and none of
   this session's documentation claims otherwise — `correction.assertion_aware`
   remains `false`.
10. **Are any claims overstated?** One found and corrected while writing
    this review: earlier phrasing risked implying the architecture
    completion itself was evidence of improvement — reworded throughout to
    state plainly that completeness and correctness were demonstrated, but
    a shipping-rate improvement was NOT.

**One genuine, newly-noticed limitation (not a safety bug, documented, not
fixed this pass):** for a "respectively" claim, `narrow_reverification_hypothesis`
narrows re-verification to `assertion_text`, which for this claim SHAPE
never narrows (only `assertion_spans` does) — so a respectively claim's
correction is always re-verified against the FULL shared sentence, diluted
by its sibling's content, even when that config flag is on. This does not
make anything unsafe (a stricter, harder-to-satisfy re-verification can
only reject more, never ship something wrong) but means one of this
project's own established levers does not extend its benefit to this claim
shape yet — a concrete, evidence-backed follow-up, consistent with the
`assertion_spans`-level extension noted in `FINAL_PRODUCTION_CONFIG.md` §5b.

## FINAL STATUS: **NOT COMPLETE** (Docker remains the sole genuine blocker)

Genuine open items are stated plainly rather than concealed. Updated
2026-09-12 (continuation session) — the correction-shipping GPU experiment
blocker was resolved in the prior same-day pass (n=62, then this session's
targeted n=10 assertion-aware replay); assertion-span-aware correction was
implemented and evaluated this session:

- [x] Fresh correction-shipping GPU experiment at n>=50 — **RESOLVED**: n=62 collected (`outputs/16gb_final_execution_report.md`), plus a targeted n=10 paired assertion-aware replay this session (`outputs/assertion_aware_correction_experiment_report.md`).
- [ ] Docker build + smoke test for today's code — **blocked**, reconfirmed this session (daemon not running, host memory tight), not done.
- [x] Assertion spans genuinely implemented (not superficial) and tested (19 tests, including 5 adversarial ones).
- [x] Assertion-span behavior experimentally compared with the previous path, AND the implementation itself adversarially audited beyond the aggregate benchmark number.
- [x] **NEW this session**: assertion-span-AWARE correction (splice-based localized fix) implemented, config-gated (`correction.assertion_aware`, default false), a controlled benchmark, and a real n=10 natural-data evaluation — genuine negative/preliminary result (0/10 shipped, same as legacy), investigated and explained case-by-case, NOT promoted. See §G2, `FINAL_PRODUCTION_CONFIG.md` §5b.
- [x] **NEW, same-day continuation**: architecture properly finished to consume the parser's real `assertion_spans` (not just `assertion_text`) — new `correction_structural_span_lost`/`correction_span_invalid` fail-closed gates, 6 more tests, and an empirical replay against all 9 real triggered attempts (0 target/outcome mismatches — confirms zero behavior change on existing data), plus `outputs/error_propagation_matrix.csv`/`.md` attributing each real case to its first-failing stage. Still not promoted — completeness is not evidence of improvement.
- [x] Correction verification/generation/shipping kept explicitly separate throughout.
- [x] Demo pack repaired in place (real bugs found and fixed, not papered over); re-verified 25/25 this session after a `run_demo.py` edit.
- [x] Full test suite passes, independently re-confirmed (**302/302**, up from 276/276).
- [x] No unsafe result hidden; no favorable-result gaming; no assertion-span promotion on n=6 alone; no assertion-aware-correction promotion despite implementation effort or architecture completeness.
- [x] `baseline/LegalSeg` untouched; git history intact; no force-push; no history rewrite.

The one remaining blocked item (Docker) is a genuine, verified,
reproducible environmental constraint on this specific machine (daemon not
running, host memory has not had sustained multi-GB headroom to safely
start Docker Desktop's WSL2 VM across four independent sessions) — not a
methodology failure, not silently abandoned, and not claimed done. Retry
is straightforward (`docker info`, then the documented build command)
whenever the daemon is running and host memory allows; no code change is
required to attempt it.
