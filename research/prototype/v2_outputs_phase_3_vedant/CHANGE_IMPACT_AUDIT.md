# CHANGE IMPACT AUDIT — ORIGINAL NyayaMind → LATEST NyayaMind

**V2 package · generated 2026-09-18 · repository `nyayamind-verification`**

Every meaningful change between the original codebase (`0e37525`, 2026-08-13) and HEAD
(`fb4e98f`, 2026-09-12), traced from git history. **47 changes** across 21 commits — of which
only 10 commits touched `src/` at all; the rest are documentation, figures and evaluation
workspace.

Machine-readable version: `metrics/change_inventory.csv` (same 47 rows, all columns).

---

## Summary

| Status | Count | Meaning |
|---|---:|---|
| **PROMOTED_PRODUCTION** | 29 | Live in the LATEST system. |
| **EXPERIMENTAL_NOT_PROMOTED** | 4 | Built and evaluated, deliberately OFF in production. Never describe these as production behaviour. |
| **EVALUATED_AND_REJECTED** | 1 | Built, benchmarked, and actively rejected on measured grounds. |
| **INFRASTRUCTURE_ONLY** | 10 | Tooling, loading mechanics or experiment scaffolding. No behavioural claim attaches. |
| **DOCS_ONLY** | 3 | Documentation. No code behaviour changed. |
| **TOTAL** | 47 | |

| Evidence grade | Count |
|---|---:|
| BEHAVIORAL | 18 |
| HISTORICAL | 12 |
| DETERMINISTIC_SYNTHETIC | 8 |
| GOLD | 4 |
| ENGINEERING | 2 |
| NOT_APPLICABLE | 2 |
| NOT_MEASURED | 1 |

- **11** changes are corroborated by an experiment **re-executed fresh for this package**.
- **1** change has **no measuring experiment at all** — listed in full in §3, alongside those covered by regression tests only.

### How the evidence grade is assigned (by rule, not by impression)

| Rule | Grade |
|---|---|
| Measured on a gold-labelled benchmark (GOLD-01) | `GOLD` |
| Measured on deterministically-constructed data or by deterministic re-execution | `DETERMINISTIC_SYNTHETIC` |
| Measured on a pre-registered adversarial set | `BEHAVIORAL` |
| Qwen-dependent and/or natural unlabelled data (not rerunnable here) | `HISTORICAL` |
| Covered by regression tests only, with no data-batch measurement | `ENGINEERING` |
| Nothing measures it | `NOT_MEASURED` |
| Docs/infrastructure, no behavioural claim | `NOT_APPLICABLE` |

> **Grade measures how well a change is EVIDENCED — isolation, sample size, statistical
> support. It never measures effect size, and it is never a quality ranking.**

---

## 1. Audit table

### PROMOTED_PRODUCTION (29)

*Live in the LATEST system.*

| ID | Component | Original behaviour | Problem | Modification | Latest behaviour | Grade |
|---|---|---|---|---|---|---|
| `CHG-01` | Claim parser - run-on multi-act sentence (act-bleed) | CITATION_REGEX act group greedy up to the next '.'/';'; _trim_act_name returned only a string; scan continued… | IPC sections 120-B/471/477 got the merged two-act act_norm 'the Indian Penal Code and Section 5(2) ... Preven… | 223eb9d research/prototype/src/claim_parser.py: _EMBEDDED_CITATION_RE, _trim_act_name -> (name… | Each citation in a run-on sentence keeps its own clean act_norm; the embedded second citation is re… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-02` | Claim parser - act-name trim heuristics (continuation verbs) | _ACT_CONTINUATION_VERBS held only 3rd-person-singular verbs; first-match-wins trim order (year -> verb -> com… | Plural-subject phrasing ('Sections 25 and 27 of the Arms Act require ...') and copula phrasing ('the Evidence… | 223eb9d (base/plural forms) and 100e263 ('pertains'/'pertain', copulas is/are/was/were) resear… | Act capture stops at plural, 'pertain' and copula continuations; cut candidates are earliest-wins,… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-03` | Claim parser - bare year mistaken for a provision number | BARE_CITATION_REGEX emitted any '<keyword> <number>' pair, including 'Regulations 2000' | 'the Post Graduate Medical Education Regulations 2000' parsed as provision_type=Regulation, provision_number=… | 223eb9d research/prototype/src/claim_parser.py: _PLAUSIBLE_YEAR_RE applied only on the BARE_CI… | A bare '<keyword> YYYY' with no act clause of its own is dropped, never emitted as a citation | `DETERMINISTIC_SYNTHETIC` |
| `CHG-04` | Claim parser - act resolution for bare citations | _sentence_level_act(sentence) resolved a bare citation only if the whole sentence contained exactly ONE disti… | Field-wide single-act fallback overrode an explicit in-sentence act (doc 2023_26, A0073-A0080); truncated sub… | 223eb9d research/prototype/src/claim_parser.py: _sentence_level_act(sentence, citation_pos) =… | Nearest-preceding same-sentence act wins; field-wide inheritance is 2-step and declines when ambigu… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-05` | Claim parser - acronym / act-alias normalization | normalize_act() only lowercased, stripped a leading 'The', stripped periods/commas and collapsed whitespace | 'IPC', 'CrPC', 'CPC', 'the Indian Penal Code (IPC)' and 'Evidence Act' never compared equal to the corpus's f… | 223eb9d (aliases + _ABBREVIATION_PAREN_RE) and 100e263 ('evidence act') research/prototype/src… | A closed, symmetric alias table (applied to both claim and corpus act names via data_loader) plus p… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-06` | Claim parser - 'Part <roman>' qualifier | No handling of 'Section 304, Part II of the IPC'; 'Part' is Title-Case so it satisfied _BARE_ACT_MENTION_RE's… | 'Part II of the Indian Penal Code' was captured as if it were the ACT name; the Part-qualified citation's act… | 100e263 research/prototype/src/claim_parser.py (_PART_QUALIFIER_PATTERN, _PART_QUALIFIER_RE, p… | The Part qualifier is consumed by the citation grammar and attached as subsection only when exactly… | `BEHAVIORAL` |
| `CHG-07` | Claim parser - trailing-abbreviation act binding ('Section… | A bare citation followed by a bare acronym had no act signal; it fell through to the field-wide single-act fa… | Reproduced case: '... Section 32 of the Indian Evidence Act, 1872. Section 100 CrPC also applies.' mis-resolv… | adf54aa research/prototype/src/claim_parser.py (_TRAILING_ABBREV_TOKENS, _TRAILING_ABBREV_RE,… | An adjacent IPC/CrPC/CPC acronym binds the citation to that already-trusted alias act, ahead of any… | `ENGINEERING` |
| `CHG-08` | Claim parser - Art./Arts. abbreviation recognition | _KEYWORD_PATTERN recognized only the full words Section/Article/Order/Rule/... and required whitespace betwee… | 'Art. 32' / 'Arts. 136' / 'Art.227' were not recognized; on one real generated paragraph citing 4 Articles ex… | c250a0e research/prototype/src/claim_parser.py (_ABBREVIATED_KEYWORD_TO_CANONICAL, _ABBREVIATE… | Art./Arts. (trailing period required, so the English word 'art' cannot match) map to canonical 'Art… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-09` | Sentence splitting - abbreviation awareness | split_sentences() split on every '.' + whitespace + capital/digit, with no abbreviation list | '...Art. 32 ... Art. 136...' was shattered into fragments separating each citation keyword from its own numbe… | c250a0e research/prototype/src/claim_parser.py (_SENTENCE_BOUNDARY_ABBREVIATIONS = ('Art.','Ar… | Sentence splitting re-merges fragments broken at the two abbreviations actually observed in 181 rea… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-10` | Claim granularity - assertion_text (per-citation sub-span) | A Claim carried only claim_text = the whole sentence; every citation in a bundled sentence shared it | On real NyayaRAG output one physical sentence routinely backs several claims, so (a) the scope check required… | 100e263 research/prototype/src/claim_parser.py (_assign_assertion_texts: semicolon split, ' wh… | Every claim carries a verbatim, contiguous assertion_text (falls back to the full sentence when no… | `HISTORICAL` |
| `CHG-11` | Claim granularity - assertion_spans ('respectively' pattern) | No structured representation for a claim whose content is not one contiguous span | For 'Sections 406 and 420 ..., which respectively deal with X and Y' a citation's number and its paired descr… | 100e263 research/prototype/src/claim_parser.py (_assign_respectively_spans, _respectively_item… | 'respectively' claims carry a LIST of independently-required verbatim fragments [bare_number_span,… | `BEHAVIORAL` |
| `CHG-12` | Evidence matcher - digit-insensitive token-overlap shortcut | _token_overlap was plain Jaccard over act_significant_words | motivation: NOT_DOCUMENTED (inferred from diff: intended to treat act names differing only by numeric tokens… | 223eb9d research/prototype/src/evidence_matcher.py _token_overlap (+4 lines: sets equal after… | Sets equal after dropping pure-digit tokens score 1.0; otherwise unchanged Jaccard | `NOT_MEASURED` |
| `CHG-13` | Evidence pool - v0 (59 records) -> v0+v1 (136 records) | load_usable_evidence() read exactly one (canonical, audit) file pair; config had no v1 paths and no use_evide… | Evidence coverage on real natural claims was ~60-63%; correctly-parsed citations returned NO_EVIDENCE purely… | 100e263: src/data_loader.py (_load_usable_records_by_key, extra_canonical_path/extra_audit_pat… | The v1 supplement is merged by dataset_citation_key (extra replaces base) when use_evidence_v1: tru… | `HISTORICAL` |
| `CHG-14` | Evidence matcher - year-conflict veto on fuzzy matching | Fuzzy fallback compared act names only by significant-word overlap; years were invisible (act_significant_wor… | Two same-named Acts differing ONLY by year ('Income Tax Act, 1961' vs 'Income-tax Act, 2025'; 'Arbitration Ac… | adf54aa research/prototype/src/evidence_matcher.py (_YEAR_RE, _act_years, _year_conflict veto… | If both sides state an explicit, disjoint year the pair can never fuzzy-match at any overlap; a sid… | `ENGINEERING` |
| `CHG-15` | Evidence matcher - NO_EVIDENCE taxonomy promoted into the l… | An unmatched claim carried no reason; the 4-category taxonomy lived only in the offline scripts/audit_no_evid… | Distinguishing 'parser could not resolve the act' from 'corpus genuinely lacks this provision' from 'differen… | adf54aa research/prototype/src/evidence_matcher.py classify_no_evidence() + src/pipeline.py cl… | Every unmatched claim records one of 4 taxonomy categories at run time; the decision rule is identi… | `BEHAVIORAL` |
| `CHG-17` | Verifier - premise framing bare -> labeled | The NLI premise was the statute text alone; apply_verification called verifier.verify(premise=rec['evidence_t… | Generated claims are attributed ('According to Section 302 of the IPC ...') but a bare premise never mentions… | fe8b15b research/prototype/src/verifier.py format_premise() + src/pipeline.py resolve_premise_… | Premise is '<Provision> <N> of <Act>: <statute text>' built from the MATCHED EVIDENCE record's own… | `GOLD` |
| `CHG-20` | Verifier - silent premise-truncation detection | Tokenizer truncation at max_sequence_length=512 happened silently; VerificationResult had no truncation field | HF pair-truncation trims the END of the premise - exactly where a statute's trailing exception/proviso sits -… | adf54aa research/prototype/src/verifier.py (untruncated tokenizer call + input_truncated field… | Every verdict records whether its input was truncated; verdict logic unchanged (detection only - th… | `BEHAVIORAL` |
| `CHG-21` | Verifier - raw softmax scores persisted in claim records | Only the argmax label + confidence (+ sub_reason) were stored; the full distribution was discarded | A low-confidence downgrade to NOT_ENOUGH_INFORMATION permanently discarded which raw label was argmax, so rec… | adf54aa research/prototype/src/pipeline.py (raw_scores on claims, reverification and sibling_r… | Every verified claim stores the full entailment/neutral/contradiction distribution; never read by a… | `BEHAVIORAL` |
| `CHG-22` | Verifier - narrow_primary_hypothesis (assertion_text as pri… | apply_verification always used the full claim_text as the NLI hypothesis; only correction re-verification cou… | Documented gap: 'the primary verification pass never uses the narrower assertion_text hypothesis - only [corr… | bb2cd93 research/prototype/src/pipeline.py apply_verification(narrow_primary_hypothesis=...) +… | When a claim has a genuinely narrower assertion_text it becomes the hypothesis in the primary pass;… | `HISTORICAL` |
| `CHG-25` | Correction scope check - atomic_scope_check false -> 'asser… | _scope_violation required every unflagged claim's FULL claim_text (the whole shared sentence) to reappear byt… | On real natural data many claims share one bundled sentence, so any edit inside the flagged citation's own po… | 100e263 research/prototype/src/pipeline.py _scope_violation(use_assertion_text, use_assertion_… | An unflagged claim is checked against its assertion_spans list (ALL fragments must survive); degrad… | `HISTORICAL` |
| `CHG-26` | Correction re-verification - narrow_reverification_hypothes… | Re-verification hypothesized the re-extracted replacement claim's full claim_text | On a bundled sentence the full-sentence hypothesis is diluted by sibling content, keeping a genuinely correct… | 100e263 research/prototype/src/pipeline.py (reverify_hypothesis + reverified_hypothesis record… | Re-verification uses the replacement claim's own assertion_text when narrower; the ENTAILED-only sh… | `HISTORICAL` |
| `CHG-27` | Correction - replacement lookup by ordinal citation identity | The replacement claim was the FIRST re-extracted claim whose (provision_type, provision_number, act_norm) mat… | A document can contain several claims citing the same provision, so citation identity alone is ambiguous betw… | 100e263 research/prototype/src/pipeline.py (_citation_identity + same-identity ordinal lookup) | The Nth same-identity claim in the baseline is matched to the Nth same-identity claim in the correc… | `HISTORICAL` |
| `CHG-28` | Correction safety - sibling-regression re-verification net | No sibling re-verification existed; the only containment was the byte-for-byte scope check | The relaxed (assertion_text/assertion_spans) scope check only requires a narrow fragment to survive, so a sib… | 100e263 research/prototype/src/pipeline.py _reverify_sibling_regressions() + status 'correctio… | Whenever an atomic scope mode is on and the correction would otherwise ship, every other evidence-m… | `HISTORICAL` |
| `CHG-29` | Correction trigger - negation safety gate | Any CONTRADICTED verdict triggered automatic correction | Empirically confirmed on the real DeBERTa checkpoint with real IPC Section 302 evidence: a negated claim ('Ne… | adf54aa research/prototype/src/pipeline.py (_NEGATION_MARKER_RE, _negation_marker_present, neg… | A CONTRADICTED verdict matching a narrow lexical negation pattern is excluded from automatic correc… | `BEHAVIORAL` |
| `CHG-30` | Correction scope check - word-boundary fragment matching | _scope_violation used plain Python 'in' substring containment for every required fragment | A bare provision-number fragment ('34', used by assertion_spans for the 'respectively' pattern) is trivially… | adf54aa research/prototype/src/pipeline.py _fragment_present(), used by both scope-check branc… | Each fragment is matched with a word boundary anchored at whichever end is a word character - stric… | `BEHAVIORAL` |
| `CHG-31` | Correction safety - unauthorized citation-addition guard | Scope enforcement only verified that EXISTING unflagged claims survived; nothing forbade introducing a NEW ci… | A corrector that fixes the flagged claim but also hallucinates an extra never-requested citation (or swaps th… | adf54aa research/prototype/src/pipeline.py (baseline citation-identity set check + status 'cor… | Any citation identity in the corrected text with no counterpart in the baseline rejects the correct… | `BEHAVIORAL` |
| `CHG-32` | Correction safety - ordinal-integrity check (fabricated con… | Ordinal matching assumed same-identity siblings keep their relative order, an invariant the scope check never… | If the corrector reorders two same-identity claims, every unflagged claim's text still appears (scope check p… | adf54aa research/prototype/src/pipeline.py (replacement vs other same-identity baseline texts… | If the selected replacement is byte-identical to another same-identity claim's original text, the c… | `BEHAVIORAL` |
| `CHG-33` | Correction safety - sibling-regression exclusion of pre-exi… | _reverify_sibling_regressions re-checked EVERY unflagged sibling, including ones already independently CONTRA… | An otherwise-successful correction was mislabeled 'correction_sibling_regression', conflating 'my edit broke… | adf54aa research/prototype/src/pipeline.py (_should_trigger_correction(rec) AND rec['claim_tex… | Already-flagged siblings are skipped ONLY when genuinely untouched (full claim_text preserved verba… | `BEHAVIORAL` |
| `CHG-36` | Final answer assembly - fail-closed sources | final_field had 4 possible sources: original / corrected / correction_failed / correction_scope_violation; a… | New rejection categories (sibling regression, ordinal ambiguity, unauthorized addition, plus the three assert… | adf54aa (+3 sources) and 8cf8fa9 (+3 assertion-aware sources) research/prototype/src/pipeline.… | 9 final_field sources; the assembly rule itself is unchanged - anything not fully verified ships th… | `HISTORICAL` |

### EXPERIMENTAL_NOT_PROMOTED (4)

*Built and evaluated, deliberately OFF in production. Never describe these as production behaviour.*

| ID | Component | Original behaviour | Problem | Modification | Latest behaviour | Grade |
|---|---|---|---|---|---|---|
| `CHG-19` | Verifier - QwenLLMVerifier (alternative LLM verifier) | Verification was DeBERTa-v3-base-mnli-fever-anli only | 'attribution prefixes (According to Section X...) and complex statutory paraphrasing cause small NLI models t… | 54c98d2 research/prototype/src/llm_verifier.py (QwenLLMVerifier) + scripts/build_verifier_benc… | Fully built but never wired into pipeline.py; production verification is still DeBERTa. The root ca… | `BEHAVIORAL` |
| `CHG-23` | Verifier - assertion_span_primary_hypothesis ('respectively… | narrow_primary_hypothesis cannot narrow a 'respectively' claim: assertion_text stays equal to claim_text by c… | For 'respectively' claims the full bundled sentence remained the hypothesis, diluting it; one real case let a… | 8cf8fa9 research/prototype/src/pipeline.py _assertion_spans_hypothesis() + apply_verification(… | Implemented, adversarially audited and left OFF: builds '<provision_type> <number> <description>' o… | `HISTORICAL` |
| `CHG-34` | Correction mechanism - assertion-aware (span rewrite + dete… | Correction asked the LLM to regenerate the WHOLE paragraph with one sentence changed, then checked afterwards… | Whole-paragraph regeneration is what makes scope violations possible at all; on bundled sentences the dominan… | 8cf8fa9 research/prototype/src/corrector.py correct_assertion_span() + src/pipeline.py apply_s… | Implemented, benchmarked and left OFF: legacy apply_selective_correction remains the production pat… | `GOLD` |
| `CHG-35` | Correction - structural-span validation and new fail-closed… | Correction had 3 outcomes: corrected / correction_failed / correction_scope_violation | The assertion-aware path can fail in ways the legacy statuses cannot express: a malformed/missing assertion_s… | 8cf8fa9 research/prototype/src/pipeline.py statuses correction_span_invalid, correction_splice… | The assertion-aware path fails closed on each of these rather than guessing; the sibling-regression… | `HISTORICAL` |

### EVALUATED_AND_REJECTED (1)

*Built, benchmarked, and actively rejected on measured grounds.*

| ID | Component | Original behaviour | Problem | Modification | Latest behaviour | Grade |
|---|---|---|---|---|---|---|
| `CHG-16` | Retrieval scoring - BM25 and embedding alternatives | The fuzzy fallback had exactly one scoring function: Jaccard token overlap at threshold 0.8, with no config k… | The corpus's 22 unique Act names mean Jaccard occasionally rejects legitimate shorthand ('Evidence Act', 'Cor… | 6347c45 research/prototype/src/retrieval_signals.py (Bm25ActIndex, EmbeddingActIndex, best_mat… | Both alternatives are implemented, tested and kept installed, but fuzzy_method stays 'jaccard': BM2… | `BEHAVIORAL` |

### INFRASTRUCTURE_ONLY (10)

*Tooling, loading mechanics or experiment scaffolding. No behavioural claim attaches.*

| ID | Component | Original behaviour | Problem | Modification | Latest behaviour | Grade |
|---|---|---|---|---|---|---|
| `CHG-18` | Verifier - explicit CPU device option | NLIVerifier hard-required CUDA and raised if torch.cuda.is_available() was False; fp16 always | The offline controlled-verifier benchmark is pure NLI scoring with no co-resident generator and had no way to… | fe8b15b research/prototype/src/verifier.py NLIVerifier.__init__(device=...), fp32 on CPU, expl… | device still defaults to 'cuda' and still refuses a silent CPU fallback; device='cpu' is an explici… | `GOLD` |
| `CHG-37` | Reproducibility metadata - config levers recorded per run | The reproducibility block recorded mode, seed, models, quantization, threshold, timestamp and software versio… | Without the lever values a committed output record could not be attributed to the config that produced it, ma… | fe8b15b (premise_framing), adf54aa (use_evidence_v1, atomic_scope_check, narrow_reverification… | Every output record names the levers that produced it | `HISTORICAL` |
| `CHG-38` | Model loading / host memory | StatuteGroundingGenerator.load() called from_pretrained() with quantization_config + device_map and no memory… | On a 15.7GB-RAM laptop with ~5.1-5.5GB free, three consecutive fresh GPU batches (n=100, n=50, n=30) all fail… | 8cf8fa9 research/prototype/src/generator.py (explicit low_cpu_mem_usage=True + gc.collect()/to… | Loading mechanics only: 'Neither changes model identity, weights, quantization config, or output';… | `BEHAVIORAL` |
| `CHG-39` | Experiment harness - checkpointed/resumable GPU ablation +… | run_narrow_primary_hypothesis_gpu_ablation.py ran a batch straight through, with no checkpointing and no host… | The same host-memory ceiling that blocked model loading also made a long batch unrecoverable if it died mid-r… | 8cf8fa9 research/prototype/scripts/run_narrow_primary_hypothesis_gpu_ablation.py (checkpoint/r… | The ablation is resumable and checks free RAM per case; it produced the committed n=62 result | `HISTORICAL` |
| `CHG-40` | Evaluation harness - synthetic stress + natural targeted ev… | Only run_mvp.py / run_eval_30.py / summarize_eval_30.py existed | No mechanism existed to produce known-wrong claims or to target natural cases with corpus overlap, so contrad… | 223eb9d research/prototype/src/synthetic_stress.py + scripts/run_synthetic_stress_eval.py + sc… | A deterministic corruption harness and a targeted natural evaluation exist and are still used as GO… | `DETERMINISTIC_SYNTHETIC` |
| `CHG-41` | Evaluation harness - 420-item controlled verifier benchmark… | Verifier quality was assessed only indirectly, through pipeline runs | The project could not tell whether NEI verdicts came from the model, the premise construction or the corpus -… | fe8b15b research/prototype/scripts/build_controlled_benchmark.py, run_controlled_benchmark.py,… | A 420-item curated benchmark with stored softmax distributions (enabling threshold ablation with no… | `GOLD` |
| `CHG-42` | Evaluation workspace - audited testing pack and reorganizat… | Evaluation artifacts lived ad hoc under outputs/ and testing/ | motivation: NOT_DOCUMENTED beyond the commit subjects (inferred from diff: consolidating provenance, per-comp… | 4e221ba, 9d39ca4, 61b240a research/prototype/testing -> research/prototype/evaluation/ (+ arch… | research/prototype/evaluation/ holds components/, ablation/, metrics/, comparisons/, live_demo/, PR… | `BEHAVIORAL` |
| `CHG-43` | Live component and pipeline demos | run_demo.py was a single monolithic demo script | motivation: NOT_DOCUMENTED (inferred from diff: per-stage demonstrations of the real production modules on re… | b83bb6b research/prototype/evaluation/live_demo/01-06 stage demos + 07_full_pipeline/ outcome… | Six per-stage demos plus four full-pipeline outcome demos that run the real production modules | `BEHAVIORAL` |
| `CHG-46` | Repo hygiene - scratch removal and config-aware evidence lo… | scratch/ held four ad-hoc analysis scripts; run_mvp.py built evidence-loader arguments by hand (v0 only) | motivation: NOT_DOCUMENTED (inferred from diff: run_mvp --check reported a pool size that ignored use_evidenc… | 3e9e09a research/prototype/scripts/run_mvp.py + deletion of research/prototype/scratch/ | run_mvp.py --check loads through load_usable_evidence_from_config and reports 136 usable records wi… | `NOT_APPLICABLE` |
| `CHG-47` | Error-propagation instrumentation for correction attempts | Correction failures were visible only as a status string per record; no stage-level attribution existed | The project could not say WHERE a correction attempt first failed (parsing, retrieval, verification, targetin… | 8cf8fa9 research/prototype/scripts/build_error_propagation_matrix.py + outputs/error_propagati… | First-failure stage is computed per (document, arm) pair for the n=10 assertion-aware batch | `BEHAVIORAL` |

### DOCS_ONLY (3)

*Documentation. No code behaviour changed.*

| ID | Component | Original behaviour | Problem | Modification | Latest behaviour | Grade |
|---|---|---|---|---|---|---|
| `CHG-24` | Verifier - confidence_threshold (evaluated, deliberately un… | confidence_threshold: 0.70, 'fixed by design (approved design doc), not calibrated' | No failure found - the open question was whether 0.70 stayed defensible after premise framing changed the ver… | 100e263 config/prototype.yaml - COMMENT ONLY; the value was never changed anywhere in the hist… | Still 0.70, documented as within 0.002 macro-F1 of the empirical optimum under both framings (label… | `BEHAVIORAL` |
| `CHG-44` | Figures, diagrams and results packs | No figures, diagrams or consolidated metric tables existed | motivation: NOT_DOCUMENTED beyond commit subjects (inferred from diff: building a presentable, provenance-tra… | a3cd187 and 4ca3fad (final_demo_pack / final_comparison), 6c74e21 (Output_phase_3_vedant: 25 f… | results_phase3/ holds figures, diagrams, tables, RESEARCH_CLAIMS.md, LIMITATIONS.md and a SOURCE_MA… | `BEHAVIORAL` |
| `CHG-45` | Decision-record and status documentation | README.md and BASELINE.md only; no decision record for config levers | motivation: NOT_DOCUMENTED as a 'problem' (inferred from diff: the production-lever decisions and their evide… | 100e263 (REPRODUCIBILITY.md, final_research_results.md, final_limitations_and_future_scope.md)… | FINAL_PRODUCTION_CONFIG.md records 5 changed levers, 2 evaluated-not-promoted mechanisms, 1 rejecte… | `NOT_APPLICABLE` |

---

## 2. Changes corroborated by a FRESH V2 experiment

These are the changes whose effect was re-measured on this machine for this package, rather
than quoted from a historical artifact.

**CHG-01, CHG-02, CHG-03, CHG-04, CHG-05**

> V2 FRESH (n=30 docs): claims resolving to evidence 38 (ORIGINAL 0e37525) -> 54 (223eb9d) -> 57 (LATEST HEAD); ORIGINAL->LATEST +10/-0 documents, sign test p=0.0020. The LATEST arm reproduces parser_fix_before_after_n30_v2_postfix.json exactly; the ORIGINAL arm reproduces 0e37525:outputs/eval_30_report.md exactly.

**CHG-13, CHG-15**

> V2 FRESH structural recount: 59 -> 136 usable records, 10 -> 22 distinct Acts (59 + 75 new-usable + 2 promoted = 136). Coverage OUTCOME remains historical.

**CHG-21, CHG-24, CHG-41**

> V2 FRESH full sweep 0.34-0.99 from stored softmax: labeled leads at EVERY threshold (smallest gap 0.1916); production 0.70 sits on a flat plateau.

**CHG-40**

> V2 FRESH (n=59, 2x2 factorial): contradiction recall 0.3559 -> 0.4576, McNemar exact p=0.0312 (6 discordant). NULL: narrow_primary_hypothesis has exactly zero effect on this set.

---

## 3. Changes with NO measuring experiment

Listed explicitly so that no reader assumes every change carries measured evidence. Most of
these are safety gates discovered adversarially and covered by regression tests — the tests
prove the failure is blocked, but nothing measures how often it occurred in real data.

| ID | Component | Why it was changed | What covers it instead |
|---|---|---|---|
| `CHG-07` | Claim parser - trailing-abbreviation act binding ('Sec… | Reproduced case: '... Section 32 of the Indian Evidence Act, 1872. Section 100 CrPC also appli… | NONE (regression tests only: research/prototype/tests/test_adversarial_cit… |
| `CHG-12` | Evidence matcher - digit-insensitive token-overlap sho… | motivation: NOT_DOCUMENTED (inferred from diff: intended to treat act names differing only by… | NONE |
| `CHG-14` | Evidence matcher - year-conflict veto on fuzzy matching | Two same-named Acts differing ONLY by year ('Income Tax Act, 1961' vs 'Income-tax Act, 2025';… | NONE for a data batch (explicitly 'not triggered in the shipped 136-record… |

---

## 4. Code-level discrepancies found during this audit

Found by auditing the LATEST source against its own configuration and documentation.
Recorded, not fixed — fixing them would mean altering frozen research artifacts.

| ID | Severity | Discrepancy | Consequence |
|---|---|---|---|
| **D1** | HIGH | `evidence_matching.fuzzy_method` and 3 sibling keys are **never read**. All four `match_evidence()` call sites in `pipeline.py` pass positional arguments, so `"jaccard"` comes from the function default. | **BM25/embedding retrieval is unreachable from production**, whatever the config says. Editing that key changes nothing. The BM25/embedding rejection decision is unaffected — but the config presents a choice that does not exist. |
| **D2** | MEDIUM | `claim_parsing.citation_regex` and `stopwords` are never read, and the config's regex copy is **stale** — it lacks `Arts?\.`, the plural `s?`, the number-list grammar and the `Part <roman>` group. | Any manifest or paper that copies the YAML regex would document a parser that does not exist. The config does mark the block informational. |
| **D3** | MEDIUM | `pipeline.py:1353` hardcodes a **"59-record"** corpus disclaimer while the live pool is **136**. | Every output record contradicts its own `usable_evidence_pool_size` field. |
| **D4** | LOW | `correction.max_attempts`, `correction.max_reverifications` and `evidence_matching.top_k` are never read. | Config suggests tunability that is not wired up. |
| **D5** | LOW | No `verification.device` key exists; the verifier is CUDA-only by constructor default and must be passed `device="cpu"` explicitly. | Not a defect — a deliberate guard — but it is undocumented in config. |
| **C-1** | MATERIAL | `config/prototype.yaml` claims four times that flipping the five levers "exactly reproduces" pre-2026-08-27 outputs. **False at HEAD**: the negation gate, year-conflict veto, injection guard and ordinal guard landed at `adf54aa` (2026-09-09) and none is config-controllable. | The configuration baseline is **strictly more gated** than the real pre-2026-09-09 system. The year-conflict veto can change which evidence is retrieved, hence the premise, hence the verdict. |
| **C-2** | MATERIAL | Under the configuration baseline the **sibling-regression gate is silently inactive** (`pipeline.py:947` gates it on a truthy `atomic_scope_check`) while four newer gates stay on. | An "`atomic_scope_check` on vs off" comparison is not a clean single-variable comparison — it also toggles a safety net. |
| **E-1** | LOW | `config/prototype.yaml` describes the pool expansion as "78 new + the 59 v0 records" = 137, but the true merged total is **136**. | Correct decomposition, recomputed via the production loader: 59 v0 usable + 75 genuinely-new usable + 2 promoted from unusable = 136. |
| **P-1** | LOW | Re-executing the **committed** `223eb9d` parser yields **54** claims resolving to evidence where the artifact committed at that same commit records **51**. Component isolation rules out the matcher and loader; the counting rule is identical. | Likely the artifact was generated from a working tree differing slightly from the committed source. **No ORIGINAL→LATEST conclusion depends on it** — both endpoints reproduce their artifacts exactly. |

---

## 5. Reading rules

1. **Never quote an `EXPERIMENTAL_NOT_PROMOTED` change as production behaviour.** Two
   mechanisms — `verification.assertion_span_primary_hypothesis` and
   `correction.assertion_aware` — are fully built, benchmarked, and deliberately **OFF**.
2. **Never present the rejected retrieval methods as an improvement.** BM25 and embedding
   matching were evaluated and **actively rejected** on safety grounds.
3. **Four levers were flipped in a single commit** (`100e263`), so their joint effect is
   confounded in every artifact that postdates it. No additive or interaction effect between
   levers is claimed anywhere in this package.
4. **`ENGINEERING` and `NOT_MEASURED` are not failures.** A gate whose only evidence is a
   regression test is still a real gate; it simply has no data-batch measurement, and this
   package says so rather than implying one exists.
5. **The models never changed.** Every difference recorded here is a system, pipeline or
   configuration change.
