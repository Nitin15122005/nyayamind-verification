#!/usr/bin/env python3
"""Validate and normalize the lawyer-reviewed NyayaMind Excel workbook."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = REPO_ROOT / "research/data/lawyer-review/raw/NyayaMind_Lawyer_Review_Final_Columns.xlsx"
DEFAULT_OUTPUT = REPO_ROOT / "research/data/lawyer-review/processed"
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
    """The workbook does not satisfy the documented annotation schema."""


def _text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def normalize_label(value: Any, *, field: str, row_number: int) -> str:
    value_text = _text(value)
    if value_text is None:
        raise DatasetValidationError(f"Excel data row {row_number}: missing {field}")
    label = LABELS.get(value_text.casefold())
    if label is None:
        raise DatasetValidationError(
            f"Excel data row {row_number}: invalid {field}={value_text!r}; "
            "expected Yes, No, or Partially"
        )
    return label


def normalize_dataframe(frame: pd.DataFrame) -> list[dict[str, Any]]:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DatasetValidationError("Missing required workbook columns: " + ", ".join(missing))

    records: list[dict[str, Any]] = []
    for index, source in frame.iterrows():
        excel_row = int(index) + 2
        record = {
            target: _text(source[source_column])
            for source_column, target in REQUIRED_COLUMNS.items()
        }
        for field in ("source_row_number", "case_reference", "legal_statement", "legal_reference"):
            if record[field] is None:
                raise DatasetValidationError(f"Excel row {excel_row}: missing {field}")

        record["statement_correctness"] = normalize_label(
            source["Is the legal statement correct? (Yes / No/ Partially)"],
            field="statement_correctness",
            row_number=excel_row,
        )
        record["reference_correctness"] = normalize_label(
            source["Is the legal reference correct?  (Yes / No/ Partially)"],
            field="reference_correctness",
            row_number=excel_row,
        )
        try:
            source_number = int(float(record["source_row_number"]))
        except (TypeError, ValueError) as exc:
            raise DatasetValidationError(
                f"Excel row {excel_row}: No. must be an integer"
            ) from exc
        record["source_row_number"] = source_number
        record["annotation_id"] = f"LR-{source_number:04d}"
        record["source_excel_row"] = excel_row
        records.append(record)

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
    tuple_groups: dict[tuple[Any, ...], list[str]] = {}
    semantic_groups: dict[tuple[Any, ...], list[str]] = {}
    semantic_fields = ("case_reference", "legal_statement", "legal_reference",
                       "statement_correctness", "reference_correctness",
                       "correction_or_clarification", "supporting_legal_authority")
    for row in records:
        tuple_key = (row["case_reference"], row["legal_statement"], row["legal_reference"])
        semantic_key = tuple(row[field] for field in semantic_fields)
        tuple_groups.setdefault(tuple_key, []).append(row["annotation_id"])
        semantic_groups.setdefault(semantic_key, []).append(row["annotation_id"])
    duplicate_tuple_groups = [ids for ids in tuple_groups.values() if len(ids) > 1]
    exact_content_groups = [ids for ids in semantic_groups.values() if len(ids) > 1]
    pattern = re.compile(r"\\b(?:as\\s+)?(?:row|no\\.?)\\s*#?\\s*(\\d+)\\b", re.IGNORECASE)
    cross_references = []
    for row in records:
        for field in ("correction_or_clarification", "supporting_legal_authority"):
            for match in pattern.finditer(row[field] or ""):
                cross_references.append({"annotation_id": row["annotation_id"],
                    "field": field, "referenced_source_row_number": int(match.group(1)),
                    "text": match.group(0)})
    return {
        "dataset_name": "NyayaMind Lawyer-Reviewed Statutory Claim Dataset",
        "schema_version": "1.0.0",
        "source_file": source_path.name,
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "worksheet": SHEET_NAME,
        "unit_of_analysis": "claim-provision assessment row",
        "num_rows": len(records),
        "num_unique_cases": len(cases),
        "num_unique_legal_statements": len(statements),
        "num_unique_case_statement_provision_tuples": len(case_statement_provision),
        "num_duplicate_case_statement_provision_groups": len(duplicate_tuple_groups),
        "num_rows_in_duplicate_case_statement_provision_groups": sum(map(len, duplicate_tuple_groups)),
        "duplicate_case_statement_provision_groups": duplicate_tuple_groups,
        "num_exact_content_duplicate_groups": len(exact_content_groups),
        "exact_content_duplicate_groups": exact_content_groups,
        "cross_reference_diagnostics": {"count": len(cross_references),
            "references": cross_references,
            "note": "Resolve source-row references before treating correction or authority text as standalone evidence."},
        "statement_correctness_counts": {
            label: statement_counts.get(label, 0) for label in ("Yes", "No", "Partially")
        },
        "reference_correctness_counts": {
            label: reference_counts.get(label, 0) for label in ("Yes", "No", "Partially")
        },
        "case_references": sorted(cases),
        "missing_optional_fields": {
            field: sum(row[field] is None for row in records)
            for field in ("correction_or_clarification", "supporting_legal_authority")
        },
        "split_policy": "No split generated; all future partitions must group by case_reference.",
        "limitations": [
            "Original judgments and judgment dates were not supplied with the workbook.",
            "Annotations do not independently establish case-specific relevance or historical applicability.",
            "Partially is retained as a distinct class.",
        ],
    }


def write_outputs(records: list[dict[str, Any]], summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "lawyer_review.normalized.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    pd.DataFrame(records).to_csv(
        output_dir / "lawyer_review.normalized.csv", index=False, encoding="utf-8"
    )
    (output_dir / "lawyer_review.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if not args.input.is_file():
        print(f"ERROR: workbook not found: {args.input}", file=sys.stderr)
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
