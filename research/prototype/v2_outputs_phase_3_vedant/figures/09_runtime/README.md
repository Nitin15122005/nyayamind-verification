# 09_runtime — deliberately empty

**No runtime or resource comparison figure is produced in this package, by design.**

A meaningful ORIGINAL-vs-LATEST runtime comparison cannot be made from this session:

1. Every historical runtime and VRAM number was measured on a CUDA GPU with 4-bit Qwen
   loaded. This machine has no GPU and Qwen is not cached, so nothing equivalent can be
   measured.
2. The fresh timings this package does have are CPU-only NLI timings under a different
   torch/transformers major version, and are not comparable to the historical ones.
3. They are not even safely comparable between arms: in the fresh GOLD-01 run the
   `labeled` arm took 471.5 s against `bare`'s 112.7 s, but that is dominated by longer
   premise strings and by CPU scheduling on a shared machine — not by a meaningful
   algorithmic cost difference. Charting it as 'LATEST is 4x slower' would be misleading.

Raw timings are retained in `metrics/gold01_v2_metrics.json` and
`metrics/gold02_v2_metrics.json` for completeness. No runtime claim is made anywhere in
this package. See `NOT_GENERATED_REGISTER.md` §4.
