import csv
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publication_annotation.py"
SPEC = importlib.util.spec_from_file_location("publication_annotation", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_blind_split_hides_identifier_metadata_and_labels(tmp_path):
    source = tmp_path / "worksheet.csv"
    write_csv(source, [{
        "item_id": "G03_0001", "source_text": "Rule text",
        "source_url": "https://example.org", "candidate_claim_without_citation": "Claim",
        "adjudicated_label": "ENTAILED", "mismatched_identifier": "Section 99",
    }])
    args = type("Args", (), {"worksheet": source, "outdir": tmp_path / "packets", "seed": 7})
    MOD.command_split_gold03(args)
    r1 = MOD.read_csv(tmp_path / "packets" / "GOLD03_R1_BLIND.csv")[0]
    assert set(r1) == set(MOD.GOLD03_REVIEW_FIELDS)
    assert "adjudicated_label" not in r1
    assert "mismatched_identifier" not in r1


def test_merge_requires_same_item_ids_and_preserves_disagreement(tmp_path):
    a, b, out = tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "merged.csv"
    common = {"item_id": "G03_1", "source_text": "Rule", "source_url": "u",
              "claim_text": "Claim", "rationale": "Because", "reviewer_id": "R"}
    write_csv(a, [{**common, "label": "ENTAILED"}])
    write_csv(b, [{**common, "label": "CONTRADICTED", "reviewer_id": "S"}])
    args = type("Args", (), {"reviewer1": a, "reviewer2": b, "output": out})
    MOD.command_merge_gold03(args)
    row = MOD.read_csv(out)[0]
    assert row["reviewer1_label"] == "ENTAILED"
    assert row["reviewer2_label"] == "CONTRADICTED"
    assert row["adjudicated_label"] == ""


def test_cohens_kappa_perfect_and_chance_agreement():
    rows = [{"reviewer1_label": "ENTAILED", "reviewer2_label": "ENTAILED"},
            {"reviewer1_label": "CONTRADICTED", "reviewer2_label": "CONTRADICTED"}]
    assert MOD.kappa(rows) == 1.0


def test_natural_export_keeps_claim_and_case_grouping(tmp_path):
    src, out = tmp_path / "input.jsonl", tmp_path / "out.csv"
    src.write_text(json.dumps({
        "document_id": "case_1", "case_text": "case context",
        "claims": [{"claim_id": "c1", "claim_text": "whole sentence",
                    "assertion_text": "atomic claim",
                    "citation_extracted": {"provision_number": "10"},
                    "verdict": "ENTAILED", "evidence_text": "statute"}],
    }) + "\n", encoding="utf-8")
    args = type("Args", (), {"input": src, "output": out, "reviewer": "R1"})
    MOD.command_export_natural(args)
    row = MOD.read_csv(out)[0]
    assert row["claim_text"] == "atomic claim"
    assert row["document_id"] == "case_1"
    assert row["reviewer_label"] == ""
