"""Paired analysis helpers; correctness requires an explicit gold label."""
from __future__ import annotations
import math


def pair_predictions(baseline, v2, gold=None):
    b = {r["id"]: r for r in baseline}
    v = {r["id"]: r for r in v2}
    if b.keys() != v.keys():
        raise ValueError("paired predictions must have identical IDs")
    rows = []
    for key in b:
        bp, vp = b[key]["predicted_label"], v[key]["predicted_label"]
        truth = gold.get(key) if gold else b[key].get("expected_label")
        abstentions = {"NOT_ENOUGH_INFORMATION", "NO_EVIDENCE"}
        if truth is None:
            category = ("both_abstain" if bp == vp and bp in abstentions else
                        "both_agree" if bp == vp else "model_disagreement_ground_truth_unavailable")
        elif bp == vp:
            category = "both_abstain" if bp in abstentions else "both_agree"
        else:
            bc, vc = bp == truth, vp == truth
            category = ("v2_improves" if vc else "v2_changes_correct_to_incorrect" if bc
                        else "baseline_changes_correct_to_incorrect" if vc else "both_fail")
        rows.append({"id": key, "gold_label": truth, "baseline": bp, "v2": vp, "category": category})
    return rows


def mcnemar_exact(baseline, v2, gold):
    """Exact two-sided McNemar test on paired correct/incorrect outcomes."""
    b = {r["id"]: r["predicted_label"] for r in baseline}
    v = {r["id"]: r["predicted_label"] for r in v2}
    if b.keys() != v.keys() or b.keys() != gold.keys():
        raise ValueError("baseline, v2, and gold IDs must match")
    b_only = sum(b[k] == gold[k] and v[k] != gold[k] for k in b)
    v_only = sum(v[k] == gold[k] and b[k] != gold[k] for k in b)
    n = b_only + v_only
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b_only, v_only) + 1)) / (2 ** n)) if n else 1.0
    return {"baseline_only_correct": b_only, "v2_only_correct": v_only,
            "discordant_pairs": n, "exact_two_sided_p": p, "n": len(b)}
