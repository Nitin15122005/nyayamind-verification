from __future__ import annotations

import unittest
from scripts.audit_lawyer_review_alignment import audit, norm_reference, norm_text


class TestLawyerReviewAlignmentAudit(unittest.TestCase):
    def test_normalizers(self):
        self.assertEqual(norm_text("  SECTION  302  "), "section 302")
        self.assertEqual(norm_reference("Section 302 of IPC"), "section302ofipc")

    def test_statement_and_reference_alignment(self):
        annotations = [{
            "annotation_id": "LR-0001", "case_reference": "case-A",
            "legal_statement": "Section 302 prescribes punishment for murder.",
            "legal_reference": "Section 302 IPC",
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
        self.assertEqual(result["rows_with_exact_statement_match"], 1)
        self.assertEqual(result["rows_with_exact_statement_and_reference_match"], 1)
        self.assertEqual(result["audit_type"], "identity_alignment_only_not_model_evaluation")

    def test_missing_case_is_not_a_negative_prediction(self):
        result = audit([{
            "annotation_id": "LR-0002", "case_reference": "case-missing",
            "legal_statement": "Some statement", "legal_reference": "Some Act",
        }], {})
        self.assertFalse(result["rows"][0]["case_found_in_model_outputs"])
        self.assertEqual(result["row_coverage"]["case_found"], 0.0)


if __name__ == "__main__":
    unittest.main()
