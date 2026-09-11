# assertion_span_primary_hypothesis benchmark: claim_text vs. assertion_spans-based hypothesis

_Generated 2026-09-11T16:36:43.436935+00:00_

**Verification-only re-scoring of every real 'respectively'-pattern claim found across every committed outputs/*.jsonl file**, under the current production "labeled" premise framing. Nothing regenerated; only claim_parser/evidence_matcher (already run, read from committed records) + real DeBERTa verification run fresh, on CPU.

> Verdicts are a small public NLI model's output against this corpus. They are not legal-correctness determinations, and no lawyer ground truth exists.

- Unique real 'respectively'-pattern claims found and scored: **6**

## Verdict distribution

| Verdict | BASELINE (claim_text) | SPAN (assertion_spans-based) |
|---|---|---|
| ENTAILED | 0 | 3 |
| CONTRADICTED | 0 | 1 |
| NOT_ENOUGH_INFORMATION | 6 | 2 |

## Claims that changed verdict (4 / 6)

- NEI -> ENTAILED (candidate coverage win): **3**
- NEI -> CONTRADICTED (candidate new correction trigger): **1**
- ENTAILED -> CONTRADICTED (**safety-relevant reversal**): **0**
- CONTRADICTED -> ENTAILED (**safety-relevant reversal**): **0**

None. No claim reversed between the two safety-relevant labels (ENTAILED<->CONTRADICTED) anywhere in this dataset.

### NEI -> ENTAILED cases (3 of 3, inspect for spurious entailment)

- **Article 14 in Constitution of India** (final_gpu_validation_A.jsonl/2002_731)
  - claim_text: The case involves the interpretation of Articles 14, 15, and 16 of the Constitution of India, which require equality before the law, prohibit discrimination on certain grounds, and provide for equalit
  - span_hypothesis: Article 14 require equality before the law
  - confidence: 0.993 -> 0.868
  - Manually inspected: genuine, not spurious -- Article 14's real text is exactly "equality before the law".
- **Article 15 in Constitution of India** (final_gpu_validation_B.jsonl/2002_731)
  - claim_text: The case involves the interpretation of Articles 14, 15, and 16 of the Constitution of India, which require equality before the law, prohibit discrimination on certain grounds, and provide for equalit
  - span_hypothesis: Article 15 prohibit discrimination on certain grounds
  - confidence: 0.961 -> 0.985
  - Manually inspected: genuine, not spurious.
- **Section 302 in The Indian Penal Code, 1860** (natural_candidates_batch2_gpu_bare.jsonl/1975_28)
  - claim_text: Statutory Grounding: The case is grounded in Sections 302 and 149 of the Indian Penal Code, which respectively provide for murder and criminal conspiracy.
  - span_hypothesis: Section 302 provide for murder
  - confidence: 0.993 -> 0.983
  - Manually inspected: genuine, not spurious.

### NEI -> CONTRADICTED case (1 of 1) -- a genuine, positive finding

- **Section 27 in The Indian Evidence Act, 1872** (final_gpu_validation_A.jsonl/1997_1005-ish)
  - claim_text: "...Sections 54, 9, and 27 of the Indian Evidence Act, which govern the admissibility of evidence, the recording of statements of witnesses, and the identification of persons by sight, respectively."
  - span_hypothesis: "Section 27 the identification of persons by sight"
  - confidence: NOT_ENOUGH_INFORMATION 0.973 -> CONTRADICTED 0.992
  - **Manually inspected: this is a real generation error the diluted full-sentence hypothesis had
    masked.** Section 27 of the Indian Evidence Act is actually about facts discovered in
    consequence of information received from an accused in custody (confession-derived discovery),
    NOT "identification of persons by sight" -- the generator misattributed which topic belongs to
    which section. The narrower hypothesis correctly surfaces this as CONTRADICTED; the baseline
    full-sentence hypothesis (diluted by the other two citations' unrelated content) had let it slip
    through as NEI. This is exactly the mechanism this lever is meant to provide.

## Statistical analysis

Not computed. n=6 is far below any threshold where a paired test (e.g. McNemar) would be
meaningful -- with this few discordant pairs, any p-value would be an artifact of sample size, not
evidence of a real effect. Reporting a significance figure here would overstate the evidence.

## Honest verdict

**Directionally positive, but statistically INCONCLUSIVE at n=6.** Every one of the 4 changed
verdicts was manually inspected and found genuine (3 correct ENTAILED recoveries, 1 correct
CONTRADICTED catch of a real generation error) -- zero spurious entailments, zero unsafe
ENTAILED<->CONTRADICTED reversals. This pattern is fully consistent with Stage 4's much larger
(n=456/107 applicable) validated result for the sibling `narrow_primary_hypothesis` lever. However,
n=6 is the ENTIRE population of real evidence-matched "respectively"-pattern claims found across
every committed experiment in this project's history -- there is no larger real sample available
without running fresh GPU generation specifically targeting cases likely to produce this pattern
(which the generator produces rarely and unpredictably). **Not promoted to production default this
pass** -- `assertion_span_primary_hypothesis` remains `false` in `config/prototype.yaml`, pending
either (a) a larger sample from future natural-data experiments naturally accumulating more
"respectively"-pattern claims, or (b) a deliberately-targeted synthetic/controlled benchmark
(analogous to `build_controlled_benchmark.py`) built specifically to stress-test this construction
at a meaningful sample size. This is a case where declining to flip a default despite a clean
positive signal is the correct call, precisely because the task's own research-integrity rule is
"if a sample is too small, explicitly call it inconclusive" -- not "round up to a decision anyway."

## Addendum (2026-09-11) — implementation audit beyond the n=6 benchmark

Before accepting the n=6 result above, the mechanism itself was adversarially stress-tested with
5 new end-to-end tests (`tests/test_assertion_span_primary_hypothesis.py::TestEndToEndAdversarialCoverage`),
covering negation, modal/exception clauses, three-citation lists, and structurally ambiguous input
-- not just trusting the aggregate 4/6 number. Summary (full detail in
`FINAL_PRODUCTION_CONFIG.md` §5a):

- Negation in a respectively item ("do not require proof of premeditation") survives verbatim,
  never silently inverted.
- Modal/exception clauses ("...unless...", "...after...") survive intact.
- Structurally ambiguous/malformed "respectively" sentences fail closed -- `_assertion_spans_hypothesis()`
  returns `None` rather than ever building a hypothesis from a wrong or partial pairing.
- One real, non-bug nuance found: verb-phrase stripping (`_KNOWN_VERB_PREFIX_RE`) only ever applies
  to the FIRST item in a list (a genuinely shared prefix); later items keep their own distinct verbs.
  This varies hypothesis richness by sentence shape but was empirically verified safe on real
  DeBERTa (CPU): both verb-less and verb-ful phrasings of the same proposition fail toward
  NOT_ENOUGH_INFORMATION when unsupported, never toward a false ENTAILED/CONTRADICTED.

**Conclusion: the implementation does what it claims and has no found safety defect.** The
decision to withhold production promotion remains about sample size (n=6), not implementation
quality -- these findings do not change the "not adopted" decision above, they support it being a
sample-size decision rather than a hidden-correctness concern.
