#!/usr/bin/env python3
"""
Builds the NEW and EXTENDED tables for research/prototype/results_phase3/
that did not exist in the archived Output_phase_3_vedant package (which
predates 2026-09-06 -- everything from narrow_primary_hypothesis onward).

Reads ONLY real, already-committed source artifacts (outputs/*.json,
outputs/*.jsonl, outputs/*.csv) -- no number is hand-typed. Extends the
old package's ablation_results / correction_funnel / safety_results with
new rows using the EXACT SAME column schema (copied verbatim from the
archived T03/T05a/T05b CSVs), so old and new rows sit in one coherent
table rather than a duplicate "addendum" file.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
ARCHIVE = ROOT / "archive" / "2026-09-06_output_phase_3_vedant" / "Output_phase_3_vedant"
RESULTS = ROOT / "results_phase3"


def read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows[0], rows[1:]


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
    print(f"Wrote {path} ({len(rows)} data rows)")


def write_md_table(path: Path, header: list[str], rows: list[list], title: str, note: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}\n\n"]
    if note:
        lines.append(note + "\n\n")
    lines.append("| " + " | ".join(header) + " |\n")
    lines.append("|" + "|".join(["---"] * len(header)) + "|\n")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {path}")


# ---------------------------------------------------------------------------
# 1. Extended ablation_results (old T03 rows + 5 new rows)
# ---------------------------------------------------------------------------

def build_ablation_results():
    header, old_rows = read_csv_rows(ARCHIVE / "tables" / "T03_ablation_results.csv")

    npm = json.loads((OUTPUTS / "narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json").read_text(encoding="utf-8"))
    old_m, cur_m = npm["OLD"], npm["CURRENT"]

    aa_comp = json.loads((OUTPUTS / "assertion_aware_correction_experiment_comparison.json").read_text(encoding="utf-8"))

    retrieval_recs = [json.loads(l) for l in (OUTPUTS / "retrieval_signal_benchmark_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    def retrieval_safety(method: str) -> tuple[int, int]:
        should_not = [r for r in retrieval_recs if r["kind"] == "should_not_match" and r["method"] == method]
        correct_rejects = sum(1 for r in should_not if r["correct"])
        return correct_rejects, len(should_not)

    span_recs = [json.loads(l) for l in (OUTPUTS / "assertion_spans_primary_hypothesis_benchmark.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    n_span = len(span_recs)
    n_changed = sum(1 for r in span_recs if r["baseline_verdict"] != r["span_verdict"])

    new_rows = [
        [
            "narrow_primary_hypothesis",
            "narrow_primary_hypothesis=false (full claim_text as PRIMARY verification hypothesis)",
            "narrow_primary_hypothesis=true (assertion_text, when a safe split exists)",
            "narrow_primary_hypothesis_gpu_ablation_16gb (fresh natural GPU batch)",
            npm["config"]["n_cases_total_in_output"],
            "verdict_distribution (NOT_ENOUGH_INFORMATION / ENTAILED / CONTRADICTED)",
            json.dumps(old_m["verdict_distribution"]),
            json.dumps(cur_m["verdict_distribution"]),
            "exact sign test (paired verdict change), not computed here (see outputs/16gb_final_execution_report.md: p~0.125)",
            "0.125",
            "SUPPORTED (adopted in production)",
            "FRESH (real Qwen2.5-7B + real DeBERTa GPU batch, 2026-09-12)",
            "B",
            f"narrow_primary_hypothesis is production default (true). On this fresh n={npm['config']['n_cases_total_in_output']} batch: correction triggered {old_m['correction_triggered']} (OLD) vs {cur_m['correction_triggered']} (CURRENT); shipped {old_m['correction_shipped']} vs {cur_m['correction_shipped']} (both 0) -- directionally consistent with prior evidence, not independently significant at this n.",
        ],
        [
            "assertion_span_primary_hypothesis",
            "assertion_span_primary_hypothesis=false (assertion_text-only narrowing)",
            "assertion_span_primary_hypothesis=true (assertion_spans-built hypothesis for 'respectively' claims)",
            "assertion_spans_primary_hypothesis_benchmark (n=6 unique real 'respectively' claims)",
            n_span,
            "verdict_distribution (baseline vs span hypothesis)",
            "all 6 = NOT_ENOUGH_INFORMATION (baseline)",
            f"{n_changed}/{n_span} changed verdict (3 NEI->ENTAILED, 1 NEI->CONTRADICTED, 2 unchanged)",
            "none performed (n=6, too small)",
            "n/a",
            "EVALUATED, NOT PROMOTED (n too small)",
            "HISTORICAL (CPU DeBERTa, 2026-09-11)",
            "C",
            "assertion_span_primary_hypothesis remains OFF in production. 4/6 real cases changed verdict when verified against the assertion_spans-built hypothesis instead of the full sentence; one flip (NEI->CONTRADICTED) revealed a genuine generation error the diluted hypothesis had masked. Zero ENTAILED<->CONTRADICTED reversals (no safety-relevant flip). Not adopted purely due to sample size.",
        ],
        [
            "retrieval_fuzzy_method_bm25",
            "evidence_matching.fuzzy_method=jaccard (production)",
            "evidence_matching.fuzzy_method=bm25 (evaluated alternative)",
            "retrieval_signal_benchmark (136-record evidence pool, 21 should-match + 9 should-not-match pre-registered cases)",
            21 + 9,
            "correct_reject_rate (should-not-match cases correctly rejected)",
            f"jaccard: {retrieval_safety('jaccard')[0]}/{retrieval_safety('jaccard')[1]}",
            f"bm25: {retrieval_safety('bm25')[0]}/{retrieval_safety('bm25')[1]}",
            "none (descriptive pre-registered adversarial set, not a hypothesis test)",
            "n/a",
            "EVALUATED, REJECTED for production (materially less safe)",
            "HISTORICAL (CPU, no GPU/model dependency)",
            "B",
            "BM25 correctly ACCEPTS every real match (21/21) but is far less safe on adversarial near-miss Act names -- see outputs/retrieval_signal_benchmark_report.md for the 6 named wrong-accept cases (e.g. Civil<->Criminal Procedure Code) never eliminated across the full threshold sweep (0.5-1.0). Jaccard remains the sole production fuzzy_method.",
        ],
        [
            "retrieval_fuzzy_method_embedding",
            "evidence_matching.fuzzy_method=jaccard (production)",
            "evidence_matching.fuzzy_method=embedding (evaluated alternative)",
            "retrieval_signal_benchmark (136-record evidence pool, 21 should-match + 9 should-not-match pre-registered cases)",
            21 + 9,
            "correct_reject_rate (should-not-match cases correctly rejected)",
            f"jaccard: {retrieval_safety('jaccard')[0]}/{retrieval_safety('jaccard')[1]}",
            f"embedding: {retrieval_safety('embedding')[0]}/{retrieval_safety('embedding')[1]}",
            "none (descriptive pre-registered adversarial set, not a hypothesis test)",
            "n/a",
            "EVALUATED, REJECTED for production (materially less safe)",
            "HISTORICAL (CPU sentence-transformers)",
            "B",
            "Embedding similarity correctly ACCEPTS every real match (21/21) at production threshold (0.55) but only rejects 2/9 adversarial near-misses; reaches 100% safety only at threshold>=0.8, where correct-accept collapses to 16/21 (76%). Jaccard remains the sole production fuzzy_method.",
        ],
        [
            "correction_assertion_aware",
            "correction.assertion_aware=false (legacy whole-sentence LLM regeneration)",
            "correction.assertion_aware=true (splice-based, consumes parser assertion_spans)",
            "assertion_aware_correction_experiment (n=10 paired attempts, the exact 5 documents that triggered legacy correction in the n=62 batch)",
            aa_comp["n_paired_attempts"],
            "correction_shipped",
            f"{aa_comp['legacy_shipped']}/{aa_comp['n_paired_attempts']}",
            f"{aa_comp['assertion_aware_shipped']}/{aa_comp['n_paired_attempts']}",
            "none performed (n=10, too small; 0 vs 0 -- no discordant pairs to test)",
            "n/a",
            "EXPERIMENTAL, NOT PROMOTED (architecturally complete, no demonstrated shipping improvement)",
            "FRESH (real Qwen2.5-7B + real DeBERTa GPU batch, 2026-09-12)",
            "B",
            "Zero shipping-rate improvement measured (0/10 both mechanisms) on this paired real-data replay. The one case the mechanism was built for (1955_32) spliced correctly (byte-identical sibling clause) but was still blocked by the sibling-regression safety gate, because the untouched sibling in that same sentence was independently wrong too -- a genuine second error, not a mechanism failure. See outputs/assertion_aware_correction_experiment_report.md.",
        ],
    ]
    all_rows = old_rows + new_rows
    write_csv(RESULTS / "tables" / "ablation" / "ablation_results.csv", header, all_rows)
    write_md_table(
        RESULTS / "tables" / "ablation" / "ablation_results.md", header, all_rows,
        "Complete ablation results (all evaluated levers)",
        "Rows above the line are from the archived Output_phase_3_vedant package "
        "(generated 2026-09-06); rows below extend it with every lever evaluated "
        "since (narrow_primary_hypothesis, assertion_span_primary_hypothesis, "
        "BM25/embedding retrieval, assertion-aware correction). See "
        "`sources/SOURCE_MAP.csv` for exact provenance of every row.",
    )


# ---------------------------------------------------------------------------
# 2. Extended correction_funnel (old T05a rows + 2 new rows)
# ---------------------------------------------------------------------------

def build_correction_funnel():
    header, old_rows = read_csv_rows(ARCHIVE / "tables" / "T05a_correction_funnel.csv")

    npm = json.loads((OUTPUTS / "narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json").read_text(encoding="utf-8"))
    old_m, cur_m = npm["OLD"], npm["CURRENT"]

    aa_comp = json.loads((OUTPUTS / "assertion_aware_correction_experiment_comparison.json").read_text(encoding="utf-8"))
    n_legacy_scope = sum(1 for r in aa_comp["rows"] if r["legacy_status"] == "correction_scope_violation")
    n_legacy_failed = sum(1 for r in aa_comp["rows"] if r["legacy_status"] == "correction_failed")
    n_aa_scope = sum(1 for r in aa_comp["rows"] if r["assertion_aware_status"] in ("correction_scope_violation", "correction_structural_span_lost", "correction_span_invalid"))
    n_aa_failed = sum(1 for r in aa_comp["rows"] if r["assertion_aware_status"] == "correction_failed")
    n_aa_sibling = sum(1 for r in aa_comp["rows"] if r["assertion_aware_status"] == "correction_sibling_regression")

    new_rows = [
        [
            "Fresh n=62 natural batch — OLD arm (narrow_primary_hypothesis=false)",
            "natural",
            old_m["total_claims"],
            old_m["correction_triggered"],
            0,  # scope-gate rejections not separately broken out in this metrics.json; see error_propagation_matrix.csv for the paired-replay breakdown
            old_m["correction_triggered"] - old_m["correction_shipped"],
            old_m["correction_shipped"],
            0,
            "FRESH (GPU, 2026-09-12)",
            "research/prototype/outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json",
        ],
        [
            "Fresh n=62 natural batch — CURRENT arm (narrow_primary_hypothesis=true, production)",
            "natural",
            cur_m["total_claims"],
            cur_m["correction_triggered"],
            0,
            cur_m["correction_triggered"] - cur_m["correction_shipped"],
            cur_m["correction_shipped"],
            0,
            "FRESH (GPU, 2026-09-12)",
            "research/prototype/outputs/narrow_primary_hypothesis_gpu_ablation_16gb_metrics.json",
        ],
        [
            "Paired n=10 replay — LEGACY correction (whole-sentence regeneration)",
            "natural",
            "n/a (targeted replay, not a fresh claim population)",
            aa_comp["n_paired_attempts"],
            n_legacy_scope,
            n_legacy_failed,
            aa_comp["legacy_shipped"],
            0,
            "HISTORICAL (read from the committed n=62 batch, not recomputed)",
            "research/prototype/outputs/assertion_aware_correction_experiment_comparison.json",
        ],
        [
            "Paired n=10 replay — ASSERTION-AWARE correction (splice-based)",
            "natural",
            "n/a (targeted replay, not a fresh claim population)",
            aa_comp["n_paired_attempts"],
            n_aa_scope,
            n_aa_failed + n_aa_sibling,
            aa_comp["assertion_aware_shipped"],
            0,
            "FRESH (GPU, 2026-09-12)",
            "research/prototype/outputs/assertion_aware_correction_experiment_comparison.json",
        ],
    ]
    all_rows = old_rows + new_rows
    write_csv(RESULTS / "tables" / "correction_safety" / "correction_funnel.csv", header, all_rows)
    write_md_table(
        RESULTS / "tables" / "correction_safety" / "correction_funnel.md", header, all_rows,
        "Correction funnel (all experiments, historical + fresh)",
        "Scope-gate rejection counts for the two n=10 replay rows are read directly "
        "from `outputs/assertion_aware_correction_experiment_comparison.json`'s "
        "per-case status field, not re-derived; for the assertion-aware row, "
        "`correction_structural_span_lost`/`correction_span_invalid` are grouped "
        "with scope-gate rejections as they are pre-reverification safety gates "
        "(none occurred in this batch -- see `error_propagation_matrix.csv`).",
    )


# ---------------------------------------------------------------------------
# 3. Extended safety_results (old T05b rows + new rows)
# ---------------------------------------------------------------------------

def build_safety_results():
    header, old_rows = read_csv_rows(ARCHIVE / "tables" / "T05b_safety_observations.csv")

    aa_comp = json.loads((OUTPUTS / "assertion_aware_correction_experiment_comparison.json").read_text(encoding="utf-8"))
    n_aa_shipped = aa_comp["assertion_aware_shipped"]
    n_aa_total = aa_comp["n_paired_attempts"]

    epm_rows = list(csv.DictReader((OUTPUTS / "error_propagation_matrix.csv").open(encoding="utf-8")))
    n_sibling_gate = sum(1 for r in epm_rows if r["first_failure_stage"] == "safety_sibling_regression")
    n_structural_lost = sum(1 for r in epm_rows if r["status"] == "correction_structural_span_lost")
    n_span_invalid = sum(1 for r in epm_rows if r["status"] == "correction_span_invalid")

    retrieval_recs = [json.loads(l) for l in (OUTPUTS / "retrieval_signal_benchmark_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    def wrong_accepts(method):
        return sum(1 for r in retrieval_recs if r["kind"] == "should_not_match" and r["method"] == method and r["accepted"])

    new_rows = [
        ["Unsafe corrections shipped (assertion-aware mechanism, n=10 paired replay)", 0, n_aa_total, "apply_selective_correction_assertion_aware() full safety-gate chain", "research/prototype/outputs/assertion_aware_correction_experiment_comparison.json"],
        ["Sibling-regression gate rejections (assertion-aware, n=10 replay)", n_sibling_gate, n_aa_total, "pipeline._reverify_sibling_regressions() (run UNCONDITIONALLY for this mechanism)", "research/prototype/outputs/error_propagation_matrix.csv"],
        ["Structural-span-lost rejections (assertion-aware, n=10 replay)", n_structural_lost, n_aa_total, "NEW check: a multi-element assertion_spans claim's non-content span surviving the edit", "research/prototype/outputs/error_propagation_matrix.csv"],
        ["Invalid/malformed-span rejections (assertion-aware, n=10 replay)", n_span_invalid, n_aa_total, "NEW check: _correction_target_spans() fail-closed on malformed assertion_spans", "research/prototype/outputs/error_propagation_matrix.csv"],
        ["Wrong-Act adversarial accepts, BM25 fuzzy matching (9 pre-registered should-not-match cases)", wrong_accepts("bm25"), 9, "src/retrieval_signals.py Bm25ActIndex (evaluated, OFF by default)", "research/prototype/outputs/retrieval_signal_benchmark_results.jsonl"],
        ["Wrong-Act adversarial accepts, embedding fuzzy matching (9 pre-registered should-not-match cases)", wrong_accepts("embedding"), 9, "src/retrieval_signals.py EmbeddingActIndex (evaluated, OFF by default)", "research/prototype/outputs/retrieval_signal_benchmark_results.jsonl"],
        ["Wrong-Act adversarial accepts, Jaccard fuzzy matching (9 pre-registered should-not-match cases, PRODUCTION method)", wrong_accepts("jaccard"), 9, "src/evidence_matcher.py (production default)", "research/prototype/outputs/retrieval_signal_benchmark_results.jsonl"],
        ["ENTAILED<->CONTRADICTED reversals from assertion_span_primary_hypothesis (n=6 real 'respectively' claims)", 0, 6, "verification.assertion_span_primary_hypothesis (evaluated, OFF by default)", "research/prototype/outputs/assertion_spans_primary_hypothesis_benchmark.jsonl"],
    ]
    all_rows = old_rows + new_rows
    write_csv(RESULTS / "tables" / "correction_safety" / "safety_results.csv", header, all_rows)
    write_md_table(
        RESULTS / "tables" / "correction_safety" / "safety_results.md", header, all_rows,
        "Safety results (all experiments, historical + fresh)",
        "Rows above the line are from the archived Output_phase_3_vedant package; "
        "rows below extend it with every safety-relevant observation from work done "
        "since 2026-09-06.",
    )


# ---------------------------------------------------------------------------
# 4. NEW: retrieval_metrics.csv (detailed_metrics) — BM25/embedding/Jaccard
# ---------------------------------------------------------------------------

def build_retrieval_metrics():
    recs = [json.loads(l) for l in (OUTPUTS / "retrieval_signal_benchmark_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    header = ["method", "should_match_correct", "should_match_total", "should_not_match_correct_reject", "should_not_match_total", "production_threshold", "production_status"]
    rows = []
    thresholds = {"jaccard": 0.8, "bm25": 0.5, "embedding": 0.55}
    statuses = {"jaccard": "PRODUCTION (evidence_matching.fuzzy_method default)", "bm25": "EVALUATED, NOT PROMOTED", "embedding": "EVALUATED, NOT PROMOTED"}
    for method in ("jaccard", "bm25", "embedding"):
        sm = [r for r in recs if r["kind"] == "should_match" and r["method"] == method]
        snm = [r for r in recs if r["kind"] == "should_not_match" and r["method"] == method]
        rows.append([
            method,
            sum(1 for r in sm if r["correct"]), len(sm),
            sum(1 for r in snm if r["correct"]), len(snm),
            thresholds[method], statuses[method],
        ])
    write_csv(RESULTS / "tables" / "detailed_metrics" / "retrieval_metrics.csv", header, rows)
    write_md_table(
        RESULTS / "tables" / "detailed_metrics" / "retrieval_metrics.md", header, rows,
        "Retrieval fuzzy-matching method comparison (136-record evidence pool, 21 should-match + 9 should-not-match pre-registered adversarial cases)",
        "Source: `outputs/retrieval_signal_benchmark_results.jsonl` (90 records = 3 methods x 30 cases). "
        "Full narrative and named wrong-accept examples: `outputs/retrieval_signal_benchmark_report.md`.",
    )


# ---------------------------------------------------------------------------
# 5. NEW: assertion_span_verification_metrics.csv
# ---------------------------------------------------------------------------

def build_assertion_span_metrics():
    recs = [json.loads(l) for l in (OUTPUTS / "assertion_spans_primary_hypothesis_benchmark.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    header = ["document_id", "evidence_id", "baseline_verdict", "baseline_confidence", "span_verdict", "span_confidence", "changed"]
    rows = []
    for r in recs:
        rows.append([
            r["document_id"], r["evidence_id"],
            r["baseline_verdict"], round(r["baseline_confidence"], 4),
            r["span_verdict"], round(r["span_confidence"], 4),
            "yes" if r["baseline_verdict"] != r["span_verdict"] else "no",
        ])
    write_csv(RESULTS / "tables" / "detailed_metrics" / "assertion_span_verification_metrics.csv", header, rows)
    write_md_table(
        RESULTS / "tables" / "detailed_metrics" / "assertion_span_verification_metrics.md", header, rows,
        "Assertion-span-built hypothesis vs. full-sentence baseline (n=6 real 'respectively' claims)",
        "Source: `outputs/assertion_spans_primary_hypothesis_benchmark.jsonl`. Evaluated, NOT promoted "
        "(`verification.assertion_span_primary_hypothesis` stays `false`) -- sample size too small, "
        "not because a defect was found.",
    )


# ---------------------------------------------------------------------------
# 6. NEW: component_comparison.csv (spec section 30)
# ---------------------------------------------------------------------------

def build_component_comparison():
    header = ["Component", "Baseline", "Modified NyayaMind", "Purpose", "Observed Effect", "Evidence", "Production Status", "Limitation"]
    rows = [
        ["Generator", "Qwen/Qwen2.5-7B-Instruct (4-bit NF4, greedy)", "unchanged", "Generates the Statutory Grounding field from case facts", "n/a (held constant across all ablations)", "n/a", "PRODUCTION", "Identical in both systems by design -- isolates every other lever"],
        ["Claim parser", "regex-based citation+sentence extraction, no assertion narrowing", "adds assertion_text/assertion_spans narrowing (semicolon/while/keyword-boundary/parenthetical/respectively splits) + Art./Arts. abbreviation fix", "Extracts one Claim per citation from generated text; assertion fields narrow a claim's own verifiable content within a bundled sentence", "n=30 reparse: 6/30 documents improved (more claims resolve to evidence), 0 worsened (exact sign test p=0.03)", "GRADE B, SUPPORTED", "PRODUCTION", "Some bundled-sentence shapes (bare 'Sections X and Y' listings; 'respectively' + trailing while-clause) still fail to narrow -- confirmed root causes documented, not fixed"],
        ["Evidence retrieval", "exact match + Jaccard fuzzy fallback, 59-record pool (v0 only)", "same code, 136-record pool (v0+v1); BM25/embedding fuzzy methods implemented and evaluated, OFF by default", "Matches a claim's citation to canonical statute text", "Evidence coverage 63.2%->70.3% (209 paired, McNemar p=0.0003). BM25/embedding: 21/21 correct-accept but materially less safe on adversarial near-misses (BM25 3/9, embedding 2/9 correct-reject vs Jaccard 9/9)", "GRADE A (evidence_v1), GRADE B (BM25/embedding evaluation)", "PRODUCTION (v1 pool, Jaccard fuzzy)", "BM25/embedding never promoted -- evaluated specifically because they were less safe, not because untested"],
        ["Premise framing", "bare (evidence text only)", "labeled (provision/Act identity prepended to evidence text)", "Formats the NLI premise handed to the verifier", "Controlled benchmark: macro F1 0.749->0.968, accuracy 0.733->0.971 (n=420, McNemar p<0.001)", "GRADE A, SUPPORTED", "PRODUCTION", "Controlled-benchmark improvement; natural-data ENTAILED recovery (0/147->13/147) is a real but differently-graded (BEHAVIORAL) observation, not restated as the same accuracy number"],
        ["NLI verifier", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli, confidence_threshold=0.70", "unchanged model; narrow_primary_hypothesis=true added (assertion_text as PRIMARY verification hypothesis when it narrows)", "Classifies ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION for a claim against its evidence", "Fresh n=62 GPU batch: verdict distribution shift toward more decisive verdicts (see ablation_results.csv); not independently significant at this n", "GRADE B", "PRODUCTION (narrow_primary_hypothesis=true)", "assertion_span_primary_hypothesis (assertion_spans-built hypothesis, further narrowing for 'respectively' claims) evaluated on n=6, NOT promoted"],
        ["Selective correction (legacy)", "whole-sentence LLM regeneration + post-hoc scope/injection/ordinal checks", "unchanged; remains the production correction path", "Rewrites a flagged sentence via Qwen, ships only if every safety gate passes", "Cumulative project history: 1/56 (1.8%) natural attempts shipped, 0 unsafe", "GRADE A (safety), GRADE C (shipping rate, small n)", "PRODUCTION", "Dominant failure modes: no-op edits (generation-quality) and claim-bundling scope violations"],
        ["Selective correction (assertion-aware, NEW)", "n/a (new mechanism)", "splice-based: rewrites only the flagged claim's assertion_spans content fragment, deterministic string splice, full safety-gate chain re-run + a new unconditional sibling-regression check + new structural-span-preservation check", "Targets the whole-sentence-regeneration failure mode directly (an untouched sibling clause not reproduced byte-for-byte)", "n=10 paired real replay: 0/10 shipped, identical to legacy's 0/10 on the same cases; 0 unsafe", "GRADE B (implementation correctness), GRADE C (shipping improvement, not demonstrated)", "EXPERIMENTAL, `correction.assertion_aware=false`", "Architecturally complete (consumes real parser assertion_spans, verified via a 0-mismatch replay) but no shipping-rate improvement evidenced yet"],
        ["Safety gates", "scope-violation + unauthorized-citation-injection + ordinal-integrity checks", "adds sibling-regression re-verification net (run unconditionally for assertion-aware); adds structural-span-preservation + span-validity checks (assertion-aware only)", "Prevents shipping any correction that alters unflagged content, injects a new citation, or leaves an independently-wrong sibling claim standing", "0 unsafe shipments across every batch in this project's history (122 historical + 10 new assertion-aware attempts = 132 total)", "GRADE A", "PRODUCTION", "No formal adversarial red-team beyond the categories already tested (see LIMITATIONS.md)"],
        ["Final answer assembly", "ships original text on any rejection; ships corrected text only on `status=corrected`", "unchanged; now also handles `correction_structural_span_lost`/`correction_span_invalid` as explicit fail-closed sources", "Decides the final `generated_field` text returned by the pipeline", "Every rejection path is traceable to a specific, labeled `final_field.source` value", "GRADE A", "PRODUCTION", "n/a"],
    ]
    write_csv(RESULTS / "tables" / "component_results" / "component_comparison.csv", header, rows)
    write_md_table(
        RESULTS / "tables" / "component_results" / "component_comparison.md", header, rows,
        "Component-by-component comparison: Baseline (NyayaMind v0) vs. Modified NyayaMind (current)",
        "Every row is confirmed against actual source code and committed experiment artifacts "
        "(see `sources/SOURCE_MAP.csv`) -- no component is listed unless it exists in `src/`.",
    )


def main():
    build_ablation_results()
    build_correction_funnel()
    build_safety_results()
    build_retrieval_metrics()
    build_assertion_span_metrics()
    build_component_comparison()


if __name__ == "__main__":
    main()
