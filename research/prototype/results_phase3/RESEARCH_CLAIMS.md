# Research Claims — classified

Every major paper-facing claim about NyayaMind, classified as **SUPPORTED**, **PROVISIONAL**,
**DESCRIPTIVE**, **ENGINEERING-ONLY**, or **NOT SUPPORTED**. See `sources/RESULT_INDEX.csv`
for exact source artifacts.

| # | Claim | Classification | Evidence | n | Experiment type | Permitted interpretation | Caveat |
|---|---|---|---|---|---|---|---|
| C1 | Labeled premise framing improves NLI verifier accuracy over bare framing | **SUPPORTED** | macro F1 0.749→0.968, McNemar p=4.16e-23 | 420 | Controlled, labeled | State the exact numbers and test | Controlled benchmark; hypotheses mechanically constructed, not free-running generated claims |
| C2 | The v0+v1 evidence pool increases evidence coverage over v0-only | **SUPPORTED** | 63.2%→70.3% (fresh), McNemar p=0.0003 | 209 | Paired natural, METRIC-ONLY | State as coverage improvement, never "accuracy" | Two distinct historical/fresh columns exist for CONTRADICTED counts — never conflate them (see FINAL_RESULTS.md §5) |
| C3 | The claim-parser fix (223eb9d + Art./Arts.) improves evidence-matchable claim extraction | **SUPPORTED** | 6/30 improved, 0 worsened, sign test p=0.03 | 30 | Historical reproduction (parser not re-executed; sign test freshly recomputed) | State the exact counts and test | Cannot re-execute the pre-fix parser without checking out old source; not attempted |
| C4 | `atomic_scope_check="assertion_spans"` reduces false scope-violation rejections | **PROVISIONAL** | 1/11 real historical scope violations unblocked on replay | 11 | Descriptive replay, no test | State as a directional, small-n observation | DIAGNOSTIC grade; a real, not fabricated, replay — but only 1/11 |
| C5 | `narrow_reverification_hypothesis` produces more decisive re-verification signals | **PROVISIONAL** | 3 real correction_failed cases, qualitative confidence shift | 3 | Historical, descriptive | State as illustrative, not general | No outcome (ship/reject) changed in the cases tested |
| C6 | `narrow_primary_hypothesis` (production default) shifts verdicts toward more decisive outcomes | **PROVISIONAL** | verdict shift on fresh n=62 batch, directionally consistent with prior evidence | 62 documents / 32 evidence-matched claims/arm | Fresh GPU natural batch | State as directional; not independently significant at this n | 0 correction shipped in both arms |
| C7 | `assertion_span_primary_hypothesis` improves verification on "respectively" claims | **PROVISIONAL, NOT PROMOTED** | 4/6 claims changed verdict, one revealing a real generation error | 6 | Historical, real | State the exact counts; do not generalize | Sample size explicitly the reason for non-promotion, not a found defect |
| C8 | BM25/embedding retrieval are viable alternatives to Jaccard fuzzy matching | **NOT SUPPORTED (evaluated and rejected)** | Correct-reject rate 33%/22% vs Jaccard's 100% on adversarial Act names | 30 pre-registered cases | Historical, descriptive adversarial set | State that both were evaluated and found materially less safe | Not "untested" — actively evaluated and rejected on safety grounds |
| C9 | Assertion-aware (splice-based) correction ships more corrections than legacy | **NOT SUPPORTED** | 0/10 shipped both mechanisms on the identical paired real replay | 10 | Fresh GPU, paired | State plainly: no improvement measured | The mechanism is architecturally correct and safe (0 unsafe) — non-promotion is about the specific outcome measured, not implementation quality |
| C10 | Assertion-aware correction properly integrates parser-produced `assertion_spans` | **SUPPORTED (engineering claim)** | 0 target/outcome mismatches replaying all 9 real triggered attempts; a real "respectively" claim tested and ships correctly in the deterministic test suite | 9 real + 1 synthetic multi-span test | ENGINEERING / architecture verification | State as an implementation-correctness result, separate from any shipping-rate claim | No real natural-data multi-span correction case has been observed yet |
| C11 | NyayaMind's correction pipeline never ships an unsafe correction | **SUPPORTED, within tested scope** | 0/132 unsafe shipments across every attempt in project history (122 historical + 10 new) | 132 | Mixed historical + fresh | State the exact denominator and that it is "within tested scope" | No formal adversarial red-team beyond the categories already exercised — see LIMITATIONS.md |
| C12 | NyayaMind is lawyer-validated / legally correct | **NOT SUPPORTED** | No lawyer ground truth exists anywhere in this project | — | — | Never make this claim | Explicitly disclaimed in every natural-data artifact in this project |
| C13 | NyayaMind's results generalize broadly beyond this evidence pool / case set | **NOT SUPPORTED** | No cross-corpus or cross-jurisdiction evaluation performed | — | — | Describe results as bounded to this evidence pool and NyayaRAG case set | — |
| C14 | Docker deployment of the current codebase has been validated | **NOT SUPPORTED (ENVIRONMENT-BLOCKED)** | Daemon not running on this machine across 5 sessions | — | — | State as environment-blocked, not failed or passed | A 2026-08-27 image (predating 5 later levers) was smoke-tested as a structural sanity check only |

## Absolutely do not claim

- Lawyer validation, guaranteed legal correctness, or a formal legal-correctness oracle (C12).
- Broad generalization beyond this project's evidence pool and case set (C13).
- Correction-rate improvement from assertion-aware correction (C9) — the real, current
  evidence is a null result.
- That BM25/embedding retrieval were "not evaluated" — they were, and rejected (C8).
- That any natural-data figure is "accuracy," "precision," or "recall" — those terms are
  reserved for GOLD-01/GOLD-02, the only labeled datasets in this project.

## Final research status

The evidence in this package supports describing NyayaMind as:

- **Research-grade**: yes — controlled benchmarks with real labels, paired natural-data
  comparisons, and a documented, evidence-based promotion/rejection process for every lever.
- **End-to-end implemented**: yes — parser → retrieval → verification → correction →
  re-verification → safety gates → final assembly, all real code, all tested.
- **Reproducible**: yes, with stated exceptions — GPU-dependent historical results are not
  re-executable on hardware without a GPU meeting the VRAM requirement; commands are
  documented in `FINAL_RESEARCH_FREEZE_REPORT.md` and this package's `sources/SOURCE_MAP.csv`.
- **Experimentally evaluated**: yes — including two mechanisms evaluated and honestly not
  promoted.
- **Paper-ready as a research prototype**: yes, with the limitations in `LIMITATIONS.md`
  stated alongside any submission.

It does **not** support describing NyayaMind as lawyer-validated, legally correct by
guarantee, production-certified, or universally generalizable.
