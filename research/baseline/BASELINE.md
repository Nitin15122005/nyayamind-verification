# RhetoricLLaMA Baseline — Frozen Reproduction Record

This document freezes the environment and configuration under which the
RhetoricLLaMA baseline was first successfully reproduced (one-row smoke
test). It is a record, not a script — nothing here is executed automatically.

## Repository

- Baseline source: `baseline/LegalSeg` (git submodule/checkout of
  `https://github.com/ShubhamKumarNigam/LegalSeg.git`)
- Commit: `af1b45c52cab22a71ddea0bf13c987741b16f042` (2026-06-04 15:39:11 +0530)
- `baseline/LegalSeg` was not modified to produce this reproduction.

## Environment

| Component | Value |
|---|---|
| Python | 3.11.9 |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU (6 GB VRAM) |
| GPU driver | 592.82 |
| CUDA (driver-reported) | 13.1 |
| CUDA (PyTorch build) | 12.1 |
| torch | 2.2.2+cu121 |
| transformers | 4.40.2 |
| accelerate | 0.29.3 |
| bitsandbytes | 0.43.1 |
| peft | 0.10.0 |

`accelerate` is pinned to `0.29.3` (not the newest release) — see
[research/requirements.txt](../requirements.txt) for why: newer `accelerate`
versions gate `dispatch_model()`'s 4-bit force-hooks path on
`model.is_loaded_in_4bit`, which `transformers==4.40.2` only sets *after*
`dispatch_model()` runs, causing a spurious
`ValueError: .to is not supported for 4-bit or 8-bit bitsandbytes models`.
`accelerate==0.29.3` gates on `model.is_quantized` instead, which is set in
time, so this pin is required for this transformers version — not an
arbitrary choice.

## Model and adapter

- Base model: `meta-llama/Llama-2-7b-chat-hf` (gated; requires HF access grant)
- LoRA adapter: `L-NLProc/LegalSeg_RhetoricLLaMA`, loaded locally from
  `baseline/LegalSeg/saved_models/RhetoricLLaMA/`
  (`adapter_config.json`, `adapter_model.safetensors`, `tokenizer.json`,
  `tokenizer_config.json`, `special_tokens_map.json`)
- Loaded via `peft.AutoPeftModelForCausalLM.from_pretrained(...)`, which
  resolves the base model from the adapter's `adapter_config.json`.

## Inference script

`research/baseline/scripts/run_baseline.py` — a CLI wrapper around the
published `baseline/LegalSeg/code/RhetoricLLaMA/inference.py` logic. Behavior
preserved exactly from the original script (see file header for the list of
non-behavioral changes: CLI args instead of hardcoded paths, `AutoPeftModelForCausalLM`
instead of a plain `AutoModelForCausalLM.from_pretrained` on an adapter-only
checkpoint dir, `HF_TOKEN` read from environment instead of hardcoded).

## Prompt template

```
 ### Instructions:
    Analyze the given legal sentence and predict its rhetorical role as a number: None-0, Facts-1, Issue-2, Arguments of Petitioner-3, Arguments of Respondent-4, Reasoning-5, Decision-6.
    Note: The response must only contain a number between 0 and 6 representing the label of sentence.     ### Input:
  case_proceeding: <{TEXT}>

  ### Response:
  ```

(`{TEXT}` is substituted with the preprocessed sentence text.)

## Preprocessing

Whitespace-tokenize the input `Text`, keep only the **last 1000 whitespace
tokens**, rejoin with a single space. No other normalization.

## Quantization configuration

```python
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)
```

## Generation configuration

- `max_new_tokens=100`
- All other generation parameters left at HF greedy defaults (no sampling
  parameters set)
- Raw decoded output is stored unmodified — no re-mapping or constraining of
  the label text.

## Output schema

CSV with the input columns (`Index`, `Text`, `Label`) plus one appended
column:

| Column | Description |
|---|---|
| `Index` | passthrough from input CSV |
| `Text` | passthrough from input CSV (post-preprocessing, i.e. truncated) |
| `Label` | passthrough from input CSV (ground-truth rhetorical role, if present) |
| `llama_p` | raw decoded model generation for that row |

## Known baseline behavior observed in the smoke test

On the one-row smoke test (`baseline/LegalSeg/Data/test.csv` row `Index=6408`,
`Text=" Dr Dhananjaya Y Chandrachud, J 1."`), the model's raw greedy generation
degenerated into a repeated pattern rather than stopping after a single label:

```
None-0

### Response:
None-0

### Response:
...(repeated up to max_new_tokens=100)...
```

This is the original script's documented behavior (raw decoded generation,
unmodified/unconstrained) and is not a bug introduced by this reproduction —
noted here as a known characteristic of this baseline, not something this
freeze attempts to fix.

## Frozen smoke-test configuration and result

- Input: a single-row CSV built from row 0 of `baseline/LegalSeg/Data/test.csv`
  (temporary, deleted after the test — not part of this repo)
- Command:
  ```
  research/.venv/Scripts/python research/baseline/scripts/run_baseline.py \
    --input-csv <one-row-temp.csv> \
    --output-csv <one-row-output.csv> \
    --model-id baseline/LegalSeg/saved_models/RhetoricLLaMA
  ```
- Result: **SUCCESS**
  - Base model loaded from local Hugging Face cache (no re-download)
  - LoRA adapter loaded
  - Tokenizer loaded
  - Model correctly placed on the RTX 4050 (single-GPU `device_map="auto"`,
    4-bit quantized, no `.to()` device-placement error)
  - One generation completed (~9s for 100 new tokens)
  - Output CSV had the correct 4-column schema described above, with
    `llama_p` populated with the raw decoded generation shown above

No dataset-wide run, no training, and no output verification/correction logic
were performed as part of this reproduction. `HF_TOKEN` is required as an
environment variable to run this script but is never written to disk or
logged by it.
