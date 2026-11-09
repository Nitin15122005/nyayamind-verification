from __future__ import annotations

import unittest

import pandas as pd

from scripts.evaluate_lawyer_review import evaluate


class TestLawyerReviewEvaluation(unittest.TestCase):
    def _annotations(self):
        return [
            {
                "annotation_id": "LR-0001",
                "case_reference": "case-A",
                "statement_correctness": "Yes",
                "reference_correctness": "No",
            },
            {
                "annotation_id": "LR-0002",
                "case_reference": "case-A",
                "statement_correctness": "Partially",
                "reference_correctness": "Partially",
            },
            {
                "annotation_id": "LR-0003",
                "case_reference": "case-B",
                "statement_correctness": "No",
                "reference_correctness": "Yes",
            },
        ]

    def test_scores_two_targets_separately(self):
        predictions = pd.DataFrame([
            {"annotation_id": "LR-0001", "predicted_statement_correctness": "Yes",
             "predicted_reference_correctness": "No"},
            {"annotation_id": "LR-0002", "predicted_statement_correctness": "No",
             "predicted_reference_correctness": "Partially"},
            {"annotation_id": "LR-0003", "predicted_statement_correctness": "No",
             "predicted_reference_correctness": "Yes"},
        ])
        result = evaluate(self._annotations(), predictions)
        self.assertEqual(result["n_rows"], 3)
        self.assertEqual(result["n_unique_cases"], 2)
        self.assertEqual(result["targets"]["statement_correctness"]["accuracy"], 2 / 3)
        self.assertEqual(result["targets"]["reference_correctness"]["accuracy"], 1.0)
        self.assertEqual(result["targets"]["statement_correctness"]["n"], 3)

    def test_rejects_missing_prediction_rows(self):
        predictions = pd.DataFrame([
            {"annotation_id": "LR-0001", "predicted_statement_correctness": "Yes",
             "predicted_reference_correctness": "No"},
        ])
        with self.assertRaisesRegex(ValueError, "do not match exactly"):
            evaluate(self._annotations(), predictions)

    def test_rejects_unknown_labels(self):
        predictions = pd.DataFrame([
            {"annotation_id": "LR-0001", "predicted_statement_correctness": "TRUE",
             "predicted_reference_correctness": "No"},
            {"annotation_id": "LR-0002", "predicted_statement_correctness": "Partially",
             "predicted_reference_correctness": "Partially"},
            {"annotation_id": "LR-0003", "predicted_statement_correctness": "No",
             "predicted_reference_correctness": "Yes"},
        ])
        with self.assertRaisesRegex(ValueError, "outside"):
            evaluate(self._annotations(), predictions)


if __name__ == "__main__":
    unittest.main()
