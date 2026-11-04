#!/usr/bin/env python3
"""Static construct-validity checks for GOLD-01 v2; does not alter the benchmark."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "outputs" / "controlled_verifier_benchmark.jsonl"


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    left, right = tokens(a), tokens(b)
    return len(left & right) / len(left | right) if left or right else 0.0


def main() -> int:
    rows = [json.loads(line) for line in BENCHMARK.read_text(encoding="utf-8").splitlines() if line.strip()]
    source_rows = {r["evidence_key"]: r for r in rows if r["condition"] == "E1_verbatim"}
    source_by_text = {r["evidence_text"]: r for r in source_rows.values()}
    n1 = [r for r in rows if r["condition"] == "N1_other_provision"]
    c1 = [r for r in rows if r["condition"] == "C1_negated_bare"]

    same_act = cross_act = 0
    overlaps = []
    for item in n1:
        target = source_rows[item["evidence_key"]]
        other = source_by_text.get(item["hypothesis"])
        if other is None:
            raise ValueError(f"N1 hypothesis does not map to a source provision: {item['benchmark_id']}")
        same_act += target["act_name"] == other["act_name"]
        cross_act += target["act_name"] != other["act_name"]
        overlaps.append((jaccard(target["evidence_text"], item["hypothesis"]), target, other))

    double_negative = [
        r for r in c1
        if re.search(r"\bNo person\b.{0,500}\bshall not\b", r["hypothesis"], re.I)
    ]
    result = {
        "n_items": len(rows),
        "n_source_provisions": len(source_rows),
        "n1_items": len(n1),
        "n1_same_act_pairs": same_act,
        "n1_cross_act_pairs": cross_act,
        "n1_jaccard_min": min((x[0] for x in overlaps), default=None),
        "n1_jaccard_max": max((x[0] for x in overlaps), default=None),
        "c1_no_person_shall_not_flags": [
            {"benchmark_id": r["benchmark_id"], "evidence_key": r["evidence_key"],
             "hypothesis": r["hypothesis"]} for r in double_negative
        ],
        "negation_rule_counts": dict(Counter(
            rule for r in rows if r["condition"].startswith("C")
            for rule in r["construction_rules"] if rule != "attribution_prefix"
        )),
        "warning": (
            "Static checks only. Different-provision pairing and low lexical overlap "
            "do not validate NEI labels; regex flags do not replace legal-semantic review."
        ),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
