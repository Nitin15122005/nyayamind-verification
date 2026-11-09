from __future__ import annotations

import unittest
from scripts.generate_lawyer_review_baseline import generate


class TestLawyerReviewBaseline(unittest.TestCase):
    def fixture(self):
        rows = []
        labels = [
            ("Yes", "No"), ("No", "Yes"), ("Partially", "Yes"),
            ("Partially", "Partially"), ("Yes", "Yes"), ("No", "Partially"),
        ]
        for case_idx, pair in enumerate(labels):
            for row_idx in range(2):
                rows.append({
                    "annotation_id": f"LR-{case_idx}-{row_idx}",
                    "case_reference": f"case-{case_idx}",
                    "statement_correctness": pair[0],
                    "reference_correctness": pair[1],
                })
        return rows

    def test_generates_complete_oof_predictions_without_case_leakage(self):
        predictions, metadata = generate(self.fixture(), n_splits=3, seed=7)
        self.assertEqual(len(predictions), 12)
        self.assertFalse(predictions.isna().any().any())
        self.assertEqual(predictions["annotation_id"].nunique(), 12)
        for target in metadata["targets"].values():
            self.assertEqual(len(target["folds"]), 3)
            self.assertTrue(all(fold["train_cases"] + fold["test_cases"] == 6 for fold in target["folds"]))
            self.assertTrue(all(fold["test_rows"] > 0 for fold in target["folds"]))

    def test_rejects_duplicate_annotation_ids(self):
        rows = self.fixture()
        rows[1]["annotation_id"] = rows[0]["annotation_id"]
        with self.assertRaises(ValueError):
            generate(rows, n_splits=3)

    def test_rejects_too_many_folds(self):
        with self.assertRaises(ValueError):
            generate(self.fixture(), n_splits=7)


if __name__ == "__main__":
    unittest.main()
