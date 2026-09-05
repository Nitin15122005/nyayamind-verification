# GOLD Inputs

**No files are duplicated here.** The two legitimate GOLD fixtures already exist, copied
and hash-verified, at `../../expected_outputs/controlled_benchmark_gold/` and
`../../expected_outputs/synthetic_stress_gold/` (built in STEP 1). This directory
documents them from the **input** side of the same files — each record is simultaneously
an input (premise + hypothesis fed to the NLI verifier) and a gold label (its
`expected_label` / by-construction verdict) — rather than creating a second copy.

## GOLD-01 — Controlled verifier benchmark (n=420)

| | |
|---|---|
| Fixture | `../../expected_outputs/controlled_benchmark_gold/controlled_verifier_benchmark.jsonl` |
| As an **input**: | `evidence_text` (premise) + `hypothesis` fields, fed directly to `src/verifier.py::NLIVerifier.verify(premise, hypothesis)` |
| As an **expected output**: | `expected_label` (ENTAILED / CONTRADICTED / NEUTRAL), assigned by the deterministic construction rule in `scripts/build_controlled_benchmark.py` |
| SHA-256 | `962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99` (identical to source, verified STEP 1 and re-verified STEP 2) |
| Classification | **GOLD** |
| Legitimate use | Genuine accuracy/F1 measurement of the verifier against a known-correct answer |
| Not legitimate | Any claim about accuracy on real, naturally-generated case text (hypotheses here are mechanically constructed, not real model output) |

## GOLD-02 — Synthetic stress set (n=59)

| | |
|---|---|
| Fixture | `../../expected_outputs/synthetic_stress_gold/run_synthetic_stress.jsonl` |
| As an **input**: | `canonical_evidence_text` (premise) + `original_synthetic_text` (the corrupted claim, hypothesis), consumable by the same `verify()` call, or by the full pipeline for correction-triggering tests |
| As an **expected output**: | CONTRADICTED for every record, by construction (one trigger phrase mechanically inverted per record) |
| SHA-256 | `2dba39cc61eb94aa81daeff9817026ace0f531174e9312d49ce12522b3e9b516` (identical to source, verified STEP 1 and re-verified STEP 2) |
| Classification | **GOLD** (narrower scope than GOLD-01: contradiction-recall only, no ENTAILED/NEUTRAL examples) |

## No other dataset may be promoted to GOLD

Every other dataset referenced anywhere in this workspace — the 588-claim aggregate, the
209-claim paired evaluation, every natural batch, every correction/safety dataset, and
all three provisional-annotation files — remains METRIC-ONLY or PROVISIONAL. See
`../metric_only/README.md` and `../provisional/README.md`.
