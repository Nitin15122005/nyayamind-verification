# Verifier / Correction Bottleneck Diagnosis

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. All numbers below come from runs committed alongside this file.

> **Scope of every verdict in this document.** These are outputs of a small public NLI
> model (DeBERTa-v3-base-mnli-fever-anli) scored against a 59-record, third-party-sourced
> evidence corpus. They are **not** legal-correctness determinations. No lawyer ground
> truth exists. The Claude assumption annotations in this repository are **not** ground
> truth either and were not used here.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

---

## Headline

The investigation set out to find why DeBERTa keeps answering NOT_ENOUGH_INFORMATION on
"reasonable legal paraphrases", and why the Qwen corrector never produces text that passes
re-verification.

**Both framings of the problem turned out to be wrong.**

1. DeBERTa is not bad at legal paraphrase. On the controlled benchmark it labels
   paraphrased statute text ENTAILED **33/33**, with slightly *higher* entailment
   probability than the verbatim text (0.990 vs 0.982).
2. The corrector was not producing bad corrections. Re-scoring the 30 corrections the real
   Qwen model already produced shows **23/30 were correct** and were being rejected by the
   gate.

The single mechanism behind both failures is how the **premise** was built. The premise was
the bare statute text with the provision label stripped off. Generated legal claims are
almost always *attributed* — "According to Section 302 of the IPC, whoever commits
murder…". Against a premise that never mentions Section 302, that sentence asserts
something the premise cannot support, and a well-behaved NLI model must answer *neutral*.

The NEI flood was the verifier being **correct about a premise that had been stripped of the
identifier the claim was about.**

Restoring the label — a premise-side change, no new model, no GPU — moves controlled-benchmark
macro F1 from **0.749 → 0.968** and verified correction success from **0% → 76.7%**.

**It does not, however, rescue natural NyayaRAG data**, where only 3 of 52 claims change
verdict. That is a separate and still-unsolved bottleneck, described in §6.

---

## 1. Controlled benchmark construction

`outputs/controlled_verifier_benchmark.jsonl` — **420 items** over the 59 usable canonical
records (`VERIFIED_EXACT` 25, `VERIFIED_CONTENT` 34). Built by
`scripts/build_controlled_benchmark.py`, tagged `CONTROLLED_VERIFIER_BENCHMARK`, kept
entirely separate from natural NyayaRAG evaluation.

**No LLM was used in construction.** Every hypothesis is a deterministic, rule-based
transformation of audited canonical text, so each gold label follows from its construction
rule. No model prediction — DeBERTa's least of all — was ever consulted to produce a label.
No legal fact was invented: every item is either canonical text, a register-level rewrite of
it, a polarity flip of it, or another corpus provision's canonical text.

The design is a **2×2 factorial on the ENTAILED side**, which is what makes the two candidate
causes separable:

| | bare | attributed |
|---|---|---|
| **verbatim** | `E1_verbatim` (59) | `E2_verbatim_attributed` (59) |
| **paraphrased** | `E3_paraphrase_bare` (33) | `E4_paraphrase_attributed` (33) |

Plus `C1_negated_bare` (59) / `C2_negated_attributed` (59) mirroring the attribution factor
for contradictions, and two neutral conditions: `N1_other_provision` (59 — the verbatim text
of a *different* corpus provision, so 59 distinct items grounded wholly in audited text) and
`N2_procedural_addition` (59 — canonical rule plus an extraneous procedural condition).

Paraphrases use 33 meaning-preserving register swaps ("Whoever" → "Any person who",
"shall be punished with" → "is liable to punishment of"); nothing touches a bare modal,
quantifier, numeral or penalty amount. 26 record-conditions were **dropped rather than
degraded** where no safe transformation applied — reported in
`controlled_verifier_benchmark_meta.json`, which is why E3/E4 have 33 items and not 59.

The builder self-validates (and refuses to write on any failure): double-negation artifacts,
paraphrase identical to source, contradiction identical to source, factor flags disagreeing
with the actual string, and lexical tie-back to canonical text. 23 regression tests in
`tests/test_controlled_benchmark.py` cover the transformations and the validator.

### Why v2 and not the existing benchmark

`scripts/build_verifier_benchmark.py` (v1, 177 items) is kept for provenance but **cannot
answer this question**, for four reasons found on inspection:

- its ENTAILED condition was canonical text copied **verbatim** behind an attribution
  prefix, so it never tested paraphrase at all — the exact phenomenon under investigation;
- its NEI condition was **one hard-coded English sentence repeated for all 59 records** —
  one effective data point, not 59;
- its CONTRADICTED rewrites were ungrammatical (`"has no power or authoritys"`, from a
  prefix-match rule firing on "powers"); and
- item ids came from Python's `hash()`, which is **salted per interpreter**, so ids changed
  on every run and results could not be joined back to items.

v1 was also never actually run: no results file for it exists in `outputs/`.

---

## 2. Current DeBERTa performance (bare premise = production)

`controlled_benchmark_deberta_{results.jsonl,metrics.json,report.txt}` — 420 items, CPU,
65s. Full per-item probability distributions are persisted; the production pipeline records
only the argmax, which is exactly why this was not diagnosable from the existing n=30 outputs.

**Accuracy 0.733 · Macro F1 0.749**

| gold \ pred | ENT | CON | NEI | total |
|---|---|---|---|---|
| **ENTAILED** | 92 | 0 | **92** | 184 |
| **CONTRADICTED** | 2 | 103 | 13 | 118 |
| **NEI** | 0 | 5 | 113 | 118 |

| label | precision | recall | F1 | support |
|---|---|---|---|---|
| ENTAILED | 0.979 | **0.500** | 0.662 | 184 |
| CONTRADICTED | 0.954 | 0.873 | 0.912 | 118 |
| NOT_ENOUGH_INFORMATION | **0.518** | 0.958 | 0.673 | 118 |

### Why paraphrases are classified as NEI — they are not

Per-condition accuracy with mean NLI probability mass:

| condition | n | acc | p(ent) | p(neu) | p(con) |
|---|---|---|---|---|---|
| E1_verbatim | 59 | **1.000** | 0.982 | 0.013 | 0.006 |
| E3_paraphrase_bare | 33 | **1.000** | 0.990 | 0.007 | 0.003 |
| E2_verbatim_attributed | 59 | **0.000** | 0.017 | 0.981 | 0.002 |
| E4_paraphrase_attributed | 33 | **0.000** | 0.057 | 0.942 | 0.001 |

Matched-pair effects, same evidence records in both cells:

| effect | n | ENTAILED recall | Δ p(entail) |
|---|---|---|---|
| paraphrase (bare) | 33 | 1.000 → 1.000 (**+0.000**) | **+0.007** |
| attribution (verbatim) | 59 | 1.000 → 0.000 (**−1.000**) | **−0.965** |
| attribution (paraphrase) | 33 | 1.000 → 0.000 (**−1.000**) | **−0.932** |

A total dissociation. Paraphrase costs nothing. Attribution destroys entailment completely —
all **92/92** ENTAILED errors are precisely the 59 E2 + 33 E4 attributed items, and not one
bare item.

Two competing explanations are ruled out:

- **Not the confidence threshold.** Only 14/420 verdicts were downgraded by the 0.70
  threshold, and just 3 of those had entailment as the raw argmax. The model's own argmax is
  neutral, at ~0.98 confidence.
- **Not legal-domain mismatch.** A domain-mismatched model would degrade on paraphrase.
  This one is perfect on paraphrase and fails only on framing.

---

## 3. Alternative verifier tested — premise framing, not a new model

The diagnosis points at the premise, so the minimal alternative is a premise-side change
rather than a model swap: `format_premise(..., framing="labeled")` in `src/verifier.py`
prepends the provision label the audited evidence record already carries —
`"Section 302 of The Indian Penal Code, 1860: Whoever commits murder…"`. It adds only the
label, never edits statute text, and falls back to bare text when label metadata is missing.

Same model, same threshold, same 420 items (`controlled_benchmark_deberta_labeled_*`):

| metric | bare (production) | **labeled** |
|---|---|---|
| Accuracy | 0.733 | **0.971** |
| Macro F1 | 0.749 | **0.968** |
| ENTAILED P / R / F1 | 0.979 / 0.500 / 0.662 | 0.974 / **1.000** / **0.987** |
| CONTRADICTED P / R / F1 | 0.954 / 0.873 / 0.912 | 0.965 / **0.932** / **0.948** |
| NEI P / R / F1 | **0.518** / 0.958 / 0.673 | **0.974** / 0.966 / **0.970** |

**Nothing regressed.** Every condition held or improved:

| condition | bare acc | labeled acc |
|---|---|---|
| E1_verbatim | 1.000 | 1.000 |
| E2_verbatim_attributed | 0.000 | **1.000** |
| E3_paraphrase_bare | 1.000 | 1.000 |
| E4_paraphrase_attributed | 0.000 | **1.000** |
| C1_negated_bare | 0.932 | 0.932 |
| C2_negated_attributed | 0.814 | **0.932** |
| N1_other_provision | 0.915 | **0.932** |
| N2_procedural_addition | 1.000 | 1.000 |

The critical safety check is `N2_procedural_addition`, which stays at **59/59 correct NEI**:
labeling the premise did **not** make the model credulous. It still refuses to entail a claim
carrying extraneous conditions the statute does not state. Contradiction detection improved
rather than eroded.

**Qwen2.5-7B was not benchmarked as an alternative verifier** — see §7, environment.
Given a premise-side fix reaches 0.968 macro F1 with the model already in production, a 7B
LLM judge is hard to justify on cost/benefit and would need to beat 0.968 to be worth it.

**Production remains unchanged.** `pipeline.py` still passes bare `evidence_text`;
`format_premise` is available and tested but not wired in.

---

## 4. Correction experiment — the corrector was never the problem

`scripts/rerun_correction_reverification.py` re-verifies the **30 corrections the real
Qwen2.5-7B corrector already produced** during the GPU synthetic stress run, read verbatim
from `run_synthetic_stress.jsonl`. Nothing was regenerated; that file was not modified. The
only variable is premise framing.

**Validity check: bare framing reproduced the original GPU verdicts 30/30**, so CPU re-scoring
is directly comparable to the original run. Scope preserved 30/30.

| re-verification verdict | bare (production) | labeled |
|---|---|---|
| ENTAILED | 0 | **23** |
| CONTRADICTED | 2 | 4 |
| NOT_ENOUGH_INFORMATION | 28 | 3 |

| premise framing | corrections passing the safety gate | rate |
|---|---|---|
| bare (production) | 0/30 | **0.0%** |
| labeled | 23/30 | **76.7%** |

The gate itself is unchanged — ship only if re-verified ENTAILED **and** the unflagged
sentence survived verbatim.

A representative case. Corrupted claim:

> Section 302 … provides that the only punishment is a nominal fine, and death or
> imprisonment can never be imposed under this provision.

Qwen's correction:

> Section 302 of The Indian Penal Code, 1860 provides that whoever commits murder shall be
> punished with death, or imprisonment for life, and shall also be liable to fine.

That is a verbatim-accurate restatement of the canonical evidence with correct attribution —
and the production gate scored it **NOT_ENOUGH_INFORMATION at 0.994** and threw it away.
The reported "0% correction success rate" was a **scoring artifact, not a corrector failure.**

### The 7 that still do not ship

Correctly refused. In most, Qwen barely edited the corruption — e.g. Section 18 of the Land
Acquisition Act, "has no legal effect in this case and imposes no obligation, right, or
restriction of any kind", still CONTRADICTED at 1.000. 4 remain CONTRADICTED and 3 remain
NEI. This is the safety property working as designed: not all 30 corrections were good, and
the gate distinguishes them.

Controlled prompt variants were **not** explored. With the scoring bug identified and 23/30
corrections already passing unchanged, prompt variation would have been tuning against a
broken measurement.

---

## 5. Safety results

- **0 unsafe corrections shipped** in every configuration examined.
- **Scope preserved 30/30** on the stored corrections; 0 scope violations.
- The re-verification gate correctly refuses the 7 genuinely-bad corrections under labeled
  framing.
- The labeled framing does **not** weaken the gate: `N2_procedural_addition` remains 59/59
  NEI, and CONTRADICTED F1 rises 0.912 → 0.948.
- **No safety threshold was relaxed anywhere.** `confidence_threshold` stays at 0.70 and the
  ship condition is unchanged. The improvement comes entirely from giving the verifier a
  premise that contains the identifier the claim is about.

---

## 6. Natural NyayaRAG data — the fix does **not** transfer

`scripts/rerun_natural_verification.py` re-scores the **52 evidence-matched claims** from the
committed n=30 and targeted n=11 runs. Verification-only; generated fields, claims and
matched evidence reused verbatim; source files unmodified. Bare framing reproduced the
recorded verdicts **52/52**.

| verdict | bare (production) | labeled |
|---|---|---|
| ENTAILED | 0 | **3** |
| CONTRADICTED | 0 | 0 |
| NOT_ENOUGH_INFORMATION | 52 | 49 |

Only **3/52** claims change. Mean p(entail) rises 0.008 → 0.094 — still very low.

The reason is visible in the claims themselves. Natural NyayaRAG statutory-grounding
sentences are not restatements of a provision's rule. They are:

- **multi-citation bundles** — "The statutory grounding … includes the Indian Penal Code,
  specifically Sections 120B, 420, and 467", verified separately against *each* section's
  text;
- **metalinguistic descriptions** — "Sections 302 and 34 …, which define the offence of
  murder and criminal liability respectively" (61.5% of evidence-matched natural claims
  match a "defines / deals with / pertains to / governs" pattern); and
- **case-level or procedural assertions** — "the prosecution must prove the guilt of the
  accused beyond a reasonable doubt" — not stated in any provision text.

Against a single provision's text, these are **genuinely neutral**, and labeling the premise
does not help because the sentence is not a restatement of that provision in the first place.

Worse, the 3 that flip are **shallow**: "…includes the Indian Penal Code, specifically
Sections 120B, 420, and 467" is now ENTAILED by Section 420's text at 0.739, which is
arguably a false entailment — that sentence restates nothing about Section 420. So the
natural-data movement is small **and** partly spurious. That is a precision risk to watch,
not a win.

**The real natural-data bottleneck is claim granularity**: the claim unit is a whole sentence
that may bundle several citations, metalinguistic description and case-level assertion, while
the premise is one provision. This is an unsolved, separate problem from the one diagnosed
here.

---

## 7. What was and was not run, and why

This session ran on a **different machine** from the one that produced the GPU results:
Intel Iris Xe integrated graphics, **no NVIDIA GPU**, 15.6 GB RAM, no CUDA, no HuggingFace
cache, Docker daemon not running. `torch` and `transformers` were absent and were installed
CPU-only.

Consequently:

- **Run.** Everything using DeBERTa (184M params) — the whole controlled benchmark in ~65s
  per pass on CPU, plus both re-verification studies. CPU reproduced the original GPU
  verdicts exactly (30/30 corrections, 52/52 natural claims), so these results are directly
  comparable to the committed GPU runs.
- **Not run.** Anything requiring Qwen2.5-7B generation: a Qwen LLM verifier benchmark
  (STEP 3 alternative), live corrector prompt variants (STEP 4), and a Mode-C natural
  evaluation (STEP 6). 4-bit quantisation requires CUDA/bitsandbytes, and the model is not
  cached locally. These need the GPU machine.

Two changes were made so this work is reproducible on either machine, without weakening the
production guard:

- `NLIVerifier(device=...)` defaults to `"cuda"` and still refuses to run without it. CPU is
  an explicit opt-in only. The guard exists because in the pipeline this model shares a 6 GB
  card with the 4-bit 7B generator, where a silent CPU fallback turns a misconfiguration into
  an inexplicably slow run.
- The three real-verifier integration tests now select CPU when CUDA is absent. Their own
  fixture always described the NLI model as "small CPU-friendly"; they were erroring only
  because `load()` hard-required CUDA. They now execute rather than error.

Docker compatibility is unaffected: no dependency was added to `requirements.txt`, and no
production call site changed.

---

## 8. Was a 10-case natural evaluation justified?

**Not yet — and it would very likely reproduce the existing null result.**

The precondition in STEP 6 was a meaningful verification improvement. On the controlled
benchmark that is unambiguous (0.749 → 0.968 macro F1). But §6 already answers the natural-data
question on **52 claims** — more than a 10-case run would yield — for zero generation cost,
and the answer is that only 3 claims move and **0** become CONTRADICTED. With no CONTRADICTED
verdicts, Mode C's correction path would again trigger on almost nothing, producing a third
null result at real GPU cost.

The genuinely open question a GPU run should answer is narrower: does Mode C behave correctly
end-to-end under labeled framing on the synthetic set, where 23/30 corrections now pass? That
is the experiment worth spending GPU time on — not another natural A/B/C sweep.

---

## 9. What improved, what did not

**Improved (controlled + synthetic evidence):**
- Controlled benchmark accuracy 0.733 → 0.971; macro F1 0.749 → 0.968.
- ENTAILED recall 0.500 → 1.000; NEI precision 0.518 → 0.974; CONTRADICTED F1 0.912 → 0.948.
- Verified correction success on stored real Qwen corrections 0/30 → 23/30 (76.7%).
- Root cause of the "0% correction" result identified as a scoring artifact.
- The stated premise of the investigation was **refuted**: DeBERTa handles legal paraphrase
  perfectly (33/33).
- Test suite 68 → **95 passing**, with 3 previously-erroring integration tests now running.

**Did not improve:**
- Natural NyayaRAG verification: 52 → 49 NEI. 3 claims moved, at least 2 of them spuriously.
- Evidence coverage: unchanged. 50/88 natural claims in n=30 still have NO_EVIDENCE.
- Claim granularity: untouched, and now the principal natural-data bottleneck.
- Corrector prompt quality: not investigated (deliberately — see §4).
- Legal correctness: not measured, and not measurable without lawyer annotation.

**Remaining limitations:**
- 59-record corpus, 34 of which are `VERIFIED_CONTENT` rather than `VERIFIED_EXACT`.
- No lawyer ground truth; every verdict is NLI output, not legal fact.
- Benchmark items are rule-generated and lexically close to canonical text — easier than real
  generated prose, so 0.968 macro F1 is a **ceiling**, not an expected field accuracy.
- 3 CONTRADICTED items are awkward constructions ("No person shall not be deprived…"), which
  the validator's literal `not not` check does not catch; they account for part of the
  residual CONTRADICTED error.
- The labeled-framing result is established on controlled and synthetic data only. Its
  natural-data benefit is currently **3/52 and partly spurious**.

---

## 10. Honest research conclusion

The verification bottleneck is **diagnosed and, on controlled and synthetic data, solved** —
by a premise-framing correction rather than a better model. The correction path was never
broken: it was being scored by a premise that made correct output unrecognisable, and 23 of
30 real Qwen corrections pass unchanged once that is fixed. The safety gate held throughout,
and no threshold was relaxed to obtain any of this.

**The research hypothesis — that this layer makes generated legal reasoning more reliable —
remains unsupported on real data.** Nothing here demonstrates improved legal correctness. On
natural NyayaRAG cases the pipeline still finds essentially nothing to correct: 0 CONTRADICTED
across 52 evidence-matched claims under both framings. What has changed is that the reason is
no longer a mystery attributed to a weak verifier — the verifier is fine, and the remaining
obstacles are concrete and named: **claim granularity, evidence coverage, and the absence of
lawyer ground truth.**
