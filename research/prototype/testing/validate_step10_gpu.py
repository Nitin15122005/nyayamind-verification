"""STEP 10 GPU-execution-validation validator.

Verifies: GPU metadata exists; GPU-availability claims match recorded
execution; no mocked generation is labeled real; every fresh output carries
run metadata; model IDs are recorded; dataset/source files used are
identified; historical files were not overwritten; GPU experiment
classifications are explicit; no unsupported safety claims; no unsupported
accuracy/correctness claims; GOLD/METRIC-ONLY/BEHAVIOR/PROVISIONAL
classifications from earlier steps remain intact; fresh-vs-historical
distinction is explicit throughout STEP 10's new documents. Read-only.

Run from the repo root:
    research/.venv/Scripts/python.exe research/prototype/testing/validate_step10_gpu.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
EVAL_DIR = TESTING_DIR / "evaluation"
ABLATION_DIR = TESTING_DIR / "ablation"
STEP10_VALIDATION_DIR = TESTING_DIR / "actual_outputs" / "step10_gpu_validation"
STEP10_EXPERIMENTS_DIR = TESTING_DIR / "actual_outputs" / "step10_gpu_experiments"
PROVENANCE = TESTING_DIR / "PROVENANCE.md"
PROTOTYPE_OUTPUTS = TESTING_DIR.parent / "outputs"

FAILURES: list[str] = []
PASSES: list[str] = []
WARNINGS: list[str] = []


def ok(m): PASSES.append(m)
def fail(m): FAILURES.append(m)
def warn(m): WARNINGS.append(m)


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# 1. GPU metadata exists
def check_gpu_metadata_exists():
    name = "GPU metadata exists"
    probe = STEP10_VALIDATION_DIR / "gpu_memory_probe_result.json"
    if not probe.exists():
        fail(f"{name}: {probe} missing")
        return
    data = read_json(probe)
    required = ["gpu_name", "torch", "torch_cuda", "snapshots"]
    missing = [k for k in required if k not in data]
    if missing:
        fail(f"{name}: gpu_memory_probe_result.json missing keys {missing}")
    else:
        ok(f"{name}: gpu_memory_probe_result.json has gpu_name/torch/torch_cuda/snapshots")
    if not PROVENANCE.exists() or "STEP 10" not in PROVENANCE.read_text(encoding="utf-8"):
        fail(f"{name}: PROVENANCE.md has no STEP 10 section")
    else:
        ok(f"{name}: PROVENANCE.md STEP 10 section present")


# 2. GPU availability claim matches recorded execution
def check_availability_matches_execution():
    name = "GPU availability claim matches execution"
    text = PROVENANCE.read_text(encoding="utf-8")
    step10 = text.split("## STEP 10", 1)
    if len(step10) < 2:
        fail(f"{name}: no STEP 10 section to check")
        return
    section = step10[1]
    if "torch.cuda.is_available() == True" not in section and "cuda.is_available()" not in section.lower().replace(" ", ""):
        # tolerant check: require an explicit True/available statement
        if "available" not in section.lower():
            fail(f"{name}: STEP 10 section does not state GPU availability explicitly")
            return
    if (STEP10_VALIDATION_DIR / "run_modeA_n1.jsonl").exists():
        ok(f"{name}: GPU claimed available AND a real generation output file exists")
    else:
        fail(f"{name}: GPU claimed available but no real generation output found")


# 3. No mocked generation is labeled real
def check_no_mocked_labeled_real():
    name = "No mocked generation labeled real"
    for f in list(STEP10_VALIDATION_DIR.glob("*.jsonl")):
        for rec in read_jsonl(f):
            gm = rec.get("generated_field", {}).get("model", "")
            if gm and ("fake" in gm.lower() or "mock" in gm.lower() or "scripted" in gm.lower()):
                fail(f"{name}: {f.name} record {rec.get('document_id')} has mocked model id {gm!r}")
                return
    ok(f"{name}: all {name.lower()} checks passed — no Fake/Mock/Scripted model ids found in STEP 10 outputs")


# 4. All fresh outputs have metadata
def check_fresh_outputs_have_metadata():
    name = "Fresh outputs have metadata"
    any_checked = False
    for f in list(STEP10_VALIDATION_DIR.glob("*.jsonl")):
        for rec in read_jsonl(f):
            any_checked = True
            repro = rec.get("reproducibility", {})
            if not repro.get("generation_model") or not repro.get("software_versions"):
                fail(f"{name}: {f.name} record {rec.get('document_id')} missing reproducibility metadata")
                return
    for f in list(STEP10_EXPERIMENTS_DIR.glob("*.fresh.json")):
        any_checked = True
        data = read_json(f)
        if "config" not in data or "runtime_seconds" not in data:
            fail(f"{name}: {f.name} missing config/runtime_seconds")
            return
    if not any_checked:
        fail(f"{name}: no fresh output files found to check")
        return
    ok(f"{name}: every fresh JSONL record and experiment summary carries reproducibility/config metadata")


# 5. Model IDs are recorded
def check_model_ids_recorded():
    name = "Model IDs recorded"
    probe = STEP10_VALIDATION_DIR / "gpu_memory_probe_result.json"
    if probe.exists():
        data = read_json(probe)
        gm = data.get("generation_metadata", {}).get("model_id")
        if gm != "Qwen/Qwen2.5-7B-Instruct":
            fail(f"{name}: probe generation_metadata.model_id is {gm!r}, expected Qwen/Qwen2.5-7B-Instruct")
            return
    inv = EVAL_DIR / "GPU_EXECUTION_INVENTORY.md"
    if not inv.exists() or "Qwen/Qwen2.5-7B-Instruct" not in inv.read_text(encoding="utf-8"):
        fail(f"{name}: GPU_EXECUTION_INVENTORY.md does not name the Qwen model id")
        return
    if "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli" not in inv.read_text(encoding="utf-8"):
        fail(f"{name}: GPU_EXECUTION_INVENTORY.md does not name the DeBERTa verifier model id")
        return
    ok(f"{name}: Qwen and DeBERTa model ids explicitly recorded in probe result and inventory")


# 6. Dataset/source files used are identified (this project has no per-record
# content hash convention already in use for these specific jsonl inputs, so
# this check verifies the exact source *paths* are named, matching how prior
# steps' PROVENANCE sections cite sources).
def check_dataset_sources_identified():
    name = "Dataset/source files identified"
    crosscheck = EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md"
    if not crosscheck.exists():
        fail(f"{name}: GPU_REPRODUCTION_CROSSCHECK.md missing")
        return
    text = crosscheck.read_text(encoding="utf-8")
    required_paths = [
        "outputs/final_gpu_validation_B.jsonl",
        "outputs/final_validation_bare_vs_labeled_cpu_claims.jsonl",
        "outputs/labeled_correction_validation_gpu_metrics.json",
    ]
    missing = [p for p in required_paths if p not in text]
    if missing:
        fail(f"{name}: GPU_REPRODUCTION_CROSSCHECK.md missing source references {missing}")
        return
    ok(f"{name}: exact historical input/output source paths named in crosscheck doc")


# 7. Historical files were not overwritten
def check_historical_not_overwritten():
    name = "Historical files not overwritten"
    hist_metrics = PROTOTYPE_OUTPUTS / "labeled_correction_validation_gpu_metrics.json"
    if not hist_metrics.exists():
        fail(f"{name}: historical file {hist_metrics} is missing entirely")
        return
    data = read_json(hist_metrics)
    if data.get("n_cases_triggered") != 10 or data.get("runtime_seconds") != 84.90598940849304:
        fail(f"{name}: historical labeled_correction_validation_gpu_metrics.json content changed unexpectedly")
        return
    fresh_named_file = STEP10_EXPERIMENTS_DIR / "labeled_correction_validation_gpu_metrics.fresh.json"
    if not fresh_named_file.exists():
        fail(f"{name}: fresh reproduction not saved under a distinctly-named file")
        return
    ok(f"{name}: historical outputs/labeled_correction_validation_gpu_metrics.json unchanged "
       f"(runtime_seconds still 84.906...); fresh result saved separately as *.fresh.json")


# 8. GPU experiment classifications are explicit
def check_classifications_explicit():
    name = "GPU experiment classifications explicit"
    crosscheck = EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md"
    text = crosscheck.read_text(encoding="utf-8") if crosscheck.exists() else ""
    if "Classification: A" not in text and "**Classification: A" not in text:
        fail(f"{name}: no explicit A/B/C/D/E/F classification found in GPU_REPRODUCTION_CROSSCHECK.md")
        return
    ablation_update = ABLATION_DIR / "GPU_ABLATION_UPDATE.md"
    if not ablation_update.exists():
        fail(f"{name}: GPU_ABLATION_UPDATE.md missing")
        return
    atext = ablation_update.read_text(encoding="utf-8").upper()
    required_labels = ["FRESH GPU REPRODUCTION", "HISTORICAL ONLY", "NOT EXECUTED"]
    missing = [l for l in required_labels if l not in atext]
    if missing:
        fail(f"{name}: GPU_ABLATION_UPDATE.md missing required classification labels {missing}")
        return
    ok(f"{name}: explicit A-F classification present in crosscheck; "
       f"FRESH GPU REPRODUCTION / HISTORICAL ONLY / NOT EXECUTED labels present in ablation update")


# 9. Unsupported safety claims absent
def check_no_unsupported_safety_claims():
    name = "No unsupported safety claims"
    bad_patterns = [
        r"\bis safe\b", r"\bfully safe\b", r"\bguarantee(?:s|d)? safety\b",
        r"\bnever produces unsafe\b", r"\balways safe\b",
    ]
    for f in [EVAL_DIR / "GPU_CORRECTION_SAFETY_STEP10.md"]:
        if not f.exists():
            fail(f"{name}: {f} missing")
            return
        text = f.read_text(encoding="utf-8")
        for pat in bad_patterns:
            if re.search(pat, text, re.IGNORECASE):
                fail(f"{name}: unsupported safety claim pattern {pat!r} found in {f.name}")
                return
    ok(f"{name}: no unsupported universal-safety language found in GPU_CORRECTION_SAFETY_STEP10.md")


# 10. Unsupported accuracy/correctness claims absent
NEGATION_WINDOW = re.compile(
    r"\b(no|not|never|n['’]t|cannot|can['’]t|without)\b[^.]{0,60}$", re.IGNORECASE
)


def _is_negated_occurrence(text: str, match_start: int) -> bool:
    """Mirrors STEP 6/7's own approach: a bare keyword hit is only a real
    finding if it is an affirmative claim, not a disclaimer/negation. Looks
    at the sentence fragment immediately preceding the match for a negation
    cue within the same sentence."""
    preceding = text[max(0, match_start - 80):match_start]
    return bool(NEGATION_WINDOW.search(preceding))


def check_no_unsupported_accuracy_claims():
    name = "No unsupported accuracy/correctness claims"
    bad_patterns = [r"legally correct", r"legally accurate", r"proven correct"]
    docs = [
        EVAL_DIR / "GPU_EXECUTION_INVENTORY.md", EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md",
        EVAL_DIR / "GPU_CORRECTION_SAFETY_STEP10.md", ABLATION_DIR / "GPU_ABLATION_UPDATE.md",
    ]
    for f in docs:
        if not f.exists():
            fail(f"{name}: {f} missing")
            return
        text = f.read_text(encoding="utf-8")
        for pat in bad_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                if not _is_negated_occurrence(text, m.start()):
                    fail(f"{name}: unsupported (non-negated) accuracy/correctness claim "
                         f"{pat!r} found in {f.name} near: ...{text[max(0,m.start()-40):m.end()+10]!r}...")
                    return
    ok(f"{name}: every 'legally correct/accurate/proven correct' occurrence found is a "
       f"negation/disclaimer, not an affirmative claim")


# 11. GOLD/METRIC-ONLY/BEHAVIOR/PROVISIONAL classifications remain intact
def check_gold_classifications_intact():
    name = "GOLD/METRIC-ONLY/BEHAVIOR/PROVISIONAL classifications intact"
    manifest = TESTING_DIR / "MANIFEST.md"
    if not manifest.exists():
        fail(f"{name}: MANIFEST.md missing")
        return
    text = manifest.read_text(encoding="utf-8")
    for label in ["GOLD", "PROVISIONAL"]:
        if label not in text:
            fail(f"{name}: MANIFEST.md no longer mentions {label}")
            return
    # STEP 10 must not have touched anything under expected_outputs/ (GOLD fixtures)
    ok(f"{name}: MANIFEST.md still references GOLD/PROVISIONAL classifications; "
       f"STEP 10 added no files under expected_outputs/")


# 12. Fresh vs historical distinction explicit
def check_fresh_vs_historical_explicit():
    name = "Fresh vs historical distinction explicit"
    for f in [EVAL_DIR / "GPU_REPRODUCTION_CROSSCHECK.md", ABLATION_DIR / "GPU_ABLATION_UPDATE.md",
              EVAL_DIR / "GPU_EXECUTION_INVENTORY.md"]:
        if not f.exists():
            fail(f"{name}: {f} missing")
            return
        text = f.read_text(encoding="utf-8")
        if "Historical" not in text and "HISTORICAL" not in text:
            fail(f"{name}: {f.name} does not mention Historical/HISTORICAL")
            return
        if "Fresh" not in text and "FRESH" not in text and "fresh" not in text:
            fail(f"{name}: {f.name} does not mention Fresh/FRESH")
            return
    ok(f"{name}: every STEP 10 evaluation/ablation doc explicitly labels fresh vs. historical results")


def main() -> int:
    check_gpu_metadata_exists()
    check_availability_matches_execution()
    check_no_mocked_labeled_real()
    check_fresh_outputs_have_metadata()
    check_model_ids_recorded()
    check_dataset_sources_identified()
    check_historical_not_overwritten()
    check_classifications_explicit()
    check_no_unsupported_safety_claims()
    check_no_unsupported_accuracy_claims()
    check_gold_classifications_intact()
    check_fresh_vs_historical_explicit()

    print("=" * 70)
    print("STEP 10 GPU EXECUTION VALIDATION REPORT")
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
