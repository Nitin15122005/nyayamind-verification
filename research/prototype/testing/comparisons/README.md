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

## `metric_based/` — everything else, described only as metrics

Every other comparison in this project — evidence-coverage before/after, verdict
distributions, paired McNemar-style comparisons between two pipeline configurations run
on identical natural cases, correction-shipping rates, agreement against the provisional
(non-lawyer-verified) assumption annotations — belongs here, and must be described using
metric language ("coverage increased from X% to Y%", "config B triggered correction on N
more cases than config A"), **never** "accuracy" or "expected vs. actual," because there
is no independent ground truth behind any of these numbers.

**Why the name is `metric_based` and not something implying a lesser status**: this
directory holds the *majority* of this project's real evidentiary weight — the
McNemar-tested evidence-coverage gain (χ²=13.07, p≈0.0003, n=209) and the premise-framing
benchmark result both live in comparison territory, one gold-backed, one not. Being
"metric-based" is not being weaker evidence — it is a different *kind* of evidence, and
mixing the two kinds under one label is the mistake this separation exists to prevent.
Read `../expected_outputs/README.md`'s Category C section before writing anything in this
subdirectory.

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

Both subdirectories are structural placeholders as of this step — no comparison has been
(re-)computed inside this workspace yet. Historical comparisons already exist and remain
authoritative at `research/prototype/final_comparison/` (frozen) until this workspace
reproduces or extends them (see `../evaluation/README.md` and `../reports/README.md` for
the planned order of work).
