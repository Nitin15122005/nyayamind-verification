# Input → Component Mapping

Every mapping below cites the exact function/class verified against `src/` in STEP 0's
pipeline trace — nothing here is an invented interface. "Expected-output comparison
legitimate?" follows strictly from `INPUT_MANIFEST.md`'s classification: only GOLD inputs
support it.

```
INPUT (case_text, from NyayaRAG or an already-generated field)
  |
  v
[1] GENERATION -- src/generator.py::StatuteGroundingGenerator.generate(case_text)
  |  Model: Qwen2.5-7B-Instruct, 4-bit. GPU required, no CPU fallback.
  |  BLOCKED on this machine (no NVIDIA GPU, confirmed STEP 2).
  v
generated_field.text
  |
  v
[2] CLAIM PARSER -- src/claim_parser.py::extract_claims(generated_text)
  |  Deterministic, no model.
  v
CLAIMS (list[Claim]: claim_text, citation_extracted, assertion_text, assertion_spans)
  |
  v
[3] EVIDENCE RETRIEVAL -- src/evidence_matcher.py::match_evidence(citation, exact_index, pool, threshold)
  |  Deterministic, no model. Pool from src/data_loader.py::load_usable_evidence_from_config
  |  (IN-01 + IN-02 -> IN-03, 136 records).
  v
MATCHED EVIDENCE (MatchResult: matched, evidence, match_method) | NO_EVIDENCE
  |
  v
[4] NLI VERIFIER -- src/verifier.py::NLIVerifier.verify(premise, hypothesis)
  |  Model: DeBERTa-v3-base-mnli-fever-anli. GPU by default, CPU opt-in exists (confirmed
  |  runnable on this machine, STEP 2).
  |  premise built by src/verifier.py::format_premise() (bare/labeled), threaded via
  |  src/pipeline.py::_premise_for_claim().
  v
VERDICT (VerificationResult: label, confidence, sub_reason, raw_scores)
  |
  v
[5] VERDICT APPLICATION -- src/pipeline.py::apply_verification (mutates claims[] in place)
  |
  v (Mode C only, first flagged claim: CONTRADICTED any confidence, or NEI+low_confidence)
  |
  v
[6] CORRECTOR -- src/corrector.py::SelectiveCorrector.correct()
  |  Reuses [1]'s loaded Qwen model. GPU required (inherits [1]).
  |  BLOCKED on this machine (no NVIDIA GPU).
  v
CANDIDATE CORRECTION (corrected_text, CorrectionMetadata)
  |
  v
[7] SCOPE / SAFETY CHECK -- src/pipeline.py::_scope_violation(), _reverify_sibling_regressions(), _citation_identity()
  |  Deterministic checks; sibling-regression re-verification re-invokes [4].
  v
SCOPE OK -> proceed | SCOPE VIOLATION -> correction_scope_violation, original text shipped
  |
  v
[8] RE-VERIFICATION -- src/pipeline.py::apply_selective_correction (re-verify step)
  |  Re-invokes [4] (DeBERTa) with the (optionally narrowed) hypothesis.
  v
SHIP / REJECT -- status = "corrected" iff result.label == ENTAILED; else "correction_failed"
  |
  v
[9] FINAL ASSEMBLY -- src/pipeline.py::run_case (final_field, reproducibility block)
  |
  v
FINAL OUTPUT
```

## Per-stage input/output/legitimacy table

| Stage | Input artifact | Exact loader/function | Component | Output artifact/object | Expected-output comparison legitimate? |
|---|---|---|---|---|---|
| 1. Generation | CASE-01 (case_text) | `src/generator.py::StatuteGroundingGenerator.generate` | Qwen2.5-7B-Instruct | `generated_field.text` | No — no independent gold exists for what a case's statutory grounding "should" say; **also currently unrunnable on this machine (no GPU)** |
| 2. Claim parsing | `generated_field.text` (fresh) OR any already-committed generated text (metric-only reuse) | `src/claim_parser.py::extract_claims` | deterministic, no model | `list[Claim]` | Category B only (ADV-01..04: exact parsing behavior for constructed/adversarial inputs) — not a statistical claim |
| 3. Evidence retrieval | `Claim.citation_extracted` + IN-03 (136-record pool) | `src/evidence_matcher.py::match_evidence` | deterministic, no model | `MatchResult` / `NO_EVIDENCE` | Category B only (ADV-01: fail-safe NO_EVIDENCE-on-ambiguity behavior) — coverage rate itself is METRIC-ONLY (MET-01) |
| 4. NLI verification | GOLD-01 (`evidence_text`, `hypothesis`) for gold evaluation; OR `MatchResult.evidence` + `Claim.claim_text` for real/metric use | `src/verifier.py::NLIVerifier.verify` (+ `format_premise`) | DeBERTa-v3-base-mnli-fever-anli | `VerificationResult` | **Yes, against GOLD-01 (n=420) — the only legitimate accuracy comparison in this project.** Also legitimate against GOLD-02 (n=59) for contradiction-recall specifically |
| 5. Verdict application | `VerificationResult` | `src/pipeline.py::apply_verification` | no model | mutated `claims[]` | No independent label; this stage applies stage 4's result verbatim |
| 6. Correction | flagged `Claim` + `MatchResult.evidence` | `src/corrector.py::SelectiveCorrector.correct` | reuses stage 1's Qwen model | `(corrected_text, CorrectionMetadata)` | No — no independent gold for "the correct fix"; **also currently unrunnable on this machine (no GPU)**. GOLD-02's by-construction CONTRADICTED labels make correction-*triggering* (not correction *content*) checkable |
| 7. Scope/safety | `corrected_text` + sibling `Claim`s | `src/pipeline.py::_scope_violation`, `_reverify_sibling_regressions`, `_citation_identity` | deterministic + re-invokes stage 4 | scope-ok/violation, sibling-regression flag | Category B only — exact behavioral guarantee ("unflagged claim's required text must survive verbatim"), not a statistical claim |
| 8. Re-verification | replacement `Claim.assertion_text`/`claim_text` + re-matched evidence | `apply_selective_correction` re-verify step | DeBERTa (stage 4 reused) | `status = "corrected" \| "correction_failed"` | No independent gold for real corrections; the unconditional ENTAILED-only gate itself is a Category B (code-behavior) guarantee, verified in `component_tests/07_reverification/` |
| 9. Final assembly | all of the above | `src/pipeline.py::run_case` | no model | final JSONL record | No — assembly-correctness is Category B (`component_tests/08_final_assembly/`), not a statistical claim |

## What is new/clarified in this document versus `../MANIFEST.md`

`MANIFEST.md` (STEP 1) tracks every testing artifact broadly, including ablations and
config files. This document is scoped specifically to the **input→component→output**
chain per pipeline stage, and adds the "exact loader/function" column that STEP 1's
manifest did not carry. Both should be read together; neither supersedes the other.
