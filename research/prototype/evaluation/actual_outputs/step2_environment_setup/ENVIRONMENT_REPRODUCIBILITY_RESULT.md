# STEP 2 — Environment Reproducibility Result

Produced: 2026-09-05, repo commit `ccbe73f3c6c504c4f7d84cd8e8c9c128397f56a3`.
This is the direct answer to STEP 1's blocker (item 4): *can the canonical
Python/dependency environment actually be reproduced on this machine?*

**Answer: partially — with one clear, hardware-level exception, reported here exactly
as found, not worked around.**

---

## What succeeded — the Python/dependency layer is fully, exactly reproducible

1. **Python 3.11.9 was already present on this machine** (not the system default —
   discovered via `py -0p` at `C:\Users\darsh\AppData\Local\Python\pythoncore-3.11-64\python.exe`,
   alongside a default system Python 3.14 that would NOT have worked). This is the exact
   patch version REPRODUCIBILITY.md pins.
2. **`research/.venv/` was created fresh** using that interpreter (the one explicit
   exception to "write only under `testing/`" that STEP 1 authorized).
3. **`pip install -r research/requirements.txt` succeeded completely, exit code 0**,
   installing every package at **exactly** its pinned version — no substitutions, no
   `--no-deps`, no relaxed constraints: `torch==2.2.2+cu121`, `transformers==4.40.2`,
   `accelerate==0.29.3`, `bitsandbytes==0.43.1`, `peft==0.10.0`, `trl==0.8.6`,
   `sentencepiece==0.2.2`, `PyYAML==6.0.3`, `pytest==9.1.1`, `numpy==1.26.4`,
   `pandas==2.2.2`, `datasets==2.19.1`, `tqdm==4.66.4`. Full log:
   `pip_install_log.txt`.
4. **`run_mvp.py --check` passes**, correctly reporting 136 usable evidence records
   (confirming `use_evidence_v1=True` resolves correctly in this fresh environment).
5. **The full existing test suite passes 205/205** (46.16s, 3 warnings — all
   deprecation/cache-symlink notices, not failures), including
   `test_correction_path_real_integration.py`, which downloads and runs the real
   `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` model on CPU. This is an **exact**
   match to REPRODUCIBILITY.md's documented expected result, with zero test
   modifications. Full log: `pytest_run_log.txt`.

**Conclusion for this layer**: the documented Python/dependency environment is not
aspirational — it is genuinely, exactly reproducible on this machine, and every CPU-only
claim in this repository's test suite and documentation now has a real, fresh, local
confirmation behind it (not just a re-reading of prior committed results).

---

## What did NOT succeed, and cannot succeed on this machine — the GPU layer

**This machine has no NVIDIA GPU.** Confirmed via Windows WMI
(`Get-CimInstance Win32_VideoController`): the only video controller present is an
**AMD Radeon (TM) Graphics** integrated GPU. There is no `nvidia-smi` anywhere on the
system.

Independently confirmed at the software level:
```
research/.venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available())"
→ False
```
and `bitsandbytes` itself prints at import time: *"The installed version of bitsandbytes
was compiled without GPU support. 8-bit optimizers, 8-bit multiplication, and GPU
quantization are unavailable."*

**This is a hardware-absence blocker, not a version/configuration/software problem.**
Reinstalling, changing torch versions, or adjusting `bitsandbytes` build flags cannot fix
it — there is no CUDA-capable device on this machine for any of these packages to use.

### Exact, concrete consequence for this project's pipeline

Per the Step 0 audit's pipeline trace, `src/generator.py::StatuteGroundingGenerator.load()`
and `src/corrector.py::SelectiveCorrector` (which reuses the generator's model)
**explicitly raise `RuntimeError` if CUDA is unavailable, by design — there is no CPU
fallback anywhere in the code for these two stages.** Concretely, on this machine:

| Can run | Cannot run |
|---|---|
| Full unit/integration test suite (205/205, CPU) | `run_mvp.py --mode {A,B,C}` (real generation) |
| `run_mvp.py --check` | `scripts/run_final_gpu_validation.py` |
| Controlled NLI benchmark build + evaluation (DeBERTa, CPU) | `scripts/run_natural_candidates_50_gpu.py` |
| Threshold-sensitivity sweep, scope-check replays (deterministic, no model) | `scripts/run_labeled_correction_validation_gpu.py` |
| CPU-only bare-vs-labeled re-verification scripts | `scripts/run_synthetic_stress_eval.py` (imports the real generator) |
| `final_demo_pack`/`final_comparison` figure regeneration (matplotlib only) | Any fresh natural-batch generation or correction |

In short: **every CPU-only claim in this project can now be independently verified on
this machine, right now. Every GPU-only claim (all real Qwen-7B generation and
correction) cannot be regenerated on this machine at all, regardless of environment
setup quality** — reproducing those would require either different hardware (an
NVIDIA GPU, as the original RTX 4050 Laptop GPU used to build this project's evaluation
record) or a remote/cloud GPU environment.

---

## What this means for the rest of STEP 2 / later steps

- Do not attempt to "work around" the missing GPU (no CPU-forced generation, no swapping
  in a different, smaller generation model that changes the pipeline's own
  specification) — that would silently invalidate any result produced that way and
  contradict STEP 1's explicit instruction not to hide or bypass this blocker.
- All CPU-reproducible evaluation/ablation work planned in `../../evaluation/README.md`
  and `../../ablation/README.md` can now proceed for real, in this exact venv.
- Any GPU-dependent work (a fresh joint-lever experiment, regenerating natural batches)
  remains blocked on this machine specifically, and must be either deferred, run
  elsewhere, or explicitly acknowledged as out of scope for this environment.
