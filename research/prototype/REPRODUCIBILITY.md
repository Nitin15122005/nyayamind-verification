# Reproducibility Guide

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Written 2026-08-27, alongside the final production-configuration decision (`FINAL_PRODUCTION_CONFIG.md`)
and the consolidated research results (`outputs/final_research_results.md`). This is the
authoritative, current reproducibility reference for the project — `README.md` describes the
architecture; this file describes exactly how to check it, run it, and reproduce every reported
number.

---

## 1. Environment

| | |
|---|---|
| OS this was built/run on | Windows 11, RTX 4050 Laptop GPU (6 GB dedicated + shared-memory fallback) |
| Python | **3.11.9** (`research/.venv`) |
| CUDA | 12.1 (`torch==2.2.2+cu121`) |
| Key pinned packages | `torch==2.2.2+cu121`, `transformers==4.40.2`, `accelerate==0.29.3`, `bitsandbytes==0.43.1`, `peft==0.10.0`, `trl==0.8.6`, `sentencepiece==0.2.2`, `numpy==1.26.4` — see `research/requirements.txt` for the complete pinned list and *why* each version is pinned (several are load-bearing compatibility constraints, not arbitrary choices). |
| Setup | `pip install -r research/requirements.txt` into a venv at `research/.venv` (the path every command below assumes — adjust if yours differs) |
| Docker alternative | `docker-compose.yml` + `Dockerfile` — `gpus: all` requires the NVIDIA Container Toolkit; only used for `run_mvp.py --check` by default, see the file's own comments |

**This project does not pin exact model-weight versions** — `Qwen/Qwen2.5-7B-Instruct` and
`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` are pulled from the Hugging Face Hub at whatever
revision is current when first loaded (no `revision=` pin in `src/generator.py`/`src/verifier.py`).
A future upstream weight update could in principle shift generation/verification output slightly;
this has not been a problem in practice across this project's history but is not hash-pinned.

---

## 2. What needs a GPU vs. what runs on CPU-only

| Class | GPU required? | Examples |
|---|---|---|
| Unit/integration tests | **No** — CPU only, no network (except `test_correction_path_real_integration.py`, which loads the real ~184M-parameter DeBERTa verifier on CPU if no GPU is present — small, fast, no 7B model involved) | `pytest research/prototype/tests/` |
| `run_mvp.py --check` | **No** — imports + config parse + evidence-file existence check only, loads no model | `run_mvp.py --check` |
| Verification-only replays/comparisons | **No** — DeBERTa (~184M params) runs fine on CPU in seconds-to-low-minutes for tens to hundreds of claims | `compare_final_validation_labeled_cpu.py`, `compare_assumption_gold_bare_vs_labeled.py`, `compare_premise_framing_synthetic.py`, `analyze_threshold_sensitivity.py`, `audit_no_evidence_taxonomy_v2.py` |
| Real generation (Mode A/B/C) and real correction | **Yes** — `Qwen/Qwen2.5-7B-Instruct`, 4-bit, requires CUDA; every generator/corrector loader in `src/generator.py` refuses to fall back to CPU by design | `run_mvp.py --mode {A,B,C}`, `run_final_gpu_validation.py`, `run_natural_candidates_50_gpu.py`, `run_labeled_correction_validation_gpu.py`, the `framing_comparison_gpu_*` family |

A useful pattern this project uses repeatedly (and that `run_labeled_correction_validation_gpu.py`
and `compare_final_validation_labeled_cpu.py` demonstrate explicitly): once real generated text
exists on disk, re-verifying it under a different config is a CPU-only, GPU-free operation — only
*generation* and *correction* (both Qwen calls) genuinely require the GPU. Prefer this pattern for
any future ablation before reaching for a new full GPU run.

---

## 3. Exact commands

All commands below assume the repo root as the working directory and `research/.venv/Scripts/python.exe`
as the interpreter (Windows; substitute `research/.venv/bin/python` on Linux/macOS).

### Tests (CPU-only, no GPU, no network — safe to run anywhere)

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
```

Expected: **205 passed** (as of 2026-08-27; the count grows as tests are added — treat any
failure as a real regression, not flakiness. The suite is deterministic).

### Config/import check (no model loaded)

```
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check
```

### Reproducing the final production evidence pool (CPU-only)

```
research/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'research/prototype')
from src.data_loader import load_usable_evidence_from_config
import yaml
cfg = yaml.safe_load(open('research/prototype/config/prototype.yaml', encoding='utf-8'))
_, pool = load_usable_evidence_from_config(cfg, '.')
print(len(pool), 'usable evidence records')  # expect 136
"
```

### Reproducing the CPU-only bare-vs-labeled and assumption-gold comparisons

These reuse already-generated text/evidence already committed under `outputs/` — no GPU, a few
seconds to a couple of minutes on CPU:

```
research/.venv/Scripts/python.exe research/prototype/scripts/compare_final_validation_labeled_cpu.py
research/.venv/Scripts/python.exe research/prototype/scripts/compare_assumption_gold_bare_vs_labeled.py
research/.venv/Scripts/python.exe research/prototype/scripts/audit_no_evidence_taxonomy_v2.py
```

### Reproducing the final GPU experiments (requires CUDA + ~15-35 min each)

**Not required to trust the committed results** — these regenerate real Qwen output, which is
greedy/deterministic given the fixed seed (42) but is not guaranteed byte-identical across
different GPU/driver/library versions. Re-run only to independently verify or extend:

```
# ~34 min on an RTX 4050: 50 new natural cases, two arms (baseline vs. improved config)
research/.venv/Scripts/python.exe research/prototype/scripts/run_final_gpu_validation.py --device cuda

# ~2 min: targeted correction-only validation under labeled framing (reuses Arm B's generated text)
research/.venv/Scripts/python.exe research/prototype/scripts/run_labeled_correction_validation_gpu.py
```

### Selecting a fresh, disjoint natural-case batch (CPU-only, no GPU, no generation)

```
research/.venv/Scripts/python.exe research/prototype/scripts/select_natural_candidates.py --out-suffix _mybatch
```

`PREVIOUSLY_EVALUATED_SOURCES` inside that script is the authoritative, hand-maintained list of
every prior natural-batch output file — update it (append, never remove) before selecting a new
batch, exactly as done for `_batch2` and `_final_validation`.

---

## 4. Where final artifacts land

| Artifact | Path |
|---|---|
| Final production config | `research/prototype/config/prototype.yaml` |
| Final config decision record | `FINAL_PRODUCTION_CONFIG.md` (repo root) |
| Final consolidated metrics (machine-readable) | `research/prototype/outputs/final_metrics.json` |
| Final consolidated research narrative | `research/prototype/outputs/final_research_results.md` |
| Final limitations / future scope | `research/prototype/outputs/final_limitations_and_future_scope.md` |
| Evidence v1 independent audit | `research/prototype/outputs/evidence_v1_independent_audit.md` |
| Final paired-arms GPU experiment | `research/prototype/outputs/final_gpu_validation.md` (+ `_A.jsonl`, `_B.jsonl`, `_corrections_detail.jsonl`, `_metrics.json`) |
| This document | `research/prototype/REPRODUCIBILITY.md` |

`outputs/` also contains a substantial amount of earlier-phase experimental history (synthetic
stress runs, prior natural batches, threshold sensitivity sweeps, parser-fix diagnostics) that the
final documents above cite as supporting evidence — nothing there was deleted or altered during
this reproducibility pass except two dated, logged, evidence-based corrections to
`research/data/evidence/canonical_statutes_v1.jsonl`/`evidence_audit_v1.jsonl` (see
`research/data/evidence/README_v1.md`'s "2026-08-27 independent audit addendum").

---

## 5. Seeds and key configuration values (as shipped)

| | Value |
|---|---|
| Global seed | `42` (`config/prototype.yaml: seed`) |
| Generation | greedy (`do_sample: False`), `max_new_tokens: 200` |
| Correction | greedy, `max_new_tokens: 220` |
| `verification.premise_framing` | **`labeled`** (production default since 2026-08-27) |
| `verification.confidence_threshold` | `0.70` (unchanged; see `outputs/threshold_sensitivity_analysis.md`) |
| `use_evidence_v1` | **`true`** (production default since 2026-08-27; 136-record pool) |
| `correction.atomic_scope_check` | **`"assertion_spans"`** (production default since 2026-08-27) |
| `correction.narrow_reverification_hypothesis` | **`true`** (production default since 2026-08-27) |

Every one of these has a dated, evidence-cited comment directly in `config/prototype.yaml`
explaining why it is set the way it is, and `FINAL_PRODUCTION_CONFIG.md` is the full decision
record. To reproduce any **pre-2026-08-27** committed result byte-for-byte, set all four back to
their old values (`use_evidence_v1: false`, `premise_framing: "bare"`,
`atomic_scope_check: false`, `narrow_reverification_hypothesis: false`) — every historical output
in `outputs/` was produced under exactly that combination, and
`tests/test_premise_framing_production.py::test_shipped_config_can_still_reproduce_every_pre_2026_08_27_committed_output`
pins that this combination still resolves correctly through the current code.

---

## 6. Known reproducibility caveats

- **`research/prototype/scripts/build_evidence_v1.py` is not re-runnable from a clean checkout.**
  It reads from a hardcoded, session-specific scratch path (`SCRATCH` at the top of the file) that
  contained the raw research-agent output batches for the v1 evidence build — that scratch space
  no longer exists on any machine. The script is retained as a **methodology record** (it
  documents exactly how `canonical_statutes_v1.jsonl`/`evidence_audit_v1.jsonl` were derived and
  audited), not as a runnable pipeline step. The data it produced is already committed; nothing
  needs to be regenerated from it.
- **`research/data/nyayarag/`** (the NyayaRAG case source JSON) was originally populated by
  copying files already extracted in an earlier session's scratch space, not a fresh download
  performed by any committed script. If missing in a new environment, re-obtain
  `3.CaseText_Statutes.zip` from `L-NLProc/NyayaRAG` on Hugging Face (see `README.md` §"Data
  sources"). No committed script downloads it automatically.
- **Model weights are not hash-pinned** (§1) — real-GPU reruns are expected to be behaviorally
  close to, but not guaranteed byte-identical to, the committed results.
- **`baseline/LegalSeg`** is a separate git submodule (the RhetoricLLaMA baseline reproduction)
  with its own, independent reproducibility story documented in `research/baseline/BASELINE.md` —
  out of scope for this document, which covers `research/prototype/` only.
