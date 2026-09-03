# Final Research Results — Consolidated Analysis

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-27. Every number below is recomputed this session directly from raw
`outputs/*.jsonl` experiment artifacts (see `outputs/final_metrics.json` for the machine-readable
form) — not copied from prior narrative reports. Where a prior report's own JSON metrics file was
reused directly (synthetic data), that is stated explicitly.

> **How to read this document.** Results are split into four parts, per this task's own
> instruction, specifically to avoid conflating incompatible data: **(A) synthetic stress**,
> **(B) natural NyayaRAG**, **(C) parser/retrieval**, **(D) correction/safety**. Within (B),
> results are further organized as a **regime table** — one row per distinct (framing, evidence
> pool, scope-check mode) combination actually run — because pooling across regimes would produce
> misleading numbers. Metrics computed against `assumption_annotation.jsonl` are marked
> **PROVISIONAL** throughout and must never be read as validated accuracy.

---

## 0. Case census (avoiding double-counting)

| Batch | Cases | Note |
|---|---:|---|
| n=30 (`run_A/B/C_n30`) | 30 | Original baseline batch |
| targeted (`run_natural_targeted`) | 11 | **Confirmed, this session: a full subset of the n=30 document_ids (0 genuinely new cases)** — never summed alongside n=30 in any pooled total below |
| batch 1 (`natural_candidates_50_gpu`) | 50 | Disjoint from n=30/targeted |
| batch 2 (`natural_candidates_batch2_gpu`) | 50 | Disjoint from all of the above |
| final validation (`final_gpu_validation`) | 50 | Disjoint from all of the above |
| **Total distinct real NyayaRAG cases ever processed** | **180** | 30 + 50 + 50 + 50 (targeted excluded, confirmed redundant) |

---

## A. Synthetic stress results

**Source**: `framing_comparison_gpu_n59_postfix_results.jsonl` (raw per-claim, recomputed this
session) + `..._metrics.json` (real GPU Qwen correction stats). 59 deliberately-corrupted claim
pairs (c1 = corrupted, c2 = paired true/unflagged claim), real DeBERTa verification, real Qwen
correction (not scripted).

| Metric | bare | labeled |
|---|---:|---:|
| c1 (corrupted) verdicts | NO_EVIDENCE 15 / CONTRADICTED 21 / NEI 23 | NO_EVIDENCE 15 / CONTRADICTED 27 / NEI 17 |
| c1 with evidence | 44/59 | 44/59 |
| **Contradiction recall, overall** | **35.6%** | **45.8%** |
| **Contradiction recall, evidence-matched only** | **47.7%** | **61.4%** |
| c2 (unflagged true claim) verdicts | NEI 59/59 | ENTAILED 59/59 |
| **False-positive rate (c2 wrongly CONTRADICTED)** | **0.0%** | **0.0%** |
| Correction triggers | 30 | 36 |
| **Corrections shipped** | **0/30 (0%)** | **26/36 (72.2%)** |
| Unsafe corrections shipped | 0 | 0 |
| Unflagged-claim preservation | 30/30 (100%) | 36/36 (100%) |

**Reading**: on synthetic (deliberately corrupted) data, labeled framing is unambiguously better on
every axis measured — higher contradiction recall, zero false positives in either arm, and a
72.2% real correction-shipping success rate vs 0% for bare. **This result has never transferred to
real natural data at anywhere near this magnitude** — see §B and §D.

---

## B. Natural NyayaRAG results — regime table

Each row is one distinct, actually-run (framing × evidence-pool × scope-check) configuration.
**Rows are never pooled across different regimes** — only same-regime rows are summed (marked ✅).

| Regime | Cases | Claims | Matched | Coverage | Verdicts (NEI / NO_EV / CONTR / ENT) | Correction triggers → shipped |
|---|---:|---:|---:|---:|---|---:|
| n=30, mode C, bare, v0(59) | 30 | 88 | 38 | 43.2% | 38 / 50 / 0 / 0 | 0 → 0 |
| targeted, mode B, bare, v0(59) *(subset of n=30, not pooled)* | 11 | 29 | 14 | 48.3% | 14 / 15 / 0 / 0 | n/a (mode B) |
| batch 1, bare, v0(59) | 50 | 251 | 168 | 66.9% | 167 / 83 / 1 / 0 | 5 → 0 |
| batch 1, labeled, v0(59) | 50 | 251 | 168 | 66.9% | 161 / 83 / 2 / 5 | 16 → 0 |
| batch 2, bare, v0(59) | 50 | 236 | 116 | 49.2% | 113 / 120 / 1 / 2 | 5 → 0 |
| batch 2, labeled, v0(59) | 50 | 236 | 116 | 49.2% | 102 / 120 / 3 / 11 | 10 → 0 |
| final validation Arm A, bare, v0(59) *[pre-2026-08-27 production]* | 50 | 209 | 132 | 63.2% | 129 / 77 / 3 / 0 | 5 → 0 |
| final validation Arm B, bare, v0+v1(137)†, assertion_spans+narrow | 50 | 209 | 147 | 70.3% | 144 / 62 / 3 / 0 | 5 → 0 |
| final validation, **labeled**, v0+v1(136)‡, assertion_spans+narrow — verification-only CPU recheck of Arm B's claims | 50 | 147 | 147 | n/a (same claims as Arm B) | 131 / — / 3 / 13 | n/a |
| final validation, **labeled**, v0+v1(136), assertion_spans+narrow — targeted GPU correction validation *[FINAL PRODUCTION REGIME]* | 50 | — | — | — | — | **10 → 1 (10%)** |

† pre-audit-fix pool size (137); ‡ post-audit-fix pool size (136, this session's evidence audit — see §C and `evidence_v1_independent_audit.md`). The 15 claims gained by the v1 pool were unaffected by the 137→136 fix (the one downgraded record, "Section 2, Income Tax Act", was not among them).

### ✅ Valid same-regime pooling: bare + v0(59)-pool + legacy-scope-check (4 disjoint sources: n=30, batch 1, batch 2, final-A)

- **180 cases, 784 claims, 454 matched (57.9% coverage)**
- Verdicts: NEI 447, NO_EVIDENCE 330, CONTRADICTED 5, ENTAILED 2
- This is the largest valid single-regime pool in the project — the closest thing to "production as
  it was before 2026-08-27, at scale."

### ✅ Valid same-regime pooling: labeled + v0(59)-pool + legacy-scope-check (2 disjoint sources: batch 1, batch 2)

- **100 cases, 487 claims, 284 matched (58.3% coverage)**
- Verdicts: NEI 263, NO_EVIDENCE 203, CONTRADICTED 5, ENTAILED 16
- **8x more ENTAILED per matched claim than the equivalent bare regime** (16/284 = 5.6% vs 2/454 =
  0.4%) — the clearest natural-data confirmation of labeled framing's detection-completion benefit,
  at a defensible pooled sample size (100 cases, not just one 50-case batch).

### Evidence coverage improvement (v0 → v0+v1), paired design

The **only** paired (same cases, same generation) coverage comparison in this project: final
validation Arm A (v0, 132/209=63.2%) vs Arm B (v0+v1, 147/209=70.3%). **+7.1pp, McNemar
χ²=13.07 (p≈0.0003), zero regressions** — full statistical detail in `final_gpu_validation.md`
§2, unchanged by this session's audit fix (confirmed: none of the 15 gained matches used the
one record downgraded by the fix).

---

## C. Parser / retrieval evaluation

**Source**: `no_evidence_taxonomy_v3.json`, this session — re-extracts claims with the **current**
`claim_parser` from all 183 distinct generated texts ever produced across every natural GPU
experiment in this project (n=30 + targeted + batch 1 + batch 2 + final validation), matches
against the **current, post-audit-fix** v0+v1 pool (136 records).

| | Count | % |
|---|---:|---:|
| Total claims (current parser, all natural texts ever generated) | 797 | 100% |
| Matched | 537 | **67.4%** |
| No citation extractable at all | 0 | 0% |
| NO_EVIDENCE, has citation | 260 | 32.6% |

**NO_EVIDENCE taxonomy** (260 claims):

| Bucket | Count | Meaning |
|---|---:|---|
| `genuinely_absent_no_such_provision_any_act` | 140 (53.8%) | Real corpus-coverage gap |
| `genuinely_absent_wrong_act_or_edition` | 78 (30.0%) | Correctly declined — different Act |
| `unresolved_act` | 40 (15.4%) | Correctly declined to guess (ambiguous field) |
| `parser_or_matcher_defect_candidate` | 2 (0.8%) | Both manually reviewed, **confirmed NOT bugs** |

**Zero confirmed parser or evidence-matcher defects** across 797 real claims spanning this
project's entire natural-data history. Full detail, including the 2 reviewed candidates and 15
new adversarial regression tests (wrong-Act, same-number/different-act, year/edition, aliases,
ranges, multi-Act, ambiguous citations — one confirmed latent limitation, fuzzy year-blindness,
not currently triggered), is in `outputs/evidence_v1_independent_audit.md`.

**Retrieval precision proxy**: match method breakdown across all natural regimes shows
`exact_normalized` dominates over `fuzzy` by roughly 60:1 to 80:1 in every batch (e.g. final
validation Arm B: 145 exact vs 2 fuzzy) — fuzzy matching, the higher-risk path for a false
positive match, is rarely exercised. **No ground truth exists to compute a true false-match rate**
(see §D and `final_limitations_and_future_scope.md`); this proxy and the manual inspection of every
CONTRADICTED verdict in `final_gpu_validation.md` §3 are the strongest evidence available that
matches are not spuriously wrong.

---

## D. Correction / safety evaluation

**Cumulative, all natural correction attempts, all regimes, all 180 distinct cases pooled**
(case-level trigger count, matching pipeline.py's own "at most one correction attempt per case"
contract — no double-counting):

| | Count |
|---:|---:|
| Total correction attempts | 56 |
| `correction_failed` | 37 |
| `correction_scope_violation` | 18 |
| **`corrected` (shipped)** | **1** |
| **Shipped rate** | **1.8%** |
| **Unsafe shipped** | **0 / 56 (0%)** |

**Synthetic vs. natural transfer gap**: synthetic (labeled) shipped 72.2% (26/36); natural
(pooled, all regimes, all history) shipped 1.8% (1/56); natural, **final production regime
specifically** (labeled + v0+v1 + assertion_spans + narrow_reverification), shipped **10% (1/10)**
— still far below synthetic, but the first time any natural regime in this project's history has
shipped anything at all under real, targeted testing beyond the single historical exception.

**The one natural shipped correction** (`2003_760`/c3, final production regime): replaced a
sentence that incorrectly restated Section 302 IPC's *definition* language with its actual
*punishment* text — re-verified ENTAILED at 0.995 confidence, 0 sibling regressions. Full detail
in `FINAL_PRODUCTION_CONFIG.md` §1 and `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl`.

**Safety rate**: 0 unsafe shipments across every correction attempt in this project's history (56
natural + 30+36 synthetic = 122 total attempts), structurally guaranteed by the
`status=="corrected"` ⟺ `reverification.verdict==ENTAILED` invariant and empirically confirmed
every time it was checked.

**Unflagged-claim preservation**: measured per-batch (batch 1 bare 45/45=100%, batch 1 labeled
83/107=77.6%, final validation both arms 16/21=76.2% claim-text / 18/21=85.7% assertion-span
basis) — see `final_gpu_validation.md` §4 for the full per-claim breakdown of what was preserved
and what wasn't in every triggered case.

---

## E. Verifier performance against provisional assumption-gold labels

> **PROVISIONAL / ASSUMPTION-BASED.** `assumption_annotation.jsonl` is Claude-generated
> provisional labeling of 88 claims (29 document_ids), **not lawyer-verified ground truth**. None
> of the numbers in this section may be cited as validated system accuracy — they describe
> agreement between two machine-produced label sets.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

Of 88 assumption-annotated claims, 38 have matched evidence (only these produce a real automated
NLI call, not a fixed NO_EVIDENCE fallback):

| | Agreement with assumption `evidence_entails_claim` |
|---|---:|
| bare (as originally computed, reused verbatim) | 20/38 = **52.6%** |
| labeled (freshly recomputed this session, CPU, same evidence text) | 18/38 = **47.4%** |

**Honest, non-cherry-picked finding: labeled framing does NOT show higher agreement with this
older, bundled-sentence-heavy assumption-annotated set** — only 2/38 claims flip to ENTAILED under
labeled framing here, far fewer than the 14 the original bare-vs-assumption disagreement analysis
(`assumption_vs_automated_report.md`) suggested "should" flip. This is recorded in full in
`FINAL_PRODUCTION_CONFIG.md` §1 as a genuine counter-signal to the premise_framing production
decision (which still rests primarily on the three stronger, more recent, less-bundled sources
described there) and as a concrete, evidence-backed limitation in
`final_limitations_and_future_scope.md`: the likely cause is that this older set is dominated by
bundled multi-citation sentences, and the PRIMARY verification pass (unlike re-verification) always
hypothesizes the full `claim_text`, never the narrower `assertion_text`.

---

## Summary of what moved and what didn't

| Question | Answer | Evidence |
|---|---|---|
| Did evidence coverage improve (v0→v0+v1)? | **Yes**, +7.1pp, p<0.001, 0 regressions | §B paired design |
| Does labeled framing detect more on natural data? | **Yes, at scale** (100-case pool): 8x ENTAILED-per-match rate | §B pooled labeled+v0 |
| Does labeled framing help on EVERY natural sample? | **No** — the provisional assumption-gold set shows the opposite direction | §E |
| Does correction ship more under the full improved+labeled config? | **Yes, directionally** (10% vs historical ~0-2%), but n=1 shipped | §D |
| Is any of this synthetic-data performance (72.2% shipped) replicated on natural data? | **No, not remotely** — 1.8% cumulative, 10% best-case targeted regime | §A vs §D |
| Are parser/matcher defects driving the remaining gap? | **No** — 0 confirmed defects in 797 claims | §C |
| Is safety intact throughout? | **Yes** — 0/122 unsafe shipments across this project's entire history | §D |
