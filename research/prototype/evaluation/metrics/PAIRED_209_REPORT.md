# Paired 209-Claim Analysis Report (STEP 6)

Per-record data: `paired_209_analysis.csv` (this directory). Full JSON records:
`../actual_outputs/natural_data_runs/209_paired/paired_209_full_records.jsonl`.

**Terminology**: `historical_*` columns = **HISTORICAL RESULT** (verdicts/evidence as
originally stored when `outputs/final_gpu_validation_{A,B}.jsonl` were generated — Arm B
under `bare` framing, since `labeled` was decided afterward). `fresh_*` columns =
**FRESH TESTING RESULT** (evidence freshly re-matched this run — Arm A against its own
original v0-only pool, Arm B against the current production v0+v1 pool — and verdicts
freshly re-verified this run via the real DeBERTa verifier, CPU, both arms under the
current production `labeled` framing).

## Paired change counts (fresh evidence matching)

| Change type | Count | Rate (of 209) |
|---|---|---|
| Evidence unchanged, matched in both arms | 132 | 63.2% |
| Evidence unchanged, NO_EVIDENCE in both arms | 62 | 29.7% |
| Evidence gained (NO_EVIDENCE → matched) | 15 | 7.2% |
| Evidence lost (matched → NO_EVIDENCE) | 0 | 0.0% |

(Exact counts reproduced from `paired_209_metrics.json`'s `evidence_change_counts`.)

## Paired change counts (fresh verdict, both arms under current labeled framing)

| Change type | Count | Rate (of 209) |
|---|---|---|
| Unchanged (both arms reached the same verdict) | 132 | 63.2% |
| Both NO_EVIDENCE (verdict not reachable in either arm) | 62 | 29.7% |
| Changed: no verdict in A → NOT_ENOUGH_INFORMATION in B | 14 | 6.7% |
| Changed: no verdict in A → CONTRADICTED in B | 1 | 0.5% |

Every "changed" case above corresponds exactly to one of the 15 "evidence gained"
claims from the table above (14+1=15) — consistent by construction, since a verdict can
only exist where evidence was matched. **No verdict changed among the 132 claims that
already had evidence in Arm A** — Arm B's evidence-pool change did not alter any verdict
for a claim that was already evidence-matched in Arm A, on this paired set.

**No verdict change is described as an "improvement" without an explicitly defined
behavioral criterion** — the only criterion used anywhere in this report is the
mechanical one stated above (evidence gained/lost/unchanged), never a legal-correctness
judgment. A CONTRADICTED verdict appearing where none existed before is reported neutrally
as "a verdict became reachable," not as a positive or negative outcome.

## McNemar's test — evidence-coverage binary event (reproducing existing project methodology)

**Binary event tested**: "did this claim receive usable evidence (yes/no)?" — the exact
same binary event `outputs/final_gpu_validation.md` already tests for this exact
comparison. No new hypothesis was invented.

| | Value |
|---|---|
| b (evidence gained, A→B) | 15 |
| c (evidence lost, A→B) | 0 |
| χ² (continuity-corrected) | 13.0667 |
| p-value | 0.000301 |

**This is a fresh, mechanical recomputation** of the binary event from freshly re-matched
evidence, not a citation of the historical number — and it reproduces the historical
figure (χ²=13.07, p≈0.0003) exactly. See `../HISTORICAL_CROSSCHECK_NATURAL.md`.

**What this legitimately shows**: the evidence-pool change (v0→v0+v1) produced a
statistically detectable shift in how often claims receive usable evidence, on this
paired 209-claim set. **What it does NOT show**: that the evidence found is legally
correct, or that Arm B's claims are more accurate than Arm A's — only that the *rate* of
finding *some* usable evidence changed, in the "gained" direction, with zero claims
losing evidence.

## Historical vs. fresh verdict distributions (both arms)

| | Historical (as stored) | Fresh (current labeled framing, this run) |
|---|---|---|
| Arm A | NEI=129, NO_EVIDENCE=77, CONTRADICTED=3 | NEI=117, NO_EVIDENCE=77, ENTAILED=13, CONTRADICTED=2 |
| Arm B | NEI=144, NO_EVIDENCE=62, CONTRADICTED=3 | NEI=131, NO_EVIDENCE=62, ENTAILED=13, CONTRADICTED=3 |

Arm A's historical verdicts were never recomputed under labeled framing in this project's
history (Arm A represents the pre-2026-08-27 baseline and was not a target of the later
labeled-framing re-verification passes) — this step's fresh Arm-A-under-labeled numbers
are new to this workspace, not a reproduction of a prior number, and are reported as
exactly that.

## What must not be concluded from any of the above

No accuracy, precision, recall, or F1 figure is calculated anywhere in this analysis.
Every number above describes observed system behavior (evidence retrieval outcomes,
verifier verdict outcomes) under two named configurations, on identical underlying
claims — never a correctness judgment.
