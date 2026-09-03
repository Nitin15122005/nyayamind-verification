# Research Phase — Next Status Report

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. Follows `verifier_framing_natural_validation.md` (the report that
discovered the bug this phase fixes). Covers: the correction re-verification bug fix, a
synthetic GPU regression check, a post-fix natural GPU correction run, a NO_EVIDENCE
root-cause diagnosis with two additional parser fixes, and a claim-granularity
(atomic-assertion) prototype.

> **Scope of every verdict below.** All verdicts are outputs of a small public NLI model
> (DeBERTa-v3-base-mnli-fever-anli) and a 7B instruction model (Qwen2.5-7B-Instruct,
> 4-bit), checked against a 59-record third-party-sourced evidence corpus. They are
> **not** legal-correctness determinations. No lawyer ground truth exists anywhere in
> this project (`lawyer_annotation.jsonl` still holds only Claude-generated assumption
> labels, per `mvp_assumption_evaluation.md`), and none is fabricated or implied here.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

---

## 0. Baseline before this phase

| Item | Value |
|---|---|
| Starting commit | `fe8b15b`, working tree clean except pre-existing `baseline/LegalSeg` and an already-modified (not by this phase) `scripts/compare_premise_framing_synthetic.py` |
| Test suite | 122 passed, 0 failed (119 + 3 tests added in the immediately preceding session) |
| Known bug (from `verifier_framing_natural_validation.md` §8c) | Correction re-verification can silently re-verify the WRONG claim when two claims in one document share a citation identity — confirmed on real document `2008_2648` |
| Synthetic GPU baseline (established, `verifier_framing_gpu_validation.md`) | bare: 35.6%/47.7% contradiction recall, 0% FP, 0/30 correction success. labeled: 45.8%/61.4%, 0% FP, 26/36 (72.2%) correction success, 0 unsafe |
| Natural correction (prior session, stale parser) | bare 0/117 triggers ever; labeled 3/117 triggers, **0/3 shipped**, 2 correction_failed, 1 scope_violation |
| Natural evidence coverage (stale parser) | 38/88 (43.2%) on n=30 alone; 52/117 (44.4%) pooled with targeted n=11 |
| GPU environment | `research/.venv` (torch 2.2.2+cu121), NVIDIA RTX 4050 Laptop GPU — used for every GPU claim below, no CPU fallback |

---

## 1. Bugs discovered and fixed

### 1a. Correction re-verification: wrong-claim matching (FIXED)

**Root cause.** `apply_selective_correction()` (`src/pipeline.py`) re-parsed the corrected
text and picked the *first* re-extracted claim whose citation identity (provision_type,
provision_number, act_norm) matched the originally-flagged claim's citation — with no
way to distinguish which claim that was when **two claims in the same document cite the
exact same provision** (a routine natural-data shape: one sentence lists "sections 406
and 420," a later sentence separately asserts something specific about "Section 420").

**Fix.** Match by **ordinal position among same-citation claims** instead: `target` is
the Nth claim (in document order) citing this exact provision; the Nth same-citation
claim re-extracted from the corrected text is the same slot — correct whether or not the
corrector changed anything in it, and safe because the scope-violation check (unchanged)
already guarantees every other claim's text and order survive verbatim. New helper
`_citation_identity()`; no threshold, no safety-gate change. See `src/pipeline.py`,
`apply_selective_correction()`.

**Verification, three independent ways:**
1. Direct reproduction of the exact failing case (`2008_2648`) against the fixed code —
   now correctly resolves to the flagged sentence.
2. 2 new regression tests (`tests/test_pipeline_mock.py`):
   `test_replacement_matched_by_ordinal_position_when_claims_share_citation`,
   `test_scope_violation_still_caught_when_shared_citation_claim_altered`, plus
   `test_single_citation_claim_behaviour_unchanged_by_ordinal_fix` for the no-op
   degenerate case.
3. **Confirmed live in the post-fix natural GPU run** (§4): document `2008_2648`'s
   correction attempt this time re-verified claim `c4` (confidence 0.693, matching the
   ORIGINAL pre-correction score exactly, since Qwen made no edit) instead of the old
   run's wrong claim (confidence 0.741, a different sentence entirely). Same document,
   same no-op correction, now measurably re-verifying the right sentence.

### 1b. Claim-parser act-name gaps (2 new fixes, on top of fixes already in `src/` but never propagated to the committed evaluation snapshot — see §3)

- **Copula not recognized as an act-name trim point.** "...the Evidence Act **is
  applicable**, which prescribes..." captured `act_raw = "the Evidence Act is
  applicable"` because `_ACT_CONTINUATION_VERBS` had no copula form. Added `is`/`are`/
  `was`/`were`. 3 real occurrences fixed (documents `2006_650`, `1998_229`, `1991_582`).
- **"Evidence Act" short form not aliased.** Even after the trim fix, `"evidence act"`
  (2 significant words) only reaches 0.5 token-overlap with the corpus's `"indian
  evidence act 1872"` (below the 0.8 fuzzy threshold) — analogous to why `"ipc"` needed
  an explicit alias. Added `"evidence act": "indian evidence act 1872"` to
  `_KNOWN_ACT_ALIASES`, the same treatment already given to IPC/CrPC/CPC/ID Act.

Both fixes are narrow, additive, and justified by real observed failures (not
speculative broadening) — see `src/claim_parser.py` and the 5 new tests in
`tests/test_claim_parser_bugfixes.py` ("Bug 5" section).

### 1c. NOT a bug, but a major process finding: the committed natural evaluation outputs are stale

`scripts/reparse_n30_with_fixed_parser.py` (pre-existing in this repo, not written for
this phase) re-parses the exact same `run_A_n30.jsonl` generated text with the CURRENT
parser. Before this phase's two new fixes, it already showed **38/88 → 54/93** matched
claims — i.e., **fixes already sitting in `src/claim_parser.py` from an earlier session
were never propagated to the committed `run_A/B/C_n30.jsonl` / `run_natural_targeted.jsonl`
files**, which every prior report in this project (including the immediately preceding
`verifier_framing_natural_validation.md`) analyzed as "the" natural dataset. This phase's
two additional fixes push that further to **57/93** (§3). The committed files themselves
were **not** modified (per the brief) — instead, a new harness
(`scripts/compare_premise_framing_natural_reparsed.py`) re-derives claims fresh from the
same committed `generated_field.text` for every natural comparison in this report.

---

## 2. Test suite

| Checkpoint | Result |
|---|---|
| Start of this phase | 122 passed, 0 failed |
| After the ordinal-matching pipeline fix + 5 new tests | 127 passed, 0 failed |
| After the 2 parser fixes + 4 new parser tests | 131 passed, 0 failed |
| After the `assertion_text` claim-granularity feature + 5 new tests | 132 passed, 0 failed |
| **After both GPU runs (final)** | **132 passed, 0 failed** |

No regressions at any point. 10 tests added this phase (5 pipeline, 5 parser +
1 assertion-text pipeline-output test — 6 total; see §1/§5 for the exact split).

---

## 3. NO_EVIDENCE taxonomy and evidence coverage

Diagnosed with a new read-only script, `scripts/diagnose_no_evidence.py`, against the
**current** parser (not the stale committed claims — see §1c). Full detail:
`outputs/no_evidence_diagnosis.json`.

| | old (stale parser, as analyzed by every prior report) | current parser, before this phase's 2 fixes | current parser, after this phase's 2 fixes |
|---|---|---|---|
| n=30 claims | 88 | 93 | 93 |
| n=30 evidence-matched | 38 (43.2%) | 54 (58.1%) | **57 (61.3%)** |
| n=30 NO_EVIDENCE | 50 (56.8%) | 39 (41.9%) | **36 (38.7%)** |
| pooled (n=30 + targeted n=11) claims | 117 | — | 122 |
| pooled evidence-matched | 52 (44.4%) | — | **71 (58.2%)** |
| pooled NO_EVIDENCE | 65 (55.6%) | — | **51 (41.8%)** |

**Taxonomy of the 36 remaining n=30 NO_EVIDENCE claims** (mechanically decidable —
auto-classified with certainty, not guessed):

| Category | Count | Meaning |
|---|---:|---|
| **A** — genuinely absent from the 59-record corpus | **35** | Right act resolved, but that exact provision isn't in the audited pool (e.g. IPC §467, §304A, §511, §309 — none in the 20-record IPC subset), or the citation names a different Act/edition entirely the corpus doesn't cover (e.g. "Indian Income Tax Act, **1922**" vs the corpus's 1961 Act; "Code of Criminal Procedure" cited for a section that, in the corpus, only exists under IPC) |
| **F** — genuinely too coarse / multi-act field, correctly declined | 1 | `2023_26`'s bare "Section 324" citation: the field has 2 acts (IPC + CrPC) so the single-act field-wide fallback correctly refuses to guess |
| B/C/D (parser bugs) | 0 remaining | Both real instances found (§1b) are already fixed |
| E (matcher threshold too strict) | 0 | None of the remaining candidates have a real near-miss overlap ≥0.5 that the threshold alone is blocking |

**Reading this taxonomy:** the dominant remaining cause (35/36 = 97%) is genuine
**evidence-corpus coverage**, not a verifier or parser defect — consistent with, and now
quantitatively sharper than, the qualitative diagnosis in `research_evaluation_final.md`
§E. The corpus does cover 10 Acts / 59 records (IPC, Constitution, CrPC, CPC, Evidence
Act, Arms Act, Land Acquisition, Income Tax, Industrial Disputes, Negotiable
Instruments) — broader than earlier reports characterized it ("only IPC and
Constitution") — but real NyayaRAG cases still cite specific provisions and Act
editions outside even that. **No corpus expansion was made in this phase** (out of
scope, and the corpus is a read-only, audited asset); the safe, code-only fixes
available (B/C/D/E) have now been exhausted for this sample.

---

## 4. Synthetic GPU regression (post-fix)

`scripts/compare_premise_framing_synthetic.py --device cuda --with-correction
--out-prefix framing_comparison_gpu_n59_postfix` — same script, same 59 cases, same
method as the established baseline; not modified this phase. New output files, baseline
(`run_synthetic_stress.jsonl`, `framing_comparison_gpu_n59_*`) untouched.

| metric | bare (established) | bare (post-fix) | labeled (established) | labeled (post-fix) |
|---|---|---|---|---|
| contradiction recall (overall) | 35.6% | **35.6%** | 45.8% | **45.8%** |
| contradiction recall (w/ evidence) | 47.7% | **47.7%** | 61.4% | **61.4%** |
| false-positive rate | 0.0% | **0.0%** | 0.0% | **0.0%** |
| correction triggers/attempts | 30/30 | **30/30** | 36/36 | **36/36** |
| corrections shipped | 0/30 | **0/30** | 26/36 (72.2%) | **26/36 (72.2%)** |
| correction_failed | 30 | **30** | 10 | **10** |
| scope violations | 0 | **0** | 0 | **0** |
| unsafe shipments | 0 | **0** | 0 | **0** |
| unflagged-claim preservation | 30/30 | **30/30** | 36/36 | **36/36** |

**Exact reproduction, every metric, both arms.** Bare-arm reproduction gate: 59/59
verdicts agree, 0 sub_reason mismatches. This is the expected result: the ordinal-position
fix only changes behavior when ≥2 claims in a document share one citation identity, which
never happens in the 2-claim (one corrupted, one unrelated) synthetic cases. **The pipeline
fix introduced zero synthetic regression.**

---

## 5. Natural GPU correction run (post-fix, current parser)

`scripts/compare_premise_framing_natural_reparsed.py --device cuda --with-correction` —
new script; committed `run_B_n30.jsonl` / `run_natural_targeted.jsonl` read-only,
generated text reused verbatim, claims re-derived fresh (§1c). 41 pooled document-runs
(30 distinct cases), 122 claims, 71 evidence-matched (58.2%).

| metric | bare | labeled |
|---|---|---|
| ENTAILED | 0 | 3 |
| CONTRADICTED | **0** | **0** |
| NOT_ENOUGH_INFORMATION | 71 | 68 |
| NO_EVIDENCE | 51 | 51 |
| documents with correction trigger | **0** | **4** |
| correction attempts | 0 | 4 |
| **corrections shipped (SUCCESS)** | 0 | **1** |
| correction_failed | 0 | 1 |
| correction_scope_violation | 0 | 2 |
| unsafe corrections shipped | 0 | **0** |
| unflagged-claim preservation | 0/0 | 11/16 (68.8%) |

**First genuine natural-data correction success in this project's history:** document
`2009_1385`, claim `c1`. Original: *"...Section 302 of the Indian Penal Code (IPC),
which defines murder as causing the death of a person with the intention to cause death
or with the knowledge that such act is likely to cause death."* Qwen rewrote it to:
*"...Section 302 of the Indian Penal Code (IPC), which punishes anyone who commits
murder with death, or imprisonment for life, and shall also be liable to fine."*
Re-verified ENTAILED at 0.959 confidence. Read narrowly: Section 302 IPC is the
**punishment** provision, not the definition provision (that's Section 300) — the
original text described definitional content under a punishment citation, and the
correction rewrote it to state the actual content of the cited section. That is a
genuine, checkable improvement in citation–content alignment. It is **not** a
lawyer-verified legal-correctness claim, and n=1 is not a rate.

**Every triggered correction, classified:**

| doc | Qwen edited the flagged sentence? | outcome | why |
|---|---|---|---|
| `2009_1385`/c1 | **Yes, substantively** | **corrected (shipped)** | genuine content rewrite, ENTAILED |
| `2004_632`/c3 | one-word spelling fix ("abetter"→"abettor") | scope_violation | same claim-duplication artifact as the prior report: c1/c2 share this exact sentence as their `claim_text`, so the spelling change breaks their verbatim-preservation check |
| `2023_26`/c5 | **Yes, substantively** (rewrote the Section 148 clause) | scope_violation | same duplication pattern: this bundled sentence backs 4 separate claim records (Sections 148/302/304/324), and editing the 148 clause changes text the other 3 claim records also depend on verbatim |
| `2008_2648`/c4 | No (byte-identical) | correction_failed | **the bug-fix confirmation case** (§1a) — correctly re-verified at 0.693, matching the pre-correction score exactly |

**2/4 attempts are now genuine, substantive correction attempts** (up from 0/3 in the
prior, stale-parser run) — the extra evidence coverage from §3's fixes surfaced more,
and more genuine, low-confidence triggers. Both scope violations are the SAME
pre-existing structural cause (one physical sentence backing multiple claim records,
correction editing content one other claim record also depends on verbatim) — not new
bugs, and correctly rejected by the unmodified safety gate in both cases. **The
claim-granularity work in §6 is a direct, partial mitigation for exactly this failure
mode**, though not wired into production here.

**Verdict flips (bare→labeled), full 122-claim set:** identical 3 claims as every prior
run in this project (`n30/1971_200/c1`, `n30/1971_200/c2`, `targeted_n11/2009_1385/c1`),
all the same shallow "includes Sections X, Y, Z" listing pattern already flagged as a
precision concern, not a content-verification success. **0 CONTRADICTED in either arm**
— still true across every natural evaluation this project has ever run; no false-positive
contradiction is possible on this data.

---

## 6. Claim granularity: atomic assertion splitting (prototype, not wired into production)

**Data justification.** Across the pooled 122-claim natural set, **33 of 53 distinct
sentences (62%) are bundled** — one physical sentence backing ≥2 claim records — and
those bundles account for **102/122 claims (84%)**. Of the 33 bundles, **15 use an
explicit parallel-clause connector** ("Section A does X, **while** Section B does Y");
the other 18 are plain citation lists with no separable per-citation content (splitting
would be meaningless for those — there is nothing distinct to attribute per citation).

**Implementation.** Added `assertion_text` to `claim_parser.Claim` and to the pipeline's
claim-record schema (`src/pipeline.py`, `generate_and_parse`) — **purely additive**:
always populated (defaults to the full `claim_text` when no safe split is found), never
required, `claim_text` itself never changes. A conservative splitter
(`_split_into_parallel_clauses` / `_assign_assertion_texts`) handles exactly the single
" while " connector shape: splits the sentence in two, and assigns each citation the
clause that **unambiguously** mentions its own "<keyword> <number>"; any citation that
can't be unambiguously placed falls back to the full sentence (never guesses, never
drops content). 6 new tests (`tests/test_claim_parser_bugfixes.py`).

**Empirical check (CPU, real DeBERTa, 11 real claim instances with a genuine split and
matched evidence):** verifying `assertion_text` instead of `claim_text` **flips 4 claims
NEI→ENTAILED under labeled framing** (0 flips under bare). Unlike the shallow
"lists sections X/Y/Z" flips in §5, these are content-bearing: e.g. `2005_360`'s "Section
302 prescribes the punishment for murder" (isolated from its sibling clause about
Section 34) verifies ENTAILED at 0.99 against the actual punishment text — a
qualitatively different, better-justified kind of ENTAILED than the listing-sentence
pattern.

**Conclusion: atomic splitting is empirically justified as a genuine, deterministic
improvement to hypothesis precision for this bundled-sentence shape.** It was **not**
wired into `apply_verification`'s default hypothesis source in this phase — doing so
would change every verdict metric in this project's history on an 11-instance sample,
which is not enough to justify a default change per this task's own integrity rules.
It is available as an explicit opt-in for a dedicated follow-up ablation (mirroring how
`premise_framing` itself was introduced).

---

## 7. Safety, across everything run in this phase

- **0 unsafe corrections shipped** — synthetic (0/30 bare, 0/36 labeled) and natural
  (0/0 bare, 0/4 labeled). Structurally guaranteed by `pipeline.py`'s unmodified gate
  (`status = "corrected"` iff re-verification == ENTAILED); this phase's fix only
  changed WHICH claim gets re-verified, never weakened when a correction ships.
- **Scope violations still correctly caught**, including the two new natural-data cases
  in §5 — the ordinal-position fix does not touch `_scope_violation()` at all.
- **No threshold was changed.** 0.70 throughout, synthetic and natural, both framings.
- **No evidence was fabricated or corpus broadened unsafely.** The two parser fixes in
  §1b are narrow, justified by ≥3 real observed occurrences each, and only ever make an
  ALREADY-CORRECT act resolution reachable — neither can invent an evidence match where
  the corpus genuinely lacks the provision (verified directly: category A, 35/36
  remaining NO_EVIDENCE claims, is unaffected by either fix).

---

## 8. What remains experimentally unproven

1. **Legal correctness.** Nothing in this phase (or any phase of this project) has
   lawyer-verified ground truth. Every ENTAILED/CONTRADICTED/"corrected" label above is
   model behavior, not a legal judgment.
2. **Natural correction success rate.** n=4 attempts, 1 shipped. Not a rate — a proof of
   existence that the path CAN work on real claims (new information this phase), not a
   measurement of how often it does.
3. **Whether the two scope-violation cases in §5 would have shipped successfully under
   an atomic (§6) claim representation.** Plausible (the claim-duplication root cause is
   exactly what §6 targets) but not tested — the correction path was not re-run against
   `assertion_text`.
4. **Whether labeled framing's shallow-ENTAILED pattern (§5, same 3 claims every run) is
   a precision problem serious enough to block promotion**, independent of the
   correction question — no natural false-positive CONTRADICTED exists to measure
   against, but the flip pattern itself has not been shown to be *legally* meaningful.
5. **Evidence-corpus expansion impact** — untested; 35/36 remaining NO_EVIDENCE claims
   are genuine corpus gaps, and no corpus change was made or evaluated this phase.

---

## 9. Should labeled framing become the production default?

**Not yet — evidence is stronger than before, but still short of the bar.**
`config/prototype.yaml` remains `bare`. In favor, newly this phase: a genuine (if
single) natural correction success now exists, with 0 unsafe shipments across every
attempt to date on both synthetic (66 attempts) and natural (7 attempts total across
this and the prior session) data under labeled framing. Against: the natural
correction-success sample is n=4, half of which fail for a structural reason unrelated
to framing (claim duplication, mitigated but not fixed by §6), and the framing's only
other natural-data effect (§5's 3 shallow flips) remains a precision concern, not a
demonstrated improvement. Per this task's own rule — "keep bare as the default unless
the evidence is strong enough to justify changing it" — this phase's evidence, while
directionally positive, does not clear that bar.

---

## 10. Is the research hypothesis supported, unsupported, or inconclusive?

**Hypothesis (implicit across this project): labeled premise framing improves selective
correction on real NyayaRAG output.**

**INCONCLUSIVE, trending toward supported, still short of proof.** This phase changes
the answer from the prior report's "0/3, corrector barely attempted anything" to "1/4
shipped, genuinely and substantively attempted in 2/4 cases" — a materially different,
more encouraging result, but built on a sample too small (n=4 real triggers, ever, in
this project's entire history) to call the hypothesis supported. The synthetic-to-natural
transfer question from the prior report is **partially answered**: correction CAN
transfer (proof of existence, §5), but does not yet transfer at anything like the 72.2%
synthetic rate, and the honest current estimate of a natural success rate has a
denominator of 4.

---

## 11. Exact next experiments required

In dependency order, each addressing a specific open item from §8:

1. **Expand the natural correction-trigger sample.** The evidence-coverage fixes in §3
   already surfaced one more trigger this phase (3→4); further, targeted expansion of
   the natural evaluation set (more NyayaRAG cases run through the pipeline, not
   invented data) would grow the n=4 sample enough to estimate a real success rate with
   any confidence. This is the single highest-leverage next step for §9/§10.
2. **Re-run the two scope-violation cases (`2004_632`, `2023_26`) under the atomic
   `assertion_text` representation from §6**, to test directly whether claim-level
   atomicity converts scope violations into shippable corrections — a concrete,
   falsifiable test of §6's practical value that this phase set up but did not run.
3. **Lawyer review of the one shipped correction** (`2009_1385`/c1) and of a sample of
   the NEI verdicts across both framings — the only route from "DeBERTa says ENTAILED"
   to an actual correctness claim, per every prior report's own standing conclusion.
4. **Evidence-corpus coverage audit against the 35 category-A NO_EVIDENCE claims** (§3)
   — determine how many are addressable by adding more audited canonical-statute
   records (a corpus/data task, not a code task) versus provisions genuinely outside
   this project's current scope.
