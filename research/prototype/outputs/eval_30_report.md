# MVP Research Evaluation — 30-case A/B/C Run

**Preliminary system-level results only. Mode C is NOT claimed to improve
correctness — no human annotation has been performed.**

- Cases: 30, selected deterministically (seed=42) from cases with >=1 citation
  overlapping the 59 usable canonical statutes.
- Same 30 cases, same generated field, run under modes A / B / C (paired comparison).
- document_ids: ['1992_534', '2009_1385', '2007_1517', '2024_244', '1987_609', '1954_7', '1996_772', '1992_31', '1994_650', '2005_360', '2005_128', '1971_200', '1982_43', '2008_1494', '1970_250', '1971_379', '1996_439', '1987_597', '2006_650', '2003_967', '1962_184', '1989_184', '1998_229', '1952_17', '1965_377', '2008_2662', '2004_632', '2023_26', '1991_582', '2008_2648']

## Generation & claim extraction (shared across A/B/C)
- Total generated fields: 30
- Total claims extracted: 88 (mean 2.93/field)
- Evidence coverage: 38/88 claims matched (43.2%)
- NO_EVIDENCE rate: 56.8% (50 claims)
- Evidence match method breakdown: {'exact_normalized': 24, 'no_evidence': 50, 'fuzzy': 14}

## Verification (modes B & C)
- Verdict counts (mode C): {'ENTAILED': 0, 'CONTRADICTED': 0, 'NOT_ENOUGH_INFORMATION': 38, 'NO_EVIDENCE': 50}
- All NEI verdicts sub_reason breakdown: {None: 38}
- NEI confidence: mean 0.9889, range [0.9414, 0.999]
- ENTAILED: 0, CONTRADICTED: 0

## Selective correction (mode C only)
- Correction-trigger rate: 0.0% (0/30)
- Correction-success rate: 0.0% of all cases (0/30)
- Correction-failed rate: 0.0% (0/30)
- Scope-violation rate: 0.0% (0/30)
- Final-field changed vs. original generation: 0.0% (0/30)
- Status counts: {'not_triggered': 30, 'corrected': 0, 'correction_failed': 0, 'correction_scope_violation': 0}

Zero corrections triggered: with 0 CONTRADICTED verdicts and every NEI verdict a
genuine high-confidence neutral (sub_reason=None, mean confidence 0.989, none below
the 0.70 threshold), neither correction-trigger condition (CONTRADICTED, or
low-confidence-downgraded NEI) was met for any of the 88 real claims in this sample.

## Runtime
- Mode A: mean 18.91s, median 19.02s, range [10.14, 28.37]s, total 567.36s
- Mode B: mean 18.94s, median 19.02s, range [10.15, 28.52]s, total 568.11s
- Mode C: mean 18.93s, median 19.02s, range [10.15, 28.35]s, total 567.97s
- Peak VRAM observed across the run: 5911 MiB

## Caveats
- These are preliminary, machine-computed system-level statistics only.
- No human review of claim correctness, evidence relevance, or NLI verdict quality
  has been performed. Do not interpret evidence coverage, verdict distribution, or
  the zero correction-trigger rate as a claim about system quality or correctness.
- Mode C's effect on correctness is UNKNOWN from this run alone — no claims were
  actually corrected in this sample, so no A-vs-C correctness comparison is possible
  yet.