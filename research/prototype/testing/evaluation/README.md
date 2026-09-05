# Evaluation

## Scope, and the boundary with `comparisons/` and `ablation/`

`evaluation/` is where a dataset-level evaluation is **run and its raw output/metrics are
computed and stored**. `comparisons/` is where results *already computed here or in
`research/prototype/outputs/`* are organized and narrated side-by-side for presentation.
`ablation/` is specifically single-variable sweeps/replays, most of which need no new
inference.

**This boundary was flagged as a likely source of duplication** by an independent review
of this workspace's design (a threshold sweep is itself "an evaluation producing
metrics," and a natural-batch metric could be computed and then immediately compared).
The working rule adopted for this workspace: **`evaluation/` owns computation and raw
artifacts; `comparisons/` only narrates and links to them, never recomputes.** Enforce
this in the next step rather than letting both accumulate the same CSVs independently.

## Environment gap affecting every command below

`research/.venv/` **does not exist in this checkout** (verified 2026-09-05) — only a
system Python 3.14 install is present, newer than this project's pinned
Python 3.11.9 / torch==2.2.2+cu121 / transformers==4.40.2 stack, with no guarantee of
compatibility. Every command below assumes the venv has first been created:
```
python -m venv research/.venv
research/.venv/Scripts/python.exe -m pip install -r research/requirements.txt
```
This is a real, currently-unaddressed reproducibility gap — see `../PROVENANCE.md`.

## Planned evaluation runs (none executed in this step)

| Evaluation | Command | Input | Model | CPU/GPU | Planned output location |
|---|---|---|---|---|---|
| Controlled NLI benchmark (420) | `scripts/build_controlled_benchmark.py` then `scripts/run_controlled_benchmark.py --device cpu --premise-framing {bare,labeled}` | 59 v0 evidence records | DeBERTa | CPU | `evaluation/controlled_benchmark/` |
| Synthetic stress (59) | `scripts/run_synthetic_stress_eval.py` (no CLI flags confirmed; run with defaults) | 59 v0 evidence records via `src.synthetic_stress` | Qwen 7B + DeBERTa | **GPU** | `evaluation/synthetic_stress/` |
| Merged evidence pool count (136) | one-liner from `REPRODUCIBILITY.md` §3 calling `load_usable_evidence_from_config` | evidence jsonl ×4 | none | CPU | `evaluation/evidence_pool/` |
| 588-claim NO_EVIDENCE taxonomy / v0-vs-v1 coverage | `scripts/audit_no_evidence_taxonomy_v2.py`, `scripts/measure_evidence_coverage_v0_vs_v1.py` (both no CLI flags) | evidence pool + all committed natural generated text | none | CPU | `evaluation/evidence_coverage/` |
| CPU-only bare-vs-labeled re-verification (209/147-claim subset, 38-claim assumption subset) | `scripts/compare_final_validation_labeled_cpu.py`, `scripts/compare_assumption_gold_bare_vs_labeled.py` (both no CLI flags) | `final_gpu_validation_B.jsonl`, `assumption_annotation.jsonl` | DeBERTa | CPU | `evaluation/premise_framing/` |
| Fresh full end-to-end natural batch | `scripts/run_final_gpu_validation.py --device cuda` (confirmed flags: `--device`, `--out-prefix`, `--candidate-file`) | fresh candidate selection, evidence, NyayaRAG case files | Qwen 7B + DeBERTa | **GPU, ~34 min** | `evaluation/end_to_end/` |

All commands above were checked against each script's actual `argparse`/`main()` entry
point in Step 0/1's audit, not assumed from documentation alone — flag names quoted are
real. `run_synthetic_stress_eval.py` has no CLI flags at all (confirmed: no `argparse`
import); run it with its built-in defaults.

## Reproduction of existing (already-committed) results vs. new evaluation

Every command above can be pointed at the **existing, frozen** inputs to reproduce
already-published numbers (e.g. confirm 136 usable evidence records, confirm the 420-item
benchmark's stored metrics) before it is ever used to evaluate something new. Do the
reproduction pass first — see `../reports/README.md`'s planned Reproducibility Report.
