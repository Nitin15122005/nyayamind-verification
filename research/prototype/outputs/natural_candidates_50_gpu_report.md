# 50-Case Deterministic-Pool Natural GPU Experiment — Report

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. Runs the deterministic 50-case candidate pool from
`natural_candidate_selected_ids_50.json` (`select_natural_candidates.py`) through the
real end-to-end pipeline for the first time: genuine Qwen2.5-7B generation (never run on
these cases before), genuine DeBERTa verification, and genuine Qwen correction +
re-verification, both premise-framing arms, on the RTX 4050.

> **Scope of every verdict below.** Outputs of a small public NLI model
> (DeBERTa-v3-base-mnli-fever-anli) and a 7B instruction model (Qwen2.5-7B-Instruct,
> 4-bit), checked against a 59-record third-party-sourced evidence corpus. Not
> legal-correctness determinations. No lawyer ground truth exists or is used here.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

---

## 0. Method

- Cases: exactly the 50 document_ids in `outputs/natural_candidate_selected_ids_50.json`,
  loaded from the raw NyayaRAG source JSON (never before generated in this project), using
  the same multi/single-variant tie-break the selection script used.
- Generation: **run once per case** (Qwen2.5-7B-Instruct, 4-bit, greedy/deterministic,
  seed 42) — shared across both framing arms, exactly as `pipeline.py`'s module docstring
  specifies generation is mode/framing-independent. **Not** re-scored from any prior run;
  these 50 cases have never been generated before in this project.
- Verification: genuine DeBERTa calls, once per arm, current `claim_parser` +
  `evidence_matcher` (post the bug fixes from the previous phase).
- Correction: genuine Qwen calls wherever a claim triggers (`CONTRADICTED`, or
  `NOT_ENOUGH_INFORMATION` with the `low_confidence` downgrade) — the same unmodified
  `pipeline.apply_selective_correction`, same 0.70 threshold, same safety gate.
- `config/prototype.yaml` untouched (`premise_framing: bare` remains the default). No
  threshold changed. Script: `scripts/run_natural_candidates_50_gpu.py` (new). Outputs:
  `natural_candidates_50_gpu_{metrics.json, bare.jsonl, labeled.jsonl,
  corrections_detail.jsonl}` — none overwrite any prior file.
- Test suite: 139 passed / 0 failed, both immediately before and after this run.
  `git status` confirms zero committed files touched by this run.

---

## 1. Cases and claims evaluated

| | value |
|---|---|
| Cases | 50 (all new — never generated in this project before) |
| Claims extracted (shared generation) | **251** |
| Claims with matched evidence | **168 (66.9%)** |
| Claims NO_EVIDENCE | 83 (33.1%) |
| Runtime | 1872.6s total (1207.1s generation, ~13.3s/case avg; remainder verification+correction) |
| Peak VRAM | 7,567 MiB |

**Evidence coverage (66.9%) is the highest ever measured on natural data in this
project** — up from 61.3% (n=30, current parser) and 58.2% (pooled n=30+targeted n=11,
current parser) in the immediately preceding phase, and far above the original 43.2–44.4%
stale-parser figures. This is the deterministic evidence-gated selection working exactly
as designed: every one of these 50 cases was screened, pre-generation, to have real
citation-evidence overlap.

---

## 2. Bare vs labeled — full comparison

| metric | bare | labeled |
|---|---:|---:|
| ENTAILED | 0 | **5** |
| CONTRADICTED | **1** | **2** |
| NOT_ENOUGH_INFORMATION | 167 | 161 |
| NO_EVIDENCE | 83 | 83 |
| correction triggers | **5** | **16** |
| correction attempts | 5 | 16 |
| **corrections shipped** | **0** | **0** |
| correction_failed | 5 | 10 |
| correction_scope_violation | 0 | 6 |
| unsafe corrections shipped | **0** | **0** |
| unflagged-claim preservation | 45/45 (100%) | 83/107 (77.6%) |

**Exact bare vs labeled differences:**
- **6 verdict flips** (bare→labeled), detailed in §4 — the largest flip count on natural
  data in this project's history (previous max: 3–4).
- **Bare framing triggered correction for the first time ever** in any evaluation this
  project has run (5 triggers: 4 low-confidence NEI + 1 genuine CONTRADICTED). Every
  prior natural report recorded exactly 0 bare triggers, always. This pool's
  denser, longer, more citation-rich sentences (a direct consequence of the
  diversity-first selection favoring multi-citation cases) are evidently enough to push
  some bare-premise verifications past the threshold on their own, without any provision
  label.
- Labeled still triggers far more (16 vs 5) and produces more genuine content-level
  matches (§4).
- **0% corrections shipped in BOTH arms** — a new low-water mark for labeled framing
  specifically (previous best: 1/4 shipped, 25%, in the prior phase's smaller run). See
  §5 for why — this is not simply "no substantive attempts."

---

## 3. Two genuine CONTRADICTED verdicts — the first ever on natural data

Every prior natural evaluation in this project (n=11, n=30, pooled n=41, this project's
entire history until now) recorded **zero** CONTRADICTED verdicts. This run found two,
both inspected in full:

**`2019_544`/c8 (CONTRADICTED in BOTH arms, 0.928 bare / 0.773 labeled).** A dense,
7-citation bundled sentence including *"Section 506(II) of the IPC, which addresses
criminal intent; Section 504 of the IPC, which deals with criminal force to deter public
servant from discharging his duty..."* This claim record matches evidence for **Section
506** (criminal intimidation punishment). Two real problems compound here: (a) the whole
251-word sentence is verified as one hypothesis against just Section 506's narrow
punishment text — the same claim-bundling imprecision flagged in the prior phase's
`assertion_text` work — and (b) **Section 504 IPC is misdescribed**: "criminal force to
deter a public servant" is actually Section 353 IPC, not Section 504 (which is
intentional insult to provoke a breach of peace). The CONTRADICTED verdict is a real
signal of something wrong in this sentence, but is not a clean per-citation catch — it is
the bundled-sentence imprecision problem manifesting as CONTRADICTED instead of NEI for
the first time observed.

**`1991_110`/c2 (NEI 0.998 under bare → CONTRADICTED 0.800 under labeled).** *"...sections
302, 149, 323, and 34 of the Indian Penal Code, 1860, which respectively deal with
murder, **criminal conspiracy**, voluntarily causing hurt, and abetting..."* This claim
record matches **Section 149** evidence (vicarious liability for unlawful-assembly
offences) — **Section 149 IPC is not criminal conspiracy** (that is Section 120B). This
is a clean, checkable, genuine mislabeling error, and it is exactly the kind of catch the
labeled-framing hypothesis predicts: **bare framing scored this 0.998-confidence NEI —
it had no way to know the hypothesis was specifically about Section 149 — while labeled
framing's provision label made the mismatch explicit and pushed the verdict to
CONTRADICTED.** This is the cleanest, most legitimate labeled-framing precision win
this project has produced on natural data.

**No false-positive contradiction is evident in either case** — both matched evidence
records are the ones the model's own citation actually names, and both descriptions in
the generated text are checkably wrong relative to that evidence (an over-broad
mischaracterization in one case, a flatly incorrect topic label in the other).

---

## 4. All 6 verdict flips, classified

| claim | evidence | bare → labeled | quality |
|---|---|---|---|
| `1991_110`/c2 | Section 149 IPC | NEI → **CONTRADICTED** | **Genuine, content-driven** (§3) |
| `1982_49`/c1 | Section 25F, Industrial Disputes Act | NEI → ENTAILED (0.973) | **Genuine, content-bearing** — states an actual, specific, checkable requirement of §25F (continuous-service retrenchment protection), verified against real evidence |
| `2000_584`/c3 | Section 302 IPC | NEI → ENTAILED (0.805) | **Genuine, content-bearing** — near-verbatim restatement of the punishment provision |
| `2000_584`/c4 | Section 34 IPC | NEI → ENTAILED (0.907) | **Genuine, content-bearing** — accurate paraphrase of common-intention liability |
| `2002_587`/c6 | Section 34 IPC | NEI → ENTAILED (0.979) | Shallow — bundled listing sentence, same pattern flagged in every prior report |
| `2008_131`/c3 | Section 324 IPC | NEI → ENTAILED (0.960) | Shallow — bundled listing sentence |

**4 of 6 flips (67%) are genuine, content-bearing verification improvements** — a
materially better mix than every prior natural evaluation in this project, where flips
were exclusively the shallow "lists sections X, Y, Z" pattern. This is the first natural
evidence that labeled framing's benefit is not *only* a shallow-listing artifact.

---

## 5. Every triggered correction, inspected (21 attempts, both arms)

Full classification (21 attempts total: 5 bare, 16 labeled):

| Pattern | Count | What happened |
|---|---:|---|
| **Byte-identical no-op** | **15** | Qwen returned the flagged sentence completely unchanged; correctly `correction_failed` on re-verification of the SAME (unimproved) sentence |
| **Genuine edit → correctly caught as scope violation** | **6** (labeled only) | Qwen edited real content but the edit altered text another claim record also depends on verbatim (the same claim-bundling structural cause diagnosed in the prior phase) |
| **Genuine edit → correction_failed on the RIGHT sentence** | **1** (`2007_1002`/c4, labeled) | Novel failure mode: Qwen *appended a whole new correct sentence* (the literal Section 149 evidence text) to the end of the paragraph instead of rewriting the flagged sentence in place — the flagged sentence itself was untouched, so re-verification correctly still returned NEI (0.575) on it |

**Of the 6 scope-violation cases, at least 4 involved edits that were substantively
meaningful, not cosmetic:**
- `2009_431`/c2: Qwen corrected **"Sections 300" → "Sections 302"** — Section 300 IPC is
  the murder *definition*, Section 302 is the murder *punishment* provision actually
  matched in evidence; this is a genuine citation-number fix.
- `2003_924`/c5: Qwen removed an incorrect **"Section 3 of... CrPC"** reference from a
  citation list, leaving only the correct "Section 482 CrPC."
- `2020_51`/c4: Qwen removed an entire clause describing Section 406/420 IPC with their
  labels **swapped** (406 is criminal breach of trust, 420 is cheating — the original
  text had them backwards).
- `2009_865`/c2: Qwen simplified an awkward "read with"/"criminal negligence" phrasing
  toward the evidence's actual wording.

Two were more cosmetic (`1991_110`/c2's edit removed "non-cognizable" without touching
the actual Section 149 mislabeling that caused the trigger; `1978_196`/c4 was a
parenthesis-spacing fix). **The safety gate rejected all 6 correctly and safely** — no
argument is made here that any of these 6 should have shipped as-is (several still leave
real errors uncorrected, or touch other claims' text) — but 4/6 demonstrate the corrector
attempting real, valid content fixes that the current one-sentence-per-citation claim
representation structurally cannot let through. This is now the second consecutive
experiment (after the prior phase's 2 scope violations) where this exact mechanism
blocks legitimate correction content, reinforcing that the `assertion_text` /
claim-granularity work from the prior phase targets a real, recurring problem, not a
one-off.

---

## 6. Safety

- **0/21 unsafe corrections shipped**, both arms. Structurally guaranteed
  (`status="corrected"` iff re-verification == ENTAILED) and empirically confirmed again.
- **0/21 corrections shipped at all** — the safety gate has nothing to be unsafe about
  this round; every attempt was rejected (no-op failure, right-sentence failure, or
  correctly-caught scope violation).
- **Unflagged-claim preservation: 45/45 (100%) bare, 83/107 (77.6%) labeled.** Lower than
  the prior phase's 87.5–100% because this batch's genuinely denser, more
  heavily-bundled sentences (by design — the selection favors high citation-diversity
  cases) create more opportunities for one edit to collide with another claim's text.
  Every collision was correctly caught (§5) — the lower raw percentage reflects more
  genuine editing attempts on harder sentences, not a safety-gate weakening.
- No threshold changed, no safety-gate code touched, config default remains `bare`.

---

## 7. Comparison against established baselines

| | synthetic GPU (59 cases, established) | natural, prior phase (41 doc-runs, reparsed) | **natural, this experiment (50 cases)** |
|---|---|---|---|
| Evidence coverage | n/a (synthetic, always paired) | 58.2% | **66.9%** |
| CONTRADICTED ever observed (natural) | n/a | 0 (both arms) | **1 bare, 2 labeled** |
| Correction triggers, bare | 30 | 0 | **5** |
| Correction triggers, labeled | 36 | 4 | **16** |
| Corrections shipped, bare | 0/30 (0%) | 0/0 | **0/5 (0%)** |
| Corrections shipped, labeled | 26/36 (**72.2%**) | 1/4 (25%) | **0/16 (0%)** |
| Scope violations, labeled | 0 | 2 | **6** |
| Unsafe shipped | 0 (both) | 0 (both) | **0 (both)** |

**The synthetic 72.2% correction-success figure continues not to transfer to natural
data — and this larger, more deliberately evidence-rich batch produced the WORST
natural correction-success rate yet measured (0%), not the best.** This is an important,
non-obvious result: a bigger, better-curated pool of evidence-backed cases did not
translate into more successful corrections — it translated into **more correction
opportunities being created** (16 vs 4 triggers) **and more of those opportunities being
correctly rejected for structural reasons** (6 scope violations vs 2), because
denser, longer, more citation-rich sentences are exactly the shape that collides with the
one-claim-per-citation-shares-a-sentence design. The corpus-coverage fix from the prior
phase and the case-selection method from this phase both worked exactly as intended
(more evidence, more genuine triggers, more genuine edit attempts) — but they also
mechanically increased exposure to the claim-granularity bottleneck.

---

## 8. Does this experiment provide meaningful evidence for or against labeled framing?

**Meaningful evidence — mixed, and more informative than any prior natural run, but
still not sufficient to promote.**

**For labeled framing:**
- The clearest, most legitimate precision win yet: a real mislabeling error
  (`1991_110`/c2, Section 149 called "criminal conspiracy") that bare framing missed at
  0.998 confidence and labeled framing correctly flagged CONTRADICTED.
- 4/6 verdict flips this round are genuine content-bearing improvements, not shallow
  listing artifacts — a qualitatively better result than every prior natural report.
- Labeled framing reaches 3x more correction opportunities (16 vs 5) with zero unsafe
  shipments, and several of its blocked corrections were substantively valid fixes
  (§5) — a positive signal about what the corrector *would* ship if the claim-scope
  constraint were relaxed at the right granularity.

**Against (or at least, not yet supporting promotion):**
- **0% shipped in either arm this round.** The correction PATH's demonstrated real-world
  yield on this batch is zero, for both framings — the one prior natural success (1/4 in
  the smaller prior run) did not repeat here.
- Bare framing triggering for the first time (including via a real, if imprecise,
  CONTRADICTED catch) complicates the "labeled framing is what unlocks correction on
  natural data" narrative — bare framing is not structurally inert on richer input.
- The dominant new failure mode (6 scope violations, several on substantively valid
  edits) is not a framing question at all — it is the claim-granularity bottleneck,
  and it now costs MORE potentially-valid corrections as the pool gets richer, not fewer.

**Conclusion: the hypothesis remains INCONCLUSIVE**, now on a considerably larger and
more informative evidence base (50 genuinely new cases, 21 real correction attempts, the
first-ever natural CONTRADICTED verdicts) than any previous phase, but the central,
recurring blocker — claim-level granularity, not premise framing — is now more clearly
the dominant lever for correction yield than the bare-vs-labeled choice itself.

---

## 9. Production default

**Not changed.** `config/prototype.yaml` remains `premise_framing: bare`. No threshold
was changed. No safety-gate code was modified. This experiment's evidence, if anything,
sharpens the case that the next highest-leverage change is claim granularity (already
prototyped, not yet wired to production, in the prior phase's `assertion_text` work),
not the framing default.

---

## 10. Next step suggested by this data (not executed here, per instruction)

Re-run this exact 50-case batch's 6 labeled scope-violation attempts using the
`assertion_text` claim representation (prior phase) instead of the shared, bundled
`claim_text`, to test directly whether claim-level atomicity converts any of the 4
substantively-valid-but-blocked edits (§5) into a shippable, safe correction. This is the
same recommendation the prior phase made, now backed by 6 concrete real cases instead of
2.
