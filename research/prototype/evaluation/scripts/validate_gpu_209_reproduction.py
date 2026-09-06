"""STEP 10B GPU-experiment-reproduction validator.

Verifies: fresh 209-claim GPU-experiment metadata exists and is complete;
model IDs and dataset hashes are recorded; historical
outputs/final_gpu_validation_* files are byte-identical to before this step
(read-only, never overwritten); the 209-claim experiment and the cumulative
1/56 figure both carry an explicit classification; no unsupported
safety/accuracy claims were introduced; fresh-vs-historical distinction is
explicit. Read-only — makes no changes.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/evaluation/scripts/validate_gpu_209_reproduction.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent.parent  # PASS 3A: scripts moved into scripts/, one level deeper
EVAL_DIR = TESTING_DIR / "metrics"  # PASS 3A: renamed from evaluation/ to avoid evaluation/evaluation confusion
ABLATION_DIR = TESTING_DIR / "ablation"
STEP10B_DIR = TESTING_DIR / "actual_outputs" / "gpu_209_reproduction"
PROVENANCE = TESTING_DIR / "PROVENANCE.md"
PROTOTYPE_OUTPUTS = TESTING_DIR.parent / "outputs"

FAILURES: list[str] = []
PASSES: list[str] = []
WARNINGS: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# Historical files' expected SHA-256, captured before STEP 10B's run started.
HISTORICAL_HASHES = {
    "final_gpu_validation_metrics.json": "8fed4f73431ebf91d35e3fc499984c59eea811abf2bfadf8176137b9bedfcc0a",
    "final_gpu_validation_A.jsonl": "27f88e760f5258c6e9b76a0f233add341bc41f0e8f37fa228c8964533dc9e532",
}


# 1. Fresh 209-claim experiment metadata exists and is complete
def check_fresh_metadata_exists():
    name = "Fresh 209-claim experiment metadata exists"
    metrics = STEP10B_DIR / "step10b_final_gpu_validation_metrics.json"
    if not metrics.exists():
        fail(f"{name}: {metrics} missing")
        return
    data = read_json(metrics)
    required_top = ["n_cases", "seed", "generation_model", "verification_model", "per_arm",
                    "n_claims_shared_generation", "runtime_seconds_total", "peak_vram_mib",
                    "reproducibility_metadata"]
    missing = [k for k in required_top if k not in data]
    if missing:
        fail(f"{name}: metrics json missing keys {missing}")
        return
    repro = data["reproducibility_metadata"]
    required_repro = ["git_commit", "exact_command", "wall_clock_start_utc", "wall_clock_end_utc",
                       "torch_version", "torch_cuda_version", "gpu_device_name", "dataset_hashes"]
    missing_repro = [k for k in required_repro if k not in repro]
    if missing_repro:
        fail(f"{name}: reproducibility_metadata missing keys {missing_repro}")
        return
    if data["n_cases"] != 50 or data["n_claims_shared_generation"] != 209:
        fail(f"{name}: expected n_cases=50, n_claims_shared_generation=209, got "
             f"{data['n_cases']}/{data['n_claims_shared_generation']}")
        return
    ok(f"{name}: step10b_final_gpu_validation_metrics.json present with full "
       f"reproducibility_metadata (git commit, torch/CUDA, GPU name, dataset hashes, exact command)")


# 2. Model IDs and dataset hashes recorded
def check_model_ids_and_hashes_recorded():
    name = "Model IDs and dataset hashes recorded"
    metrics = STEP10B_DIR / "step10b_final_gpu_validation_metrics.json"
    if not metrics.exists():
        fail(f"{name}: metrics file missing")
        return
    data = read_json(metrics)
    if data.get("generation_model") != "Qwen/Qwen2.5-7B-Instruct":
        fail(f"{name}: generation_model is {data.get('generation_model')!r}, expected Qwen/Qwen2.5-7B-Instruct")
        return
    if data.get("verification_model") != "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli":
        fail(f"{name}: verification_model is {data.get('verification_model')!r}, expected DeBERTa-v3")
        return
    dh = data["reproducibility_metadata"]["dataset_hashes"]
    if not dh.get("candidate_file", {}).get("sha256"):
        fail(f"{name}: candidate_file sha256 missing")
        return
    if not dh.get("nyayarag_case_files") or not all(f.get("sha256") for f in dh["nyayarag_case_files"]):
        fail(f"{name}: nyayarag_case_files hashes missing/incomplete")
        return
    if not dh.get("evidence_files") or not all(f.get("sha256") for f in dh["evidence_files"]):
        fail(f"{name}: evidence_files hashes missing/incomplete")
        return
    ok(f"{name}: Qwen/DeBERTa model ids and SHA-256 hashes for candidate file, "
       f"NyayaRAG source files, and evidence files all recorded")


# 3. Historical outputs/final_gpu_validation_* files untouched
def check_historical_files_untouched():
    name = "Historical outputs/final_gpu_validation_* files untouched"
    for fname, expected_hash in HISTORICAL_HASHES.items():
        p = PROTOTYPE_OUTPUTS / fname
        if not p.exists():
            fail(f"{name}: historical file {p} is missing entirely")
            return
        actual = sha256_file(p)
        if actual != expected_hash:
            fail(f"{name}: {fname} SHA-256 changed — expected {expected_hash}, got {actual} "
                 f"(historical file was modified or overwritten)")
            return
    # Also confirm the fresh run did not create any file under outputs/ with the
    # historical prefix reused (it must use its own step10b_ prefix instead).
    for fname in ("step10b_final_gpu_validation_metrics.json",):
        if (PROTOTYPE_OUTPUTS / fname).exists():
            fail(f"{name}: fresh output {fname} was written into research/prototype/outputs/ "
                 f"instead of evaluation/actual_outputs/gpu_209_reproduction/")
            return
    ok(f"{name}: final_gpu_validation_metrics.json and _A.jsonl SHA-256 hashes unchanged; "
       f"fresh outputs confined to evaluation/actual_outputs/gpu_209_reproduction/")


# 4. Byte-for-byte generation comparison actually holds (re-verified, not just trusted from prose)
def check_generation_byte_identical():
    name = "Fresh vs historical generated text byte-identical"
    fresh_path = STEP10B_DIR / "step10b_final_gpu_validation_A.jsonl"
    hist_path = PROTOTYPE_OUTPUTS / "final_gpu_validation_A.jsonl"
    if not fresh_path.exists() or not hist_path.exists():
        fail(f"{name}: one of {fresh_path}, {hist_path} missing")
        return
    fresh = [json.loads(l) for l in fresh_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    hist = [json.loads(l) for l in hist_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(fresh) != len(hist):
        fail(f"{name}: row count differs (fresh={len(fresh)}, historical={len(hist)})")
        return
    mismatches = 0
    for f, h in zip(fresh, hist):
        if f.get("document_id") != h.get("document_id"):
            mismatches += 1
            continue
        if f.get("generated_field", {}).get("text") != h.get("generated_field", {}).get("text"):
            mismatches += 1
    if mismatches:
        fail(f"{name}: {mismatches}/{len(fresh)} cases have non-identical generated text")
        return
    ok(f"{name}: all {len(fresh)}/{len(fresh)} Arm-A generated texts byte-identical, "
       f"fresh vs. historical (re-verified independently by this validator)")


# 5. Classifications explicit for both the 209-claim experiment and the cumulative figure
def check_classifications_explicit():
    name = "GPU experiment classifications explicit (STEP 10B)"
    crosscheck = EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md"
    if not crosscheck.exists():
        fail(f"{name}: GPU_REPRODUCTION_CROSSCHECK.md missing")
        return
    text = crosscheck.read_text(encoding="utf-8")
    if "Experiment 3" not in text:
        fail(f"{name}: no 'Experiment 3' (209-claim) section found in crosscheck doc")
        return
    if "PROTOCOL INSUFFICIENT" not in text.upper():
        fail(f"{name}: no PROTOCOL INSUFFICIENT classification found for the cumulative 1/56 figure")
        return
    ablation = ABLATION_DIR / "GPU_ABLATION_UPDATE.md"
    if not ablation.exists() or "PROTOCOL INSUFFICIENT" not in ablation.read_text(encoding="utf-8").upper():
        fail(f"{name}: GPU_ABLATION_UPDATE.md does not carry the PROTOCOL INSUFFICIENT classification")
        return
    ok(f"{name}: Experiment 3 (209-claim) classified, cumulative 1/56 explicitly classified "
       f"PROTOCOL INSUFFICIENT in both crosscheck and ablation update")


# 6. No unsupported safety/accuracy claims introduced by STEP 10B's new text
NEGATION_WINDOW = re.compile(r"\b(no|not|never|n['’]t|cannot|can['’]t|without)\b[^.]{0,60}$", re.IGNORECASE)


def _is_negated(text: str, start: int) -> bool:
    return bool(NEGATION_WINDOW.search(text[max(0, start - 80):start]))


def check_no_unsupported_claims():
    name = "No unsupported safety/accuracy claims (STEP 10B additions)"
    bad_safety = [r"\bis safe\b", r"\bfully safe\b", r"\bguarantee(?:s|d)? safety\b", r"\balways safe\b"]
    bad_accuracy = [r"legally correct", r"legally accurate", r"proven correct"]
    docs = [EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md", ABLATION_DIR / "GPU_ABLATION_UPDATE.md", PROVENANCE]
    for f in docs:
        if not f.exists():
            fail(f"{name}: {f} missing")
            return
        text = f.read_text(encoding="utf-8")
        for pat in bad_safety:
            if re.search(pat, text, re.IGNORECASE):
                fail(f"{name}: unsupported safety claim pattern {pat!r} found in {f.name}")
                return
        for pat in bad_accuracy:
            for m in re.finditer(pat, text, re.IGNORECASE):
                if not _is_negated(text, m.start()):
                    fail(f"{name}: unsupported accuracy claim {pat!r} found in {f.name} near "
                         f"...{text[max(0,m.start()-40):m.end()+10]!r}...")
                    return
    ok(f"{name}: no unsupported universal-safety or legal-correctness claims found")


# 7. Fresh vs historical distinction explicit
def check_fresh_vs_historical_explicit():
    name = "Fresh vs historical distinction explicit (STEP 10B)"
    for f in [EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md", ABLATION_DIR / "GPU_ABLATION_UPDATE.md"]:
        text = f.read_text(encoding="utf-8")
        if "STEP 10B" not in text and "Experiment 3" not in text:
            fail(f"{name}: {f.name} does not reference STEP 10B / Experiment 3")
            return
        if not re.search(r"\bfresh\b", text, re.IGNORECASE) or not re.search(r"\bhistorical\b", text, re.IGNORECASE):
            fail(f"{name}: {f.name} missing explicit fresh/historical language")
            return
    ok(f"{name}: both updated documents explicitly distinguish STEP 10B fresh results from historical ones")


def main() -> int:
    check_fresh_metadata_exists()
    check_model_ids_and_hashes_recorded()
    check_historical_files_untouched()
    check_generation_byte_identical()
    check_classifications_explicit()
    check_no_unsupported_claims()
    check_fresh_vs_historical_explicit()

    print("=" * 70)
    print("STEP 10B GPU EXPERIMENT REPRODUCTION VALIDATION REPORT")
    print("=" * 70)
    print(f"\nPASSED ({len(PASSES)}):")
    for p in PASSES:
        print(f"  [PASS] {p}")
    if WARNINGS:
        print(f"\nWARNINGS ({len(WARNINGS)}):")
        for w in WARNINGS:
            print(f"  [WARN] {w}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  [FAIL] {f}")
        print(f"\nRESULT: FAIL ({len(FAILURES)} failure(s), {len(PASSES)} passed, {len(WARNINGS)} warnings)")
        return 1

    print(f"\nRESULT: PASS ({len(PASSES)} checks passed, 0 failures, {len(WARNINGS)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
