# Correction Re-verification — premise-framing diagnosis

_Generated 2026-08-26T09:22:35.023280+00:00_

**SYNTHETIC DATA.** Re-verification only: the corrected claims are the ones the
real Qwen2.5-7B corrector produced during the GPU synthetic stress run and wrote to
`run_synthetic_stress.jsonl`. Nothing was regenerated here, and that file was not
modified. The single variable is how the NLI premise is framed.

- Stored corrections examined: **30**
- Bare-framing verdicts reproduced from the original GPU run: **30/30**
- Scope preserved (unflagged sentence intact): **30/30**

## Re-verification verdict on the corrected claim

| Verdict | bare premise (production) | labeled premise |
|---|---|---|
| ENTAILED | 0 | 23 |
| CONTRADICTED | 2 | 4 |
| NOT_ENOUGH_INFORMATION | 28 | 3 |

## Corrections that would pass the safety gate

| Premise framing | Corrections shipped | Rate |
|---|---|---|
| bare (production) | 0/30 | 0.0% |
| labeled | 23/30 | 76.7% |

The gate is unchanged: a correction ships only if it re-verifies as ENTAILED and the
unflagged sentence survived verbatim. Only the premise framing differs.

## Examples

### Corrections rejected under bare framing but accepted under labeled (23)

- **Section 302 in The Indian Penal Code, 1860** (`punishment_death_to_fine_only`)
  - corrupted claim: Section 302 of The Indian Penal Code, 1860 provides that the only punishment is a nominal fine, and death or imprisonment can never be imposed under this provision.
  - Qwen correction: Section 302 of The Indian Penal Code, 1860 provides that whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.
  - bare: NOT_ENOUGH_INFORMATION (0.994) → labeled: ENTAILED (0.994)
- **Section 34 in The Indian Penal Code, 1860** (`generic_negation`)
  - corrupted claim: Section 34 of The Indian Penal Code, 1860 has no legal effect in this case and imposes no obligation, right, or restriction of any kind.
  - Qwen correction: Section 34 of The Indian Penal Code, 1860 provides that when a criminal act is done by several persons in furtherance of the common intention of all, each of such persons is liable for that act in the
  - bare: NOT_ENOUGH_INFORMATION (0.996) → labeled: ENTAILED (0.992)
- **Section 149 in The Indian Penal Code, 1860** (`generic_negation`)
  - corrupted claim: Section 149 of The Indian Penal Code, 1860 has no legal effect in this case and imposes no obligation, right, or restriction of any kind.
  - Qwen correction: Section 149 of The Indian Penal Code, 1860 imposes liability on members of an unlawful assembly for offences committed in prosecution of the common object of that assembly, or such as the members of t
  - bare: NOT_ENOUGH_INFORMATION (0.994) → labeled: ENTAILED (0.996)
- **Section 307 in The Indian Penal Code, 1860** (`punishment_death_to_fine_only`)
  - corrupted claim: Section 307 of The Indian Penal Code, 1860 provides that the only punishment is a nominal fine, and death or imprisonment can never be imposed under this provision.
  - Qwen correction: Section 307 of The Indian Penal Code, 1860 provides that whoever does any act with such intention or knowledge, and under such circumstances that, if he by that act caused death, he would be guilty of
  - bare: NOT_ENOUGH_INFORMATION (0.992) → labeled: ENTAILED (0.990)
- **Section 148 in The Indian Penal Code, 1860** (`punishment_death_to_fine_only`)
  - corrupted claim: Section 148 of The Indian Penal Code, 1860 provides that the only punishment is a nominal fine, and death or imprisonment can never be imposed under this provision.
  - Qwen correction: Section 148 of The Indian Penal Code, 1860 provides that the punishment for rioting, being armed with a deadly weapon or with anything which, used as a weapon of offence, is likely to cause death, sha
  - bare: NOT_ENOUGH_INFORMATION (0.992) → labeled: ENTAILED (0.993)

### Corrections still not shipping under labeled framing (7)

- **Section 376 in The Indian Penal Code, 1860** (`punishment_life_imprisonment_to_short_term`) → NOT_ENOUGH_INFORMATION (0.774), scope_preserved=True
  - Qwen correction: Section 376 of The Indian Penal Code, 1860 limits the maximum punishment to rigorous imprisonment of either description for a term which shall not be less than ten years, but which may extend to imprisonment for life, an
- **Article 12 in Constitution of India** (`condition_reversed_unless_except`) → CONTRADICTED (0.930), scope_preserved=True
  - Qwen correction: Article 12 of Constitution of India applies unconditionally in every case, without any of the exceptions or qualifying conditions as stated in the statute.
- **Section 18 in The Land Acquisition Act, 1894** (`generic_negation`) → CONTRADICTED (1.000), scope_preserved=True
  - Qwen correction: Section 18 of The Land Acquisition Act, 1894 has no legal effect in this case and imposes no obligation, right, or restriction of any kind.
- **Section 109 in The Indian Penal Code, 1860** (`generic_negation`) → CONTRADICTED (0.999), scope_preserved=True
  - Qwen correction: Section 109 of The Indian Penal Code, 1860 has no legal effect in this case as it pertains to abetting an offence, and imposes no obligation, right, or restriction of any kind.
- **Section 302 in The Code of Criminal Procedure, 1973** (`may_to_must`) → CONTRADICTED (0.917), scope_preserved=True
  - Qwen correction: Section 302 of The Code of Criminal Procedure, 1973 makes this action an absolute, non-discretionary legal duty that must always be carried out, with no discretion permitted.
- **Section 256 in The Income Tax Act, 1961** (`generic_negation`) → NOT_ENOUGH_INFORMATION (0.537), scope_preserved=True
  - Qwen correction: Section 256 of The Income Tax Act, 1961 provides for the reference of questions of law to the High Court and imposes no obligation, right, or restriction of any kind in this case.
- **Section 2 in The Industrial Disputes Act, 1947** (`generic_negation`) → NOT_ENOUGH_INFORMATION (0.688), scope_preserved=True
  - Qwen correction: Section 2 of The Industrial Disputes Act, 1947 provides definitions for various terms used throughout the Act but has no legal effect in this case and imposes no obligation, right, or restriction of any kind.
