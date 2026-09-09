# narrow_primary_hypothesis benchmark: full claim_text vs. assertion_text

_Generated 2026-09-09T09:45:31.837406+00:00_

**Verification-only re-scoring of existing runs, both under the current production "labeled" premise framing.** Generated fields, extracted claims (including `assertion_text`) and matched evidence come verbatim from every committed outputs/*.jsonl file; nothing was regenerated, no source file was modified.

> Verdicts are a small public NLI model's output against this corpus. They are not legal-correctness determinations, and no lawyer ground truth exists.

- Unique real evidence-matched (claim_text, evidence_id) pairs collected: **456**
- Of those, claims with an actually-narrower `assertion_text` (i.e. this change can even apply): **107** (23.5%)

## Verdict distribution (all claims; unaffected claims counted identically in both)

| Verdict | full claim_text (production) | narrow assertion_text |
|---|---|---|
| ENTAILED | 30 | 61 |
| CONTRADICTED | 7 | 8 |
| NOT_ENOUGH_INFORMATION | 419 | 387 |

## Claims that changed verdict (34 / 107 claims with a narrower assertion)

- NEI -> ENTAILED (candidate coverage win): **31**
- NEI -> CONTRADICTED (candidate new correction trigger): **2**
- ENTAILED -> CONTRADICTED (**safety-relevant reversal**): **0**
- CONTRADICTED -> ENTAILED (**safety-relevant reversal**): **0**

None. No claim reversed between the two genuinely-safety-relevant labels (ENTAILED<->CONTRADICTED) anywhere in this dataset.

### NEI -> ENTAILED cases (first 10 of 31, inspect for spurious entailment)

- **Article 21 in Constitution of India** (final_gpu_validation_A.jsonl/2003_999)
  - claim_text: The statutory grounding includes Article 21 of the Constitution of India, which guarantees the right to life and personal liberty; Article 22(1), which provides certain safeguards in respect of personal liberties while a
  - assertion_text: The statutory grounding includes Article 21 of the Constitution of India, which guarantees the right to life and personal liberty
  - confidence: 0.916 -> 0.906
- **Article 22 in Constitution of India** (final_gpu_validation_A.jsonl/2003_999)
  - claim_text: The statutory grounding includes Article 21 of the Constitution of India, which guarantees the right to life and personal liberty; Article 22(1), which provides certain safeguards in respect of personal liberties while a
  - assertion_text: Article 22(1), which provides certain safeguards in respect of personal liberties while a person is under arrest or detention
  - confidence: 0.974 -> 0.954
- **Section 323 in The Indian Penal Code, 1860** (final_gpu_validation_A.jsonl/2004_1020)
  - claim_text: Section 147 IPC deals with the unlawful assembly with intent to commit a felony or to cause fear or violence, Section 323 IPC pertains to voluntarily causing hurt, Section 302 IPC defines murder, and Section 34 IPC provi
  - assertion_text: Section 323 IPC pertains to voluntarily causing hurt
  - confidence: 0.546 -> 0.975
- **Section 302 in The Indian Penal Code, 1860** (final_gpu_validation_A.jsonl/2006_641)
  - claim_text: The statutory grounding of this case includes the Indian Penal Code (IPC) sections 147 and 148, which deal with criminal trespass and riot, respectively; section 302, which prescribes the punishment for murder; section 3
  - assertion_text: section 302, which prescribes the punishment for murder
  - confidence: 0.922 -> 0.993
- **Section 324 in The Indian Penal Code, 1860** (final_gpu_validation_A.jsonl/2006_641)
  - claim_text: The statutory grounding of this case includes the Indian Penal Code (IPC) sections 147 and 148, which deal with criminal trespass and riot, respectively; section 302, which prescribes the punishment for murder; section 3
  - assertion_text: section 324, which pertains to voluntarily causing hurt
  - confidence: 0.528 -> 0.988
- **Section 302 in The Indian Penal Code, 1860** (final_gpu_validation_A.jsonl/2006_1150)
  - claim_text: Section 302 prescribes the punishment for murder, while Section 364 deals with abetment of suicide.
  - assertion_text: Section 302 prescribes the punishment for murder
  - confidence: 0.999 -> 0.992
- **Section 420 in The Indian Penal Code, 1860** (final_gpu_validation_A.jsonl/2006_1150)
  - claim_text: Section 420 criminalizes cheating, Section 467 and 468 deal with forgery and criminal conspiracy respectively, and Section 471 pertains to the use of a forged document.
  - assertion_text: Section 420 criminalizes cheating
  - confidence: 0.783 -> 0.999
- **Section 302 in The Indian Penal Code, 1860** (final_gpu_validation_A.jsonl/2008_2318)
  - claim_text: Section 300 defines the different degrees of murder, while Section 302 prescribes the punishment for murder.
  - assertion_text: Section 302 prescribes the punishment for murder.
  - confidence: 0.999 -> 0.995
- **Section 6 in The Land Acquisition Act, 1894** (final_gpu_validation_A.jsonl/1962_210)
  - claim_text: Section 4 authorizes the state to acquire land for public purposes, section 5A mandates the payment of compensation, section 6 provides that the declaration of the state regarding the necessity and public purpose of the 
  - assertion_text: section 6 provides that the declaration of the state regarding the necessity and public purpose of the acquisition is conclusive
  - confidence: 0.980 -> 0.990
- **Article 14 in Constitution of India** (final_gpu_validation_A.jsonl/2006_5)
  - claim_text: Article 14 requires equal protection of laws, Article 15 prohibits discrimination on grounds of religion, race, caste, sex, or place of birth, Article 16 ensures equality of opportunity and reasonable classification in m
  - assertion_text: Article 14 requires equal protection of laws
  - confidence: 0.980 -> 0.924
