#!/usr/bin/env python3
"""
STEP 2 — evaluate a verifier on the CONTROLLED_VERIFIER_BENCHMARK.

Persists the FULL per-item NLI probability distribution, not just the argmax
label and its confidence. The production pipeline records only the argmax, which
is precisely why the "everything is NEI" result could not be diagnosed from the
existing n=30 outputs: a neutral verdict at 0.99 and a neutral verdict that
barely edged out entailment look identical once the distribution is discarded.

Reports, in addition to the usual confusion matrix / P / R / F1 / macro-F1:

  * the ENTAILED 2x2 (attribution x paraphrase), which is the actual instrument
    for "why are paraphrases classified as NEI" — it separates a premise-side
    framing problem from a domain-generalisation problem, and those two have
    completely different fixes;
  * mean entailment/neutral/contradiction mass per condition, so a systematic
    bias shows up as a shifted distribution rather than only as a flipped label;
  * how many verdicts came from the confidence-threshold downgrade rather than
    from the model's own argmax.

Usage:
  python scripts/run_controlled_benchmark.py [--device cpu|cuda] [--limit N]
"""
from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
import time
from collections import defaultdict
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.verifier import (
    NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION,
    format_premise, PREMISE_FRAMINGS,
)

LABELS = [ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION]
SHORT = {ENTAILED: "ENT", CONTRADICTED: "CON", NOT_ENOUGH_INFORMATION: "NEI"}


def compute_metrics(expected: list[str], predicted: list[str]) -> tuple[dict, dict, float]:
    cm = {e: {p: 0 for p in LABELS} for e in LABELS}
    for e, p in zip(expected, predicted):
        cm[e][p] += 1

    per_class, f1s = {}, []
    for lbl in LABELS:
        tp = cm[lbl][lbl]
        fp = sum(cm[o][lbl] for o in LABELS if o != lbl)
        fn = sum(cm[lbl][o] for o in LABELS if o != lbl)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[lbl] = {"precision": prec, "recall": rec, "f1": f1,
                          "support": sum(cm[lbl].values()), "tp": tp, "fp": fp, "fn": fn}
        f1s.append(f1)
    return cm, per_class, sum(f1s) / len(f1s)


def fmt_confusion(cm: dict) -> list[str]:
    out = ["", "Confusion matrix (rows = gold, cols = predicted):",
           f"  {'gold \\ pred':<16}" + "".join(f"{SHORT[l]:>7}" for l in LABELS) + f"{'total':>8}"]
    for e in LABELS:
        row = sum(cm[e].values())
        out.append(f"  {SHORT[e]:<16}" + "".join(f"{cm[e][p]:>7}" for p in LABELS) + f"{row:>8}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--benchmark", default="controlled_verifier_benchmark.jsonl")
    ap.add_argument("--out-prefix", default="controlled_benchmark_deberta")
    ap.add_argument("--premise-framing", default="bare", choices=list(PREMISE_FRAMINGS),
                    help="'bare' = production behaviour (statute text only); "
                         "'labeled' = prepend the provision label to the premise")
    args = ap.parse_args()

    config = yaml.safe_load((_PROTOTYPE_ROOT / "config" / "prototype.yaml").read_text(encoding="utf-8"))
    outputs = _PROTOTYPE_ROOT / "outputs"

    items = [json.loads(l) for l in (outputs / args.benchmark).read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        items = items[: args.limit]
    print(f"Loaded {len(items)} benchmark items from {args.benchmark}", flush=True)

    verifier = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
        device=args.device,
    )
    print(f"Loading {verifier.model_id} on {args.device} ...", flush=True)
    t_load = time.time()
    verifier.load()
    print(f"Loaded in {time.time() - t_load:.1f}s", flush=True)

    results, t0 = [], time.time()
    for i, it in enumerate(items, 1):
        premise = format_premise(
            it["evidence_text"],
            framing=args.premise_framing,
            provision_type=it.get("provision_type"),
            provision_number=it.get("provision_number"),
            act=it.get("act_name"),
        )
        r = verifier.verify(premise, it["hypothesis"])
        results.append({
            "benchmark_id": it["benchmark_id"],
            "evidence_key": it["evidence_key"],
            "condition": it["condition"],
            "expected_label": it["expected_label"],
            "predicted_label": r.label,
            "correct": r.label == it["expected_label"],
            "confidence": r.confidence,
            "sub_reason": r.sub_reason,
            # The whole point: keep the distribution, not just the winner.
            "raw_scores": r.raw_scores,
            "factor_attribution": it["factor_attribution"],
            "factor_paraphrase": it["factor_paraphrase"],
            "verifier_model": r.verifier_model,
            "premise_framing": args.premise_framing,
            "premise": premise,
            "hypothesis": it["hypothesis"],
            "evidence_text": it["evidence_text"],
        })
        if i % 50 == 0 or i == len(items):
            print(f"  {i}/{len(items)}  ({time.time() - t0:.0f}s)", flush=True)
    elapsed = time.time() - t0

    res_path = outputs / f"{args.out_prefix}_results.jsonl"
    with res_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    expected = [r["expected_label"] for r in results]
    predicted = [r["predicted_label"] for r in results]
    cm, per_class, macro_f1 = compute_metrics(expected, predicted)
    accuracy = sum(r["correct"] for r in results) / len(results)

    lines = [
        f"VERIFIER: {verifier.model_id}",
        f"premise_framing={args.premise_framing}",
        f"device={args.device}  items={len(results)}  elapsed={elapsed:.1f}s "
        f"({elapsed / len(results):.2f}s/item)",
        f"confidence_threshold={verifier.confidence_threshold}",
        f"\nOverall accuracy: {accuracy:.3f}    Macro F1: {macro_f1:.3f}",
    ]
    lines += fmt_confusion(cm)
    lines += ["", "Per-class:", f"  {'label':<24}{'prec':>8}{'rec':>8}{'f1':>8}{'support':>9}"]
    for lbl in LABELS:
        m = per_class[lbl]
        lines.append(f"  {lbl:<24}{m['precision']:>8.3f}{m['recall']:>8.3f}{m['f1']:>8.3f}{m['support']:>9}")

    # ---- per-condition behaviour, with mean probability mass -------------
    by_cond = defaultdict(list)
    for r in results:
        by_cond[r["condition"]].append(r)

    lines += ["", "Per-condition accuracy and mean NLI probability mass:",
              f"  {'condition':<26}{'n':>4}{'acc':>7}{'p(ent)':>9}{'p(neu)':>9}{'p(con)':>9}  modal prediction"]
    cond_stats = {}
    for cond in sorted(by_cond):
        rs = by_cond[cond]
        acc = sum(x["correct"] for x in rs) / len(rs)
        pe = sum(x["raw_scores"].get("entailment", 0.0) for x in rs) / len(rs)
        pn = sum(x["raw_scores"].get("neutral", 0.0) for x in rs) / len(rs)
        pc = sum(x["raw_scores"].get("contradiction", 0.0) for x in rs) / len(rs)
        counts = defaultdict(int)
        for x in rs:
            counts[x["predicted_label"]] += 1
        modal = max(counts.items(), key=lambda kv: kv[1])
        cond_stats[cond] = {"n": len(rs), "accuracy": acc, "mean_p_entailment": pe,
                            "mean_p_neutral": pn, "mean_p_contradiction": pc,
                            "prediction_counts": dict(counts)}
        lines.append(f"  {cond:<26}{len(rs):>4}{acc:>7.3f}{pe:>9.3f}{pn:>9.3f}{pc:>9.3f}"
                     f"  {SHORT[modal[0]]} {modal[1]}/{len(rs)}")

    # ---- the 2x2 that answers the research question ---------------------
    quad = {}
    for cond, attr, para in [("E1_verbatim", False, False), ("E2_verbatim_attributed", True, False),
                             ("E3_paraphrase_bare", False, True), ("E4_paraphrase_attributed", True, True)]:
        rs = by_cond.get(cond, [])
        if rs:
            quad[cond] = {"attribution": attr, "paraphrase": para, "n": len(rs),
                          "entailed_recall": sum(x["predicted_label"] == ENTAILED for x in rs) / len(rs),
                          "mean_p_entailment": sum(x["raw_scores"].get("entailment", 0.0) for x in rs) / len(rs)}

    lines += ["", "ENTAILED 2x2 — recall of the ENTAILED label (higher is better):",
              f"  {'':<22}{'bare':>18}{'attributed':>18}"]
    if "E1_verbatim" in quad and "E2_verbatim_attributed" in quad:
        lines.append(f"  {'verbatim':<22}{quad['E1_verbatim']['entailed_recall']:>18.3f}"
                     f"{quad['E2_verbatim_attributed']['entailed_recall']:>18.3f}")
    if "E3_paraphrase_bare" in quad and "E4_paraphrase_attributed" in quad:
        lines.append(f"  {'paraphrased':<22}{quad['E3_paraphrase_bare']['entailed_recall']:>18.3f}"
                     f"{quad['E4_paraphrase_attributed']['entailed_recall']:>18.3f}")

    # Main effects are only comparable on records present in BOTH cells, so the
    # paraphrase contrast is computed on the matched subset rather than across
    # different record sets (E3/E4 exist for fewer records than E1/E2).
    effects = {}
    id_of = lambda r: r["evidence_key"]
    def matched(c_from: str, c_to: str) -> dict | None:
        a = {id_of(r): r for r in by_cond.get(c_from, [])}
        b = {id_of(r): r for r in by_cond.get(c_to, [])}
        keys = sorted(set(a) & set(b))
        if not keys:
            return None
        ra = sum(a[k]["predicted_label"] == ENTAILED for k in keys) / len(keys)
        rb = sum(b[k]["predicted_label"] == ENTAILED for k in keys) / len(keys)
        pa = sum(a[k]["raw_scores"].get("entailment", 0.0) for k in keys) / len(keys)
        pb = sum(b[k]["raw_scores"].get("entailment", 0.0) for k in keys) / len(keys)
        return {"n_matched": len(keys), "from": c_from, "to": c_to,
                "entailed_recall_from": ra, "entailed_recall_to": rb, "delta_recall": rb - ra,
                "mean_p_entailment_from": pa, "mean_p_entailment_to": pb, "delta_p_entailment": pb - pa}

    for name, c_from, c_to in [
        ("attribution_effect_on_verbatim", "E1_verbatim", "E2_verbatim_attributed"),
        ("attribution_effect_on_paraphrase", "E3_paraphrase_bare", "E4_paraphrase_attributed"),
        ("paraphrase_effect_bare", "E1_verbatim", "E3_paraphrase_bare"),
        ("paraphrase_effect_attributed", "E2_verbatim_attributed", "E4_paraphrase_attributed"),
        ("attribution_effect_on_contradiction", "C1_negated_bare", "C2_negated_attributed"),
    ]:
        m = matched(c_from, c_to)
        if m:
            effects[name] = m

    lines += ["", "Matched-pair effects (same evidence records in both cells):"]
    for name, m in effects.items():
        lines.append(f"  {name}: {m['from']} -> {m['to']}  (n={m['n_matched']})")
        lines.append(f"      ENTAILED recall {m['entailed_recall_from']:.3f} -> {m['entailed_recall_to']:.3f}"
                     f"  (delta {m['delta_recall']:+.3f})")
        lines.append(f"      mean p(entail)  {m['mean_p_entailment_from']:.3f} -> {m['mean_p_entailment_to']:.3f}"
                     f"  (delta {m['delta_p_entailment']:+.3f})")

    # ---- how much of the NEI is the threshold, not the model? -----------
    downgraded = [r for r in results if r["sub_reason"] == "low_confidence"]
    lines += ["", f"Verdicts downgraded to NEI by the {verifier.confidence_threshold} confidence "
                  f"threshold: {len(downgraded)}/{len(results)}"]
    if downgraded:
        agree = sum(1 for r in downgraded
                    if max(r["raw_scores"], key=r["raw_scores"].get) == "entailment")
        lines.append(f"  of those, {agree} had entailment as the raw argmax "
                     f"(threshold, not the model, produced the NEI)")

    # ---- error examples --------------------------------------------------
    lines += ["", "Error examples (up to 3 per gold label):"]
    for lbl in LABELS:
        errs = [r for r in results if r["expected_label"] == lbl and not r["correct"]]
        lines.append(f"  gold={lbl}: {len(errs)} errors")
        for r in errs[:3]:
            rs = r["raw_scores"]
            lines.append(f"    [{r['condition']}] -> {r['predicted_label']} "
                         f"(ent={rs.get('entailment', 0):.3f} neu={rs.get('neutral', 0):.3f} "
                         f"con={rs.get('contradiction', 0):.3f})")
            lines.append(f"      EVID : {r['evidence_text'][:110]}")
            lines.append(f"      CLAIM: {r['hypothesis'][:110]}")

    report = "\n".join(lines)
    print("\n" + report, flush=True)

    metrics = {
        "benchmark_tag": "CONTROLLED_VERIFIER_BENCHMARK",
        "benchmark_file": args.benchmark,
        "verifier": verifier.model_id,
        "verifier_kind": "deberta_nli",
        "premise_framing": args.premise_framing,
        "device": args.device,
        "confidence_threshold": verifier.confidence_threshold,
        "n_items": len(results),
        "elapsed_seconds": elapsed,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "confusion_matrix": cm,
        "per_class": per_class,
        "per_condition": cond_stats,
        "entailed_2x2": quad,
        "matched_pair_effects": effects,
        "threshold_downgrades": len(downgraded),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    try:
        import torch, transformers
        metrics["environment"]["torch"] = torch.__version__
        metrics["environment"]["transformers"] = transformers.__version__
    except Exception:
        pass

    met_path = outputs / f"{args.out_prefix}_metrics.json"
    met_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    rep_path = outputs / f"{args.out_prefix}_report.txt"
    rep_path.write_text(report + "\n", encoding="utf-8")

    print(f"\nWrote {res_path}\nWrote {met_path}\nWrote {rep_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
