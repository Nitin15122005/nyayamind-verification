#!/usr/bin/env python3
"""
Re-score EXISTING evidence-matched claims (from every committed real-data
run under outputs/*.jsonl) under two PRIMARY-verification hypothesis
choices: the full `claim_text` (current production) vs. the narrower
`assertion_text` (the new, opt-in `verification.narrow_primary_hypothesis`
flag). Both use the current production "labeled" premise framing -- only
the hypothesis differs.

This is Mode-B-style re-scoring: generated fields, extracted claims, and
matched evidence are all read verbatim from already-committed output;
nothing is regenerated, no case is re-selected, no source file is
modified. Real DeBERTa (184M params) runs fine on CPU, so this needs no
GPU -- mirrors scripts/rerun_natural_verification.py's methodology exactly.

Why this is worth running: outputs/final_limitations_and_future_scope.md
Sec.3a names this as a concrete, evidence-backed next step -- "the primary
verification pass never uses the narrower assertion_text hypothesis" -- but
it was never actually measured. This script measures it, honestly: an
NEI-to-ENTAILED flip is only a genuine win if the assertion_text really is
a narrower, non-fabricated restatement of what the evidence supports, NOT
an artifact of throwing away context that made the full sentence correctly
neutral (the labeled-framing diagnosis already found exactly this risk for
a related change -- see verifier_correction_diagnosis.md Sec.6, "3 that flip
are shallow"). Every changed case is written out for manual inspection, not
just the aggregate counts.

Output: outputs/narrow_primary_hypothesis_benchmark.jsonl (per-claim, both
verdicts) and outputs/narrow_primary_hypothesis_benchmark_report.md.
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

from src.data_loader import load_usable_evidence_from_config
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, format_premise


def _iter_claim_blocks(rec: dict):
    """Every real output-file shape observed in this repo: claims either sit
    directly on the record, or nested one level under a mode key."""
    if isinstance(rec.get("claims"), list):
        yield rec["claims"]
    for key in ("mode_A", "mode_B", "mode_C", "A", "B", "C"):
        sub = rec.get(key)
        if isinstance(sub, dict) and isinstance(sub.get("claims"), list):
            yield sub["claims"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = ap.parse_args()

    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    repo_root = _PROTOTYPE_ROOT.parent.parent
    outputs = _PROTOTYPE_ROOT / "outputs"

    exact_index, all_usable = load_usable_evidence_from_config(config, repo_root)
    by_key = {r.dataset_citation_key: r for r in all_usable}

    seen: dict[tuple, dict] = {}  # (claim_text, evidence_id) -> claim dict (dedup across files)
    for fp in sorted(outputs.glob("*.jsonl")):
        try:
            for line in fp.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                for block in _iter_claim_blocks(rec):
                    for c in block:
                        if not isinstance(c, dict):
                            continue
                        if not (c.get("evidence_text") and c.get("evidence_id") and c.get("claim_text")):
                            continue
                        if c["evidence_id"] not in by_key:
                            continue
                        key = (c["claim_text"], c["evidence_id"])
                        if key not in seen:
                            seen[key] = {"source_file": fp.name, "document_id": rec.get("document_id"), "claim": c}
        except Exception:
            continue

    print(f"Collected {len(seen)} unique (claim_text, evidence_id) real evidence-matched claim pairs")

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=args.device,
    )
    verifier.load()
    framing = config["verification"]["premise_framing"]

    rows = []
    for (claim_text, evidence_id), meta in seen.items():
        c = meta["claim"]
        ev = by_key[evidence_id]
        assertion_text = c.get("assertion_text") or claim_text
        has_narrower = assertion_text != claim_text

        premise = format_premise(
            ev.canonical_text, framing=framing,
            provision_type=ev.provision_type, provision_number=ev.provision_number, act=ev.act,
        )
        full_result = verifier.verify(premise, claim_text)
        narrow_result = verifier.verify(premise, assertion_text) if has_narrower else full_result

        rows.append({
            "source_file": meta["source_file"], "document_id": meta["document_id"],
            "evidence_id": evidence_id, "claim_text": claim_text, "assertion_text": assertion_text,
            "has_narrower_assertion": has_narrower,
            "full_verdict": full_result.label, "full_confidence": full_result.confidence,
            "narrow_verdict": narrow_result.label, "narrow_confidence": narrow_result.confidence,
        })

    out_jsonl = outputs / "narrow_primary_hypothesis_benchmark.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(rows)
    with_narrower = [r for r in rows if r["has_narrower_assertion"]]
    full_dist = Counter(r["full_verdict"] for r in rows)
    narrow_dist = Counter(r["narrow_verdict"] for r in rows)
    changed = [r for r in with_narrower if r["full_verdict"] != r["narrow_verdict"]]
    nei_to_entailed = [r for r in changed if r["full_verdict"] == NOT_ENOUGH_INFORMATION and r["narrow_verdict"] == ENTAILED]
    nei_to_contradicted = [r for r in changed if r["full_verdict"] == NOT_ENOUGH_INFORMATION and r["narrow_verdict"] == CONTRADICTED]
    entailed_to_contradicted = [r for r in changed if r["full_verdict"] == ENTAILED and r["narrow_verdict"] == CONTRADICTED]
    contradicted_to_entailed = [r for r in changed if r["full_verdict"] == CONTRADICTED and r["narrow_verdict"] == ENTAILED]

    md = [
        "# narrow_primary_hypothesis benchmark: full claim_text vs. assertion_text\n\n",
        f"_Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()}_\n\n",
        "**Verification-only re-scoring of existing runs, both under the current production "
        "\"labeled\" premise framing.** Generated fields, extracted claims (including "
        "`assertion_text`) and matched evidence come verbatim from every committed "
        "outputs/*.jsonl file; nothing was regenerated, no source file was modified.\n\n",
        "> Verdicts are a small public NLI model's output against this corpus. They are not "
        "legal-correctness determinations, and no lawyer ground truth exists.\n\n",
        f"- Unique real evidence-matched (claim_text, evidence_id) pairs collected: **{n}**\n",
        f"- Of those, claims with an actually-narrower `assertion_text` (i.e. this change can "
        f"even apply): **{len(with_narrower)}** ({100*len(with_narrower)/n:.1f}%)\n\n",
        "## Verdict distribution (all claims; unaffected claims counted identically in both)\n\n",
        "| Verdict | full claim_text (production) | narrow assertion_text |\n|---|---|---|\n",
    ]
    for lbl in (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION):
        md.append(f"| {lbl} | {full_dist.get(lbl, 0)} | {narrow_dist.get(lbl, 0)} |\n")
    md += [
        f"\n## Claims that changed verdict ({len(changed)} / {len(with_narrower)} claims with a narrower assertion)\n\n",
        f"- NEI -> ENTAILED (candidate coverage win): **{len(nei_to_entailed)}**\n",
        f"- NEI -> CONTRADICTED (candidate new correction trigger): **{len(nei_to_contradicted)}**\n",
        f"- ENTAILED -> CONTRADICTED (**safety-relevant reversal**): **{len(entailed_to_contradicted)}**\n",
        f"- CONTRADICTED -> ENTAILED (**safety-relevant reversal**): **{len(contradicted_to_entailed)}**\n\n",
    ]
    if entailed_to_contradicted or contradicted_to_entailed:
        md.append("### Safety-relevant reversals (inspect manually before ever enabling this default)\n\n")
        for r in (entailed_to_contradicted + contradicted_to_entailed)[:10]:
            md += [
                f"- **{r['evidence_id']}** ({r['source_file']}/{r['document_id']})\n",
                f"  - claim_text: {r['claim_text'][:220]}\n",
                f"  - assertion_text: {r['assertion_text'][:220]}\n",
                f"  - {r['full_verdict']} ({r['full_confidence']:.3f}) -> {r['narrow_verdict']} ({r['narrow_confidence']:.3f})\n",
            ]
    else:
        md.append("None. No claim reversed between the two genuinely-safety-relevant labels "
                   "(ENTAILED<->CONTRADICTED) anywhere in this dataset.\n")

    md.append(f"\n### NEI -> ENTAILED cases (first 10 of {len(nei_to_entailed)}, inspect for spurious entailment)\n\n")
    for r in nei_to_entailed[:10]:
        md += [
            f"- **{r['evidence_id']}** ({r['source_file']}/{r['document_id']})\n",
            f"  - claim_text: {r['claim_text'][:220]}\n",
            f"  - assertion_text: {r['assertion_text'][:220]}\n",
            f"  - confidence: {r['full_confidence']:.3f} -> {r['narrow_confidence']:.3f}\n",
        ]

    (outputs / "narrow_primary_hypothesis_benchmark_report.md").write_text("".join(md), encoding="utf-8")

    print(f"Claims with a narrower assertion_text: {len(with_narrower)}/{n}")
    print(f"Changed verdict: {len(changed)}")
    print(f"NEI->ENTAILED: {len(nei_to_entailed)}, NEI->CONTRADICTED: {len(nei_to_contradicted)}")
    print(f"ENTAILED->CONTRADICTED: {len(entailed_to_contradicted)}, CONTRADICTED->ENTAILED: {len(contradicted_to_entailed)}")
    print(f"\nWrote {out_jsonl}")
    print(f"Wrote {outputs / 'narrow_primary_hypothesis_benchmark_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
