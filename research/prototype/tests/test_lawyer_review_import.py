from __future__ import annotations

import unittest
import pandas as pd
from scripts.import_lawyer_review import DatasetValidationError, REQUIRED_COLUMNS, normalize_dataframe, normalize_label


def frame():
    return pd.DataFrame([{
        "No.": 1,
        "Case reference": "1956_41",
        "Legal statement for review": "Section 57 permits externment in specified circumstances.",
        "Provision / legal reference mentioned": "Bombay Police Act, 1951, Section 57",
        "Is the legal statement correct? (Yes / No/ Partially)": "Partially",
        "Is the legal reference correct?  (Yes / No/ Partially)": "Yes",
        "Correction or clarification (if required)": "Clarify statutory prerequisites.",
        "Legal authority supporting your assessment": "Maharashtra Police Act, 1951, s.57",
    }], columns=list(REQUIRED_COLUMNS))


class TestLawyerReviewImport(unittest.TestCase):
    def test_preserves_two_independent_labels(self):
        row = normalize_dataframe(frame())[0]
        self.assertEqual(row["annotation_id"], "LR-0001")
        self.assertEqual(row["statement_correctness"], "Partially")
        self.assertEqual(row["reference_correctness"], "Yes")

    def test_normalizes_label_case_and_whitespace(self):
        self.assertEqual(normalize_label(" partially ", field="label", row_number=2), "Partially")

    def test_rejects_unknown_label(self):
        with self.assertRaises(DatasetValidationError):
            normalize_label("Maybe", field="label", row_number=2)

    def test_rejects_missing_column(self):
        with self.assertRaises(DatasetValidationError):
            normalize_dataframe(frame().drop(columns=["Case reference"]))

    def test_summary_distinguishes_tuple_and_exact_content_duplicates(self):
        from scripts.import_lawyer_review import build_summary
        combined = pd.concat([frame(), frame()], ignore_index=True)
        combined.loc[1, "No."] = 2
        records = normalize_dataframe(combined)
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xlsx"
            source.write_bytes(b"fixture")
            summary = build_summary(records, source)
        self.assertEqual(summary["num_duplicate_case_statement_provision_groups"], 1)
        self.assertEqual(summary["num_exact_content_duplicate_groups"], 1)

    def test_summary_detects_row_cross_references(self):
        from scripts.import_lawyer_review import build_summary
        records = normalize_dataframe(frame())
        records[0]["correction_or_clarification"] = "As row 5, see correction."
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xlsx"
            source.write_bytes(b"fixture")
            summary = build_summary(records, source)
        self.assertEqual(summary["cross_reference_diagnostics"]["count"], 1)

    def test_rejects_duplicate_source_ids(self):
        with self.assertRaises(DatasetValidationError):
            normalize_dataframe(pd.concat([frame(), frame()], ignore_index=True))


if __name__ == "__main__":
    unittest.main()
