# NyayaMind: Typed Statutory-Grounding Verification for AI-Generated Legal Summaries

**Manuscript status:** internal research draft; not submission-ready pending the gates in `PUBLICATION_READINESS.md`.

**Authors:** [Complete author names, affiliations, and contribution statements before submission]

## Abstract

AI-generated summaries of judicial decisions can contain statutory references that are imprecise, mismatched, or unsupported by the cited legal text. We describe NyayaMind, a prototype pipeline for checking statutory grounding in generated legal summaries. The pipeline combines claim extraction, typed provision matching, retrieval of canonical statutory text, and natural-language-inference (NLI) classification. We also report an exploratory analysis of a lawyer-reviewed dataset containing 251 claim–provision assessment rows from 45 cases. The dataset supplies two distinct three-class judgments: statement correctness and legal-reference correctness. We audit record alignment before evaluation and restrict structured-signal modelling to 220 uniquely aligned rows across 44 cases. Under five-fold case-grouped cross-validation, structured-signal models obtain macro-F1 of 0.4016 for statement correctness and 0.4212 for legal-reference correctness, while their accuracies (0.4227 and 0.4500) are below same-fold majority baselines (0.5818 and 0.6000). Paired case-cluster bootstrap intervals indicate higher macro-F1 but lower accuracy than the majority comparator on this selected subset. These results are exploratory agreement measurements against supplied annotations, not estimates of legal accuracy. The source workbook does not contain the original judgments or judgment dates, and independent legal review and external validation have not been completed. We therefore present the work as a prototype and evaluation study, not as a validated legal decision-support system.

**Keywords:** legal NLP; statutory grounding; claim verification; evidence retrieval; natural language inference; Indian law; evaluation methodology

## 1. Introduction

Large language models can produce fluent summaries while misstating the legal authority supporting a proposition. Statutory-grounding verification is narrower than evaluating the correctness of an entire judgment summary: it asks whether an extracted proposition is supported by the identified statutory provision and whether the provision reference is correctly typed and identified.

NyayaMind addresses this narrower task through a staged pipeline. The system extracts citation-bearing claims, resolves Act and provision identifiers, retrieves statutory text, and applies an NLI classifier to the claim–evidence pair. The design separates record linkage and provision identity from semantic inference. In particular, a Section/Rule mismatch must not be silently repaired by textual similarity.

This study has two objectives: (1) describe the prototype's statutory-grounding workflow and its explicit limits; and (2) document an initial, case-grouped evaluation against a lawyer-reviewed annotation workbook, including strict alignment and exploratory structured-feature results.

The study does not claim that an NLI label establishes legal truth, that annotation agreement equals legal accuracy, or that the current benchmark establishes case-specific statutory applicability.

## 2. System overview

### 2.1 Pipeline

The prototype workflow is:

1. Generate legal-summary text using Qwen2.5-7B.
2. Extract citation-bearing claims using a deterministic claim parser.
3. Match Act names and typed provision identifiers against canonical statutory records.
4. Retrieve the candidate statutory text.
5. Apply DeBERTa-v3-base in an NLI configuration to classify the claim–evidence relationship.
6. In a separate correction mode, selectively propose corrections for flagged claims subject to scope and safety constraints.

Detection and correction are separate functions. An NLI classification is a model output about the supplied text pair; it is not a legal conclusion. Correction is not assumed to follow automatically from detection.

### 2.2 Typed statutory identity

A statutory reference is represented using at least the Act identity, provision type (for example, Section or Rule), and provision identifier. A reference-text similarity signal cannot override a typed identifier mismatch. The audit retains such mismatches as explicit discrepancies rather than coercing one provision type into another.

### 2.3 NLI labels and legal annotations

The NLI output space (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, NO_EVIDENCE) is not mapped to the lawyer annotation labels (Yes, No, Partially). The latter are supplied separately for statement correctness and legal-reference correctness. These two annotation targets remain independent.

## 3. Dataset

The lawyer-reviewed workbook contains 251 claim–provision assessment rows from 45 unique cases and 81 unique legal statements. It provides two separate three-class targets:

| Target | Yes | No | Partially |
|---|---:|---:|---:|
| Statement correctness | 43 | 73 | 135 |
| Legal-reference correctness | 150 | 26 | 75 |

The unit of analysis is a claim–provision assessment row. There are 241 unique case–statement–provision tuples. Repeated tuples are retained and diagnosed rather than indiscriminately removed because duplicate rows are not necessarily identical annotations.

The source workbook's SHA-256 is `7daca97c77f58d2e2d2c9806458de1632d5ea7cf3e8afdfa8aa9b7d753d48c`. The normalized dataset and its provenance summary are generated by the repository importer. The data owner has confirmed permission to redistribute the workbook and annotations; reviewer metadata and confidential notes must still be checked before wider release.

### 3.1 Dataset limitations

The workbook does not contain original judgment texts or judgment dates. Accordingly, the annotations cannot independently establish whether a provision was relevant to the particular case, whether the provision was in force on the relevant date, or whether the source judgment itself supports the annotation. Annotation instructions, reviewer qualifications, adjudication procedures, and inter-annotator agreement are not sufficiently documented to report those quantities.

## 4. Alignment audit

The alignment audit is performed before feature evaluation. On the current regenerated audit:

- 251/251 rows have a corresponding case in model outputs and an exact legal-statement text match.
- 220 rows have a unique typed provision/Act-compatible alignment.
- 30 rows have multiple compatible reference-aligned candidates and remain ambiguous.
- One row (LR-0232) is a typed Section-versus-Rule discrepancy: the annotation identifies Code of Criminal Procedure 1973, Section 3, while the generated claim identifies Rule 3. This is retained as a typed mismatch, not an exact match.
- No unmatched reference-alignment rows remain after the typed-mismatch state is represented explicitly.

The structured-signal experiment uses only the 220 uniquely aligned rows across 44 cases. Ambiguous rows and the typed mismatch are excluded. This eligibility filter limits the scope of inference: results do not automatically generalize to unmatched or ambiguous claims.

## 5. Evaluation methodology

### 5.1 Majority reference baseline

For each lawyer target independently, a five-fold StratifiedGroupKFold procedure groups all rows from a case (`case_reference`) into one fold. Each held-out row receives the majority label from that fold's training partition. The baseline is a reference floor, not a NyayaMind model.

### 5.2 Structured verifier-signal experiment

A separate three-class logistic-regression model is trained for each target using structured verifier and retrieval metadata: provision type, Act match, evidence matching method, NLI verdict, verifier model, evidence presence, provision-identifier match, reference-text match, confidence, and number of distinct statement matches.

The feature set excludes case identifiers, annotation identifiers, raw legal-statement text, correction/clarification text, supporting legal authority, and annotation-derived audit conclusions. Evaluation uses five-fold StratifiedGroupKFold grouped by case. The same eligible rows and fold policy are used for both targets. A same-fold majority comparator is evaluated on the same subset.

### 5.3 Metrics and uncertainty

We report accuracy, macro-F1, and per-class precision, recall, F1, and support. Confidence intervals are case-cluster percentile bootstrap intervals (2,000 replicates; seed 20261109). Paired bootstrap intervals resample the same cases for the structured model and majority comparator and report model-minus-majority differences. The paired bootstrap is conditional on fixed out-of-fold predictions; it does not retrain the models inside each replicate.

## 6. Results

### 6.1 Structured-signal model versus same-subset majority baseline

| Target | Model accuracy (95% CI) | Model macro-F1 (95% CI) | Majority accuracy | Majority macro-F1 | Paired accuracy difference (95% CI) | Paired macro-F1 difference (95% CI) |
|---|---:|---:|---:|---:|---:|---:|
| Statement correctness | 0.4227 [0.3452, 0.5388] | 0.4016 [0.3298, 0.5029] | 0.5818 | 0.2452 | -0.1591 [-0.2919, -0.0209] | +0.1564 [+0.0538, +0.2593] |
| Legal-reference correctness | 0.4500 [0.3110, 0.5377] | 0.4212 [0.2898, 0.5051] | 0.6000 | 0.2500 | -0.1500 [-0.3010, -0.0238] | +0.1712 [+0.0702, +0.2598] |

On this selected subset, the structured models have higher macro-F1 but lower accuracy than the majority comparator. The paired accuracy-difference intervals are below zero, while the paired macro-F1-difference intervals are above zero. This is a minority-class trade-off, not an unqualified performance improvement.

### 6.2 Per-class results

| Target | Class | Precision | Recall | F1 | Support |
|---|---|---:|---:|---:|---:|
| Statement correctness | Yes | 0.2286 | 0.3902 | 0.2883 | 41 |
| Statement correctness | No | 0.3731 | 0.4902 | 0.4237 | 51 |
| Statement correctness | Partially | 0.6265 | 0.4063 | 0.4929 | 128 |
| Legal-reference correctness | Yes | 0.6346 | 0.5000 | 0.5593 | 132 |
| Legal-reference correctness | No | 0.3500 | 0.9130 | 0.5060 | 23 |
| Legal-reference correctness | Partially | 0.2143 | 0.1846 | 0.1983 | 65 |

The legal-reference model has weak recall for Partially. The modest number of cases and the strict alignment-based subset selection limit the strength and generalizability of these findings.

## 7. Discussion

The experiments show why accuracy alone is insufficient for this imbalanced three-class task: a majority comparator has higher accuracy, while the structured models obtain higher macro-F1. The result does not justify claiming that the structured model is superior overall. The low recall for the Partially class in legal-reference correctness is a material weakness.

The typed alignment audit is an important methodological safeguard. A superficially similar reference string must not convert a Rule into a Section. Likewise, exact statement matching is insufficient when multiple claims share statement text but differ in provision identity.

The present evaluation is not an end-to-end test of the full NyayaMind verifier against lawyer labels. It is an exploratory structured-metadata experiment on a selected subset. No lawyer-target fine-tuning or external validation has been performed. The current dataset also cannot support claims about case-specific relevance or historical statutory applicability.

## 8. Related work

Fact verification research commonly separates evidence retrieval from claim verification. FEVER introduced a large-scale evidence-grounded fact-verification benchmark with Supported, Refuted, and NotEnoughInfo labels (Thorne et al., 2018). Legal-domain benchmarks such as LexGLUE standardize evaluation across legal language-understanding tasks (Chalkidis et al., 2022), while LegalBench assembles tasks intended to measure legal reasoning capabilities in language models (Guha et al., 2023).

NyayaMind addresses a narrower operational problem: checking the statutory grounding of claims in generated legal summaries, with explicit typed provision identity and a separation between statement correctness and reference correctness. This positioning should be treated as a task distinction, not a novelty claim. A final submission requires a broader and systematic review of Indian legal NLP, statutory retrieval, legal citation resolution, and legal hallucination detection.

## 9. Limitations and responsible use

1. The benchmark has 251 rows but only 45 cases; the effective independent case count is small.
2. The source workbook lacks original judgments and dates, preventing independent assessment of case relevance and historical applicability.
3. Annotation methodology, reviewer qualifications, adjudication, and inter-annotator agreement are not documented sufficiently for publication claims.
4. The structured experiment excludes ambiguous and typed-mismatch rows and therefore evaluates a selected subset.
5. The structured experiment is not end-to-end verifier evaluation and has no external test set.
6. No lawyer-target fine-tuning was performed.
7. NLI outputs are not legal truth labels. Annotation agreement is not legal accuracy.
8. The correction component has not demonstrated reliable scalable correction and should not be represented as an autonomous legal editor.
9. The system is a research prototype, not a substitute for legal research, professional judgment, or review by a qualified lawyer.

## 10. Conclusion

We describe a prototype for statutory-grounding checks in AI-generated legal summaries and an initial case-grouped analysis of lawyer-reviewed annotations. The audit and evaluation tooling enforce strict typed provision alignment and keep statement correctness separate from legal-reference correctness. Exploratory structured-signal models trade lower accuracy for higher macro-F1 relative to same-subset majority baselines. The current evidence supports a transparent prototype and benchmark-methodology report, but not a claim of legal accuracy, external validity, or production readiness. Independent legal review, annotation-process documentation, end-to-end evaluation, and external validation remain necessary.

## References

- Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos, I., Katz, D., & Aletras, N. (2022). *LexGLUE: A Benchmark Dataset for Legal Language Understanding in English*. Proceedings of ACL 2022, 4310–4330. https://doi.org/10.18653/v1/2022.acl-long.297
- Guha, N., Nyarko, J., Ho, D. E., Ré, C., Chilton, A., et al. (2023). *LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models*. Advances in Neural Information Processing Systems 36. https://doi.org/10.52202/075280-1915
- Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). *FEVER: A Large-scale Dataset for Fact Extraction and VERification*. Proceedings of NAACL-HLT 2018, 809–819. https://doi.org/10.18653/v1/N18-1074

## Author completion before submission

- Replace author placeholders and add affiliations, corresponding author, and contribution statements.
- Verify every technical statement against the frozen code and artifacts.
- Expand related work with a systematic search and discuss jurisdiction-specific Indian legal NLP.
- Add a system architecture figure and an error-analysis table generated from reviewed examples.
- Add venue-specific formatting, ethics statement, data availability statement, and any required conflict/funding statements.
- Do not remove the limitations or convert annotation-agreement results into legal-accuracy claims.
