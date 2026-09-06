# Complete Correction Funnel (STEP 8)

Machine-readable source: `CORRECTION_FUNNEL.csv`. Three populations are kept **strictly
separate** — synthetic, natural targeted, and natural cumulative — per this step's
explicit instruction not to merge them into a single success rate.

## Synthetic correction behavior (GOLD-02-derived, 59 cases, deliberately corrupted)

| Stage | Bare | Labeled |
|---|---|---|
| Candidate claims | 59 | 59 |
| Correction triggered | 30 | 36 |
| Correction generated | 30 | 36 |
| Scope gate rejected | 0 | 0 |
| Re-verification not ENTAILED | 30 | 10 |
| Sibling regression rejected | NOT AVAILABLE | NOT AVAILABLE |
| Citation identity failures | NOT AVAILABLE | NOT AVAILABLE |
| **Shipped** | **0** | **26** |

**26/36 = 72.2%** shipped under labeled framing. This is a **synthetic, deliberately
corrupted, GOLD-adjacent** population — every candidate is contradictory by
construction, so a correct fix is unambiguous. This figure must **never** be presented
as equivalent to the natural shipped-correction rate below.

## Natural targeted correction history (final_validation batch, 50 cases, 209 claims)

| Stage | Bare (original) | Labeled (current, isolated) |
|---|---|---|
| Candidate claims (evidence-matched) | 147 | — |
| Correction triggered | 5 | 10 |
| Correction generated | 5 | 10 |
| Scope gate rejected | 2 | 3 |
| Re-verification not ENTAILED | 3 | 6 |
| Sibling regression rejected | 0 | NOT AVAILABLE |
| Citation identity failures | NOT AVAILABLE | NOT AVAILABLE |
| **Shipped** | **0** | **1** |

## Natural cumulative correction history (entire project, all natural GPU sessions)

| Stage | Count |
|---|---|
| Candidate claims | NOT AVAILABLE (not tracked as a single denominator across all sessions) |
| Correction triggered | 56 |
| Correction generated | 56 |
| Scope gate rejected | 18 |
| Re-verification not ENTAILED (`correction_failed`) | 37 |
| Sibling regression rejected | NOT AVAILABLE (not separately tracked at the cumulative level; 0 observed in every individually-tested batch) |
| Citation identity failures | NOT AVAILABLE (0 confirmed false-ship cases per the STEP 0 audit, not tracked as a running count) |
| **Shipped** | **1 (1.8%)** |

## Why these three populations cannot be merged

**"72.2% synthetic correction" cannot be presented as equivalent to "natural shipped
correction rate."** The synthetic population is constructed so every candidate is
genuinely, unambiguously contradictory — the correction task is comparatively easy. The
natural populations involve real generated text where most triggers stem from
low-confidence or genuinely ambiguous verifier judgments, not guaranteed
contradictions. Merging them would silently substitute an easy, synthetic success rate
for a much harder, real one.

## Stages marked NOT AVAILABLE, and why

Sibling-regression and citation-identity failure counts are not tracked as running
totals across the whole project's history — they are recorded per-experiment (and were
found to be 0 in every experiment that did track them, per the STEP 0 audit and
`final_gpu_validation_metrics.json`). Rather than infer a cumulative 0 from the absence
of any observed failure, this funnel reports NOT AVAILABLE at the cumulative level and
the actual observed 0 at the experiment level where it was genuinely measured.
