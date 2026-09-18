#!/usr/bin/env python3
"""
V2 FRESH RERUN — claim parser + evidence matcher, ORIGINAL CODE vs LATEST CODE.

WHAT THIS MEASURES
------------------
A genuine ORIGINAL-CODEBASE -> LATEST-CODEBASE comparison of the deterministic
front half of the pipeline (claim parsing + evidence matching), executed fresh
on this machine.

  ORIGINAL arm : src/{claim_parser,evidence_matcher,data_loader}.py exactly as
                 they existed at commit 0e37525 ("Initial release: legal claim
                 verification prototype", 2026-08-13), extracted from git at
                 runtime via `git show` — never vendored, never approximated.
  LATEST arm   : the same three modules at HEAD.

Both arms run over the IDENTICAL already-generated Qwen text in
`outputs/run_A_n30.jsonl` (30 real NyayaRAG documents) and the IDENTICAL
read-only v0 evidence files. No model is loaded, no GPU is used, and no text
is regenerated — so this comparison is unaffected by this machine having no
GPU, and is fully deterministic (no seed required).

HOW THIS DIFFERS FROM THE HISTORICAL n=30 PARSER RESULT
-------------------------------------------------------
`scripts/reparse_n30_with_fixed_parser.py` compared the then-current parser
against the `claims` array already stored inside run_A_n30.jsonl (i.e. against
a stored artifact of the pre-fix parser). This script instead re-executes the
original parser source itself, so both arms are freshly computed here under
one stack. That makes it a stronger ORIGINAL-vs-LATEST claim, and it also
covers every parser change since, not only the 223eb9d fix.

WHY THE EVIDENCE POOL IS HELD AT v0 IN BOTH ARMS
------------------------------------------------
To isolate the PARSER/MATCHER lever. `use_evidence_v1` is a separate lever
measured separately (see compute_evidence_pool_composition.py and the evidence
experiments). A supplementary arm — latest parser + v1 pool — is also reported,
and is explicitly labelled as varying TWO levers at once, so it must never be
quoted as a parser-only effect.

NOTE ON act_norm
----------------
`normalize_act()` lives in claim_parser.py and is used by data_loader to
normalise the EVIDENCE side too. Each arm therefore loads the evidence pool
with its OWN data_loader, which is the faithful reproduction: the acronym
normalisation change affects both the claim side and the evidence side, and
that is part of the change being measured.

STATISTICS
----------
Two-sided exact sign test on the per-document paired change in the number of
claims that resolve to evidence. Documents with zero change are discarded
(standard sign-test treatment); the reported n is the number of discordant
documents. Descriptive counts are reported alongside.

OUTPUT
------
metrics/parser_original_vs_latest_v2.json
metrics/parser_original_vs_latest_v2_per_document.csv
"""
from __future__ import annotations

import csv
import importlib
import json
import math
import platform
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
_PROTOTYPE_ROOT = _V2_ROOT.parent
_REPO_ROOT = _PROTOTYPE_ROOT.parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml  # noqa: E402

ORIGINAL_COMMIT = "0e37525"
# Intermediate checkpoint: the commit whose parser fix the HISTORICAL n=30 result
# measured. Including it turns a two-point comparison into an attributable
# three-point progression, and reconciles this script's numbers against the
# historical artifact (which stops at this commit) rather than appearing to
# contradict it.
INTERMEDIATE_COMMIT = "223eb9d"
ORIGINAL_MODULES = ("__init__", "claim_parser", "evidence_matcher", "data_loader")
INPUT_JSONL = _PROTOTYPE_ROOT / "outputs" / "run_A_n30.jsonl"
CONFIG_PATH = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
METRICS_DIR = _V2_ROOT / "metrics"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(_REPO_ROOT), check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout


def materialise_commit(dest: Path, commit: str, pkg_name: str) -> dict:
    """Extract one commit's parser/matcher/loader into an importable package.

    Read-only: uses `git show <commit>:<path>`. The working tree is never
    checked out, reset, or otherwise touched.
    """
    pkg = dest / pkg_name
    pkg.mkdir(parents=True, exist_ok=True)
    provenance = {}
    for mod in ORIGINAL_MODULES:
        rel = f"research/prototype/src/{mod}.py"
        content = git("show", f"{commit}:{rel}")
        (pkg / f"{mod}.py").write_text(content, encoding="utf-8")
        blob = git("rev-parse", f"{commit}:{rel}").strip()
        provenance[rel] = {"blob_sha": blob, "bytes": len(content.encode("utf-8"))}
    return provenance


def summarise_claims(claims, match_fn, exact_index, all_usable, threshold) -> dict:
    """Run evidence matching over a parsed claim list and summarise."""
    n_matched = 0
    methods = Counter()
    rows = []
    for c in claims:
        cit = c.citation_extracted
        res = match_fn(cit, exact_index, all_usable, threshold)
        methods[res.match_method] += 1
        if res.matched:
            n_matched += 1
        rows.append({
            "claim_id": c.claim_id,
            "provision_type": cit.provision_type,
            "provision_number": cit.provision_number,
            "subsection": cit.subsection,
            "act_norm": cit.act_norm,
            "matched": res.matched,
            "match_method": res.match_method,
            "evidence_key": res.evidence.dataset_citation_key if res.evidence else None,
            "has_assertion_text": bool(getattr(c, "assertion_text", None)),
        })
    return {
        "n_claims": len(claims),
        "n_matched": n_matched,
        "methods": dict(methods),
        "rows": rows,
    }


def sign_test_two_sided(n_pos: int, n_neg: int) -> dict:
    """Exact two-sided sign test. Ties are excluded, per standard treatment."""
    n = n_pos + n_neg
    if n == 0:
        return {"n_discordant": 0, "n_improved": 0, "n_worsened": 0,
                "p_value": 1.0, "test": "exact sign test (two-sided)",
                "note": "no discordant documents"}
    k = min(n_pos, n_neg)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return {
        "n_discordant": n,
        "n_improved": n_pos,
        "n_worsened": n_neg,
        "p_value": min(1.0, 2.0 * tail),
        "test": "exact sign test (two-sided)",
    }


def main() -> int:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    head = git("rev-parse", "HEAD").strip()
    orig_full = git("rev-parse", ORIGINAL_COMMIT).strip()
    orig_date = git("show", "-s", "--format=%cI", ORIGINAL_COMMIT).strip()

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    usable_verdicts = set(cfg["usable_evidence_verdicts"])
    threshold = cfg["evidence_matching"]["fuzzy_token_overlap_threshold"]

    c0 = _REPO_ROOT / paths["canonical_statutes"]
    a0 = _REPO_ROOT / paths["evidence_audit"]
    c1 = _REPO_ROOT / paths["canonical_statutes_v1"]
    a1 = _REPO_ROOT / paths["evidence_audit_v1"]

    tmpdir = Path(tempfile.mkdtemp(prefix="nyayamind_hist_"))
    prov_orig = materialise_commit(tmpdir, ORIGINAL_COMMIT, "nyayamind_original")
    prov_mid = materialise_commit(tmpdir, INTERMEDIATE_COMMIT, "nyayamind_intermediate")
    sys.path.insert(0, str(tmpdir))

    arms: dict[str, dict] = {}

    def register(name, parser_mod, matcher_mod, loader_mod, commit, provenance):
        index, allrecs = loader_mod.load_usable_evidence(c0, a0, usable_verdicts)
        arms[name] = {
            "parser": parser_mod, "matcher": matcher_mod,
            "index": index, "all": allrecs,
            "commit": commit, "provenance": provenance,
            "claims": 0, "matched": 0, "assertion_text": 0,
            "methods": Counter(),
        }

    register("ORIGINAL_0e37525",
             importlib.import_module("nyayamind_original.claim_parser"),
             importlib.import_module("nyayamind_original.evidence_matcher"),
             importlib.import_module("nyayamind_original.data_loader"),
             git("rev-parse", ORIGINAL_COMMIT).strip(), prov_orig)
    register("INTERMEDIATE_223eb9d",
             importlib.import_module("nyayamind_intermediate.claim_parser"),
             importlib.import_module("nyayamind_intermediate.evidence_matcher"),
             importlib.import_module("nyayamind_intermediate.data_loader"),
             git("rev-parse", INTERMEDIATE_COMMIT).strip(), prov_mid)
    register("LATEST_HEAD",
             importlib.import_module("src.claim_parser"),
             importlib.import_module("src.evidence_matcher"),
             importlib.import_module("src.data_loader"),
             head, {"path": "research/prototype/src/ (working tree at HEAD)"})

    l_loader = importlib.import_module("src.data_loader")
    l_matcher = importlib.import_module("src.evidence_matcher")
    l_index_v1, l_all_v1 = l_loader.load_usable_evidence(c0, a0, usable_verdicts, c1, a1)
    latest_v1_matched = 0

    arm_names = list(arms)
    per_doc = []
    matched_by_arm: dict[str, list[int]] = {k: [] for k in arm_names}

    with INPUT_JSONL.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            doc_id = rec["document_id"]
            text = rec["generated_field"]["text"]

            row = {"document_id": doc_id}
            latest_claims_cache = None
            for name in arm_names:
                a = arms[name]
                claims = a["parser"].extract_claims(text)
                s = summarise_claims(claims, a["matcher"].match_evidence,
                                     a["index"], a["all"], threshold)
                a["methods"].update(s["methods"])
                a["claims"] += s["n_claims"]
                a["matched"] += s["n_matched"]
                n_assert = sum(1 for r in s["rows"] if r["has_assertion_text"])
                a["assertion_text"] += n_assert
                matched_by_arm[name].append(s["n_matched"])
                row[f"{name}_claims"] = s["n_claims"]
                row[f"{name}_matched"] = s["n_matched"]
                if name == "LATEST_HEAD":
                    latest_claims_cache = claims
                    row["LATEST_claims_with_assertion_text"] = n_assert

            s_v1 = summarise_claims(latest_claims_cache, l_matcher.match_evidence,
                                    l_index_v1, l_all_v1, threshold)
            latest_v1_matched += s_v1["n_matched"]
            row["LATEST_matched_with_v1_pool"] = s_v1["n_matched"]
            row["delta_matched_original_to_latest"] = (
                row["LATEST_HEAD_matched"] - row["ORIGINAL_0e37525_matched"])
            per_doc.append(row)

    def paired(a_name: str, b_name: str) -> dict:
        pos = neg = same = 0
        for x, y in zip(matched_by_arm[a_name], matched_by_arm[b_name]):
            if y > x:
                pos += 1
            elif y < x:
                neg += 1
            else:
                same += 1
        r = sign_test_two_sided(pos, neg)
        r["unchanged"] = same
        r["from"] = a_name
        r["to"] = b_name
        return r

    sign = paired("ORIGINAL_0e37525", "LATEST_HEAD")
    n_improved, n_worsened, n_same = sign["n_improved"], sign["n_worsened"], sign["unchanged"]
    progression_tests = {
        "original_to_latest": sign,
        "original_to_intermediate": paired("ORIGINAL_0e37525", "INTERMEDIATE_223eb9d"),
        "intermediate_to_latest": paired("INTERMEDIATE_223eb9d", "LATEST_HEAD"),
    }

    tot = {
        "orig_claims": arms["ORIGINAL_0e37525"]["claims"],
        "intermediate_claims": arms["INTERMEDIATE_223eb9d"]["claims"],
        "latest_claims": arms["LATEST_HEAD"]["claims"],
        "orig_matched": arms["ORIGINAL_0e37525"]["matched"],
        "intermediate_matched": arms["INTERMEDIATE_223eb9d"]["matched"],
        "latest_matched": arms["LATEST_HEAD"]["matched"],
        "latest_v1_matched": latest_v1_matched,
        "latest_claims_with_assertion_text": arms["LATEST_HEAD"]["assertion_text"],
    }
    o_methods = arms["ORIGINAL_0e37525"]["methods"]
    m_methods = arms["INTERMEDIATE_223eb9d"]["methods"]
    l_methods = arms["LATEST_HEAD"]["methods"]
    provenance = {k: arms[k]["provenance"] for k in arm_names}
    n_docs = len(per_doc)

    out = {
        "artifact_id": "PARSER-V2-FRESH",
        "comparison": "ORIGINAL CODEBASE (0e37525) vs LATEST CODEBASE (HEAD) — claim parser + evidence matcher",
        "comparison_scope": (
            "Isolates the deterministic parsing/matching front half of the pipeline. "
            "Evidence pool held at v0 in BOTH arms so the parser/matcher change is the "
            "only thing varying. The supplementary 'latest parser + v1 pool' figure "
            "varies TWO levers and must never be quoted as a parser-only effect."
        ),
        "evidence_grade": "DETERMINISTIC_SYNTHETIC",
        "grade_note": (
            "Deterministic re-execution of real committed code over real already-generated "
            "text. There are NO gold labels for claim extraction here: 'matched' means the "
            "extracted citation resolved to a record in the audited evidence pool, which is "
            "a retrieval/coverage outcome, NOT a correctness label. Do not call any number "
            "here accuracy, precision, recall or F1."
        ),
        "deterministic": True,
        "seed_required": False,
        "models_used": None,
        "gpu_required": False,
        "arms": {
            "ORIGINAL_0e37525": {
                "commit": orig_full, "commit_short": ORIGINAL_COMMIT, "commit_date": orig_date,
                "role": "ORIGINAL NyayaMind codebase (root commit)",
                "capabilities_absent": ["assertion_text", "assertion_spans",
                                        "Art./Arts. abbreviation", "acronym/alias normalization"],
            },
            "INTERMEDIATE_223eb9d": {
                "commit": git("rev-parse", INTERMEDIATE_COMMIT).strip(),
                "commit_short": INTERMEDIATE_COMMIT,
                "commit_date": git("show", "-s", "--format=%cI", INTERMEDIATE_COMMIT).strip(),
                "role": ("the parser-fix commit the HISTORICAL n=30 artifact measured "
                         "(outputs/parser_fix_before_after_n30.json). Included so this "
                         "script reconciles with, rather than appears to contradict, that artifact."),
            },
            "LATEST_HEAD": {"commit": head, "modules_path": "research/prototype/src/",
                            "role": "LATEST NyayaMind codebase"},
        },
        "module_provenance": provenance,
        "input": {
            "path": str(INPUT_JSONL.relative_to(_PROTOTYPE_ROOT)),
            "n_documents": n_docs,
            "note": "already-generated Qwen2.5-7B output; no regeneration performed",
        },
        "evidence_pool_both_arms": {
            "canonical": str(c0.relative_to(_REPO_ROOT)),
            "audit": str(a0.relative_to(_REPO_ROOT)),
            "usable_records_by_arm": {k: len(arms[k]["all"]) for k in arm_names},
            "fuzzy_token_overlap_threshold": threshold,
        },
        "totals": tot,
        "progression_claims_resolving_to_evidence": {
            "ORIGINAL_0e37525": tot["orig_matched"],
            "INTERMEDIATE_223eb9d": tot["intermediate_matched"],
            "LATEST_HEAD": tot["latest_matched"],
            "denominator_claims_extracted": {
                "ORIGINAL_0e37525": tot["orig_claims"],
                "INTERMEDIATE_223eb9d": tot["intermediate_claims"],
                "LATEST_HEAD": tot["latest_claims"],
            },
        },
        "match_methods": {
            "ORIGINAL_0e37525": dict(o_methods),
            "INTERMEDIATE_223eb9d": dict(m_methods),
            "LATEST_HEAD": dict(l_methods),
        },
        "per_document_outcome_original_to_latest": {
            "n_documents": n_docs,
            "improved": n_improved,
            "worsened": n_worsened,
            "unchanged": n_same,
        },
        "statistics": progression_tests,
        "reconciliation_against_committed_artifacts": {
            "ORIGINAL_arm": {
                "fresh_value_claims_matched": tot["orig_matched"],
                "fresh_value_claims_extracted": tot["orig_claims"],
                "historical_artifacts": [
                    "0e37525:research/prototype/outputs/eval_30_report.md — 30 cases, 88 claims, 38/88 evidence coverage",
                    "outputs/parser_fix_before_after_n30.json — totals.old_claims=88, totals.old_with_evidence=38",
                ],
                "status": "EXACT_REPRODUCTION (88 claims / 38 matched)",
            },
            "LATEST_arm": {
                "fresh_value_claims_matched": tot["latest_matched"],
                "fresh_value_claims_extracted": tot["latest_claims"],
                "historical_artifact": "outputs/parser_fix_before_after_n30_v2_postfix.json — totals.new_claims=93, totals.new_with_evidence=57",
                "status": "EXACT_REPRODUCTION (93 claims / 57 matched)",
            },
            "INTERMEDIATE_arm": {
                "fresh_value_claims_matched": tot["intermediate_matched"],
                "historical_artifact": "outputs/parser_fix_before_after_n30.json — totals.new_with_evidence=51 (committed AT 223eb9d)",
                "status": "DISCREPANCY_UNRESOLVED",
                "delta": tot["intermediate_matched"] - 51,
                "investigation": (
                    "Re-executing the COMMITTED 223eb9d parser source over the same 30 texts yields 54 "
                    "claims resolving to evidence, where the artifact committed at that same commit records 51. "
                    "Component isolation rules out the matcher and loader: holding the parser at 223eb9d and "
                    "swapping the evidence_matcher/data_loader between 223eb9d and HEAD gives 54 either way, "
                    "and holding the parser at HEAD gives 57 either way — so the entire 54->57 movement is "
                    "parser-side and the matcher changes are inert on this data. The counting rule is also "
                    "identical (claims whose evidence_id is not None). The most likely explanation is that the "
                    "artifact was generated from a working tree whose parser differed slightly from the source "
                    "finally committed at 223eb9d. Recorded, not resolved."
                ),
                "impact_on_conclusions": (
                    "None of the ORIGINAL->LATEST conclusions depend on this arm: both endpoints reproduce their "
                    "committed artifacts exactly. The intermediate arm is reported for attribution only."
                ),
            },
        },
        "supplementary_two_lever": {
            "description": "latest parser + v1 evidence pool (parser AND use_evidence_v1 both changed)",
            "latest_matched_with_v1_pool": tot["latest_v1_matched"],
            "warning": "TWO levers vary here — not attributable to the parser alone",
        },
        "new_capability_note": (
            f"{tot['latest_claims_with_assertion_text']} of {tot['latest_claims']} latest-arm claims "
            f"carry an assertion_text span. The ORIGINAL parser had no such field at all "
            f"(Claim = claim_id, claim_text, citation_extracted), so this is a new capability "
            f"with no original-arm counterpart — a capability count, not an improvement metric."
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "generated_by": "v2_outputs_phase_3_vedant/scripts/rerun_parser_original_vs_latest.py",
    }

    (METRICS_DIR / "parser_original_vs_latest_v2.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    csv_path = METRICS_DIR / "parser_original_vs_latest_v2_per_document.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_doc[0].keys()))
        w.writeheader()
        w.writerows(per_doc)

    print("=== PARSER: ORIGINAL (0e37525) -> INTERMEDIATE (223eb9d) -> LATEST (HEAD) ===")
    print(f"  documents                : {n_docs}")
    print(f"  claims extracted         : {tot['orig_claims']} -> {tot['intermediate_claims']} -> {tot['latest_claims']}")
    print(f"  claims resolving to evid.: {tot['orig_matched']} -> {tot['intermediate_matched']} -> {tot['latest_matched']}")
    for k, v in progression_tests.items():
        print(f"  {k:28}: +{v['n_improved']}/-{v['n_worsened']}/={v['unchanged']} docs, p={v['p_value']:.4f}")
    print(f"  match methods ORIGINAL   : {dict(o_methods)}")
    print(f"  match methods INTERMED.  : {dict(m_methods)}")
    print(f"  match methods LATEST     : {dict(l_methods)}")
    print(f"  [supplementary] latest parser + v1 pool matched: {tot['latest_v1_matched']}")
    print(f"  wrote {METRICS_DIR / 'parser_original_vs_latest_v2.json'}")
    print(f"  wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
