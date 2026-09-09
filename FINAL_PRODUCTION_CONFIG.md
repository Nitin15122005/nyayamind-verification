# Final Production Configuration — Decision Record

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Decided 2026-08-27. This document is the single source of truth for what
`research/prototype/config/prototype.yaml` ships with and why. Every option below was
evaluated against **all completed experiments** (synthetic + every natural evaluation this
project has run), never against synthetic results alone. Where the evidence justified a change,
`config/prototype.yaml` was updated and a regression test was added locking the new value
(`tests/test_premise_framing_production.py::test_shipped_config_locks_the_2026_08_27_final_production_decision`).
Full pytest (205/205 as of 2026-08-27; the suite has grown since as later commits added their
own regression tests — see each commit's message for its own count) and `run_mvp.py --check`
pass with the config exactly as shipped.

---

## Summary table

| Option | Old default | **New default** | Changed? |
|---|---|---|---|
| `premise_framing` | `bare` | **`labeled`** | ✅ Yes |
| `use_evidence_v1` | `false` | **`true`** | ✅ Yes |
| `correction.atomic_scope_check` | `false` | **`"assertion_spans"`** | ✅ Yes |
| `correction.narrow_reverification_hypothesis` | `false` | **`true`** | ✅ Yes |
| `verification.narrow_primary_hypothesis` | `false` | **`true`** (added 2026-09-09) | ✅ Yes |
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
bundled, multi-citation listing sentences, and at the time this section was written the PRIMARY
verification pass (unlike re-verification) always hypothesized the full `claim_text`, never the
narrower `assertion_text` — so labeled framing's provision label helped less when the surrounding
sentence still diluted the hypothesis with sibling citations' content. At n=38, against a
provisional (not real) gold standard, and on an older claim set, this was not treated as
outweighing sources 1-3, but it was recorded here in full rather than omitted, and it sharpened a
concrete, evidence-backed item for future work.

**Addressed 2026-09-09 — see §5 below.** `verification.narrow_primary_hypothesis` now extends
`assertion_text`-based hypotheses to the PRIMARY verification pass, not just re-verification.
This paragraph's diagnosis is kept as historical record of why that change was made.

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

**Update 2026-09-08 — a real gap found and fixed in the containment mechanics itself, not the
above decision.** `pipeline._scope_violation()`'s `assertion_spans` check used plain Python `in`
substring containment. A bare provision-number fragment (`claim_parser._bare_number_span`, used for
the "respectively" pattern — e.g. the flagship sentence's own "34") is trivially "present" inside
an unrelated, unauthorized "134" — so a corrector silently changing an UNFLAGGED sibling's own
section number (e.g. 34 → 134) could ship undetected: reproduced concretely, and confirmed that
`_reverify_sibling_regressions` (§4's safety net) does **not** catch it either, since it explicitly
skips a sibling whose citation no longer re-extracts at all, assuming (incorrectly, in this one
case) the scope check had already rejected it. Fixed via `_fragment_present()`, which anchors a
`\b` word-boundary at whichever end of a fragment is itself a word character — this only tightens
the check (a genuine, honestly-preserved verbatim fragment always already sits at a real
word/punctuation boundary), never loosens it. This was never observed in any committed real-data
run (like the evidence-matcher year-blindness gap, this is a theoretical/adversarially-discovered
class of gap, not a retroactive finding against the "0 unsafe corrections shipped" observation
above) — no historical output is affected. See
`tests/test_pipeline_mock.py::test_assertion_spans_catches_sibling_provision_number_changed_to_a_superstring`.

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

## 5. `verification.narrow_primary_hypothesis`: false → **true** (added 2026-09-09)

### What it does

Extends the exact same technique in §4 above — verify a claim's narrower `assertion_text`
instead of the full bundled `claim_text`, when a genuinely narrower one is available — to the
**primary** verification pass, not just correction re-verification. This closes a gap
`outputs/final_limitations_and_future_scope.md` §3a named explicitly as unaddressed: "the
primary verification pass never uses the narrower `assertion_text` hypothesis."

### Evidence

`scripts/benchmark_narrow_primary_hypothesis.py` re-scored, on CPU, every unique real
evidence-matched `(claim_text, evidence_id)` pair already committed under `outputs/*.jsonl` —
**456 claims**, no fresh generation, under the current production "labeled" premise framing
(see `outputs/narrow_primary_hypothesis_benchmark_report.md` for the full report):

- **107/456 (23.5%)** claims have an actually-narrower `assertion_text` — the only population
  this change can affect at all.
- **31** flip NOT_ENOUGH_INFORMATION → ENTAILED. Every one of the first 10 (and a spot-check of
  the rest) manually inspected: each is a genuine, faithful, verbatim isolation of one citation's
  own clause from a bundled multi-citation sentence (e.g. "Section 323 IPC pertains to
  voluntarily causing hurt" correctly isolated from a 4-citation bundle) — **not** the
  "shallow"/spurious-entailment pattern `outputs/verifier_correction_diagnosis.md` §6 warned
  labeled framing alone could produce on bundled sentences (that pattern was the *opposite*
  direction: a full sentence entailed against an unrelated section's text).
- **2** flip NEI → CONTRADICTED — new, legitimate correction triggers.
- **0/456 safety-relevant reversals** (ENTAILED↔CONTRADICTED) anywhere in the dataset.

### Why this is adopted, not just evaluated

Same risk profile as §4: only narrows the hypothesis, never widens what counts as
evidence-consistent (`assertion_text` is always a genuine substring of the model's own generated
text), and the shipping/verdict gate is otherwise unchanged. Zero unsafe reversals across every
real evidence-matched claim this project has ever produced is a stronger evidentiary bar than
several of the other defaults above cleared at the time they were adopted.

### Caveat, stated honestly

This is CPU re-scoring of already-generated text, not a fresh end-to-end GPU run — it does not
by itself measure the downstream effect on `correction` shipping rates (the 2 new
NEI→CONTRADICTED claims are new correction *triggers*, not yet observed shipped corrections).

**Follow-up done 2026-09-09** (`scripts/run_narrow_primary_hypothesis_gpu_ablation.py`, see
`outputs/narrow_primary_hypothesis_gpu_ablation_report.md`): a fresh, real end-to-end Mode-C GPU
run (Qwen2.5-7B generation + DeBERTa verification + selective correction, through the actual
production `pipeline.py`) on **15 genuinely fresh** natural cases never used in any prior
experiment in this repo, isolating exactly this one lever (OLD=false vs CURRENT=true, everything
else identical). Result, stated honestly:

- **Verification recovery confirmed directionally**: 1/12 evidence-matched claims flipped
  NEI → ENTAILED under CURRENT vs OLD — small-sample but consistent with the CPU benchmark's
  mechanism and direction.
- **Correction shipping remains genuinely unmeasured, NOT improved**: correction triggered
  **0/15 times under BOTH arms** — this batch produced zero CONTRADICTED verdicts and zero
  low-confidence-NEI triggers on either config, so the correction pathway was never even
  entered. This is not a null result for the lever; it is an absence of the precondition
  (a flagged claim) needed to observe one, at this sample size. **Do not read this as evidence
  the 1.8%-cumulative correction-shipping rate improved or stayed flat — it was not exercised at
  all in this batch.** A larger fresh batch (n>=50, matching the scale of
  `outputs/final_gpu_validation.md`) is the natural next step to actually observe correction
  behavior under this lever, not done in this session for time/GPU-cost reasons.

---

## 6. `verification.confidence_threshold`: **unchanged at 0.70**

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

## 7. Sibling-regression protection — not an independent config option

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

## 8. Citation-identity preservation on correction — always on, was never a toggle

`apply_selective_correction()`'s ordinal-position citation-identity matching
(`_citation_identity()`, same-identity-claims ordinal lookup) is core, always-active pipeline
logic — present regardless of any config flag, in every mode and every framing this project has
ever run. It guarantees a corrected replacement claim is matched back to the *same* citation the
original flagged claim named, never a different one. This session's independent audit confirmed
it functions correctly: every case where a corrector's edit disturbed a claim's citation identity
correctly produced `correction_failed` with `reverification: null` (the "citation identity lost"
failure category — see `outputs/final_gpu_validation.md` §4), never a false ship.

**Update 2026-09-08 — a real gap found and fixed in the ordinal-matching mechanics themselves,
found during a multi-agent adversarial hardening campaign.** The ordinal-position scheme above
relies on an invariant the scope check never actually enforced: that same-citation-identity
siblings keep their *relative order* in the corrected text, not just their presence somewhere in
it. Reproduced concretely: two claims sharing one citation, the corrector's output reorders them
(the newly-corrected one moved ahead of the untouched sibling) — every unflagged claim's text
still appeared verbatim (the scope check passed), but "the Nth same-identity claim in reading
order" no longer denoted the same claim slot it did in the baseline, so the replacement lookup
silently grabbed the untouched sibling's own original sentence and shipped `status="corrected"`
with a genuine-looking ENTAILED confirmation that was never computed against the real edit at
all — a **fabricated safety confirmation**, strictly worse than an honest rejection. Fixed via an
ordinal-integrity check (`apply_selective_correction`, new status
`correction_ordinal_ambiguous`): if the selected "replacement" is byte-identical to some *other*
same-identity claim's own original baseline text, the ordinal slot is untrusted and the correction
is rejected rather than shipped. See
`tests/test_pipeline_mock.py::test_reordered_shared_citation_claims_rejected_not_fabricated_as_corrected`.

**Also fixed in the same pass:** (a) a corrector hallucinating a brand-new, never-requested
citation (alongside a genuinely correct fix to the flagged claim, or by swapping the flagged
claim's own citation for a different provision) previously shipped undetected — `_scope_violation`
only verified *existing* unflagged claims survive, with no concept of "no new citation may be
introduced"; fixed via a new `correction_unauthorized_addition` status
(`tests/test_pipeline_mock.py::test_correction_hallucinating_an_extra_new_citation_is_rejected_not_shipped`).
(b) `_reverify_sibling_regressions()` previously re-checked *every* unflagged sibling
indiscriminately, including one that was already independently CONTRADICTED in the *baseline* (a
pre-existing failure the correction attempt never touched — only the first flagged claim in a
field is ever targeted) — mislabeling an otherwise-successful correction as
`correction_sibling_regression` and conflating "my edit broke something" with "something else was
already broken." Fixed by excluding already-independently-flagged siblings from this check
(`tests/test_pipeline_mock.py::test_sibling_regression_check_excludes_a_pre_existing_independently_flagged_sibling`).

---

## 8a. Negation safety gate — new, 2026-09-08

Empirically confirmed (real `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, real IPC evidence,
during the same hardening campaign's adversarial claim-parser audit): a negated statutory claim
("Neither Section 302 nor Section 304 of the Indian Penal Code, 1860 applies to this case.")
reaches CONTRADICTED at 0.998 confidence, while the identical legal content phrased affirmatively
reaches ENTAILED at 0.896 against the same premise — a well-documented general NLI weakness
(negation-word/contradiction spurious correlation), not something any premise-construction change
can repair in a fixed pretrained model. This matters because CONTRADICTED always triggered
automatic correction: unmitigated, the pipeline could rewrite a claim that correctly, truthfully
asserts a *negative* legal conclusion (e.g. explaining why a lesser charge applies instead) into an
affirmative statement — which, if the rewrite happened to re-verify ENTAILED, would ship a claim
asserting the *opposite* of what may have been true. Fixed via a narrow, lexical negation-marker
check (`pipeline._NEGATION_MARKER_RE` — "neither...nor", "does/do/did not apply",
"is/are/was/were not applicable", "no longer applies/applicable", "not applicable"): a
CONTRADICTED verdict matching one of these patterns is excluded from the automatic
correction-trigger list (a new `negation_contradiction_caveat` claim-record field marks this) —
the verdict/confidence themselves are left fully untouched and visible for manual review; only the
automatic rewrite attempt is suppressed. Confirmed via both a real-model test
(`tests/test_correction_path_real_integration.py::test_negated_claim_reaches_contradicted_via_real_verifier_but_never_triggers_correction`,
using a corrector that raises `AssertionError` if ever invoked, proving the attempt itself is
suppressed) and a mock-based wiring test. This is a narrow, deterministic safety gate on the
correction *trigger*, not a threshold/calibration change — no NLI threshold was touched, and this
never widens what counts as ENTAILED/CONTRADICTED/NO_EVIDENCE for any other claim.

---

## 9. What would justify a *different* answer

- **`premise_framing`**: a larger (50-100 case) fresh natural batch under the full final config
  showing the 1/10 shipped-correction rate holds or improves, OR any single unsafe shipment,
  which would immediately warrant reverting to `bare` pending investigation.
- **`use_evidence_v1`**: completing independent verification of the remaining 32/82 v1 records
  (currently blocked by source-site rate limiting, not a decision).
- **`atomic_scope_check`/`narrow_reverification_hypothesis`**: a larger sample of real
  scope-violation/correction_failed cases under the current combined config, to move past
  "no harm found" to a measured shipping-rate benefit specifically attributable to these two
  levers.

## 10. Regression tests locking this configuration

- `tests/test_premise_framing_production.py::test_shipped_config_locks_the_2026_08_27_final_production_decision`
  — asserts `config/prototype.yaml` exactly matches every value in the summary table above.
- `tests/test_premise_framing_production.py::test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`
  — asserts the pre-2026-08-27 combination (all four flags at their old values) still resolves
  correctly through the same production code path, so historical outputs remain reproducible.
- `tests/test_adversarial_citations.py` (15 tests, 2026-08-27) — locks the citation
  parsing/evidence-matching behavior this configuration relies on. Its one confirmed latent
  limitation (fuzzy matching was year-blind) was fixed 2026-09-07 in `evidence_matcher.py`
  (`_year_conflict` veto); the test suite now pins the fixed, safer behavior (17 tests in that
  file) instead of merely pinning the known gap.
