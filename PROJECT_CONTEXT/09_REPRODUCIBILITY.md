# Reproducibility — navigation

**Full, authoritative reproducibility reference**: `research/prototype/REPRODUCIBILITY.md`.
This file is a quick-start pointer, not a replacement — always check that document for the
current, exact command set and any caveats.

## Fastest checks (no GPU, no network, safe to run anywhere)

```
# Repo root
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check
research/.venv/Scripts/python.exe research/prototype/archive/2026-08-27_presentation/final_demo_pack/metadata/validate_pack.py
```

Expected (as of this writing): **302 tests passing**, `run_mvp.py --check` reports 136 usable
evidence records, `validate_pack.py` reports **25/25** checks passed.

## What needs a GPU vs. CPU-only

See `research/prototype/REPRODUCIBILITY.md` §2 for the full table. In short: tests and
`--check` never need a GPU; re-verifying already-generated text is CPU-safe; only fresh
generation and fresh correction (both Qwen calls) require CUDA.

## Where things live

| What | Where |
|---|---|
| Production config | `research/prototype/config/prototype.yaml` |
| Environment/pinned packages | `research/requirements.txt`, `REPRODUCIBILITY.md` §1 |
| Exact commands for every historical experiment | `research/prototype/REPRODUCIBILITY.md` §3 |
| Where final artifacts land | `research/prototype/REPRODUCIBILITY.md` §4 |
| Seeds and key config values as shipped | `research/prototype/REPRODUCIBILITY.md` §5 |
| Known reproducibility caveats (e.g. `build_evidence_v1.py` not re-runnable from clean checkout) | `research/prototype/REPRODUCIBILITY.md` §6 |

## Results-package-specific validation

`research/prototype/results_phase3/` was built by scripts under `research/prototype/scripts/`
(`build_results_phase3_*.py`) that read ONLY committed source artifacts — no experiment is
re-run to rebuild a figure/table. To regenerate any of them:

```
research/.venv/Scripts/python.exe research/prototype/scripts/build_results_phase3_tables.py
research/.venv/Scripts/python.exe research/prototype/scripts/build_results_phase3_figures.py
research/.venv/Scripts/python.exe research/prototype/scripts/build_results_phase3_diagrams.py
research/.venv/Scripts/python.exe research/prototype/scripts/build_results_phase3_sources.py
research/.venv/Scripts/python.exe research/prototype/scripts/build_results_phase3_f16_ablation.py
```

## Resource constraints (real, on the development machine)

- **16GB RAM ceiling**: a confirmed OOM pattern occurred at n=100/50/30 for a large fresh GPU
  batch before a memory-loading fix (`src/generator.py`: explicit `low_cpu_mem_usage=True` +
  `gc.collect()`/`torch.cuda.empty_cache()` before `from_pretrained()`). Per project
  convention, that OOM configuration is never blindly repeated — see
  `research/prototype/outputs/16gb_memory_architecture_audit.md`.
- **GPU**: validated on an NVIDIA RTX 4050 Laptop GPU, 6GB VRAM class.
- **Docker**: ENVIRONMENT-BLOCKED — the Docker daemon has not been running across every
  session that checked it on this machine. Not attempted to be claimed passing; a
  2026-08-27 image (predating five later production levers) was smoke-tested as a structural
  sanity check only, not evidence for current code.

## Historical frozen results

`research/prototype/outputs/` (100+ files) is a lab notebook, not clutter — every file is a
dated checkpoint in a real experimental sequence, cited by at least one final/consolidated
document. Nothing there should be deleted or altered without a clear, evidence-based reason.
See `REPOSITORY_MANIFEST.md` (repo root) §3 for the full family-by-family inventory (as of
2026-09-06; files added since are not yet catalogued there but follow the same convention).
