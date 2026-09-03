# Natural NyayaRAG claims — premise-framing re-verification

_Generated 2026-08-26T09:24:01.498383+00:00_

**Verification-only re-scoring of existing runs.** The generated fields, extracted
claims and matched evidence come verbatim from the committed `run_B_n30.jsonl` and
`run_natural_targeted.jsonl`; nothing was regenerated and those files were not
modified. Only the NLI premise framing differs.

> Verdicts are a small public NLI model's output against a 59-record evidence corpus.
> They are not legal-correctness determinations, and no lawyer ground truth exists.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

- Evidence-matched natural claims re-scored: **52**
- Bare-framing verdicts reproduced from the original GPU runs: **52/52**

## Verdict distribution

| Verdict | bare premise (production) | labeled premise |
|---|---|---|
| ENTAILED | 0 | 3 |
| CONTRADICTED | 0 | 0 |
| NOT_ENOUGH_INFORMATION | 52 | 49 |

## Correction trigger rate

| Premise framing | Claims triggering correction |
|---|---|
| bare (production) | 0/52 |
| labeled | 3/52 |

## Interpretation

A claim moving NEI → ENTAILED here means the NLI model now finds the statute text
supports the sentence once the premise carries the provision label the sentence is
about. It does NOT mean the sentence is legally correct, and it does not by itself
demonstrate that the pipeline improves anything: on natural data a higher ENTAILED
count means fewer claims are flagged, so the correction path stays mostly idle.

## Claims that changed verdict

3/52 claims changed verdict under labeled framing.

- **Section 120B in The Indian Penal Code, 1860** (n30/1971_200/c1)
  - claim: The statutory grounding for this case includes the Indian Penal Code, specifically Sections 120B, 420, and 467.
  - NOT_ENOUGH_INFORMATION (0.996) → ENTAILED (0.808)
- **Section 420 in The Indian Penal Code, 1860** (n30/1971_200/c2)
  - claim: The statutory grounding for this case includes the Indian Penal Code, specifically Sections 120B, 420, and 467.
  - NOT_ENOUGH_INFORMATION (0.992) → ENTAILED (0.739)
- **Section 302 in The Indian Penal Code, 1860** (targeted_n11/2009_1385/c1)
  - claim: The statutory grounding for this case is Section 302 of the Indian Penal Code (IPC), which defines the offense of murder.
  - NOT_ENOUGH_INFORMATION (0.997) → ENTAILED (0.874)

## Claims still NEI under labeled framing (49)

These are the ones worth a lawyer's eye: the statute text plus its label still does
not settle them, which is often correct for a sentence that bundles several
citations or asserts something about the case rather than about the provision.

- **Section 302 in The Indian Penal Code, 1860**: The case was governed by Sections 302 and 34 of the Indian Penal Code, 1860, which define the offence of murder and criminal liability respectively.
- **Section 34 in The Indian Penal Code, 1860**: The case was governed by Sections 302 and 34 of the Indian Penal Code, 1860, which define the offence of murder and criminal liability respectively.
- **Section 302 in The Indian Penal Code, 1860**: The Indian Penal Code, specifically Sections 302 and 34, apply to this case.
- **Section 34 in The Indian Penal Code, 1860**: The Indian Penal Code, specifically Sections 302 and 34, apply to this case.
- **Section 302 in The Indian Penal Code, 1860**: Section 302 prescribes the punishment for murder, while Section 34 deals with criminal liability for an act done by more than one person in furtherance of the common intention or common obje
- **Section 34 in The Indian Penal Code, 1860**: Section 302 prescribes the punishment for murder, while Section 34 deals with criminal liability for an act done by more than one person in furtherance of the common intention or common obje
- **Section 120B in The Indian Penal Code, 1860**: Section 120B deals with criminal conspiracy, Section 420 pertains to cheating, and Section 467 addresses the offence of passing off goods as new when they are old or damaged.
- **Section 420 in The Indian Penal Code, 1860**: Section 120B deals with criminal conspiracy, Section 420 pertains to cheating, and Section 467 addresses the offence of passing off goods as new when they are old or damaged.
