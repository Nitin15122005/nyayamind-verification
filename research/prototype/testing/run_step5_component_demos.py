#!/usr/bin/env python3
"""STEP 5 — concrete input/output demonstrations for each pipeline component.

Every example here either (a) calls a real, unmodified production function directly
with a fixture copied VERBATIM from an existing test file (cited by name/line), or
(b) re-runs `src/pipeline.py::run_case` with the EXACT same fixtures
(`tests/test_correction_path_real_integration.py`'s own `FakeGenerator`/
`ScriptedCorrector`/sentences) that test already uses -- so the faculty-review
question "show me an actual input and actual output" has a concrete, traceable answer
for every component, without inventing any new legal content or rewriting any test.

The DeBERTa verifier used below is REAL (device="cpu" -- no NVIDIA GPU on this
machine, per STEP 2). No Qwen generation or correction is ever invoked -- every
generator/corrector here is a FakeGenerator/ScriptedCorrector, exactly as the cited
test already uses, never the real 7B model.

Writes only under research/prototype/testing/actual_outputs/step5_components/.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = TESTING_DIR.parent
RESEARCH_DIR = PROTOTYPE_DIR.parent
REPO_ROOT = RESEARCH_DIR.parent

sys.path.insert(0, str(PROTOTYPE_DIR))

import yaml  # noqa: E402
from src.claim_parser import ExtractedCitation, extract_citations, extract_claims, normalize_act  # noqa: E402
from src.data_loader import Case, EvidenceRecord, load_usable_evidence  # noqa: E402
from src.evidence_matcher import match_evidence  # noqa: E402
from src.generator import GenerationMetadata  # noqa: E402
from src.corrector import CorrectionMetadata  # noqa: E402
from src.pipeline import run_case  # noqa: E402
from src.verifier import NLIVerifier, CONTRADICTED, ENTAILED, NOT_ENOUGH_INFORMATION  # noqa: E402

OUT = TESTING_DIR / "actual_outputs" / "step5_components"
CONFIG = yaml.safe_load((PROTOTYPE_DIR / "config" / "prototype.yaml").read_text(encoding="utf-8"))


def write_json(subdir: str, name: str, data) -> None:
    p = OUT / subdir / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {p}")


# ---------------------------------------------------------------------------
# 01 -- Claim parser: real, verbatim sentence from tests/test_claim_parser_bugfixes.py
# ---------------------------------------------------------------------------

def demo_claim_parser():
    sentence = (
        "The case is grounded in the United Commercial Bank (Conduct and "
        "Discipline and Appeal) Regulation, 1976, specifically Regulation "
        "15(2), and the Manual on Disciplinary Action and Related Matters of "
        "UCO Bank, particularly Clause 22 thereof, as well as Sections 120-B, "
        "471, and 477 of the Indian Penal Code and Section 5(2) read with "
        "Section 1(d) of the Prevention of Corruption Act, 1947, which pertain "
        "to the criminal charges and the prevention of corruption respectively."
    )
    citations = extract_citations(sentence)
    claims = extract_claims(sentence)
    result = {
        "source_of_input": "tests/test_claim_parser_bugfixes.py, _BUG1_SENTENCE (verbatim from real Qwen output, document_id 2007_1517)",
        "expected_behavior_asserted_by": "tests/test_claim_parser_bugfixes.py::test_bug1_ipc_sections_do_not_merge_with_poca_act_name, test_bug1_poca_citation_recovered_not_lost",
        "input_sentence": sentence,
        "actual_extracted_citations": [c.as_dict() for c in citations],
        "actual_extracted_claims_count": len(claims),
        "software_invariant_checked": "IPC 120-B/471/477 citations must not have their act polluted by the trailing POCA clause; the POCA Section 1(d) citation must be recovered as its own, separate claim, not swallowed",
    }
    ipc = [c for c in citations if c.provision_number in ("120-B", "471", "477")]
    poca = [c for c in citations if c.act_norm == "prevention of corruption act 1947"]
    result["pass"] = (
        len(ipc) == 3
        and all(c.act_norm in ("indian penal code", "indian penal code 1860") for c in ipc)
        and len(poca) == 1
    )
    write_json("01_claim_parser", "demo_examples.json", result)
    return result


# ---------------------------------------------------------------------------
# 02 -- Evidence matcher: real production pool (exact match) + a same-number,
#        three-different-acts case verbatim from test_adversarial_citations.py
# ---------------------------------------------------------------------------

def demo_evidence_matcher():
    canonical_path = REPO_ROOT / "research/data/evidence/canonical_statutes.jsonl"
    audit_path = REPO_ROOT / "research/data/evidence/evidence_audit.jsonl"
    exact_index, all_usable = load_usable_evidence(canonical_path, audit_path, {"VERIFIED_EXACT", "VERIFIED_CONTENT"})

    # (a) real production pool, exact match -- Section 302 IPC (same record used by
    # tests/test_correction_path_real_integration.py)
    citation_302 = ExtractedCitation(
        provision_type="Section", provision_number="302", subsection=None,
        act_raw="the Indian Penal Code, 1860", act_norm=normalize_act("the Indian Penal Code, 1860"),
    )
    real_match = match_evidence(citation_302, exact_index, all_usable, CONFIG["evidence_matching"]["fuzzy_token_overlap_threshold"])

    # (b) same-number-different-Act, verbatim from tests/test_adversarial_citations.py::test_same_section_number_three_way_split_across_acts
    def _make_evidence(provision_type, provision_number, act, text):
        return EvidenceRecord(
            dataset_citation_key=f"{provision_type} {provision_number} in {act}",
            act=act, provision_type=provision_type, provision_number=provision_number,
            subsection=None, canonical_text=text, source_url="https://example.invalid/doc/1",
            audit_verdict="VERIFIED_EXACT", act_norm=normalize_act(act),
        )
    ipc34 = _make_evidence("Section", "34", "The Indian Penal Code, 1860", "Common intention text.")
    arb1940_34 = _make_evidence("Section", "34", "The Arbitration Act, 1940", "1940-Act text (repealed 1996).")
    arb1996_34 = _make_evidence("Section", "34", "The Arbitration And Conciliation Act, 1996", "Setting aside an arbitral award text.")
    adv_index = {(e.provision_type, e.provision_number, e.subsection, e.act_norm): e for e in (ipc34, arb1940_34, arb1996_34)}
    adv_pool = [ipc34, arb1940_34, arb1996_34]

    adv_results = []
    all_correct = True
    for act_raw, expected_text in (
        ("the Indian Penal Code, 1860", "Common intention text."),
        ("the Arbitration Act, 1940", "1940-Act text (repealed 1996)."),
        ("the Arbitration and Conciliation Act, 1996", "Setting aside an arbitral award text."),
    ):
        c = ExtractedCitation(provision_type="Section", provision_number="34", subsection=None,
                               act_raw=act_raw, act_norm=normalize_act(act_raw))
        r = match_evidence(c, adv_index, adv_pool, 0.8)
        correct = r.matched and r.evidence.canonical_text == expected_text
        all_correct = all_correct and correct
        adv_results.append({"act_raw": act_raw, "matched": r.matched,
                             "match_method": r.match_method,
                             "matched_text": r.evidence.canonical_text if r.evidence else None,
                             "expected_text": expected_text, "correct": correct})

    result = {
        "case_a_real_production_pool": {
            "source_of_input": "real production pool (research/data/evidence/), same citation tests/test_correction_path_real_integration.py uses",
            "input_citation": citation_302.as_dict(),
            "actual_matched": real_match.matched,
            "actual_match_method": real_match.match_method,
            "actual_evidence_id": real_match.evidence.dataset_citation_key if real_match.evidence else None,
            "actual_evidence_text": real_match.evidence.canonical_text if real_match.evidence else None,
            "expected_behavior": "resolves to 'Section 302 in The Indian Penal Code, 1860' via exact-key match",
            "pass": real_match.matched and real_match.evidence.dataset_citation_key == "Section 302 in The Indian Penal Code, 1860",
        },
        "case_b_same_number_three_acts": {
            "source_of_input": "tests/test_adversarial_citations.py::test_same_section_number_three_way_split_across_acts (verbatim fixture)",
            "expected_behavior": "Section 34 under 3 different Acts must each resolve independently to its own Act's text, never cross-matching",
            "results": adv_results,
            "pass": all_correct,
        },
    }
    write_json("02_evidence_matcher", "demo_examples.json", result)
    return result


# ---------------------------------------------------------------------------
# 05 -- Citation / adversarial safety: wrong-Act CrPC-vs-CPC + aliases,
#        verbatim from test_adversarial_citations.py
# ---------------------------------------------------------------------------

def demo_citation_adversarial():
    def _make_evidence(provision_type, provision_number, act, text):
        return EvidenceRecord(
            dataset_citation_key=f"{provision_type} {provision_number} in {act}",
            act=act, provision_type=provision_type, provision_number=provision_number,
            subsection=None, canonical_text=text, source_url="https://example.invalid/doc/1",
            audit_verdict="VERIFIED_EXACT", act_norm=normalize_act(act),
        )

    # wrong-Act: CrPC-vs-CPC Section 100, verbatim from
    # test_wrong_act_crpc_vs_cpc_section_100_never_cross_matches
    cpc_100 = _make_evidence("Section", "100", "The Code of Civil Procedure, 1908", "Second appeal text.")
    wrong_act_index = {(cpc_100.provision_type, cpc_100.provision_number, cpc_100.subsection, cpc_100.act_norm): cpc_100}
    claim_act_norm = normalize_act("the Code of Criminal Procedure (CrPC)")
    citation = ExtractedCitation(provision_type="Section", provision_number="100", subsection=None,
                                  act_raw="the Code of Criminal Procedure (CrPC)", act_norm=claim_act_norm)
    wrong_act_result = match_evidence(citation, wrong_act_index, [cpc_100], 0.8)

    # aliases: CrPC/CPC normalize distinctly (pure normalize_act check, no matcher call needed)
    alias_crpc = normalize_act("CrPC")
    alias_cpc = normalize_act("CPC")

    cases = [
        {
            "category": "wrong_act",
            "source_test": "test_adversarial_citations.py::test_wrong_act_crpc_vs_cpc_section_100_never_cross_matches",
            "input_citation": citation.as_dict(),
            "available_evidence": [cpc_100.dataset_citation_key],
            "actual_matched": wrong_act_result.matched,
            "actual_match_method": wrong_act_result.match_method,
            "expected_software_behavior": "must resolve to NO_EVIDENCE, never cross-match to the CPC record despite both being 'Section 100' and sharing 'code'/'procedure' tokens",
            "pass": wrong_act_result.matched is False and wrong_act_result.match_method == "no_evidence",
            "note": "This is a retrieval/matching behavior finding, not a legal-reasoning failure -- the corpus genuinely has no CrPC Section 100 record; the matcher correctly refuses to guess.",
        },
        {
            "category": "aliases",
            "source_test": "test_adversarial_citations.py::test_aliases_crpc_and_cpc_are_distinct_and_each_resolves_correctly",
            "input": {"CrPC": "CrPC", "CPC": "CPC"},
            "actual_normalize_act_crpc": alias_crpc,
            "actual_normalize_act_cpc": alias_cpc,
            "expected_software_behavior": "CrPC -> 'code of criminal procedure 1973', CPC -> 'code of civil procedure 1908', and the two must be distinct",
            "pass": alias_crpc == "code of criminal procedure 1973" and alias_cpc == "code of civil procedure 1908" and alias_crpc != alias_cpc,
        },
    ]
    result = {"cases": cases, "all_pass": all(c["pass"] for c in cases)}
    write_json("05_citation_adversarial", "demo_examples.json", result)
    return result


# ---------------------------------------------------------------------------
# 03/04/06/07 -- real DeBERTa verifier + real run_case(), exact fixtures from
# tests/test_correction_path_real_integration.py (FakeGenerator/ScriptedCorrector,
# never the real 7B Qwen model -- GPU generation was not executed on this machine)
# ---------------------------------------------------------------------------

_REAL_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with the unlawful assembly, which may be "
    "relevant if the prosecution can show that the accused acted as part of an "
    "unlawful assembly."
)
_CORRUPTED_FLAGGED_SENTENCE = (
    "The offense of murder under Section 302 of the Indian Penal Code, 1860 is "
    "punishable only by a fine and never by death or imprisonment."
)
_CORRECTED_FLAGGED_SENTENCE = (
    "Whoever commits murder under Section 302 of the Indian Penal Code, 1860 "
    "shall be punished with death, or imprisonment for life, and shall also be "
    "liable to fine."
)
_ALTERED_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with theft, which may be relevant if the "
    "prosecution can show that the accused acted alone."
)


class FakeGenerator:
    """Verbatim pattern from tests/test_correction_path_real_integration.py -- supplies
    a pre-existing real generated field directly, never invokes the real 7B model."""
    def __init__(self, text, model_id):
        self._text, self._model_id = text, model_id

    def generate(self, case_text):
        meta = GenerationMetadata(model_id=self._model_id, quantization={"load_in_4bit": True},
                                   max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42)
        return self._text, meta


class ScriptedCorrector:
    """Verbatim pattern from tests/test_correction_path_real_integration.py -- returns
    pre-authored 'corrected' text, never invokes the real 7B model."""
    def __init__(self, corrected_text, model_id):
        self._corrected_text, self._model_id = corrected_text, model_id
        self.calls = []

    def correct(self, case_text, original_field_text, flagged_claim_text, evidence_text):
        self.calls.append((flagged_claim_text, evidence_text))
        meta = CorrectionMetadata(model_id=self._model_id, max_new_tokens=220, do_sample=False, seed=42)
        return self._corrected_text, meta


def demo_verifier_verdict_correction_and_assembly(real_verifier, exact_index, all_usable):
    case = Case(document_id="1994_495", case_text="facts...", raw_citation_keys=[])

    # 03/04: mode B, corrupted claim -> real matched evidence -> real CONTRADICTED verdict
    corrupted_text = _CORRUPTED_FLAGGED_SENTENCE + " " + _REAL_UNFLAGGED_SENTENCE
    generator = FakeGenerator(corrupted_text, CONFIG["generation"]["model_id"])
    record_b = run_case(case, "B", generator, real_verifier, corrector=None,
                         exact_index=exact_index, all_usable=all_usable, config=CONFIG)
    flagged = next(c for c in record_b["claims"] if c["citation_extracted"]["provision_number"] == "302")

    verifier_verdict_demo = {
        "source_of_input": "tests/test_correction_path_real_integration.py::test_corrupted_claim_reaches_contradicted_against_real_evidence (exact same fixtures)",
        "input_generated_field_text": corrupted_text,
        "real_component_used": "src.verifier.NLIVerifier (real DeBERTa-v3-base-mnli-fever-anli, device=cpu -- no NVIDIA GPU on this machine)",
        "actual_evidence_id": flagged["evidence_id"],
        "actual_evidence_text": flagged["evidence_text"],
        "actual_verdict": flagged["verdict"],
        "actual_confidence": flagged["confidence"],
        "expected_behavior": "must resolve evidence to 'Section 302 in The Indian Penal Code, 1860' and verdict CONTRADICTED, confidence above threshold",
        "pass": (flagged["evidence_id"] == "Section 302 in The Indian Penal Code, 1860"
                 and flagged["verdict"] == CONTRADICTED
                 and flagged["confidence"] > CONFIG["verification"]["confidence_threshold"]),
        "full_verdict_application_record_claims": record_b["claims"],
    }
    write_json("03_verifier", "demo_examples.json", {"case": verifier_verdict_demo})
    write_json("04_verdict_application", "demo_examples.json", {"case": verifier_verdict_demo})

    # 06/07: mode C, full correction path -- SHIP outcome
    corrected_text = _CORRECTED_FLAGGED_SENTENCE + " " + _REAL_UNFLAGGED_SENTENCE
    corrector_good = ScriptedCorrector(corrected_text, CONFIG["generation"]["model_id"])
    record_c_ship = run_case(case, "C", generator, real_verifier, corrector_good,
                              exact_index=exact_index, all_usable=all_usable, config=CONFIG)

    ship_demo = {
        "source_of_input": "tests/test_correction_path_real_integration.py::test_full_correction_path_triggers_and_reverifies_with_real_verifier (exact same fixtures)",
        "generator": "FakeGenerator (supplies pre-existing text; real 7B Qwen model NOT invoked)",
        "corrector": "ScriptedCorrector (supplies pre-authored corrected text; real 7B Qwen model NOT invoked)",
        "gpu_generation_executed": False,
        "input_corrupted_text": corrupted_text,
        "candidate_correction_text": corrected_text,
        "actual_correction_block": record_c_ship["correction"],
        "actual_final_field": record_c_ship["final_field"],
        "expected_behavior": "correction triggered for claim 302 only; real re-verification via real DeBERTa verifier; SHIP (status=corrected) iff re-verification verdict is ENTAILED",
        "pass": (record_c_ship["correction"]["status"] == "corrected"
                 and record_c_ship["correction"]["reverification"]["verdict"] == ENTAILED
                 and record_c_ship["final_field"]["source"] == "corrected"
                 and record_c_ship["final_field"]["text"] == corrected_text),
    }

    # 06/07: mode C, scope-violation path -- REJECT outcome
    bad_corrected_text = _CORRECTED_FLAGGED_SENTENCE + " " + _ALTERED_UNFLAGGED_SENTENCE
    corrector_bad = ScriptedCorrector(bad_corrected_text, CONFIG["generation"]["model_id"])
    record_c_reject = run_case(case, "C", generator, real_verifier, corrector_bad,
                                exact_index=exact_index, all_usable=all_usable, config=CONFIG)

    reject_demo = {
        "source_of_input": "tests/test_correction_path_real_integration.py::test_scope_violation_protection_when_corrector_alters_unflagged_claim (exact same fixtures)",
        "generator": "FakeGenerator (real 7B Qwen model NOT invoked)",
        "corrector": "ScriptedCorrector -- deliberately alters the UNFLAGGED sentence too (real 7B Qwen model NOT invoked)",
        "gpu_generation_executed": False,
        "input_corrupted_text": corrupted_text,
        "candidate_correction_text_bad": bad_corrected_text,
        "actual_correction_block": record_c_reject["correction"],
        "actual_final_field": record_c_reject["final_field"],
        "expected_behavior": "_scope_violation() must catch the altered unflagged sentence BEFORE re-verification and refuse to ship it -- status=correction_scope_violation, reverification=None, original corrupted text shipped instead",
        "pass": (record_c_reject["correction"]["status"] == "correction_scope_violation"
                 and record_c_reject["correction"]["reverification"] is None
                 and record_c_reject["final_field"]["source"] == "correction_scope_violation"
                 and record_c_reject["final_field"]["text"] == corrupted_text),
    }

    correction_safety_out = {"ship_case": ship_demo, "reject_case": reject_demo,
                              "citation_identity_note": "Both cases route the corrected claim back to claim_id via ordinal position within its citation-identity group (src/pipeline.py::_citation_identity) -- see record['claims'] for the claim_id continuity."}
    write_json("06_correction_safety", "demo_examples.json", correction_safety_out)

    final_assembly_out = {
        "source_of_input": "tests/test_correction_path_real_integration.py (exact same FakeGenerator/ScriptedCorrector fixtures, real run_case() call)",
        "source_test": "test_full_correction_path_triggers_and_reverifies_with_real_verifier, test_scope_violation_protection_when_corrector_alters_unflagged_claim",
        "expected_behavior": "src/pipeline.py::run_case's final assembly must correctly select final_field.source per status, include a reproducibility block, and strip internal bookkeeping keys, for both a shipped correction and a scope-violation rejection",
        "gpu_generation_executed": False,
        "ship_case_full_record": record_c_ship,
        "reject_case_full_record": record_c_reject,
        "note": "Full final output records (src/pipeline.py::run_case's complete return value) for both a shipped correction and a scope-violation rejection -- demonstrates final_field source selection, reproducibility block, and stripped internal keys end to end.",
        "gpu_dependent_portions_not_executed": "Generation (stage 1) and real correction text generation (stage 6) both require the real 7B Qwen model, which requires an NVIDIA GPU not present on this machine (see STEP 2). Both are supplied here by FakeGenerator/ScriptedCorrector instead, exactly as tests/test_correction_path_real_integration.py already does. Everything else (claim parsing, evidence retrieval, verification, verdict, scope check, sibling-regression check, re-verification, shipping decision, final assembly) is 100% real, unmodified production code.",
    }
    write_json("07_final_assembly", "demo_examples.json", final_assembly_out)

    return {"ship": ship_demo["pass"], "reject": reject_demo["pass"]}


def main():
    for d in OUT.iterdir():
        pass  # directories already created by the shell step before this runs

    print("=== 01 claim parser ===")
    r1 = demo_claim_parser()
    print(f"  pass={r1['pass']}")

    print("=== 02 evidence matcher ===")
    r2 = demo_evidence_matcher()
    print(f"  case_a pass={r2['case_a_real_production_pool']['pass']}  case_b pass={r2['case_b_same_number_three_acts']['pass']}")

    print("=== 05 citation adversarial ===")
    r5 = demo_citation_adversarial()
    print(f"  all_pass={r5['all_pass']}")

    print("=== loading real evidence pool + real DeBERTa verifier (CPU) ===")
    canonical_path = REPO_ROOT / "research/data/evidence/canonical_statutes.jsonl"
    audit_path = REPO_ROOT / "research/data/evidence/evidence_audit.jsonl"
    exact_index, all_usable = load_usable_evidence(canonical_path, audit_path, {"VERIFIED_EXACT", "VERIFIED_CONTENT"})
    real_verifier = NLIVerifier(
        model_id=CONFIG["verification"]["model_id"],
        confidence_threshold=CONFIG["verification"]["confidence_threshold"],
        max_sequence_length=CONFIG["verification"]["max_sequence_length"],
        device="cpu",
    )
    real_verifier.load()
    print("  loaded.")

    print("=== 03/04/06/07 verifier + verdict + correction-safety + final-assembly ===")
    r_combo = demo_verifier_verdict_correction_and_assembly(real_verifier, exact_index, all_usable)
    print(f"  ship_case pass={r_combo['ship']}  reject_case pass={r_combo['reject']}")

    print("\nAll STEP 5 component demos complete.")


if __name__ == "__main__":
    main()
