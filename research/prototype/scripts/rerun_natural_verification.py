#!/usr/bin/env python3
"""
Re-score the EXISTING natural NyayaRAG generations under both premise framings.

This is a Mode-B (verification-only) re-scoring: the generated statutory_grounding
fields, the extracted claims and the matched evidence are all read from the
committed n=30 and targeted n=11 runs and reused verbatim. Nothing is
regenerated, no case is re-selected, and the source files are opened read-only.
Only the NLI premise framing changes.

Why this is worth running before any new natural evaluation: the controlled
benchmark says the bare premise cannot entail an attributed claim, and real
NyayaRAG claims are overwhelmingly attributed. If that mechanism is what
produced "52/52 NEI" on natural data, it should show up here — on the exact
claims that produced that number — without spending a single GPU generation.

What it CANNOT tell us: whether a corrected field would be better, or whether
any verdict is legally right. Mode C needs generation; legal correctness needs
a lawyer. Both remain out of scope here.

Output: outputs/natural_reverification_framing.{jsonl,md}
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

SOURCES = [
    ("run_B_n30.jsonl", "n30", None),
    ("run_natural_targeted.jsonl", "targeted_n11", "mode_B"),
]


def iter_claims(outputs: Path):
    for fname, tag, sub in SOURCES:
        path = outputs / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            block = rec[sub] if sub else rec
            for c in block.get("claims", []):
                if c.get("evidence_text") and c.get("evidence_id"):
                    yield tag, rec["document_id"], c


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

    claims = [(tag, doc, c) for tag, doc, c in iter_claims(outputs) if c["evidence_id"] in by_key]
    print(f"Re-scoring {len(claims)} evidence-matched natural claims", flush=True)

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=args.device,
    )
    verifier.load()

    rows = []
    for tag, doc_id, c in claims:
        ev = by_key[c["evidence_id"]]
        row = {
            "source": tag, "document_id": doc_id, "claim_id": c["claim_id"],
            "claim_text": c["claim_text"], "evidence_id": c["evidence_id"],
            "evidence_text": c["evidence_text"],
            "recorded_verdict": c["verdict"], "recorded_confidence": c["confidence"],
        }
        for framing in (PREMISE_FRAMING_BARE, PREMISE_FRAMING_LABELED):
            premise = format_premise(
                ev.canonical_text, framing=framing,
                provision_type=ev.provision_type, provision_number=ev.provision_number,
                act=ev.act,
            )
            r = verifier.verify(premise, c["claim_text"])
            row[f"{framing}_verdict"] = r.label
            row[f"{framing}_confidence"] = r.confidence
            row[f"{framing}_sub_reason"] = r.sub_reason
            row[f"{framing}_raw_scores"] = r.raw_scores
        rows.append(row)

    out_jsonl = outputs / "natural_reverification_framing.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(rows)
    bare = Counter(r["bare_verdict"] for r in rows)
    lab = Counter(r["labeled_verdict"] for r in rows)
    reproduced = sum(1 for r in rows if r["bare_verdict"] == r["recorded_verdict"])

    # Correction fires on CONTRADICTED, or on NEI that only got there via the
    # confidence downgrade — same trigger the pipeline uses.
    def triggers(r, fr):
        return r[f"{fr}_verdict"] == CONTRADICTED or r[f"{fr}_sub_reason"] == "low_confidence"

    trig_bare = sum(triggers(r, PREMISE_FRAMING_BARE) for r in rows)
    trig_lab = sum(triggers(r, PREMISE_FRAMING_LABELED) for r in rows)

    md = [
        "# Natural NyayaRAG claims — premise-framing re-verification",
        "",
        f"_Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()}_",
        "",
        "**Verification-only re-scoring of existing runs.** The generated fields, extracted",
        "claims and matched evidence come verbatim from the committed `run_B_n30.jsonl` and",
        "`run_natural_targeted.jsonl`; nothing was regenerated and those files were not",
        "modified. Only the NLI premise framing differs.",
        "",
        "> Verdicts are a small public NLI model's output against a 59-record evidence corpus.",
        "> They are not legal-correctness determinations, and no lawyer ground truth exists.",
        "",
        f"- Evidence-matched natural claims re-scored: **{n}**",
        f"- Bare-framing verdicts reproduced from the original GPU runs: **{reproduced}/{n}**"
        + ("" if reproduced == n else "  ⚠️ mismatch — runs not directly comparable"),
        "",
        "## Verdict distribution",
        "",
        # NOTE: "bare" was production when this script was written
        # (2026-08-26); production has been "labeled" since 2026-08-27 (see
        # FINAL_PRODUCTION_CONFIG.md). Labeled as "historical baseline" here
        # so a future rerun never mislabels the current production framing.
        "| Verdict | bare (historical baseline) | labeled |",
        "|---|---|---|",
    ]
    for lbl in (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION):
        md.append(f"| {lbl} | {bare.get(lbl, 0)} | {lab.get(lbl, 0)} |")
    md += [
        "",
        "## Correction trigger rate",
        "",
        "| Premise framing | Claims triggering correction |",
        "|---|---|",
        f"| bare (historical baseline) | {trig_bare}/{n} |",
        f"| labeled | {trig_lab}/{n} |",
        "",
        "## Interpretation",
        "",
        "A claim moving NEI → ENTAILED here means the NLI model now finds the statute text",
        "supports the sentence once the premise carries the provision label the sentence is",
        "about. It does NOT mean the sentence is legally correct, and it does not by itself",
        "demonstrate that the pipeline improves anything: on natural data a higher ENTAILED",
        "count means fewer claims are flagged, so the correction path stays mostly idle.",
        "",
        "## Claims that changed verdict",
        "",
    ]
    changed = [r for r in rows if r["bare_verdict"] != r["labeled_verdict"]]
    md.append(f"{len(changed)}/{n} claims changed verdict under labeled framing.")
    md.append("")
    for r in changed[:10]:
        md += [
            f"- **{r['evidence_id']}** ({r['source']}/{r['document_id']}/{r['claim_id']})",
            f"  - claim: {r['claim_text'][:200]}",
            f"  - {r['bare_verdict']} ({r['bare_confidence']:.3f}) → "
            f"{r['labeled_verdict']} ({r['labeled_confidence']:.3f})",
        ]

    still_nei = [r for r in rows if r["labeled_verdict"] == NOT_ENOUGH_INFORMATION]
    md += ["", f"## Claims still NEI under labeled framing ({len(still_nei)})", "",
           "These are the ones worth a lawyer's eye: the statute text plus its label still does",
           "not settle them, which is often correct for a sentence that bundles several",
           "citations or asserts something about the case rather than about the provision.", ""]
    for r in still_nei[:8]:
        md += [f"- **{r['evidence_id']}**: {r['claim_text'][:190]}"]

    (outputs / "natural_reverification_framing.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\nClaims: {n}   bare reproduced original: {reproduced}/{n}")
    print(f"Bare:    {dict(bare)}")
    print(f"Labeled: {dict(lab)}")
    print(f"Correction triggers — bare: {trig_bare}/{n}, labeled: {trig_lab}/{n}")
    print(f"Changed verdict: {len(changed)}/{n}")
    print(f"\nWrote {out_jsonl}\nWrote {outputs / 'natural_reverification_framing.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
