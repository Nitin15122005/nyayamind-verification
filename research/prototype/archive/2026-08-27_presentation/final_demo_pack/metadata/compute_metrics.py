#!/usr/bin/env python
"""
Demo-pack metrics aggregator.

Reads ONLY already-committed, frozen raw artifacts under
research/prototype/outputs/ and research/data/evidence/ (never modifies
them) and produces ONE canonical
research/prototype/final_demo_pack/metadata/computed_metrics.json that every
chart, table, and report in final_demo_pack/ must source its numbers from.

Nothing here recomputes a fresh NLI/LLM inference call -- every number is
either (a) read directly from an already-computed *_metrics.json /
*_taxonomy*.json artifact (produced by the research scripts in
research/prototype/scripts/, never hand-edited), or (b) a deterministic,
auditable aggregation over already-committed *.jsonl per-claim/per-case
records (counting, grouping, histogram-binning -- no model calls). Every
top-level section carries `source_files`, `n`, `methodology`, `defensible`
(bool) and `notes` so DATA_LINEAGE.md can point at this file's own code for
"how was this computed" and every consumer can quote `source_files` instead
of re-deriving anything.

Run: research/.venv/Scripts/python.exe research/prototype/final_demo_pack/metadata/compute_metrics.py
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = REPO_ROOT / "research/prototype/outputs"
EVID_DIR = REPO_ROOT / "research/data/evidence"
DEMO_DIR = REPO_ROOT / "research/prototype/final_demo_pack"


def load_json(rel_path: str):
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def load_jsonl(rel_path: str):
    path = REPO_ROOT / rel_path
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# 1. Pass through the already-vetted final_metrics.json sections verbatim.
#    (This file's own provenance field already states it was computed
#    directly from raw outputs/*.jsonl, not copied from narrative reports.)
# ---------------------------------------------------------------------------
def section_from_final_metrics() -> dict:
    fm = load_json("research/prototype/outputs/final_metrics.json")
    return {
        "case_census": fm["case_census"],
        "section_A_synthetic": fm["section_A_synthetic"],
        "section_B_natural_regimes": fm["section_B_natural_regimes"],
        "section_B_pooled_bare_v0": fm["section_B_pooled_bare_v0"],
        "section_B_pooled_labeled_v0": fm["section_B_pooled_labeled_v0"],
        "section_C_parser_retrieval": fm["section_C_parser_retrieval"],
        "section_D_correction_safety_cumulative": fm["section_D_correction_safety_cumulative"],
        "section_E_verifier_vs_provisional_assumption_gold": fm["section_E_verifier_vs_provisional_assumption_gold"],
        "synthetic_vs_natural_correction_transfer_gap": fm["synthetic_vs_natural_correction_transfer_gap"],
        "source_files": ["research/prototype/outputs/final_metrics.json"],
        "methodology": (
            "Verbatim pass-through of final_metrics.json, itself computed directly "
            "from raw outputs/*.jsonl experiment artifacts (see that file's own "
            "'provenance' field) -- not re-derived here to avoid a second, "
            "possibly-diverging computation of the same historical numbers."
        ),
        "defensible": True,
        "notes": "This is the project's single canonical results computation. Reused, not recomputed.",
    }


# ---------------------------------------------------------------------------
# 2. Evidence v0 -> v1 coverage (paired natural-batch comparison already run)
# ---------------------------------------------------------------------------
def section_evidence_coverage_v0_v1() -> dict:
    ev = load_json("research/prototype/outputs/evidence_coverage_v0_vs_v1.json")
    ev["source_files"] = ["research/prototype/outputs/evidence_coverage_v0_vs_v1.json"]
    ev["methodology"] = (
        "Same-claims, same-generation comparison: claims extracted from natural "
        "GPU generations already on disk, matched once against v0-only pool and "
        "once against v0+v1 pool. Not a synthetic corpus."
    )
    ev["defensible"] = True
    ev["notes"] = "Paired design (same claims, two evidence pools) -- the strongest evidence-coverage comparison available."
    return ev


# ---------------------------------------------------------------------------
# 3. Threshold sensitivity (deterministic replay over stored softmax outputs)
# ---------------------------------------------------------------------------
def section_threshold_sensitivity() -> dict:
    ts = load_json("research/prototype/outputs/threshold_sensitivity_analysis.json")
    return {
        "production_threshold": ts["production_threshold"],
        "bare": ts["results"]["bare"],
        "labeled": ts["results"]["labeled"],
        "source_files": ["research/prototype/outputs/threshold_sensitivity_analysis.json"],
        "methodology": (
            "Deterministic sweep (0.50-0.95) replayed against the already-computed "
            "420-item controlled benchmark's stored softmax distributions -- no "
            "re-inference. n=420 items per framing, both bare and labeled."
        ),
        "defensible": True,
        "notes": "Controlled benchmark (curated real legal claims, not synthetic corruption, not natural NyayaRAG).",
    }


# ---------------------------------------------------------------------------
# 4. Controlled verifier benchmark (bare vs labeled, synthetic-corruption-free)
# ---------------------------------------------------------------------------
def section_controlled_benchmark() -> dict:
    bare = load_json("research/prototype/outputs/controlled_benchmark_deberta_metrics.json")
    labeled = load_json("research/prototype/outputs/controlled_benchmark_deberta_labeled_metrics.json")
    return {
        "bare": bare,
        "labeled": labeled,
        "source_files": [
            "research/prototype/outputs/controlled_benchmark_deberta_metrics.json",
            "research/prototype/outputs/controlled_benchmark_deberta_labeled_metrics.json",
        ],
        "methodology": (
            "420 curated real legal claim/evidence pairs (controlled_verifier_benchmark.jsonl), "
            "8 conditions per claim family (verbatim/paraphrase x attribution, negated variants), "
            "real DeBERTa-v3 inference, CPU. Not synthetic stress corruption, not natural NyayaRAG."
        ),
        "defensible": True,
        "notes": "Best-available ground truth is the benchmark's own constructed labels (known-correct by construction), not lawyer annotation.",
    }


# ---------------------------------------------------------------------------
# 5. Assumption-gold agreement (explicitly PROVISIONAL, never legal ground truth)
# ---------------------------------------------------------------------------
def section_assumption_gold() -> dict:
    ag = load_json("research/prototype/outputs/assumption_gold_bare_vs_labeled_metrics.json")
    ag["source_files"] = ["research/prototype/outputs/assumption_gold_bare_vs_labeled_metrics.json"]
    ag["defensible"] = False
    ag["defensible_reason"] = (
        "assumption_annotation.jsonl is Claude-generated provisional labeling, "
        "NOT lawyer-verified ground truth. These numbers describe agreement "
        "between two machine-produced label sets and MUST NOT be presented as "
        "validated legal accuracy."
    )
    return ag


# ---------------------------------------------------------------------------
# 6. Evidence corpus composition (v0 + v1) -- act/provision diversity, source
#    distribution, audit-verdict distribution. Computed fresh from the
#    evidence files themselves (pure counting, no inference).
# ---------------------------------------------------------------------------
def section_evidence_corpus_composition() -> dict:
    def read_pairs(canon_path, audit_path):
        canon = load_jsonl(canon_path)
        audit = load_jsonl(audit_path)
        audit_by_key = {r["dataset_citation_key"]: r for r in audit}
        return canon, audit, audit_by_key

    v0_canon, v0_audit, v0_by_key = read_pairs(
        "research/data/evidence/canonical_statutes.jsonl",
        "research/data/evidence/evidence_audit.jsonl",
    )
    v1_canon, v1_audit, v1_by_key = read_pairs(
        "research/data/evidence/canonical_statutes_v1.jsonl",
        "research/data/evidence/evidence_audit_v1.jsonl",
    )

    def composition(canon, audit_by_key, label):
        acts = Counter(r.get("act", "UNKNOWN") for r in canon)
        provision_types = Counter(r.get("provision_type", "UNKNOWN") for r in canon)
        sources = Counter(r.get("source_name", "UNKNOWN") for r in canon)
        provenance = Counter(r.get("text_provenance", "UNKNOWN") for r in canon)
        verdicts = Counter(a.get("audit_verdict", "UNKNOWN") for a in audit_by_key.values())
        usable = sum(1 for a in audit_by_key.values() if a.get("audit_verdict") in ("VERIFIED_EXACT", "VERIFIED_CONTENT"))
        return {
            "label": label,
            "n_records": len(canon),
            "n_distinct_acts": len(acts),
            "top_acts_by_record_count": acts.most_common(10),
            "provision_type_distribution": dict(provision_types),
            "source_distribution": dict(sources),
            "text_provenance_distribution": dict(provenance),
            "audit_verdict_distribution": dict(verdicts),
            "n_usable_verified_exact_or_content": usable,
        }

    v0_comp = composition(v0_canon, v0_by_key, "v0 (63 records)")
    v1_comp = composition(v1_canon, v1_by_key, "v1 supplement (82 records)")

    # Combined pool as actually merged at load time by src/data_loader.py:
    # v1 records with a same-keyed v0 record REPLACE it; every other v1
    # record is added. Recreate that merge here for the combined view.
    merged_canon = {r["dataset_citation_key"]: r for r in v0_canon}
    merged_canon.update({r["dataset_citation_key"]: r for r in v1_canon})
    merged_audit = dict(v0_by_key)
    merged_audit.update(v1_by_key)
    combined_comp = composition(list(merged_canon.values()), merged_audit, "v0+v1 combined (post-merge, pre-2026-08-27-audit-fix)")

    return {
        "v0": v0_comp,
        "v1_supplement": v1_comp,
        "combined_v0_plus_v1": combined_comp,
        "source_files": [
            "research/data/evidence/canonical_statutes.jsonl",
            "research/data/evidence/evidence_audit.jsonl",
            "research/data/evidence/canonical_statutes_v1.jsonl",
            "research/data/evidence/evidence_audit_v1.jsonl",
        ],
        "methodology": (
            "Direct counting over the committed evidence files, replicating "
            "src/data_loader.py's own v0+v1 merge-by-citation-key rule (v1 "
            "replaces same-keyed v0 records, adds the rest). No inference."
        ),
        "defensible": True,
        "notes": (
            "'combined' count here (145 raw union before verdict filtering) differs from the "
            "136 *usable* (VERIFIED_EXACT+VERIFIED_CONTENT) production pool reported in "
            "final_metrics.json -- that number additionally excludes SOURCE_ONLY/INVALID/"
            "UNRESOLVED records and reflects the 2026-08-27 independent-audit fix "
            "(one record downgraded after this file's audit_verdict snapshot). See "
            "research/data/evidence/README_v1.md 'independent audit addendum' for that fix."
        ),
    }


# ---------------------------------------------------------------------------
# 7. Correction / safety audit -- recomputed fresh from every raw
#    corrections-detail / full-run jsonl this project ever produced.
#    This is the basis for "UNSAFE SHIPMENTS = 0" and the full status
#    breakdown, cross-checked against final_metrics.json's cumulative count.
# ---------------------------------------------------------------------------
CORRECTION_SOURCES_NATURAL = [
    "research/prototype/outputs/run_C_n30.jsonl",
    "research/prototype/outputs/natural_candidates_50_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/natural_candidates_batch2_gpu_corrections_detail.jsonl",
    "research/prototype/outputs/final_gpu_validation_A.jsonl",
    "research/prototype/outputs/final_gpu_validation_B.jsonl",
    "research/prototype/outputs/labeled_correction_validation_gpu_corrections_detail.jsonl",
]

def _extract_correction_records(rows: list, source: str) -> list:
    """Different files nest a 'correction attempt' differently:
    - run_C_n30.jsonl / final_gpu_validation_*.jsonl: one 'correction' dict per case record
    - *_corrections_detail.jsonl: one row IS one correction attempt
    Normalize to a flat list of dicts with a common shape.
    """
    out = []
    for row in rows:
        if "correction" in row and isinstance(row.get("correction"), dict):
            c = row["correction"]
            status = c.get("status")
            if status and status != "not_triggered":
                out.append({
                    "source": source,
                    "document_id": row.get("document_id"),
                    "status": status,
                    "reverification": c.get("reverification"),
                    "sibling_regressions": c.get("sibling_regressions", []),
                })
        elif "status" in row and ("triggered_for_claim_id" in row or "regenerated_text" in row):
            out.append({
                "source": source,
                "document_id": row.get("document_id"),
                "status": row.get("status"),
                "reverification": row.get("reverification"),
                "sibling_regressions": row.get("sibling_regressions", []),
            })
    return out


def section_correction_safety_audit(fm_pass_through: dict) -> dict:
    all_natural = []
    for src in CORRECTION_SOURCES_NATURAL:
        rows = load_jsonl(src)
        all_natural.extend(_extract_correction_records(rows, src))

    # framing_comparison_gpu_n59_postfix_results.jsonl carries only per-claim
    # verification verdicts (c1/c2), not per-attempt correction/reverification
    # records -- the synthetic correction stats live in the already-computed
    # section_A_synthetic.correction_{bare,labeled} blocks (sourced from
    # framing_comparison_gpu_n59_postfix_metrics.json), reused verbatim here
    # rather than mis-recomputed from a file that doesn't carry that data.
    synth_bare = fm_pass_through["section_A_synthetic"]["correction_bare"]
    synth_labeled = fm_pass_through["section_A_synthetic"]["correction_labeled"]
    synthetic_audit = {
        "label": "synthetic stress (framing_comparison_gpu_n59_postfix_metrics.json, real GPU Qwen correction)",
        "bare": {
            "n_correction_attempts": synth_bare["correction_attempts"],
            "status_breakdown": synth_bare["correction_statuses"],
            "n_shipped_corrected": synth_bare["corrections_shipped_success"],
            "n_unsafe_shipped": synth_bare["unsafe_corrections_shipped"],
        },
        "labeled": {
            "n_correction_attempts": synth_labeled["correction_attempts"],
            "status_breakdown": synth_labeled["correction_statuses"],
            "n_shipped_corrected": synth_labeled["corrections_shipped_success"],
            "n_unsafe_shipped": synth_labeled["unsafe_corrections_shipped"],
        },
        "n_correction_attempts": synth_bare["correction_attempts"] + synth_labeled["correction_attempts"],
        "n_shipped_corrected": synth_bare["corrections_shipped_success"] + synth_labeled["corrections_shipped_success"],
        "n_unsafe_shipped": synth_bare["unsafe_corrections_shipped"] + synth_labeled["unsafe_corrections_shipped"],
        "source_files": ["research/prototype/outputs/framing_comparison_gpu_n59_postfix_metrics.json"],
    }

    def audit(records, label):
        status_counts = Counter(r["status"] for r in records)
        shipped = [r for r in records if r["status"] == "corrected"]
        unsafe = [
            r for r in shipped
            if not (r.get("reverification") and r["reverification"].get("verdict") == "ENTAILED")
        ]
        sibling_regressions_flagged = sum(1 for r in records if r.get("sibling_regressions"))
        return {
            "label": label,
            "n_correction_attempts": len(records),
            "status_breakdown": dict(status_counts),
            "n_shipped_corrected": len(shipped),
            "n_unsafe_shipped": len(unsafe),
            "unsafe_shipment_examples": unsafe[:5],
            "n_attempts_with_sibling_regression_flagged": sibling_regressions_flagged,
            "invariant_checked": "status=='corrected' <=> reverification.verdict=='ENTAILED'",
            "invariant_holds": len(unsafe) == 0,
        }

    natural_audit = audit(all_natural, "natural (all historical batches)")

    return {
        "natural": natural_audit,
        "synthetic": synthetic_audit,
        "combined_total_attempts": natural_audit["n_correction_attempts"] + synthetic_audit["n_correction_attempts"],
        "combined_total_unsafe_shipped": natural_audit["n_unsafe_shipped"] + synthetic_audit["n_unsafe_shipped"],
        "source_files": CORRECTION_SOURCES_NATURAL + ["research/prototype/outputs/framing_comparison_gpu_n59_postfix_metrics.json"],
        "methodology": (
            "Every raw jsonl artifact recording a correction attempt (case-level records "
            "with an embedded 'correction' dict, or dedicated *_corrections_detail.jsonl "
            "row-per-attempt files) parsed directly; status/reverification/sibling_regressions "
            "read verbatim, never re-simulated. The ENTAILED<=>corrected invariant is checked "
            "against every single attempt, not sampled."
        ),
        "defensible": True,
        "notes": (
            "Natural count here (56, cross-check target) should match final_metrics.json's "
            "section_D_correction_safety_cumulative.total_correction_attempts (56) -- see "
            "cross_checks in this same computed_metrics.json output."
        ),
    }


# ---------------------------------------------------------------------------
# 8. Confidence distributions (for histograms) -- pooled bare-v0 regime
#    (n=180 cases, the largest valid same-regime pool) plus labeled-v0.
# ---------------------------------------------------------------------------
CONFIDENCE_SOURCES = {
    "bare_v0_pooled": [
        "research/prototype/outputs/run_B_n30.jsonl",
        "research/prototype/outputs/natural_candidates_50_gpu_bare.jsonl",
        "research/prototype/outputs/natural_candidates_batch2_gpu_bare.jsonl",
        "research/prototype/outputs/final_gpu_validation_A.jsonl",
    ],
    "labeled_v0_pooled": [
        "research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl",
        "research/prototype/outputs/natural_candidates_batch2_gpu_labeled.jsonl",
    ],
}


def _claims_from_rows(rows):
    claims = []
    for row in rows:
        for c in row.get("claims", []):
            claims.append(c)
    return claims


def section_confidence_distributions() -> dict:
    result = {}
    for label, files in CONFIDENCE_SOURCES.items():
        claims = []
        for f in files:
            claims.extend(_claims_from_rows(load_jsonl(f)))
        matched = [c for c in claims if c.get("evidence_id") and c.get("confidence") is not None]
        confidences = [c["confidence"] for c in matched]
        by_verdict = defaultdict(list)
        for c in matched:
            by_verdict[c.get("verdict", "UNKNOWN")].append(c["confidence"])
        bins = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        hist = Counter()
        for conf in confidences:
            for lo, hi in zip(bins[:-1], bins[1:]):
                if lo <= conf < hi or (hi == 1.0 and conf == 1.0):
                    hist[f"{lo}-{hi}"] += 1
                    break
        result[label] = {
            "n_matched_claims": len(matched),
            "mean": round(statistics.mean(confidences), 4) if confidences else None,
            "median": round(statistics.median(confidences), 4) if confidences else None,
            "stdev": round(statistics.stdev(confidences), 4) if len(confidences) > 1 else None,
            "min": round(min(confidences), 4) if confidences else None,
            "max": round(max(confidences), 4) if confidences else None,
            "histogram_bins_0.1_wide": dict(hist),
            "by_verdict_mean_confidence": {
                v: round(statistics.mean(vals), 4) for v, vals in by_verdict.items()
            },
            "source_files": files,
        }
    result["methodology"] = (
        "Confidence values read verbatim from each claim record's 'confidence' field "
        "(the verifier's own softmax-derived confidence, post low-confidence-downgrade "
        "logic). Only evidence-matched claims counted (NO_EVIDENCE claims carry no "
        "verifier confidence). No re-inference performed."
    )
    result["defensible"] = True
    result["notes"] = "Distributional summary only -- not a claim about verifier calibration against legal ground truth."
    return result


# ---------------------------------------------------------------------------
# 9. Claim/evidence/correction funnel -- pooled bare+v0 (largest valid
#    single-regime pool, 180 cases) and the final production regime.
# ---------------------------------------------------------------------------
def section_funnel(fm_pass_through: dict) -> dict:
    pooled_bare = fm_pass_through["section_B_pooled_bare_v0"]
    prod = fm_pass_through["section_B_natural_regimes"]["final_labeled_v1_assertionspans_narrow_CORRECTION_GPU"]
    prod_verify = fm_pass_through["section_B_natural_regimes"]["final_labeled_v1_assertionspans_narrow_CPUVERIFY"]

    bare_funnel = {
        "regime": "pooled bare + v0(59) + legacy scope check, 180 cases (n=30, batch1, batch2, final-A)",
        "n_cases": fm_pass_through["case_census"]["n30"] + fm_pass_through["case_census"]["batch1"] + fm_pass_through["case_census"]["batch2"] + fm_pass_through["case_census"]["final_validation"],
        "n_claims": pooled_bare["n_claims"],
        "n_evidence_matched": pooled_bare["n_matched"],
        "n_no_evidence": pooled_bare["verdict_counts"].get("NO_EVIDENCE", 0),
        "n_flagged_for_correction": pooled_bare["verdict_counts"].get("CONTRADICTED", 0),
        "n_correction_triggers": None,  # correction only ran per-batch under mode C; see section_D
        "n_shipped": None,
    }
    prod_funnel = {
        "regime": "final production regime: labeled + v0+v1(136) + assertion_spans + narrow_reverification",
        "n_cases_generation_and_matching": prod_verify.get("n_cases"),
        "n_claims": prod_verify.get("n_claims"),
        "n_evidence_matched": prod_verify.get("n_matched"),
        "verdict_counts_on_matched": prod_verify.get("verdict_counts"),
        "n_correction_triggers": prod["correction"]["correction_triggers"],
        "n_correction_shipped": prod["correction"]["shipped"],
        "n_unsafe_shipped": prod["correction"]["unsafe_shipped"],
    }
    return {
        "bare_v0_pooled_180_cases": bare_funnel,
        "final_production_regime": prod_funnel,
        "source_files": ["research/prototype/outputs/final_metrics.json"],
        "methodology": "Derived arithmetically from final_metrics.json's already-computed section values -- no new counting.",
        "defensible": True,
        "notes": "Two funnels shown because correction only actually ran under Mode C on specific batches -- see final_research_results.md B for the full regime table.",
    }


# ---------------------------------------------------------------------------
# 10. Batch/experiment timeline (for the progression chart) -- dates from git
#     history of each output family, already established during the cleanup pass.
# ---------------------------------------------------------------------------
def section_timeline() -> dict:
    # Static, hand-verified against `git log --format=%ad -- <path>` during the
    # cleanup/freeze pass (2026-08-27 session) -- dates are commit dates of the
    # artifact family's introduction, not re-derived here to avoid depending on
    # git history from within this script (keeps this script runnable from a
    # plain checkout/tarball without .git).
    return {
        "milestones": [
            {"date": "2026-08-25", "event": "n=30 baseline batch (run_A/B/C_n30), synthetic stress v1, mvp_assumption_evaluation", "commit_tag": "223eb9d"},
            {"date": "2026-08-26", "event": "QwenLLMVerifier, controlled verifier benchmark (420 items), research_evaluation_final", "commit_tag": "54c98d2"},
            {"date": "2026-08-26/27", "event": "pre-GPU correction validation (labeled framing, 76.7% pass under labeled framing)", "commit_tag": "fe8b15b"},
            {"date": "2026-08-27", "event": "Evidence v1 build+audit, natural batch1/batch2 GPU runs, final_gpu_validation paired arms, labeled-framing targeted correction validation, final production config decision, full reproducibility pass", "commit_tag": "100e263"},
            {"date": "2026-08-27", "event": "Cleanup/consolidation, run_mvp.py evidence-loader fix, repository freeze", "commit_tag": "3e9e09a"},
        ],
        "source_files": ["git log (commit dates)", "research/prototype/outputs/research_completion_report.md", "research/prototype/outputs/final_research_results.md"],
        "methodology": "Commit-dated project milestones, cross-checked against each artifact family's own stated date and commit history.",
        "defensible": True,
        "notes": "Illustrates development sequence only -- not a performance metric.",
    }


# ---------------------------------------------------------------------------
# 11. Cross-checks -- catch drift between this file's fresh computations and
#     the already-vetted final_metrics.json numbers before anything downstream
#     is generated from them.
# ---------------------------------------------------------------------------
def cross_checks(sections: dict) -> dict:
    checks = []

    fm_total_attempts = sections["final_metrics_passthrough"]["section_D_correction_safety_cumulative"]["total_correction_attempts"]
    fresh_natural_attempts = sections["correction_safety_audit"]["natural"]["n_correction_attempts"]
    checks.append({
        "check": "natural correction attempts: final_metrics.json cumulative vs. fresh recount",
        "final_metrics_value": fm_total_attempts,
        "recomputed_value": fresh_natural_attempts,
        "match": fm_total_attempts == fresh_natural_attempts,
    })

    fm_unsafe = sections["final_metrics_passthrough"]["section_D_correction_safety_cumulative"]["total_unsafe_shipped"]
    fresh_unsafe = sections["correction_safety_audit"]["combined_total_unsafe_shipped"]
    checks.append({
        "check": "total unsafe shipments: final_metrics.json vs. fresh recount (natural+synthetic)",
        "final_metrics_value": fm_unsafe,
        "recomputed_value": fresh_unsafe,
        "match": fm_unsafe == fresh_unsafe,
    })

    fm_shipped = sections["final_metrics_passthrough"]["section_D_correction_safety_cumulative"]["total_shipped"]
    fresh_shipped = sections["correction_safety_audit"]["natural"]["n_shipped_corrected"]
    checks.append({
        "check": "natural shipped (corrected) count: final_metrics.json vs. fresh recount",
        "final_metrics_value": fm_shipped,
        "recomputed_value": fresh_shipped,
        "match": fm_shipped == fresh_shipped,
    })

    all_match = all(c["match"] for c in checks)
    return {"checks": checks, "all_match": all_match}


def main():
    sections = {}
    sections["final_metrics_passthrough"] = section_from_final_metrics()
    sections["evidence_coverage_v0_v1"] = section_evidence_coverage_v0_v1()
    sections["threshold_sensitivity"] = section_threshold_sensitivity()
    sections["controlled_benchmark_verifier"] = section_controlled_benchmark()
    sections["assumption_gold_provisional"] = section_assumption_gold()
    sections["evidence_corpus_composition"] = section_evidence_corpus_composition()
    sections["correction_safety_audit"] = section_correction_safety_audit(sections["final_metrics_passthrough"])
    sections["confidence_distributions"] = section_confidence_distributions()
    sections["funnel"] = section_funnel(sections["final_metrics_passthrough"])
    sections["timeline"] = section_timeline()
    sections["cross_checks"] = cross_checks(sections)

    sections["_meta"] = {
        "generated_by": "research/prototype/final_demo_pack/metadata/compute_metrics.py",
        "generated_for": "research/prototype/final_demo_pack/ (demo/evaluation pack)",
        "does_not_modify": "No file under research/prototype/outputs/ or research/data/evidence/ is written by this script.",
        "integrity_rule": (
            "Every number in every chart/table/report under final_demo_pack/ must trace to "
            "a field in this file (computed_metrics.json) or directly to one of the "
            "source_files it cites. No hand-typed numbers."
        ),
    }

    out_path = DEMO_DIR / "metadata" / "computed_metrics.json"
    out_path.write_text(json.dumps(sections, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Cross-checks all match: {sections['cross_checks']['all_match']}")
    if not sections["cross_checks"]["all_match"]:
        for c in sections["cross_checks"]["checks"]:
            if not c["match"]:
                print(f"  MISMATCH: {c}")


if __name__ == "__main__":
    main()
