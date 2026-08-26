#!/usr/bin/env python3
"""
STEP 4/5 — diagnose the 0% correction success rate.

Re-verifies the corrections the REAL Qwen corrector already produced and saved
in outputs/run_synthetic_stress.jsonl, under both premise framings. No text is
regenerated: the corrected claims are read from disk exactly as the GPU run
emitted them, so this isolates the re-verification gate as the only variable and
costs no generation. run_synthetic_stress.jsonl is opened read-only and never
rewritten.

The question this answers: were those 30 corrections actually bad, or was the
gate rejecting good ones? Those have opposite implications — the first is a
corrector problem, the second is a scoring bug that was suppressing a working
correction path.

Output: outputs/correction_reverification_framing.{jsonl,md}
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.data_loader import load_usable_evidence
from src.verifier import (
    NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
    format_premise, PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED,
)

# The unflagged sentence the synthetic harness appends to every field; the
# scope-preservation property is that correction must leave it byte-identical.
UNFLAGGED_SENTENCE = ("Article 14 of the Constitution of India guarantees equality "
                      "before the law.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = ap.parse_args()

    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    _, usable = load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )
    by_key = {r.dataset_citation_key: r for r in usable}

    src = outputs / "run_synthetic_stress.jsonl"
    records = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]

    cases = []
    for rec in records:
        corr = rec["condition_C"]["correction"]
        if not corr.get("regenerated_text"):
            continue
        rv = corr.get("reverification") or {}
        claim = rv.get("claim_text")
        ev_id = rv.get("evidence_id") or rec.get("evidence_id")
        if not claim or ev_id not in by_key:
            continue
        cases.append({
            "synthetic_claim_id": rec["synthetic_claim_id"],
            "transform_rule": rec["transform_rule"],
            "evidence_id": ev_id,
            "evidence": by_key[ev_id],
            "original_claim": rec["original_synthetic_text"],
            "corrected_claim": claim,
            "corrected_field_text": corr["regenerated_text"],
            "original_status": corr["status"],
            "original_verdict": rv.get("verdict"),
            "original_confidence": rv.get("confidence"),
        })

    print(f"Loaded {len(cases)} stored Qwen corrections from {src.name}", flush=True)
    if not cases:
        print("No stored corrections found; nothing to diagnose.")
        return 1

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=args.device,
    )
    verifier.load()
    print(f"Loaded {verifier.model_id} on {args.device}", flush=True)

    rows = []
    for c in cases:
        ev = c["evidence"]
        row = dict(c)
        row.pop("evidence")
        # Scope preservation is a property of the corrector's output text and is
        # independent of framing, so it is checked once on the stored field.
        row["scope_preserved"] = UNFLAGGED_SENTENCE in c["corrected_field_text"]
        for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
            premise = format_premise(
                ev.canonical_text, framing=framing,
                provision_type=ev.provision_type, provision_number=ev.provision_number,
                act=ev.act,
            )
            r = verifier.verify(premise, c["corrected_claim"])
            row[f"{framing}_verdict"] = r.label
            row[f"{framing}_confidence"] = r.confidence
            row[f"{framing}_raw_scores"] = r.raw_scores
            # A correction may only ship if it re-verifies as ENTAILED *and*
            # left the unflagged sentence intact — the same gate production uses.
            row[f"{framing}_would_ship"] = (r.label == ENTAILED) and row["scope_preserved"]
        rows.append(row)

    out_jsonl = outputs / "correction_reverification_framing.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    bare = Counter(r["bare_verdict"] for r in rows)
    lab = Counter(r["labeled_verdict"] for r in rows)
    ship_bare = sum(r["bare_would_ship"] for r in rows)
    ship_lab = sum(r["labeled_would_ship"] for r in rows)
    scope_ok = sum(r["scope_preserved"] for r in rows)
    n = len(rows)

    # Reproduction check: bare framing here should match what the GPU run
    # recorded. If it does not, the two runs are not comparable and the whole
    # comparison below is void, so say so loudly rather than quietly reporting.
    reproduced = sum(1 for r in rows if r["bare_verdict"] == r["original_verdict"])

    md = [
        "# Correction Re-verification — premise-framing diagnosis",
        "",
        f"_Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()}_",
        "",
        "**SYNTHETIC DATA.** Re-verification only: the corrected claims are the ones the",
        "real Qwen2.5-7B corrector produced during the GPU synthetic stress run and wrote to",
        "`run_synthetic_stress.jsonl`. Nothing was regenerated here, and that file was not",
        "modified. The single variable is how the NLI premise is framed.",
        "",
        f"- Stored corrections examined: **{n}**",
        f"- Bare-framing verdicts reproduced from the original GPU run: **{reproduced}/{n}**"
        + ("" if reproduced == n else "  ⚠️ mismatch — runs are not directly comparable"),
        f"- Scope preserved (unflagged sentence intact): **{scope_ok}/{n}**",
        "",
        "## Re-verification verdict on the corrected claim",
        "",
        "| Verdict | bare premise (production) | labeled premise |",
        "|---|---|---|",
    ]
    for lbl in (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION):
        md.append(f"| {lbl} | {bare.get(lbl, 0)} | {lab.get(lbl, 0)} |")
    md += [
        "",
        "## Corrections that would pass the safety gate",
        "",
        "| Premise framing | Corrections shipped | Rate |",
        "|---|---|---|",
        f"| bare (production) | {ship_bare}/{n} | {ship_bare / n:.1%} |",
        f"| labeled | {ship_lab}/{n} | {ship_lab / n:.1%} |",
        "",
        "The gate is unchanged: a correction ships only if it re-verifies as ENTAILED and the",
        "unflagged sentence survived verbatim. Only the premise framing differs.",
        "",
        "## Examples",
        "",
    ]
    flipped = [r for r in rows if not r["bare_would_ship"] and r["labeled_would_ship"]]
    still_failing = [r for r in rows if not r["labeled_would_ship"]]

    md.append(f"### Corrections rejected under bare framing but accepted under labeled ({len(flipped)})")
    md.append("")
    for r in flipped[:5]:
        md += [
            f"- **{r['evidence_id']}** (`{r['transform_rule']}`)",
            f"  - corrupted claim: {r['original_claim'][:200]}",
            f"  - Qwen correction: {r['corrected_claim'][:200]}",
            f"  - bare: {r['bare_verdict']} ({r['bare_confidence']:.3f}) → "
            f"labeled: {r['labeled_verdict']} ({r['labeled_confidence']:.3f})",
        ]
    md += ["", f"### Corrections still not shipping under labeled framing ({len(still_failing)})", ""]
    for r in still_failing[:8]:
        md += [
            f"- **{r['evidence_id']}** (`{r['transform_rule']}`) → {r['labeled_verdict']} "
            f"({r['labeled_confidence']:.3f}), scope_preserved={r['scope_preserved']}",
            f"  - Qwen correction: {r['corrected_claim'][:220]}",
        ]

    out_md = outputs / "correction_reverification_framing.md"
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\nStored corrections: {n}")
    print(f"Bare-framing reproduction of original run: {reproduced}/{n}")
    print(f"Scope preserved: {scope_ok}/{n}")
    print(f"Bare verdicts:    {dict(bare)}")
    print(f"Labeled verdicts: {dict(lab)}")
    print(f"Would ship — bare: {ship_bare}/{n} ({ship_bare / n:.1%})   "
          f"labeled: {ship_lab}/{n} ({ship_lab / n:.1%})")
    print(f"\nWrote {out_jsonl}\nWrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
