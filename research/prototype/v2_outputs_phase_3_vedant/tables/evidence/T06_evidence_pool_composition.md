# T06_evidence_pool_composition

Structural composition of the evidence pool, recomputed via the production loader (`src/data_loader.load_usable_evidence`).

| property | ORIGINAL (v0) | LATEST (v0+v1 merged) | delta |
|---|---|---|---|
| Records in v0 file | 63 | - | - |
| Usable records | 59 | 136 | +77 |
| Distinct Acts | 10 | 22 | +12 |
| VERIFIED_EXACT | 25 | 103 | - |
| VERIFIED_CONTENT | 34 | 33 | - |
| Records in v1 supplement file | - | 82 | - |
|   of which usable | - | 78 | - |
|   genuinely new keys | - | 79 | - |
|   new keys that are usable | - | 75 | - |
|   v0 keys corrected | - | 3 | - |
| RECONCILIATION | 59 v0 usable | + 75 new + 2 promoted = 136 | reconciles: True |

## Notes

- 59 + 78 = 137, not 136. The '78' is the count of USABLE records inside the v1 supplement FILE, not the count of records ADDED to the pool. Correct decomposition: 59 v0 usable + 75 genuinely-new usable keys + 2 keys promoted from unusable by a v0 correction = 136.
- A deterministic structural count over read-only evidence files using the production loader. This is an INPUT property of the system, not a retrieval outcome — it is not an accuracy, precision, recall or coverage measurement.
