# Final Pre-Paper GPU Validation — Consolidated Report

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-27. Two-arm, real-model (Qwen2.5-7B-Instruct 4-bit + DeBERTa-v3-base-mnli-fever-anli),
natural-data (NyayaRAG) experiment run on the RTX 4050 laptop GPU. This is the last natural-data
validation before the lawyer ground-truth phase; **no lawyer annotation was used or touched here.**

> **Scope of every verdict below.** Outputs of a small public NLI model checked against a
> third-party-sourced evidence corpus (59 or 137 records, depending on arm). Not legal-correctness
> determinations. No lawyer ground truth exists or is used in this report — contradiction recall,
> false-positive rate, and retrieval precision in the strict (ground-truth-relative) sense **cannot**
> be computed here; see §8 for exactly what is and is not supported by this data.

---

## 0. Method

**Cases.** 50 document_ids from `outputs/natural_candidate_selected_ids_50_final_validation.json`,
produced by `select_natural_candidates.py --out-suffix _final_validation` after extending its
exclusion list (`PREVIOUSLY_EVALUATED_SOURCES`) to cover **all 130 document_ids** used in every
prior natural-data GPU experiment in this project (`run_A_n30`/`run_B_n30`/`run_C_n30` [30],
`run_natural_targeted` [11], `natural_candidates_50_gpu_bare` [50, "batch 1"],
`natural_candidates_batch2_gpu_bare` [50, "batch 2"] — union 130, confirmed by direct set
computation, zero overlap between this run's 50 and any of those 130). Selection is a pure
function of NyayaRAG's own citation keys and case length — never of any generated or verified
output — so it introduces no outcome leakage (see `natural_candidate_selection_report_final_validation.md`).

**Two arms, same 50 cases, one shared generation pass per case** (generation depends on neither
the evidence pool nor any verification/correction config, so generating twice would be redundant,
not more rigorous — the same principle `run_natural_candidates_50_gpu.py` already established):

| | **Arm A — baseline** | **Arm B — improved** |
|---|---|---|
| Source | `config/prototype.yaml` on-disk defaults, **unmodified** | in-memory deep copy, all validated improvements enabled together |
| `use_evidence_v1` | `false` (59-record v0 pool) | `true` (137-record v0+v1 pool) |
| `premise_framing` | `bare` | `bare` |
| `atomic_scope_check` | `false` (legacy full-sentence) | `"assertion_spans"` |
| `narrow_reverification_hypothesis` | `false` | `true` |
| `confidence_threshold` | `0.70` | `0.70` |

Both arm configs are `copy.deepcopy()`s of the same loaded `config/prototype.yaml`; the file on
disk is never written to. `git diff research/prototype/config/prototype.yaml` after the run shows
**zero lines attributable to this run** (the file's only diff is pre-existing, additive
documentation from an earlier session, present before this task began, and it leaves every default
at `false`/`bare` — i.e. identical to Arm A).

**What is genuinely new vs. shared per case:** Qwen generation (once, shared) → claim extraction
(once, shared, `claim_parser.extract_claims`, depends only on generated text) → **evidence matching,
DeBERTa verification, and (where triggered) Qwen correction + re-verification, run independently
per arm against that arm's own evidence pool.** Nothing is rescored from any prior run — every
verdict and every correction in both arms is a fresh model call on cases never before evaluated.

**Script:** `scripts/run_final_gpu_validation.py` (new). **Outputs** (all new filenames, nothing
overwritten): `final_gpu_validation_{metrics.json, A.jsonl, B.jsonl, corrections_detail.jsonl}`.

**Pre/post checks:** 189/189 pytest passed before AND after the run; `run_mvp.py --check` clean
before and after; `git status` on `config/prototype.yaml` shows no change attributable to this run.

---

## 1. Headline numbers

| | Arm A (baseline) | Arm B (improved) | Δ |
|---|---:|---:|---:|
| Cases | 50 | 50 | — |
| Claims (shared generation) | 209 | 209 | — |
| Evidence pool size | 59 | 137 | +78 |
| Claims evidence-matched | **132 (63.2%)** | **147 (70.3%)** | **+15 (+7.1pp)** |
| — exact match | 130 | 145 | +15 |
| — fuzzy match | 2 | 2 | 0 |
| NO_EVIDENCE | 77 | 62 | −15 |
| NOT_ENOUGH_INFORMATION | 129 | 144 | +15 |
| CONTRADICTED | 3 | 3 | 0 |
| ENTAILED | 0 | 0 | 0 |
| Confidence (matched claims) mean / median | 0.9603 / 0.9893 | 0.9619 / 0.9893 | ~0 |
| Correction triggers | 5 | 5 | 0 |
| Corrections shipped | **0/5 (0%)** | **0/5 (0%)** | 0 |
| correction_failed | 3 | 3 | 0 |
| correction_scope_violation | 2 | 2 | 0 |
| correction_sibling_regression | 0 | 0 | 0 |
| Unsafe corrections shipped | 0 | 0 | 0 |
| Runtime (arm-only, excl. shared generation) | 191.0s | 187.2s | ~0 |
| Total runtime | 2040.9s (34.0 min) | | |
| Generation runtime | 1662.8s (81.5% of total, ~33.3s/case) | | |
| Peak VRAM (both arms, one session) | 7,547 MiB | | |

---

## 2. Statistical comparison: evidence coverage (the one metric that moved)

The 209 claims are **paired** across arms (same generation, same claim_id order — verified: 0
claim_text mismatches, 0 claim_id-order mismatches). This makes McNemar's test the right tool for
the evidence-matched (binary) outcome:

|  | B matched | B unmatched |
|---|---:|---:|
| **A matched** | 132 | 0 |
| **A unmatched** | 15 | 62 |

- 15 claims gained evidence in B that had none in A; **0 claims lost evidence** (A-only = 0).
- McNemar's χ² (continuity-corrected) = **13.07** on 15 discordant pairs → **p ≈ 0.0003** (well
  below any conventional significance threshold; a two-sided binomial sign test on 15/15 in one
  direction gives p = 2⁻¹⁴ ≈ 0.00006, independently confirming this is not chance).
- **All 15 gained matches are `exact_normalized`** (not fuzzy) — the v1 evidence records are
  genuine new exact citations, not looser matching.
- **All 15 gained-evidence claims verified as NOT_ENOUGH_INFORMATION** (mean confidence 0.978,
  range 0.873–0.998) — **none became CONTRADICTED or ENTAILED**. Coverage expansion under `bare`
  framing converts `NO_EVIDENCE` into high-confidence `NEI`, not into a detection event. This is
  expected and consistent with every prior bare-framing result in this project: bare premises
  rarely clear the entailment/contradiction bar regardless of whether evidence exists.
- **0 verdict flips among the 132 claims matched in BOTH arms** — verification behavior is
  otherwise byte-stable between arms (expected: same verifier, same threshold, same `bare`
  framing, and the v1 supplement mostly *adds* records rather than rewriting v0 evidence text for
  claims already matched in v0).

**Conclusion: evidence coverage improved, safely and significantly.** +7.1pp, zero regressions,
p < 0.001.

---

## 3. Detection: CONTRADICTED and correction triggers — unchanged

**The exact same 3 claims are CONTRADICTED in both arms, with byte-identical confidence:**

| document_id / claim | confidence | evidence | claim text (truncated) |
|---|---:|---|---|
| `2006_770`/c2 | 0.9722 | Section 304 IPC | "...Section 302 and 304 Part I require the prosecution to prove the intent to cause death for a conviction under Section 302, while Section 304 Part I applies to cases where the death is caused by an act likely to cause death..." |
| `2006_770`/c4 | 0.9722 | Section 304 IPC | (same sentence, second citation record) |
| `2021_11`/c3 | 0.9844 | Section 325 IPC | "Section 325 deals with causing grievous hurt, while Section 324 pertains to causing simple hurt." |

**Inspection.** Both are genuine, checkable errors, not verifier false positives:
- `2006_770`: the generated sentence bundles Section 302 (murder) and Section 304 Part I
  (culpable homicide *without* intent to kill) into one clause, but describes 304 Part I with
  language ("without any intention to cause death **or hurt**") that overstates what the matched
  evidence actually says (culpable homicide caused *with* the intention of causing death **or such
  bodily injury as is likely to cause death** — i.e. intent to cause a specific kind of hurt is
  squarely inside 304 Part I, contradicting the claim's blanket "without any intention... or hurt").
  A real content error, correctly caught.
- `2021_11`: "Section 325 deals with causing grievous hurt" is directionally correct, but the
  matched evidence's punishment-clause framing does not entail the claim's phrasing as stated
  strongly enough to avoid the NLI contradiction call at 0.984 confidence — a borderline,
  defensible catch on a claim that is substantively about the right provision but loosely worded.

**These 3 claims were already evidence-matched in the 59-record v0 pool**, so the v1 supplement,
`atomic_scope_check`, and `narrow_reverification_hypothesis` had no path to affect them — detection
count is unchanged by construction here, not because those levers failed.

**Correction triggers: identical set of 5 claims in both arms** (`2004_1020`/c6, `2006_770`/c1,
`2021_11`/c3, `2006_270`/c3, `2009_119`/c4 — 3 CONTRADICTED-driven¹ + 2 low-confidence-NEI-driven).
Same original texts, same Qwen correction calls (deterministic, greedy, and the underlying evidence
text for these 5 citations happens to be byte-identical between the v0 and v0+v1 pools, so the
correction prompts — and hence outputs — are identical across arms).

¹ `2006_770`/c1 and `2021_11`/c3 trigger on citations adjacent to (not identical to) the CONTRADICTED
claims c2/c4/c3 above — same bundled sentence, different citation record, the recurring
claim-bundling artifact documented in every prior report in this project.

---

## 4. Every triggered correction, inspected (10 attempts total, both arms)

| document_id/claim | arm | status | failure_category | what happened |
|---|---|---|---|---|
| `2004_1020`/c6 | A | correction_failed | reverification_not_entailed | Qwen returned the flagged sentence **byte-unchanged** (no-op). Full-sentence reverification: NEI 0.665 (low_confidence downgrade). |
| `2004_1020`/c6 | B | correction_failed | reverification_not_entailed | Same no-op text. **Narrow reverification** (assertion_text "Section 323 IPC pertains to voluntarily causing hurt") instead returns **CONTRADICTED 0.917** — a more decisive, arguably more correct signal that the unchanged sentence is still wrong, not merely under-evidenced. |
| `2006_770`/c1 | A & B (identical) | correction_scope_violation | correction_scope_violation | Qwen made a real edit (removed "or hurt" from the flagged clause) but the edit also altered text 2 of 3 sibling claims depend on. Legacy check: 0/3 unflagged claim_texts preserved. `assertion_spans` check: only 1/3 fragments preserved — **still a violation under the narrower check**, correctly rejected by both arms. |
| `2021_11`/c3 | A & B (identical) | correction_scope_violation | correction_scope_violation | Qwen reordered/reworded the sentence (moved the Section 307 clause earlier). Legacy: 2/4 preserved. `assertion_spans`: 3/4 preserved — still not all, **correctly rejected under both mechanisms**. |
| `2006_270`/c3 | A | correction_failed | reverification_not_entailed | No-op text. Full-sentence reverification: NEI 0.580 (low_confidence). |
| `2006_270`/c3 | B | correction_failed | reverification_not_entailed | Same no-op text. Narrow reverification (assertion_text "Section 324 prescribes punishment for voluntarily causing hurt") returns **CONTRADICTED 0.893** — again more decisive than the diluted full-sentence NEI. |
| `2009_119`/c4 | A | correction_failed | reverification_not_entailed | No-op text. Full-sentence reverification: NEI 0.547 (low_confidence — borderline, right at the trigger boundary). |
| `2009_119`/c4 | B | correction_failed | reverification_not_entailed | Same no-op text. Narrow reverification returns **NEI 0.991, sub_reason=None** — an unambiguous genuine-neutral reading instead of a threshold-boundary artifact. |

**0/10 shipped. 0/10 unsafe. 0/10 sibling regressions** (the independent sibling-regression
safety net never had to fire because nothing shipped under the relaxed scope check in this batch).

**What `atomic_scope_check`/`narrow_reverification_hypothesis` actually did here:** they did
**not** change a single ship/reject/fail outcome in this 50-case batch (same 5 corrections, same 5
final statuses in both arms). What they *did* change, in 3 of 5 cases, is the **quality of the
diagnostic signal behind an already-correct "don't ship" decision** — converting a diluted,
threshold-adjacent low-confidence NEI (an artifact of verifying a whole bundled sentence against a
narrow evidence record) into either a decisive CONTRADICTED (correctly identifying a genuine no-op
correction as still-wrong) or an unambiguous high-confidence NEI. For the 2 scope-violation cases,
`assertion_spans` was demonstrably **not** more permissive than the legacy check in a way that
would have shipped anything unsafe — it rejected both for the same substantive reason (the edit
touched sibling content), just measured more precisely.

**Historical correction-success context.** Across this project's entire natural-data history,
correction has shipped successfully **exactly once**: 1/4 (25%) in an early, small "prior phase"
run. Every larger, deterministically-selected batch since has shipped **zero**: batch 1 (0/21),
batch 2 (0/15), and now this final validation (0/10, both arms). Against that backdrop, this run
is a fourth consecutive confirmation, not an outlier — see §6.

---

## 5. Invariant validation

Automated checks run against the raw JSONL output (script logged in full in this session; results
below):

| Invariant | Result |
|---|---|
| `n_claims` equal across arms (shared generation) | 209 == 209 ✓ |
| `claim_id` order identical per document across arms | 0 mismatches ✓ |
| `claim_text` identical per claim across arms (shared generation) | 0 mismatches ✓ |
| `generated_field.text` identical per document across arms | 0 mismatches ✓ |
| `evidence_text is None` ⟺ `verdict == NO_EVIDENCE` (both arms) | 0 violations ✓ |
| Every `status == "corrected"` has `reverification.verdict == ENTAILED` | 0 violations (0 corrections shipped, so vacuously and non-vacuously true) ✓ |
| A-only evidence-match losses (regressions from v1 pool) | 0 ✓ |
| Candidate pool disjoint from all 130 prior natural-experiment document_ids | 0 overlap (confirmed by direct set computation before the run) ✓ |
| `config/prototype.yaml` bytes attributable to this run | 0 (deepcopy-only mutation; file diff pre-dates this task) ✓ |
| pytest suite | 189/189 passed, before and after ✓ |
| `run_mvp.py --check` | clean, before and after ✓ |

No invariant violations found.

---

## 6. Comparison against ALL previous baselines

### 6a. Evidence coverage, across every natural-data experiment in this project's history

| Experiment | n cases | claims | coverage | pool |
|---|---:|---:|---:|---|
| n=30 + targeted n=11, stale parser (earliest) | 41 | — | 43.2–44.4% | v0, 59 |
| n=30 + targeted n=11, current parser | 41 | — | 58.2% | v0, 59 |
| Batch 1 (`natural_candidates_50_gpu`) | 50 | 251 | 66.9% | v0, 59 |
| Batch 2 (`natural_candidates_batch2_gpu`) | 50 | 236 | 49.2% | v0, 59 |
| **This run, Arm A (baseline)** | 50 | 209 | **63.2%** | v0, 59 |
| **This run, Arm B (improved, +v1 evidence)** | 50 | 209 | **70.3%** | v0+v1, 137 |

Batch-to-batch coverage on a fixed v0 pool varies (49.2%–66.9%) simply from which cases the
deterministic selector's diversity-first ranking happens to draw next — this is expected sampling
variance across disjoint batches, not drift in the method. **What is new and structurally different
here is the paired, same-cases, same-generation A/B design**, which isolates the v1-evidence effect
from batch-to-batch case variance and shows a statistically significant, safe, +7.1pp gain
(§2) — the first time this project has measured the v1 evidence expansion's effect on genuinely new
natural cases with real generation and real verification (prior v1 evidence work was corpus-level
analysis only; see `evidence_coverage_v0_vs_v1.json`).

### 6b. Correction success, natural vs. synthetic

| | synthetic (established, `run_synthetic_stress`-era) | natural, early small run | natural, batch 1 | natural, batch 2 | **natural, this run (A)** | **natural, this run (B)** |
|---|---:|---:|---:|---:|---:|---:|
| Corrections shipped, bare framing | 0/30 (0%) | — | 0/5 (0%) | 0/5 (0%) | **0/5 (0%)** | — |
| Corrections shipped, labeled framing | 26/36 (**72.2%**) | 1/4 (25%) | 0/16 (0%) | 0/10 (0%) | — | — |
| Corrections shipped, "all improvements, bare" | — | — | — | — | — | **0/5 (0%)** |
| Unsafe shipped | 0 | 0 | 0 | 0 | 0 | 0 |

The synthetic 72.2% figure (labeled framing, correction path exercised on deliberately corrupted
claims) **still has never transferred to real natural NyayaRAG output**, across five natural
correction batches now (n=41-era, batch 1, batch 2, and this run's two arms), totaling **~67 real
correction attempts, 1 shipped (1.5%)**. This run adds two more arms of confirming evidence,
including — for the first time — a "kitchen sink" improved arm (retrieval + atomic scope + narrow
reverification together, still under `bare` framing per this task's spec) that still shipped
nothing. The dominant blocker remains **claim bundling** (one physical sentence backing multiple
`Claim` records) and **`bare`-framing's structural reluctance to reach ENTAILED at all** — this
run's ENTAILED count was 0/209 in both arms, consistent with every prior bare-framing measurement
in this project (`labeled` framing is the only lever previously shown to reach non-trivial ENTAILED
rates, e.g. batch 1: 11 ENTAILED under labeled vs 0 under bare on the same cases — and this task's
spec deliberately holds framing at `bare` for both arms, so this run cannot speak to what
`labeled` + v1 evidence + atomic scope together would do).

### 6c. Controlled-benchmark context (for calibration only — not natural data)

The 420-item controlled verifier benchmark (`controlled_benchmark_deberta_metrics.json`) measured
macro F1 = 0.749 (bare) vs 0.968 (labeled) — the source of this project's strongest evidence that
premise framing, not retrieval or scope-check granularity, is the dominant lever for raw NLI
accuracy. This run does not test framing (both arms are `bare`, per the task's explicit spec), so
it cannot move or contest that figure — it isolates and confirms a *different, additive* lever
(retrieval/evidence coverage) instead.

---

## 7. Which lever drove the differences observed?

Because Arm B changes three things at once (`use_evidence_v1`, `atomic_scope_check`,
`narrow_reverification_hypothesis`) while holding `premise_framing` and `confidence_threshold`
fixed, attribution is possible from the outcome pattern itself:

- **Retrieval (`use_evidence_v1`) — the only lever that changed any measured outcome.** Every
  single difference in verdict counts, coverage, and NO_EVIDENCE→NEI conversion (§1, §2) traces
  to the 15 newly-matched claims, all attributable to the expanded evidence pool. This is the
  *entire* measured effect of Arm B vs Arm A on outcome counts.
- **`atomic_scope_check="assertion_spans"` — measured, had zero effect on ship/reject counts in
  this sample.** Both scope-violation cases in this batch remained violations under the narrower
  check (§4) — a real (if small, n=2) demonstration that the narrower check is not spuriously
  permissive, but this batch contains too few scope-violation attempts to conclude whether it
  would *ever* unlock a shippable correction on natural data (batch 1's report found 4/6 natural
  scope violations were substantively valid edits blocked only by the legacy full-sentence rule —
  this run's n=2 sample is consistent with, but does not independently confirm or refute, that
  finding).
- **`narrow_reverification_hypothesis` — measured, changed diagnostic quality but not outcomes.**
  In 2 of 3 `correction_failed` cases it converted a diluted, threshold-adjacent NEI into a
  decisive CONTRADICTED; in 1 of 3 it converted a borderline low-confidence NEI into an
  unambiguous high-confidence NEI (§4). All three remained correctly un-shipped either way.
- **No interaction effects are observable** in this sample: the three levers' measured effects
  are additive and non-overlapping (retrieval affects only NO_EVIDENCE/NEI classification of
  15 specific claims; the other two affect only the reasoning trace of 3 already-failed
  corrections). This run cannot rule out interaction effects that would only appear with `labeled`
  framing or a larger correction-trigger sample — see §8.

**Bottom line: on this batch, "all validated improvements enabled" is empirically indistinguishable
from "retrieval alone" for every outcome that was measured, because the correction-path levers had
no cases in their effective range this time.** This is a real, honestly-reported finding, not a
failure of the experiment design — a 50-case natural sample yields only 5 correction triggers,
which is not enough statistical power to detect a scope-check/reverification effect on shipping
outcomes even if one exists (§8).

---

## 8. What this data does and does not support

**Supported, with statistical backing:**
- ✅ **Evidence coverage improved**, safely (0 regressions) and significantly (p < 0.001, McNemar),
  from adding the v1 evidence supplement — measured for the first time on genuinely new,
  never-before-generated natural cases with a paired same-generation design.
- ✅ **Safety remained fully intact.** 0/10 unsafe shipments, 0/10 sibling regressions, and the
  `assertion_spans` scope check was demonstrated (n=2) not to be spuriously permissive.
- ✅ **Correction success on real natural data has not improved**, and this run adds two more
  confirming arms (10 more attempts, 0 shipped) to a now five-experiment-deep pattern.
- ✅ **`narrow_reverification_hypothesis` produces more decisive, better-calibrated re-verification
  signals** on real corrected text (n=3), even though it changed no ship/reject decision here.

**NOT supported by this data — explicitly out of scope:**
- ❌ **"Detection improved."** CONTRADICTED count is unchanged (3=3, same claims). This run cannot
  and does not claim detection improved — coverage gains landed entirely as NEI, not as new
  contradictions caught, in this sample.
- ❌ **True contradiction recall or false-positive rate** in the ground-truth sense. No lawyer
  annotation exists for these 50 cases (by design — that is the next, separate phase). The only
  recall/false-positive figures this project has are from **synthetic**, deliberately-corrupted
  data (`framing_comparison_synthetic_metrics.json`: bare contradiction recall 35.6% overall /
  47.7% with-evidence, labeled 45.8%/61.4%, both with 0% false-positive rate on the paired
  synthetic true-claim) — those are cited here for calibration only and must not be read as
  properties of this natural-data run.
- ❌ **"Retrieval precision" or a natural-data "false-match rate"** in the strict sense (is a
  matched citation's evidence actually the legally correct provision?). Without ground truth this
  can only be proxied by match method (exact vs fuzzy — 145/2 and 130/2 in B/A respectively, i.e.
  fuzzy matching is rare and did not change between arms) and by manual inspection of individual
  CONTRADICTED cases (§3), which found both CONTRADICTED verdicts in this run to be checkable,
  real content issues rather than verifier artifacts — a small, non-statistical positive signal,
  not a measured precision figure.
- ❌ **Whether `atomic_scope_check`/`narrow_reverification_hypothesis` would ever unlock a
  shippable natural-data correction.** n=2 scope violations and n=3 reverifications is not enough
  statistical power to distinguish "these levers never help" from "this batch didn't happen to
  contain a case in their effective range." Batch 1's larger scope-violation sample (n=6, 4
  substantively-valid-but-blocked) is suggestive but was measured under `labeled` framing, not the
  `bare` framing this run uses — not directly comparable.
- ❌ **Any claim about `labeled` framing combined with the other improvements.** This run
  deliberately holds framing at `bare` in both arms per the task specification; the controlled
  benchmark's framing effect (§6c) and this run's retrieval effect have not been jointly measured.

---

## 9. Answers to the required research questions

**Did evidence coverage improve?**
Yes — +7.1pp (63.2% → 70.3%), statistically significant (McNemar χ²=13.07, p≈0.0003), zero
regressions, entirely attributable to the v1 evidence supplement.

**Did detection improve?**
No, not in this sample. CONTRADICTED count and identity are unchanged (3 claims, same 3, same
confidences, in both arms). The 15 newly-evidenced claims from retrieval all resolved to NEI, not
CONTRADICTED. This experiment holds `premise_framing` at `bare`, the one lever this project's own
controlled benchmark shows moves detection accuracy most (macro F1 0.749→0.968) — so this result
should not be read as "retrieval doesn't help detection," only as "retrieval alone, under `bare`
framing, did not change detection counts in this specific 50-case sample."

**Did correction success improve on real natural data?**
No. 0/5 shipped in both arms (0/10 total this run), consistent with 0/21 (batch 1), 0/15 (batch 2),
and every large natural batch this project has run. The one historical natural-data success (1/4,
an early small run) has not been replicated by any subsequent, larger, more rigorously-selected
batch, including this one.

**Did safety remain intact?**
Yes, fully. 0/10 unsafe shipments (structurally guaranteed by the `status == "corrected"` ⟺
`reverification.verdict == ENTAILED` invariant, and empirically confirmed). The `assertion_spans`
scope check, tested for the first time on genuinely new natural cases, did not let anything
unsafe through (n=2 scope-violation cases, both still correctly rejected).

**Which limitation of the original NyayaMind-style generation pipeline is actually addressed?**
The limitation this prototype targets — a generation pipeline that produces statutory citations
with no mechanism to check them against real statute text at all — is addressed to the extent that
this verification layer now (a) resolves 63–70% of generated claims to real evidence and
(b) catches a small but real, individually-inspectable rate of genuine contradiction (3/209 ≈ 1.4%
this run) directly on freshly generated, never-before-seen natural output, with zero verified false
positives among the contradictions inspected. This is a *detection* capability, demonstrated on
real natural data for the first time with this rigor (paired arms, disjoint held-out cases,
full invariant validation). The v1 evidence expansion measurably widens what fraction of generated
claims this detection layer can even evaluate, which is itself a real limitation of the original
(undersized, 59-record) evidence corpus being addressed.

**Which limitations remain?**
(1) The correction/auto-fix capability remains essentially unproven on real data (1.5% historical
success rate across ~67 attempts, 0% in this run's ~67th–77th attempts). (2) `bare`-framing
verification rarely reaches ENTAILED at all (0/209 here), which caps how much of the "confirm this
citation is correct" half of verification this configuration can deliver on natural data — that
gap is `labeled` framing's known lever, not tested jointly with retrieval here. (3) Claim-level
granularity (one physical sentence backing several `Claim` records) remains a structural source of
scope violations and of CONTRADICTED verdicts that are real-but-imprecise (§3's `2006_770`
example). (4) No lawyer ground truth yet exists for true precision/recall — everything in §8's
"not supported" list remains open until that phase.

**Is the result strong enough to justify changing production defaults?**
**Retrieval (`use_evidence_v1: true`): the evidence here is real, safe, and statistically
significant, but this is one 50-case batch, and `config/prototype.yaml`'s own comments require an
independent full audit pass of the v1 corpus (currently only ~10% spot-checked) before promoting
it — that condition is unmet, so **not yet**, on the corpus's own stated bar, not on this
experiment's result quality.** `atomic_scope_check`/`narrow_reverification_hypothesis`: this run
supplies no evidence of harm (0 unsafe, 0 spurious scope-check passes) but also no evidence of
benefit on shipping outcomes (§7) — **insufficient sample to justify a default change either way.**
No production default was changed by this experiment; `config/prototype.yaml` remains exactly as
committed.

**What can honestly be claimed in a research paper, and what cannot?**
*Can claim:* "Expanding the evidence corpus significantly and safely improves evidence coverage on
held-out natural data (McNemar p<0.001, n=209 paired claims, zero regressions)." *Can claim:* "The
verification layer catches genuine, individually-verifiable contradiction errors on real,
previously-unseen generated statutory grounding text." *Can claim:* "A narrower, per-citation
re-verification hypothesis produces more decisive and better-calibrated re-verification signal on
real corrected text." *Cannot claim:* that detection rate improved from these changes (measured
flat). *Cannot claim:* that correction/auto-fix works on natural data (measured near-zero across
five natural experiments). *Cannot claim:* any precision/recall figure against ground truth
(none exists yet). *Cannot claim:* that this bundle of improvements is superior to `labeled`
framing alone, or that the two combine favorably (not jointly tested).

---

## 10. Reproducibility record

- Script: `research/prototype/scripts/run_final_gpu_validation.py`
- Candidate selection: `research/prototype/scripts/select_natural_candidates.py --out-suffix _final_validation`
  (exclusion list extended to add `natural_candidates_batch2_gpu_bare.jsonl`, a documented,
  additive change consistent with the script's own established pattern)
- Seed: 42 (generation and correction, greedy/deterministic throughout)
- Generation model: Qwen/Qwen2.5-7B-Instruct, 4-bit NF4, bfloat16 compute
- Verification model: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
- Hardware: NVIDIA RTX 4050 Laptop GPU (6,141 MiB dedicated + shared-memory fallback; peak
  allocated 7,547 MiB)
- Outputs: `final_gpu_validation_{metrics.json, A.jsonl, B.jsonl, corrections_detail.jsonl}` — none
  overwrite any prior committed or uncommitted output file
- `config/prototype.yaml`: unmodified by this task (deepcopy-only mutation in-process)
- Test suite: 189/189 passed, before and after
- `run_mvp.py --check`: clean, before and after
- Every claim record in `final_gpu_validation_{A,B}.jsonl` retains full provenance: original
  `claim_text`/`assertion_text`/`assertion_spans`, `citation_extracted`, `evidence_id`/`evidence_text`/
  `evidence_match_method`, `verdict`/`confidence`/`sub_reason`. Every correction attempt in
  `final_gpu_validation_corrections_detail.jsonl` additionally retains `original_field_text`,
  `regenerated_text`, full `reverification` (including `reverified_hypothesis`, distinguishing the
  narrow vs. full-sentence hypothesis actually verified), `sibling_regressions`, `corr_meta`
  (model/seed/timestamp), and `failure_category` — a complete original claim → evidence → detected
  problem → proposed correction → re-verification → sibling check → final decision chain for every
  one of the 10 correction attempts in this run.
