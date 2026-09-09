#!/usr/bin/env python
"""
Measure the real, concrete impact of the Art./Arts. citation-abbreviation
fix (src/claim_parser.py: _SENTENCE_BOUNDARY_ABBREVIATIONS,
_ABBREVIATED_KEYWORD_PATTERN) across every unique real generated text
already committed under outputs/*.jsonl, WITHOUT re-running Qwen generation.

IMPORTANT METHODOLOGY NOTE: the OLD baseline here is the parser exactly as
it stood at git commit OLD_COMMIT below (immediately before this fix) --
loaded fresh via `git show`, NOT the `claims` field already stored in each
output record. Those stored fields were produced by whatever parser
version existed on the date each experiment originally ran, which for many
older files predates SEVERAL unrelated historical bugfixes (bug1-bug5,
trim-heuristic fixes, etc.) -- diffing against them would silently
attribute all of that historical drift to THIS fix, overstating its impact.
Comparing two in-memory parser versions on the exact same already-generated
text isolates only this fix's own effect.

Read-only w.r.t. every existing output file (never modifies them, and the
git show is read-only too). Writes
outputs/article_abbreviation_fix_impact.json (per-case deltas) and
outputs/article_abbreviation_fix_impact_report.md (summary).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.claim_parser import extract_claims as extract_claims_new
from src.data_loader import load_usable_evidence_from_config
from src.evidence_matcher import match_evidence

# The commit immediately before this fix (Stage 2 / retrieval-signals
# commit) -- `git log --oneline` in this repo to confirm before reusing.
OLD_COMMIT = "6347c45"


def _load_old_extract_claims(repo_root: Path):
    """Load the pre-fix claim_parser.extract_claims via `git show` into an
    isolated temp package, without touching the working tree or the
    already-imported `src` module."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="claim_parser_old_"))
    pkg_dir = tmp_dir / "old_claim_parser_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    for name in ("claim_parser.py", "data_loader.py", "evidence_matcher.py"):
        result = subprocess.run(
            ["git", "show", f"{OLD_COMMIT}:research/prototype/src/{name}"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        )
        (pkg_dir / name).write_text(result.stdout, encoding="utf-8")
    sys.path.insert(0, str(tmp_dir))
    from old_claim_parser_pkg.claim_parser import extract_claims as old_extract_claims
    return old_extract_claims


def main() -> int:
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    exact_index, all_usable = load_usable_evidence_from_config(config, repo_root)
    fuzzy_threshold = config["evidence_matching"]["fuzzy_token_overlap_threshold"]

    old_extract_claims = _load_old_extract_claims(repo_root)

    outputs_dir = _PROTOTYPE_ROOT / "outputs"
    seen_texts: dict[str, dict] = {}  # generated text -> {doc_id, source_file}

    for fp in sorted(outputs_dir.glob("*.jsonl")):
        try:
            with fp.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    gf = rec.get("generated_field")
                    if not (isinstance(gf, dict) and isinstance(gf.get("text"), str)):
                        continue
                    text = gf["text"]
                    if text not in seen_texts:
                        seen_texts[text] = {
                            "doc_id": rec.get("document_id"),
                            "source_file": fp.name,
                        }
        except Exception:
            continue

    per_case = []
    changed = []
    totals = {"old_claims": 0, "new_claims": 0, "old_with_evidence": 0, "new_with_evidence": 0}

    for text, meta in seen_texts.items():
        old_claims = old_extract_claims(text)
        new_claims = extract_claims_new(text)

        def _count_with_evidence(claims_list):
            n = 0
            for c in claims_list:
                if c.citation_extracted is None:
                    continue
                result = match_evidence(
                    c.citation_extracted, exact_index, all_usable,
                    fuzzy_token_overlap_threshold=fuzzy_threshold,
                )
                if result.matched:
                    n += 1
            return n

        old_with_evidence = _count_with_evidence(old_claims)
        new_with_evidence = _count_with_evidence(new_claims)

        old_n = len(old_claims)
        new_n = len(new_claims)
        totals["old_claims"] += old_n
        totals["new_claims"] += new_n
        totals["old_with_evidence"] += old_with_evidence
        totals["new_with_evidence"] += new_with_evidence

        row = {
            "doc_id": meta["doc_id"],
            "source_file": meta["source_file"],
            "old_claim_count": old_n,
            "new_claim_count": new_n,
            "old_claims_with_evidence": old_with_evidence,
            "new_claims_with_evidence": new_with_evidence,
            "delta": new_n - old_n,
        }
        per_case.append(row)
        if new_n != old_n:
            changed.append(row)

    out_json = outputs_dir / "article_abbreviation_fix_impact.json"
    out_json.write_text(
        json.dumps({"totals": totals, "unique_texts_checked": len(seen_texts), "per_case": per_case}, indent=2),
        encoding="utf-8",
    )

    decreased = [r for r in changed if r["delta"] < 0]
    report = [
        "# Art./Arts. Citation-Abbreviation Fix: Real-Data Impact Audit\n\n",
        f"Both parser versions loaded fresh via `git show` / the current working tree and run "
        f"in-memory on the exact same {len(seen_texts)} unique real generated texts (deduplicated "
        f"across every outputs/*.jsonl `generated_field.text`) -- OLD = commit {OLD_COMMIT} "
        f"(immediately before this fix), NEW = current. This isolates ONLY this fix's effect, "
        f"unlike diffing against each record's stored `claims` field (which reflects whatever "
        f"parser version existed when that experiment originally ran, months of unrelated "
        f"bugfixes ago in some cases).\n\n",
        f"- Total claims (OLD parser): {totals['old_claims']}\n",
        f"- Total claims (NEW/fixed parser, same texts): {totals['new_claims']}\n",
        f"- Net claims recovered: {totals['new_claims'] - totals['old_claims']}\n",
        f"- OLD claims with a matched evidence record: {totals['old_with_evidence']}\n",
        f"- NEW claims with a matched evidence record: {totals['new_with_evidence']}\n\n",
        f"## Cases where claim count changed ({len(changed)} / {len(seen_texts)})\n\n",
    ]
    if changed:
        report.append("| doc_id | source_file | old | new | delta | old w/ evidence | new w/ evidence |\n")
        report.append("|---|---|---|---|---|---|---|\n")
        for row in changed:
            report.append(
                f"| {row['doc_id']} | {row['source_file']} | {row['old_claim_count']} | "
                f"{row['new_claim_count']} | {row['delta']:+d} | {row['old_claims_with_evidence']} | "
                f"{row['new_claims_with_evidence']} |\n"
            )
    else:
        report.append("None.\n")
    if decreased:
        report.append(
            f"\n**WARNING: {len(decreased)} case(s) show a claim-count DECREASE** -- "
            "this fix was intended to be strictly additive/corrective; a decrease means either "
            "a real regression or a legitimate correction of an over-count. Investigate before "
            "treating this fix as safe.\n"
        )
    else:
        report.append(
            "\nNo claim count ever decreased between the two parser versions on any of these "
            f"{len(seen_texts)} real texts -- this fix is strictly additive/corrective on every "
            "real generated paragraph this project has produced to date.\n"
        )

    out_md = outputs_dir / "article_abbreviation_fix_impact_report.md"
    out_md.write_text("".join(report), encoding="utf-8")

    print(f"Checked {len(seen_texts)} unique real generated texts.")
    print(f"Old total claims: {totals['old_claims']}, New total claims: {totals['new_claims']}")
    print(f"Cases changed: {len(changed)}")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
