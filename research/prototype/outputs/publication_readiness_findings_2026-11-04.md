# Publication-readiness audit findings — 2026-11-04

## Scope and method

This is a source-document consistency review of the publication-readiness branch. It compares the evidence-corpus READMEs, runtime loader, shipped configuration, reproducibility guide, and classified research claims. It is not an execution report: the Python test suite and corpus audit script have not yet been run in a repository runtime. No statutory text was legally validated in this review.

## Confirmed documentation defects

### F-01 — v1 README contains stale usable-record counts
**Severity: high | Status: documentation correction required**

`research/data/evidence/README_v1.md`'s original summary table says 79 `VERIFIED_EXACT`, 3 `SOURCE_ONLY`, and describes a 137-record merged pool. Its dated 2026-08-27 independent-audit addendum later records that Section 2 of the Income Tax Act, 1961 was downgraded from `VERIFIED_EXACT` to `SOURCE_ONLY`, producing 78 usable v1 records and a 136-record merged pool. The top-level summary is therefore stale relative to its own addendum and current audit data. The addendum is the later decision record; update the summary table and arithmetic only after confirming the current JSONL counts.

### F-02 — shipped config comments contain conflicting audit coverage
**Severity: high | Status: documentation correction required**

`research/prototype/config/prototype.yaml` says 50% of v1 records were directly re-fetched, while the v1 README addendum confirms 41/82 (50%). The earlier README section still says 8/82. These are sequential audit stages, not necessarily contradictory, but the chronology is easy to misread. The config comment should explicitly say the original build spot-checked 8/82 and the later independent audit re-fetched 41/82, rather than presenting only the final figure without context.

### F-03 — reproducibility guide's expected test count is stale
**Severity: medium | Status: execution required**

`research/prototype/REPRODUCIBILITY.md` still says 205 tests expected as of 2026-08-27. Project context elsewhere reports 302 tests, but this review did not execute pytest. Replace the expected count with the actual current run only after executing the complete documented command; otherwise state that the count is not currently verified.

### F-04 — reproducibility guide overstates reproducibility
**Severity: high | Status: wording correction required**

The guide says model revisions are not pinned, and that GPU results may not be byte-identical across hardware/software. It also describes the project as reproducible. These statements need a precise distinction: code/data/config replayability is not the same as exact model-output reproducibility. A paper should state which artifacts are exactly replayable, which are environment-dependent, and which historical GPU experiments cannot be regenerated from a clean checkout.

### F-05 — current data-loader docstrings describe old defaults/counts
**Severity: medium | Status: documentation correction required**

`src/data_loader.py`'s `select_cases_with_evidence_overlap` docstring refers to a 59-record evidence pool, while shipped config sets `use_evidence_v1: true` and its comments describe a 136-record pool. The lower-level loader's generic documentation correctly describes v0-only behavior when no supplement is supplied, but case-selection documentation should refer to the configured pool or explicitly state that 59 is the historical v0-only count.

## Research-design risks requiring experiments or annotation

### R-01 — controlled GOLD-01 benchmark is not natural-claim validation
The classified claims document itself states that the 420 hypotheses were mechanically constructed. Its very high labeled-framing result supports a controlled framing comparison on that benchmark, not broad accuracy on free-running legal summaries. The paper must report construction procedure, split unit, case/source overlap, template diversity, and any repeated lexical or structural patterns. A case-disjoint and template-disjoint test is needed before claiming generalization.

### R-02 — v1 audit scope is materially narrower than v0
The later addendum reports 41/82 direct re-fetches, not a full independent re-fetch of all v1 records. The corpus is suitable for bounded research use under the documented policy, but it must not be presented as exhaustively independently source-verified. Prioritize the remaining 41 records for source re-fetch and record-level provenance.

### R-03 — statutory versioning is not represented as a full temporal applicability model
The corpus records a coarse `historical_status`, but its own README identifies old IPC/CrPC/Evidence Act transitions, Income-tax Act replacement, and amendments to specific provisions. A citation match on Act + section does not by itself establish that the retrieved text is the version applicable on the judgment date. This is a core limitation for any paper claim involving historical legal grounding. A future schema should represent effective-from/effective-to dates, amendment/version identifiers, repeal/savings status, and source authority separately. Do not silently modify the frozen corpus as part of this audit.

### R-04 — source authority and text provenance are heterogeneous
The v0 README reports that most records were search-synthesized summaries, while the v1 README reports a mix of verbatim and summarized text; source pages are third-party IndianKanoon rather than the official India Code repository. The verifier's premise quality is therefore heterogeneous. Evaluation should stratify by provenance and authority, and the manuscript must describe the source policy accurately.

### R-05 — retrieval benchmark is small and corpus-specific
The documented retrieval comparison uses 30 adversarial/positive examples. It supports the current conservative choice within that tested set, not a universal claim that Jaccard is superior to BM25 or embeddings. Expand the benchmark with unseen Act aliases, year conflicts, same-section-number collisions, subordinate legislation, and historical editions. Keep the production default unchanged until paired evidence supports a change.

### R-06 — correction outcome is sparse
The claims table reports 1/56 shipped in cumulative natural history and 0/10 for the newer assertion-aware paired replay. The system's safety gates may be useful, but sparse correction opportunities limit claims about practical correction effectiveness. Report coverage, attempted corrections, eligible corrections, accepted corrections, rejected corrections, and semantic regressions separately.

### R-07 — no independent legal gold standard
The project has no lawyer-annotated gold set. This does not prevent a systems or methodology paper, but it limits legal-validity claims. The paper should frame the contribution as statutory-claim extraction, evidence retrieval, NLI-based consistency assessment, and constrained correction under a bounded corpus—not as a legal correctness guarantee.

## Engineering issues in the current structural audit script

1. The script stores all usable records in an intermediate dictionary inside the report-building path. This is acceptable for the current small corpus but should remain excluded from the serialized report (currently done).
2. The exact-index collision key includes provision type, provision number, subsection, and normalized Act. This matches the loader's key shape. Keep both implementations synchronized.
3. It currently validates HTTPS URLs and required fields but does not validate provenance/verdict consistency (for example, `webfetch_summarized_not_verbatim` must not be treated as `VERIFIED_EXACT`). Add a rule based on the corpus's documented audit policy, but first inspect every allowed provenance value and exception in the actual JSONL.
4. It does not independently re-fetch source URLs; its status must remain explicitly structural.
5. It imports the runtime parser. Running it requires the project package path and dependencies to be available; test this on Windows and POSIX invocation paths.

## Immediate order of work

1. Correct stale corpus README summary and configuration comments after a fresh count of the committed JSONL files.
2. Add unit tests for the structural audit using temporary JSONL fixtures: valid pair, missing/orphan audit row, duplicate key, invalid JSON, unknown verdict, v1 supersession, year/version index collision, and provenance/verdict mismatch.
3. Run the full test suite and the audit script in the actual project environment; capture command, interpreter, commit SHA, exit status, counts, and report hash.
4. Build a case-disjoint, template-disjoint verifier benchmark and report per-class metrics, confidence intervals, calibration, and selective risk.
5. Expand retrieval and correction evaluation without changing production defaults.
6. Add a temporal-version schema proposal and a record-level legal annotation protocol; lawyer review remains a separate validation stage.

## Preservation

No production defaults, frozen canonical JSONL files, historical results, baseline submodule, or `main` branch were changed by this review. Findings are documentation and research-design actions, not claims that fixes or experiments have already passed.
