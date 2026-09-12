#!/usr/bin/env python3
"""Shared constants, paths, and loaders for the Phase-3 mentor visualisation package.

READ-ONLY against the rest of the repository. Nothing in this package writes
anywhere except research/prototype/Output_phase_3_vedant/.

Every system/model name below is READ FROM a repository artifact, never invented:

  * modified (current) config  -> research/prototype/config/prototype.yaml
  * baseline (original) config -> research/prototype/archive/2026-08-27_presentation/
                                  final_comparison/comparison_config.json  ("ORIGINAL")
  * evidence pool sizes        -> computed live via src.data_loader
  * model ids                  -> config/prototype.yaml (generation/verification/correction)
"""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import yaml

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PKG_DIR = Path(__file__).resolve().parent.parent          # Output_phase_3_vedant/
PROTO_DIR = PKG_DIR.parent                                 # research/prototype/
RESEARCH_DIR = PROTO_DIR.parent                            # research/
REPO_ROOT = RESEARCH_DIR.parent                            # repo root

CONFIG_YAML = PROTO_DIR / "config" / "prototype.yaml"
OUTPUTS = PROTO_DIR / "outputs"
EVAL = PROTO_DIR / "evaluation"
EVAL_ACTUAL = EVAL / "actual_outputs"
EVAL_METRICS = EVAL / "metrics"
EVAL_ABLATION = EVAL / "ablation"
EVAL_REPORTS = EVAL / "reports"
ARCHIVE_COMPARISON = (
    PROTO_DIR / "archive" / "2026-08-27_presentation" / "final_comparison"
)

OUT_METRICS = PKG_DIR / "metrics"
OUT_FIGURES = PKG_DIR / "figures"
OUT_DIAGRAMS = PKG_DIR / "diagrams"
OUT_TABLES = PKG_DIR / "tables"
OUT_PPT = PKG_DIR / "ppt_assets"
OUT_PPT_FIG = OUT_PPT / "figures"
OUT_PPT_DIA = OUT_PPT / "diagrams"
OUT_VALIDATION = PKG_DIR / "validation"
BUILD_STATE = PKG_DIR / "scripts" / "_manifest_parts"


def rel(p: Path | str) -> str:
    """Repo-root-relative POSIX path, for provenance columns."""
    return Path(p).resolve().relative_to(REPO_ROOT).as_posix()


# --------------------------------------------------------------------------
# Config loading (the authoritative definitions of the two systems)
# --------------------------------------------------------------------------
def load_current_config() -> dict:
    with CONFIG_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_baseline_config_record() -> dict:
    with (ARCHIVE_COMPARISON / "comparison_config.json").open(encoding="utf-8") as f:
        return json.load(f)


CFG = load_current_config()
CMP = load_baseline_config_record()
ORIGINAL = CMP["ORIGINAL"]
CURRENT = CMP["CURRENT"]

GENERATION_MODEL = CFG["generation"]["model_id"]              # Qwen/Qwen2.5-7B-Instruct
VERIFICATION_MODEL = CFG["verification"]["model_id"]          # MoritzLaurer/DeBERTa-v3-...
CORRECTION_MODEL = CFG["correction"]["model_id"]              # reuses the generator
QUANT = CFG["generation"]["quantization"]["bnb_4bit_quant_type"]  # nf4
CONF_THRESHOLD = CFG["verification"]["confidence_threshold"]  # 0.70

# Out-of-scope, different-task baseline (research/baseline/BASELINE.md)
RHETORIC_BASE_MODEL = "meta-llama/Llama-2-7b-chat-hf"
RHETORIC_ADAPTER = "L-NLProc/LegalSeg_RhetoricLLaMA"

# --------------------------------------------------------------------------
# Canonical display names.  NEVER "old/new", "before/after", "original/current".
# --------------------------------------------------------------------------
BASELINE_NAME = "NyayaMind v0 (pre-2026-08-27 baseline)"
MODIFIED_NAME = "NyayaMind (2026-08-27 production)"

BASELINE_LABEL = "Baseline: NyayaMind v0\nbare premise · evidence v0 (59 rec)"
MODIFIED_LABEL = "Modified: NyayaMind production\nlabeled premise · evidence v0+v1 (136 rec)"

BASELINE_LABEL_1L = "Baseline: NyayaMind v0 (bare premise · evidence v0, 59 rec)"
MODIFIED_LABEL_1L = "Modified: NyayaMind production (labeled premise · evidence v0+v1, 136 rec)"

BASELINE_SHORT = "Baseline: NyayaMind v0\n(bare premise)"
MODIFIED_SHORT = "Modified: NyayaMind\n(labeled premise)"

SHARED_STACK = (
    f"Generator {GENERATION_MODEL} (4-bit {QUANT}) + Verifier {VERIFICATION_MODEL} "
    f"— identical in both systems; only configuration differs"
)

# --------------------------------------------------------------------------
# Colours (consistent across every figure and diagram in this package)
# --------------------------------------------------------------------------
C_BASELINE = "#8C8C8C"     # grey  — baseline / original configuration
C_MODIFIED = "#2A6099"     # blue  — modified NyayaMind production configuration
C_GOLD = "#55A868"         # green — GOLD (labelled ground truth) datasets
C_NATURAL = "#4C72B0"      # blue  — natural, METRIC-ONLY datasets
C_HISTORICAL = "#BFBFBF"   # light grey — historical (not freshly re-executed)
C_FRESH = "#2A6099"
C_SHIPPED = "#3F8F4F"
C_REJECT = "#C44E52"
C_SCOPE = "#DD8452"
C_UNSAFE = "#B22222"
C_ACCENT = "#7A3E9D"
GRADE_COLORS = {"A": "#2A6F2A", "B": "#7FB37F", "C": "#D9A441",
                "D": "#B0B0B0", "E": "#808080"}

VERDICT_COLORS = {
    "ENTAILED": "#3F8F4F",
    "CONTRADICTED": "#C44E52",
    "NOT_ENOUGH_INFORMATION": "#DDA63A",
    "NO_EVIDENCE": "#9E9E9E",
}

# --------------------------------------------------------------------------
# Small JSON/CSV helpers
# --------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def read_csv(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pct(x: float, nd: int = 1) -> str:
    return f"{100.0 * float(x):.{nd}f}%"
