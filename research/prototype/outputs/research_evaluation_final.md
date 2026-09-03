# Research Evaluation — Final Results

**Prototype v0 · NyayaMind Selective-Correction Pipeline**
**Generated**: 2026-08-25 · All metrics extracted from existing JSONL outputs; no inference re-run.

> [!IMPORTANT]
> All verdicts are from an automated NLI model (DeBERTa-v3-base-mnli-fever-anli) checked
> against a 59-record third-party-sourced evidence corpus. They are NOT legal-correctness
> determinations. No lawyer ground-truth annotation has been completed.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

---

## A. Natural NyayaRAG Evaluation

**Source**: `run_natural_targeted.jsonl` (11 documents), `run_A/B/C_n30.jsonl` (30 documents)

### Natural Targeted Evaluation (n=11)

| Metric | Mode A | Mode B | Mode C |
|--------|--------|--------|--------|
| Documents evaluated | 11 | 11 | 11 |
| Total claims extracted | 29 | 29 | 29 |
| Claims with evidence | 14 | 14 | 14 |
| Claims NO_EVIDENCE | 15 | 15 | 15 |
| ENTAILED | — | 0 | 0 |
| CONTRADICTED | — | 0 | 0 |
| NOT_ENOUGH_INFORMATION | — | 14 | 14 |
| NO_EVIDENCE | — | 15 | 15 |
| Correction triggered | n/a | n/a | **0** |
| Final field source | original (11/11) | original (11/11) | original (11/11) |
| Avg time per doc | 41.1s | 41.5s | 41.4s |

### N=30 Evaluation (original A/B/C run)

| Metric | Mode A | Mode B | Mode C |
|--------|--------|--------|--------|
| Documents evaluated | 30 | 30 | 30 |
| Total claims extracted | 88 | 88 | 88 |
| Claims with evidence | 38 | 38 | 38 |
| Claims NO_EVIDENCE | 50 | 50 | 50 |
| ENTAILED | — | 0 | 0 |
| CONTRADICTED | — | 0 | 0 |
| NOT_ENOUGH_INFORMATION | — | 38 | 38 |
| NO_EVIDENCE | — | 50 | 50 |
| Correction triggered | n/a | n/a | **0** |
| Final field source | original (30/30) | original (30/30) | original (30/30) |

**Key finding**: On real NyayaRAG-generated statute-grounding fields, Qwen2.5-7B-Instruct (4-bit) produced **zero CONTRADICTED claims** in both the n=30 and n=11 samples. All 14/38 evidence-matched claims were classified as NOT_ENOUGH_INFORMATION with high confidence (mean ~0.99). Consequently, Mode C's correction path was never triggered on natural data.

---

## B. Synthetic Contradiction Stress Test

**Source**: `run_synthetic_stress.jsonl` (59 records, one per usable canonical statute)
**Label**: ALL RESULTS IN THIS SECTION ARE FROM SYNTHETIC DATA

### Mutation types

| Transform Rule | Count |
|----------------|-------|
| shall_negated | 20 |
| may_to_must | 19 |
| punishment_death_to_fine_only | 9 |
| generic_negation | 9 |
| punishment_life_imprisonment_to_short_term | 1 |
| condition_reversed_unless_except | 1 |
| **Total** | **59** |

### Verification Results (Condition B — injected contradictions only)

| Verdict on c1 (injected contradiction) | Count |
|-----------------------------------------|-------|
| CONTRADICTED | 21 |
| NOT_ENOUGH_INFORMATION (high-confidence) | 23 |
| NOT_ENOUGH_INFORMATION (low_confidence sub_reason) | **—** |
| NO_EVIDENCE | 15 |
| ENTAILED | 0 |

**Detection recall**:
- Overall (59 synthetic contradictions): **21/59 = 35.6%**
- Where evidence was found (44 claims with evidence match): **21/44 = 47.7%**
- Where evidence was NOT found: 15/59 = 25.4% (parser extracted act_norm did not match evidence index)

### Evidence Coverage Gap (Synthetic)

15 out of 59 synthetic contradictions could not be matched to evidence at all (NO_EVIDENCE). This is because the claim parser extracts the act name as part of `act_norm`, and when the synthetic claim transforms the original text, the extracted `act_norm` often fails to match the evidence index key. This is a **parser/normalization limitation**, not a verifier limitation.

### False Positive Rate (Unflagged Claims)

| Verdict on c2 (unflagged true claim) | Condition B | Condition C |
|---------------------------------------|-------------|-------------|
| NOT_ENOUGH_INFORMATION | 59 | 59 |
| CONTRADICTED | 0 | 0 |
| NO_EVIDENCE | 0 | 0 |

**False positive rate: 0%** — The verifier never incorrectly flagged a true, unflagged claim (Article 14 sentence) as CONTRADICTED in either condition.

---

## C. Selective-Correction Results (Synthetic Condition C)

### Correction Trigger Breakdown

| Metric | Count |
|--------|-------|
| Total synthetic claims | 59 |
| Correction triggered | **30** |
| — Triggered by CONTRADICTED verdict | 21 |
| — Triggered by NEI low_confidence sub_reason | 9 |
| Correction not triggered | 29 |
| — NO_EVIDENCE (no evidence to verify against) | 15 |
| — NEI high-confidence (genuine neutral) | 14 |

### Qwen Correction Attempts

| Metric | Count |
|--------|-------|
| Total correction attempts | **30** |
| Correction became ENTAILED (shipped) | **0** |
| Correction remained NEI (correction_failed) | 28 |
| Correction remained CONTRADICTED (correction_failed) | 2 |
| Correction scope violation | 0 |
| **Correction success rate** | **0/30 = 0%** |

### Why Corrections Failed

All 30 Qwen correction attempts were re-verified by DeBERTa NLI. None achieved ENTAILED:
- 28 re-verified as NOT_ENOUGH_INFORMATION — Qwen rewrote the claim closer to the evidence text, but DeBERTa still classified it as NEI rather than ENTAILED
- 2 re-verified as CONTRADICTED — Qwen's rewrite still contradicted the evidence

The pipeline correctly refused all 30 corrections and shipped the original text (`source: "correction_failed"` for 30, `source: "original"` for 29).

### Unsafe Corrections Shipped

| Metric | Count |
|--------|-------|
| Corrections shipped while still CONTRADICTED | **0** |
| Corrections shipped while still NEI | **0** |
| Total unsafe shipments | **0** |

---

## D. Safety / Re-verification Results

The re-verification gate operated correctly across all evaluations:

1. **No corrections were shipped**: All 30 correction attempts in synthetic C failed re-verification (none reached ENTAILED), so original text was preserved in every case.
2. **No scope violations occurred**: Qwen never modified unflagged claims in the corrected output (0 scope violations).
3. **No false positives on unflagged claims**: The verifier correctly left all c2 (true) claims as NEI in both B and C conditions. 0/59 unflagged claims were incorrectly flagged.
4. **Natural data was never modified**: Mode C on real data never triggered correction (0/11 targeted, 0/30 n=30), so no real generated field was altered.

---

## E. Evidence-Corpus Limitations

| Limitation | Impact |
|------------|--------|
| Only 59 usable evidence records (IPC + Constitution) | 56.8% of real claims (50/88 in n=30) had NO_EVIDENCE, making verification impossible for those claims |
| Evidence covers only IPC 1860 and Constitution of India | Cases citing CrPC, CPC, specific Acts, or state laws cannot be verified at all |
| Evidence is section/article-level text only | No subsection, proviso, or explanation-level granularity |
| Third-party sourced, not official gazette text | Canonical text may have minor differences from official gazette versions |
| No evidence audit for subsection-level claims | Claims referencing specific subsections fall back to full-section matching |

---

## F. Parser/Extraction Limitations

| Limitation | Impact |
|------------|--------|
| `act_norm` extraction captures clause fragments | When claims say "the Indian Penal Code pertains to...", the full phrase becomes the act_norm, failing to match the index key "indian penal code 1860" |
| Synthetic mutations break `act_norm` matching | 15/59 synthetic claims lost evidence matching because the mutation altered the phrase around the act reference |
| Anaphoric references ("the same code") fail | Claims using "the same code" instead of repeating the act name produce `act_norm = "same code"` which cannot match any evidence |
| No cross-sentence coreference resolution | If Act A is named in sentence 1 and sentence 2 says "Section X of the above Act", sentence 2's claim cannot resolve the act reference |
| DeBERTa NLI model has domain mismatch | Trained on MNLI/FEVER/ANLI (general English), not legal text — may systematically prefer NEI for legal paraphrases that are semantically entailed |

---

## G. What the Experiment Actually Proves

1. **The pipeline architecture works end-to-end**: Generation → claim extraction → evidence matching → NLI verification → selective correction → re-verification → scope enforcement → safe output selection all execute correctly with real models on GPU.

2. **The safety gate works**: When corrections fail re-verification, they are rejected. Zero unsafe corrections were shipped across 59 synthetic + 41 natural claim evaluations. This is the pipeline's core safety property.

3. **The verifier detects some synthetic contradictions**: 21/44 evidence-matched synthetic contradictions were correctly flagged as CONTRADICTED (47.7% recall with evidence). This demonstrates the NLI model can catch at least some factual distortions about statutory provisions.

4. **Unflagged claims are preserved**: 0/59 unflagged true claims were incorrectly flagged (0% false positive rate in synthetic). Correction never altered unflagged sentences (0 scope violations).

5. **Qwen2.5-7B does not produce detectable contradictions on natural data**: On 30 real NyayaRAG cases (88 claims), zero CONTRADICTED verdicts were produced. This means either (a) Qwen's natural generations are factually consistent with statutory evidence, or (b) the NLI model and 59-record evidence pool are insufficient to detect errors in natural generations.

---

## H. What It Does NOT Prove

1. **Does NOT prove Mode C improves legal correctness**: Zero corrections were triggered or shipped on natural data. The correction path was only exercised on synthetic data, and achieved 0% success rate. There is no evidence that Mode C produces more legally correct outputs than Mode A or B on real data.

2. **Does NOT prove Qwen's natural generations are legally correct**: Zero CONTRADICTED verdicts ≠ zero errors. The verifier classified all evidence-matched natural claims as NEI, which means "the NLI model could not determine whether the claim is supported or contradicted by the evidence." This is not the same as "the claim is correct."

3. **Does NOT prove the NLI verifier is accurate for legal text**: With no lawyer ground truth annotation, we cannot compute precision, recall, or F1 for the verifier on real legal claims. The 47.7% recall on synthetic data is a lower bound under ideal conditions (grossly distorted claims).

4. **Does NOT prove the pipeline scales**: n=30 cases is a tiny fraction of the NyayaRAG dataset. The 59-record evidence pool is far too small for production use. Evidence coverage would need to be expanded by 10-100x.

5. **Does NOT prove the correction model can fix real errors**: The 0% correction success rate (0/30 synthetic, 0/0 natural) means Qwen's corrections, while often directionally correct (rewriting toward the evidence text), do not satisfy DeBERTa's ENTAILED threshold. This may be a DeBERTa domain-mismatch issue, a prompt engineering issue, or fundamental to the task difficulty.

6. **Does NOT establish whether NEI is a correct verdict for natural claims**: All 38 evidence-matched natural claims received NEI. Without lawyer annotation, we cannot determine whether this reflects true semantic neutrality, a domain-mismatch bias toward NEI in legal text, or a systematic verifier limitation.

---

## Summary Table

| Evaluation | N | CONTRADICTED detected | Corrections triggered | Corrections shipped | Unsafe shipments |
|------------|---|----------------------|----------------------|--------------------|-----------------:|
| Natural targeted (n=11) | 29 claims | 0 | 0 | 0 | 0 |
| Natural n=30 | 88 claims | 0 | 0 | 0 | 0 |
| Synthetic stress (n=59) | 118 claims | 21 (c1 only) | 30 | 0 | 0 |
