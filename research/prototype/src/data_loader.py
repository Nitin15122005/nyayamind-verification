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
    """Load one canonical/audit pair with fail-closed structural checks.

    Duplicate keys, malformed JSONL, missing/orphan audit rows, unknown
    verdicts and incomplete evidence records are rejected. Silently
    overwriting a duplicate or silently dropping a record would make the
    effective evidence corpus depend on file order.
    """
    allowed_verdicts = {
        "VERIFIED_EXACT", "VERIFIED_CONTENT", "SOURCE_ONLY", "INVALID", "UNRESOLVED",
    }

    def read_jsonl(path: Path, kind: str) -> list[dict]:
        if not path.is_file():
            raise FileNotFoundError(f"{kind} file does not exist: {path}")
        rows: list[dict] = []
        with path.open(encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, 1):
                if not raw.strip():
                    raise ValueError(f"{kind} contains a blank line: {path}:{line_no}")
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {kind}: {path}:{line_no}: {exc}"
                    ) from exc
                if not isinstance(record, dict):
                    raise ValueError(
                        f"{kind} record must be a JSON object: {path}:{line_no}"
                    )
                rows.append(record)
        return rows

    audit_rows = read_jsonl(audit_path, "evidence audit")
    canonical_rows = read_jsonl(canonical_path, "canonical evidence")

    verdict_by_key: dict[str, str] = {}
    for line_no, record in enumerate(audit_rows, 1):
        key = record.get("dataset_citation_key")
        verdict = record.get("audit_verdict")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Missing audit citation key: {audit_path}:{line_no}")
        if key in verdict_by_key:
            raise ValueError(f"Duplicate audit citation key {key!r}: {audit_path}:{line_no}")
        if verdict not in allowed_verdicts:
            raise ValueError(
                f"Unknown audit verdict {verdict!r} for {key!r}: {audit_path}:{line_no}"
            )
        verdict_by_key[key] = verdict

    by_key: dict[str, EvidenceRecord] = {}
    for line_no, record in enumerate(canonical_rows, 1):
        key = record.get("dataset_citation_key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Missing canonical citation key: {canonical_path}:{line_no}")
        if key in by_key:
            raise ValueError(f"Duplicate canonical citation key {key!r}: {canonical_path}:{line_no}")
        verdict = verdict_by_key.get(key)
        if verdict is None:
            raise ValueError(f"Canonical record has no audit row for {key!r}")
        required = ("act", "provision_type", "provision_number", "canonical_text", "source_url")
        missing = [field for field in required if not isinstance(record.get(field), str)
                   or not record[field].strip()]
        if missing:
            raise ValueError(
                f"Canonical record {key!r} has missing/empty fields: {', '.join(missing)}"
            )
        act_norm = normalize_act(record["act"])
        if not act_norm:
            raise ValueError(f"Canonical record {key!r} has an unnormalizable Act name")
        by_key[key] = EvidenceRecord(
            dataset_citation_key=key,
            act=record["act"],
            provision_type=record["provision_type"],
            provision_number=str(record["provision_number"]),
            subsection=record.get("subsection"),
            canonical_text=record["canonical_text"],
            source_url=record["source_url"],
            audit_verdict=verdict,
            act_norm=act_norm,
        )

    orphan_audit_keys = set(verdict_by_key) - set(by_key)
    if orphan_audit_keys:
        sample = sorted(orphan_audit_keys)[:5]
        raise ValueError(
            f"Audit contains {len(orphan_audit_keys)} orphan record(s); examples: {sample}"
        )

    return {
        key: record for key, record in by_key.items()
        if record.audit_verdict in usable_verdicts
    }

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
    approved_verdicts = {"VERIFIED_EXACT", "VERIFIED_CONTENT"}
    requested_verdicts = set(usable_verdicts)
    if not requested_verdicts or not requested_verdicts.issubset(approved_verdicts):
        raise ValueError(
            "usable_verdicts may contain only VERIFIED_EXACT and "
            f"VERIFIED_CONTENT; received {sorted(requested_verdicts)!r}"
        )
    if (extra_canonical_path is None) != (extra_audit_path is None):
        raise ValueError(
            "extra_canonical_path and extra_audit_path must be supplied together; "
            "a partial evidence-pool supplement is not permitted."
        )

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
        previous = exact_index.get(index_key)
        if previous is not None:
            raise ValueError(
                "Evidence index collision for "
                f"{index_key!r}: {previous.dataset_citation_key!r} and "
                f"{ev.dataset_citation_key!r}. Refusing order-dependent overwrite."
            )
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
