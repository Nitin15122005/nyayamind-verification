# Prototype v0 — Statutory-Claim Verification + Selective Correction

Field-level verification and selective correction for the "Statutory
Grounding" field of a generated Indian court judgment summary: generate the
field, extract its statutory claims, match each claim against independently
sourced canonical statute text, verify it with an NLI model, and — in Mode
C only — regenerate just the claims flagged as unsupported or contradicted.

Nothing in `config/prototype.yaml` is a tuned/calibrated value except where
the file marks it "fixed by design" — thresholds and generation params are
v0 defaults from the approved design doc, not results of a calibration run.

## Architecture

```
Case (case_text)
   |
   v
[1] StatuteGroundingGenerator.generate()   -- src/generator.py
   |  Qwen2.5-7B-Instruct, 4-bit, greedy decoding, fixed seed
   v
generated_field.text  (one paragraph, statutory grounding only)
   |
   v
[2] claim_parser.extract_claims()          -- src/claim_parser.py
   |  deterministic: split into sentences, keep only sentences with an
   |  explicit "Section/Article/... N of/in <Act>" citation
   v
claims[]  (one Claim per citation-bearing sentence)
   |
   v
[3] evidence_matcher.match_evidence()      -- src/evidence_matcher.py
   |  deterministic: exact (provision_type, provision_number, subsection,
   |  act_norm) lookup, then fuzzy act-name-token-overlap fallback,
   |  against the usable evidence pool (canonical_statutes.jsonl joined
   |  with evidence_audit.jsonl, VERIFIED_EXACT/VERIFIED_CONTENT only)
   v
claim.evidence_text | NO_EVIDENCE
   |
   v (Mode B/C only)
[4] NLIVerifier.verify()                   -- src/verifier.py
   |  MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
   |  premise=evidence_text, hypothesis=claim_text
   |  ENTAILED / CONTRADICTED / NOT_ENOUGH_INFORMATION
   |  (low-confidence argmax is downgraded to NOT_ENOUGH_INFORMATION,
   |   sub_reason="low_confidence")
   v
claim.verdict
   |
   v (Mode C only, first flagged claim)
[5] SelectiveCorrector.correct()           -- src/corrector.py
   |  reuses the already-loaded generation model; rewrites ONLY the
   |  flagged sentence, asked to copy every other sentence verbatim
   v
corrected_text
   |
   v
[6] Scope-violation gate                   -- src/pipeline.py:_scope_violation
   |  programmatic check (not just a prompt instruction): every unflagged
   |  claim's exact original sentence must still appear verbatim in
   |  corrected_text. Violation -> correction_scope_violation, corrected
   |  text discarded, original shipped.
   v
[7] Re-parse + re-match + re-verify ONLY the corrected sentence
   v
final_field  (original | corrected | correction_failed | correction_scope_violation)
```

Orchestration lives in `src/pipeline.py::run_case()`. All three modes share
stage [1]-[3] (generation + claim extraction + evidence matching), run
once and independent of mode, so comparing A vs B vs C is a paired
comparison against an identical baseline, not three different generations.

## Modes A / B / C

| Mode | Generation | Verification | Correction | `final_field` |
|------|-----------|---------------|------------|----------------|
| A | yes | no | no | always the raw generated text |
| B | yes | yes | no (diagnostic only) | always the raw generated text, even if a claim is CONTRADICTED |
| C | yes | yes | yes | original, corrected, `correction_failed`, or `correction_scope_violation` — see `final_field.source` |

Correction triggers only for the **first** flagged claim in the field
(CONTRADICTED at any confidence, or NOT_ENOUGH_INFORMATION with
`sub_reason == "low_confidence"`), never for NO_EVIDENCE and never for a
genuine high-confidence neutral NLI prediction. This "first flagged claim
only" scoping is a documented v0 simplification, not a bug — multi-claim
correction per field is out of scope for this prototype.

## Models

- **Generation + correction** (same loaded model, reused): `Qwen/Qwen2.5-7B-Instruct`, 4-bit (bitsandbytes nf4, double quant, bfloat16 compute), greedy decoding (`do_sample=False`), `max_new_tokens=200` (generation) / `220` (correction).
- **Verification**: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, fp16, `confidence_threshold=0.70`, label order read from the model's own `config.id2label` rather than hardcoded.

Both require CUDA — neither loader falls back to CPU (this was validated on
an RTX 4050 6GB card; see `research/baseline/BASELINE.md` for the
accelerate/transformers version constraints this prototype's generator
inherits).

## Data sources

- `research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl` (read-only) — a 100-citation, independently-sourced canonical statute evidence table plus its audit. Only `VERIFIED_EXACT` / `VERIFIED_CONTENT` records (59 total) are usable evidence; `SOURCE_ONLY` / `INVALID` / `UNRESOLVED` are excluded by design. See `research/data/evidence/README.md`.
- `research/data/nyayarag/CaseText_Statutes/*.json` — NyayaRAG `CaseText_Statutes` case data (`L-NLProc/NyayaRAG` on Hugging Face, `3.CaseText_Statutes.zip`: `SCI_56k_multi_5k_summarised_w_sections.json`, `SCI_56k_single_5k_summarised_w_sections.json`), copied into this stable project-relative location from an earlier session's scratch extraction (no new download performed for this fix). Only `case_text` and the case's own citation **keys** are read from these files — never NyayaRAG's own free-text `sections` values, which are not treated as evidence anywhere in this pipeline (see docstrings in `src/data_loader.py`).

`config/prototype.yaml`'s `paths:` block is resolved relative to the repo
root by `scripts/run_mvp.py`, so the config works regardless of the
directory it's invoked from.

## Known limitations

- **NLI verdict ≠ legal correctness.** The verifier reports a small public NLI model's statistical confidence that the matched statute text entails/contradicts/is neutral toward the claim sentence — not a lawyer-verified legal-accuracy judgment. No gold evaluation of verifier accuracy has been run yet. This disclaimer is repeated in every output record's `verification.disclaimer` field.
- **59-record evidence pool.** Coverage is the top-100-citation profile from the NyayaRAG corpus, filtered to audit-verified records. Most claims in an arbitrary case will resolve to `NO_EVIDENCE`; case selection (`select_cases_with_evidence_overlap`) filters to cases with ≥1 overlapping citation specifically to avoid trivial all-`NO_EVIDENCE` runs.
- **Pre-2024-07-01 "canonical" text for IPC/CrPC-heavy citations.** IPC and CrPC (41 of the top-100 citations) are nationally superseded by the Bharatiya Nyaya Sanhita / Bharatiya Nagarik Suraksha Sanhita as of 2024-07-01; canonical text here is the pre-repeal version. See `research/data/evidence/README.md`.
- **One claim per sentence, first citation only.** A sentence with multiple citations is represented by its first citation only (documented simplification in `claim_parser.extract_citation`).
- **First flagged claim only drives correction** (Mode C). If a field has more than one flagged claim, only the first one is corrected; the rest keep their original verdicts.
- **Selective-correction scope is enforced programmatically, not just by prompt.** `pipeline._scope_violation()` checks that every unflagged claim's original sentence text still appears verbatim in the corrected paragraph; if the corrector alters an unflagged claim anyway, the run is marked `correction_scope_violation` and the corrected text is discarded (never shipped as `final_field`), while both texts are retained in the output record for inspection.
- **`research/data/nyayarag/` was populated by copying files already extracted to local scratch space in an earlier session**, not by a fresh download performed as part of this fix. If those files are ever missing in a new environment, they must be re-obtained from `L-NLProc/NyayaRAG` (`3.CaseText_Statutes.zip`) before Mode A/B/C can run — `scripts/run_mvp.py --check` does not verify their presence (only the evidence files), so a real run is the first point that would surface a missing-file error.
- **Hard-capped at `MAX_ALLOWED_CASES = 5`** cases per invocation of `scripts/run_mvp.py`, by design — not a performance limit, a "don't run the full dataset yet" guardrail until a deliberate decision to scale up.
- **No real inference has been run against this prototype.** Everything above the mocked pipeline tests (`tests/test_pipeline_mock.py`) is unexercised — the `--check` command confirms imports/config/evidence-loading only; it loads no model.

## First run

Import/config check only — loads no model, downloads nothing:

```
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py --check
```

Unit tests (also no model, no GPU, no network):

```
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -v
```

First real case (Mode A, generation only — loads Qwen2.5-7B-Instruct in
4-bit onto the GPU; not executed as part of building this prototype):

```
research/.venv/Scripts/python.exe research/prototype/scripts/run_mvp.py \
    --mode A --num-cases 1 --output research/prototype/outputs/run_A_n1.jsonl
```
