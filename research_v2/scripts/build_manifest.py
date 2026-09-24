#!/usr/bin/env python3
"""Write immutable references and SHA-256 hashes for audited source datasets."""
from __future__ import annotations
import hashlib, json, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=[
 "research/prototype/evaluation/expected_outputs/controlled_benchmark_gold/controlled_verifier_benchmark.jsonl",
 "research/prototype/evaluation/expected_outputs/synthetic_stress_gold/run_synthetic_stress.jsonl",
 "research/prototype/outputs/final_gpu_validation_A.jsonl",
 "research/prototype/outputs/final_gpu_validation_B.jsonl",
 "research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl",
 "research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl",
 "research/prototype/outputs/natural_candidate_selected_ids_50_final_validation.json",
]
def main():
 rows=[]
 for rel in SOURCES:
  p=ROOT/rel
  rows.append({"path":rel,"exists":p.is_file(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,"size_bytes":p.stat().st_size if p.is_file() else None})
 dest=ROOT/"research_v2"/"data"/"manifests"/"source_manifest.json"
 dest.write_text(json.dumps({"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"sources":rows},indent=2),encoding="utf-8")
 print(dest)
if __name__=="__main__":main()
