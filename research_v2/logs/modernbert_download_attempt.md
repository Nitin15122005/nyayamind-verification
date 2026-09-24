# ModernBERT model fetch attempts

Requested checkpoint: `tasksource/ModernBERT-large-nli` (not substituted). The Hugging Face repository reports a 1.59 GB checkpoint. The first `run_all.py --device cuda:0` attempt completed the fresh DeBERTa GOLD-01 baseline (n=420), then stalled fetching ModernBERT. Subsequent checks found incomplete safetensors fragments (335,331,183 bytes and 178,257,920 bytes) with no progress across repeated checks. A retry with Xet high-performance enabled also stalled. A further retry with `HF_HUB_DISABLE_XET=1` created a zero-byte incomplete fragment and made no measurable progress. Both retries were stopped before inference.

This is a checkpoint transfer failure, not an inference, label-map, or OOM result. No ModernBERT inference ran, its runtime label map was not verified, and no alternate checkpoint was used. Qwen3 weight download was not attempted because the ModernBERT prerequisite blocked the paired model run.

Commands attempted:

- `py -3.11 research_v2/scripts/run_all.py --device cuda:0`
- `py -3.11 research_v2/scripts/run_sanity.py --model v2 --device cuda:0` with `HF_XET_HIGH_PERFORMANCE=1`
- `py -3.11 research_v2/scripts/run_sanity.py --model v2 --device cuda:0` with `HF_HUB_DISABLE_XET=1`

The incomplete Hugging Face cache resides outside Git and was not copied into the repository.
