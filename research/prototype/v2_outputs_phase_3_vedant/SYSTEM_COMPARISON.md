# SYSTEM COMPARISON — ORIGINAL NyayaMind vs LATEST NyayaMind

**V2 package · generated 2026-09-18 · repository `nyayamind-verification` · HEAD `fb4e98f`**

This document answers, in order: what exactly the original system was, what was wrong with it,
what was changed, what the latest system is, what was measured, what actually improved, and what
did not.

Everything here is traceable to a source artifact. Where the repository's own documentation
disagrees with its code, **the code wins** and the disagreement is recorded rather than smoothed
over.

---

## 0. The first thing a reader must understand: "ORIGINAL" has two meanings

This is not a quibble. Getting it wrong makes numbers non-comparable, and the repository itself
contains documents that quote both meanings without distinguishing them.

| | **O-CODE** | **O-CFG** ("NyayaMind v0") |
|---|---|---|
| What it is | The original historical **codebase** | A **configuration baseline**: HEAD code with five levers at their un-evidenced defaults |
| Commit | `0e37525` (2026-08-13, sole root commit) | `fb4e98f` (HEAD) with levers flipped |
| Parser | `claim_parser.py` @ 17,150 bytes | `claim_parser.py` @ 56,697 bytes (the HEAD parser) |
| Evidence pool | 59 usable records | 59 usable records |
| Is it a real historical system? | **Yes** — it ran, and its outputs are committed | **No** — see below |
| How many experiments measure it? | **Exactly one** (the claim-parser comparison) | **Essentially all the others** |

### O-CFG is a retrospective construct, not a historical snapshot

The five levers **never coexisted at their defaults in any real production state**.
`premise_framing` first appears at `fe8b15b` (2026-08-26); `narrow_primary_hypothesis` at
`bb2cd93` (2026-09-09) — two weeks later. O-CFG is a legitimate and useful **ablation arm**. It
is **not** a snapshot of the system as it was on any date.

Two further facts make the "flip five levers to reproduce the old system" framing inaccurate at
HEAD, and both are recorded as open discrepancies:

- **C-1.** `config/prototype.yaml` claims four separate times that setting these levers false
  "exactly reproduces every evaluation output committed before 2026-08-27". **This is false at
  HEAD.** The negation gate, year-conflict veto, unauthorized-citation guard and ordinal-integrity
  guard all landed at `adf54aa` (2026-09-09) and **none of them is config-controllable**. Running
  HEAD with all five levers at defaults runs a *strictly more gated* system than anything that
  existed before 2026-09-09. The year-conflict veto in particular can change *which evidence
  record is retrieved*, hence the premise, hence the verdict.
- **C-2.** Under O-CFG the **sibling-regression gate is silently inactive** (`pipeline.py:947`
  gates it on a truthy `atomic_scope_check`), while four newer gates stay on. So an
  "O-CFG vs production" comparison is not a clean single-variable comparison for
  `atomic_scope_check` either.

**This package therefore always states which baseline a number belongs to.** Quoting
"the original system's 43.2% evidence coverage" (O-CODE) alongside "ORIGINAL 63.2% coverage"
(O-CFG, the 209-paired arm) as if they were the same system is a category error.

---

## 1. What exactly the ORIGINAL system was

**O-CODE — commit `0e37525`, 2026-08-13, "Initial release: legal claim verification prototype".**
Verified as the sole root commit (`git rev-list --max-parents=0` returns one hash; no tags; no
other refs). It is a **squashed import of an already-mature prototype**, not a first line of
code: its 47-file tree already ships completed 30-case runs and an evaluation report. Anything
earlier is unrecoverable from this repository.

| Component | ORIGINAL behaviour |
|---|---|
| Generation | `Qwen/Qwen2.5-7B-Instruct`, 4-bit NF4, greedy, 200 new tokens, seed 42 |
| Claim parser | One `Claim` per citation; fields **only** `{claim_id, claim_text, citation_extracted}`; `claim_text` is the whole sentence |
| Evidence pool | v0 only — **59 usable** records of 63 (`VERIFIED_EXACT` 25 + `VERIFIED_CONTENT` 34), **10 distinct Acts** |
| Evidence retrieval | exact_normalized → exact ignoring subsection → fuzzy Jaccard ≥ 0.8. **No year-conflict veto** |
| NLI verification | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`; premise = **raw statute text, unlabelled**; hypothesis = **the full claim sentence** |
| Verdict | ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION / NO_EVIDENCE; argmax confidence < 0.70 downgrades to NEI |
| Correction | Whole-paragraph LLM regeneration, same Qwen instance, first flagged claim only, max 1 attempt |
| Re-verification | **Present** — one pass, bare premise, full-sentence hypothesis |
| Safety gates | **Exactly one**: the full-sentence scope check (`pipeline.py:133-153`) |

**O-CODE's own measured behaviour** (`0e37525:outputs/eval_30_report.md`): 30 cases, 88 claims,
**38/88 (43.2%)** resolving to evidence, verdicts {ENTAILED 0, CONTRADICTED 0, NEI 38,
NO_EVIDENCE 50}, **correction trigger rate 0/30**, final field changed **0.0%**.

That last line is the real problem statement for this whole project: *the original system never
actually did anything.* It could not find evidence for 57% of the claims it extracted, it never
returned a single ENTAILED or CONTRADICTED verdict, and it therefore never triggered a
correction.

---

## 2. What was wrong with it

| # | Flaw | Evidence it was real |
|---|---|---|
| 1 | **Premise/hypothesis mismatch.** Generated claims are overwhelmingly *attributed* ("According to Section 302 of the IPC, ..."). A bare premise contains the rule but never names Section 302, so half the hypothesis is genuinely unsupported and a well-behaved NLI model must answer neutral. | 38/38 evidence-matched claims returned NEI at high confidence (mean 0.9889) — the model was being *correct* about a premise stripped of the identifier the claim was about |
| 2 | **Evidence pool too small and too narrow.** 59 records over 10 Acts. | 50/88 claims (57%) resolved to nothing |
| 3 | **Parser could not normalise real citation forms.** No acronym/alias handling (IPC/CrPC/CPC), no `Art./Arts.` abbreviation, no plural or list grammar, run-on multi-Act sentences merged two Acts into one `act_norm` and lost the second citation. | 14/38 matches rested on a fuzzy token-overlap heuristic; 7 claims had an unresolved Act |
| 4 | **Verification hypothesis too wide.** The whole sentence was the hypothesis even when only one clause concerned the cited provision. | Motivated `assertion_text` / `assertion_spans` |
| 5 | **Almost no safety net on correction.** One scope check. Nothing stopped the corrector inventing a citation, reordering same-citation siblings, flipping a negation, or regressing an untouched sibling claim. | Each gate added later has regression tests demonstrating the failure it blocks |
| 6 | **No year-awareness in retrieval.** A claim citing a differently-dated Act could match the wrong record. | Motivated the year-conflict veto |

---

## 3. What exactly the LATEST system is

**HEAD `fb4e98f`, 2026-09-12.** Working tree clean; the audited source *is* HEAD.

The models are **unchanged**: generation and correction are the same `Qwen/Qwen2.5-7B-Instruct`
(one loaded instance reused for both), and verification is the same
`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`.

> **Stated explicitly, because it governs how every number in this package must be read:**
> the underlying model weights are unchanged between ORIGINAL and LATEST. Every measured
> difference is attributable to system, pipeline and configuration changes — **not** to a
> different or better underlying model.

Live configuration: `use_evidence_v1=true` (136-record pool), `premise_framing="labeled"`,
`narrow_primary_hypothesis=true`, `atomic_scope_check="assertion_spans"`,
`narrow_reverification_hypothesis=true`, `confidence_threshold=0.70`,
`assertion_span_primary_hypothesis=false` (experimental), `correction.assertion_aware=false`
(experimental → the **legacy** whole-paragraph correction path is the one that is live).

The premise template is literally `f"{provision_type} {provision_number} of {act}: {evidence_text}"`
(`verifier.py:78`), and the label comes from the **matched evidence record**, never from the
claim's own — possibly wrong — citation. That detail is what keeps the change honest: no legal
content is invented and the statute text is passed through untouched.

Corrected text ships in exactly one circumstance: `status == "corrected"`, which requires passing
every gate **and** re-verifying ENTAILED. Every rejection ships the **original** text with the
reason recorded in `final_field.source`. All gates are **fail-closed**.

---

## 4. Component-by-component comparison

| Component | ORIGINAL | Problem / failure | Modification | LATEST | Evidence |
|---|---|---|---|---|---|
| NLI premise | Raw statute text, unlabelled | Attributed claims structurally cannot be entailed | `premise_framing` bare→labeled; prepend the provision label already on the audited record | `"<Type> <N> of <Act>: <text>"` | GOLD-01 n=420 fresh: macro F1 0.7487→0.9684, acc 0.7333→0.9714, McNemar exact p=1.6e-30 — **but 99% of the gain is in attributed conditions; see §6** |
| Evidence pool | 59 usable, 10 Acts | 57% of claims resolved to nothing | `use_evidence_v1` false→true, merge audited v1 supplement | 136 usable, 22 Acts | Fresh structural recount; historical paired coverage 63.2%→70.3%, McNemar p=0.0003 (n=209) |
| Claim parser | 17 KB; no assertion spans, no acronyms, no `Art./Arts.` | Lost citations, unresolved Acts, fuzzy-dependent matching | Acronym/alias normalisation, `Art./Arts.`, list/plural grammar, act-bleed fix, assertion spans | 57 KB | Fresh 3-arm rerun, n=30 docs: claims resolving to evidence **38→57**, +10/−0 documents, sign test p=0.0020 |
| Evidence matching | exact → loose → Jaccard ≥ 0.8 | No year awareness | Unconditional year-conflict veto | Same ladder + veto | Regression tests; **no data-batch measurement** |
| Verification hypothesis | Full sentence | Too wide | `narrow_primary_hypothesis` false→true (use `assertion_text` when available) | Narrow when available | Historical CPU n=456: 31 NEI→ENTAILED, 2 NEI→CONTRADICTED, 0 unsafe reversals. **Null on GOLD-02** (§7) |
| Correction | Whole-paragraph regen, 1 gate | No protection against invented citations, ordinal confusion, negation flips, sibling regressions | 5 further fail-closed gates added | Legacy regen + full gate chain | Regression tests per gate; **zero-event safety results only** |
| Scope check | Full-sentence | Blocked genuine isolated edits | `atomic_scope_check` false→`"assertion_spans"` | Span-level | Replay: **1/11** historical violations unblocked — weaker than the finding that motivated it |
| Re-verification | Bare premise, full sentence | Same mismatch as primary | `narrow_reverification_hypothesis` false→true | Narrow hypothesis | n=3 diagnostic; **0 ship/reject outcomes changed** |
| Retrieval method | Jaccard | — | BM25 and embedding built and benchmarked | **Jaccard retained** | Jaccard 9/9 vs BM25 3/9 vs embedding 2/9 correct-reject on the 9 adversarial cases — **rejected on safety** |

*This table is a map of changes, not a ranking. Rows are ordered by subsystem, not by importance.*

---

## 5. What was measured, freshly, for this package

Five experiments were re-executed from scratch on this machine (CPU only, DeBERTa only — no Qwen,
no GPU). All are deterministic: inference is greedy argmax over a softmax, so no inference seed
exists and the runs are exactly repeatable.

| Experiment | Design | Grade | Result |
|---|---|---|---|
| GOLD-01 verifier | n=420 gold items, bare vs labeled, single lever | **GOLD** | acc 0.7333→0.9714; macro F1 0.7487→0.9684; McNemar exact p=1.58e-30 (100 fixed, **0 broken**) |
| GOLD-01 stratified | same items, split by construction condition | **GOLD** | **99/100 of the gain is in attributed conditions**; non-attributed p=1.0 |
| GOLD-02 contradiction | n=59 synthetic, **2×2 factorial** | DETERMINISTIC_SYNTHETIC | recall 0.3559→0.4576, McNemar exact p=0.0312 (6 discordant); `narrow_primary_hypothesis` effect **exactly zero** |
| Parser progression | n=30 docs, 3 real commits re-executed from git | DETERMINISTIC_SYNTHETIC | 38→54→57 resolving to evidence; ORIGINAL→LATEST p=0.0020; INTERMEDIATE→LATEST p=0.2500 (**n.s.**) |
| Evidence pool | structural recount via production loader | DETERMINISTIC_SYNTHETIC | 59→136 records, 10→22 Acts; exact decomposition recovered |
| Threshold sensitivity | full sweep 0.34–0.99 from stored softmax | GOLD-derived | labeled leads at **every** threshold; production 0.70 on a flat plateau |

**Cross-stack reproduction is itself a finding.** The fresh GOLD-01 and GOLD-02 runs reproduced
the historical numbers **exactly** — identical accuracy, macro F1, and confusion matrices — on
Python 3.13.1 / torch 2.13.0+cpu / transformers 5.15.1, against historical runs made on Python
3.11.9 / torch 2.2.2+cu121 / transformers 4.40.2. The fresh parser LATEST arm (57) likewise
reproduces the committed `parser_fix_before_after_n30_v2_postfix.json` exactly, and the fresh
ORIGINAL arm (88 claims / 38 matched) reproduces `0e37525:outputs/eval_30_report.md` exactly.

---

## 6. The most important caveat in this package

**The GOLD-01 headline is overwhelmingly a benchmark-construction effect.**

GOLD-01 has 8 construction conditions. Three are *attributed*: the hypothesis names the provision,
while the ORIGINAL bare premise deliberately omits that identifier.

| Stratum | n | ORIGINAL acc | LATEST acc | Fixed | Broken | Sign test |
|---|---|---|---|---|---|---|
| All items | 420 | 0.7333 | 0.9714 | 100 | 0 | p = 1.6e-30 |
| **ATTRIBUTED** conditions | 151 | **0.3179** | **0.9735** | **99** | 0 | p = 3.2e-30 |
| **NON-attributed** conditions | 269 | **0.9665** | **0.9703** | **1** | 0 | **p = 1.0 (not significant)** |

**99.0% of every item the LATEST framing fixes lies in the attributed conditions**, where the bare
arm is structurally unable to succeed *by construction*. On the other 269 items the two arms are
statistically indistinguishable.

So the honest statement is:

> Labeled framing removes a **premise/hypothesis mismatch**. It is **not** demonstrated to
> improve legal reasoning generally, and the headline macro F1 0.749→0.968 must always be quoted
> with this stratification.

**It still matters.** Real generated statutory claims *are* overwhelmingly attributed, so the
attributed conditions are the realistic ones, not the artificial ones. The caveat constrains the
**size and generality** of the number, not whether the change was worth making. The argument is
carried independently by real-data evidence (a 147-claim CPU re-verification shifting ENTAILED
0→13, and the first shipped correction on a held-out natural batch) — evidence that does not
depend on the benchmark's construction at all.

---

## 7. Null, negative and inconclusive results — preserved

These are findings, not failures, and none of them is reframed as an improvement anywhere in this
package.

| Result | Status |
|---|---|
| **`narrow_primary_hypothesis` on GOLD-02** | **Exactly zero effect.** The narrow-only cell equals ORIGINAL to the item; the LATEST cell equals framing-only to the item. The entire GOLD-02 movement is premise framing. |
| **Parser work after `223eb9d`** | +3 claims over 3 documents, sign test **p = 0.25 — not significant** at n=30. The significant parser gain is the `223eb9d` fix (p=0.0156). |
| **`correction.assertion_aware`** | **0/10 shipped, identical to legacy's 0/10** on the same paired replay. Architecturally complete and safe; no shipping improvement demonstrated. Remains OFF. |
| **`assertion_span_primary_hypothesis`** | Evaluated at n=6 (the entire population found), 4/6 verdicts changed. **Not promoted** — sample size, not a found defect. Remains OFF. |
| **BM25 / embedding retrieval** | **Actively rejected.** Both accept every real match but are materially less safe on adversarial near-miss Act names. |
| **`narrow_reverification_hypothesis`** | n=3 diagnostic; **0 ship/reject outcomes changed**. Promoted on mechanism reasoning, not on a measured outcome improvement. |
| **`atomic_scope_check`** | Motivated by a finding (4/6 genuine edits blocked) that the later replay **did not reproduce** (1/11 unblocked). |
| **Joint four-/five-lever ablation** | **NOT EXECUTED and not executable here.** No additive or interaction effect between levers is claimed anywhere in this package. |
| **Correction shipping overall** | Cumulative natural rate **1/56 (1.8%)**, 0 unsafe. The dominant failure is the 7B corrector producing no-op or inadequate edits — a generation-quality limitation, not a pipeline defect. |

---

## 8. What remains limited

1. **No lawyer-validated ground truth exists anywhere in this project.** Every "accuracy" here is
   NLI agreement against audited statute text, never a legal-correctness determination.
2. **Correction evidence is thin and entirely historical.** 1/56 shipped; the mechanism
   comparisons run at n=6 and n=10. None of it could be rerun here (no GPU, Qwen uncached).
3. **Safety results are zero-event.** "0 unsafe shipped corrections" is real and worth stating,
   but it is over a small denominator and most gates have regression tests rather than
   data-batch measurements.
4. **The deterministic subsystems are strongly evidenced; the generative ones are not.** This
   package's fresh evidence covers parsing, retrieval, verification and verdict assignment. It
   does not cover generation or correction.
5. **Model identity is unpinned.** No `from_pretrained()` call pins a revision SHA, so exact
   weight identity for historical results is `UNDETERMINED`.
6. **Open discrepancies remain open** — see `NOT_GENERATED_REGISTER.md` §6 and
   `CHANGE_IMPACT_AUDIT.md`. They are recorded rather than fixed, because fixing them would mean
   altering frozen research artifacts.

---

## 9. The one-paragraph answer

The original NyayaMind (`0e37525`) was a complete, working pipeline that in practice did nothing:
on 30 real cases it resolved 38 of 88 claims to evidence, returned NEI for every single one of
them, and never once triggered a correction. Three things were wrong — the NLI premise omitted
the provision identifier that generated claims actually assert, the evidence pool was too small,
and the parser could not normalise real Indian citation forms — and all three were fixed. The
model weights never changed. Freshly re-measured on this machine, the parser change moves claims
resolving to evidence from 38 to 57 (p=0.0020), the pool grows 59→136 records across 10→22 Acts,
and the premise change moves gold-labelled verifier macro F1 from 0.749 to 0.968 — though 99% of
that last gain sits in benchmark conditions where the original premise was constructed to fail,
so it evidences a fixed premise/hypothesis mismatch rather than better legal reasoning. The
safety architecture grew from one gate to a full fail-closed chain, but its evidence is
regression tests and zero-event outcomes, not measured harm reduction. Correction remains the
weak link: 1 shipped correction in 56 natural attempts, and the two mechanisms built to improve
it both returned null.
