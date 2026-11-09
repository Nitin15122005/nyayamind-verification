from __future__ import annotations

import unittest

import pandas as pd

from scripts.import_lawyer_review import (
    DatasetValidationError,
    REQUIRED_COLUMNS,
    normalize_dataframe,
    normalize_label,
)


def make_frame() -> pd.DataFrame:
    rows = [{
        "No.": 1,
        "Case reference": "1956_41",
        "Legal statement for review": "Section 57 permits externment in specified circumstances.",
        "Provision / legal reference mentioned": "Bombay Police Act, 1951, Section 57",
        "Is the legal statement correct? (Yes / No/ Partially)": "Partially",
        "Is the legal reference correct?  (Yes / No/ Partially)": "Yes",
        "Correction or clarification (if required)": "Clarify statutory prerequisites.",
        "Legal authority supporting your assessment": "Maharashtra Police Act, 1951, s.57",
    }]
    return pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))


class TestLawyerReviewImport(unittest.TestCase):
    def test_normalizes_three_way_labels_and_preserves_dimensions(self):
        records = normalize_dataframe(make_frame())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["annotation_id"], "LR-0001")
        self.assertEqual(records[0]["statement_correctness"], "Partially")
        self.assertEqual(records[0]["reference_correctness"], "Yes")
        self.assertEqual(records[0]["case_reference"], "1956_41")

    def test_label_normalization_is_case_insensitive(self):
        self.assertEqual(
            normalize_label(" partially ", field="label", row_number=2),
            "Partially",
        )

    def test_rejects_unknown_label(self):
        with self.assertRaises(DatasetValidationError):
            normalize_label("Maybe", field="label", row_number=2)

    def test_rejects_missing_required_column(self):
        frame = make_frame().drop(columns=["Case reference"])
        with self.assertRaises(DatasetValidationError):
            normalize_dataframe(frame)

    def test_rejects_duplicate_source_row_numbers(self):
        frame = pd.concat([make_frame(), make_frame()], ignore_index=True)
        with self.assertRaises(DatasetValidationError):
            normalize_dataframe(frame)


if __name__ == "__main__":
    unittest.main()
