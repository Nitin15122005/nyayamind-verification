# MVP Evaluation — 30-Case A/B/C Run, Provisional Assumption Analysis

> **PROVISIONAL / ASSUMPTION-BASED.** Every "assumption" figure in this
> report comes from `lawyer_annotation.jsonl`, which currently holds
> Claude-generated labels (`annotation_source:
> "CLAUDE_ASSUMPTION_NOT_LAWYER_VERIFIED"` on every record) — **not real
> human/lawyer ground truth.** No claim in this report about correctness,
> accuracy, or improvement should be read as legally validated. It becomes
> validated only once `lawyer_annotation.jsonl` is overwritten with the
> lawyer's real judgments from the annotated PDF, and this report is
> re-run against that.

Sources used: `lawyer_annotation.jsonl` (88 rows, assumption labels),
`assumption_vs_automated_report.md`, `run_A_n30.jsonl`, `run_B_n30.jsonl`,
`run_C_n30.jsonl` (30 cases each). All figures below were recomputed
directly from these files and cross-checked against
`eval_30_report.md` / `assumption_annotation_summary.md` where they
overlap; no numbers are carried over unverified.

---

## 1. Dataset

| Metric | Value |
|---|---|
| Cases | 30 (deterministic seed=42, document_ids listed in `eval_30_report.md`) |
| Claims extracted | 88 (mean 2.93/case) |
| Claims with matched evidence | 38 (43.2%) |
| Claims without evidence (`NO_EVIDENCE`) | 50 (56.8%) |
| Evidence match method | exact_normalized: 24, fuzzy: 14, no_evidence: 50 |

Identical across all three modes (A/B/C) — generation, claim extraction,
and evidence matching are one shared stage run once, confirmed by direct
comparison: `generated_field.text` and each case's `claim_text` list are
byte-identical across `run_A_n30.jsonl`, `run_B_n30.jsonl`, and
`run_C_n30.jsonl`.

## 2. Verification

| Label set | Source | Comparable claims (evidence-matched only) |
|---|---|---|
| Automated NLI (`automated_verdict` / mode B & C `verification.counts`) | NLI model run in the pipeline | 38 |
| Assumption labels (`lawyer_annotation.evidence_entails_claim`) | Claude, provisional | 38 |

The remaining 50/88 claims have no matched evidence, so the NLI verifier
is never invoked for them (fixed `NO_EVIDENCE` verdict on both sides) —
they carry no comparison signal and are excluded from the tables below.

### Automated NLI verdict (38 evidence-matched claims)

| Verdict | Count |
|---|---|
| NOT_ENOUGH_INFORMATION | 38 |
| ENTAILED | 0 |
| CONTRADICTED | 0 |

The NLI model called every single evidence-matched claim "neutral" —
`eval_30_report.md` confirms this was a genuine high-confidence neutral
prediction (`sub_reason: None` for all 38, mean confidence 0.989), not a
low-confidence downgrade.

### Assumption verdict (38 evidence-matched claims)

| Verdict | Count |
|---|---|
| NOT_ENOUGH_INFORMATION | 20 |
| ENTAILED | 16 |
| CONTRADICTED | 2 |

### Agreement / disagreement

| | Count | % of 38 |
|---|---|---|
| Agree | 20 | 52.6% |
| Disagree | 18 | 47.4% |

### Breakdown of the 18 disagreements

| Pattern | Count | Description |
|---|---|---|
| Assumption ENTAILED vs. automated NEI | 16 | Claim makes a tight, specific factual assertion the matched evidence text directly states (e.g. "Section 302 prescribes the punishment for murder" against the literal Sec.302 punishment sentence); NLI model still called it neutral. |
| Assumption CONTRADICTED vs. automated NEI | 2 | `A0039` (Sec.201 IPC evidence is about concealing evidence/screening an offender, not "abetment" as claimed) and `A0078` (an upstream act-attribution bug fed in CrPC §302 "permission to conduct prosecution" text as if it were IPC §302 murder text). |
| Assumption NEI vs. automated NEI | 20 | Agreement — generic "grounding/applies to this case" claims, or claims adding an unconfirmed specific detail (mens rea, standard of proof) beyond what the evidence states. |

Full per-claim disagreement table with document_id/claim_id/reason is in
`assumption_vs_automated_report.md` §5 — not duplicated here.

## 3. Selective correction (Mode C, `run_C_n30.jsonl`)

| Metric | Value |
|---|---|
| Correction triggers (`triggered_for_claim_id` non-null) | 0 / 30 |
| Correction successes (`status: "corrected"`) | 0 / 30 |
| Correction failures (`status: "correction_failed"`) | 0 / 30 |
| Scope violations (`status: "correction_scope_violation"`) | 0 / 30 |
| `status: "not_triggered"` | 30 / 30 |
| Final-field changed vs. original generation (`final_field.text != generated_field.text`) | 0 / 30 |

`correction.status` is `"not_triggered"` for all 30 cases in
`run_C_n30.jsonl`, confirmed directly from the file. This matches
`_should_trigger_correction()`'s documented rule
(`pipeline.py`): correction fires only for a `CONTRADICTED` verdict, or a
`NOT_ENOUGH_INFORMATION` verdict specifically downgraded from
low-confidence. Since the NLI model produced zero `CONTRADICTED` verdicts
and every NEI verdict was a genuine high-confidence neutral (not a
downgrade), neither trigger condition was ever met in this 30-case sample.

## 4. A/B/C comparison (measurable without human ground truth)

| Metric | Mode A | Mode B | Mode C |
|---|---|---|---|
| Cases | 30 | 30 | 30 |
| Claims extracted | 88 | 88 | 88 |
| Claims with evidence | 38 | 38 | 38 |
| Evidence match breakdown | exact:24, fuzzy:14, none:50 | same | same |
| `verification.counts` (self-reported) | all `None`/not run (mode A skips verification) | ENTAILED:0, CONTRADICTED:0, NEI:38, NO_EVIDENCE:50 | ENTAILED:0, CONTRADICTED:0, NEI:38, NO_EVIDENCE:50 |
| Correction attempts | n/a (mode A has no correction stage) | n/a (mode B never applies correction) | 0/30 triggered |
| `final_field.source` | `"original"` ×30 | `"original"` ×30 | `"original"` ×30 |
| `final_field.text` vs. `generated_field.text` | identical (0/30 differ) | identical (0/30 differ) | identical (0/30 differ) |
| Runtime (from `eval_30_report.md`, not recomputed here) | mean 18.91s | mean 18.94s | mean 18.93s |

**Result: A, B, and C produced byte-identical final output text for all
30 cases in this run.** Mode B only adds diagnostic verification metadata
on top of A's output (by design, verification never changes mode B's
output); Mode C's correction stage never fired, so its final field also
never diverged from the shared baseline generation.

**No correctness claim is made or supportable here.** Because Mode C never
triggered a correction, this run provides **no evidence either for or
against** the hypothesis that selective correction improves output
correctness — that comparison requires cases where correction actually
fires, which requires either a larger/more provocative sample or (more
fundamentally) human ground truth to know whether the "corrected" text is
actually more correct. Per project ground rules, we do not claim Mode C is
better based on this run.

## 5. Main findings

- **Evidence-corpus coverage is the dominant limitation.** Only 43.2%
  (38/88) of claims found any matching evidence at all, because the
  canonical evidence corpus behind this prototype covers only ~59 usable
  citation keys (see `research/data/evidence/README.md`) — nowhere near
  full coverage of the citations these 30 cases actually reference. This
  alone caps how much of the pipeline's output can be verified at all,
  independent of any other limitation.
- **Parser/extraction issues materially affect a meaningful minority of
  claims.** The assumption pass identified 15/88 claims (17%) where
  `extracted_citation`'s act attribution is clearly broken — independent
  of evidence-matching outcome — via three distinct bug patterns in
  `claim_parser.py`: (1) a multi-act run-on sentence bleeding a later
  clause's act into an earlier citation (`2007_1517`, 5 claims); (2) a
  year mistaken for a provision number with the act wrongly
  field-inherited from an unrelated citation (`2003_967`, 1 claim); (3) a
  trim heuristic that fails to stop at the act name on certain phrasings,
  swallowing the rest of the sentence (`1989_184`, 2 claims); (4) the
  field-wide single-act fallback overriding an explicit in-sentence act
  attribution (`2023_26`, 7 claims — two of which then matched genuinely
  wrong-act evidence). Full detail: `assumption_annotation_summary.md`
  §"Extraction bugs found" and `assumption_vs_automated_report.md` §6.
  **No source code was changed to fix these** — they are flagged for a
  future `claim_parser.py` pass.
- **The NLI verifier disagrees with the (provisional) assumption reading
  on nearly half of evidence-matched claims (18/38, 47.4%)**, almost
  entirely in one direction: the model calls "neutral" a number of claims
  that a plain reading of the matched evidence text would call directly
  confirmed (16 cases) or directly conflicting (2 cases). This is a
  genuine candidate weakness in the small public NLI model used, worth
  a closer look, but should be read cautiously since the "assumption"
  side of this comparison is itself unverified.
- **Selective correction had zero measurable impact in this run because
  it never fired.** With 0 `CONTRADICTED` verdicts and every NEI verdict
  a genuine high-confidence neutral (none low-confidence-downgraded), the
  documented trigger conditions in `pipeline.py` were never met for any
  of the 88 real claims — this is a direct, mechanical consequence of the
  verifier's verdict distribution in section 2 above, not a separate
  finding about the corrector itself. The correction path (success,
  failure, and scope-violation handling) remains functionally untested
  end-to-end on real pipeline output; it has only been exercised by the
  mocked unit tests in `research/prototype/tests/`.
- **What must be re-evaluated once real lawyer annotations arrive:**
  everything in sections 2–5 above that currently relies on the
  assumption labels. Specifically: (a) whether the NLI model's "neutral"
  calls are actually right or wrong against real legal judgment — the
  disagreement analysis here only tells us the NLI model and Claude
  disagree with each other, not which one (if either) is correct; (b)
  whether `citation_valid`/`evidence_relevance` judgments made here hold
  up against a lawyer's reading of `claim_text`; (c) any future run where
  correction actually triggers, to see whether corrected output is closer
  to or further from the lawyer's judgment than the original; (d) whether
  the 15 flagged parser bugs, once fixed, change the evidence-coverage and
  verdict-distribution numbers materially.

## 6. Current Research Status

| Item | Status |
|---|---|
| Prototype implemented (`claim_parser.py`, `evidence_matcher.py`, `verifier.py`, `corrector.py`, `pipeline.py`) | ✅ Done |
| Docker reproducibility validated | ✅ Done |
| 30-case A/B/C evaluation completed (`run_A/B/C_n30.jsonl`, `eval_30_report.md`) | ✅ Done |
| Provisional Claude (assumption) annotation completed for all 88 claims | ✅ Done — `assumption_annotation.jsonl`, `lawyer_annotation.jsonl` (temporarily populated), this report |
| Lawyer annotation (real ground truth) | ⏳ Pending — `lawyer_annotation.jsonl` / `lawyer_annotation_guide.md` prepared and waiting on the annotated PDF |
| Final correctness metrics (citation validity, entailment accuracy, correction efficacy vs. real ground truth) | ⏳ Pending lawyer annotation — not measurable from assumption labels alone |
