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
