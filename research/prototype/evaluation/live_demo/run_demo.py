#!/usr/bin/env python
"""
Small, deterministic, end-to-end demo of the NyayaMind pipeline using the
EXISTING production implementation (research/prototype/src/*, unmodified,
unmocked) and the EXISTING production config (research/prototype/config/prototype.yaml,
unmodified -- use_evidence_v1: true, premise_framing: "labeled",
atomic_scope_check: "assertion_spans", narrow_reverification_hypothesis: true).

What is genuinely LIVE in this demo (real code, real model, executed now):
  [2] claim extraction        -- src.claim_parser.extract_claims()
  [3] evidence retrieval      -- src.evidence_matcher.match_evidence() against the
                                  real 136-record production pool
  [4] NLI verification        -- src.verifier.NLIVerifier, real DeBERTa-v3-base-mnli-
                                  fever-anli inference, CPU (small model, no GPU needed
                                  -- see REPRODUCIBILITY.md S2)
  [6] re-verification         -- the SAME live verifier, called again on the corrected
                                  sentence
  [7] safety gate             -- src.pipeline._scope_violation(), the actual
                                  programmatic gate function, called directly

What is REPLAYED from an already-committed real experiment output (clearly labeled
each time), not re-run:
  [1] generation               -- Qwen2.5-7B-Instruct text generation requires a GPU
                                   and several GB of VRAM; re-running it for a demo
                                   is unnecessary GPU work this script deliberately
                                   avoids (per this task's own instruction: "do not
                                   launch unnecessary large experiments"). The text
                                   shown is real, previously-generated Qwen output,
                                   read verbatim from a committed outputs/*.jsonl file.
  [5] selective correction     -- likewise a Qwen2.5-7B generation call. The
                                   corrected text shown is the real, already-shipped
                                   correction from
                                   outputs/labeled_correction_validation_gpu_corrections_detail.jsonl
                                   (document 2003_760/c3 -- the one natural shipped
                                   correction in this project's history).

To run a genuine end-to-end GPU generation+correction yourself (optional, requires
CUDA + Qwen2.5-7B, several minutes): use the actual production entry point,
research/prototype/scripts/run_mvp.py --mode C --num-cases 1 --output <path> -- this
demo intentionally does not duplicate that code path.

Run:
  research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/run_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PROTOTYPE_ROOT = REPO_ROOT / "research/prototype"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(PROTOTYPE_ROOT))

# Windows consoles/redirected-output default to the system codepage (often
# cp1252), which cannot encode the em-dashes and smart quotes this script and
# some source jsonl text contain -- force UTF-8 so redirected logs are always
# readable regardless of host locale.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml  # noqa: E402

from src import claim_parser, pipeline  # noqa: E402
from src.data_loader import load_usable_evidence_from_config  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402
from src.verifier import NLIVerifier  # noqa: E402


def load_config() -> dict:
    with (PROTOTYPE_ROOT / "config/prototype.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_record(rel_path: str, document_id: str) -> dict:
    with (REPO_ROOT / rel_path).open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("document_id") == document_id:
                return rec
    raise KeyError(f"{document_id} not found in {rel_path}")


CORRECTION_DETAIL_FILES = [
    "research/prototype/outputs/natural_candidates_50_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/natural_candidates_batch2_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl",
]


def load_committed_correction_attempt(document_id: str, claim_id: str):
    """Search every committed correction-attempt record across every experiment
    batch this project has run for one matching (document_id, claim_id) --
    a case can be flagged live under the current production config even if the
    committed correction attempt for it was recorded under a different
    historical run/framing; there is no guarantee a specific document/claim
    combination has a committed replay available, so this returns None rather
    than assuming one particular file."""
    for rel in CORRECTION_DETAIL_FILES:
        with (REPO_ROOT / rel).open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("document_id") == document_id and rec.get("triggered_for_claim_id") == claim_id:
                    return rel, rec
    return None, None


DEMO_CASES = [
    {
        "document_id": "2011_625",
        "source": "research/prototype/outputs/final_gpu_validation_B.jsonl",
        "headline": "NO_EVIDENCE — claim outside the corpus, correctly never verified or corrected",
    },
    {
        "document_id": "1997_1306",
        "source": "research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl",
        "headline": "CONTRADICTED — a citation's claimed content does not match its evidence",
    },
    {
        "document_id": "2003_760",
        "source": "research/prototype/outputs/final_gpu_validation_B.jsonl",
        "headline": "Flagged claim -> shipped correction (the project's one natural shipped correction)",
    },
]


def banner(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def stage(n: int, name: str, live: bool) -> None:
    tag = "LIVE" if live else "REPLAYED (from committed output, not re-run)"
    print(f"\n  --- Stage [{n}] {name} :: {tag} ---")


def main() -> int:
    config = load_config()
    print("Production config in use (unmodified, research/prototype/config/prototype.yaml):")
    print(f"  premise_framing              = {config['verification']['premise_framing']}")
    print(f"  use_evidence_v1               = {config['use_evidence_v1']}")
    print(f"  atomic_scope_check            = {config['correction']['atomic_scope_check']}")
    print(f"  narrow_reverification_hypothesis = {config['correction']['narrow_reverification_hypothesis']}")
    print(f"  confidence_threshold          = {config['verification']['confidence_threshold']}")

    print("\nLoading production evidence pool (real data, no model)...")
    exact_index, all_usable = load_usable_evidence_from_config(config, REPO_ROOT)
    print(f"  Loaded {len(all_usable)} usable evidence records (expect 136).")

    print("\nLoading the real DeBERTa-v3-base-mnli-fever-anli verifier (CPU, small model,"
          " no GPU required)... this takes a few seconds.")
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    verifier.load()
    premise_framing = pipeline.resolve_premise_framing(config)
    print("  Verifier loaded.")

    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    for case in DEMO_CASES:
        banner(f"CASE {case['document_id']} — {case['headline']}")
        rec = load_record(case["source"], case["document_id"])
        generated_text = rec["generated_field"]["text"]

        stage(1, "Generation (Qwen2.5-7B-Instruct, 4-bit, greedy)", live=False)
        print(f"  Source: {case['source']}")
        print(f"  Generated statutory-grounding text:\n    {generated_text[:400]}"
              + ("..." if len(generated_text) > 400 else ""))

        stage(2, "Claim extraction (deterministic regex, no LLM)", live=True)
        claims = claim_parser.extract_claims(generated_text)
        print(f"  Extracted {len(claims)} citation-bearing claim(s).")
        for c in claims[:3]:
            print(f"    [{c.claim_id}] {c.claim_text[:100]}")
        if len(claims) > 3:
            print(f"    ... ({len(claims) - 3} more claim(s) not shown)")

        stage(3, "Evidence retrieval (exact + fuzzy match, 136-record production pool)", live=True)
        claim_records = []
        for claim in claims:
            match = match_evidence(claim.citation_extracted, exact_index, all_usable, fuzzy_threshold)
            claim_records.append({
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "assertion_text": claim.assertion_text,
                "assertion_spans": list(claim.assertion_spans),
                "citation_extracted": claim.citation_extracted.as_dict() if claim.citation_extracted else None,
                "evidence_id": match.evidence.dataset_citation_key if match.matched else None,
                "evidence_text": match.evidence.canonical_text if match.matched else None,
                "_evidence_provision": {
                    "provision_type": match.evidence.provision_type,
                    "provision_number": match.evidence.provision_number,
                    "act": match.evidence.act,
                } if match.matched else None,
                "evidence_match_method": match.match_method,
                "verdict": None, "confidence": None, "sub_reason": None, "verifier_model": None,
            })
            if not match.matched:
                claim_records[-1]["verdict"] = "NO_EVIDENCE"
        for cr in claim_records:
            print(f"    [{cr['claim_id']}] evidence_id={cr['evidence_id']!r} method={cr['evidence_match_method']}")

        stage(4, f"NLI verification (premise_framing={premise_framing!r}, real DeBERTa call per matched claim)", live=True)
        baseline = {"document_id": rec["document_id"], "claims": claim_records}
        pipeline.apply_verification(baseline, verifier, premise_framing=premise_framing)
        flagged_claim_id = None
        for cr in claim_records:
            print(f"    [{cr['claim_id']}] verdict={cr['verdict']} confidence={cr['confidence']}")
            if cr["verdict"] not in ("NO_EVIDENCE", None) and pipeline._should_trigger_correction(cr):
                flagged_claim_id = flagged_claim_id or cr["claim_id"]

        if not flagged_claim_id:
            print("\n  No claim triggers correction (no CONTRADICTED, no low-confidence NEI) —"
                  " pipeline correctly stops here. final_field == generated_field.")
            continue

        print(f"\n  Claim [{flagged_claim_id}] triggers correction.")
        stage(5, "Selective correction (Qwen2.5-7B-Instruct rewrite of the flagged sentence)", live=False)
        source_file, committed = load_committed_correction_attempt(case["document_id"], flagged_claim_id)
        if committed is None:
            print(f"  No committed correction-attempt record exists for this exact "
                  f"(document_id, claim_id) under any historical run. Skipping stages 6-7 "
                  f"for this case rather than fabricating a correction attempt.")
            continue
        corrected_text = committed["regenerated_text"]
        print(f"  Source: {source_file}  (historical status: {committed['status']!r}, framing: {committed.get('framing', 'n/a')!r})")
        print(f"  Corrected text:\n    {corrected_text[:400]}" + ("..." if len(corrected_text) > 400 else ""))

        stage(6, "Re-verification of the corrected sentence (real DeBERTa call)", live=True)
        target = next(cr for cr in claim_records if cr["claim_id"] == flagged_claim_id)
        # Same ordinal-position citation-identity matching src.pipeline.apply_selective_correction
        # itself uses (a document can have multiple claims citing the same provision;
        # identity alone is ambiguous, so the Nth same-citation claim in extraction
        # order is matched to the Nth same-citation claim re-extracted from the
        # corrected text -- see src/pipeline.py's own docstring on this).
        target_identity = pipeline._citation_identity(target["citation_extracted"])
        target_ordinal = None
        if target_identity is not None:
            same_identity_baseline = [
                cr for cr in claim_records
                if pipeline._citation_identity(cr["citation_extracted"]) == target_identity
            ]
            target_ordinal = next(i for i, cr in enumerate(same_identity_baseline) if cr is target)
        recorrected_claims = claim_parser.extract_claims(corrected_text)
        target_recorrected = None
        if target_identity is not None:
            same_identity_reextracted = [
                c for c in recorrected_claims if pipeline._citation_identity(c.citation_extracted) == target_identity
            ]
            if target_ordinal < len(same_identity_reextracted):
                target_recorrected = same_identity_reextracted[target_ordinal]
        reverify_hypothesis = (target_recorrected.assertion_text if target_recorrected else None) \
            or target["claim_text"]
        reverify_result = verifier.verify(
            premise=pipeline._premise_for_claim(target, premise_framing),
            hypothesis=reverify_hypothesis,
        )
        print(f"  Reverified hypothesis: {reverify_hypothesis[:150]}")
        print(f"  Reverification verdict: {reverify_result.label} (confidence {reverify_result.confidence:.4f})")
        print(f"  (Historical committed reverification for comparison: {committed.get('reverification')})")

        stage(7, "Safety gate (programmatic scope-violation check, src.pipeline._scope_violation)", live=True)
        violation = pipeline._scope_violation(
            claim_records, flagged_claim_id, corrected_text,
            use_assertion_spans=(config["correction"]["atomic_scope_check"] == "assertion_spans"),
            use_assertion_text=(config["correction"]["atomic_scope_check"] is True),
        )
        print(f"  Scope violation detected: {violation}")
        ships = (not violation) and reverify_result.label == "ENTAILED"
        print(f"  FINAL GATE DECISION: {'SHIP corrected text' if ships else 'REJECT — keep original text'}"
              f" (ship iff not violation AND reverification.verdict == ENTAILED)")
        print(f"  (Historical committed outcome for comparison: {committed['status']!r})")

    banner("Demo complete. No file under research/prototype/outputs/ or research/data/ was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
