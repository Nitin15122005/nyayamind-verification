# NyayaMind Demo / Evaluation Pack

Presentation and evaluation material for the NyayaMind statutory-claim
verification prototype (v0 research prototype — see
`research/prototype/README.md` for the full system, `FINAL_PRODUCTION_CONFIG.md`
for the frozen production configuration this pack describes). Built for showing
the finished system to an evaluator/professor. **Nothing here modifies the
frozen research** — every script in this pack only reads
`research/prototype/{src,config,outputs}` and `research/data/evidence/`; see
`ARTIFACT_INDEX.md`'s closing note.

## Start here

1. **`EXECUTIVE_SUMMARY.md`** — what the system does, headline measured
   results, what's diagnostic-only, what's NOT established (read this first).
2. **`SYSTEM_STATUS.md`** — frozen production config, test status, open items.
3. **`METRICS_TABLE.md`** — the full metric checklist, one place.
4. **`live_demo/run_demo.py`** — run this to see the 7-stage pipeline execute
   against real cases in under a minute (no GPU needed).
5. **`examples/EXAMPLES_INDEX.md`** — 8 real, hand-picked-with-stated-criteria
   cases: a CONTRADICTED catch, the one shipped correction, a rejected
   correction, a scope violation, a NO_EVIDENCE case, a v1-evidence-gain case,
   a labeled-framing-improvement case, and a correctly-declined case.

## Directory structure

```
final_demo_pack/
├── README.md                     <- this file
├── EXECUTIVE_SUMMARY.md          <- Part A
├── SYSTEM_STATUS.md              <- Part A
├── METRICS_TABLE.md              <- Part A/B
├── RUNBOOK.md                    <- Part J: exact regeneration commands
├── ARTIFACT_INDEX.md             <- Part J: every file, what it is, how it's made
├── DATA_LINEAGE.md               <- Part J: provenance chain, raw data -> every output
├── reports/                      <- Parts G/H/I: retrieval, verifier, correction+safety deep dives
├── tables/                       <- Part D: 16 chart-backing table families + 1 comprehensive table
├── figures/                      <- Part C: 16 PNG charts
├── examples/                     <- Part E: 8 exemplar real cases + selection methodology
├── live_demo/                    <- Part F: deterministic end-to-end demo runner
└── metadata/                     <- The computed-metrics single source of truth + validation
```

## What this pack is and is not

- **Is:** a faithful, source-traced presentation of this project's real,
  already-committed experimental results and a live demonstration of the real
  production code running against real cases.
- **Is not:** a claim of lawyer-verified legal accuracy (none exists — see
  every report's disclaimer), a new experiment (no new GPU inference beyond
  the small CPU-only DeBERTa calls the live demo makes), or a modification of
  any frozen research artifact (evidence corpus, `outputs/*`, `config/prototype.yaml`

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
  are all read-only inputs to everything in this pack).

## Validation status (as of the last build of this pack)

- `pytest research/prototype/tests/ -q` — 205/205 passed
- `research/prototype/scripts/run_mvp.py --check` — passed, 136 usable evidence records
- `metadata/validate_pack.py` — 25/25 checks passed (see `metadata/validation_log.md`)
- `live_demo/run_demo.py` — runs clean, live-reproduces the one shipped correction's
  reverification confidence to within floating-point noise of the committed record
  (0.9946 live vs. 0.99457 committed)

See `RUNBOOK.md` to regenerate any of the above.

## Addendum — 2026-09-09 (post-freeze update, pack refreshed in place)

This pack was built 2026-08-27 and is a frozen replay of that date's committed
outputs (see "What this pack is and is not" above) — that framing still
holds. Four commits since then changed real pipeline/config behavior; none of
them altered any file this pack's `metadata/compute_metrics.py` reads
(`outputs/final_metrics.json` and friends), so every number in
`computed_metrics.json`, every figure, and every table was **re-run against
current source data during this addendum pass and reproduced byte-for-byte
identical to the 2026-08-27 committed versions** (`compute_metrics.py`'s own
`Cross-checks all match: True` still holds). What follows is new information
layered on top, not a correction of anything already stated as of 2026-08-27:

1. **`adf54aa` — adversarial-hardening safety pass.** Five real safety gaps
   found and fixed: bare trailing-abbreviation citations ("Section 100 CrPC")
   now resolve via a trusted alias instead of a field-wide guess; fuzzy
   evidence matching now vetoes candidates with explicit, disjoint years
   (this closes the "fuzzy matching is year-blind" limitation noted in
   `reports/retrieval_analysis.md`); a negation safety gate now excludes
   negation-driven CONTRADICTED verdicts from triggering correction;
   word-boundary-aware scope-violation matching (was falsely satisfiable by
   e.g. "34" inside "134"); an unauthorized-citation-injection guard and an
   ordinal-integrity guard. 231/231 tests pass.
2. **`6347c45` — BM25/embedding retrieval evaluated, REJECTED.** Jaccard
   remains the production `fuzzy_method` default. See
   `research/prototype/outputs/retrieval_signal_benchmark_report.md`: at this
   corpus's scale (22 unique Acts), Jaccard is the only method tested that
   reaches 100% correct-reject on a 9-case safety set (BM25 and embedding
   both wrongly match legally-distinct Acts, e.g. "Arbitration Act, 1940" vs
   "Arbitration and Conciliation Act, 1996") while also having the best
   correct-accept rate of any method at full safety.
3. **`c250a0e` — Art./Arts. citation-abbreviation parser fix.** Recovered 7
   claims net (795 → 802) across the 181 unique real generated texts this
   project has ever produced, isolated by running both parser versions
   in-memory on the same texts. See
   `research/prototype/outputs/article_abbreviation_fix_impact_report.md`.
   This supersedes the "Zero confirmed parser or evidence-matcher defects"
   framing in `reports/retrieval_analysis.md` — see that report's own
   addendum below.
4. **`bb2cd93` — `narrow_primary_hypothesis` extended to primary
   verification, default flipped to `true`.** In a CPU re-scoring benchmark
   over 456 real evidence-matched claim/evidence pairs (verification-only,
   no regeneration), 31/107 applicable claims recovered NEI → ENTAILED, 2/107
   went NEI → CONTRADICTED, and **0 claims reversed between the two
   safety-relevant labels (ENTAILED ↔ CONTRADICTED)**. See
   `research/prototype/outputs/narrow_primary_hypothesis_benchmark_report.md`.
   This is a fifth production-config change beyond the four documented in
   `SYSTEM_STATUS.md`'s table and figure 15 (both explicitly dated
   2026-08-27 and correctly left as-is) — see `FINAL_PRODUCTION_CONFIG.md`
   §5 for the full decision record and `SYSTEM_STATUS.md`'s own addendum.
   A dedicated fresh-GPU ablation isolating this lever landed during this
   addendum pass: 15 genuinely fresh natural cases (never used in any prior
   experiment), real Qwen generation + real DeBERTa verification through the
   actual production pipeline, OLD (`narrow_primary_hypothesis=false`) vs
   CURRENT (`=true`), everything else held identical. Result: 1/12
   evidence-matched claims NEI → ENTAILED, 0 CONTRADICTED either arm, 0
   corrections triggered/shipped either arm (so no shipping-safety
   comparison is possible from this small sample). Directional, n=15, not a
   statistically powered claim — consistent in direction with, but far
   smaller than, the 456-claim CPU re-scoring result above. See
   `research/prototype/outputs/narrow_primary_hypothesis_gpu_ablation_report.md`.

**CORRECTION (2026-09-11)**: the paragraph originally here (2026-09-09 addendum
pass) incorrectly claimed `live_demo/` and `examples/` were deleted by commit
`61b240a` with their source generator scripts gone. That was wrong —
`git show -M --name-status 61b240a` shows these paths were **renamed** (94-100%
content similarity), not deleted: `final_demo_pack/examples/*` →
`research/prototype/evaluation/examples/*` and `final_demo_pack/live_demo/*` →
`research/prototype/evaluation/live_demo/*`. Both are fully intact there today,
and `live_demo/` was actively extended afterward (commit `b83bb6b` added
`common/` helpers and 6 more numbered per-stage demo scripts). The 8 example
case studies, `cases.json`, `candidate_pool.json`, and `run_demo.py` (already
updated for Stage 1-4's `assertion_text`/`assertion_spans`/narrow-hypothesis
config) all still exist and work — see `research/prototype/evaluation/` directly
rather than this archived pack for the live demo and example case studies.
`metadata/validate_pack.py`'s failure on the missing `examples/` path (see
`metadata/validation_log.md`'s addendum) is real for THIS archived copy
specifically (the files were never copied into `archive/2026-08-27_presentation/`
in the first place, only the top-level `final_demo_pack/` files were), but is not
evidence of data loss — the content simply lives at `evaluation/` instead of
inside this frozen archive snapshot.
