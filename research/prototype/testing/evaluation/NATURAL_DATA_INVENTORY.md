# Natural Data Inventory (STEP 6)

Drawn from `../inputs/INPUT_MANIFEST.md` and `../inputs/INPUT_SUMMARY.md` — no dataset
substituted. Every dataset below is confirmed to exist at the stated path with the
stated record count (re-verified in Phase 2, `input_integrity/`).

| Dataset | N | Classification | Independent labels? | Evaluation type | GPU required? |
|---|---|---|---|---|---|
| 588-claim natural aggregate | 588 claims (133 distinct texts) | **METRIC-ONLY — no independent correctness labels.** | No | Fresh re-derivation: claim parsing + evidence matching (current v0+v1 pool) + real DeBERTa verification (CPU) | No (verification is CPU-capable; underlying text is already-generated, no fresh Qwen call) |
| 209-claim paired natural evaluation | 209 claims × 2 arms (Arm A = original config, Arm B = v0+v1 evidence) | **METRIC-ONLY — no independent correctness labels.** Paired comparative data, not ground truth. | No | Fresh re-derivation: evidence matching (each arm's own config) + real DeBERTa verification (CPU, current labeled framing) for paired change analysis | No |
| Natural batch n=30 | 30 cases | **METRIC-ONLY** | No | Historical descriptive tabulation (already-computed verdicts) | N/A (no fresh generation) |
| Natural batch1 (n=50, bare+labeled) | 50 cases × 2 framings | **METRIC-ONLY** | No | Historical descriptive tabulation | N/A |
| Natural batch2 (n=50, bare+labeled) | 50 cases × 2 framings | **METRIC-ONLY** | No | Historical descriptive tabulation | N/A |
| Final validation batch (n=50) | 50 cases (= the 209-claim set above, both arms) | **METRIC-ONLY** | No | Covered under the 209-paired analysis above | No |
| Targeted/disjoint set | 11 + 1 cases | **METRIC-ONLY** | No | Included within the 588-claim aggregate's `run_natural_targeted.jsonl` source | N/A |

## Source, schema, and safety notes per dataset

### 588-claim natural aggregate
- **Source files** (exact list, matching `scripts/measure_evidence_coverage_v0_vs_v1.py`'s
  own `SOURCES` list — not substituted): `outputs/run_A_n30.jsonl` (30 cases, whole
  record), `outputs/run_natural_targeted.jsonl` (11 cases, `mode_B` sub-block),
  `outputs/natural_candidates_50_gpu_bare.jsonl` (50 cases),
  `outputs/natural_candidates_batch2_gpu_bare.jsonl` (50 cases).
- **Deduplication**: by exact `generated_field.text` string match, exactly as the
  existing script does (avoids double-counting identical generations appearing in more
  than one source file).
- **Re-verified this step**: 133 distinct texts, 588 claims — reproduces the historical
  figure exactly (see Phase 2).
- **Contains historical outputs**: yes — the underlying `generated_field.text` values are
  historical (Qwen generation already run in a prior GPU session); only claim
  parsing/evidence matching/verification are freshly (re-)computed on top of them.
- **Safe for fresh execution**: yes, fully CPU-safe — no Qwen call, real DeBERTa only.

### 209-claim paired natural evaluation
- **Source files**: `outputs/final_gpu_validation_A.jsonl`, `outputs/final_gpu_validation_B.jsonl`
  — 50 cases each, 209 claims each, confirmed claim-for-claim aligned (identical
  `document_id` order, identical claim count per case, identical `claim_text` per
  position — i.e. genuinely the same generation, evidence-matched independently per arm).
- **Original configurations** (read directly from each file's own `reproducibility`
  block, not assumed): Arm A = `premise_framing=bare, use_evidence_v1=False,
  atomic_scope_check=False, narrow_reverification_hypothesis=False, evidence_pool_size=59`.
  Arm B (as originally stored) = `premise_framing=bare, use_evidence_v1=True,
  atomic_scope_check="assertion_spans", narrow_reverification_hypothesis=True,
  evidence_pool_size=137`. **Note**: Arm B's originally-stored verdicts used `bare`
  framing, not the current production `labeled` value — `premise_framing=labeled` was
  decided *after* this data was generated, partly based on a separate CPU-only
  re-verification of it (`outputs/final_validation_bare_vs_labeled_cpu_metrics.json`).
  This step's fresh re-verification (Phase 5) makes this distinction explicit rather than
  conflating "as originally stored" with "under today's full production config."
- **Contains historical outputs**: yes (both arms' generation and originally-stored
  verdicts).
- **Safe for fresh execution**: yes, for evidence re-matching and DeBERTa re-verification
  (CPU-only); NOT safe/possible for fresh generation (would require Qwen/GPU).

### Natural batches (n=30, batch1, batch2, final_validation, targeted)
- Confirmed disjoint by case-ID intersection in STEP 0/1 (not re-verified here since no
  claim is made requiring re-confirmation beyond that already-established finding).
- This step's Phase 6 treats these as **historical descriptive tabulations only** —
  existing, already-computed verdicts/coverage read and reported, not re-derived. The
  588-claim and 209-paired analyses above already provide the fresh, re-derived layer for
  the batches that feed into them (n=30, targeted, batch1-bare, batch2-bare are inside the
  588 aggregate; the final_validation batch is the 209-paired set). Batch1-labeled and
  batch2-labeled framing arms are reported historically since fresh CPU re-verification of
  every framing arm of every batch would substantially duplicate the 588/209 analyses'
  purpose without adding a new legitimate metric.

## Why nothing here is promoted to GOLD

None of these datasets carries an independently-derived expected label — every metric
reported from them in this step is descriptive or paired-comparative, never scored
against a known-correct answer. See `../inputs/metric_only/README.md` (STEP 3) and
`METRIC_DEFINITIONS.md` (this step) for the enforced vocabulary.
