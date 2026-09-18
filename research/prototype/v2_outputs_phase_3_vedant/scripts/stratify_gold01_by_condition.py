#!/usr/bin/env python3
"""
V2 FRESH — GOLD-01 stratified by benchmark construction condition.

WHY THIS EXISTS — READ BEFORE QUOTING THE HEADLINE
--------------------------------------------------
The headline GOLD-01 result (macro F1 0.749 -> 0.968) is real and reproduces
exactly. But it is NOT evenly distributed across the benchmark, and quoting it
without this stratification overstates what the premise_framing lever does.

GOLD-01 is built from 8 construction conditions. Some are *attributed*: the
hypothesis explicitly names the provision ("Article 12 of the Constitution of
India provides that..."), while the ORIGINAL `bare` premise deliberately omits
that identifier and passes only the statute text. For those items a
well-behaved NLI model MUST answer neutral, because the hypothesis asserts
something (this rule is what Article 12 says) that the premise genuinely does
not contain. The `bare` arm is therefore structurally incapable of passing
them — that is the benchmark's design, not a model defect.

This script partitions the 420 items into ATTRIBUTED vs NON-ATTRIBUTED and
recomputes both arms within each stratum, so a reader can see exactly how much
of the headline comes from each. No new inference is run: it reads the
`condition` field already stored on every prediction by the fresh GOLD-01 run.

CONDITION MAP (from outputs/controlled_verifier_benchmark_meta.json)
    E1_verbatim              59   non-attributed
    E2_verbatim_attributed   59   ATTRIBUTED
    E3_paraphrase_bare       33   non-attributed
    E4_paraphrase_attributed 33   ATTRIBUTED
    C1_negated_bare          59   non-attributed
    C2_negated_attributed    59   ATTRIBUTED
    N1_other_provision       59   non-attributed
    N2_procedural_addition   59   non-attributed

OUTPUT
------
metrics/gold01_v2_stratified_by_condition.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
M = _V2_ROOT / "metrics"

LABELS = ("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION")

ATTRIBUTED_CONDITIONS = {"E2_verbatim_attributed", "E4_paraphrase_attributed", "C2_negated_attributed"}


def metrics(expected, predicted):
    cm = {e: {p: 0 for p in LABELS} for e in LABELS}
    for e, p in zip(expected, predicted):
        cm[e][p] += 1
    f1s, per_class = [], {}
    for lbl in LABELS:
        tp = cm[lbl][lbl]
        fp = sum(cm[o][lbl] for o in LABELS if o != lbl)
        fn = sum(cm[lbl][o] for o in LABELS if o != lbl)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_class[lbl] = {"precision": prec, "recall": rec, "f1": f1,
                          "support": sum(cm[lbl].values())}
        f1s.append(f1)
    n = len(expected)
    acc = sum(1 for e, p in zip(expected, predicted) if e == p) / n if n else 0.0
    present = [l for l in LABELS if per_class[l]["support"] > 0]
    macro_present = sum(per_class[l]["f1"] for l in present) / len(present) if present else 0.0
    return {
        "n": n, "accuracy": acc,
        "macro_f1_all_three_classes": sum(f1s) / len(f1s) if f1s else 0.0,
        "macro_f1_over_present_classes_only": macro_present,
        "classes_present": present,
        "per_class": per_class,
    }


def sign_exact(n_pos, n_neg):
    n = n_pos + n_neg
    if n == 0:
        return {"n_discordant": 0, "improved": 0, "worsened": 0, "p_value": 1.0,
                "test": "exact sign test (two-sided)", "note": "no discordant items"}
    k = min(n_pos, n_neg)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return {"n_discordant": n, "improved": n_pos, "worsened": n_neg,
            "p_value": min(1.0, 2.0 * tail), "test": "exact sign test (two-sided)"}


def load(framing):
    p = M / f"gold01_v2_predictions_{framing}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def analyse(bare_rows, lab_rows, keep):
    idx = [i for i, r in enumerate(bare_rows) if keep(r["condition"])]
    exp = [bare_rows[i]["expected_label"] for i in idx]
    pb = [bare_rows[i]["predicted_label"] for i in idx]
    pl = [lab_rows[i]["predicted_label"] for i in idx]
    cb = [e == p for e, p in zip(exp, pb)]
    cl = [e == p for e, p in zip(exp, pl)]
    fixed = sum(1 for a, b in zip(cb, cl) if (not a) and b)
    broken = sum(1 for a, b in zip(cb, cl) if a and not b)
    mo, ml = metrics(exp, pb), metrics(exp, pl)
    return {
        "n_items": len(idx),
        "conditions_included": sorted({bare_rows[i]["condition"] for i in idx}),
        "original_bare": mo,
        "latest_labeled": ml,
        "delta_accuracy": ml["accuracy"] - mo["accuracy"],
        "items_fixed_by_latest": fixed,
        "items_broken_by_latest": broken,
        "paired_sign_test": sign_exact(fixed, broken),
    }


def main() -> int:
    bare, lab = load("bare"), load("labeled")
    assert [r["benchmark_id"] for r in bare] == [r["benchmark_id"] for r in lab], \
        "prediction files are not aligned item-for-item"

    total_fixed = sum(1 for b, l in zip(bare, lab)
                      if b["expected_label"] != b["predicted_label"]
                      and l["expected_label"] == l["predicted_label"])

    strata = {
        "ALL_420": analyse(bare, lab, lambda c: True),
        "ATTRIBUTED_conditions": analyse(bare, lab, lambda c: c in ATTRIBUTED_CONDITIONS),
        "NON_ATTRIBUTED_conditions": analyse(bare, lab, lambda c: c not in ATTRIBUTED_CONDITIONS),
    }

    per_condition = {}
    for cond in sorted({r["condition"] for r in bare}):
        per_condition[cond] = analyse(bare, lab, lambda c, _c=cond: c == _c)
        per_condition[cond]["is_attributed"] = cond in ATTRIBUTED_CONDITIONS

    attributed_fixed = strata["ATTRIBUTED_conditions"]["items_fixed_by_latest"]
    share = attributed_fixed / total_fixed if total_fixed else 0.0

    out = {
        "artifact_id": "GOLD01-V2-STRATIFIED",
        "measurement": "GOLD-01 ORIGINAL(bare) vs LATEST(labeled), stratified by benchmark construction condition",
        "evidence_grade": "GOLD",
        "no_new_inference": True,
        "source_artifacts": [
            "metrics/gold01_v2_predictions_bare.jsonl",
            "metrics/gold01_v2_predictions_labeled.jsonl",
        ],
        "attributed_conditions": sorted(ATTRIBUTED_CONDITIONS),
        "attributed_definition": (
            "Conditions whose hypothesis explicitly names the provision, while the ORIGINAL "
            "'bare' premise deliberately omits that identifier. The bare arm is structurally "
            "unable to entail these — by benchmark construction, not by model defect."
        ),
        "strata": strata,
        "per_condition": per_condition,
        "headline_attribution": {
            "total_items_fixed_by_latest": total_fixed,
            "of_which_in_attributed_conditions": attributed_fixed,
            "share_of_gain_from_attributed_conditions": share,
            "items_fixed_in_non_attributed_conditions":
                strata["NON_ATTRIBUTED_conditions"]["items_fixed_by_latest"],
            "non_attributed_paired_sign_test":
                strata["NON_ATTRIBUTED_conditions"]["paired_sign_test"],
        },
        "REQUIRED_CAVEAT": (
            f"{share:.1%} of every item the LATEST framing fixes on GOLD-01 lies in the "
            f"attributed conditions, where the ORIGINAL bare premise was constructed to omit "
            f"the very identifier the hypothesis asserts. On the "
            f"{strata['NON_ATTRIBUTED_conditions']['n_items']} non-attributed items the two arms are "
            f"near-identical (accuracy "
            f"{strata['NON_ATTRIBUTED_conditions']['original_bare']['accuracy']:.4f} -> "
            f"{strata['NON_ATTRIBUTED_conditions']['latest_labeled']['accuracy']:.4f}, "
            f"sign test p="
            f"{strata['NON_ATTRIBUTED_conditions']['paired_sign_test']['p_value']:.4f}). "
            f"The headline macro F1 0.749 -> 0.968 must therefore always be reported WITH this "
            f"stratification. It is strong evidence that labeled framing removes a premise/hypothesis "
            f"mismatch; it is NOT evidence of a general +0.22 macro-F1 improvement in legal reasoning."
        ),
        "why_this_still_matters": (
            "Real generated statutory claims ARE overwhelmingly attributed ('According to Section 302 "
            "of the IPC, ...'), so the attributed conditions are the realistic ones, not the artificial "
            "ones. The correct reading is: the ORIGINAL bare premise had a structural mismatch with how "
            "claims are actually phrased, and the LATEST framing fixes it. The caveat is about the SIZE "
            "and GENERALITY of the number, not about whether the change was worth making. Independent "
            "real-data corroboration is required to carry that argument — see the natural-data evidence "
            "in CHANGE_IMPACT_AUDIT.md."
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "v2_outputs_phase_3_vedant/scripts/stratify_gold01_by_condition.py",
    }

    p = M / "gold01_v2_stratified_by_condition.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== GOLD-01 STRATIFIED ===")
    for k, s in strata.items():
        print(f"  {k:28} n={s['n_items']:>3}  acc {s['original_bare']['accuracy']:.4f} -> "
              f"{s['latest_labeled']['accuracy']:.4f}  fixed={s['items_fixed_by_latest']:>3} "
              f"broken={s['items_broken_by_latest']}  p={s['paired_sign_test']['p_value']:.4g}")
    print(f"\n  share of gain from attributed conditions: {share:.1%} "
          f"({attributed_fixed}/{total_fixed})")
    print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
