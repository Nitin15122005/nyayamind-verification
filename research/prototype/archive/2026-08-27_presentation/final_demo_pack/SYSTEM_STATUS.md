# System Status

## Production configuration (frozen, `research/prototype/config/prototype.yaml`)

| Option | Value | Changed from v0 default? | Decision record |
|---|---|---|---|
| `premise_framing` | `"labeled"` | Yes (was `"bare"`) | `FINAL_PRODUCTION_CONFIG.md` §1 |
| `use_evidence_v1` | `true` (136-record pool) | Yes (was `false`, 59-record pool) | `FINAL_PRODUCTION_CONFIG.md` §2 |
| `correction.atomic_scope_check` | `"assertion_spans"` | Yes (was `false`) | `FINAL_PRODUCTION_CONFIG.md` §3 |
| `correction.narrow_reverification_hypothesis` | `true` | Yes (was `false`) | `FINAL_PRODUCTION_CONFIG.md` §4 |
| `verification.confidence_threshold` | `0.70` | **No** — evidence supports keeping it | `FINAL_PRODUCTION_CONFIG.md` §5 |
| Generation model | `Qwen/Qwen2.5-7B-Instruct`, 4-bit, greedy | n/a (unchanged since inception) | `research/prototype/README.md` |
| Verification model | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, fp16 | n/a | `research/prototype/README.md` |

Every value above was locked by `tests/test_premise_framing_production.py::test_shipped_config_locks_the_2026_08_27_final_production_decision`, which asserts the shipped config exactly matches this table. Nothing in this configuration has been changed while building the demo pack.

## Test / check status (as of the last verification run in this project, 2026-08-27 repository freeze)

| Check | Result |
|---|---|
| `pytest research/prototype/tests/ -q` | **205 passed** |
| `run_mvp.py --check` | Passed — loads 136 usable evidence records (`use_evidence_v1=True`) |
| Docker build + `run_mvp.py --check` inside container | Passed |

This demo pack does not re-run or re-verify these itself except where the FINAL REPOSITORY FREEZE validation step explicitly re-ran them (see `research/prototype/final_demo_pack/metadata/validation_log.md` for the demo-pack-build-time re-check).

## Frozen vs. open items

**Frozen (will not change without a new decision record):**
- Model choices, quantization, generation parameters (`research/prototype/config/prototype.yaml`)
- Evidence corpus content (`research/data/evidence/*.jsonl` — v0 63 records + v1 82-record supplement, additive, never merged into v0 files)
- All committed experiment outputs (`research/prototype/outputs/*`)
- The four production-config values in the table above

**Known open items (explicitly documented, not silently outstanding):**
1. **`premise_framing: labeled` rests partly on n=1 shipped / 10 triggered** — the newest, least-repeated evidence behind this decision. `FINAL_PRODUCTION_CONFIG.md` §1 recommends a fresh 50-100-case batch under the full final config to confirm the shipped-correction rate before treating this as fully settled.
2. **A genuine counter-signal exists and is not suppressed**: re-verifying the older, PROVISIONAL assumption-annotated set (38 evidence-matched claims, Claude-generated labels, NOT lawyer-verified) under labeled framing shows *slightly lower* agreement (18/38, 47.4%) than bare (20/38, 52.6%) — the opposite direction from every other source behind the `premise_framing` decision. See `FINAL_PRODUCTION_CONFIG.md` §1 and `reports/verifier_analysis.md`.
3. **39% of the v1 evidence supplement (32/82 records) still rests on build-time provenance only**, not independently re-verified — rate-limited by the source site, not a decision to stop early (`research/data/evidence/README_v1.md`).
4. **No lawyer/professional-legal ground-truth evaluation exists.** This is the single largest open item for any claim about real-world accuracy.

   _See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
5. **`run_mvp.py`'s evidence-loader bug** (silently loading only the 59-record v0 pool regardless of `use_evidence_v1`) was found and fixed during the 2026-08-27 repository freeze (commit `3e9e09a`) — flagged here so the fix's existence and reasoning are visible alongside frozen status, not because it's still open.

## Reproducing this status

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check
```

See `research/prototype/REPRODUCIBILITY.md` for the complete command reference, and `RUNBOOK.md` in this pack for demo-pack-specific regeneration commands.

## Addendum — 2026-09-09

**A fifth production-config value changed since the table above was built
(2026-08-27)**, via commit `bb2cd93`:

| Option | Value | Changed from 2026-08-27 default? | Decision record |
|---|---|---|---|
| `verification.narrow_primary_hypothesis` | `true` | Yes (was `false`) — new, added 2026-09-09 | `FINAL_PRODUCTION_CONFIG.md` §5 |

This is a distinct setting from `correction.narrow_reverification_hypothesis`
(already `true` since 2026-08-27, unchanged, still row 4 of the table above)
— the new setting extends the same narrow-hypothesis idea to **primary**
verification, not just correction re-verification. `reports/verifier_analysis.md`'s own addendum now supersedes that report's original
"primary verification always hypothesizes the full `claim_text`" statement.
`tests/test_premise_framing_production.py`'s shipped-config lock test was
itself extended 2026-09-09 to additionally assert
`cfg["verification"]["narrow_primary_hypothesis"] is True` — the lock
described in this file's original table still holds, now with one more
asserted field.

Other new findings since 2026-08-27 (do not change any number already in
this file, since none touched the config values the table above locks):
`adf54aa` (5 adversarial safety gaps fixed), `6347c45` (BM25/embedding
retrieval evaluated and rejected, Jaccard stays default), `c250a0e`
(Art./Arts. parser fix, +7 claims). Full detail: `README.md`'s addendum.

**This demo-pack build's own regeneration paths needed a fix this pass**:
`metadata/compute_metrics.py`, `metadata/validate_pack.py`, and
`figures/generate_figures.py` (in this pack) and
`../final_comparison/scripts/{build_comparison_data,generate_figures}.py`
each computed their repo-root via a hardcoded `Path(...).parents[N]` walk-up
that was correct for this pack's original build location
(`research/prototype/final_demo_pack/`) but broke silently — resolving to the
wrong directory — after the whole pack was archived one level deeper
(`research/prototype/archive/2026-08-27_presentation/final_demo_pack/`)
during the 2026-08-27 freeze/reorg. Fixed in place this pass (see each
script's own inline comment); re-running `compute_metrics.py`,
`generate_figures.py`, and `tables/generate_tables.py` after the fix
reproduced every existing figure/table/JSON byte-for-byte identical to the
committed versions — confirming this was a path bug, not a data change.

**`metadata/validate_pack.py` (path-fixed, re-run this pass) now runs
further than before but still does not complete**: it crashes on
`examples/cases.json`, because the `examples/` and `live_demo/` directories
(and their generator scripts) were deleted from this pack in commit
`61b240a` ("Reorganize evaluation workspace and finalize validation") while
`README.md`, `RUNBOOK.md`, and `ARTIFACT_INDEX.md` still describe them as
present. This predates and is unrelated to the four commits documented here.
It was not fixed this pass — reconstructing hand-written case prose is out
of scope for a metrics-regeneration pass, and the check was left as a hard
failure rather than weakened to pass. All 21 checks that ran before the
crash passed (JSON/CSV validity, all 16 figures present and non-trivial,
every headline number spot-check). See `metadata/validation_log.md`'s own
addendum for the exact re-run transcript.
