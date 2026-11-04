# Publication-readiness programme — NyayaMind

Status: work programme opened 2026-11-04 on branch `publication/readiness-engineering`.
Baseline preserved at `backup/pre-publication-baseline-2026-11-04`.
This programme does not imply that any validation below has already passed.

## Objective and publication standard

Prepare a defensible research paper and reproducible research artifact for the narrow task
actually implemented: verification and selective correction of statutory-grounding claims
in LLM-generated Indian case-summary fields. Do not claim general legal reasoning, legal
advice, lawyer validation, universal legal correctness, or broad generalization.

A publication-ready result requires (i) a sound research question and contribution,
(ii) independently defensible labels and evaluation, (iii) leakage-resistant experimental
design, (iv) transparent baselines and ablations, (v) safety and failure analysis,
(vi) reproducible code/data/model provenance, and (vii) a manuscript whose claims match
the evidence. Passing unit tests alone is not publication readiness.

## Non-negotiable preservation rules

- Do not alter `main`, the baseline backup branch, the frozen LegalSeg submodule, the
  historical `outputs/` lab notebook, archived packages, or canonical evidence JSONL
  without an explicit, separately reviewed change proposal.
- Keep production defaults unchanged until a proposed change has tests, a paired evaluation,
  a safety analysis, and a recorded decision.
- Keep negative/null findings. Never delete inconvenient runs or overwrite historical data.
- Never describe rule-generated labels as lawyer annotations or natural-data coverage as
  accuracy.
- Never claim legal correctness or lawyer validation before qualified review.
- All new runs get unique names, metadata, seeds, input hashes, config snapshots, and logs.

## Workstreams and acceptance gates

### A. Research question, novelty, and contribution
- Reconstruct the target task, intended users, threat model, and exact unit of analysis.
- Separate claim extraction, citation resolution, evidence sufficiency, NLI classification,
  correction, and safe abstention as distinct subproblems.
- Compare the contribution against current legal NLP, RAG verification, citation checking,
  NLI, selective prediction, and LLM self-correction literature.
- State a falsifiable primary hypothesis and pre-register primary outcomes before new runs.
- Gate: a contribution matrix with closest prior work, exact delta, evidence, and limitations.

### B. Dataset and annotation validity
- Audit case-source provenance, selection procedure, duplicates, case overlap, temporal span,
  court/Act distribution, and representativeness.
- Separate source text, generated claims, extracted claims, retrieved evidence, labels, and
  adjudicated outcomes; preserve immutable IDs and hashes.
- Design a lawyer annotation protocol for evidence correctness, temporal applicability,
  entailment/contradiction/insufficiency, and correction acceptability.
- Obtain independent annotations and adjudicate disagreements; report agreement and class
  prevalence. No lawyer work is assumed complete.
- Gate: documented dataset card, annotation handbook, blind split policy, and provenance
  ledger.

### C. Evidence corpus and legal versioning
- Validate JSONL parseability, schema, key uniqueness, canonical/audit joins, source URLs,
  exact-index collisions, and v0/v1 merge semantics.
- Distinguish direct verbatim source retrieval, paraphrase/synthesis, and independent
  re-fetch audit. A provenance label is not a substitute for content checking.
- Build a date-aware statute-version model: enactment, amendment, commencement, repeal,
  savings/transitional clauses, and case-date applicability.
- Prefer official Gazette/India Code/legislative sources where accessible; record third-party
  source limitations explicitly.
- Gate: machine audit report plus independent source audit; unresolved records remain unusable.

### D. Parser and retrieval validity
- Create a gold parser set with citation spans, claim spans, provision identity, subsection,
  Act/year, multi-citation relationships, and abstention/ambiguity labels.
- Report exact-match precision/recall/F1, span overlap, unresolved rate, and wrong-Act rate.
- Test adversarial citation forms: abbreviations, aliases, OCR/noise, multi-Act bundles,
  same-number cross-Act collisions, historical enactments, ranges, provisos, and malformed refs.
- Compare retrieval against meaningful baselines (exact lookup, current Jaccard, BM25,
  dense retrieval, hybrid) under a fixed candidate set and report wrong-evidence retrieval,
  not just recall.
- Gate: held-out, independently labeled parser/retrieval benchmark with confidence intervals.

### E. Verifier evaluation
- Reassess GOLD-01 construction for premise/hypothesis dependence, templating artifacts,
  class balance, duplicate templates, and train/evaluation contamination.
- Treat rule-generated labels as controlled diagnostic labels, not legal ground truth.
- Build a lawyer-reviewed natural claim set; freeze split by case (not claim) to avoid
  within-case leakage.
- Report per-class precision/recall/F1, macro-F1, confusion matrix, calibration, selective
  risk/coverage, abstention quality, and paired confidence intervals.
- Compare at least the production DeBERTa verifier with transparent baselines and a
  second materially different verifier; tune only on validation data.
- Gate: primary evaluation on blind test set with pre-registered metrics.

### F. Correction and safety
- Define what counts as a shipped correction and a safe correction before evaluating.
- Measure correction success, preservation of unflagged content, citation additions,
  statutory meaning, sibling regression, abstention, and unsafe acceptance.
- Add red-team cases for negation, exceptions/provisos, temporal mismatch, wrong Act,
  fabricated citations, partial section text, contradictory authorities, multi-claim
  sentences, prompt injection in case text/evidence, and low-confidence evidence.
- Compare no-correction, legacy correction, and any experimental correction in paired tests.
- Gate: no unsafe behavior in defined tests is reported with denominator and scope; never
  infer zero risk from zero observed failures.

### G. Statistics and experimental design
- Pre-register primary and secondary endpoints, inclusion/exclusion rules, sample sizes,
  seeds, and stopping rules.
- Use case-level grouping, deduplication, paired tests where appropriate, confidence
  intervals, effect sizes, and correction for multiple comparisons.
- Perform power/sample-size analysis for the primary comparison.
- Keep exploratory analyses separate from confirmatory results.
- Gate: reproducible analysis script and full experiment manifest.

### H. Systems engineering and reproducibility
- Add CI for CPU-only tests, static checks, corpus integrity, config validation, and artifact
  consistency. Keep GPU tests separately marked and documented.
- Pin model revisions/commit hashes, tokenizer revisions, package lock/environment, CUDA,
  driver, hardware, prompts, decoding settings, and random seeds.
- Test clean-checkout setup, documented commands, offline/online behavior, failure modes,
  memory limits, and deterministic re-verification.
- Add structured logs, stable run IDs, schema versions, and machine-readable outputs.
- Gate: clean environment reproduction by a second person/machine.

### I. Manuscript and release
- Rebuild paper claims directly from canonical metric artifacts; no manually typed numbers.
- Include limitations, error taxonomy, ethical/legal-risk statement, dataset/model cards,
  and reproducibility statement.
- Audit every table, figure, denominator, p-value, citation, and cross-reference.
- Freeze submission commit/tag and archive exact supplementary artifacts.
- Gate: internal technical review, supervisor review, and legal review of legal-content claims.

## Immediate implementation order

1. Run and preserve the structural corpus audit; inspect all findings.
2. Reconcile documentation drift (notably old test-count statements) without rewriting
   historical experiment records.
3. Build a publication audit report with each claim linked to source artifacts and exact
   denominators.
4. Add CI and independent validation scripts.
5. Design the blind lawyer annotation protocol and natural test set.
6. Execute parser/retrieval/verifier/correction evaluations in that order.
7. Revise the manuscript only after the evaluation design and evidence are frozen.

## Known issues observed at programme start

- `REPRODUCIBILITY.md` still states an expected 205 tests in one section, while current
  project context reports 302; this is documentation drift to reconcile.
- The evidence corpus has 63 v0 and 82 v1 source rows, with 59 and 78 usable audit verdicts
  respectively before merge/supersession semantics. The loader's actual merged count must be
  measured, not inferred by adding those counts.
- v1 audit history includes an original 8/82 spot check and a later 41/82 independent
  re-fetch addendum. It must not be described as exhaustive re-fetch of all 82.
- GOLD-01's high verifier score is tied to a controlled, mechanically labeled construction;
  its interpretation and possible framing/template dependence require a fresh leakage audit.
- The existing 302-test count is documented but has not been rerun by this work programme yet.
- Docker remains environment-blocked in the documented development environment.

## Change log

- 2026-11-04: programme created on isolated publication branch; no production code/config or
  frozen research data changed by this document.


## Code-side publication tooling added on 2026-11-04

The following tooling is implemented on the isolated `production-hardening-2026-11-04` branch and included in draft PR #8. It is code preparation, not evidence that annotation or legal validation has been completed.

- `research/prototype/scripts/publication_annotation.py`: blind GOLD-03 reviewer packet creation, source SHA-256 manifest, strict independent-review merge, adjudication validation, Cohen's kappa and class counts; natural-case export plus separate double-review packets and merge.
- `research/prototype/scripts/evaluate_natural_annotations.py`: joins adjudicated natural annotations to the exact archived pipeline run by document/claim ID; reports per-class precision/recall/F1, confusion matrix, evidence coverage, and document-cluster bootstrap intervals. NO_EVIDENCE is reported separately rather than relabelled as NOT_ENOUGH_INFORMATION.
- Tests: `test_publication_annotation.py` and `test_evaluate_natural_annotations.py`.
- Operator instructions: `research/prototype/PUBLICATION_ANNOTATION_WORKFLOW.md`.

### Remaining non-code actions

1. Independently draft citation-free GOLD-03 claims from source provisions; the existing worksheet deliberately does not generate semantic claims or labels.
2. Have two independent reviewers annotate, then adjudicate; freeze the dataset and record reviewer roles and agreement.
3. Review natural claims against authoritative statutory text and applicable historical versions; adjudicate the claim labels.
4. Populate only source-verified effective-date intervals and explicit judgment dates.
5. Pin verified model commit SHAs and perform a clean-checkout/full-model reproduction.
6. Run and inspect the latest CI suite and all model integration checks before merging PR #8.

The evaluator, annotation tools, and CI are not substitutes for those steps. Historical data and GOLD-01 remain unchanged.
