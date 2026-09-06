# Final Reconciliation Report — STEP 11

> **ARCHIVED (PASS 2 cleanup, 2026-09-06).** This document's two genuinely unique
> sections — the STEP 1→STEP 10B canonical source inventory, and the STEP 11 claim
> safety audit — were carried forward verbatim into
> `reports/FACULTY_EVALUATION_REPORT.md`'s new "Appendix: Technical reconciliation
> detail" section. Everything else in this document (the machine-distinction narrative,
> GOLD/natural-data/ablation/correction/safety restatements) duplicated
> `FACULTY_EVALUATION_REPORT.md`'s §3-§11 almost verbatim and was not carried forward
> separately. This file is preserved here, unedited below this notice, as the complete
> original STEP 11 document for anyone who wants it in its original form. It is no
> longer the current reference — use `FACULTY_EVALUATION_REPORT.md` for that.

---

**Purpose**: consolidate and reconcile every validated finding from STEP 1 through
STEP 10B, with no new experiments, before faculty-facing assembly. Every number below
is traced to a canonical source artifact (`FINAL_CLAIM_REGISTER.csv` gives the
file-level citation for each). Nothing here supersedes or edits any prior step's
artifact — this is a reconciliation layer, added under `testing/reports/`, that reads
everything and writes nothing back into STEP 1-10B's own files.

## Executive status

GPU capability has now been demonstrated end-to-end on a second machine. Every
CPU-only finding from STEP 1-9 remains unchanged and accurately scoped to the STEP
1-9 machine (confirmed, no unscoped stale claims found anywhere in the workspace —
see "Claim safety audit" below). Every GPU experiment in this project's history that
has a recoverable, well-specified protocol has now been freshly reproduced, exactly.
One aggregate figure (cumulative 1/56 correction rate) and one experiment that was
never designed (joint four-lever isolation) remain genuinely unavailable, for
documented structural reasons — not failures, and not something further effort on
this workspace would resolve.

**Final reconciliation complete; ready for faculty-facing assembly.**

## Canonical findings (STEP 1 → STEP 10B inventory)

| Step | Canonical source artifact(s) | Headline result |
|---|---|---|
| STEP 1 | `PROVENANCE.md` (workspace creation), `MANIFEST.md` | Workspace scaffolding; `research/.venv` found missing; GOLD/BEHAVIOR/METRIC-ONLY/PROVISIONAL classification scheme established |
| STEP 2 | `actual_outputs/step2_environment_setup/ENVIRONMENT_REPRODUCIBILITY_RESULT.md` | Venv built from `research/requirements.txt`, zero version substitutions; 205/205 pytest; machine confirmed to have **no NVIDIA GPU** (AMD Radeon integrated only) |
| STEP 3 | `inputs/README.md` (originally `inputs/INPUT_MANIFEST.md`, merged in PASS 1), `actual_outputs/step3_input_validation/validate_inputs_report.txt` | 38/38 input-integrity checks; GOLD-01 n=420, GOLD-02 n=59, hashes verified |
| STEP 4 | `actual_outputs/step4_gold_verifier/{gold01_controlled,gold02_synthetic}/*_metrics.json` | GOLD-01/GOLD-02 bare vs. labeled accuracy/F1, bit-for-bit historical match |
| STEP 5 | `components/` (renamed from `component_tests/`, demo data moved from `actual_outputs/step5_components/`, both in PASS 1), `evaluation/COMPONENT_TEST_MATRIX.csv` | 205/205 full suite; 7 component groups, 0 failures |
| STEP 6 | `actual_outputs/step6_natural_data/{588_claims,209_paired}/*_metrics.json` | 588-claim aggregate (66.3% coverage), 209-claim paired CPU re-verification (63.2%→70.3%, McNemar χ²=13.0667, p=0.000301) |
| STEP 7 | `ablation/ABLATION_SUMMARY.json`, `ABLATION_EVIDENCE_GRADES.md` (moved from `evaluation/` in PASS 1) | 9 levers graded A-E; joint four-lever confirmed absent |
| STEP 8 | `evaluation/CANONICAL_METRICS.{csv,json}`, `CONSOLIDATION_SOURCE_MAP.md` | 16 canonical metrics (M01-M16) consolidated, 26 headline values reconciled, 0 discrepancies |
| STEP 9 | `figures/FIGURE_NUMERIC_AUDIT.md`, `figures/*.png` | 11 figures, 99/99 automated checks, every displayed value traced to a STEP 4-8 CSV cell |
| STEP 10 | `PROVENANCE.md` STEP 10 section, `evaluation/GPU_REPRODUCTION_CROSSCHECK.md` Experiment 1 | Real GPU validated (RTX 4050, 6GB); real Qwen generation + correction executed; 10-case targeted-correction experiment exactly reproduced |
| STEP 10B | `PROVENANCE.md` STEP 10B section, `evaluation/GPU_REPRODUCTION_CROSSCHECK.md` Experiment 3 | 209-claim/50-case/two-arm GPU generation experiment exactly reproduced (byte-identical text, identical metrics); cumulative 1/56 found PROTOCOL INSUFFICIENT |

No new canonical value was invented anywhere in this reconciliation. Every figure
cited above was read directly from its named source file during this step.

## CPU reproduction (STEP 1-9, unchanged)

All CPU-only fresh reproductions from STEP 2-9 remain valid and unaffected by STEP
10/10B: GOLD-01 (bit-for-bit), GOLD-02 (to stated precision), 588-claim aggregate
(bit-for-bit), 209-claim CPU re-verification (exact), atomic scope-check replay
(exact), claim-parser sign test (exact), 205/205 regression suite at every step.
These were all executed on the STEP 1-9 machine, which has no NVIDIA GPU — this
remains true and does not change; it is a fact about that machine, not a permanent
project limitation (see next section).

## GPU reproduction (STEP 10/10B, new)

This is the highest-priority reconciliation item. STEP 1-9 established that a
CPU-only environment cannot execute Qwen generation or correction (`src/generator.py`
and `src/corrector.py` hard-require CUDA by design, no fallback). STEP 10 then
validated a **second, GPU-equipped machine** (NVIDIA GeForce RTX 4050 Laptop GPU, 6GB
VRAM, driver 592.82, CUDA 12.1 torch build) and, on it:

- Verified `torch.cuda.is_available()==True`, ran a real CUDA matmul round-trip.
- Loaded the real production `StatuteGroundingGenerator` (Qwen2.5-7B-Instruct,
  4-bit nf4) and `NLIVerifier` (DeBERTa, on GPU) successfully.
- Executed one real minimal Qwen generation (mode A, n=1) and a real 5-case
  correction-pipeline smoke test (mode C) — both via the unmodified production entry
  point `scripts/run_mvp.py`.
- Exactly reproduced the historical 10-case targeted labeled-framing
  correction-validation experiment (byte-identical corrected text for all 10 cases).

STEP 10B then closed the one gap STEP 10 explicitly left open: the 209-claim,
50-case, two-arm evidence-v0-vs-v1 **generation** experiment behind
`outputs/final_gpu_validation_{A,B}.jsonl`. This is genuinely distinct from STEP 6's
prior work — STEP 6 only ever re-read already-stored verdicts and did CPU-only
re-verification (confirmed from `run_step6_209_paired_evaluation.py`'s own docstring:
"No Qwen generation or correction is invoked"). STEP 10B re-ran the actual Qwen
generation itself, on GPU, and the result was an **exact reproduction**: all 50/50
generated texts byte-for-byte identical to the 2026-08-27 historical run, every
per-arm metric identical (claims=209, evidence-matched 132/147, verdict counts,
correction triggers 5/5, shipped 0/0, unsafe 0/0), identical peak VRAM (7547 MiB).

**Reconciled statement, superseding two now-stale forward-looking notes**: STEP 10's
own PROVENANCE.md section states the 209-claim experiment "was not reproduced this
step" — true when written, and that section is left unedited as the accurate
historical record of STEP 10 itself. It is superseded prospectively by STEP 10B,
whose own PROVENANCE.md section records the reproduction. No file was edited to
correct this — STEP 10B's section already supersedes it, and this report makes the
supersession explicit for anyone reading STEP 10 in isolation. Likewise, STEP
8/9-era documents (`evaluation/REPRODUCIBILITY_MATRIX.md`, `CONSOLIDATED_FACULTY_SUMMARY.md`,
`CONSOLIDATED_EXECUTIVE_SUMMARY.md`) correctly state, **for their own time and
machine**, "no NVIDIA GPU," "Qwen generation/correction NOT EXECUTED, any step" — these
statements are accurate as scoped (they say "this machine," referring to the STEP
1-9 machine) and are left unedited as historical record; they are now superseded, not
contradicted, by STEP 10/10B's separate-machine results.

**Explicit distinction, going forward**:
- **CPU-only machine limitation**: applies only to the STEP 1-9 machine (AMD Radeon
  integrated GPU, `torch.cuda.is_available()==False`, confirmed in STEP 2). This fact
  about that specific machine is permanent and does not change.
- **GPU validation machine**: a separate machine with an NVIDIA RTX 4050 Laptop GPU,
  used for STEP 10/10B, on which real Qwen generation and correction demonstrably
  execute.

No stale, *unscoped* "GPU is unavailable" statement was found anywhere in the
workspace during this reconciliation's audit (see "Claim safety audit" below) — every
existing occurrence already reads "this machine" or "on this machine," which remains
literally true for STEP 1-9's own machine.

## GOLD findings (unchanged)

- GOLD-01 controlled benchmark (n=420): accuracy 0.7333 (bare) → 0.9714 (labeled);
  macro F1 0.7487 → 0.9684. McNemar χ²=98.01, p=4.16e-23; exact sign test
  p=1.5777e-30. Evidence grade **A**. Source: `CANONICAL_METRICS.csv` M01-M03,
  `ABLATION_SUMMARY.json`.
- GOLD-02 synthetic stress (n=59): contradiction recall 0.3559 (bare) → 0.4576
  (labeled). Evidence grade **A** (as a GOLD, by-construction-labeled stress set).
  Source: M04.

These are curated/synthetic-label results. **They do not transfer to natural-data
accuracy or legal correctness** — no source document in this workspace makes that
claim, and this report does not introduce one.

## Natural-data findings (unchanged, METRIC-ONLY)

- 209-claim paired evidence coverage: 63.2% (v0) → 70.3% (v0+v1), McNemar χ²=13.0667,
  p=0.000301, exact sign test p=6.10e-05, zero regressions (gained=15, lost=0,
  unchanged=194). Evidence grade **A**, classification **SUPPORTED**. Source: M05,
  `paired_209_metrics.json`. Now additionally corroborated by STEP 10B's exact GPU
  re-execution of the underlying generation (see above) — a reproducibility
  confirmation of the generation step, not a new statistical result.
- 588-claim natural aggregate: 66.3% (390/588) evidence coverage; verdict
  distribution NEI=364, NO_EVIDENCE=198, ENTAILED=21, CONTRADICTED=5. **Descriptive
  only — no independent label exists for any of these 588 claims.** Source: M06-M07.
- Natural 147-claim evidence-matched subset (bare→labeled): ENTAILED 0→13,
  CONTRADICTED 3→3 (unchanged). Evidence grade **B**. Source: M09-M10.

None of these natural-data numbers is, or is treated as, an accuracy or F1 figure.

## Component behavior findings (unchanged)

- Full regression suite: **205/205**, unchanged across every step, STEP 2-10B. This
  is the sole authoritative test-count figure.
- 7 component groups (STEP 5): 01=111, 02=72, 03=48, 04=3, 05=15, 06=35, 07=5 —
  these sum to 289, **not** 205, because the groups are overlapping categorizations
  of the same 205-test suite by pipeline stage, not disjoint additional tests. The
  authoritative total is 205; group counts are never summed as an alternative total.
  Source: `evaluation/COMPONENT_TEST_MATRIX.csv`, `PROVENANCE.md` STEP 5 section.

## Ablation findings (unchanged, STEP 7; annotated by STEP 10/10B)

Grades A-E per `ABLATION_EVIDENCE_GRADES.md`: Evidence v1 (A), premise framing on
GOLD-01 (A), premise framing on natural 147-subset (B), claim parser fix (B),
confidence threshold (B), atomic scope check (C), narrow re-verification (C),
correction levers targeted (C), joint four-lever isolation (E, does not exist). **No
grade was changed by STEP 10, STEP 10B, or this reconciliation** — STEP 10/10B only
added "freshly reproduced on GPU" annotations to two already-graded findings
(evidence v1's generation step, correction levers targeted), per
`ablation/GPU_ABLATION_UPDATE.md`.

## Correction findings

Three populations, kept strictly separate per this project's own methodology (never
pooled except where the project's own historical `final_metrics.json` already pools
them, which is itself flagged as a limitation, not treated as more granular than it
is):

- **Synthetic** (GOLD-02-adjacent, n=59 cases): labeled framing 26/36 (72.2%)
  shipped; bare framing 0/30 shipped. Source: M13, `CORRECTION_FUNNEL.csv`.
- **Natural targeted** (framing-isolated comparison, same 50-case batch): bare 0/5 →
  labeled 1/10 shipped. Not statistically supported at this n (Wilson intervals
  overlap almost entirely). Evidence grade **C**. Source: M11. **Exactly reproduced
  on GPU** in STEP 10 (10-case run) and independently corroborated again inside STEP
  10B's 209-claim re-run (5-trigger subset, also exact).
- **Natural cumulative** (project's entire correction history): 1/56 shipped (1.8%),
  0 unsafe. Evidence grade **D**. Source: M12, `outputs/final_metrics.json`
  `section_D_correction_safety_cumulative`. **HISTORICAL-ONLY, PROTOCOL INSUFFICIENT
  for fresh reproduction** (see below) — this status is unchanged by, and was
  explicitly investigated and confirmed by, STEP 10B.

## Safety observations

0 unsafe corrections observed across every correction attempt tested in this
project's history (56 natural + 66 synthetic = 122 total attempts) — an **observed
count in the tested population**, not a probabilistic guarantee and not a universal
safety claim. Source: M14, `SAFETY_SUMMARY.csv`. STEP 10/10B's fresh GPU
reproductions (10-case targeted, 5-case smoke test, 209-claim 5-trigger set) add 0
further unsafe shipments to this observed count, consistent with (not proof of
extending) the historical figure.

## Historical-only findings (explicitly preserved)

1. **Cumulative correction rate, 1/56 = 1.8%**. Status: **HISTORICAL-ONLY / NOT
   FRESHLY RE-DERIVED / PROTOCOL INSUFFICIENT.** Reason: `outputs/final_metrics.json`'s
   own `provenance` field names an ad-hoc, never-committed "build_final_metrics
   analysis" script; no such script exists anywhere in the repository (confirmed by
   STEP 10B's repository-wide search), and the pooled `56` carries no
   per-constituent breakdown that would let it be reconstructed from the historical
   artifact alone. Reconstructing it honestly would require re-running every
   GPU-dependent correction experiment in the project's history and re-summing — out
   of scope for any single validation/reconciliation step. **Not approximated
   anywhere in this report.**
2. **Joint four-lever experiment**. Status: **DOES NOT EXIST.** Re-confirmed by
   repository-wide search in STEP 10, STEP 10B, and again in this reconciliation
   step (`grep -ri "four-lever\|joint lever" research/` — no protocol found beyond
   STEP 7's own NOT_ISOLABLE conclusion). No additive or interaction effect between
   the four production levers (`premise_framing`, `use_evidence_v1`,
   `atomic_scope_check`, `narrow_reverification_hypothesis`) can be inferred from
   the separate single-lever findings, and none is inferred here.
3. **Narrow re-verification** (3 cases). Status: **HISTORICAL-ONLY, DIAGNOSTIC (grade
   C).** Cited narratively from `FINAL_PRODUCTION_CONFIG.md` §4 and
   `outputs/research_completion_report.md` §17c; not re-derivable from raw per-case
   data without ambiguity (STEP 7's own finding, unchanged).
4. **Claim parser fix** (n=30). Status: **HISTORICAL REPRODUCTION for the underlying
   code change** (the pre-fix parser cannot be re-executed without checking out old
   source) but the **statistic itself was freshly recomputed** (STEP 7) from raw
   historical per-case data and matches exactly. Evidence grade **B**.

## Unavailable experiments

- Joint four-lever isolation (see above) — no protocol, none invented.
- A single-script reconstruction of the cumulative 1/56 figure (see above) — no
  recoverable protocol, none invented.

## Claim safety audit

A repository-wide search across every `testing/evaluation/`, `testing/ablation/`, and
`testing/reports/` document for the prohibited claim patterns (natural-data
accuracy/F1, legal correctness without GOLD labels, universal safety, "correction is
solved," "GPU results prove correctness," joint-lever interaction effects, transfer
of controlled-benchmark results to natural data) found:

- **Zero affirmative violations.** The only regex hit
  (`CONSOLIDATED_FACULTY_SUMMARY.md:105`, "...no natural-data accuracy figure exists
  anywhere in this project") is itself a negation/disclaimer, not a claim.
- **Zero unscoped "GPU unavailable" statements.** Every occurrence found (in
  `ENVIRONMENT_REPRODUCIBILITY_RESULT.md`, `EXPECTED_VS_ACTUAL_REPORT.md`,
  `component_tests/03_verifier/RESULT.md`, `CONSOLIDATED_EXECUTIVE_SUMMARY.md`,
  `CONSOLIDATED_FACULTY_SUMMARY.md`, `evaluation/REPRODUCIBILITY_MATRIX.md`,
  `inputs/INPUT_TO_COMPONENT_MAP.md`) is explicitly scoped to "this machine,"
  correctly describing the STEP 1-9 machine at the time it was written. None
  required correction; none was edited.

Category separation (GOLD / SOFTWARE BEHAVIOR / METRIC-ONLY / HISTORICAL-ONLY /
GPU-REPRODUCED / DIAGNOSTIC) is preserved throughout this report and in
`FINAL_CLAIM_REGISTER.csv` — no category is collapsed into another anywhere above.

## Figure validity status

STEP 9's 11 figures were built entirely from STEP 8's locked
`evaluation/figure_data/*.csv` contracts. STEP 10B's fresh GPU reproduction of the
209-claim experiment produced numbers **identical** to the historical data those
figures already plot (exact match, verified in `GPU_REPRODUCTION_CROSSCHECK.md`
Experiment 3) — so no figure's displayed data is stale or wrong.

**FIGURES REMAIN VALID — NO REGENERATION REQUIRED.**

The only thing that has changed is the *freshness/execution-status annotation*
available for the underlying 209-claim data (now also GPU-re-executed, not only
CPU-re-verified) — this is a documentation-layer fact captured in this report and in
`FINAL_CLAIM_REGISTER.csv`, not a figure caption error. No figure caption makes an
execution-status claim that this changes (per `figures/FIGURE_NUMERIC_AUDIT.md`,
captions cite data values, not GPU-execution provenance).

## Explicit limitations (carried forward, unchanged, and current)

1. No joint four-lever causal isolation exists anywhere in this project.
2. No human/lawyer ground truth exists anywhere in this project — all GOLD labels
   are Claude-generated/self-tagged or by-construction (synthetic corruption).
3. Cumulative 1/56 correction rate cannot be freshly re-derived from a single
   recoverable protocol (confirmed, not merely asserted, by STEP 10B).
4. The scope-check-mode ablation discrepancy (1/11 vs. an earlier batch-1-only 4/6)
   remains unreconciled — both numbers are real, from different batches; neither
   supersedes the other (STEP 1/7 finding, unaffected by GPU work).
5. v1 evidence audit coverage remains partial (50/82 records independently
   re-fetched as of 2026-08-27; the rest rest on build-time provenance only).
6. A root-level "Project Author Statement" claiming professional legal review is
   unverifiable and is not cited as evidence anywhere in this workspace.
7. Historical GPU runs' exact physical-machine identity is not independently
   confirmed — only that production code targets "this RTX 4050 6GB machine" per
   `src/generator.py`'s docstring, and the STEP 10/10B machine matches that GPU
   model/VRAM class. No claim of identical hardware is made anywhere.
