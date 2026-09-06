# Exemplar Cases — Index and Selection Methodology

Eight real system outputs, one per requested category, pulled from already-committed
natural NyayaRAG experiment runs (never synthetic, never invented). This index states
the **selection methodology up front** so the choice is auditable rather than a silent
cherry-pick.

## Selection methodology

1. `find_candidates.py` (this directory) scanned every relevant committed raw
   `outputs/*.jsonl` file and mechanically collected **every** record matching each
   category's structural criterion (e.g. "verdict == CONTRADICTED", "status ==
   correction_scope_violation") — not a hand-search for a flattering example.
2. The full candidate pool for each category is preserved at
   `research/prototype/evaluation/examples/candidate_pool.json` for anyone to
   audit — every case below was chosen from that pool, and the pool itself was not
   filtered for outcome before selection.
3. Within each category's candidate pool, one case was picked for **narrative
   clarity** (a claim/evidence pair a non-specialist reader can follow without
   parsing a 7-citation bundled sentence) — never for a more favorable verdict than
   its neighbors. Where a category's pool contained near-duplicate claims from the
   same document (a bundled sentence produces one claim record per citation), only
   one is shown per document to avoid padding the count.
4. No case here has been reviewed by a lawyer. Every verdict shown is this
   system's own automated output (DeBERTa-v3-base-mnli-fever-anli, third-party
   IndianKanoon-sourced evidence). Read each case as "what the system did," not
   "what the law actually says."

## The eight cases

| # | Category | Case | File |
|---|---|---|---|
| 1 | Genuine CONTRADICTED catch | `1997_1306` / claim c6 | `case_01_contradicted_catch.md` |
| 2 | Successful correction (shipped) | `2003_760` / claim c3 | `case_02_successful_correction.md` |
| 3 | Correction attempted, correctly rejected as unsafe | `2008_2063` / claim c9 | `case_03_rejected_unsafe_correction.md` |
| 4 | Scope violation (unflagged claim damaged) | `2009_865` / claim c2 | `case_04_scope_violation.md` |
| 5 | NO_EVIDENCE (not "legally unsupported") | `2011_625` / claim c5 | `case_05_no_evidence.md` |
| 6 | Evidence gained by the v1 supplement | `1971_200` / claim c3 | `case_06_v1_evidence_gain.md` |
| 7 | Labeled-framing improvement (same claim, bare→labeled) | `1982_49` / claim c1 | `case_07_labeled_framing_improvement.md` |
| 8 | System correctly declines to correct | `2004_1020` / claim c1 | `case_08_correctly_declines.md` |

Structured, machine-readable versions of all eight (identical field values to the
prose write-ups) are in `cases.json`.

## What these cases do NOT show

- They do not establish that the verifier's verdicts are legally correct — no
  lawyer has reviewed any of them (see `research/prototype/outputs/lawyer_annotation_guide.md`:
  that review has not happened).
  _See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._
- They are not a random sample and are not a rate estimate — see
  `research/prototype/archive/2026-08-27_presentation/final_demo_pack/reports/correction_safety_analysis.md` and
  `tables/METRICS_COMPREHENSIVE.csv` for the actual population-level counts each
  category is drawn from.
