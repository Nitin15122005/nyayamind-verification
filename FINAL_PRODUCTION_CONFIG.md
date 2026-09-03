# Final Production Configuration — Decision Record

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Decided 2026-08-27. This document is the single source of truth for what
`research/prototype/config/prototype.yaml` ships with and why. Every option below was
evaluated against **all completed experiments** (synthetic + every natural evaluation this
project has run), never against synthetic results alone. Where the evidence justified a change,
`config/prototype.yaml` was updated and a regression test was added locking the new value
(`tests/test_premise_framing_production.py::test_shipped_config_locks_the_2026_08_27_final_production_decision`).
Full pytest (205/205) and `run_mvp.py --check` pass with the config exactly as shipped.

---

## Summary table

| Option | Old default | **New default** | Changed? |
|---|---|---|---|
| `premise_framing` | `bare` | **`labeled`** | ✅ Yes |
| `use_evidence_v1` | `false` | **`true`** | ✅ Yes |
| `correction.atomic_scope_check` | `false` | **`"assertion_spans"`** | ✅ Yes |
| `correction.narrow_reverification_hypothesis` | `false` | **`true`** | ✅ Yes |
| `verification.confidence_threshold` | `0.70` | `0.70` | No — evidence supports keeping it |
| Sibling-regression protection | — | Always active when either atomic-scope mode is on | Not independently toggleable |
| Citation-identity preservation on correction | — | Always active | Not independently toggleable, never was |

Every evaluation output committed **before 2026-08-27** was produced under the *old* values —
`config/prototype.yaml`'s own comments document exactly how to set every flag back to reproduce
that historical behavior byte-for-byte.

---

## 1. `premise_framing`: bare → **labeled**

### Evidence (three convergent, non-synthetic sources)

1. **Controlled benchmark** (420 curated real legal claims, not synthetic corruption):
   macro F1 **0.749 → 0.968**, ENTAILED recall 0.500 → 1.000, no per-condition regression
   (`outputs/verifier_correction_diagnosis.md`, `outputs/controlled_benchmark_deberta*_metrics.json`).
2. **CPU-only re-verification of real natural data** — the 147 evidence-matched claims from
   `final_gpu_validation`'s Arm B (v1 evidence, `assertion_spans` scope check), re-verified this
   session under labeled framing on the *exact same claims*: **ENTAILED 0 → 13**, verdict
   distribution measurably more decisive throughout, 0 change in CONTRADICTED count
   (`outputs/final_validation_bare_vs_labeled_cpu_metrics.json`).
3. **Real, targeted GPU correction validation** — the swing evidence. Labeled framing, combined
   with the full improved config, triggered correction in **10/50 cases** (vs 5/50 under bare on
   the identical cases) and **shipped 1 genuine, safe, substantively-correct correction** (0.995
   ENTAILED, 0 sibling regressions) — replacing a sentence that incorrectly restated Section
   302 IPC's *definition* language with its actual *punishment* text, matching real evidence
   almost verbatim. **Bare framing, same cases, same improved config: 0/5 shipped.** This is the
   first shipped correction on a "final validation"-caliber held-out natural batch in this
   project's history (`outputs/labeled_correction_validation_gpu_metrics.json`,
   `outputs/labeled_correction_validation_gpu_corrections_detail.jsonl`).

### Why this doesn't violate "don't decide from synthetic results alone"

None of the three sources above is synthetic-stress data (deliberately corrupted claims). The
controlled benchmark is curated real legal claims; the other two are this project's own natural
NyayaRAG data, generated fresh, never before evaluated.

### Honest caveat

Source 3 is **n=1 shipped / 10 triggered** — a small sample, and the newest, least-repeated
evidence behind any change in this document. It reverses a prior (pre-`assertion_spans`) natural
finding that labeled framing produced *worse* correction outcomes than bare (more scope
violations, same 0% shipped) — that finding was measured *without* `atomic_scope_check`, which is
exactly the gap this session's combined change closes. **Recommended follow-up**: a fresh
50-100-case batch under the full final config to confirm the shipped-correction rate holds up
at a larger sample size, before this is treated as fully settled rather than strongly indicated.

### A genuine counter-signal, reported honestly, not suppressed

A fourth comparison this session — re-verifying the 38 evidence-matched claims from
`assumption_annotation.jsonl` (the older n=30-era set, PROVISIONAL/Claude-generated labels, NOT
lawyer-verified) under labeled framing and checking agreement against those assumption labels —
found labeled framing agrees *slightly less* (18/38, 47.4%) than the already-stored bare verdicts
do (20/38, 52.6%), and only 2/38 claims flip to ENTAILED (`outputs/assumption_gold_bare_vs_labeled_metrics.json`).
This is the opposite direction from sources 1-3 above. The most likely explanation, consistent
with this project's own long-documented claim-bundling problem: this older set is dominated by
bundled, multi-citation listing sentences, and the PRIMARY verification pass (unlike
re-verification) always hypothesizes the full `claim_text`, never the narrower `assertion_text` —
so labeled framing's provision label helps less when the surrounding sentence still dilutes the
hypothesis with sibling citations' content. At n=38, against a provisional (not real) gold
standard, and on an older claim set, this is not treated as outweighing sources 1-3, but it is
recorded here in full rather than omitted, and it sharpens a concrete, evidence-backed item for
future work (extending `assertion_text`-based hypotheses to the PRIMARY verification pass, not
just re-verification) — see `outputs/final_limitations_and_future_scope.md`.

### What was NOT done

No safety gate or threshold was loosened to produce this result. The shipped correction passed
through the exact same `status == "corrected"` ⟺ `reverification.verdict == ENTAILED` gate every
other correction in this project's history has passed through.

---

## 2. `use_evidence_v1`: false → **true**

### Evidence

1. **Paired-arms GPU experiment** (`outputs/final_gpu_validation.md`): 50 held-out natural
   cases, same generation, evidence matched independently per arm. **+7.1pp evidence coverage**
   (63.2% → 70.3%), **McNemar χ²=13.07, p≈0.0003**, **zero regressions** (0 claims lost evidence
   that the v0-only pool had found).
2. **Independent audit** (`outputs/evidence_v1_independent_audit.md`, this session): 50% of the
   82 v1 records directly re-fetched from source and content-verified (vs. the original build's
   10%), plus a 100%-coverage structural/programmatic pass. **Zero fabricated or wrong-provision
   content found.** Two genuine, narrow defects found — **both fixed in place** (a missing inline
   omission note; a provenance mislabel corrected, downgrading one record out of the usable pool,
   137 → 136). A NO_EVIDENCE taxonomy re-run across all 797 claims from every natural experiment
   in this project's history found **zero confirmed parser/matcher defects** (2 near-miss
   candidates, both manually confirmed to be correct, safe behavior — now permanent regression
   tests in `tests/test_adversarial_citations.py`).

### Why this addresses the prior "not yet" condition

`README_v1.md` previously stated v1 was not audited enough to promote past 10% independent
verification. This session's audit raised that to 50% with no fabrication found and both real
defects fixed — the corpus's own stated blocker for wider use is substantially addressed.

### What's still true

v1 (like v0) remains explicitly **not** a substitute for professional legal review — no audit
this project performs changes that.

_See `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._ 39% of v1's records (32/82) still rest on build-time
provenance only, not independently re-verified this session (rate-limited by the source site,
not a decision to stop early) — see `evidence_v1_independent_audit.md` §6 for the full,
honestly-stated list of remaining gaps.

---

## 3. `correction.atomic_scope_check`: false → **`"assertion_spans"`**

### Evidence

- **Structurally safety-neutral-or-positive by construction**: the independent
  sibling-regression safety net (§4 below) exists specifically to cover the gap this relaxed
  check opens. Across every natural GPU experiment this project has run under it (this session:
  final_gpu_validation Arm B, the targeted labeled-framing correction validation), **0 unsafe
  corrections have ever shipped**.
- **Real natural-data motivation** (prior phase, `outputs/natural_candidates_50_gpu_report.md`
  §5): 4 of 6 genuine scope-violation-blocked edits on that batch were substantively valid fixes
  (e.g. a wrong provision number corrected) blocked purely by the legacy full-sentence
  requirement — the exact bundled-claim-sharing-one-sentence structural pattern
  `assertion_spans` targets.
- **This session's own tests**: the 2 scope-violation cases actually re-tested under
  `assertion_spans` (final_gpu_validation, both arms) were **correctly still rejected** — the
  narrower check did not spuriously let anything through. Honestly, this specific batch did not
  reproduce batch-1's "4/6 unlocked" finding; the decision rests on batch-1's larger sample plus
  the structural safety guarantee, not a repeat of that exact number here.

### Net judgment

No observed harm across every real test to date, a clear theoretical and previously-observed
benefit (unblocking legitimate bundled-sentence edits), and an independent safety net purpose-built
for the residual risk. This does not weaken any safety gate — it changes what counts as "in
scope" for the check, and the ENTAILED-only shipping gate is untouched.

---

## 4. `correction.narrow_reverification_hypothesis`: false → **true**

### Evidence

- On the final validation batch's 3 real `correction_failed` cases, this produced **more decisive,
  better-calibrated re-verification signals**: 2 of 3 converted a diluted, threshold-adjacent
  low-confidence NEI (an artifact of verifying a whole bundled sentence against one citation's
  narrow evidence) into a **decisive CONTRADICTED** — correctly identifying that an unchanged
  (no-op) correction was still wrong, not merely under-evidenced. The third converted a
  borderline low-confidence downgrade into an **unambiguous high-confidence NEI**.
- **Never widens what counts as evidence-consistent** — `assertion_text` is always a genuine,
  non-fabricated substring of the model's own corrected output (see `claim_parser.py`'s own
  invariant). It only asks a more precisely-targeted question about the same text.
- **Zero ship/reject outcomes changed** by this lever alone in the batches tested — its
  contribution is diagnostic quality, not (yet, in this sample) a different shipping decision.
  Paired with `atomic_scope_check` since a claim only has a narrower `assertion_text` in the
  first place when one of that feature's split patterns applied.

### Why "no harm found, real benefit found" is enough here

This is the lowest-risk of the four changed defaults: it only ever narrows the *hypothesis*
verified, never the evidence trusted, and the ENTAILED-only shipping gate applies identically
regardless.

---

## 5. `verification.confidence_threshold`: **unchanged at 0.70**

`outputs/threshold_sensitivity_analysis.md`'s deterministic sweep (0.50–0.95, no re-inference —
replayed against the already-computed 420-item controlled benchmark's stored softmax
distributions) shows 0.70 sits within 0.002 macro-F1 of the empirical optimum under **both**
framings:

| | bare (peak) | bare @0.70 | labeled (peak) | labeled @0.70 |
|---|---:|---:|---:|---:|
| macro F1 | 0.751 (@0.55–0.65) | 0.749 | 0.968 (@0.65–0.75) | **0.968** |

Under labeled framing (the new default), 0.70 sits *inside* the optimal plateau exactly. No
evidence anywhere in this project supports moving it, and per this task's explicit instruction,
it was not moved merely to chase a metric.

---

## 6. Sibling-regression protection — not an independent config option

`src/pipeline.py`'s `_reverify_sibling_regressions()` is **automatically active** whenever
`atomic_scope_check` is truthy (either `true`/legacy-atomic or `"assertion_spans"`) — it is not a
separate flag and cannot be independently disabled while an atomic scope-check mode is on. It
exists precisely because those modes relax the byte-for-byte full-sentence requirement, and its
job is to catch the case that relaxation could in principle miss: a sibling claim's *surrounding*
text (not its required fragment) changing enough to alter what it entails. It re-parses the
corrected text, finds each sibling's counterpart, and genuinely re-verifies it against its own
evidence — a correction can only ever be rejected by this check, never additionally approved by
it. Measured: 0 sibling regressions found in every triggered correction this session (10 in
`final_gpu_validation`, 10 in the labeled-framing correction validation).

---

## 7. Citation-identity preservation on correction — always on, was never a toggle

`apply_selective_correction()`'s ordinal-position citation-identity matching
(`_citation_identity()`, same-identity-claims ordinal lookup) is core, always-active pipeline
logic — present regardless of any config flag, in every mode and every framing this project has
ever run. It guarantees a corrected replacement claim is matched back to the *same* citation the
original flagged claim named, never a different one. This session's independent audit confirmed
it functions correctly: every case where a corrector's edit disturbed a claim's citation identity
correctly produced `correction_failed` with `reverification: null` (the "citation identity lost"
failure category — see `outputs/final_gpu_validation.md` §4), never a false ship.

---

## 8. What would justify a *different* answer

- **`premise_framing`**: a larger (50-100 case) fresh natural batch under the full final config
  showing the 1/10 shipped-correction rate holds or improves, OR any single unsafe shipment,
  which would immediately warrant reverting to `bare` pending investigation.
- **`use_evidence_v1`**: completing independent verification of the remaining 32/82 v1 records
  (currently blocked by source-site rate limiting, not a decision).
- **`atomic_scope_check`/`narrow_reverification_hypothesis`**: a larger sample of real
  scope-violation/correction_failed cases under the current combined config, to move past
  "no harm found" to a measured shipping-rate benefit specifically attributable to these two
  levers.

## 9. Regression tests locking this configuration

- `tests/test_premise_framing_production.py::test_shipped_config_locks_the_2026_08_27_final_production_decision`
  — asserts `config/prototype.yaml` exactly matches every value in the summary table above.
- `tests/test_premise_framing_production.py::test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`
  — asserts the pre-2026-08-27 combination (all four flags at their old values) still resolves
  correctly through the same production code path, so historical outputs remain reproducible.
- `tests/test_adversarial_citations.py` (15 tests, new this session) — locks the citation
  parsing/evidence-matching behavior this configuration relies on, including the one confirmed
  latent limitation (fuzzy matching is year-blind) so it cannot silently worsen.
