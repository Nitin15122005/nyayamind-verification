#!/usr/bin/env python3
"""
Honest CPU re-scoring benchmark for `verification.assertion_span_primary_hypothesis`
(src/pipeline.py: `_assertion_spans_hypothesis()`), mirroring the exact
methodology `scripts/benchmark_narrow_primary_hypothesis.py` used for Stage 4:
scan every committed outputs/*.jsonl file for real "respectively"-pattern
claims (assertion_spans with exactly 2 elements, first matching the claim's
own provision number), and re-score each one under the current production
"labeled" premise framing, comparing:

  BASELINE  -- claim_text (what narrow_primary_hypothesis alone sends for
               these claims today, since assertion_text is left unnarrowed
               by construction for the respectively pattern)
  SPAN      -- the new assertion_spans-based hypothesis
               ("<provision_type> <provision_number> <description>")

Nothing is regenerated; only the deterministic claim_parser + evidence_matcher
+ real DeBERTa verification stages run, on already-generated text. No GPU
required.

Output: outputs/assertion_spans_primary_hypothesis_benchmark.jsonl (per-claim
both verdicts) and outputs/assertion_spans_primary_hypothesis_benchmark_report.md.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import sys
from collections import Counter
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.data_loader import load_usable_evidence_from_config
from src.pipeline import _assertion_spans_hypothesis
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION, format_premise


def _iter_claim_blocks(rec: dict):
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

    seen: dict[tuple, dict] = {}  # (claim_text, evidence_id) -> {claim, source_file, doc_id}
    for fp in sorted(outputs.glob("*.jsonl")):
        try:
            for line in fp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
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
                        spans = c.get("assertion_spans")
                        citation = c.get("citation_extracted") or {}
                        if not (
                            isinstance(spans, list) and len(spans) == 2
                            and c.get("evidence_text") and c.get("evidence_id")
                            and citation.get("provision_number") == spans[0]
                            and spans[1] and spans[1] != c.get("assertion_text")
                        ):
                            continue
                        if c["evidence_id"] not in by_key:
                            continue
                        key = (c["claim_text"], c["evidence_id"], tuple(spans))
                        if key not in seen:
                            seen[key] = {"claim": c, "source_file": fp.name, "doc_id": rec.get("document_id")}
        except Exception:
            continue

    print(f"Found {len(seen)} unique real 'respectively'-pattern claims across committed outputs")

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=args.device,
    )
    verifier.load()
    framing = config["verification"]["premise_framing"]

    rows = []
    for (claim_text, evidence_id, spans_tuple), meta in seen.items():
        c = meta["claim"]
        ev = by_key[evidence_id]
        # `_evidence_provision` is internal bookkeeping, stripped before a
        # claim record is ever written to a committed outputs/*.jsonl file
        # (see pipeline.py's run_case() docstring) -- reconstruct it here
        # from the real EvidenceRecord this claim's evidence_id resolves to,
        # exactly as the live pipeline would have had it in memory.
        c_with_provision = {
            **c,
            "_evidence_provision": {
                "provision_type": ev.provision_type,
                "provision_number": ev.provision_number,
                "act": ev.act,
            },
        }
        span_hypothesis = _assertion_spans_hypothesis(c_with_provision)
        if span_hypothesis is None:
            continue  # defensive; shouldn't happen given the pre-filter above

        premise = format_premise(
            ev.canonical_text, framing=framing,
            provision_type=ev.provision_type, provision_number=ev.provision_number, act=ev.act,
        )
        baseline_result = verifier.verify(premise, claim_text)
        span_result = verifier.verify(premise, span_hypothesis)

        rows.append({
            "source_file": meta["source_file"], "document_id": meta["doc_id"],
            "evidence_id": evidence_id, "claim_text": claim_text,
            "assertion_spans": list(spans_tuple), "span_hypothesis": span_hypothesis,
            "baseline_verdict": baseline_result.label, "baseline_confidence": baseline_result.confidence,
            "span_verdict": span_result.label, "span_confidence": span_result.confidence,
        })

    out_jsonl = outputs / "assertion_spans_primary_hypothesis_benchmark.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(rows)
    baseline_dist = Counter(r["baseline_verdict"] for r in rows)
    span_dist = Counter(r["span_verdict"] for r in rows)
    changed = [r for r in rows if r["baseline_verdict"] != r["span_verdict"]]
    nei_to_entailed = [r for r in changed if r["baseline_verdict"] == NOT_ENOUGH_INFORMATION and r["span_verdict"] == ENTAILED]
    nei_to_contradicted = [r for r in changed if r["baseline_verdict"] == NOT_ENOUGH_INFORMATION and r["span_verdict"] == CONTRADICTED]
    entailed_to_contradicted = [r for r in changed if r["baseline_verdict"] == ENTAILED and r["span_verdict"] == CONTRADICTED]
    contradicted_to_entailed = [r for r in changed if r["baseline_verdict"] == CONTRADICTED and r["span_verdict"] == ENTAILED]
    unsafe_reversals = entailed_to_contradicted + contradicted_to_entailed

    md = [
        "# assertion_span_primary_hypothesis benchmark: claim_text vs. assertion_spans-based hypothesis\n\n",
        f"_Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()}_\n\n",
        "**Verification-only re-scoring of every real 'respectively'-pattern claim found across "
        "every committed outputs/*.jsonl file**, under the current production \"labeled\" premise "
        "framing. Nothing regenerated; only claim_parser/evidence_matcher (already run, read from "
        "committed records) + real DeBERTa verification run fresh, on CPU.\n\n",
        "> Verdicts are a small public NLI model's output against this corpus. They are not "
        "legal-correctness determinations, and no lawyer ground truth exists.\n\n",
        f"- Unique real 'respectively'-pattern claims found and scored: **{n}**\n\n",
        "## Verdict distribution\n\n",
        "| Verdict | BASELINE (claim_text) | SPAN (assertion_spans-based) |\n|---|---|---|\n",
    ]
    for lbl in (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION):
        md.append(f"| {lbl} | {baseline_dist.get(lbl, 0)} | {span_dist.get(lbl, 0)} |\n")
    md += [
        f"\n## Claims that changed verdict ({len(changed)} / {n})\n\n",
        f"- NEI -> ENTAILED (candidate coverage win): **{len(nei_to_entailed)}**\n",
        f"- NEI -> CONTRADICTED (candidate new correction trigger): **{len(nei_to_contradicted)}**\n",
        f"- ENTAILED -> CONTRADICTED (**safety-relevant reversal**): **{len(entailed_to_contradicted)}**\n",
        f"- CONTRADICTED -> ENTAILED (**safety-relevant reversal**): **{len(contradicted_to_entailed)}**\n\n",
    ]
    if unsafe_reversals:
        md.append("### Safety-relevant reversals (inspect before ever enabling this default)\n\n")
        for r in unsafe_reversals[:10]:
            md += [
                f"- **{r['evidence_id']}** ({r['source_file']}/{r['document_id']})\n",
                f"  - claim_text: {r['claim_text'][:200]}\n",
                f"  - span_hypothesis: {r['span_hypothesis']}\n",
                f"  - {r['baseline_verdict']} ({r['baseline_confidence']:.3f}) -> "
                f"{r['span_verdict']} ({r['span_confidence']:.3f})\n",
            ]
    else:
        md.append("None. No claim reversed between the two safety-relevant labels "
                   "(ENTAILED<->CONTRADICTED) anywhere in this dataset.\n")

    md.append(f"\n### NEI -> ENTAILED cases (first 10 of {len(nei_to_entailed)}, inspect for spurious entailment)\n\n")
    for r in nei_to_entailed[:10]:
        md += [
            f"- **{r['evidence_id']}** ({r['source_file']}/{r['document_id']})\n",
            f"  - claim_text: {r['claim_text'][:200]}\n",
            f"  - span_hypothesis: {r['span_hypothesis']}\n",
            f"  - confidence: {r['baseline_confidence']:.3f} -> {r['span_confidence']:.3f}\n",
        ]

    verdict_line = (
        "n too small / no clear signal" if n < 20 else
        ("net positive" if len(nei_to_entailed) > len(nei_to_contradicted) + len(unsafe_reversals) * 3 else "mixed/unclear")
    )
    md.append(
        f"\n## Honest verdict\n\nSample size n={n}. "
        + ("This is a SMALL sample -- treat as directional/inconclusive, not a production decision "
           "by itself.\n" if n < 50 else "\n")
        + f"Unsafe reversals: {len(unsafe_reversals)}. "
        + ("Any unsafe reversal is disqualifying regardless of sample size -- do NOT enable this "
           "default if unsafe_reversals > 0 without first understanding and fixing the cause.\n"
           if unsafe_reversals else "Zero unsafe reversals observed.\n")
    )

    report_path = outputs / "assertion_spans_primary_hypothesis_benchmark_report.md"
    report_path.write_text("".join(md), encoding="utf-8")

    print(f"n={n}, changed={len(changed)}, NEI->ENTAILED={len(nei_to_entailed)}, "
          f"NEI->CONTRADICTED={len(nei_to_contradicted)}, unsafe_reversals={len(unsafe_reversals)}")
    print(f"Wrote {out_jsonl}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
