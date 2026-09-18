#!/usr/bin/env python3
"""
Builds CHANGE_IMPACT_AUDIT.md and metrics/change_inventory.csv for the V2 package
from the verified 47-row change inventory produced by the change-mapping workstream.

The evidence grade for each change is DERIVED BY RULE from what actually measures it
(see `grade_for()`), never assigned by impression. The rules are printed in the
document itself so a reader can check them.
"""
from __future__ import annotations

import csv
import shutil
from collections import Counter, OrderedDict
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
SRC_CSV = Path(
    r"C:/Users/VEDANT~1/AppData/Local/Temp/claude/d--Major/"
    r"0bceb748-3051-4f9a-abab-be8dd56574b4/scratchpad/recon/agent3_change_inventory.csv"
)
OUT_MD = _V2_ROOT / "CHANGE_IMPACT_AUDIT.md"
OUT_CSV = _V2_ROOT / "metrics" / "change_inventory.csv"

STATUS_ORDER = [
    "PROMOTED_PRODUCTION",
    "EXPERIMENTAL_NOT_PROMOTED",
    "EVALUATED_AND_REJECTED",
    "INFRASTRUCTURE_ONLY",
    "DOCS_ONLY",
]

STATUS_BLURB = {
    "PROMOTED_PRODUCTION": "Live in the LATEST system.",
    "EXPERIMENTAL_NOT_PROMOTED": "Built and evaluated, deliberately OFF in production. Never describe these as production behaviour.",
    "EVALUATED_AND_REJECTED": "Built, benchmarked, and actively rejected on measured grounds.",
    "INFRASTRUCTURE_ONLY": "Tooling, loading mechanics or experiment scaffolding. No behavioural claim attaches.",
    "DOCS_ONLY": "Documentation. No code behaviour changed.",
}

# V2 fresh results, keyed by a substring of the experiment reference they supersede
# or corroborate. Only fresh, re-executed results appear here.
V2_FRESH = {
    "parser_fix_before_after": (
        "V2 FRESH (n=30 docs): claims resolving to evidence 38 (ORIGINAL 0e37525) -> 54 (223eb9d) "
        "-> 57 (LATEST HEAD); ORIGINAL->LATEST +10/-0 documents, sign test p=0.0020. "
        "The LATEST arm reproduces parser_fix_before_after_n30_v2_postfix.json exactly; the "
        "ORIGINAL arm reproduces 0e37525:outputs/eval_30_report.md exactly."
    ),
    "gold01": (
        "V2 FRESH (n=420 GOLD): acc 0.7333->0.9714, macro F1 0.7487->0.9684, McNemar exact "
        "p=1.58e-30 (100 fixed, 0 broken). REQUIRED CAVEAT: 99/100 of the fixed items lie in the "
        "attributed conditions; on the 269 non-attributed items sign test p=1.0."
    ),
    "controlled_verifier_benchmark": (
        "V2 FRESH (n=420 GOLD): reproduced exactly on a different software stack. See gold01_v2_metrics.json."
    ),
    "verifier_correction_diagnosis": (
        "V2 FRESH corroboration via GOLD-01 rerun; see gold01_v2_metrics.json and the stratification caveat."
    ),
    "evidence_coverage_v0_vs_v1": (
        "V2 FRESH structural recount: 59 -> 136 usable records, 10 -> 22 distinct Acts "
        "(59 + 75 new-usable + 2 promoted = 136). Coverage OUTCOME remains historical."
    ),
    "synthetic_stress": (
        "V2 FRESH (n=59, 2x2 factorial): contradiction recall 0.3559 -> 0.4576, McNemar exact "
        "p=0.0312 (6 discordant). NULL: narrow_primary_hypothesis has exactly zero effect on this set."
    ),
    "threshold_sensitivity": (
        "V2 FRESH full sweep 0.34-0.99 from stored softmax: labeled leads at EVERY threshold "
        "(smallest gap 0.1916); production 0.70 sits on a flat plateau."
    ),
}


def grade_for(exp: str, status: str) -> tuple[str, str]:
    """(evidence_grade, limitation) derived by rule from the measuring experiment."""
    e = (exp or "").strip()
    low = e.lower()
    if not e or low in {"none", "n/a", "-"}:
        if status in {"DOCS_ONLY", "INFRASTRUCTURE_ONLY"}:
            return "NOT_APPLICABLE", "No behavioural claim attaches to this change."
        return ("NOT_MEASURED",
                "No experiment measures this change. Correctness rests on code review and, where "
                "present, regression tests only.")
    has_test = "tests/" in low or "test_" in low
    has_data = any(k in low for k in (
        "outputs/", "evaluation/", "gold01", "gold02", ".json", ".jsonl", ".csv", ".md"))
    if has_test and not has_data:
        return ("ENGINEERING",
                "Regression tests only - demonstrates the failure is blocked, but no data-batch "
                "measurement of how often it occurred in practice.")
    if "gold01" in low or "controlled_verifier_benchmark" in low or "controlled_benchmark" in low:
        return ("GOLD",
                "Gold-labelled benchmark. See the attributed/non-attributed stratification caveat "
                "before quoting the headline.")
    if "synthetic_stress" in low or "gold02" in low or "framing_comparison" in low:
        return ("DETERMINISTIC_SYNTHETIC",
                "Synthetic contradictions built deterministically from real statute text. Probes "
                "detection; says nothing about real-world legal accuracy.")
    if "parser_fix_before_after" in low or "article_abbreviation_fix" in low:
        return ("DETERMINISTIC_SYNTHETIC",
                "Deterministic re-execution over real generated text. 'Resolving to evidence' is a "
                "coverage outcome, NOT a correctness label - there are no gold extraction labels.")
    if "retrieval_signal" in low:
        return ("BEHAVIORAL",
                "Pre-registered adversarial set (21 should-match + 9 adversarial). The 9/9, 3/9, 2/9 "
                "rates are over the 9 adversarial cases, not over 30.")
    if any(k in low for k in ("gpu", "final_gpu_validation", "correction", "narrow_primary",
                              "assertion_aware", "assertion_span", "209", "natural")):
        return ("HISTORICAL",
                "Qwen-dependent and/or natural unlabelled data. RERUN_INFEASIBLE in this session "
                "(no GPU, Qwen uncached). Reused as historical evidence only.")
    return ("BEHAVIORAL", "Observational evidence from committed artifacts; not gold-labelled.")


def v2_note(exp: str) -> str:
    low = (exp or "").lower()
    for key, note in V2_FRESH.items():
        if key in low:
            return note
    return ""


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def trunc(s: str, n: int) -> str:
    s = esc(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def main() -> int:
    rows = list(csv.DictReader(SRC_CSV.open(encoding="utf-8")))
    for r in rows:
        g, lim = grade_for(r.get("experiment_that_measures_it", ""), r.get("status", ""))
        r["evidence_grade"] = g
        r["limitation"] = lim
        r["v2_fresh_result"] = v2_note(r.get("experiment_that_measures_it", ""))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    counts = Counter(r["status"] for r in rows)
    grades = Counter(r["evidence_grade"] for r in rows)
    n_fresh = sum(1 for r in rows if r["v2_fresh_result"])
    n_unmeasured = sum(1 for r in rows if r["evidence_grade"] == "NOT_MEASURED")

    L: list[str] = []
    A = L.append
    A("# CHANGE IMPACT AUDIT — ORIGINAL NyayaMind → LATEST NyayaMind")
    A("")
    A("**V2 package · generated 2026-09-18 · repository `nyayamind-verification`**")
    A("")
    A("Every meaningful change between the original codebase (`0e37525`, 2026-08-13) and HEAD")
    A("(`fb4e98f`, 2026-09-12), traced from git history. **47 changes** across 21 commits — of which")
    A("only 10 commits touched `src/` at all; the rest are documentation, figures and evaluation")
    A("workspace.")
    A("")
    A("Machine-readable version: `metrics/change_inventory.csv` (same 47 rows, all columns).")
    A("")
    A("---")
    A("")
    A("## Summary")
    A("")
    A("| Status | Count | Meaning |")
    A("|---|---:|---|")
    for s in STATUS_ORDER:
        if counts.get(s):
            A(f"| **{s}** | {counts[s]} | {STATUS_BLURB[s]} |")
    A(f"| **TOTAL** | {len(rows)} | |")
    A("")
    A("| Evidence grade | Count |")
    A("|---|---:|")
    for g, c in grades.most_common():
        A(f"| {g} | {c} |")
    A("")
    A(f"- **{n_fresh}** changes are corroborated by an experiment **re-executed fresh for this package**.")
    _plural = "change has" if n_unmeasured == 1 else "changes have"
    A(f"- **{n_unmeasured}** {_plural} **no measuring experiment at all** — listed in full in §3, "
      f"alongside those covered by regression tests only.")
    A("")
    A("### How the evidence grade is assigned (by rule, not by impression)")
    A("")
    A("| Rule | Grade |")
    A("|---|---|")
    A("| Measured on a gold-labelled benchmark (GOLD-01) | `GOLD` |")
    A("| Measured on deterministically-constructed data or by deterministic re-execution | `DETERMINISTIC_SYNTHETIC` |")
    A("| Measured on a pre-registered adversarial set | `BEHAVIORAL` |")
    A("| Qwen-dependent and/or natural unlabelled data (not rerunnable here) | `HISTORICAL` |")
    A("| Covered by regression tests only, with no data-batch measurement | `ENGINEERING` |")
    A("| Nothing measures it | `NOT_MEASURED` |")
    A("| Docs/infrastructure, no behavioural claim | `NOT_APPLICABLE` |")
    A("")
    A("> **Grade measures how well a change is EVIDENCED — isolation, sample size, statistical")
    A("> support. It never measures effect size, and it is never a quality ranking.**")
    A("")
    A("---")
    A("")
    A("## 1. Audit table")
    A("")

    for status in STATUS_ORDER:
        sub = [r for r in rows if r["status"] == status]
        if not sub:
            continue
        A(f"### {status} ({len(sub)})")
        A("")
        A(f"*{STATUS_BLURB[status]}*")
        A("")
        A("| ID | Component | Original behaviour | Problem | Modification | Latest behaviour | Grade |")
        A("|---|---|---|---|---|---|---|")
        for r in sub:
            A("| `{id}` | {comp} | {orig} | {prob} | {mod} | {latest} | `{grade}` |".format(
                id=esc(r["change_id"]),
                comp=trunc(r["component"], 60),
                orig=trunc(r["original_behavior"], 110),
                prob=trunc(r["problem/failure"], 110),
                mod=trunc(r["modification (commit + file)"], 95),
                latest=trunc(r["latest_behavior"], 100),
                grade=r["evidence_grade"],
            ))
        A("")

    A("---")
    A("")
    A("## 2. Changes corroborated by a FRESH V2 experiment")
    A("")
    A("These are the changes whose effect was re-measured on this machine for this package, rather")
    A("than quoted from a historical artifact.")
    A("")
    seen: OrderedDict[str, list[str]] = OrderedDict()
    for r in rows:
        if r["v2_fresh_result"]:
            seen.setdefault(r["v2_fresh_result"], []).append(r["change_id"])
    for note, ids in seen.items():
        A(f"**{', '.join(ids)}**")
        A("")
        A(f"> {note}")
        A("")

    A("---")
    A("")
    A("## 3. Changes with NO measuring experiment")
    A("")
    A("Listed explicitly so that no reader assumes every change carries measured evidence. Most of")
    A("these are safety gates discovered adversarially and covered by regression tests — the tests")
    A("prove the failure is blocked, but nothing measures how often it occurred in real data.")
    A("")
    A("| ID | Component | Why it was changed | What covers it instead |")
    A("|---|---|---|---|")
    for r in rows:
        if r["evidence_grade"] in {"NOT_MEASURED", "ENGINEERING"}:
            A("| `{id}` | {comp} | {prob} | {cov} |".format(
                id=esc(r["change_id"]),
                comp=trunc(r["component"], 55),
                prob=trunc(r["problem/failure"], 95),
                cov=trunc(r["experiment_that_measures_it"] or "nothing", 75),
            ))
    A("")

    A("---")
    A("")
    A("## 4. Code-level discrepancies found during this audit")
    A("")
    A("Found by auditing the LATEST source against its own configuration and documentation.")
    A("Recorded, not fixed — fixing them would mean altering frozen research artifacts.")
    A("")
    A("| ID | Severity | Discrepancy | Consequence |")
    A("|---|---|---|---|")
    A("| **D1** | HIGH | `evidence_matching.fuzzy_method` and 3 sibling keys are **never read**. All four `match_evidence()` call sites in `pipeline.py` pass positional arguments, so `\"jaccard\"` comes from the function default. | **BM25/embedding retrieval is unreachable from production**, whatever the config says. Editing that key changes nothing. The BM25/embedding rejection decision is unaffected — but the config presents a choice that does not exist. |")
    A("| **D2** | MEDIUM | `claim_parsing.citation_regex` and `stopwords` are never read, and the config's regex copy is **stale** — it lacks `Arts?\\.`, the plural `s?`, the number-list grammar and the `Part <roman>` group. | Any manifest or paper that copies the YAML regex would document a parser that does not exist. The config does mark the block informational. |")
    A("| **D3** | MEDIUM | `pipeline.py:1353` hardcodes a **\"59-record\"** corpus disclaimer while the live pool is **136**. | Every output record contradicts its own `usable_evidence_pool_size` field. |")
    A("| **D4** | LOW | `correction.max_attempts`, `correction.max_reverifications` and `evidence_matching.top_k` are never read. | Config suggests tunability that is not wired up. |")
    A("| **D5** | LOW | No `verification.device` key exists; the verifier is CUDA-only by constructor default and must be passed `device=\"cpu\"` explicitly. | Not a defect — a deliberate guard — but it is undocumented in config. |")
    A("| **C-1** | MATERIAL | `config/prototype.yaml` claims four times that flipping the five levers \"exactly reproduces\" pre-2026-08-27 outputs. **False at HEAD**: the negation gate, year-conflict veto, injection guard and ordinal guard landed at `adf54aa` (2026-09-09) and none is config-controllable. | The configuration baseline is **strictly more gated** than the real pre-2026-09-09 system. The year-conflict veto can change which evidence is retrieved, hence the premise, hence the verdict. |")
    A("| **C-2** | MATERIAL | Under the configuration baseline the **sibling-regression gate is silently inactive** (`pipeline.py:947` gates it on a truthy `atomic_scope_check`) while four newer gates stay on. | An \"`atomic_scope_check` on vs off\" comparison is not a clean single-variable comparison — it also toggles a safety net. |")
    A("| **E-1** | LOW | `config/prototype.yaml` describes the pool expansion as \"78 new + the 59 v0 records\" = 137, but the true merged total is **136**. | Correct decomposition, recomputed via the production loader: 59 v0 usable + 75 genuinely-new usable + 2 promoted from unusable = 136. |")
    A("| **P-1** | LOW | Re-executing the **committed** `223eb9d` parser yields **54** claims resolving to evidence where the artifact committed at that same commit records **51**. Component isolation rules out the matcher and loader; the counting rule is identical. | Likely the artifact was generated from a working tree differing slightly from the committed source. **No ORIGINAL→LATEST conclusion depends on it** — both endpoints reproduce their artifacts exactly. |")
    A("")
    A("---")
    A("")
    A("## 5. Reading rules")
    A("")
    A("1. **Never quote an `EXPERIMENTAL_NOT_PROMOTED` change as production behaviour.** Two")
    A("   mechanisms — `verification.assertion_span_primary_hypothesis` and")
    A("   `correction.assertion_aware` — are fully built, benchmarked, and deliberately **OFF**.")
    A("2. **Never present the rejected retrieval methods as an improvement.** BM25 and embedding")
    A("   matching were evaluated and **actively rejected** on safety grounds.")
    A("3. **Four levers were flipped in a single commit** (`100e263`), so their joint effect is")
    A("   confounded in every artifact that postdates it. No additive or interaction effect between")
    A("   levers is claimed anywhere in this package.")
    A("4. **`ENGINEERING` and `NOT_MEASURED` are not failures.** A gate whose only evidence is a")
    A("   regression test is still a real gate; it simply has no data-batch measurement, and this")
    A("   package says so rather than implying one exists.")
    A("5. **The models never changed.** Every difference recorded here is a system, pipeline or")
    A("   configuration change.")
    A("")

    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT_MD} ({OUT_MD.stat().st_size} bytes)")
    print(f"wrote {OUT_CSV} ({OUT_CSV.stat().st_size} bytes)")
    print(f"  {len(rows)} changes | statuses: {dict(counts)}")
    print(f"  grades: {dict(grades)}")
    print(f"  fresh-corroborated: {n_fresh} | not measured: {n_unmeasured}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
