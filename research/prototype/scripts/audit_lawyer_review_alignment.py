#!/usr/bin/env python3
"""Audit lawyer-review rows against frozen model outputs; never infer legal labels."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PROVISION_RE = re.compile(
    r"\b(section|sections|article|articles|rule|rules|regulation|regulations)\s+"
    r"([0-9]+(?:-[A-Za-z0-9]+)?[A-Za-z]?(?:\([^)]+\))*(?:\s*(?:,|and|&)\s*[0-9]+(?:-[A-Za-z0-9]+)?[A-Za-z]?(?:\([^)]+\))*)*)",
    re.IGNORECASE,
)


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def norm_reference(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_text(value))


def normalize_provision_number(value: Any) -> str:
    """Normalize typographic variants such as 295-A and 295A to one identifier."""
    return re.sub(r"[^a-z0-9()]", "", norm_text(value))


def provision_keys(value: Any) -> set[tuple[str, str]]:
    """Extract typed provision identifiers without guessing an Act or legal meaning."""
    result: set[tuple[str, str]] = set()
    for match in PROVISION_RE.finditer(norm_text(value)):
        kind = match.group(1).rstrip("s")
        for number in re.findall(r"[0-9]+(?:-[a-z0-9]+)?[a-z]?(?:\([^)]+\))*", match.group(2)):
            result.add((kind, normalize_provision_number(number)))
    return result


def extract_reference_act(value: Any) -> str:
    """Remove provision locators and subsection qualifiers from a lawyer reference."""
    text = PROVISION_RE.sub(" ", norm_text(value))
    text = re.sub(r"\b(?:sub[- ]?section|subsection|clause|paragraph)\s+[0-9]+[a-z]?(?:\([^)]+\))*", " ", text)
    text = re.sub(r"^\s*the\b", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(?:18|19|20)\d{2}\b", " ", text)
    normalized = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return "" if normalized in {"same act", "ibid"} else normalized


def act_name_match(reference_act: str, candidate_act: Any) -> str:
    """Return match/mismatch/unspecified; never infer an Act from a bare section number."""
    if not reference_act:
        return "unspecified"
    candidate = norm_text(candidate_act)
    if not candidate or candidate in {"same act", "ibid"}:
        return "unspecified"
    aliases = {
        "ipc": "indian penal code",
        "crpc": "code of criminal procedure",
        "pota": "prevention of terrorism act",
    }
    for alias, expansion in aliases.items():
        reference_act = re.sub(rf"\b{alias}\b", expansion, reference_act)
        candidate = re.sub(rf"\b{alias}\b", expansion, candidate)
    def core(value: str) -> str:
        value = re.sub(r"^the\s+", "", value.strip())
        value = re.sub(r"^part\s+[ivxlcdm]+\s+of\s+", "", value)
        return " ".join(
            token for token in value.split()
            if not re.fullmatch(r"(?:18|19|20)\d{2}", token)
        )
    reference_core = core(reference_act)
    candidate_core = core(candidate)
    if reference_core == candidate_core or reference_core in candidate_core or candidate_core in reference_core:
        return "match"
    return "mismatch"

def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc


def collect_model_claims(outputs_dir: Path) -> dict[str, list[dict[str, Any]]]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(outputs_dir.glob("*.jsonl")):
        if "annotation" in path.name.casefold():
            continue
        for record in read_jsonl(path):
            case_id = record.get("document_id") or record.get("case_reference")
            claims = record.get("claims")
            if not case_id or not isinstance(claims, list):
                continue
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                citation = claim.get("citation_extracted") or claim.get("extracted_citation") or {}
                by_case[str(case_id)].append({
                    "document_id": str(case_id), "source_file": path.name,
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text") or "",
                    "assertion_text": claim.get("assertion_text") or "",
                    "provision_type": citation.get("provision_type"),
                    "provision_number": citation.get("provision_number"),
                    "act_raw": citation.get("act_raw"), "act_norm": citation.get("act_norm"),
                    "evidence_id": claim.get("evidence_id"),
                    "evidence_match_method": claim.get("evidence_match_method"),
                    "verdict": claim.get("verdict"), "confidence": claim.get("confidence"),
                    "verifier_model": claim.get("verifier_model"),
                })
