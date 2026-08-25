#!/usr/bin/env python3
"""
Phase 1: Build Controlled Verifier Benchmark from 59 canonical statutes.
Programmatically creates 3 claim types per statute:
  1. ENTAILED: Faithful paraphrase of the statute text
  2. CONTRADICTED: Deterministic legal contradiction
  3. NOT_ENOUGH_INFORMATION: Related statement that cannot be established from the statute text

Deterministic seed = 42. Output: research/prototype/outputs/verifier_benchmark.jsonl
"""
import json
import random
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml
from src.data_loader import load_usable_evidence

def build_benchmark_claims(usable_records, seed=42):
    random.seed(seed)
    benchmark_items = []

    for rec in usable_records:
        key = rec.dataset_citation_key
        text = rec.canonical_text
        prov_type = rec.provision_type
        prov_num = rec.provision_number
        act = rec.act

        # 1. ENTAILED: Faithful paraphrase / attribution-bearing faithful statement
        # We test faithful paraphrases of the statute rule
        entailed_hypothesis = f"According to {prov_type} {prov_num} of {act}, {text}"
        
        # 2. CONTRADICTED: Deterministic legal contradiction
        # Transform the statute text to contradict its core legal mandate
        text_lower = text.lower()
        if "shall not" in text_lower:
            contradicted_text = text.replace("shall not", "shall at all times").replace("Shall not", "Shall at all times")
        elif "shall be punished" in text_lower:
            contradicted_text = text.replace("shall be punished with", "is completely exempt from punishment and cannot be penalized for").replace("shall also be liable to fine", "shall not be subject to any fine")
        elif "shall have powers" in text_lower or "shall have power" in text_lower:
            contradicted_text = text.replace("shall have power", "has no power or authority").replace("shall have powers", "has no powers or authority")
        elif "shall" in text_lower:
            contradicted_text = text.replace("shall", "shall not").replace("Shall", "Shall not")
        elif "may" in text_lower:
            contradicted_text = text.replace("may", "shall under no circumstances").replace("May", "Shall under no circumstances")
        else:
            contradicted_text = f"This provision has been completely repealed and imposes no legal effect whatsoever regarding {text[:30]}."
        
        contradicted_hypothesis = f"{prov_type} {prov_num} of {act} provides that {contradicted_text}"

        # 3. NOT_ENOUGH_INFORMATION: Extraneous related claim that cannot be established from evidence alone
        nei_hypothesis = (
            f"{prov_type} {prov_num} of {act} requires prior written authorization from the High Court Registrar "
            f"and mandatory filing within 14 business days of the alleged occurrence."
        )

        item_id_base = f"bench_{hash(key) & 0xffffffff:08x}"

        benchmark_items.append({
            "benchmark_id": f"{item_id_base}_entailed",
            "evidence_key": key,
            "evidence_text": text,
            "hypothesis": entailed_hypothesis,
            "expected_label": "ENTAILED",
            "construction_rule": "faithful_paraphrase_with_attribution",
            "provision_type": prov_type,
            "provision_number": prov_num,
            "act_name": act,
        })

        benchmark_items.append({
            "benchmark_id": f"{item_id_base}_contradicted",
            "evidence_key": key,
            "evidence_text": text,
            "hypothesis": contradicted_hypothesis,
            "expected_label": "CONTRADICTED",
            "construction_rule": "deterministic_negation",
            "provision_type": prov_type,
            "provision_number": prov_num,
            "act_name": act,
        })

        benchmark_items.append({
            "benchmark_id": f"{item_id_base}_nei",
            "evidence_key": key,
            "evidence_text": text,
            "hypothesis": nei_hypothesis,
            "expected_label": "NOT_ENOUGH_INFORMATION",
            "construction_rule": "interpretive_beyond_evidence",
            "provision_type": prov_type,
            "provision_number": prov_num,
            "act_name": act,
        })

    return benchmark_items

def main():
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    _, usable_records = load_usable_evidence(canonical_path, audit_path, set(config["usable_evidence_verdicts"]))

    benchmark = build_benchmark_claims(usable_records, seed=42)
    output_path = _PROTOTYPE_ROOT / "outputs" / "verifier_benchmark.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for item in benchmark:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Generated {len(benchmark)} controlled benchmark records for {len(usable_records)} statutes.")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
