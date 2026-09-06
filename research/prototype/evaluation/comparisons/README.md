# Comparisons

This directory has two subdirectories that must **never** be treated as equivalent tiers
of evidence, despite sitting side by side:

## `expected_vs_actual/` — true accuracy, only against the two gold datasets

Reserved **exclusively** for comparisons of a fresh (or historical) actual output against
one of the two datasets in `../expected_outputs/` (the 420-item controlled NLI benchmark,
or the 59-item synthetic stress set). This is the only place in the entire workspace
where the phrase "accuracy" or "correct/incorrect" may legitimately be used against a
model prediction, because these are the only two datasets whose labels do not come from
the system being tested.

## Metric-based comparisons — described only as metrics, not "accuracy"

**PASS 1 correction (2026-09-05)**: earlier drafts of this document described a
`metric_based/` subdirectory as the planned home for this content. That subdirectory was
never built — the STEP 8 consolidation instead adopted `evaluation/`'s own stated design
rule ("`evaluation/` owns computation; `comparisons/` only narrates") and placed this
content directly in `../evaluation/`. There is no `comparisons/metric_based/` directory,
and none should be created — the content below already exists at the paths cited.

Every comparison other than a gold-vs-actual one — evidence-coverage before/after,
verdict distributions, paired McNemar-style comparisons between two pipeline
configurations run on identical natural cases, correction-shipping rates, agreement
against the provisional (non-lawyer-verified) assumption annotations — is described using
metric language ("coverage increased from X% to Y%", "config B triggered correction on N
more cases than config A"), **never** "accuracy" or "expected vs. actual," because there
is no independent ground truth behind any of these numbers. See in particular
`../evaluation/NATURAL_DATA_REPORT.md`, `EVIDENCE_STRENGTH_MATRIX.md`,
`STATISTICAL_RESULTS.md`, `CORRECTION_FUNNEL.md`, `SAFETY_SUMMARY.md`, and
`PAIRED_209_REPORT.md`.

**This content is not lesser evidence**: the McNemar-tested evidence-coverage gain
(χ²=13.07, p≈0.0003, n=209) and the premise-framing benchmark result both carry real
evidentiary weight, one gold-backed, one not. Being "metric-based" is a different *kind*
of evidence from `expected_vs_actual/`'s, not a weaker one — mixing the two kinds under
one label is the mistake this separation exists to prevent. Read
`../expected_outputs/README.md`'s Category C section before writing anything that draws
on this material.

**Two facts that must appear in every summary that draws on this subdirectory, not just
buried in a footnote:**
1. The correction-shipping-rate improvement (5→10 triggered, 0→1 shipped) is **not
   statistically significant** at this sample size (Wilson confidence intervals overlap
   almost entirely) — report it as directional, not proven.
2. **No single experiment combines all four current production-config levers in one
   fresh generation pass** — every headline "original vs. current" number is assembled
   from a chain of separate experiments on the same underlying case batch, not one joint
   run. See `../PROVENANCE.md` for the full caveat list.

## What's physically here right now

`expected_vs_actual/` holds the real GOLD-01/GOLD-02 comparison (STEP 4). Metric-based
comparison content, as corrected above, lives in `../evaluation/`, not in a subdirectory
of this one. Historical comparisons remain separately authoritative at
`research/prototype/archive/2026-08-27_presentation/final_comparison/` (frozen, archived
in PASS 3B) — see `../README.md` and `../reports/README.md`.
