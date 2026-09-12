# Data and Evidence

## Case data

`research/data/nyayarag/CaseText_Statutes/*.json` — from `L-NLProc/NyayaRAG` on Hugging Face
(`3.CaseText_Statutes.zip`). Only `case_text` and the case's own citation **keys** are read;
NyayaRAG's own free-text `sections` values are never treated as evidence anywhere in this
pipeline (`src/data_loader.py`).

## Evidence pools

| Pool | Records | File | Status |
|---|---|---|---|
| v0 | 59 usable (of 63 resolved; `VERIFIED_EXACT`/`VERIFIED_CONTENT` only) | `research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl` | Baseline (v0-only) config |
| v1 (additive) | +82 (136 total usable) | `canonical_statutes_v1.jsonl` + `evidence_audit_v1.jsonl` | Production (`use_evidence_v1=true`), merged ON TOP of v0 at load time, never a replacement |

Full audit methodology and provenance: `research/data/evidence/README.md` (v0),
`README_v1.md` (v1, including a 2026-08-27 independent re-audit addendum).

**Known corpus limitation**: pre-2024-07-01 canonical text for IPC/CrPC-heavy citations (41 of
the top-100). Nationally superseded by the BNS/BNSS as of 2024-07-01 — this corpus reflects
the pre-repeal text.

## Controlled (labeled) benchmarks — the ONLY two labeled datasets in this project

| Dataset | n | Construction | Used for |
|---|---|---|---|
| GOLD-01 (controlled verifier benchmark) | 420 | Deterministically constructed, not hand-labeled | Verifier accuracy/precision/recall/F1/confusion matrices |
| GOLD-02 (synthetic stress) | 59 | Deterministically constructed | Contradiction-detection recall |

Provenance, including SHA-256 hashes: `research/prototype/evaluation/MANIFEST.md`. **These are
the only two datasets in the entire project for which "accuracy," "precision," or "recall" are
legitimate terms.**

## Natural-data datasets (unlabeled — never call these "accuracy")

| Dataset | n | What it can legitimately support |
|---|---|---|
| 209-claim paired natural evaluation | 209 | Evidence coverage (%), paired verdict-distribution shift, McNemar test on the binary "received usable evidence" event |
| 588-record corpus | 588 | Evidence coverage (%), NO_EVIDENCE taxonomy |
| 147-claim natural framing shift | 147 | Verdict distribution shift (bare vs labeled) — a BEHAVIORAL observation, not the same measurement as the GOLD-01 controlled result |
| Fresh n=62 natural GPU batch (narrow_primary_hypothesis) | 62 docs / 32 evidence-matched claims per arm | Verdict distribution shift, correction-trigger/shipping counts |
| n=10 paired assertion-aware correction replay | 10 | Correction-shipping counts, first-failure-stage attribution |
| n=6 real "respectively" claims | 6 (entire population found) | Verdict change under assertion_spans-built hypothesis |
| n=30 retrieval adversarial set | 30 (21 should-match + 9 should-not-match) | Correct-accept/correct-reject rate by fuzzy method — pre-registered, not a labeled ground truth in the GOLD sense, but a deterministic, unambiguous adversarial check |

## Evidence grades used throughout this project

- **A** — strongly supported: real isolation, adequate sample size, statistical test performed.
- **B** — supported: real isolation, smaller sample or reproduction rather than fresh execution.
- **C** — diagnostic/evaluated-not-promoted: real data, but sample too small or purely
  descriptive.
- **D** — (rarely used) weaker support.
- **E** — not isolable: the experiment needed to isolate this factor does not exist anywhere in
  the project; never claim otherwise.

## Explicit warning

**Never describe a natural-data coverage percentage, verdict-distribution shift, or paired
outcome count as "accuracy."** No correctness labels exist for any of the natural-data
datasets above — only the NLI verifier's own statistical output against evidence text, which
is not a legal-correctness determination. This distinction is enforced throughout
`research/prototype/results_phase3/` (see `LIMITATIONS.md` and `RESEARCH_CLAIMS.md`) and must
be preserved in any future documentation.
