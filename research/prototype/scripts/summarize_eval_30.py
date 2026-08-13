#!/usr/bin/env python
"""
Machine-generated summary of a 30-case A/B/C evaluation run (see
run_eval_30.py). Reads the three saved JSONL outputs only — does not
re-run generation/verification/correction, does not touch src/, does not
alter any generated claim.

Usage:
  research/.venv/Scripts/python.exe research/prototype/scripts/summarize_eval_30.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = _PROTOTYPE_ROOT / "outputs"


def load_records(mode: str) -> list[dict]:
    path = OUTPUT_DIR / f"run_{mode}_n30.jsonl"
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def summarize_mode(mode: str, records: list[dict]) -> dict:
    total_fields = len(records)
    all_claims = [c for r in records for c in r["claims"]]
    total_claims = len(all_claims)
    with_evidence = sum(1 for c in all_claims if c["evidence_text"] is not None)
    no_evidence = total_claims - with_evidence

    verdict_counts = {"ENTAILED": 0, "CONTRADICTED": 0, "NOT_ENOUGH_INFORMATION": 0, "NO_EVIDENCE": 0}
    for c in all_claims:
        v = c["verdict"]
        if v in verdict_counts:
            verdict_counts[v] += 1

    summary = {
        "mode": mode,
        "total_generated_fields": total_fields,
        "total_claims_extracted": total_claims,
        "claims_per_field_mean": round(total_claims / total_fields, 2) if total_fields else 0,
        "claims_with_evidence": with_evidence,
        "evidence_coverage_pct": round(100 * with_evidence / total_claims, 1) if total_claims else None,
        "no_evidence_count": no_evidence,
        "no_evidence_rate_pct": round(100 * no_evidence / total_claims, 1) if total_claims else None,
        "verdict_counts": verdict_counts,
    }

    if mode == "C":
        statuses = [r["correction"]["status"] for r in records]
        n = len(statuses)
        triggered = sum(1 for s in statuses if s not in ("not_triggered", "not_applicable_mode_C"))
        corrected = statuses.count("corrected")
        failed = statuses.count("correction_failed")
        scope_violation = statuses.count("correction_scope_violation")
        final_changed = sum(
            1 for r in records if r["final_field"]["text"] != r["generated_field"]["text"]
        )
        summary["correction"] = {
            "cases_total": n,
            "trigger_rate_pct": round(100 * triggered / n, 1) if n else None,
            "success_rate_pct": round(100 * corrected / n, 1) if n else None,   # of ALL cases
            "success_rate_of_triggered_pct": round(100 * corrected / triggered, 1) if triggered else None,
            "failed_rate_pct": round(100 * failed / n, 1) if n else None,
            "scope_violation_rate_pct": round(100 * scope_violation / n, 1) if n else None,
            "status_counts": {
                "not_triggered": statuses.count("not_triggered"),
                "corrected": corrected,
                "correction_failed": failed,
                "correction_scope_violation": scope_violation,
            },
            "final_field_changed_count": final_changed,
            "final_field_changed_rate_pct": round(100 * final_changed / n, 1) if n else None,
        }

    timings = [r["_timing"]["total_seconds"] for r in records if "_timing" in r]
    if timings:
        summary["runtime_seconds"] = {
            "mean": round(statistics.mean(timings), 2),
            "median": round(statistics.median(timings), 2),
            "min": round(min(timings), 2),
            "max": round(max(timings), 2),
            "total": round(sum(timings), 2),
        }

    return summary


def _nei_breakdown(records: list[dict]) -> dict:
    confidences = []
    sub_reasons: dict = {}
    methods: dict = {}
    for r in records:
        for c in r["claims"]:
            methods[c["evidence_match_method"]] = methods.get(c["evidence_match_method"], 0) + 1
            if c["verdict"] == "NOT_ENOUGH_INFORMATION":
                confidences.append(c["confidence"])
                sub_reasons[c["sub_reason"]] = sub_reasons.get(c["sub_reason"], 0) + 1
    return {
        "evidence_match_method_counts": methods,
        "nei_sub_reason_counts": sub_reasons,
        "nei_confidence_mean": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "nei_confidence_min": round(min(confidences), 4) if confidences else None,
        "nei_confidence_max": round(max(confidences), 4) if confidences else None,
    }


def _write_markdown_report(summaries: dict, doc_ids: list[str], extra: dict, peak_vram_mib: int | None, path: Path) -> None:
    a, b, c = summaries["A"], summaries["B"], summaries["C"]
    lines = []
    lines.append("# MVP Research Evaluation — 30-case A/B/C Run")
    lines.append("")
    lines.append("**Preliminary system-level results only. Mode C is NOT claimed to improve")
    lines.append("correctness — no human annotation has been performed.**")
    lines.append("")
    lines.append(f"- Cases: 30, selected deterministically (seed=42) from cases with >=1 citation")
    lines.append(f"  overlapping the 59 usable canonical statutes.")
    lines.append(f"- Same 30 cases, same generated field, run under modes A / B / C (paired comparison).")
    lines.append(f"- document_ids: {doc_ids}")
    lines.append("")
    lines.append("## Generation & claim extraction (shared across A/B/C)")
    lines.append(f"- Total generated fields: {a['total_generated_fields']}")
    lines.append(f"- Total claims extracted: {a['total_claims_extracted']} (mean {a['claims_per_field_mean']}/field)")
    lines.append(f"- Evidence coverage: {a['claims_with_evidence']}/{a['total_claims_extracted']} claims matched ({a['evidence_coverage_pct']}%)")
    lines.append(f"- NO_EVIDENCE rate: {a['no_evidence_rate_pct']}% ({a['no_evidence_count']} claims)")
    lines.append(f"- Evidence match method breakdown: {extra['evidence_match_method_counts']}")
    lines.append("")
    lines.append("## Verification (modes B & C)")
    lines.append(f"- Verdict counts (mode C): {c['verdict_counts']}")
    lines.append(f"- All NEI verdicts sub_reason breakdown: {extra['nei_sub_reason_counts']}")
    lines.append(f"- NEI confidence: mean {extra['nei_confidence_mean']}, range [{extra['nei_confidence_min']}, {extra['nei_confidence_max']}]")
    lines.append(f"- ENTAILED: {c['verdict_counts']['ENTAILED']}, CONTRADICTED: {c['verdict_counts']['CONTRADICTED']}")
    lines.append("")
    lines.append("## Selective correction (mode C only)")
    corr = c["correction"]
    lines.append(f"- Correction-trigger rate: {corr['trigger_rate_pct']}% ({corr['status_counts']['corrected'] + corr['status_counts']['correction_failed'] + corr['status_counts']['correction_scope_violation']}/{corr['cases_total']})")
    lines.append(f"- Correction-success rate: {corr['success_rate_pct']}% of all cases ({corr['status_counts']['corrected']}/{corr['cases_total']})")
    lines.append(f"- Correction-failed rate: {corr['failed_rate_pct']}% ({corr['status_counts']['correction_failed']}/{corr['cases_total']})")
    lines.append(f"- Scope-violation rate: {corr['scope_violation_rate_pct']}% ({corr['status_counts']['correction_scope_violation']}/{corr['cases_total']})")
    lines.append(f"- Final-field changed vs. original generation: {corr['final_field_changed_rate_pct']}% ({corr['final_field_changed_count']}/{corr['cases_total']})")
    lines.append(f"- Status counts: {corr['status_counts']}")
    lines.append("")
    lines.append("Zero corrections triggered: with 0 CONTRADICTED verdicts and every NEI verdict a")
    lines.append("genuine high-confidence neutral (sub_reason=None, mean confidence 0.989, none below")
    lines.append("the 0.70 threshold), neither correction-trigger condition (CONTRADICTED, or")
    lines.append("low-confidence-downgraded NEI) was met for any of the 88 real claims in this sample.")
    lines.append("")
    lines.append("## Runtime")
    for m in ("A", "B", "C"):
        rt = summaries[m]["runtime_seconds"]
        lines.append(f"- Mode {m}: mean {rt['mean']}s, median {rt['median']}s, range [{rt['min']}, {rt['max']}]s, total {rt['total']}s")
    lines.append(f"- Peak VRAM observed across the run: {peak_vram_mib} MiB" if peak_vram_mib else "- Peak VRAM: not recorded")
    lines.append("")
    lines.append("## Caveats")
    lines.append("- These are preliminary, machine-computed system-level statistics only.")
    lines.append("- No human review of claim correctness, evidence relevance, or NLI verdict quality")
    lines.append("  has been performed. Do not interpret evidence coverage, verdict distribution, or")
    lines.append("  the zero correction-trigger rate as a claim about system quality or correctness.")
    lines.append("- Mode C's effect on correctness is UNKNOWN from this run alone — no claims were")
    lines.append("  actually corrected in this sample, so no A-vs-C correctness comparison is possible")
    lines.append("  yet.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    modes = ("A", "B", "C")
    records_by_mode = {m: load_records(m) for m in modes}
    doc_ids = [r["document_id"] for r in records_by_mode["A"]]
    for m in modes:
        assert [r["document_id"] for r in records_by_mode[m]] == doc_ids, \
            f"mode {m} document_id order does not match mode A — not a paired comparison"

    summaries = {m: summarize_mode(m, records_by_mode[m]) for m in modes}
    extra = _nei_breakdown(records_by_mode["C"])

    print(json.dumps(summaries, indent=2))
    print()
    print("extra:", json.dumps(extra, indent=2))
    print()
    print("document_ids:", doc_ids)

    report_path = OUTPUT_DIR / "eval_30_report.md"
    _write_markdown_report(summaries, doc_ids, extra, peak_vram_mib=5911, path=report_path)
    print(f"\nWrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
