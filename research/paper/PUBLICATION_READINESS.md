# Publication readiness and release checklist

**Repository state reviewed:** `research/lawyer-annotation-benchmark`  
**PR:** [#9](https://github.com/Nitin15122005/nyayamind-verification/pull/9)  
**Purpose:** distinguish work completed in code from work that requires independent human review or new evidence.

## Status summary

| Workstream | Status | Evidence / remaining action |
|---|---|---|
| Dataset import, schema validation, provenance hash | Implemented | Importer, tests, normalized summary |
| Duplicate and source-row diagnostics | Implemented | Importer summary and regression tests |
| Typed Act/provision alignment | Implemented with explicit exclusions | 220 unique; 30 ambiguous; 1 typed mismatch |
| Case-grouped majority baseline | Implemented | Five-fold OOF predictions and metrics |
| Structured verifier-signal experiment | Implemented; exploratory only | Separate three-class targets; paired case-cluster intervals |
| CI and artifact generation | Passing on recorded head | Run 42600428229; 33 tests passed |
| Manuscript draft | Drafted | `NYAYAMIND_BENCHMARK_STUDY_DRAFT.md` |
| Reproduction instructions | Existing documentation plus CI | Verify in a clean environment before archival release |
| Related-work bibliography | Starter references only | Complete systematic literature review |
| Human legal validation | **Blocked on independent reviewer** | Verify annotations, provision alignment, reviewer credentials |
| Annotation protocol and adjudication | **Blocked on source information** | Obtain reviewer instructions, number of reviewers, adjudication process |
| Inter-annotator agreement | **Not available** | Requires independent annotations before adjudication |
| Judgment texts and dates | **Not present in supplied dataset** | Obtain lawful access and add case/date-grounded evaluation |
| End-to-end verifier predictions against both lawyer targets | **Not yet evaluated** | Define prediction export contract and run on all eligible cases |
| External validation | **Not performed** | Collect a separate, non-overlapping set of judgments/cases |
| Ablation and robustness experiments | **Not performed** | Run pre-specified ablations and perturbation tests |
| Submission metadata | **Author action required** | Authors, affiliations, funding, conflicts, ethics and venue |

## Completed without external human review

- Dataset normalization and provenance tracking.
- Strict typed provision alignment and explicit ambiguity/mismatch states.
- Case-grouped out-of-fold majority baselines for both independent targets.
- Structured-signal evaluation, per-class metrics, and paired case-cluster bootstrap intervals.
- CI tests and reproducible artifact generation.
- Transparent reporting of negative/trade-off results and dataset limitations.
- Initial manuscript draft and this readiness ledger.

## Remaining work that can be done by the research team

These tasks do not require a legal reviewer, but they do require access to the original code/data and compute:

1. **End-to-end verifier evaluation:** export one prediction per annotation ID for each target. Do not infer lawyer labels from NLI classes. Compare against both targets separately using the existing grouped split and evaluation script.
2. **Baselines:** add a transparent lexical/rule baseline and, if technically comparable, an off-the-shelf legal-domain or general NLI baseline. Avoid comparing systems on different row subsets.
3. **Ablations:** predefine and remove one feature group at a time (typed provision/Act identity, evidence-match signals, NLI signals, confidence/model metadata). Keep the case folds fixed.
4. **Robustness:** evaluate paraphrases, misspelled/aliased Act names, Section/Rule swaps, absent evidence, amended/repealed statutory text, and conflicting candidate provisions. Report each slice separately.
5. **Error analysis:** generate a de-identified table of false positives, false negatives, and partially-correct cases; manually inspect examples only as engineering analysis, not as legal adjudication.
6. **Reproduction audit:** run all documented commands from a clean checkout and verify artifact hashes, package versions, seeds, and expected output counts.
7. **Literature review:** expand beyond FEVER, LexGLUE, and LegalBench to Indian legal NLP, statute retrieval, citation resolution, and legal hallucination evaluation. Record search dates and inclusion criteria.
8. **Submission packaging:** finalize authorship, affiliations, funding, conflict-of-interest, ethics, data availability, and venue formatting.

## Human-review gate (intentionally not completed)

An independent qualified reviewer must:
- inspect a sample or all annotations and typed provision alignments;
- verify whether the annotation rubric is legally coherent and consistently applied;
- document reviewer qualifications and the number of annotators;
- adjudicate disagreements and explain the adjudication process;
- assess the LR-0232 discrepancy and ambiguous rows;
- determine whether original judgment text/date evidence is required for each label;
- approve any legal interpretation or legal-validity claims in the manuscript.

Do not manufacture reviewer identities, agreement statistics, adjudication outcomes, or legal sign-off.

## Publication claims permitted by current evidence

Permitted:
- “The prototype performs statutory claim extraction, typed provision matching, evidence retrieval, and NLI classification.”
- “The benchmark contains 251 claim–provision assessment rows from 45 cases.”
- “The structured-signal models achieved the reported annotation-agreement metrics on 220 uniquely aligned rows across 44 cases.”
- “The models had higher macro-F1 but lower accuracy than the same-subset majority baseline in this experiment.”

Not supported:
- “NyayaMind achieves X% legal accuracy.”
- “The model is validated by lawyers” without documented independent review.
- “The dataset has high inter-annotator agreement.”
- “The system detects all statutory hallucinations.”
- “The model generalizes to Indian judgments” without external validation.
- “The correction module reliably fixes legal errors.”

## Release decision

**Current decision: do not mark publication-ready and do not convert PR #9 from draft.** The repository can be shared as a transparent prototype/benchmark-tooling artifact with its limitations. A paper may be circulated internally as a draft, but formal submission should wait for the human-review gate and the remaining empirical work above.
