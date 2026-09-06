# Natural-Data Metric-Only Evaluation Report (STEP 6)

Full machine-readable data: `NATURAL_DATA_METRICS.csv` (this directory). Every number
below is either a **FRESH TESTING RESULT** (computed by this step's scripts, this run,
CPU-only) or a **HISTORICAL RESULT** (already-computed verdicts, tabulated fresh but not
re-derived) — labeled explicitly throughout, never conflated.

**Classification reminder**: every dataset in this report is **METRIC-ONLY — no
independent correctness labels.** No accuracy, precision, recall, or F1 figure appears
anywhere below.

## Table 1 — Evidence coverage and verdict distribution

| Dataset | N | Evidence coverage | NO_EVIDENCE | ENTAILED | CONTRADICTED | NOT_ENOUGH_INFORMATION | Fresh/Historical |
|---|---|---|---|---|---|---|---|
| 588-claim aggregate | 588 | 0.6633 | 198 | 21 | 5 | 364 | FRESH |
| 209-paired, Arm A | 209 | 0.6316 | 77 | 13 | 2 | 117 | FRESH |
| 209-paired, Arm B | 209 | 0.7033 | 62 | 13 | 3 | 131 | FRESH |
| n=30 (Mode B) | 88 | 0.4318 | 50 | 0 | 0 | 38 | HISTORICAL |
| targeted (Mode B) | 29 | 0.4828 | 15 | 0 | 0 | 14 | HISTORICAL |
| batch1, bare | 251 | 0.6693 | 83 | 0 | 1 | 167 | HISTORICAL |
| batch1, labeled | 251 | 0.6693 | 83 | 5 | 2 | 161 | HISTORICAL |
| batch2, bare | 236 | 0.4915 | 120 | 2 | 1 | 113 | HISTORICAL |
| batch2, labeled | 236 | 0.4915 | 120 | 11 | 3 | 102 | HISTORICAL |
| final_validation, Arm A (as stored, bare) | 209 | 0.6316 | 77 | 0 | 3 | 129 | HISTORICAL |
| final_validation, Arm B (as stored, bare) | 209 | 0.7033 | 62 | 0 | 3 | 144 | HISTORICAL |

**Note on batch N counts**: "N" here is claim count, not case count (e.g. n=30 cases
produced 88 claims). Batches are never merged or pooled across rows — each row is its
own, separately-reported regime, per `outputs/final_research_results.md`'s own
methodology.

**Note on final_validation rows appearing twice**: the FRESH rows (Table 1's rows 2-3)
re-derive evidence and verdicts fresh, under the current production `labeled` framing,
this run. The HISTORICAL rows (rows 10-11) are the values as originally stored at
generation time (Arm B under `bare` framing — see `NATURAL_DATA_INVENTORY.md`). Both are
legitimate, distinct pieces of information about the same underlying 209 claims.

## Table 2 — Fresh vs. historical, configuration, GPU status

| Dataset | Fresh/Historical | Configuration | GPU stage executed? |
|---|---|---|---|
| 588-claim aggregate | FRESH (parsing+matching+verification) | v0+v1 (136 records), labeled framing, threshold 0.70 | No |
| 209-paired, Arm A | FRESH (matching+verification) | v0-only (59), labeled framing | No |
| 209-paired, Arm B | FRESH (matching+verification) | v0+v1 (136), labeled framing | No |
| All natural batches (Table 1 rows 4-11) | HISTORICAL | as originally recorded (see `NATURAL_DATA_INVENTORY.md`) | No (never executed here; original generation used GPU in a prior session) |

**No row in this table involved GPU execution on this machine.** See `GPU_LIMITATIONS.md`.

## Table 3 — Paired 209-claim change types (fresh evidence matching)

| Change type | Count | Rate |
|---|---|---|
| Verdict unchanged (evidence unchanged, matched both arms) | 132 | 63.2% |
| Both NO_EVIDENCE (unchanged) | 62 | 29.7% |
| Evidence gained (NO_EVIDENCE → matched) | 15 | 7.2% |
| Evidence lost (matched → NO_EVIDENCE) | 0 | 0.0% |

Full detail, including the McNemar reproduction (χ²=13.0667, p=0.000301) and the fresh
verdict-change breakdown, in `PAIRED_209_REPORT.md`.

## What this report legitimately supports

- A concrete, reproducible description of how often the current production pipeline's
  retrieval stage finds usable evidence for real, previously-generated claims (66.3% on
  the 588-claim aggregate; 63.2%→70.3% on the paired 209-claim set).
- A concrete, reproducible description of how verifier verdicts are distributed across
  those claims under the current production configuration.
- An exact, mechanically-reproduced paired statistical result (McNemar) for the
  evidence-coverage change between the original and current evidence pool.

## What this report does NOT support

- Any claim about how many of these claims are legally accurate.
- Any claim about "improvement" in a correctness sense — every "gained"/"changed"
  category above is a mechanical description of what changed, not a judgment of which
  state is better.
- Any accuracy, precision, recall, or F1 number for natural data — none is calculated
  anywhere in this report, per `METRIC_DEFINITIONS.md`'s explicit rule.
