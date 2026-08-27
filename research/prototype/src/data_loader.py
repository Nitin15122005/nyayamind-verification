"""
Read-only loaders for:
  - research/data/evidence/canonical_statutes.jsonl (never written to)
  - research/data/evidence/evidence_audit.jsonl (never written to)
  - the NyayaRAG CaseText_Statutes JSON files already extracted to scratch
    space in an earlier session (paths come from config; not re-downloaded
    here)

NyayaRAG's own `sections` text is used ONLY to decide which real citation
KEYS a case mentions, for case selection (finding cases whose citations
overlap the small usable-evidence pool). The corresponding free-text VALUES
in NyayaRAG's `sections` dict are never read into anything that could reach
the verifier as evidence — evidence text always comes from
canonical_statutes.jsonl.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .claim_parser import normalize_act


@dataclass
class EvidenceRecord:
    dataset_citation_key: str
    act: str
    provision_type: str
    provision_number: str
    subsection: str | None
    canonical_text: str
    source_url: str
    audit_verdict: str
    act_norm: str


def _load_usable_records_by_key(
    canonical_path: Path, audit_path: Path, usable_verdicts: set[str],
) -> dict[str, EvidenceRecord]:
    """One (canonical, audit) file pair -> {dataset_citation_key: EvidenceRecord},
    filtered to usable_verdicts. Shared by load_usable_evidence for both the
    base v0 corpus and any optional v1+ supplement, so both are built by the
    exact same rules."""
    verdict_by_key: dict[str, str] = {}
    with audit_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            verdict_by_key[rec["dataset_citation_key"]] = rec["audit_verdict"]

    by_key: dict[str, EvidenceRecord] = {}
    with canonical_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            key = rec["dataset_citation_key"]
            verdict = verdict_by_key.get(key)
            if verdict not in usable_verdicts:
                continue
            act_norm = normalize_act(rec["act"])
            by_key[key] = EvidenceRecord(
                dataset_citation_key=key,
                act=rec["act"],
                provision_type=rec["provision_type"],
                provision_number=rec["provision_number"],
                subsection=rec.get("subsection"),
                canonical_text=rec["canonical_text"],
                source_url=rec["source_url"],
                audit_verdict=verdict,
                act_norm=act_norm,
            )
    return by_key


def load_usable_evidence(
    canonical_path: str | Path,
    audit_path: str | Path,
    usable_verdicts: set[str],
    extra_canonical_path: str | Path | None = None,
    extra_audit_path: str | Path | None = None,
) -> tuple[dict[tuple, EvidenceRecord], list[EvidenceRecord]]:
    """Load canonical_statutes.jsonl, join with evidence_audit.jsonl on
    dataset_citation_key, and keep only records whose audit_verdict is in
    `usable_verdicts` (by default VERIFIED_EXACT / VERIFIED_CONTENT only —
    SOURCE_ONLY / INVALID / UNRESOLVED records are excluded, per the audit's
    own recommendation, never silently promoted).

    `extra_canonical_path`/`extra_audit_path` (both optional, default None —
    omitting either reproduces the exact v0-only behaviour of every prior
    call site in this project): an additional (canonical, audit) file pair,
    loaded with the identical verdict-filtering rule, then merged on top of
    the base corpus by `dataset_citation_key` — a record in the extra pair
    REPLACES a same-keyed base record (used for v1's 3 corrections to known
    v0 INVALID/UNRESOLVED/wrong-historical_status records; see
    research/data/evidence/README.md), and every other extra-pair record is
    simply added. This is how research/data/evidence/canonical_statutes_v1.jsonl
    + evidence_audit_v1.jsonl (built by scripts/build_evidence_v1.py) become
    available WITHOUT ever modifying the base v0 files.

    Returns:
      (exact_index, all_usable_records)
      exact_index: dict keyed by (provision_type, provision_number,
                   subsection, act_norm) -> EvidenceRecord, for O(1) exact
                   lookups.
      all_usable_records: flat list, for fuzzy fallback matching.
    """
    canonical_path = Path(canonical_path)
    audit_path = Path(audit_path)

    by_key = _load_usable_records_by_key(canonical_path, audit_path, usable_verdicts)

    if extra_canonical_path is not None and extra_audit_path is not None:
        extra_by_key = _load_usable_records_by_key(
            Path(extra_canonical_path), Path(extra_audit_path), usable_verdicts
        )
        by_key.update(extra_by_key)  # extra records replace same-keyed base records

    exact_index: dict[tuple, EvidenceRecord] = {}
    all_usable: list[EvidenceRecord] = []
    for ev in by_key.values():
        index_key = (ev.provision_type, ev.provision_number, ev.subsection, ev.act_norm)
        exact_index[index_key] = ev
        all_usable.append(ev)

    return exact_index, all_usable


def load_usable_evidence_from_config(
    config: dict, repo_root: str | Path,
) -> tuple[dict[tuple, EvidenceRecord], list[EvidenceRecord]]:
    """Config-aware convenience wrapper: reads `paths.canonical_statutes`/
    `evidence_audit` (always) and, only when `use_evidence_v1: true` is set,
    also `paths.canonical_statutes_v1`/`evidence_audit_v1` (see
    config/prototype.yaml for what this changes and why it defaults off).
    Existing call sites that build the same arguments by hand and call
    `load_usable_evidence` directly are unaffected — this is an additive,
    opt-in entry point for new code, not a replacement."""
    repo_root = Path(repo_root)
    kwargs = {}
    if config.get("use_evidence_v1", False):
        kwargs["extra_canonical_path"] = repo_root / config["paths"]["canonical_statutes_v1"]
        kwargs["extra_audit_path"] = repo_root / config["paths"]["evidence_audit_v1"]
    return load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
        **kwargs,
    )


@dataclass
class Case:
    document_id: str
    case_text: str
    raw_citation_keys: list[str]   # NyayaRAG's own section KEYS (identity only)


def load_nyayarag_cases(paths: list[str | Path]) -> list[Case]:
    """Load case_text + citation keys from the already-extracted NyayaRAG
    CaseText_Statutes JSON files. Does NOT read the noisy `sections` text
    values into the returned Case objects — only the keys, used later for
    case-selection filtering (see select_cases_with_evidence_overlap)."""
    cases: list[Case] = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        for r in data:
            cases.append(
                Case(
                    document_id=r["document_id"],
                    case_text=r["summarized_text"],
                    raw_citation_keys=list((r.get("sections") or {}).keys()),
                )
            )
    return cases


def select_cases_with_evidence_overlap(
    cases: list[Case],
    exact_index: dict[tuple, EvidenceRecord],
    min_overlap: int = 1,
) -> list[Case]:
    """Filter to cases whose own citation KEYS (identity only, never their
    text) normalize to at least `min_overlap` entries in the usable
    evidence index. Cases with zero overlap can't be meaningfully verified
    against this 59-record evidence pool, so running the pipeline on them
    would trivially yield NO_EVIDENCE for every claim."""
    from .claim_parser import extract_citation  # reuse the same parser regex/logic

    selected: list[Case] = []
    for case in cases:
        overlap = 0
        for raw_key in case.raw_citation_keys:
            citation = extract_citation(raw_key)
            if citation is None:
                continue
            index_key = (
                citation.provision_type,
                citation.provision_number,
                citation.subsection,
                citation.act_norm,
            )
            if index_key in exact_index:
                overlap += 1
        if overlap >= min_overlap:
            selected.append(case)
    return selected
