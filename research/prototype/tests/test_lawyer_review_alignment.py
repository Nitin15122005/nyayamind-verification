from __future__ import annotations

import unittest
from scripts.audit_lawyer_review_alignment import audit, norm_reference, norm_text, provision_keys


class TestLawyerReviewAlignmentAudit(unittest.TestCase):
    def test_normalizers(self):
        self.assertEqual(norm_text("  SECTION  302  "), "section 302")
        self.assertEqual(norm_reference("Section 302 of IPC"), "section302ofipc")

    def test_provision_parser_handles_lists(self):
        self.assertEqual(
            provision_keys("Sections 147, 148 and 149 of the IPC"),
            {("section", "147"), ("section", "148"), ("section", "149")},
        )

    def test_statement_and_reference_alignment(self):
        annotations = [{
            "annotation_id": "LR-0001", "case_reference": "case-A",
            "legal_statement": "Section 302 prescribes punishment for murder.",
            "legal_reference": "Section 302 IPC",
            "statement_correctness": "Yes", "reference_correctness": "Yes",
        }]
        outputs = {"case-A": [{
            "document_id": "case-A", "source_file": "run.jsonl", "claim_id": "c1",
            "claim_text": "Section 302 prescribes punishment for murder.",
            "assertion_text": "Section 302 prescribes punishment for murder.",
            "provision_type": "Section", "provision_number": "302",
            "act_raw": "Indian Penal Code", "act_norm": "indian penal code",
            "evidence_id": "Section 302 in The Indian Penal Code, 1860",
            "evidence_match_method": "exact_normalized", "verdict": "ENTAILED",
            "confidence": 0.98,
        }]}
        result = audit(annotations, outputs)
        row = result["rows"][0]
        self.assertEqual(result["rows_with_exact_statement_match"], 1)
        self.assertEqual(result["rows_with_exact_statement_and_reference_match"], 1)
        self.assertTrue(row["matched_model_claims"][0]["provision_identifier_match"])
        self.assertEqual(row["statement_correctness"], "Yes")
        self.assertEqual(result["audit_type"], "identity_and_provision_alignment_only_not_model_evaluation")

    def test_reference_match_does_not_remove_statement_ambiguity(self):
        annotation = {
            "annotation_id": "LR-0002", "case_reference": "case-A",
            "legal_statement": "Sections 147, 148 and 149 apply.",
            "legal_reference": "Section 148 IPC",
        }
        claims = []
        for number in ("147", "148", "149"):
            claims.append({
                "document_id": "case-A", "source_file": "run.jsonl", "claim_id": "c" + number,
                "claim_text": "Sections 147, 148 and 149 apply.", "assertion_text": "",
                "provision_type": "Section", "provision_number": number,
                "act_raw": "IPC", "verdict": "NOT_ENOUGH_INFORMATION",
            })
        row = audit([annotation], {"case-A": claims})["rows"][0]
        self.assertEqual(row["num_distinct_statement_matches"], 3)
        self.assertEqual(row["num_reference_aligned_matches"], 1)

    def test_missing_case_is_not_a_negative_prediction(self):
        result = audit([{
            "annotation_id": "LR-0003", "case_reference": "case-missing",
            "legal_statement": "Some statement", "legal_reference": "Some Act",
        }], {})
        self.assertFalse(result["rows"][0]["case_found_in_model_outputs"])
        self.assertEqual(result["row_coverage"]["case_found"], 0.0)


if __name__ == "__main__":
    unittest.main()
