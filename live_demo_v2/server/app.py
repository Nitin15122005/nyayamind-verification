#!/usr/bin/env python
"""
NyayaMind Live Demo v2 -- streaming JSON API over the REAL, unmodified
research/prototype/src/* pipeline.

Wraps src.pipeline's own public, composable stage functions
(generate_and_parse, apply_verification, apply_selective_correction /
apply_selective_correction_assertion_aware) behind a small stdlib-only HTTP
API (http.server, json -- no new Python dependency). Claim parsing, evidence
retrieval, NLI verification, safety-gate reasoning, and re-verification
always execute LIVE, for every request -- curated example or custom text.

Two execution paths for the one GPU-only stage (correction generation),
both honest about which they are:

  * Curated examples (EXAMPLE_SPECS below) replay an already-committed,
    real Qwen2.5-7B-Instruct correction from research/prototype/outputs/ --
    the exact "LIVE vs REPLAYED vs SCRIPTED" convention this project's own
    research/prototype/evaluation/live_demo/ already established. No text
    is invented anywhere in this file.

  * Custom user text has no pre-existing committed correction to replay,
    so LazyLiveCorrector below loads the REAL Qwen2.5-7B-Instruct model
    (4-bit bitsandbytes -- the exact config src/generator.py's own
    docstring says is already validated on this machine's GPU) and
    generates a genuine correction live, the first time one is actually
    triggered. Never loaded unconditionally at startup.

Every request streams newline-delimited JSON stage events over a chunked
HTTP response as each real pipeline stage completes -- the frontend's
pipeline animation reflects genuine computation, not a timer. This
process's own terminal additionally prints a plain, real-values-only
progress log ([NyayaMind] lines) as each stage actually runs; the website
itself never receives or shows this log, nor any file path, filename, or
internal flag name.

Run (from repo root):

    research/.venv/Scripts/python.exe live_demo_v2/server/app.py
"""

from __future__ import annotations

import copy
import json
import sys
import threading
import traceback

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


# ===========================================================================
# STREAMING / TERMINAL LOGGING
# ===========================================================================

# Force line-buffered stdout/stderr even when this process's output is
# redirected to a file/pipe rather than a real console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)


# ===========================================================================
# PATH SETUP
# ===========================================================================
#
# CURRENT DIRECTORY STRUCTURE:
#
#   repository-root/
#   ├── live_demo_v2/
#   │   ├── server/
#   │   │   └── app.py
#   │   └── web/
#   │
#   └── research/
#       └── prototype/
#
# Previously app.py lived one level deeper:
#
#   live_demo_v2/
#       stitch_nyayamind_legal_verification_platform/
#           server/
#
# Therefore the old path calculation walked one directory too far upward.
#
# ---------------------------------------------------------------------------

SERVER_ROOT = Path(__file__).resolve().parent

# live_demo_v2/
LIVE_DEMO_V2_DIR = SERVER_ROOT.parent

# repository root/
REPO_ROOT = LIVE_DEMO_V2_DIR.parent

# research/prototype/
PROTOTYPE_ROOT = REPO_ROOT / "research" / "prototype"

# Existing real evaluation helpers.
EVAL_LIVE_DEMO_DIR = PROTOTYPE_ROOT / "evaluation" / "live_demo"


# Add the actual repository locations to Python's import path.
for _p in (
    REPO_ROOT,
    PROTOTYPE_ROOT,
    EVAL_LIVE_DEMO_DIR,
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ===========================================================================
# REAL RESEARCH PIPELINE IMPORTS
# ===========================================================================

from common import pipeline_helpers as ph  # noqa: E402
from common import formatting as fmt  # noqa: E402

from src import pipeline  # noqa: E402
from src.data_loader import Case  # noqa: E402
from src.corrector import CorrectionMetadata, SelectiveCorrector  # noqa: E402
from src.generator import StatuteGroundingGenerator  # noqa: E402


# ===========================================================================
# REPLAY CORRECTOR
# ===========================================================================

class ReplayCorrector:
    """
    Supplies a real, already-committed whole-paragraph correction
    (LEGACY correction path) instead of invoking Qwen2.5-7B live.

    The REAL apply_selective_correction() logic still runs live:
      - scope gate
      - unauthorized-addition check
      - ordinal check
      - re-verification
      - sibling-regression check
    """

    def __init__(
        self,
        corrected_text: str,
        model_id: str,
        source_label: str,
    ):
        self._corrected_text = corrected_text
        self._model_id = model_id
        self.source_label = source_label

    def correct(
        self,
        case_text,
        original_field_text,
        flagged_claim_text,
        evidence_text,
    ):
        meta = CorrectionMetadata(
            model_id=self._model_id,
            max_new_tokens=220,
            do_sample=False,
            seed=42,
        )

        return self._corrected_text, meta


class ReplayAssertionCorrector:
    """
    Same idea as ReplayCorrector, for the ASSERTION-AWARE correction path.

    Supplies a real, already-committed corrected FRAGMENT rather than
    a whole paragraph.
    """

    def __init__(
        self,
        corrected_fragment: str,
        model_id: str,
        source_label: str,
    ):
        self._corrected_fragment = corrected_fragment
        self._model_id = model_id
        self.source_label = source_label

    def correct_assertion_span(
        self,
        case_text,
        target_span,
        evidence_text,
        assertion_span_system_prompt,
        max_new_tokens,
    ):
        meta = CorrectionMetadata(
            model_id=self._model_id,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            seed=42,
        )

        return self._corrected_fragment, meta


# ===========================================================================
# REAL LIVE CORRECTOR
# ===========================================================================

class LazyLiveCorrector:
    """
    Loads the REAL Qwen2.5-7B-Instruct generator + SelectiveCorrector.

    The model is loaded only when a real correction is genuinely triggered
    for custom input.

    It is never loaded at server startup and is reused after the first load.
    """

    def __init__(self, config: dict, log):
        self._config = config
        self._log = log
        self._generator = None
        self._corrector = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._corrector is not None:
                return

            self._log(
                "corrector -> loading live correction model "
                "(Qwen2.5-7B-Instruct, 4-bit) "
                "-- first use, this takes a little while..."
            )

            gen_cfg = self._config["generation"]

            generator = StatuteGroundingGenerator(
                model_id=gen_cfg["model_id"],
                quantization=gen_cfg["quantization"],
                device_map=gen_cfg["device_map"],
                max_new_tokens=gen_cfg["max_new_tokens"],
                do_sample=gen_cfg["do_sample"],
                temperature=gen_cfg["temperature"],
                top_p=gen_cfg["top_p"],
                system_prompt=gen_cfg["system_prompt"],
                user_prompt_template=gen_cfg["user_prompt_template"],
                seed=self._config["seed"],
            )

            generator.load()

            corr_cfg = self._config["correction"]

            self._corrector = SelectiveCorrector(
                generator=generator,
                max_new_tokens=corr_cfg["max_new_tokens"],
                do_sample=corr_cfg["do_sample"],
                system_prompt=corr_cfg["system_prompt"],
            )

            self._generator = generator

            self._log(
                "corrector -> live correction model loaded and ready."
            )

    def correct(self, *args, **kwargs):
        self._ensure_loaded()
        return self._corrector.correct(*args, **kwargs)

    def correct_assertion_span(self, *args, **kwargs):
        self._ensure_loaded()
        return self._corrector.correct_assertion_span(*args, **kwargs)


# ===========================================================================
# SAFETY CHECK PRESENTATION
# ===========================================================================

def _build_safety_checks(record: dict) -> list[dict]:
    corr = record["correction"]
    status = corr["status"]

    checks = []

    def row(name, result, detail):
        checks.append(
            {
                "name": name,
                "result": result,
                "detail": detail,
            }
        )

    if status.startswith("not_applicable") or status == "not_triggered":
        return checks

    row(
        "Evidence available for the flagged claim",
        "PASS",
        "The flagged claim resolved to a matched canonical statute record before "
        "any correction was attempted (NO_EVIDENCE claims never trigger correction).",
    )

    if status == "correction_span_invalid":
        row(
            "Target span valid",
            "BLOCK",
            "The flagged claim's own verifiable fragment could not be resolved "
            "unambiguously; no edit was attempted rather than guessing.",
        )
        return checks

    row(
        "Target span valid",
        "PASS",
        "The flagged claim's own verifiable fragment was resolved.",
    )

    if status == "correction_splice_unavailable":
        row(
            "Deterministic splice",
            "BLOCK",
            "The corrected fragment could not be spliced back into the paragraph "
            "unambiguously; the edit was withheld rather than guessed.",
        )
        return checks

    if status == "correction_structural_span_lost":
        row(
            "Structural span preserved",
            "BLOCK",
            "A structural element of the claim's citation did not survive the edit.",
        )
        return checks

    row(
        "Structural span preserved",
        "PASS",
        "No structural citation element was disturbed by the edit.",
    )

    scope_ok = status != "correction_scope_violation"

    row(
        "Unflagged claims preserved (scope)",
        "PASS" if scope_ok else "BLOCK",
        (
            "Every OTHER claim's required text still appears verbatim "
            "in the corrected paragraph."
            if scope_ok
            else
            "At least one unflagged claim's required text is missing from "
            "the corrected paragraph -- the edit touched content outside "
            "the flagged claim."
        ),
    )

    if status == "correction_scope_violation":
        return checks

    addition_ok = status != "correction_unauthorized_addition"

    row(
        "No unauthorized citation added",
        "PASS" if addition_ok else "BLOCK",
        (
            "No new citation identity appears in the corrected text."
            if addition_ok
            else
            "The corrected text introduces a citation identity that was "
            "not present anywhere in the original field."
        ),
    )

    if status == "correction_unauthorized_addition":
        return checks

    ordinal_ok = status != "correction_ordinal_ambiguous"

    row(
        "Ordinal citation-identity integrity",
        "PASS" if ordinal_ok else "BLOCK",
        (
            "Same-citation claims kept their relative order, so the corrected "
            "claim could be matched back unambiguously."
            if ordinal_ok
            else
            "The corrected text reordered same-citation claims; which sentence "
            "is the correction cannot be trusted."
        ),
    )

    if status == "correction_ordinal_ambiguous":
        return checks

    reverif = corr.get("reverification")

    if status == "correction_failed" or reverif is None:
        row(
            "Re-verification reaches ENTAILED",
            "BLOCK",
            "The corrected sentence could not be re-parsed/re-matched against "
            "its own evidence, or the corrector produced no usable replacement.",
        )
        return checks

    reverif_ok = reverif.get("verdict") == "ENTAILED"

    confidence = reverif.get("confidence")

    if isinstance(confidence, float):
        detail = (
            "Re-verifying the corrected sentence against its own evidence "
            f"returned {reverif.get('verdict')} "
            f"(confidence {confidence:.4f})."
        )
    else:
        detail = (
            "Re-verifying the corrected sentence against its own evidence "
            f"returned {reverif.get('verdict')}."
        )

    row(
        "Re-verification reaches ENTAILED",
        "PASS" if reverif_ok else "BLOCK",
        detail,
    )

    if not reverif_ok:
        return checks

    siblings = corr.get("sibling_regressions") or []

    if status == "correction_sibling_regression" or siblings:
        row(
            "No untouched sibling claim regresses",
            "BLOCK",
            f"{len(siblings)} untouched sibling claim(s) in the same sentence "
            "independently re-verify as CONTRADICTED against their own evidence.",
        )
        return checks

    row(
        "No untouched sibling claim regresses",
        "PASS",
        "Every other claim sharing this sentence still re-verifies consistently "
        "with its own evidence.",
    )

    row(
        "Final decision",
        "PASS",
        "All safety gates passed -- the correction ships.",
    )

    return checks


# ===========================================================================
# REAL-TIME SAFETY EVENT HELPERS
# ===========================================================================

_GATE_TO_STATUS = {
    "scope": "correction_scope_violation",
    "unauthorized_addition": "correction_unauthorized_addition",
    "ordinal": "correction_ordinal_ambiguous",
    "splice": "correction_splice_unavailable",
    "sentence_splice": "correction_splice_unavailable",
    "structural_span": "correction_structural_span_lost",
}


def _passed_structural_checks(assertion_aware: bool) -> list[dict]:
    checks = [
        {
            "name": "Evidence available for the flagged claim",
            "result": "PASS",
            "detail": (
                "The flagged claim resolved to a matched canonical statute "
                "record before any correction was attempted."
            ),
        },
    ]

    if assertion_aware:
        checks.append(
            {
                "name": "Target span valid",
                "result": "PASS",
                "detail": (
                    "The flagged claim's own verifiable fragment was resolved."
                ),
            }
        )

        checks.append(
            {
                "name": "Structural span preserved",
                "result": "PASS",
                "detail": (
                    "No structural citation element was disturbed by the edit."
                ),
            }
        )

    checks.append(
        {
            "name": "Unflagged claims preserved (scope)",
            "result": "PASS",
            "detail": (
                "Every OTHER claim's required text still appears verbatim "
                "in the corrected paragraph."
            ),
        }
    )

    checks.append(
        {
            "name": "No unauthorized citation added",
            "result": "PASS",
            "detail": (
                "No new citation identity appears in the corrected text."
            ),
        }
    )

    checks.append(
        {
            "name": "Ordinal citation-identity integrity",
            "result": "PASS",
            "detail": (
                "Same-citation claims kept their relative order."
            ),
        }
    )

    return checks


# ===========================================================================
# PUBLIC CLAIM HELPERS
# ===========================================================================

def _public_claims(claims: list[dict]) -> list[dict]:
    return [
        {
            k: v
            for k, v in c.items()
            if not k.startswith("_")
        }
        for c in claims
    ]


def _claim_groups(claims: list[dict]) -> list[dict]:
    order: list[str] = []
    by_sentence: dict[str, list[dict]] = {}

    for c in claims:
        key = c["claim_text"]

        if key not in by_sentence:
            by_sentence[key] = []
            order.append(key)

        by_sentence[key].append(c)

    return [
        {
            "sentence": sentence,
            "claims": _public_claims(by_sentence[sentence]),
        }
        for sentence in order
    ]


# ===========================================================================
# CURATED EXAMPLES
# ===========================================================================

_REAL_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with the unlawful assembly, which may be "
    "relevant if the prosecution can show that the accused acted as part of an "
    "unlawful assembly."
)

_CORRUPTED_FLAGGED_SENTENCE = (
    "The offense of murder under Section 302 of the Indian Penal Code, 1860 is "
    "punishable only by a fine and never by death or imprisonment."
)

_CORRECTED_FLAGGED_SENTENCE = (
    "Whoever commits murder under Section 302 of the Indian Penal Code, 1860 "
    "shall be punished with death, or imprisonment for life, and shall also be "
    "liable to fine."
)

_ALTERED_UNFLAGGED_SENTENCE = (
    "Additionally, Section 148 deals with theft, which may be relevant if the "
    "prosecution can show that the accused acted alone."
)

CORRUPTED_TEXT_1994_495 = (
    _CORRUPTED_FLAGGED_SENTENCE
    + " "
    + _REAL_UNFLAGGED_SENTENCE
)

GOOD_CORRECTED_TEXT_1994_495 = (
    _CORRECTED_FLAGGED_SENTENCE
    + " "
    + _REAL_UNFLAGGED_SENTENCE
)

BAD_CORRECTED_TEXT_1994_495 = (
    _CORRECTED_FLAGGED_SENTENCE
    + " "
    + _ALTERED_UNFLAGGED_SENTENCE
)


EXAMPLE_SPECS = [
    {
        "id": "entailed_34_2003_760",
        "category": "entailed",
        "title": "Supported Claim",
        "headline": (
            "A citation whose claimed content genuinely matches its statute text."
        ),
        "document_id": "2003_760",
        "mode": "B",
        "note": (
            "Section 34, Indian Penal Code, 1860 -- cited twice in this field; "
            "one of the two citations reaches ENTAILED."
        ),
        "kind": "mode_b",
        "source_rel": (
            "research/prototype/outputs/final_gpu_validation_B.jsonl"
        ),
    },
    {
        "id": "contradicted_148_1997_1306",
        "category": "contradicted",
        "title": "Contradicted Claim (Citation Mismatch)",
        "headline": (
            "A citation's claimed content does not match what its own statute actually says."
        ),
        "document_id": "1997_1306",
        "mode": "B",
        "note": (
            "Section 148, Indian Penal Code, 1860 -- the generated text calls "
            "it criminal trespass; the real Section 148 IPC defines rioting "
            "armed with a deadly weapon."
        ),
        "kind": "mode_b",
        "source_rel": (
            "research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl"
        ),
    },
    {
        "id": "mixed_2011_625",
        "category": "mixed",
        "title": "Insufficient Evidence & Out-of-Corpus Claims",
        "headline": (
            "One claim is genuinely inconclusive against real evidence; another "
            "cites a provision outside the evidence corpus."
        ),
        "document_id": "2011_625",
        "mode": "B",
        "note": (
            "Section 149, Indian Penal Code, 1860 reaches a genuine high-confidence "
            "neutral verdict. Other claims cite provisions outside the evidence corpus."
        ),
        "kind": "mode_b",
        "source_rel": (
            "research/prototype/outputs/final_gpu_validation_B.jsonl"
        ),
    },
    {
        "id": "correction_shipped_2003_760",
        "category": "correction_shipped",
        "title": "Correction Candidate -- Applied",
        "headline": (
            "The one naturally-occurring, fully-shipped correction in this project's "
            "evaluation history."
        ),
        "document_id": "2003_760",
        "mode": "C",
        "note": (
            "Section 302, Indian Penal Code, 1860: the generated text described "
            "the murder offense's definition rather than its prescribed punishment."
        ),
        "kind": "mode_c_replay",
        "source_rel": (
            "research/prototype/outputs/final_gpu_validation_B.jsonl"
        ),
        "correction_detail_rel": (
            "research/prototype/outputs/"
            "labeled_correction_validation_gpu_corrections_detail.jsonl"
        ),
    },
    {
        "id": "correction_scripted_ship_1994_495",
        "category": "correction_shipped",
        "title": "Selective Correction -- Safe Edit Ships",
        "headline": (
            "A correction that fixes the flagged claim and leaves every other "
            "sentence untouched."
        ),
        "document_id": "1994_495",
        "mode": "C",
        "note": (
            "A deliberately corrupted Section 302 IPC claim is corrected to "
            "state the real statutory penalty; the untouched Section 148 "
            "sentence survives byte-for-byte."
        ),
        "kind": "mode_c_scripted",
        "generated_text": CORRUPTED_TEXT_1994_495,
        "corrected_text": GOOD_CORRECTED_TEXT_1994_495,
    },
    {
        "id": "correction_scripted_block_1994_495",
        "category": "correction_blocked",
        "title": "Selective Correction -- Unsafe Edit Blocked",
        "headline": (
            "A correction that fixes the flagged claim but also alters an "
            "unrelated sentence -- rejected."
        ),
        "document_id": "1994_495",
        "mode": "C",
        "note": (
            "The same Section 302 fix as the SHIP example, but the corrector's "
            "output also silently changes the untouched Section 148 sentence. "
            "The scope gate catches this."
        ),
        "kind": "mode_c_scripted",
        "generated_text": CORRUPTED_TEXT_1994_495,
        "corrected_text": BAD_CORRECTED_TEXT_1994_495,
    },
    {
        "id": "assertion_aware_1955_32",
        "category": "assertion_aware_blocked",
        "title": "Assertion-Aware Correction -- Targeted Fix, Blocked by Safety",
        "headline": (
            "A surgical, single-fragment fix that re-verifies correctly on its "
            "own, but is withheld because an untouched sibling claim is independently wrong."
        ),
        "document_id": "1955_32",
        "mode": "C",
        "note": (
            "Sections 392 and 395, Indian Penal Code, 1860, share one bundled "
            "sentence. The flagged Section 395 claim is spliced to 'ten years', "
            "re-verifies ENTAILED -- but the untouched Section 392 clause "
            "independently regresses."
        ),
        "kind": "mode_c_assertion_aware",
        "source_rel": (
            "research/prototype/outputs/"
            "assertion_aware_correction_experiment_CURRENT.jsonl"
        ),
    },
]


EXAMPLE_BY_ID = {
    spec["id"]: spec
    for spec in EXAMPLE_SPECS
}

METADATA_FIELDS = (
    "id",
    "category",
    "title",
    "headline",
    "document_id",
    "mode",
    "note",
)


def _preview_text(spec: dict) -> str:
    if spec["kind"] == "mode_c_scripted":
        return spec["generated_text"]

    rec = ph.load_record(
        spec["source_rel"],
        spec["document_id"],
    )

    return rec.get("generated_field", {}).get("text", "")


def build_metadata_list() -> list[dict]:
    out = []

    for spec in EXAMPLE_SPECS:
        item = {
            k: spec.get(k)
            for k in METADATA_FIELDS
        }

        item["input_preview"] = _preview_text(spec)
        out.append(item)

    return out


# ===========================================================================
# EXAMPLE PREPARATION
# ===========================================================================

def _prepare_example(spec: dict, config: dict):
    kind = spec["kind"]

    if kind == "mode_b":
        rec = ph.load_record(
            spec["source_rel"],
            spec["document_id"],
        )

        case = Case(
            document_id=rec["document_id"],
            case_text=rec.get("case_text", ""),
            raw_citation_keys=[],
        )

        generator = ph.FakeGenerator(
            rec["generated_field"]["text"],
            rec["generated_field"]["model"],
        )

        return case, "B", generator, None, config

    if kind == "mode_c_replay":
        rec = ph.load_record(
            spec["source_rel"],
            spec["document_id"],
        )

        committed = None

        with (
            REPO_ROOT / spec["correction_detail_rel"]
        ).open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)

                if r.get("document_id") == spec["document_id"]:
                    committed = r
                    break

        if committed is None:
            raise KeyError(
                f"No committed correction record for {spec['document_id']}"
            )

        case = Case(
            document_id=rec["document_id"],
            case_text=rec.get("case_text", ""),
            raw_citation_keys=[],
        )

        generator = ph.FakeGenerator(
            rec["generated_field"]["text"],
            rec["generated_field"]["model"],
        )

        corrector = ReplayCorrector(
            committed["regenerated_text"],
            config["generation"]["model_id"],
            spec["correction_detail_rel"],
        )

        return case, "C", generator, corrector, config

    if kind == "mode_c_scripted":
        case = Case(
            document_id=spec["document_id"],
            case_text="",
            raw_citation_keys=[],
        )

        generator = ph.FakeGenerator(
            spec["generated_text"],
            config["generation"]["model_id"],
        )

        corrector = ReplayCorrector(
            spec["corrected_text"],
            config["generation"]["model_id"],
            "real fixture text (project test suite)",
        )

        return case, "C", generator, corrector, config

    if kind == "mode_c_assertion_aware":
        rec = ph.load_record(
            spec["source_rel"],
            spec["document_id"],
        )

        corrected_fragment = None

        with (
            REPO_ROOT / spec["source_rel"]
        ).open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)

                if r.get("document_id") == spec["document_id"]:
                    corrected_fragment = r["correction"]["corrected_fragment"]
                    break

        if corrected_fragment is None:
            raise KeyError(
                f"No committed assertion-aware fragment for "
                f"{spec['document_id']}"
            )

        case = Case(
            document_id=rec["document_id"],
            case_text=rec.get("case_text", ""),
            raw_citation_keys=[],
        )

        generator = ph.FakeGenerator(
            rec["generated_field"]["text"],
            rec["generated_field"]["model"],
        )

        corrector = ReplayAssertionCorrector(
            corrected_fragment,
            config["generation"]["model_id"],
            spec["source_rel"],
        )

        aa_config = copy.deepcopy(config)

        aa_config["correction"]["assertion_aware"] = True

        return (
            case,
            "C",
            generator,
            corrector,
            aa_config,
        )

    raise ValueError(
        f"Unknown example kind: {kind!r}"
    )


# ===========================================================================
# STREAMING PIPELINE
# ===========================================================================

def run_streaming(
    case,
    mode,
    generator,
    verifier,
    corrector,
    exact_index,
    all_usable,
    config,
    emit,
    log,
) -> dict:

    log("pipeline -> started")

    # -----------------------------------------------------------------------
    # CLAIM EXTRACTION
    # -----------------------------------------------------------------------

    emit("claims", "started")

    log("claim_parser -> extracting claims")

    baseline = pipeline.generate_and_parse(
        case,
        generator,
        exact_index,
        all_usable,
        config["evidence_matching"][
            "fuzzy_token_overlap_threshold"
        ],
    )

    baseline["_exact_index"] = exact_index
    baseline["_all_usable"] = all_usable
    baseline["_verifier"] = verifier

    log(
        f"claim_parser -> "
        f"{len(baseline['claims'])} claim(s) extracted"
    )

    emit(
        "claims",
        "complete",
        {
            "source_text": baseline["generated_field"]["text"],
            "claims": _public_claims(baseline["claims"]),
        },
    )

    # -----------------------------------------------------------------------
    # EVIDENCE
    # -----------------------------------------------------------------------

    emit("evidence", "started")

    log("evidence_retrieval -> retrieving evidence")

    with_evidence = sum(
        1
        for c in baseline["claims"]
        if c["evidence_text"] is not None
    )

    log(
        f"evidence_retrieval -> "
        f"{with_evidence}/{len(baseline['claims'])} claim(s) matched"
    )

    emit(
        "evidence",
        "complete",
        {
            "claims": _public_claims(baseline["claims"]),
        },
    )

    # -----------------------------------------------------------------------
    # VERIFICATION
    # -----------------------------------------------------------------------

    emit("verification", "started")

    if mode in ("B", "C"):
        narrow_primary = bool(
            (config.get("verification") or {}).get(
                "narrow_primary_hypothesis",
                False,
            )
        )

        span_primary = bool(
            (config.get("verification") or {}).get(
                "assertion_span_primary_hypothesis",
                False,
            )
        )

        log("verifier -> NLI verification started")

        pipeline.apply_verification(
            baseline,
            verifier,
            pipeline.resolve_premise_framing(config),
            narrow_primary,
            span_primary,
        )

        counts: dict[str, int] = {}

        for c in baseline["claims"]:
            counts[c["verdict"]] = (
                counts.get(c["verdict"], 0) + 1
            )

        log(
            f"verifier -> {len(baseline['claims'])} verdict(s) produced ("
            + ", ".join(
                f"{k}={v}"
                for k, v in counts.items()
            )
            + ")"
        )

    emit(
        "verification",
        "complete",
        {
            "claims": _public_claims(
                baseline["claims"]
            ),
        },
    )

    # -----------------------------------------------------------------------
    # DEFAULT RESULT STRUCTURE
    # -----------------------------------------------------------------------

    correction_summary = {
        "triggered_for_claim_id": None,
        "trigger_reason": None,
        "attempts": 0,
        "status": "not_applicable_mode_" + mode,
        "regenerated_text": None,
        "original_field_text": baseline[
            "generated_field"
        ]["text"],
        "reverification": None,
    }

    final_field = {
        "text": baseline["generated_field"]["text"],
        "source": "original",
    }

    safety_checks: list[dict] = []

    # -----------------------------------------------------------------------
    # CORRECTION
    # -----------------------------------------------------------------------

    if mode == "C":

        assertion_aware_correction = bool(
            (config.get("correction") or {}).get(
                "assertion_aware",
                False,
            )
        )

        def on_event(stage, status, data):
            data = data or {}

            # ---------------------------------------------------------------
            # CORRECTION
            # ---------------------------------------------------------------

            if stage == "correction":

                if status == "started":
                    log(
                        "corrector -> correction requested"
                    )

                    emit(
                        "correction",
                        "started",
                    )

                elif status == "completed":

                    log(
                        "corrector -> correction produced"
                    )

                    emit(
                        "correction",
                        "complete",
                        {
                            "triggered": True,
                            "regenerated_text": data.get(
                                "regenerated_text"
                            ),
                            "original_field_text": data.get(
                                "original_fragment",
                                baseline[
                                    "generated_field"
                                ]["text"],
                            ),
                            "corr_meta": data.get(
                                "corr_meta"
                            ),
                            "fragment_only": bool(
                                data.get(
                                    "fragment_only"
                                )
                            ),
                        },
                    )

            # ---------------------------------------------------------------
            # SAFETY
            # ---------------------------------------------------------------

            elif stage == "safety":

                if status == "started":

                    log(
                        "safety -> validating correction candidate"
                    )

                    emit(
                        "safety",
                        "started",
                    )

                elif status == "completed":

                    passed = bool(
                        data.get("passed")
                    )

                    gate = data.get("gate")

                    if passed:

                        checks = _passed_structural_checks(
                            assertion_aware_correction
                        )

                        log(
                            "safety -> structural checks passed"
                        )

                    else:

                        checks = _build_safety_checks(
                            {
                                "correction": {
                                    "status":
                                        _GATE_TO_STATUS[gate]
                                }
                            }
                        )

                        log(
                            f"safety -> blocked ({gate})"
                        )

                    for chk in checks:
                        log(
                            f"safety ->   "
                            f"{chk['name']}: "
                            f"{chk['result']}"
                        )

                    emit(
                        "safety",
                        "complete",
                        {
                            "triggered": True,
                            "passed": passed,
                            "checks": checks,
                        },
                    )

            # ---------------------------------------------------------------
            # RE-VERIFICATION
            # ---------------------------------------------------------------

            elif stage == "recheck":

                if status == "started":

                    log(
                        "verifier -> re-verification started"
                    )

                    emit(
                        "recheck",
                        "started",
                    )

                elif status == "completed":

                    verdict = data.get(
                        "verdict"
                    )

                    conf = data.get(
                        "confidence"
                    )

                    log(
                        f"verifier -> re-verification complete: "
                        f"{verdict}"
                        + (
                            f" ({conf:.4f})"
                            if isinstance(
                                conf,
                                float,
                            )
                            else ""
                        )
                    )

                    emit(
                        "recheck",
                        "complete",
                        {
                            "triggered": True,
                            **data,
                        },
                    )

                elif status == "skipped":

                    log(
                        "verifier -> re-verification not reached"
                    )

                    emit(
                        "recheck",
                        "skipped",
                        {
                            "triggered": True
                        },
                    )

        # -------------------------------------------------------------------
        # REAL PIPELINE CALL
        # -------------------------------------------------------------------

        if assertion_aware_correction:

            correction_summary = (
                pipeline.apply_selective_correction_assertion_aware(
                    baseline,
                    case,
                    corrector,
                    config,
                    on_event=on_event,
                )
            )

        else:

            correction_summary = (
                pipeline.apply_selective_correction(
                    baseline,
                    case,
                    corrector,
                    config,
                    on_event=on_event,
                )
            )

        # -------------------------------------------------------------------
        # FINAL FIELD
        # -------------------------------------------------------------------

        status = correction_summary["status"]

        if status == "corrected":

            final_field = {
                "text": correction_summary[
                    "regenerated_text"
                ],
                "source": "corrected",
            }

        elif status != "not_triggered":

            final_field = {
                "text": baseline[
                    "generated_field"
                ]["text"],
                "source": status,
            }

        # -------------------------------------------------------------------
        # CORRECTION NOT TRIGGERED
        # -------------------------------------------------------------------

        if status in (
            "not_triggered",
            "correction_span_invalid",
        ):

            if status == "not_triggered":

                log(
                    "safety -> no claim met the correction "
                    "trigger condition; nothing to correct"
                )

            else:

                log(
                    "safety -> flagged claim's target span "
                    "could not be resolved"
                )

            emit(
                "correction",
                "skipped",
                {
                    "triggered": False
                },
            )

            emit(
                "safety",
                "skipped",
                {
                    "triggered": False
                },
            )

            emit(
                "recheck",
                "skipped",
                {
                    "triggered": False
                },
            )

        else:

            log(
                f"pipeline -> correction decision: {status}"
            )

            safety_checks = _build_safety_checks(
                {
                    "correction":
                        correction_summary
                }
            )

    # -----------------------------------------------------------------------
    # NON-CORRECTION MODE
    # -----------------------------------------------------------------------

    else:

        emit(
            "correction",
            "skipped",
            {
                "triggered": False,
                "applicable": False,
            },
        )

        emit(
            "safety",
            "skipped",
            {
                "triggered": False,
                "applicable": False,
            },
        )

        emit(
            "recheck",
            "skipped",
            {
                "triggered": False,
                "applicable": False,
            },
        )

    # -----------------------------------------------------------------------
    # FINAL RECORD
    # -----------------------------------------------------------------------

    verifier_model_id = (
        getattr(
            verifier,
            "model_id",
            None,
        )
        if verifier is not None
        else None
    )

    record = {
        "document_id": baseline[
            "document_id"
        ],

        "case_text": baseline[
            "case_text"
        ],

        "generated_field": baseline[
            "generated_field"
        ],

        "claims": _public_claims(
            baseline["claims"]
        ),

        "evidence": pipeline._summarize_evidence(
            baseline["claims"],
            len(all_usable),
        ),

        "verification": pipeline._summarize_verification(
            baseline["claims"],
            mode,
            verifier_model_id,
            config["verification"][
                "confidence_threshold"
            ],
        ),

        "correction": {
            k: v
            for k, v in correction_summary.items()
            if not k.startswith("_")
        },

        "final_field": final_field,
    }

    log(
        "pipeline -> final result ready"
    )

    emit(
        "result",
        "complete",
        {
            "record": record,
            "claim_groups": _claim_groups(
                baseline["claims"]
            ),
            "safety_checks": safety_checks,
        },
    )

    return record


# ===========================================================================
# ARCHITECTURE INFORMATION
# ===========================================================================

ARCHITECTURE_STAGES = [
    {
        "id": "input",
        "label": "Input",
        "detail": (
            "The statutory-grounding text to verify."
        ),
    },
    {
        "id": "claims",
        "label": "Claim Extraction",
        "detail": (
            "Deterministic citation-bearing claim extraction."
        ),
    },
    {
        "id": "evidence",
        "label": "Evidence Retrieval",
        "detail": (
            "Canonical statute matching with conservative fallback."
        ),
    },
    {
        "id": "verification",
        "label": "NLI Verification",
        "detail": (
            "DeBERTa-v3 classifies claims against their own evidence."
        ),
    },
    {
        "id": "correction",
        "label": "Selective Correction",
        "detail": (
            "Only the flagged claim's content is rewritten."
        ),
    },
    {
        "id": "safety",
        "label": "Safety Gates",
        "detail": (
            "Candidate edits are validated before downstream trust."
        ),
    },
    {
        "id": "recheck",
        "label": "Re-verification",
        "detail": (
            "The corrected text is checked against its own evidence."
        ),
    },
    {
        "id": "result",
        "label": "Result",
        "detail": (
            "The correction ships only if the required checks pass."
        ),
    },
]


# ===========================================================================
# SERVER STATE
# ===========================================================================

_STATE: dict = {
    "metadata_list": None,
    "config": None,
    "pool_size": None,
    "exact_index": None,
    "all_usable": None,
    "verifier": None,
    "lazy_corrector": None,
}

_STATE_LOCK = threading.Lock()

# Single-examiner demo: serialize runs so two GPU corrections do not overlap.
_RUN_LOCK = threading.Lock()


# ===========================================================================
# JSON SERIALIZATION
# ===========================================================================

def _json_default(o):
    if isinstance(o, float):
        return o

    return str(o)


# ===========================================================================
# HTTP HANDLER
# ===========================================================================

class Handler(BaseHTTPRequestHandler):

    server_version = "NyayaMindDemoV2/1.0"

    protocol_version = "HTTP/1.1"

    # -----------------------------------------------------------------------
    # ACCESS LOG
    # -----------------------------------------------------------------------

    def log_message(self, fmt_, *args):
        # Explicit NyayaMind logs are used instead of the default noisy
        # BaseHTTPRequestHandler access log.
        pass

    # -----------------------------------------------------------------------
    # JSON RESPONSE
    # -----------------------------------------------------------------------

    def _send_json(self, payload, status=200):

        body = json.dumps(
            payload,
            default=_json_default,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

        self.end_headers()

        self.wfile.write(body)

    # -----------------------------------------------------------------------
    # OPTIONS
    # -----------------------------------------------------------------------

    def do_OPTIONS(self):

        self._send_json({})

    # -----------------------------------------------------------------------
    # GET
    # -----------------------------------------------------------------------

    def do_GET(self):

        path = urlparse(self.path).path

        with _STATE_LOCK:

            metadata_list = _STATE[
                "metadata_list"
            ]

            config = _STATE[
                "config"
            ]

            pool_size = _STATE[
                "pool_size"
            ]

        # ---------------------------------------------------------------
        # HEALTH
        # ---------------------------------------------------------------

        if path == "/api/health":

            status = (
                "ready"
                if metadata_list is not None
                else "warming_up"
            )

            print(
                f"[NyayaMind] GET /api/health -> {status}",
                flush=True,
            )

            self._send_json(
                {
                    "status": status
                }
            )

            return

        if metadata_list is None:

            self._send_json(
                {
                    "error": (
                        "The verification engine is still "
                        "starting up. Retry shortly."
                    )
                },
                status=503,
            )

            return

        # ---------------------------------------------------------------
        # CONFIG
        # ---------------------------------------------------------------

        if path == "/api/config":

            print(
                "[NyayaMind] GET /api/config",
                flush=True,
            )

            self._send_json(
                {
                    "premise_framing":
                        config["verification"][
                            "premise_framing"
                        ],

                    "usable_evidence_pool_size":
                        pool_size,

                    "confidence_threshold":
                        config["verification"][
                            "confidence_threshold"
                        ],

                    "disclaimer":
                        fmt.NLI_DISCLAIMER,
                }
            )

            return

        # ---------------------------------------------------------------
        # EXAMPLES
        # ---------------------------------------------------------------

        if path == "/api/examples":

            print(
                "[NyayaMind] GET /api/examples",
                flush=True,
            )

            self._send_json(
                metadata_list
            )

            return

        # ---------------------------------------------------------------
        # ARCHITECTURE
        # ---------------------------------------------------------------

        if path == "/api/architecture":

            print(
                "[NyayaMind] GET /api/architecture",
                flush=True,
            )

            self._send_json(
                {
                    "stages":
                        ARCHITECTURE_STAGES
                }
            )

            return

        # ---------------------------------------------------------------
        # 404
        # ---------------------------------------------------------------

        self._send_json(
            {
                "error": "not found"
            },
            status=404,
        )

    # -----------------------------------------------------------------------
    # POST
    # -----------------------------------------------------------------------

    def do_POST(self):

        path = urlparse(self.path).path

        if path != "/api/run":

            self._send_json(
                {
                    "error": "not found"
                },
                status=404,
            )

            return

        # ---------------------------------------------------------------
        # READ STATE
        # ---------------------------------------------------------------

        with _STATE_LOCK:

            ready = (
                _STATE["metadata_list"]
                is not None
            )

            config = _STATE[
                "config"
            ]

            exact_index = _STATE[
                "exact_index"
            ]

            all_usable = _STATE[
                "all_usable"
            ]

            verifier = _STATE[
                "verifier"
            ]

            lazy_corrector = _STATE[
                "lazy_corrector"
            ]

        if not ready:

            self._send_json(
                {
                    "error": (
                        "The verification engine is still "
                        "starting up. Retry shortly."
                    )
                },
                status=503,
            )

            return

        print(
            "[NyayaMind] POST /api/run",
            flush=True,
        )

        # ---------------------------------------------------------------
        # REQUEST BODY
        # ---------------------------------------------------------------

        length = int(
            self.headers.get(
                "Content-Length",
                0,
            )
            or 0
        )

        raw = (
            self.rfile.read(length)
            if length
            else b"{}"
        )

        try:

            body = (
                json.loads(
                    raw.decode("utf-8")
                )
                if raw
                else {}
            )

        except Exception:

            print(
                "[NyayaMind] POST /api/run "
                "-> 400 (invalid JSON body)",
                flush=True,
            )

            self._send_json(
                {
                    "error":
                        "invalid JSON body"
                },
                status=400,
            )

            return

        print(
            "[NyayaMind] request accepted",
            flush=True,
        )

        if body.get("mode") == "example":

            print(
                "[NyayaMind] request -> curated example "
                f"{body.get('id')!r}",
                flush=True,
            )

        elif body.get("mode") == "custom":

            print(
                "[NyayaMind] request -> custom input",
                flush=True,
            )

        # ---------------------------------------------------------------
        # STREAM RESPONSE
        # ---------------------------------------------------------------

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/x-ndjson; charset=utf-8",
        )

        self.send_header(
            "Cache-Control",
            "no-cache",
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Connection",
            "close",
        )

        self.end_headers()

        self.close_connection = True

        def emit(
            stage,
            status,
            data=None,
        ):

            event = {
                "stage": stage,
                "status": status,
                "data": data or {},
            }

            try:

                self.wfile.write(
                    (
                        json.dumps(
                            event,
                            default=_json_default,
                        )
                        + "\n"
                    ).encode("utf-8")
                )

                self.wfile.flush()

            except (
                BrokenPipeError,
                ConnectionAbortedError,
                OSError,
            ):
                pass

        def log(msg):

            print(
                f"[NyayaMind] {msg}",
                flush=True,
            )

        emit(
            "run",
            "started",
        )

        # ---------------------------------------------------------------
        # SERIALIZE ACTUAL RUN
        # ---------------------------------------------------------------

        with _RUN_LOCK:

            try:

                mode = body.get(
                    "mode"
                )

                # =======================================================
                # CURATED EXAMPLE
                # =======================================================

                if mode == "example":

                    ex_id = body.get(
                        "id"
                    )

                    spec = EXAMPLE_BY_ID.get(
                        ex_id
                    )

                    if spec is None:

                        log(
                            "Run failed: unknown "
                            f"example id {ex_id!r}"
                        )

                        emit(
                            "error",
                            "complete",
                            {
                                "message":
                                    f"Unknown example id {ex_id!r}"
                            },
                        )

                        return

                    emit(
                        "input",
                        "started",
                    )

                    emit(
                        "input",
                        "complete",
                        {},
                    )

                    (
                        case,
                        run_mode,
                        generator,
                        corrector,
                        cfg,
                    ) = _prepare_example(
                        spec,
                        config,
                    )

                    run_streaming(
                        case,
                        run_mode,
                        generator,
                        verifier,
                        corrector,
                        exact_index,
                        all_usable,
                        cfg,
                        emit,
                        log,
                    )

                # =======================================================
                # CUSTOM INPUT
                # =======================================================

                elif mode == "custom":

                    text = (
                        body.get("text")
                        or ""
                    ).strip()

                    if not text:

                        log(
                            "Run failed: no input text provided"
                        )

                        emit(
                            "error",
                            "complete",
                            {
                                "message":
                                    "No input text provided."
                            },
                        )

                        return

                    emit(
                        "input",
                        "started",
                    )

                    emit(
                        "input",
                        "complete",
                        {},
                    )

                    case = Case(
                        document_id="custom_input",
                        case_text="",
                        raw_citation_keys=[],
                    )

                    generator = ph.FakeGenerator(
                        text,
                        "user_input",
                    )

                    run_streaming(
                        case,
                        "C",
                        generator,
                        verifier,
                        lazy_corrector,
                        exact_index,
                        all_usable,
                        config,
                        emit,
                        log,
                    )

                # =======================================================
                # INVALID MODE
                # =======================================================

                else:

                    log(
                        "Run failed: invalid mode "
                        f"{mode!r}"
                    )

                    emit(
                        "error",
                        "complete",
                        {
                            "message":
                                "mode must be "
                                "'example' or 'custom'"
                        },
                    )

                    return

                emit(
                    "run",
                    "complete",
                )

                print(
                    "[NyayaMind] POST /api/run -> 200",
                    flush=True,
                )

            except Exception as exc:

                traceback.print_exc()

                log(
                    f"Run failed: {exc}"
                )

                emit(
                    "error",
                    "complete",
                    {
                        "message":
                            "This run could not be completed."
                    },
                )

                print(
                    "[NyayaMind] POST /api/run -> 500",
                    flush=True,
                )


# ===========================================================================
# STARTUP
# ===========================================================================

def _startup_log(msg):

    print(
        f"[NyayaMind] {msg}",
        flush=True,
    )


def main() -> int:

    _startup_log(
        "starting"
    )

    _startup_log(
        "loading production config"
    )

    config = ph.load_config()

    _startup_log(
        "loading evidence corpus"
    )

    exact_index, all_usable = (
        ph.load_evidence_pool(
            config
        )
    )

    _startup_log(
        f"evidence records available: "
        f"{len(all_usable)}"
    )

    _startup_log(
        "loading verifier "
        "(DeBERTa-v3, real model, "
        "this takes a few seconds)"
    )

    verifier = ph.load_verifier(
        config,
        announce=False,
    )

    _startup_log(
        "verifier ready"
    )

    # Qwen remains lazy-loaded.
    lazy_corrector = LazyLiveCorrector(
        config,
        _startup_log,
    )

    metadata_list = (
        build_metadata_list()
    )

    _startup_log(
        f"{len(metadata_list)} "
        "curated example(s) ready"
    )

    # ---------------------------------------------------------------
    # PUBLISH SERVER STATE
    # ---------------------------------------------------------------

    with _STATE_LOCK:

        _STATE["metadata_list"] = (
            metadata_list
        )

        _STATE["config"] = (
            config
        )

        _STATE["pool_size"] = (
            len(all_usable)
        )

        _STATE["exact_index"] = (
            exact_index
        )

        _STATE["all_usable"] = (
            all_usable
        )

        _STATE["verifier"] = (
            verifier
        )

        _STATE["lazy_corrector"] = (
            lazy_corrector
        )

    # ---------------------------------------------------------------
    # HTTP SERVER
    # ---------------------------------------------------------------

    port = 8421

    httpd = ThreadingHTTPServer(
        (
            "127.0.0.1",
            port,
        ),
        Handler,
    )

    _startup_log(
        "API ready"
    )

    _startup_log(
        f"listening on "
        f"http://127.0.0.1:{port} "
        "(Ctrl+C to stop)"
    )

    try:

        httpd.serve_forever()

    except KeyboardInterrupt:

        _startup_log(
            "shutdown requested"
        )

    finally:

        httpd.server_close()

        _startup_log(
            "server stopped"
        )

    return 0


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )