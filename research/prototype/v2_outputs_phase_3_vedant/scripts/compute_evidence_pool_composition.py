#!/usr/bin/env python3
"""
V2 FRESH — deterministic composition of the ORIGINAL (v0) vs LATEST (v1-merged)
evidence pool.

WHAT THIS MEASURES
------------------
The `use_evidence_v1` lever: ORIGINAL NyayaMind loaded the v0 corpus only;
LATEST merges the v1 supplement on top under the identical verdict-filter
rule (`src/data_loader.load_usable_evidence`). This script recomputes the
pool composition from the READ-ONLY evidence files using the production
loader itself, so no pool size is hand-typed.

It is a DETERMINISTIC_SYNTHETIC-grade structural measurement (a count over
files), not a model result. It involves no inference, no GPU and no
randomness. It is NOT a retrieval-accuracy measurement — pool size is an
input property, not an outcome.

WHY THIS EXISTS IN V2
---------------------
`config/prototype.yaml` describes the v0->v1 change as "78 new
VERIFIED_EXACT + the 59 v0 records, with 3 v0 corrections applied", which
does not reconcile to the observed total of 136 (59 + 78 = 137). This
script recovers the exact decomposition and records the discrepancy rather
than repeating the config's arithmetic.

OUTPUT
------
metrics/evidence_pool_composition_v2.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
_PROTOTYPE_ROOT = _V2_ROOT.parent
_REPO_ROOT = _PROTOTYPE_ROOT.parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml  # noqa: E402

from src.data_loader import load_usable_evidence  # noqa: E402

CONFIG_PATH = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
METRICS_DIR = _V2_ROOT / "metrics"


def read_verdicts(canonical: Path, audit: Path) -> dict[str, str]:
    verdict_by_key: dict[str, str] = {}
    with audit.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                verdict_by_key[rec["dataset_citation_key"]] = rec["audit_verdict"]
    out: dict[str, str] = {}
    with canonical.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                key = rec["dataset_citation_key"]
                out[key] = verdict_by_key.get(key, "MISSING_FROM_AUDIT")
    return out


def main() -> int:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    usable = set(cfg["usable_evidence_verdicts"])

    def rel(p: str) -> Path:
        return _REPO_ROOT / p

    c0, a0 = rel(paths["canonical_statutes"]), rel(paths["evidence_audit"])
    c1, a1 = rel(paths["canonical_statutes_v1"]), rel(paths["evidence_audit_v1"])

    # Production loader — the same code path the pipeline uses.
    by0, list0 = load_usable_evidence(c0, a0, usable)
    by1, list1 = load_usable_evidence(c0, a0, usable, c1, a1)

    v0_verdicts = read_verdicts(c0, a0)
    v1_verdicts = read_verdicts(c1, a1)

    v0_usable_keys = {k for k, v in v0_verdicts.items() if v in usable}
    v1_usable_keys = {k for k, v in v1_verdicts.items() if v in usable}

    overlap = sorted(set(v1_verdicts) & set(v0_verdicts))
    corrections = [
        {
            "dataset_citation_key": k,
            "v0_verdict": v0_verdicts[k],
            "v1_verdict": v1_verdicts[k],
            "was_usable_in_v0": k in v0_usable_keys,
            "usable_in_v1": k in v1_usable_keys,
            "effect": (
                "PROMOTED_TO_USABLE" if (k not in v0_usable_keys and k in v1_usable_keys)
                else "VERDICT_UPGRADE_ONLY" if (k in v0_usable_keys and k in v1_usable_keys)
                else "OTHER"
            ),
        }
        for k in overlap
    ]

    new_keys = set(v1_verdicts) - set(v0_verdicts)
    new_usable = new_keys & v1_usable_keys
    promoted = [c for c in corrections if c["effect"] == "PROMOTED_TO_USABLE"]

    reconciliation = {
        "v0_usable": len(list0),
        "plus_new_usable_keys": len(new_usable),
        "plus_promoted_from_unusable": len(promoted),
        "equals_latest_usable": len(list0) + len(new_usable) + len(promoted),
        "observed_latest_usable": len(list1),
        "reconciles": (len(list0) + len(new_usable) + len(promoted)) == len(list1),
    }

    out = {
        "artifact_id": "EVIDENCE-POOL-V2",
        "measurement": "evidence pool composition, ORIGINAL (v0-only) vs LATEST (v0+v1 merged)",
        "lever": "use_evidence_v1 (false -> true)",
        "evidence_grade": "DETERMINISTIC_SYNTHETIC",
        "grade_note": (
            "A deterministic structural count over read-only evidence files using the "
            "production loader. This is an INPUT property of the system, not a retrieval "
            "outcome — it is not an accuracy, precision, recall or coverage measurement."
        ),
        "deterministic": True,
        "model_used": None,
        "usable_evidence_verdicts": sorted(usable),
        "original_v0": {
            "files": [str(c0.relative_to(_REPO_ROOT)), str(a0.relative_to(_REPO_ROOT))],
            "records_in_file": len(v0_verdicts),
            "usable_records": len(list0),
            "verdict_breakdown": dict(Counter(r.audit_verdict for r in list0)),
            "distinct_acts": len({r.act_norm for r in list0}),
            "distinct_provision_types": dict(Counter(r.provision_type for r in list0)),
        },
        "latest_v1_merged": {
            "files": [
                str(c0.relative_to(_REPO_ROOT)), str(a0.relative_to(_REPO_ROOT)),
                str(c1.relative_to(_REPO_ROOT)), str(a1.relative_to(_REPO_ROOT)),
            ],
            "records_in_supplement_file": len(v1_verdicts),
            "usable_records": len(list1),
            "verdict_breakdown": dict(Counter(r.audit_verdict for r in list1)),
            "distinct_acts": len({r.act_norm for r in list1}),
            "distinct_provision_types": dict(Counter(r.provision_type for r in list1)),
        },
        "delta": {
            "usable_records": len(list1) - len(list0),
            "distinct_acts": len({r.act_norm for r in list1}) - len({r.act_norm for r in list0}),
        },
        "supplement_composition": {
            "supplement_file_records": len(v1_verdicts),
            "supplement_file_usable": len(v1_usable_keys),
            "keys_overlapping_v0_corrections": len(overlap),
            "corrections": corrections,
            "genuinely_new_keys": len(new_keys),
            "genuinely_new_keys_usable": len(new_usable),
        },
        "reconciliation": reconciliation,
        "documentation_discrepancy": {
            "config_comment": (
                "config/prototype.yaml states the pool expands 'from 59 to 136 records "
                "(78 new VERIFIED_EXACT + the 59 v0 records, with 3 v0 corrections applied)'."
            ),
            "issue": (
                "59 + 78 = 137, not 136. The '78' is the count of USABLE records inside the "
                "v1 supplement FILE, not the count of records ADDED to the pool."
            ),
            "correct_decomposition": (
                f"{len(list0)} v0 usable + {len(new_usable)} genuinely-new usable keys + "
                f"{len(promoted)} keys promoted from unusable by a v0 correction = {len(list1)}."
            ),
            "severity": "documentation imprecision only — the pool size itself (136) is correct",
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "v2_outputs_phase_3_vedant/scripts/compute_evidence_pool_composition.py",
    }

    path = METRICS_DIR / "evidence_pool_composition_v2.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"ORIGINAL v0 usable: {len(list0)}   LATEST merged usable: {len(list1)}   delta: +{len(list1)-len(list0)}")
    print(f"distinct acts: {out['original_v0']['distinct_acts']} -> {out['latest_v1_merged']['distinct_acts']}")
    print(f"reconciles: {reconciliation['reconciles']}  ({reconciliation['v0_usable']} + "
          f"{reconciliation['plus_new_usable_keys']} + {reconciliation['plus_promoted_from_unusable']} "
          f"= {reconciliation['equals_latest_usable']})")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
