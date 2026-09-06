# STEP 10 / STEP 10B — GPU Ablation Status Update

Revisits STEP 7's (`ABLATION_EVIDENCE_GRADES.md`,
`ABLATION_RESULTS.md` — both in this directory) GPU-dependent findings in light of what
STEP 10 actually executed on GPU hardware. No evidence grade is upgraded
except where a specific historical experiment was, itself, freshly and
successfully reproduced this step — see `../evaluation/GPU_REPRODUCTION_CROSSCHECK.md`
for the underlying comparison.

| STEP 7 lever | STEP 7 grade | GPU-dependent? | STEP 10/10B status | Notes |
|---|---|---|---|---|
| Evidence v0-vs-v1 (209-claim paired) | SUPPORTED (A) | Underlying generation: yes (real Qwen); the v0-vs-v1 *evidence-coverage comparison itself*: no — verification-only, CPU DeBERTa | **FRESH GPU REPRODUCTION (generation) + HISTORICAL CPU re-derivation (STEP 6, unchanged)** | STEP 6 already freshly reproduced the CPU-side evidence-matching/verification comparison from the ORIGINALLY-STORED generation output. STEP 10B went one level deeper and freshly regenerated the underlying Qwen output itself (`scripts/run_final_gpu_validation.py`, 50 cases, 209 claims) — **exact reproduction**, byte-for-byte identical generated text for all 50 cases, identical evidence-match/verdict/correction counts to the historical run. See `../evaluation/GPU_REPRODUCTION_CROSSCHECK.md` Experiment 3. Grade is **not** upgraded — the underlying finding (McNemar χ²=13.07, p≈0.0003 on the paired evidence-coverage shift) was already SUPPORTED from STEP 6's fresh CPU re-derivation; STEP 10B's contribution is confirming the GPU generation step that fed it is itself independently reproducible on a second machine, not new statistical evidence. |
| Premise framing (GOLD-01, controlled) | SUPPORTED (A) | No — CPU DeBERTa only | **HISTORICAL ONLY (unchanged)** | Same as above; not GPU-dependent. |
| Claim parser fix | SUPPORTED (B) | No | **HISTORICAL ONLY (unchanged)** | Not GPU-dependent. |
| Confidence threshold | DESCRIPTIVE (B) | No | **HISTORICAL ONLY (unchanged)** | Descriptive sweep over stored CPU verification data. |
| Atomic scope check (assertion_spans) | DIAGNOSTIC (C) | No — pure Python replay | **HISTORICAL ONLY (unchanged)** | STEP 7 already freshly replayed this on CPU. |
| Narrow re-verification | DIAGNOSTIC (C) | Partially — the 3 cited cases involve real Qwen-generated corrected text, but re-verification itself is a CPU/GPU DeBERTa call, not regenerated | **NOT EXECUTED THIS STEP** | STEP 7 marked this narrative-only, not re-derivable from raw per-case data without ambiguity; STEP 10 did not attempt to resolve that ambiguity. Remains DIAGNOSTIC (C), HISTORICAL. |
| **Correction levers (targeted correction-validation, GPU)** | DIAGNOSTIC (C) | **Yes — real Qwen correction calls** | **FRESH GPU REPRODUCTION** | Freshly reproduced this step, exact match (10/10 cases, identical status per case, byte-identical corrected text for all 10, 1 shipped, 0 unsafe). See `../evaluation/GPU_REPRODUCTION_CROSSCHECK.md` Experiment 1. Grade is **not** upgraded from DIAGNOSTIC — n=10 pre-selected cases remains too small and too narrowly selected (only cases where labeled framing flagged a claim) to support a stronger evidence grade; what changed is that this specific experiment is now independently confirmed reproducible on a second machine, not that its statistical power increased. |
| Cumulative correction rate (1/56) | Reported as a funnel stage, not graded as a lever | Yes — depends on historical Qwen correction calls across the project's full history | **PROTOCOL INSUFFICIENT (STEP 10B), NOT RE-DERIVED** | STEP 10 ran two new, smaller correction populations (n=5 smoke test with 1 trigger; n=10 targeted, exactly reproducing the historical 10-case result); STEP 10B added a third (5-trigger 209-claim experiment, also exact). STEP 10B explicitly investigated whether the pooled 56-attempt cumulative figure itself could be freshly reproduced and found it cannot: `final_metrics.json`'s own provenance names an ad-hoc, never-committed "build_final_metrics analysis" script with no per-constituent breakdown preserved, and no such script exists in the repository. Reconstructing it would require re-running every GPU correction experiment in the project's history. See `../evaluation/GPU_REPRODUCTION_CROSSCHECK.md`, "Cumulative correction rate" section. |
| Joint four-lever isolation | NOT_ISOLABLE (E, does not exist) | N/A | **REMAINS UNAVAILABLE** | See `JOINT_FOUR_LEVER_STEP10.md` / STEP 10 Phase 15 finding below — no protocol exists in the repository; none was created. |

## Summary

**STEP 10**: exactly one GPU-dependent historical finding — the targeted
labeled-framing correction-validation experiment — was freshly reproduced,
exact-match classification.

**STEP 10B**: a second, larger GPU-dependent historical finding — the
209-claim (50-case, two-arm) evidence-v0-vs-v1 generation experiment that
originally produced `outputs/final_gpu_validation_{A,B}.jsonl` — was freshly
reproduced, also an exact match (byte-for-byte identical generated text for
all 50 cases; identical evidence-match, verdict, and correction counts in
both arms). STEP 10B also investigated the pooled cumulative 1/56 correction
figure and determined it is **PROTOCOL INSUFFICIENT** for fresh
reproduction — a rollup with no recoverable single script or per-constituent
breakdown, not a bounded experiment.

All other STEP 7 findings remain either not GPU-dependent (unaffected) or
HISTORICAL ONLY / NOT EXECUTED / PROTOCOL INSUFFICIENT, matching STEP 7's
own classification. No evidence grade in `ABLATION_EVIDENCE_GRADES.md` is
changed by STEP 10 or STEP 10B; these steps only add "freshly reproduced on
GPU" annotations to two existing findings (one DIAGNOSTIC, one SUPPORTED)
and an explicit non-reproducibility finding for the cumulative figure.
