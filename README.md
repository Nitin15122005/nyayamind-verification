# nyayamind-verification

Field-level **statutory-claim verification and selective correction** for
LLM-generated Indian court judgment summaries, plus a reproduction of the
**LegalSeg / RhetoricLLaMA** rhetorical-role-classification baseline it
builds alongside.

## Project Author Statement — 2026-09-03

**The project author confirms that professional legal review has since been
incorporated into relevant aspects of the project's legal analysis.
Reviewer identities and detailed review records are not included in this
repository.**

This statement reflects the current status communicated by the project
author and should be treated separately from the historical research
findings, dated limitations, experimental records, and reproducibility
documentation contained elsewhere in this repository. It does not modify
or supersede those documented findings, and it does not indicate that
individual, automatically-generated pipeline outputs have received
case-by-case professional legal approval (see "Known limitations" below
and each output record's own `disclaimer` field).

## Project purpose

LLMs asked to summarize Indian court judgments will readily name statutes,
sections, and articles that sound plausible but are wrong, outdated, or
unsupported by the case. This project asks a narrower question than "is the
summary good": for the **Statutory Grounding** field specifically, does each
cited provision actually say what the model claims it says — and can a
verification + selective-correction step fix it without touching anything
else in the field?

## Research contribution

- A deterministic pipeline that generates a statutory-grounding paragraph,
  extracts its individual citation-bearing claims, matches each claim
  against independently-sourced canonical statute text, verifies it with an
  NLI model, and — only for the first flagged claim — regenerates just that
  sentence while leaving the rest of the paragraph untouched.
- A **programmatic** (not prompt-only) scope guard: if a correction attempt
  alters any sentence other than the one it was asked to fix, the pipeline
  detects it and discards the correction rather than shipping it.
- A small, independently-audited canonical statute evidence corpus (100
  most-cited provisions in the source case corpus, cross-checked
  record-by-record against their sources — see `research/data/evidence/README.md`
  for the full audit methodology and known limitations).
- A frozen, documented reproduction of the RhetoricLLaMA baseline
  (`research/baseline/`) this prototype's generation stack inherits its
  quantization/version constraints from.

This is a **v0 research prototype**: every threshold and generation
parameter is a documented, un-calibrated design default (see
`research/prototype/config/prototype.yaml`), not a tuned result. See
"Known limitations" below before drawing conclusions from its output.

## Architecture

```
Case (case_text)
   |
   v
[1] Generate statutory_grounding field   -- Qwen2.5-7B-Instruct, 4-bit, greedy
   v
[2] Extract citation-bearing claims      -- deterministic regex, no LLM
   v
[3] Match each claim to canonical evidence -- exact key match, fuzzy fallback
   v (Mode B/C only)
[4] Verify each claim with NLI           -- MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
   v (Mode C only, first flagged claim)
[5] Regenerate ONLY the flagged sentence -- reuses the loaded generation model
   v
[6] Programmatic scope-violation gate    -- unflagged claims must survive verbatim
   v
[7] Re-verify the corrected sentence
   v
final_field (original | corrected | correction_failed | correction_scope_violation)
```

Full design detail, mode semantics, and every documented v0 simplification:
[`research/prototype/README.md`](research/prototype/README.md).

## Prerequisites

- **GPU is required — there is no CPU fallback.** Both the generator and the
  verifier raise immediately if `torch.cuda.is_available()` is false; this
  is deliberate (a 7B model on CPU would be impractically slow, per the
  source comments), not an oversight.
- Validated hardware: NVIDIA RTX 4050 Laptop GPU, **6GB VRAM**, driver
  supporting CUDA 12.1+. This is a tight VRAM budget by design (Qwen2.5-7B
  4-bit ≈5GB + DeBERTa-v3 fp16 ≈0.3–0.5GB) — closing other GPU-heavy
  applications is recommended before a real run.
- Python 3.11 (pinned to 3.11.9 in the validated environment).
- For Docker: NVIDIA Container Toolkit / a GPU-passthrough-enabled Docker
  runtime (Docker Desktop + WSL2 GPU support on Windows).

## Native setup

```
python -m venv research/.venv
research/.venv/Scripts/pip install -r research/requirements.txt   # Windows
# research/.venv/bin/pip install -r research/requirements.txt      # Linux/macOS
```

Import/config check only — loads no model, downloads nothing:

```
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check
```

Unit tests (mostly no model/GPU/network; one file loads the real NLI
verifier and does require CUDA — see "Reproducibility notes"):

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -v
```

## Docker setup

```
docker compose build
docker compose run --rm app                     # --check only, loads no model
docker compose run --rm app python research/prototype/scripts/run_mvp.py \
    --mode A --num-cases 1 --output research/prototype/outputs/run_A_n1.jsonl
docker compose run --rm app python research/prototype/scripts/run_mvp.py \
    --mode C --num-cases 1 --output research/prototype/outputs/run_C_n1.jsonl
```

The image installs the exact pinned dependency set from
`research/requirements.txt` and downloads **no model weights at build
time**. Qwen2.5-7B-Instruct and the DeBERTa verifier are pulled by
`transformers` on first real run, into a named volume
(`HF_HOME=/root/.cache/huggingface`) that persists across container
restarts. `research/prototype/outputs/` is bind-mounted so run output lands
back on the host. See the `Dockerfile` / `docker-compose.yml` for full
comments.

## HF_TOKEN scope

`HF_TOKEN` is **only** required for `research/baseline/scripts/run_baseline.py`,
which loads the gated `meta-llama/Llama-2-7b-chat-hf`. It is **not** needed
anywhere in the prototype pipeline (Mode A/B/C) — `Qwen/Qwen2.5-7B-Instruct`
and `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` are both public models
loaded with no token. Never hardcode `HF_TOKEN`; export it in your shell or
pass it via `docker compose` (`environment: HF_TOKEN=${HF_TOKEN:-}`, already
wired), which reads it from the host environment at run time only.

## Mode A / B / C commands

| Mode | Generation | Verification | Correction |
|---|---|---|---|
| A | yes | no | no |
| B | yes | yes | no (diagnostic only) |
| C | yes | yes | yes (first flagged claim only) |

```
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --mode A --num-cases 1 --output research/prototype/outputs/run_A_n1.jsonl
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --mode B --num-cases 1 --output research/prototype/outputs/run_B_n1.jsonl
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --mode C --num-cases 1 --output research/prototype/outputs/run_C_n1.jsonl
```

Hard-capped at 5 cases per invocation by design (`MAX_ALLOWED_CASES` in
`run_mvp.py`) — not a performance limit, a deliberate guardrail until a
separate decision is made to scale up.

## Evidence dataset

`research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl`:
a 100-most-cited-provision evidence table, independently audited
record-by-record against its own sources. Only `VERIFIED_EXACT` /
`VERIFIED_CONTENT` records (59 of 63 resolved records) are used as verifier
premises; `SOURCE_ONLY` / `INVALID` / `UNRESOLVED` are excluded by design.
Case text and citation keys come from `research/data/nyayarag/CaseText_Statutes/`
(`L-NLProc/NyayaRAG` on Hugging Face — only citation **keys** are read from
that data, never its own free-text section values). Full audit methodology,
provenance, and caveats: [`research/data/evidence/README.md`](research/data/evidence/README.md).

## Reproducibility notes

- Every generation call records its exact model id, quantization config,
  and generation parameters into the output record's `reproducibility`
  block, alongside installed `torch`/`transformers`/`accelerate`/
  `bitsandbytes`/`peft` versions.
- `accelerate==0.29.3` is a **load-bearing pin**, not an arbitrary choice —
  newer `accelerate` breaks the 4-bit dispatch path against
  `transformers==4.40.2` specifically (see `research/requirements.txt`
  comments and `research/baseline/BASELINE.md`). Do not bump it in
  isolation.
- `research/prototype/tests/test_correction_path_real_integration.py` loads
  the **real** NLI verifier and therefore requires CUDA, unlike the rest of
  the test suite — a CPU-only CI stage will need to exclude it explicitly.
- `baseline/LegalSeg` is tracked as a **Git submodule** pointing at
  [`ShubhamKumarNigam/LegalSeg`](https://github.com/ShubhamKumarNigam/LegalSeg.git),
  not vendored source — run `git submodule update --init` after cloning.
  Its large data/model files (`Data/*.csv`, `saved_models/RhetoricLLaMA/`)
  are **not** part of that repo's committed history and must be obtained
  separately per `research/baseline/README.md` ("Expected model/data
  locations").

## Known limitations

- **NLI verdict ≠ legal correctness.** The verifier reports a small public
  NLI model's statistical confidence, not a lawyer-verified judgment. No
  gold evaluation of verifier accuracy has been run.
- **59-record evidence pool** — most claims in an arbitrary case resolve to
  `NO_EVIDENCE`; case selection filters to cases with ≥1 overlapping
  citation to avoid trivial all-`NO_EVIDENCE` runs.
- **Pre-2024-07-01 canonical text for IPC/CrPC-heavy citations** — nationally
  superseded by the BNS/BNSS as of 2024-07-01; this corpus reflects the
  pre-repeal text.
- **First flagged claim only drives correction** in Mode C — a documented
  v0 simplification, not a bug.
- Full list of documented simplifications and data-provenance caveats:
  [`research/prototype/README.md`](research/prototype/README.md) §"Known
  limitations".

## Citation / prior work

- Baseline model and rhetorical-role task: **LegalSeg**
  ([ShubhamKumarNigam/LegalSeg](https://github.com/ShubhamKumarNigam/LegalSeg)),
  reproduced here at commit `af1b45c52cab22a71ddea0bf13c987741b16f042`
  (frozen record: `research/baseline/BASELINE.md`).
- LoRA adapter: `L-NLProc/LegalSeg_RhetoricLLaMA` on Hugging Face.
- Case/statute data: **NyayaRAG**, `L-NLProc/NyayaRAG` on Hugging Face
  (`3.CaseText_Statutes.zip`).
- Generation model: `Qwen/Qwen2.5-7B-Instruct` (Qwen team).
- Verification model: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`
  (Moritz Laurer).
