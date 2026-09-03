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
