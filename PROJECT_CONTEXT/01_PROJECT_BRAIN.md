# NyayaMind — Project Brain

**Read this file first.** It is the compact mental model of the whole project. For depth on
any topic, follow the links to the other `PROJECT_CONTEXT/` files and the canonical source
artifacts they point to — do not assume this file alone is a substitute for verifying a claim
against its source.

## 1. Project identity

**nyayamind-verification** — a statutory-claim verification and selective-correction layer for
LLM-generated Indian court judgment summaries, developed alongside a frozen reproduction of an
unrelated baseline task (RhetoricLLaMA/LegalSeg rhetorical-role classification, kept for
provenance only — see §4).

## 2. Research objective

Not "is the summary good" — a narrower question: for the **Statutory Grounding** field of a
generated case summary, does each cited legal provision actually say what the model claims it
says, and can a verification + selective-correction step fix an unsupported/contradicted claim
without touching anything else in the field?

## 3. Problem being addressed

LLMs asked to summarize Indian court judgments readily name statutes, sections, and articles
that sound plausible but are wrong, outdated, or unsupported by the actual case. This project
builds a deterministic, auditable layer that catches this for one specific field, rather than
trying to solve general summary quality.

## 4. Baseline system

**NyayaMind v0 (pre-2026-08-27 baseline)** — the same pipeline code as the modified system,
with five configuration levers at their un-evidenced defaults: `premise_framing=bare`,
`use_evidence_v1=false` (59-record evidence pool), `atomic_scope_check=false`,
`narrow_reverification_hypothesis=false`, `narrow_primary_hypothesis=false`. This is a
**configuration baseline within one project**, not a different codebase.

Separately, `research/baseline/` contains a frozen reproduction of **LegalSeg/RhetoricLLaMA**
(`meta-llama/Llama-2-7b-chat-hf` + `L-NLProc/LegalSeg_RhetoricLLaMA` LoRA adapter) — a
**different task on a different dataset** (rhetorical-role classification, not statutory
verification). It is NOT a quantitative baseline for any NyayaMind result; kept only because
this project's generation stack inherits its `accelerate`/`transformers` version constraints.
See `research/baseline/BASELINE.md`. Never compare NyayaMind numbers to it.

## 5. Modified NyayaMind system (current production)

Same pipeline code, five levers changed based on real evidence: `premise_framing=labeled`,
`use_evidence_v1=true` (136-record pool), `atomic_scope_check="assertion_spans"`,
`narrow_reverification_hypothesis=true`, `narrow_primary_hypothesis=true`. Decision record for
every one of these: `FINAL_PRODUCTION_CONFIG.md` (repo root). Two further mechanisms were
built and evaluated but **not promoted**: `verification.assertion_span_primary_hypothesis`
(off) and `correction.assertion_aware` (off) — see §20.

## 6. Exact model names

| Role | Model |
|---|---|
| Generation | `Qwen/Qwen2.5-7B-Instruct`, 4-bit NF4, greedy decoding |
| Correction | same loaded generation model, reused (not a second model) |
| Verification (NLI) | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, fp16 |
| Baseline (out-of-scope reference) | `meta-llama/Llama-2-7b-chat-hf` + `L-NLProc/LegalSeg_RhetoricLLaMA` |

Full detail: `PROJECT_CONTEXT/05_MODELS_AND_CONFIGURATIONS.md`.

## 7-17. Major components and the end-to-end pipeline

```
Case (case_text)
  -> [1] Generate Statutory Grounding field    (Qwen2.5-7B-Instruct)         PRODUCTION
  -> [2] Claim parsing + assertion spans       (src/claim_parser.py, regex)  PRODUCTION
  -> [3] Evidence retrieval                    (exact + Jaccard fuzzy)      PRODUCTION
       (BM25 / embedding fuzzy methods: EVALUATED, REJECTED — see §21)
  -> [4] NLI verification                      (DeBERTa-v3-mnli)            PRODUCTION
       (narrow_primary_hypothesis=true: PRODUCTION; assertion_span_primary_hypothesis: EXPERIMENTAL, off)
  -> [5] Verdict assignment + negation gate     (src/pipeline.py)            PRODUCTION
  -> [6] Selective correction (legacy)          (whole-sentence regen)      PRODUCTION (Mode C)
       (assertion-aware splice-based correction: EXPERIMENTAL, off — see §20)
  -> [7] Re-parse + re-verify corrected text                                 PRODUCTION
  -> [8] Safety gates (scope/citation/ordinal/sibling-regression/structural-span) PRODUCTION
  -> [9] Final answer assembly (final_field)                                 PRODUCTION
```

Component-by-component detail: `PROJECT_CONTEXT/02_ARCHITECTURE.md`,
`PROJECT_CONTEXT/03_COMPONENTS.md`. Source of truth: `research/prototype/src/`.

## 18. Production components (summary)

Generator, claim parser (incl. assertion_text/assertion_spans narrowing + Art./Arts. fix),
Jaccard-based evidence retrieval, labeled premise framing, DeBERTa verifier with
`narrow_primary_hypothesis`, legacy selective correction with the full safety-gate chain,
`atomic_scope_check="assertion_spans"`, `narrow_reverification_hypothesis`.

## 19. Experimental components (implemented, tested, NOT production default)

- `verification.assertion_span_primary_hypothesis` — evaluated on n=6 real "respectively"
  claims, not promoted (sample size, not a found defect).
- `correction.assertion_aware` — splice-based correction targeting the parser's real
  `assertion_spans`; architecturally complete and safe; evaluated on n=10 real paired
  attempts, 0/10 shipped (same as legacy's 0/10 on the identical cases) — no shipping
  improvement demonstrated yet.

## 20. Evaluated-but-rejected components

- **BM25 and sentence-embedding fuzzy Act-name matching** (`src/retrieval_signals.py`) —
  both accept every real match but are materially less safe than Jaccard on adversarial
  near-miss Act names (e.g. Civil↔Criminal Procedure Code). Rejected for production,
  kept in source as an evaluated, documented alternative.

## 21. Major experiments (map)

Full map with n, model, CPU/GPU, freshness, grade: `PROJECT_CONTEXT/04_EXPERIMENTS_AND_RESULTS.md`.
Headlines: controlled verifier benchmark (n=420, macro F1 0.749→0.968), paired evidence
coverage (n=209, 63.2%→70.3%), claim-parser fix (n=30, 6 improved/0 worsened), correction
funnel (cumulative natural: 1/56 shipped, 0 unsafe), narrow_primary_hypothesis (n=62 fresh GPU
batch), assertion-span verification (n=6), assertion-aware correction (n=10 paired real
replay, 0/10 both mechanisms).

## 22. Major validated results

See `research/prototype/results_phase3/FINAL_RESULTS.md` §1 (Executive Summary) — this is the
single most complete, up-to-date results narrative in the repository.

## 23. Negative/null results (preserved, not hidden)

- `assertion_span_primary_hypothesis`: evaluated, not promoted (n=6).
- `correction.assertion_aware`: 0/10 shipped vs legacy's 0/10 on the identical paired replay —
  the mechanism is correct and safe, the specific outcome it was built to improve did not
  improve on this evidence.
- BM25/embedding retrieval: evaluated and actively rejected for safety reasons.
- Joint four-lever ablation: **NOT_ISOLABLE, NOT_EXECUTED** — no experiment in this project's
  history varies all four production levers from one common baseline in a single run; never
  claim otherwise.

## 24. Important failure modes (real, documented)

- Correction: dominant historical failure is the 7B corrector producing no-op or inadequate
  edits (a generation-quality limitation, not a pipeline defect) and claim-bundling scope
  violations.
- Parser: two confirmed bundled-sentence shapes never narrow via `assertion_text`/`assertion_spans`
  — a bare "Sections X and Y" listing with no per-citation clause, and a "respectively" pattern
  immediately followed by a trailing " while " clause.
- Assertion-aware correction case study (`1955_32`): the splice mechanism produced a correct,
  isolated fix, but shipping was still blocked because an untouched sibling claim in the same
  sentence was independently wrong — the safety design working as intended, not a mechanism
  failure.

## 25. Known limitations

Full list: `PROJECT_CONTEXT/07_SAFETY_AND_LIMITATIONS.md` and
`research/prototype/results_phase3/LIMITATIONS.md`. Headline: no lawyer-validated ground truth
exists anywhere in this project; small samples throughout correction-shipping and
assertion-span work; no formal 15-category red-team safety evaluation; Docker is
environment-blocked on the development machine (not attempted to be hidden as passed).

## 26. Scientific non-claims

Never say: lawyer-validated, guaranteed legal correctness, universally generalizable,
production-certified, or that a null result (assertion-aware correction, BM25/embeddings) is
an improvement. Full registry: `PROJECT_CONTEXT/08_RESEARCH_CLAIMS.md`.

## 27-30. Where canonical artifacts live

| What | Where |
|---|---|
| Canonical results (figures, tables, diagrams, claims, limitations) | `research/prototype/results_phase3/` |
| Canonical figures | `research/prototype/results_phase3/figures/` |
| Canonical tables | `research/prototype/results_phase3/tables/` |
| Canonical architecture/flow diagrams | `research/prototype/results_phase3/diagrams/` |
| Production config decision record | `FINAL_PRODUCTION_CONFIG.md` (repo root) |
| Full research freeze narrative | `FINAL_RESEARCH_FREEZE_REPORT.md` (repo root) |

## 31-33. Source, tests, historical artifacts

| What | Where |
|---|---|
| Source code | `research/prototype/src/` |
| Tests (302 passing as of this writing) | `research/prototype/tests/` |
| Production config | `research/prototype/config/prototype.yaml` |
| Raw experiment outputs (100+ files, a lab notebook, not clutter) | `research/prototype/outputs/` |
| Presentation/evaluation workspace (pre-2026-09-06 snapshot, read-only source for the archived Phase-3 package) | `research/prototype/evaluation/` |
| 2026-08-27 presentation snapshot (archived) | `research/prototype/archive/2026-08-27_presentation/` |
| Prior Phase-3 results package (archived 2026-09-12, superseded by `results_phase3/`) | `research/prototype/archive/2026-09-06_output_phase_3_vedant/` |

## 34. Current frozen state

See `PROJECT_CONTEXT/11_CURRENT_STATUS.md` for the live summary. In brief: implementation
complete and tested (302/302); `results_phase3/` is the authoritative, current results
package; two mechanisms remain EXPERIMENTAL by evidence-based decision; Docker is
ENVIRONMENT-BLOCKED, not attempted to be claimed passing.

## 35. Rules for future Claude sessions

1. **Do not fabricate results, ground truth, labels, or statistical significance.**
2. **Do not call a natural-data observation "accuracy," "precision," or "recall"** — those
   terms are reserved for the two labeled datasets (GOLD-01 n=420, GOLD-02 n=59).
3. **Do not confuse historical and fresh results** — some artifacts (e.g. the 209-paired
   evidence-coverage file) carry BOTH a historical and a fresh column for the same metric;
   read the field names, don't assume.
4. **Do not confuse controlled (labeled) and natural (unlabeled) data.**
5. **Do not confuse experimental and production components** — check
   `config/prototype.yaml`'s actual live values, not what a feature's existence implies.
6. **Do not overwrite or silently alter historical evidence** — this project's convention is
   to APPEND a dated update/addendum to a document, never rewrite history out.
7. **Do not casually modify frozen research artifacts** (`outputs/`, `results_phase3/`,
   archived packages) without a clear, stated reason and the user's intent to do so.
8. **Verify every claim against its canonical source artifact** before repeating it — a memory
   or a prior document's claim is not itself evidence.
9. **Preserve negative results** — a null or rejected result is a legitimate, valuable finding
   in this project and must never be hidden or reframed as a win.
10. **Prefer existing evidence over assumptions** — if unsure whether something is current,
    check the live config/code/latest committed artifact rather than guessing from an older
    document.

### Recommended workflow for any new task

1. Read this file (`01_PROJECT_BRAIN.md`).
2. Read the relevant `PROJECT_CONTEXT/0X_*.md` document(s) for the topic at hand.
3. Read `PROJECT_CONTEXT/10_REPOSITORY_MAP.md` to locate the right directory.
4. Inspect the canonical source artifact the task concerns (a specific `outputs/*.json`,
   `results_phase3/tables/*.csv`, `config/prototype.yaml`, etc.).
5. Inspect actual source code (`research/prototype/src/`) if implementation behavior matters.
6. Only then make changes — and follow the project's existing conventions (append, don't
   overwrite; new experiments get new output files; never touch `baseline/LegalSeg`).
