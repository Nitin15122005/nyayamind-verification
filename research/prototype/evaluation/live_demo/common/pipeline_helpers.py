"""
Path setup + shared loaders for every live_demo script.

Importing this module (from any demo script, at any depth under live_demo/)
makes `research/prototype/src/*` importable and exposes the loaders every
demo needs: production config, the real 136-record evidence pool, the real
DeBERTa verifier (auto CPU/GPU), and lookup helpers over the real, already-
committed experiment output files under research/prototype/outputs/.

Nothing here modifies src/, tests/, config/, research/data/, or outputs/ --
every function is read-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# This file always lives at research/prototype/evaluation/live_demo/common/
# pipeline_helpers.py, five directories below the repo root, regardless of
# which demo script (at any depth under live_demo/) imports it -- so path
# computation here is depth-independent for callers.
_THIS_FILE = Path(__file__).resolve()
LIVE_DEMO_ROOT = _THIS_FILE.parent.parent
EVALUATION_ROOT = LIVE_DEMO_ROOT.parent
PROTOTYPE_ROOT = EVALUATION_ROOT.parent
RESEARCH_ROOT = PROTOTYPE_ROOT.parent
REPO_ROOT = RESEARCH_ROOT.parent

for _p in (REPO_ROOT, PROTOTYPE_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Windows consoles / redirected output default to the system codepage (often
# cp1252), which cannot encode the em-dashes and smart quotes real generated
# legal text and this module's own output contain -- force UTF-8 so every
# demo's output is readable regardless of host locale, whether run
# interactively or redirected to a log file.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml  # noqa: E402

from src.data_loader import load_usable_evidence_from_config  # noqa: E402
from src.verifier import NLIVerifier  # noqa: E402

CONFIG_PATH = PROTOTYPE_ROOT / "config" / "prototype.yaml"
OUTPUTS_DIR = PROTOTYPE_ROOT / "outputs"


def load_config() -> dict:
    """The real, unmodified production config (research/prototype/config/prototype.yaml)."""
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_evidence_pool(config: dict):
    """(exact_index, all_usable) -- the real production evidence pool (136
    records: v0's 59 usable + v1's 77 additive, per config['use_evidence_v1']).
    No model involved; pure data load."""
    return load_usable_evidence_from_config(config, REPO_ROOT)


def load_verifier(config: dict, announce: bool = True) -> NLIVerifier:
    """The real DeBERTa-v3-base-mnli-fever-anli verifier, loaded.

    Device is auto-detected exactly the way
    tests/test_correction_path_real_integration.py's own `real_verifier`
    fixture does it (`"cuda" if torch.cuda.is_available() else "cpu"`) --
    never hardcoded to either. This ~184M-parameter model runs fine on CPU
    in seconds (see REPRODUCIBILITY.md's reproduction-cost table); only
    *generation* and *correction* (the 7B Qwen calls) genuinely require a
    GPU. This is the one behavioral difference from the pipeline's own
    NLIVerifier default (device="cuda", refuses to silently fall back) --
    that default exists to stop a co-resident 7B generator from being
    starved of VRAM by an accidental CPU fallback, a constraint that does
    not apply to a standalone verifier-only demo.
    """
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if announce:
        print(f"Loading real DeBERTa-v3-base-mnli-fever-anli verifier (device={device})"
              " ... this takes a few seconds.")
    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=device,
    )
    verifier.load()
    if announce:
        print(f"  Verifier loaded ({device}).")
    return verifier


def load_record(rel_path: str, document_id: str) -> dict:
    """One record from a committed research/prototype/outputs/*.jsonl file,
    by document_id. Raises KeyError if not found -- callers should pass a
    (rel_path, document_id) pair already known to exist, never guess."""
    with (REPO_ROOT / rel_path).open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("document_id") == document_id:
                return rec
    raise KeyError(f"{document_id} not found in {rel_path}")


def find_claim_by_provision(claim_records: list[dict], provision_number: str, matched: bool | None = None):
    """First claim record whose citation_extracted.provision_number matches
    (order-of-extraction, never a hardcoded claim_id index -- robust to
    extraction detail changes). `matched`, if given, additionally filters on
    whether evidence_text is/isn't None. Raises StopIteration if none match
    -- callers should only pass provision numbers already confirmed present
    in the target document's real generated text."""
    for c in claim_records:
        citation = c.get("citation_extracted")
        if not citation or citation.get("provision_number") != provision_number:
            continue
        if matched is not None and (c.get("evidence_text") is not None) != matched:
            continue
        return c
    raise StopIteration(f"no claim with provision_number={provision_number!r} (matched={matched}) found")


class FakeGenerator:
    """Supplies a pre-existing, already-committed real generated field
    directly -- never invokes the real 7B Qwen model. Identical pattern to
    tests/test_correction_path_real_integration.py's own FakeGenerator
    (reused here, not reinvented), used throughout live_demo/ so that
    src.pipeline.run_case() -- the REAL, unmodified orchestration function
    -- can be exercised end-to-end on a GPU-free machine, substituting only
    the one stage (text generation) that genuinely requires a GPU.
    """

    def __init__(self, text: str, model_id: str):
        self._text = text
        self._model_id = model_id

    def generate(self, case_text: str):
        from src.generator import GenerationMetadata

        meta = GenerationMetadata(
            model_id=self._model_id, quantization={"load_in_4bit": True},
            max_new_tokens=200, do_sample=False, temperature=1.0, top_p=1.0, seed=42,
        )
        return self._text, meta


class ScriptedCorrector:
    """Returns pre-authored 'corrected' text -- never invokes the real 7B
    Qwen model. Identical pattern to
    tests/test_correction_path_real_integration.py's own ScriptedCorrector.
    Only src.pipeline.apply_selective_correction()'s REAL logic (scope
    check, real re-verification via the real verifier, status decision) is
    demonstrated -- never the LLM's correction-writing quality, which is
    not reproducible without a GPU."""

    def __init__(self, corrected_text: str, model_id: str):
        self._corrected_text = corrected_text
        self._model_id = model_id
        self.calls: list[tuple[str, str | None]] = []

    def correct(self, case_text, original_field_text, flagged_claim_text, evidence_text):
        from src.corrector import CorrectionMetadata

        self.calls.append((flagged_claim_text, evidence_text))
        meta = CorrectionMetadata(
            model_id=self._model_id, max_new_tokens=220, do_sample=False, seed=42,
        )
        return self._corrected_text, meta
