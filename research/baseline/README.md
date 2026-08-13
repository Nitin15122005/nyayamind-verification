# RhetoricLLaMA Baseline — Reproduction Environment

## Environment setup

```
python -m venv research/.venv
research/.venv/Scripts/pip install -r research/requirements.txt
```

## Required environment variable

```
HF_TOKEN   # Hugging Face access token with access to meta-llama/Llama-2-7b-chat-hf
```

## Expected model/data locations

- LoRA adapter: `baseline/LegalSeg/saved_models/RhetoricLLaMA/` (adapter_config.json, adapter_model.safetensors, tokenizer.json, tokenizer_config.json, special_tokens_map.json — from `L-NLProc/LegalSeg_RhetoricLLaMA`)
- Test data: a CSV with a `Text` column (e.g. `baseline/LegalSeg/Data/test.csv` or `baseline/LegalSeg/Data/RhetoricLLaMA/test.csv` — from `L-NLProc/LegalSeg_CSV`)

Neither is downloaded by this environment; both must be placed at the paths above (or pointed to via CLI args) before running.

## Baseline execution command

```
research/.venv/Scripts/python research/baseline/scripts/run_baseline.py \
  --input-csv baseline/LegalSeg/Data/test.csv \
  --output-csv research/baseline/outputs/RhetoricLLaMA_predictions.csv \
  --model-id baseline/LegalSeg/saved_models/RhetoricLLaMA
```
