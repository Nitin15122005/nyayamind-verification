from __future__ import annotations

import unittest
import pandas as pd
from scripts.evaluate_lawyer_review import evaluate


class TestLawyerReviewEvaluation(unittest.TestCase):
    def annotations(self):
        return [
            {"annotation_id":"LR-0001","case_reference":"case-A","statement_correctness":"Yes","reference_correctness":"No"},
            {"annotation_id":"LR-0002","case_reference":"case-A","statement_correctness":"Partially","reference_correctness":"Partially"},
            {"annotation_id":"LR-0003","case_reference":"case-B","statement_correctness":"No","reference_correctness":"Yes"},
        ]

    def predictions(self):
        return pd.DataFrame([
            {"annotation_id":"LR-0001","predicted_statement_correctness":"Yes","predicted_reference_correctness":"No"},
            {"annotation_id":"LR-0002","predicted_statement_correctness":"No","predicted_reference_correctness":"Partially"},
            {"annotation_id":"LR-0003","predicted_statement_correctness":"No","predicted_reference_correctness":"Yes"},
        ])

    def test_scores_targets_separately(self):
        result = evaluate(self.annotations(), self.predictions())
        self.assertEqual(result["n_rows"], 3)
        self.assertEqual(result["n_unique_cases"], 2)
        self.assertAlmostEqual(result["targets"]["statement_correctness"]["accuracy"], 2/3)
        self.assertEqual(result["targets"]["reference_correctness"]["accuracy"], 1.0)

    def test_rejects_unmatched_ids(self):
        with self.assertRaisesRegex(ValueError, "do not match exactly"):
            evaluate(self.annotations(), self.predictions().iloc[:1])

    def test_rejects_unknown_labels(self):
        predictions = self.predictions()
        predictions.loc[0, "predicted_statement_correctness"] = "TRUE"
        with self.assertRaisesRegex(ValueError, "outside"):
            evaluate(self.annotations(), predictions)


if __name__ == "__main__":
    unittest.main()
