from __future__ import annotations

import unittest

import pandas as pd

from scripts.evaluate_lawyer_review_features import (
    CATEGORICAL, NUMERIC, build_feature_frame, evaluate,
)


class TestLawyerReviewFeatureEvaluation(unittest.TestCase):
    def _annotation(self, i: int) -> dict:
        label = ["Yes", "No", "Partially"][i % 3]
        return {
            "annotation_id": f"LR-{i:04d}", "case_reference": f"case-{i:04d}",
            "statement_correctness": label, "reference_correctness": label,
            "correction_or_clarification": "must never enter features",
            "supporting_legal_authority": "must never enter features",
        }

    def _audit_row(self, i: int) -> dict:
        return {
            "annotation_id": f"LR-{i:04d}", "exact_statement_match": True,
            "num_reference_aligned_matches": 1, "num_candidate_claims_for_case": 3,
            "matched_model_claims": [{
                "provision_identifier_match": True, "reference_text_match": False,
                "act_match": "match", "provision_type": "Section",
                "evidence_match_method": "exact_normalized", "verdict": "ENTAILED",
                "verifier_model": "deberta", "evidence_id": "Section 1 in Act",
                "evidence_text": "text", "confidence": 0.9,
            }],
        }

    def test_builds_only_unique_aligned_structured_features(self):
        annotations = [self._annotation(i) for i in range(3)]
        audit_rows = [self._audit_row(i) for i in range(3)]
        audit_rows[1]["num_reference_aligned_matches"] = 2
        audit_rows[2]["exact_statement_match"] = False
        frame, diagnostics = build_feature_frame(annotations, {"rows": audit_rows})
        self.assertEqual(len(frame), 1)
        self.assertEqual(diagnostics["excluded_rows"]["reference_alignment_not_unique"], 1)
        self.assertEqual(diagnostics["excluded_rows"]["no_exact_statement_match"], 1)
        self.assertFalse(set(CATEGORICAL + NUMERIC) & {
            "correction_or_clarification", "supporting_legal_authority",
            "case_reference", "annotation_id",
        })

    def test_case_grouped_predictions_cover_each_row_and_both_targets(self):
        rows = []
        for i in range(30):
            label = ["Yes", "No", "Partially"][i % 3]
            rows.append({
                "annotation_id": f"LR-{i:04d}", "case_reference": f"case-{i:04d}",
                "statement_correctness": label, "reference_correctness": label,
                "provision_type": "Section" if i % 2 else "Article",
                "act_match": "match", "evidence_match_method": "exact_normalized",
                "provision_identifier_match": "True", "reference_text_match": "False",
                "verdict": ["ENTAILED", "CONTRADICTED", "NO_EVIDENCE"][i % 3],
                "verifier_model": "deberta", "evidence_present": "yes",
                "confidence": 0.7 + (i % 3) * 0.1, "candidate_count": 1.0,
            })
        predictions, metrics = evaluate(pd.DataFrame(rows), folds=3, seed=7, bootstrap_reps=100)
        self.assertEqual(len(predictions), 30)
        for target in ("statement_correctness", "reference_correctness"):
            self.assertIn(f"predicted_{target}_model", predictions.columns)
            self.assertIn(f"predicted_{target}_majority", predictions.columns)
            self.assertEqual(metrics["targets"][target]["n"], 30)
            for fold in metrics["targets"][target]["folds"]:
                self.assertGreater(fold["train_cases"], 0)
                self.assertGreater(fold["test_cases"], 0)


if __name__ == "__main__":
    unittest.main()
