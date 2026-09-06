# NyayaMind Prototype — Faculty Executive Summary

*One-page summary. Full detail in `FACULTY_EVALUATION_REPORT.md`; all figures cited
here are traceable via claim ID `[C##]` to `FINAL_CLAIM_REGISTER.csv`.*

## What this project is

A field-level statutory-grounding verification and selective-correction layer over
Qwen2.5-7B-Instruct generation and a DeBERTa-v3 NLI verifier, evaluated across 12
sequential steps of increasingly rigorous, independently-checked testing.

## Headline results

- **Controlled benchmark (GOLD-01, n=420)**: verifier accuracy 73.3%→97.1%, macro F1
  74.9%→96.8% under labeled premise framing (McNemar p=4.2×10⁻²³). The strongest
  statistical result in the project — but on a curated benchmark, not real generated
  text. `[C01-C04]`
- **Real natural data (209-claim paired set)**: evidence-v1 increased observed evidence
  coverage 63.2%→70.3% (McNemar p=0.0003, zero regressions) — a real, reproducible
  retrieval-coverage finding, **not** an accuracy or correctness claim (no ground truth
  exists for natural claims). `[C07, C08]`
- **GPU capability, now demonstrated**: a second machine with a real NVIDIA GPU (RTX
  4050 Laptop, 6 GB) was validated. Real Qwen generation and the full correction
  pipeline execute successfully on it. Two historical experiments — a 10-case targeted
  correction validation and the 209-claim/50-case two-arm generation experiment — were
  **exactly reproduced**, byte-for-byte, against 2026-08-27 historical runs. `[C09-C13]`
  This is new since the STEP 1-9 evaluation, which ran on a machine with **no** NVIDIA
  GPU (a fact about that specific machine, permanent and unchanged, not a current
  project-wide limitation).
- **Correction safety**: 0 unsafe corrections observed across 122 tested attempts
  project-wide (an observed count, not a guarantee). Corrections ship rarely on natural
  data — 1 of 56 cumulative attempts (1.8%), a figure that is historical-only and cannot
  currently be freshly re-derived (see limitations). `[C20, C22]`
- **Software correctness**: 205/205 tests pass, unchanged across every step on both the
  CPU-only and GPU-equipped machines; none of the 205 tests require a GPU to run. `[C23, C26]`

## What is NOT claimed

- No natural-data accuracy or F1 figure exists anywhere in this project.
- No legal-correctness claim is made — no independent lawyer/human ground truth exists.
- No claim that correction is "solved," or that safety is universally guaranteed.
- No joint four-lever interaction experiment exists; no such effect is inferred.
- The cumulative 1/56 correction rate was **not** freshly reproduced or approximated —
  its underlying aggregation protocol is no longer recoverable from the repository.

## Bottom line

The project's GOLD-benchmark and natural-data-coverage findings are unchanged and
independently reconciled with zero discrepancies found against source artifacts. The
one open question from the prior evaluation phase — whether real GPU-dependent
generation and correction could be executed and reproduced at all — has now been
answered affirmatively wherever a recoverable protocol existed. Two items remain
genuinely unavailable for documented structural reasons (the cumulative 1/56 rollup, and
the joint four-lever experiment) — not failures, and not something further effort on
this workspace alone would resolve.
