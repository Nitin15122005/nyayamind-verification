# Safety and Limitations

Full detail: `research/prototype/results_phase3/LIMITATIONS.md` (the canonical, most
up-to-date limitations document). This file summarizes and adds the safety-architecture map.

## Safety architecture (fail-closed throughout)

| Gate | What it catches | Location | Path |
|---|---|---|---|
| Scope violation | An unflagged claim's required text does not survive a correction | `pipeline._scope_violation` | both correction paths |
| Unauthorized citation addition | A new citation identity appears that wasn't in the original field | inline in `apply_selective_correction*` | both |
| Ordinal-integrity check | The same-citation-identity ordinal slot resolves to a different, untouched sibling | inline | both |
| Sibling-regression re-verification | An independently re-verified sibling claim now genuinely CONTRADICTED | `pipeline._reverify_sibling_regressions` | legacy: opt-in; assertion-aware: UNCONDITIONAL |
| Negation safety gate | A CONTRADICTED verdict driven by a negation pattern is excluded from auto-correction | `pipeline._NEGATION_MARKER_RE` and related | verification stage, both paths |
| Structural-span preservation (NEW) | A multi-element `assertion_spans` claim's non-content element (e.g. bare citation number) does not survive the edit | `pipeline.apply_selective_correction_assertion_aware` | assertion-aware only |
| Span validity (NEW) | A missing/malformed `assertion_spans` representation | `pipeline._correction_target_spans` | assertion-aware only |

**Observed result across every correction attempt in project history: 0/132 unsafe
shipments** (122 historical + 10 new). "Unsafe" here means: shipped as `corrected` despite an
unflagged claim being altered, a citation being injected, or a sibling claim regressing.

## What "safety" does NOT mean here

- **No formal, independently-designed 15-category red-team safety evaluation has been
  performed.** Safety has been tested against categories that arose from real historical
  failures plus a pre-registered adversarial retrieval set — a real, meaningful, but not
  exhaustive, coverage. Never say "formally proven safe."
- Safety gates catch structural/textual violations; they do not detect a correction that
  preserves surface-level entailment while subtly changing legal meaning outside the tested
  categories (negation, modality flip, citation swap, sibling regression).

## Limitations by area (see LIMITATIONS.md for full detail)

- **Ground truth**: no lawyer-validated ground truth exists anywhere in this project. The only
  labeled datasets (GOLD-01, GOLD-02) are deterministically constructed, not human-annotated.
- **Sample sizes**: correction shipping (1/56, 1/10, 0/9, 0/10 across various batches),
  `assertion_span_primary_hypothesis` (n=6), and the assertion-aware correction replay (n=10)
  are all small; none supports a confident population-level rate estimate.
- **NLI verifier**: confidence-threshold behavior characterized only in the 0.50-0.95 range;
  negation handled by an exclusion rule, not general understanding.
- **Retrieval**: bounded by the 136-record pool; BM25/embeddings evaluated and rejected on
  safety grounds specifically, not "untested."
- **Parser**: two confirmed bundled-sentence shapes never narrow (see `03_COMPONENTS.md`).
- **Correction**: dominant failure is generation quality, not pipeline defect; assertion-aware
  correction has not yet been exercised on a real, natural, multi-span correction case.
- **Resources**: several historical results require a specific GPU (RTX 4050, 6GB class); this
  machine's 16GB RAM ceiling means large fresh GPU batches (n>62) have not been attempted since
  a confirmed OOM pattern, and per project convention that OOM configuration is not repeated.
- **Docker**: ENVIRONMENT-BLOCKED (daemon not running on the development machine across every
  session checked) — never claim this as "passed" or as a research blocker; it is an
  environment fact, not a methodology gap.

## Experimental components are not promoted BY DESIGN, not oversight

`verification.assertion_span_primary_hypothesis` and `correction.assertion_aware` are both
fully implemented and tested. Their production value is `false` because the evidence available
does not yet support promotion — this is a deliberate, evidence-based engineering decision
recorded in `FINAL_PRODUCTION_CONFIG.md` §5a/§5b, not unfinished work.
