#!/usr/bin/env python3
"""Validate and normalize the lawyer-reviewed NyayaMind Excel workbook.

This is a deterministic data-ingestion step. It does not train a model, infer
legal correctness, modify the source workbook, or silently discard rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = (
    REPO_ROOT
    / "research"
    / "data"
    / "lawyer-review"
    / "raw"
    / "NyayaMind_Lawyer_Review_Final_Columns.xlsx"
)
DEFAULT_OUTPUT = REPO_ROOT / "research" / "data" / "lawyer-review" / "processed"

SHEET_NAME = "Legal Review"
REQUIRED_COLUMNS = {
    "No.": "source_row_number",
    "Case reference": "case_reference",
    "Legal statement for review": "legal_statement",
    "Provision / legal reference mentioned": "legal_reference",
    "Is the legal statement correct? (Yes / No/ Partially)": "statement_correctness",
    "Is the legal reference correct?  (Yes / No/ Partially)": "reference_correctness",
    "Correction or clarification (if required)": "correction_or_clarification",
    "Legal authority supporting your assessment": "supporting_legal_authority",
}
LABELS = {"yes": "Yes", "no": "No", "partially": "Partially"}


class DatasetValidationError(ValueError):
    """Raised when the source workbook violates the documented data contract."""


def _text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    result = str(value).strip()
    return result or None


def normalize_label(value: Any, *, field: str, row_number: int) -> str:
    text = _text(value)
    if text is None:
        raise DatasetValidationError(
            f"Excel data row {row_number}: missing required label in {field!r}"
        )
    normalized = LABELS.get(text.casefold())
    if normalized is None:
        raise DatasetValidationError(
            f"Excel data row {row_number}: invalid {field!r} value {text!r}; "
            "expected Yes, No, or Partially"
        )
    return normalized


def normalize_dataframe(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert the Legal Review worksheet to stable, schema-controlled records."""
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DatasetValidationError(
            "Missing required workbook columns: " + ", ".join(missing)
        )

    records: list[dict[str, Any]] = []
    for index, source in frame.iterrows():
        excel_row = int(index) + 2  # header is Excel row 1
        row: dict[str, Any] = {}
        for source_column, target_field in REQUIRED_COLUMNS.items():
            row[target_field] = _text(source[source_column])

        if row["source_row_number"] is None:
            raise DatasetValidationError(f"Excel row {excel_row}: missing No.")
        if row["case_reference"] is None:
            raise DatasetValidationError(f"Excel row {excel_row}: missing Case reference")
        if row["legal_statement"] is None:
            raise DatasetValidationError(f"Excel row {excel_row}: missing legal statement")
        if row["legal_reference"] is None:
            raise DatasetValidationError(f"Excel row {excel_row}: missing legal reference")

        row["statement_correctness"] = normalize_label(
            source["Is the legal statement correct? (Yes / No/ Partially)"],
            field="statement_correctness",
            row_number=excel_row,
        )
        row["reference_correctness"] = normalize_label(
            source["Is the legal reference correct?  (Yes / No/ Partially)"],
            field="reference_correctness",
            row_number=excel_row,
        )
        row["annotation_id"] = f"LR-{int(float(row['source_row_number'])):04d}"
        row["source_excel_row"] = excel_row
        records.append(row)

    ids = [record["annotation_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise DatasetValidationError("Duplicate source No. values; annotation IDs are not unique")

    return records


def build_summary(records: list[dict[str, Any]], source_path: Path) -> dict[str, Any]:
    statement_counts = Counter(row["statement_correctness"] for row in records)
    reference_counts = Counter(row["reference_correctness"] for row in records)
    cases = {row["case_reference"] for row in records}
    statements = {row["legal_statement"] for row in records}
    case_statement_provision = {
        (row["case_reference"], row["legal_statement"], row["legal_reference"])
        for row in records
    }
    exact_rows = [
        (
            row["case_reference"],
            row["legal_statement"],
            row["legal_reference"],
            row["statement_correctness"],
            row["reference_correctness"],
        )
        for row in records
    ]
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()

    return {
        "dataset_name": "NyayaMind Lawyer-Reviewed Statutory Claim Dataset",
        "schema_version": "1.0.0",
        "source_file": source_path.name,
        "source_sha256": digest,
        "worksheet": SHEET_NAME,
        "unit_of_analysis": "claim-provision assessment row",
        "num_rows": len(records),
        "num_unique_cases": len(cases),
        "num_unique_legal_statements": len(statements),
        "num_unique_case_statement_provision_tuples": len(case_statement_provision),
        "num_exact_annotation_duplicates": len(exact_rows) - len(set(exact_rows)),
        "statement_correctness_counts": {
            label: statement_counts.get(label, 0)
            for label in ("Yes", "No", "Partially")
        },
        "reference_correctness_counts": {
            label: reference_counts.get(label, 0)
            for label in ("Yes", "No", "Partially")
        },
        "case_references": sorted(cases),
        "missing_optional_fields": {
            field: sum(row[field] is None for row in records)
            for field in ("correction_or_clarification", "supporting_legal_authority")
        },
        "split_policy": (
            "No split generated. Any future split must group by case_reference."
        ),
        "limitations": [
            "The source workbook states that original judgments and judgment dates were not supplied.",
            "Annotations do not independently establish case-specific relevance or historical applicability.",
            "Partially is retained as a distinct class.",
        ],
    }


def write_outputs(records: list[dict[str, Any]], summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "lawyer_review.normalized.jsonl"
    csv_path = output_dir / "lawyer_review.normalized.csv"
    summary_path = output_dir / "lawyer_review.summary.json"

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    pd.DataFrame(records).to_csv(csv_path, index=False, encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(
            f"ERROR: workbook not found: {args.input}\n"
            "Place the lawyer-reviewed workbook at the documented raw/ path or pass --input.",
            file=sys.stderr,
        )
        return 2

    try:
        frame = pd.read_excel(args.input, sheet_name=SHEET_NAME, engine="openpyxl")
        records = normalize_dataframe(frame)
        summary = build_summary(records, args.input)
        write_outputs(records, summary, args.output_dir)
    except (DatasetValidationError, ValueError, OSError, ImportError) as exc:
        print(f"ERROR: lawyer-review import failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "status": "ok",
        "rows": summary["num_rows"],
        "unique_cases": summary["num_unique_cases"],
        "statement_correctness_counts": summary["statement_correctness_counts"],
        "reference_correctness_counts": summary["reference_correctness_counts"],
        "output_dir": str(args.output_dir),
        "source_sha256": summary["source_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
