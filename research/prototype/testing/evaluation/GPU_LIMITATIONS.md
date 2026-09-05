# GPU Limitations (STEP 6)

- **NVIDIA GPU available: NO** (unchanged since STEP 2 — this machine has an AMD Radeon
  integrated GPU only).
- **Qwen generation executed: NO.**
- **Qwen correction executed: NO.**

## CPU-safe stages executed (fresh, this step)

- Claim parsing (`src/claim_parser.py::extract_claims`) — deterministic, re-run on all
  133 distinct historical generated texts for the 588-claim aggregate.
- Evidence matching (`src/evidence_matcher.py::match_evidence`) — deterministic, re-run
  for the 588-claim aggregate (current v0+v1 pool) and for both arms of the 209-claim
  paired set (Arm A against its own original v0-only pool, Arm B against the current
  v0+v1 pool).
- NLI verification (`src/verifier.py::NLIVerifier`, real MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli,
  `device="cpu"`) — real model, freshly run for every evidence-matched claim in both the
  588-claim aggregate and the 209-claim paired set, under the current production
  `premise_framing="labeled"`.

## GPU-dependent stages not executed

- **Generation** (`src/generator.py::StatuteGroundingGenerator`, Qwen2.5-7B-Instruct) —
  hard-requires CUDA, no CPU fallback exists in the code. Every generated text analyzed
  in this step is historical, produced in a prior GPU session; no new text was generated.
- **Correction** (`src/corrector.py::SelectiveCorrector`) — reuses the generation model,
  same hard CUDA requirement. This step performs no fresh correction of any kind;
  `outputs/final_gpu_validation_corrections_detail.jsonl` and equivalent historical
  correction records are only tabulated descriptively (status counts) where analyzed at
  all, never regenerated.

## Explicit separation enforced throughout this step's artifacts

| Category | Meaning | Where it appears |
|---|---|---|
| **A. FRESH CPU-EXECUTED RESULTS** | Computed by this step's own scripts, this run, on this machine, CPU-only | 588-claim results (`claims_588_*`), 209-paired `fresh_*` columns and evidence/verdict re-derivations |
| **B. HISTORICAL GPU-DEPENDENT RESULTS** | Originally produced by a real Qwen generation/correction run on different (GPU) hardware, in a prior session | The underlying `generated_field.text` in every source file; the 209-paired `historical_*` columns; all natural-batch verdicts tabulated in `batches_analysis.json` |
| **C. NOT EXECUTED ON THIS MACHINE** | Cannot be run here at all | Any fresh generation or fresh correction of any kind |

No artifact in this step claims GPU execution, and no historical GPU-dependent result is
described as "fresh" anywhere.
