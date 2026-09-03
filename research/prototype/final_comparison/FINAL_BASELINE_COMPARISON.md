# Final Baseline Comparison — NyayaMind ORIGINAL vs CURRENT

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-27. This report is the narrative companion to the machine-computed
tables/figures in `final_comparison/tables/` and `final_comparison/figures/`, all produced
by `final_comparison/scripts/build_comparison_data.py` and `generate_figures.py` directly
from real, already-committed experiment artifacts in `research/prototype/outputs/`. Every
number quoted below traces to one of those tables — none is hand-typed independently of
them. See `comparison_config.json` for exact config definitions and source-file provenance,
and `RUN_COMPARISON.md` to reproduce every figure.

---

## Executive result

NyayaMind's own project history contains no external, separately-published "NyayaMind
paper" for this comparison to reproduce against (`outputs/final_limitations_and_future_scope.md`
states this explicitly). **"ORIGINAL" in this comparison therefore means this project's own
pre-2026-08-27 production baseline** — the configuration that produced every historical
output committed before that date — and **"CURRENT" means `research/prototype/config/prototype.yaml`
exactly as shipped**, both running through identical pipeline code. This is a controlled
configuration A/B on one project, not a comparison against an external system.

On the strongest available paired, real natural-data evidence (the `final_gpu_validation`
50-case batch and its two direct follow-on experiments):

- **Evidence coverage improved significantly and safely**: 63.2% → 70.3% (+7.1pp), McNemar
  χ²=13.07, p≈0.0003, zero claims lost evidence.
- **Premise framing (bare→labeled) is the dominant lever for verifier accuracy**: macro F1
  0.749→0.968 on a 420-item controlled benchmark (McNemar p≈10⁻²³); on natural data, ENTAILED
  reached on 147 already-matched claims went 0→13 (McNemar p≈0.0009).
- **Correction shipping improved directionally but not yet at a defensible sample size**:
  0/5 (ORIGINAL) → 1/10 (CURRENT, targeted validation); cumulative across this project's
  entire natural-data history, 1/56 (1.8%).
- **Safety remained fully intact throughout**: 0 unsafe corrections shipped across every
  attempt measured, in both ORIGINAL and CURRENT configurations.
- **Detection (CONTRADICTED count) did not improve** in the paired retrieval-only
  comparison — coverage gains landed as NEI, not new contradictions, when framing is held
  at bare.

None of this is claimed as validated legal accuracy. No lawyer ground truth exists anywhere
in this project (see "What still requires lawyer ground truth" below).

---

## What "original" means

There is no external NyayaMind paper in this repository to compare against. "ORIGINAL"
here is precisely defined in `comparison_config.json` as the configuration under which
every output committed before 2026-08-27 was produced:

| Setting | ORIGINAL value |
|---|---|
| `use_evidence_v1` | `false` (59-record evidence pool) |
| `premise_framing` | `bare` |
| `correction.atomic_scope_check` | `false` (legacy full-sentence rule) |
| `correction.narrow_reverification_hypothesis` | `false` |
| `verification.confidence_threshold` | `0.70` |

This is not a hypothetical reconstruction — `tests/test_premise_framing_production.py::test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`
pins that the current codebase still reproduces this exact combination byte-for-byte, and
`final_gpu_validation.md` Arm A is explicitly labeled `[PRE-2026-08-27 PRODUCTION BASELINE]`
in this project's own artifacts.

**One nuance, disclosed explicitly**: the very earliest experiments (`run_A/B/C_n30`,
`run_natural_targeted`, commit `0e37525`) predate an even earlier claim-parser fix (commit
`223eb9d`) and used a buggier parser. The primary ORIGINAL baseline used throughout this
comparison (`final_gpu_validation` Arm A, and the `batch1`/`batch2` bare-v0 runs) already
uses the current, fixed parser — that earlier fix is measured separately as its own
ablation (see Ablations below), not conflated with the four-lever ORIGINAL/CURRENT
distinction.

## What changed in NyayaMind

Four configuration levers changed, each independently evidenced before being combined
(`FINAL_PRODUCTION_CONFIG.md` is the full decision record):

1. **`premise_framing: bare → labeled`** — the NLI premise is prefixed with the provision
   label ("Section 302 of the IPC: ...") instead of statute text alone.
2. **`use_evidence_v1: false → true`** — evidence pool expands from 59 to 136 records
   (78 new + 3 corrections to v0, 1 later downgraded by this session's own audit).
3. **`correction.atomic_scope_check: false → "assertion_spans"`** — the scope-violation
   check on unflagged claims narrows from "the full original sentence must survive
   byte-for-byte" to "each unflagged claim's own verbatim sub-span must survive."
4. **`correction.narrow_reverification_hypothesis: false → true`** — correction
   re-verification uses a claim's own narrower `assertion_text` instead of the full bundled
   sentence, when one exists.

Unchanged: generation model/prompts, verification model, confidence threshold (0.70),
correction model/prompts, seed (42), and two invariants that were never toggles in the
first place — the sibling-regression safety net (auto-active whenever a scope-check mode is
on) and citation-identity preservation on correction (always active).

**No single experiment in this project has flipped all four levers simultaneously on one
fresh natural GPU batch from a single generation pass.** The strongest available evidence
chains four real experiments on the *same* 50-case batch: Arm A (ORIGINAL) → Arm B (+v1
evidence/+scope/+narrow-reverify, still bare) → a CPU-only labeled re-verification of Arm
B's claims (+labeled) → a targeted GPU correction validation under the full combination
(+labeled correction path). This is disclosed as a real gap, not glossed over — see
Limitations.

## Dataset / evaluation protocol

| Dataset | n | Real GPU? | Role |
|---|---:|---|---|
| `final_gpu_validation` (Arms A/B) | 50 cases, 209 claims | Yes | Primary paired ORIGINAL-vs-(+retrieval/+scope/+narrow) comparison, isolates retrieval |
| `final_validation_bare_vs_labeled_cpu` | 147 already-matched claims (subset of above) | No (CPU re-verify) | Isolates premise framing on natural data, same claims |
| `labeled_correction_validation_gpu` | 10 triggered cases (subset of above) | Yes | Isolates framing's effect on correction shipping |
| `controlled_verifier_benchmark` | 420 curated items | No (CPU) | Calibration benchmark, not natural data; strongest statistical signal for framing |
| Pooled bare+v0 natural (n30+batch1+batch2+finalA) | 180 cases, 784 claims | Yes | Largest ORIGINAL-regime pool, NOT paired with the labeled pool below |
| Pooled labeled+v0 natural (batch1+batch2) | 100 cases, 487 claims | Yes | Largest labeled-framing natural pool at v0 evidence, NOT paired with the above |
| `parser_fix_before_after_n30` | 30 documents, re-parsed | No | Isolates the claim-parser fix (commit 223eb9d) |
| `atomic_scope_check_final_replay` | 11 real scope-violation cases | No (deterministic replay) | Isolates the scope-check lever |
| `evidence_coverage_v0_vs_v1` | 588 pooled claims | No (corpus scan) | Corpus-level corroboration of the retrieval lever |
| `assumption_gold_bare_vs_labeled` | 38 claims vs PROVISIONAL Claude-generated labels | No | **PROVISIONAL only** — not accuracy |

Case selection for every natural batch is a deterministic function of NyayaRAG's own
citation keys and case length, computed before any generation — no outcome leakage
(`natural_candidate_selection_report_final_validation.md`). All natural batches are
confirmed pairwise-disjoint document_id sets (`final_research_results.md` §0).

---

## Retrieval results

**Paired, 50 cases, bare framing held fixed in both arms** (`retrieval_results.csv` row 1,
independently recomputed in `build_comparison_data.py` from the raw per-claim JSONL, not
copied from a prior report):

| | ORIGINAL | CURRENT (retrieval only) | Δ |
|---|---:|---:|---:|
| Claims matched | 132/209 (63.2%) | 147/209 (70.3%) | +15 (+7.2pp) |
| Claims lost | — | 0 | 0 regressions |
| Verdict flips among claims matched in both | — | — | 0 |

McNemar (continuity-corrected) χ²=13.07, p≈0.0003; exact two-sided sign test on 15
one-directional discordant pairs, p≈6.1×10⁻⁵ — independently confirms the same conclusion.
All 15 gained matches are `exact_normalized`, not fuzzy.

Corpus-level corroboration (588 claims pooled from every natural experiment, not an
independently paired arm — see `retrieval_results.csv` row 2): 60.2% → 66.3% (+6.1pp, +36
claims). Consistent in direction and rough magnitude with the paired result; not separately
tested for significance to avoid double-counting the same underlying phenomenon.

**What this does not show**: detection improved. All 15 gained-evidence claims resolved to
NOT_ENOUGH_INFORMATION under bare framing, none to CONTRADICTED or ENTAILED — see Case 3.

## Verification results

**Premise framing, controlled benchmark (420 curated items, paired)** — the single
strongest statistical result in this project:

| | ORIGINAL (bare) | CURRENT (labeled) |
|---|---:|---:|
| Accuracy | 73.3% | 97.1% |
| Macro F1 | 0.749 | 0.968 |
| ENTAILED recall | 0.500 | 1.000 |

McNemar χ²=98.01, exact sign-test p≈1.6×10⁻³⁰. This is a curated adversarial benchmark
(attribution/paraphrase/negation factors), not natural generated text — a calibration
signal, not a natural-data result.

**Premise framing, natural data (147 already-matched claims, CPU re-verification, paired)**:
ENTAILED 0→13 (McNemar χ²=11.08, p≈0.0009; exact sign-test p≈0.00024). One reversal in the
opposite direction also occurred (a CONTRADICTED claim became NEI under labeled) — the
effect is strongly but not purely one-directional (see Case 2).

**Detection (CONTRADICTED), paired retrieval-only comparison**: unchanged, 3/209 in both
arms, byte-identical confidences — the same 3 claims, because this experiment holds framing
at bare in both arms by design (see Case 6). This experiment cannot and does not claim
detection improved; it isolates retrieval alone.

**Pooled natural-data scale check** (not paired, different case sets, reported directionally
only): bare+v0 pooled (180 cases, 784 claims) reaches ENTAILED on 2/454 matched claims
(0.4%); labeled+v0 pooled (100 cases, 487 claims) reaches ENTAILED on 16/284 matched claims
(5.6%) — an 8× rate difference at a defensible pooled sample size, though not a controlled
experiment.

**Honest counter-signal**: against the older, PROVISIONAL, non-lawyer `assumption_annotation.jsonl`
set (38 evidence-matched claims, bundled-sentence-heavy), labeled framing agrees *less*
(18/38, 47.4%) than bare's already-stored verdicts (20/38, 52.6%). This is recorded, not
suppressed — see Limitations.

## Correction results

| Regime | Triggers | Shipped | Shipped rate | Unsafe |
|---|---:|---:|---:|---:|
| ORIGINAL — final-validation Arm A | 5 | 0 | 0% | 0 |
| +retrieval/+scope/+narrow-reverify, still bare — Arm B | 5 | 0 | 0% | 0 |
| **CURRENT (all four levers) — targeted GPU validation** | 10 | **1** | **10%** | 0 |
| Cumulative, all natural regimes/history (56 attempts) | 56 | 1 | 1.8% | 0 |
| Synthetic stress, labeled (calibration only, NOT natural) | 36 | 26 | 72.2% | 0 |

The one shipped correction (`2003_760`/c3, Case 4) replaced a sentence that incorrectly
restated Section 302 IPC's *definition* language with its actual *punishment* text —
re-verified ENTAILED at 0.995, 0 sibling regressions. **This is n=1 shipped / 10 triggered**
— directional evidence, not a measured rate (Wilson 95% CI for CURRENT: [0.018, 0.404];
for ORIGINAL: [0.000, 0.434] — the intervals overlap almost entirely; no 2-proportion
significance test is reported because n is too small to support one, see
`statistical_tests.csv`).

The synthetic 72.2% figure has never transferred to natural data at anywhere near this
magnitude across five natural correction batches now (n≈41-era, batch1, batch2, and both
final-validation arms) — see figure 11.

## Safety results

| | ORIGINAL (pooled natural attempts) | CURRENT (targeted validation) | Cumulative (all history) |
|---|---:|---:|---:|
| Correction attempts | 15 | 10 | 56 (+ 66 synthetic) |
| Unsafe shipped | 0 | 0 | 0 |
| Scope violations | (5 combined across batch1/batch2/final-A) | 3 | 18 |
| Sibling regressions found | n/a (mechanism inactive under legacy scope check) | 0 (checked once, on the 1 shipped case) | 0 (checked on every triggered correction under `assertion_spans`) |

**Zero unsafe corrections have shipped across every correction attempt in this project's
history, in both ORIGINAL and CURRENT configurations.** This is structurally guaranteed by
the `status=="corrected"` ⟺ `reverification.verdict=="ENTAILED"` invariant and empirically
confirmed every time it was checked. Citation-identity preservation on correction
(`_citation_identity()`) is always active in both configurations — never a toggle — and
every case where an edit disturbed citation identity correctly produced `correction_failed`
with `reverification=null` rather than a false ship.

**Zero observed unsafe shipments is an observed safety result on the data measured so far,
not a proof of zero future risk.** The largest single CURRENT-config correction sample is
10 triggered cases; the scope-check relaxation was stress-tested on only 11 real
scope-violation replays (1 unblocked) and 2 within the paired batch (Case 5). A materially
larger sample could still surface an unsafe edge case the sibling-regression net does not
catch — the net itself has fired 0 times in this project's history because nothing unsafe
has reached it, which means its own effectiveness against a genuine attempt is also
unproven, not just its necessity.

## Ablations

See `ablation_results.csv` for the full machine-generated table; summary:

| Lever | Verdict |
|---|---|
| Evidence corpus (v0→v0+v1) | **Confirmed**: significant, safe (McNemar p<0.001, 0 regressions) |
| Claim parser (pre-fix→current) | **Confirmed**: unambiguous improvement, 6/30 documents improved, 0 worsened (exact sign-test p≈0.031); not a strict paired-claim comparison since segmentation itself changed (88→93 claims) |
| Premise framing (bare→labeled), controlled benchmark | **Confirmed**: largest, most robust effect measured (McNemar p≈10⁻²³) — calibration data, not natural |
| Premise framing (bare→labeled), natural CPU re-verify | **Confirmed**: dominant driver of correction triggers (9→19) and ENTAILED (0→13) |
| Scope-check (legacy→assertion_spans) | **Weak/inconclusive**: 1/11 real scope violations unblocked in the full deterministic replay across both batches; an earlier batch1-only analysis found 4/6 legacy-blocked edits were substantively valid, not reconciled with this larger, less favorable replay |
| Narrow re-verification hypothesis | **Confirmed diagnostic-quality lever, no shown shipping-outcome effect**: 0/3 ship/reject outcomes changed; 2/3 converted diluted NEI to decisive CONTRADICTED, 1/3 to unambiguous NEI |
| Citation-identity preservation | Invariant in both configs — not an ablation, included for completeness |

Because Arm B changes three levers at once, attribution is possible from the outcome
pattern itself (`final_gpu_validation.md` §7): every measured difference in verdict counts
traces to the 15 newly-matched claims from retrieval — the scope-check and
narrow-reverification levers changed reasoning quality on already-failed corrections but no
ship/reject counts, in this specific 50-case sample. No interaction effects are observable
in available data; this cannot rule out interactions that only appear jointly with labeled
framing at a larger sample.

## Statistical analysis

Full detail in `statistical_tests.csv`. Every paired comparison uses McNemar's test
(continuity-corrected) plus an independent exact two-sided sign test as a cross-check —
both methods agree on every comparison performed. Where sample sizes are too small to
support a meaningful test (correction shipping, n=5 vs n=10; scope-check unblocking, n=11
with 1 discordant case), this is stated explicitly and no p-value is manufactured — Wilson
95% confidence intervals are reported instead, and both intervals are shown to overlap
substantially.

| Comparison | n | Method | Statistic | p-value |
|---|---:|---|---:|---:|
| Evidence coverage (retrieval, paired GPU) | 209 | McNemar | χ²=13.07 | 0.0003 |
| ENTAILED rate (framing, natural CPU re-verify) | 147 | McNemar | χ²=11.08 | 0.0009 |
| Accuracy (framing, controlled benchmark) | 420 | McNemar | χ²=98.01 | ≈1.6×10⁻³⁰ (exact sign test) |
| Correction shipped rate (ORIGINAL vs CURRENT) | 5 vs 10 | Wilson CI only | — | not tested — n too small |
| Evidence coverage (parser fix, per-document sign test) | 30 docs | exact sign test | 6 improved / 0 worsened | 0.031 |

Effect sizes: retrieval +7.2pp (McNemar-supported); framing macro-F1 +0.22 (McNemar-supported,
calibration data); framing ENTAILED-rate +8.8pp on 147 natural claims (McNemar-supported);
correction shipped rate +10pp directional only, not power-supported.

## Representative cases

Full detail with exact source records and reproduction commands in `cases/`:

1. **Genuine improvement** — `2002_731`/c4: bare NEI (0.995) → labeled ENTAILED (0.996), same
   claim, same evidence.
2. **Genuine detection missed by ORIGINAL** — `2006_1150`/c12: bare NEI (0.913) → labeled
   CONTRADICTED (0.811), a real misattribution (Section 468 mislabeled "criminal conspiracy").
3. **Retrieval improvement** — `2000_1266`/c1: v0 NO_EVIDENCE → v0+v1 matched (Section 197
   CrPC), same generation.
4. **Correction improvement** — `2003_760`/c3: the one shipped correction, Section 302's
   definition-language error fixed to punishment text, ENTAILED 0.995, 0 sibling regressions.
5. **Safe rejection of an unsafe/out-of-scope correction** — `2006_770`/c1: real Qwen edit
   correctly rejected as a scope violation identically under both the legacy and
   `assertion_spans` checks.
6. **Both systems behave identically** — `2006_770`/c2: CONTRADICTED at byte-identical
   confidence (0.97217) in both ORIGINAL and CURRENT (retrieval-only) arms — a correctly
   predicted null result, and a genuine, manually-inspected content catch.
7. **Important remaining failure** — `2004_1020`/c6: Qwen returns a no-op; CURRENT's narrow
   reverification correctly upgrades a borderline NEI (0.665) to a decisive CONTRADICTED
   (0.917), but the outcome is `correction_failed` either way — diagnosis improved, the fix
   still did not happen.

## Limitations

- **The four CURRENT levers were never jointly measured on one fresh natural GPU batch from
  a single generation pass** — the strongest evidence is a four-experiment chain on the same
  50-case batch, not one combined run. Stated explicitly in `comparison_config.json`.
- **Detection (CONTRADICTED count) has not been shown to improve** — the only paired
  natural-data measurement (retrieval-only, bare framing both arms) found it flat (3=3).
  Framing's effect on detection is measured on natural data only via the unpaired pooled
  comparison and the CPU re-verify chain, not a single controlled experiment isolating
  framing alone with a fresh generation pass.
- **Correction shipping improvement is not statistically supported** — n=5 vs n=10 is too
  small for a defensible test; reported directionally only.
- **The scope-check ablation is genuinely inconclusive** and its own two available
  measurements (batch1-only 4/6, full 11-case replay 1/11) are not reconciled — both are
  reported rather than picking the more favorable one.
- **The assumption-gold counter-signal is real and unresolved**: labeled framing agrees
  *less* with an older, bundled-sentence-heavy PROVISIONAL label set. The likely mechanism
  (primary verification never uses the narrower `assertion_text` hypothesis) is documented
  but not yet fixed or tested.
- **No true retrieval precision or false-match rate exists** for either configuration —
  only proxies (exact/fuzzy match ratio, manual inspection of CONTRADICTED verdicts).
- **VRAM is only measured for the shared paired GPU session**, not decomposed per arm
  (`efficiency_results.csv`); the targeted correction-validation run did not separately log
  VRAM.
- **Claim-parser ablation is not a strict paired-claim comparison** — the fix changes claim
  segmentation itself (88→93 claims across the same 30 documents), so "coverage" is compared
  at the document level, not the individual-claim level.

## What we can honestly claim

- Evidence coverage improved, safely and significantly, from the v1 corpus expansion
  (McNemar p<0.001, paired, 0 regressions).
- Premise framing (labeled) is the dominant lever for verifier accuracy on curated legal
  claims (macro F1 +0.22, p≈10⁻²³), and measurably increases ENTAILED reached on real
  natural claims when framing alone is isolated (0→13 of 147, p≈0.0009).
- Safety has remained fully intact across every measured correction attempt, in both
  configurations, across this project's entire history (0/56+66 unsafe).
- The verification layer catches genuine, individually-verifiable contradiction errors on
  real, previously-unseen generated text, not just synthetic ones (Cases 2, 6).
- The full CURRENT configuration shipped a genuine, safe, substantively correct real-data
  correction for the first time in this project's history (Case 4) — demonstrated possible,
  not yet a measured rate.
- The claim parser fix (commit 223eb9d) unambiguously improved evidence coverage on the same
  30 documents, with zero documents made worse.

## What still requires lawyer ground truth

No lawyer or professional legal ground truth exists anywhere in this project
(`REPOSITORY_MANIFEST.md` §6, `final_limitations_and_future_scope.md` §3b). This means, for

> _See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

both ORIGINAL and CURRENT, this comparison **cannot** and does not claim:

- True contradiction recall or false-positive rate (only synthetic-data figures exist for
  these, and this project's own history shows synthetic results do not predict natural
  behavior — synthetic labeled correction success 72.2% vs natural 1.8-10%).
- True retrieval precision (whether a matched citation is the legally correct provision) —
  only match-method proxies and manual spot-inspection exist.
- Any accuracy figure against `assumption_annotation.jsonl` or `lawyer_annotation.jsonl` —
  both are Claude-generated PROVISIONAL labels, explicitly disclaimed as such everywhere
  they appear, never a substitute for professional review.
- That either configuration's verdicts are legally correct in any individual case — every
  case study in `cases/` is presented as "what the automated system did," never as "what the
  law actually says."

## Final conclusion

Within the bounds of what this project can measure without lawyer ground truth, the CURRENT
production configuration improves on the ORIGINAL pre-2026-08-27 baseline on two
independently-evidenced, statistically supported axes — evidence coverage and premise-framing
detection/entailment accuracy — while preserving a perfect safety record across every
measured correction attempt in both configurations. The correction-shipping improvement is
real but small-sample and directional only; the scope-check and narrow-reverification levers
are shown to cause no harm but not yet a measured shipping benefit; and one natural-data
counter-signal (assumption-gold agreement) is reported honestly rather than omitted. The
single most valuable next experiment — a larger, fresh, single-pass natural batch under the
full CURRENT configuration — is not required to trust any number in this comparison, but
would move the correction-shipping and joint-lever findings from "demonstrated possible" to
"measured at a defensible sample size."
