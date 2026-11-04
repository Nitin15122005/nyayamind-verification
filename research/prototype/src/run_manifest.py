"""Deterministic run manifest helpers for reproducible prototype outputs."""
from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from importlib import metadata


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cuda_available() -> bool | None:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return None


def _is_immutable_revision(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", value) is not None


def build_run_manifest(config: dict, evidence_records: list) -> dict:
    """Fingerprint effective config and exact evidence text used by a run.

    Model identifiers are recorded as configured identifiers, not claimed
    weight hashes. Exact weight reproducibility still requires immutable model
    revisions and separately archived artifact hashes.
    """
    evidence = []
    for item in evidence_records:
        evidence.append({
            "key": getattr(item, "dataset_citation_key", None),
            "act": getattr(item, "act", None),
            "provision_type": getattr(item, "provision_type", None),
            "provision_number": getattr(item, "provision_number", None),
            "subsection": getattr(item, "subsection", None),
            "canonical_text": getattr(item, "canonical_text", None),
            "source_url": getattr(item, "source_url", None),
            "audit_verdict": getattr(item, "audit_verdict", None),
        })
    evidence.sort(key=lambda row: (str(row["key"]), str(row["act"]), str(row["provision_number"])))

    packages = {}
    for package in ("torch", "transformers", "accelerate", "bitsandbytes", "peft", "numpy", "PyYAML"):
        try:
            packages[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            packages[package] = None

    return {
        "manifest_version": 1,
        "config_sha256": _sha256_json(config),
        "evidence_records": len(evidence),
        "evidence_sha256": _sha256_json(evidence),
        "generation_model_id": (config.get("generation") or {}).get("model_id"),
        "verification_model_id": (config.get("verification") or {}).get("model_id"),
        "generation_model_revision": (config.get("generation") or {}).get("revision"),
        "verification_model_revision": (config.get("verification") or {}).get("revision"),
        "models_pinned_to_immutable_revisions": (
            _is_immutable_revision((config.get("generation") or {}).get("revision"))
            and _is_immutable_revision((config.get("verification") or {}).get("revision"))
        ),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "package_versions": packages,
        "cuda_available": _cuda_available(),
        "model_revision_note": (
            "A revision is counted as pinned only when it is a full 40- or 64-character "
            "hex commit identifier. Model IDs alone are not weight fingerprints; archive artifact hashes "
            "for exact model-weight reproducibility."
        ),
    }
