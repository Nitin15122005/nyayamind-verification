# Canonical Statute Evidence Corpus — v1 supplement

`canonical_statutes_v1.jsonl` + `evidence_audit_v1.jsonl` are an **additive supplement**
to the v0 corpus (`canonical_statutes.jsonl` + `evidence_audit.jsonl`, see `README.md`)
— they are never merged into the v0 files, and v0 remains byte-for-byte unchanged.
Loading v1 is opt-in: `config/prototype.yaml`'s `use_evidence_v1: false` (default)
reproduces exactly the v0-only behaviour every existing committed output in this
project was produced under; setting it `true` merges v1 on top via
`src/data_loader.load_usable_evidence_from_config`.

Built 2026-08-27, as the "Priority 1/6" evidence-expansion pass of the CPU pre-GPU
optimization task. Produced by `scripts/build_evidence_v1.py` from research done by 4
parallel research agents, each independently resolving a disjoint batch of citation
keys, plus 3 corrections to known-bad v0 records the original `README.md` had already
flagged.

## What's in it

| | Count |
|---|---:|
| Total v1 records | 82 |
| Corrections to existing v0 records (same `dataset_citation_key`, replaces on merge) | 3 |
| Genuinely new citation keys | 79 |
| Audit verdict: `VERIFIED_EXACT` (usable by default `usable_evidence_verdicts`) | 79 |
| Audit verdict: `SOURCE_ONLY` (NOT usable by default — same policy as v0) | 3 |

**Net effect on the usable evidence pool when `use_evidence_v1: true`: 59 → 137
records** (59 v0 usable, minus 1 replaced-in-place by its v1 correction, plus 3 v1
corrections, plus 76 newly-usable v1 records = 137; verified directly by loading both
configurations and counting — see `outputs/research_completion_report.md`).

## Target selection (no outcome leakage)

The 79 new citation keys are the next 79 most-frequent citation keys — by real
occurrence count across BOTH NyayaRAG source files (`SCI_56k_multi_5k_...json`,
`SCI_56k_single_5k_...json`), the exact same deterministic, generation-free counting
method `scripts/select_natural_candidates.py` and the original v0 `README.md`'s
top-100 build both used — that were **not already present** in the v0 corpus (v0
covered the top 63 by this method; v1 covers ranks 64-143). Nothing about which claims
a generated summary makes, which verdict the NLI verifier assigns, or any other model
output was used to choose these targets — the ranking is a pure function of NyayaRAG's
own `sections` dict KEYS (never their text values).

## Methodology (identical policy to v0, see `README.md` for full detail)

1. `indiacode.nic.in` (the official Government source) was tried once per research
   batch (4 attempts total) — every attempt returned HTTP 403, exactly reproducing
   v0's documented finding. No further India Code attempts were made.
2. `IndianKanoon.org` was the practical resolution source for all 82 records, exactly
   as in v0. Every `source_url` is a specific, real, individually-verified
   `indiankanoon.org/doc/NNNNNN/` page — never a search-results page, never guessed.
3. `canonical_text` was never taken from NyayaRAG's own `sections` text under any
   circumstance.
4. Where a citation could not be confirmed to genuinely cover the exact Act +
   provision claimed, it was excluded rather than shipped uncertain — 1 citation
   (`Section 3 in The Companies Act, 1956`) was excluded this way; see the batch
   research notes preserved in `outputs/research_completion_report.md`.
5. `text_provenance: "webfetch_verbatim"` for a genuine direct-fetch quote (79
   records); `"websearch_synthesized_summary"` for a search-aggregated but
   URL-pinned result (3 records) — same two-tier distinction as v0.

## Audit policy — narrower than v0's, honestly

v0's `evidence_audit.jsonl` independently RE-FETCHED and hand-compared all 63 records
against their stored `source_url` in a dedicated audit pass. **v1's audit is smaller in
scope**: 8 of the 82 records (~10%, at least one drawn from each of the 4 research
batches) were independently re-fetched and hand-compared in this same session — all 8
matched the researching agent's reported `canonical_text` exactly, with no discrepancy.

Given that clean spot-check result, `evidence_audit_v1.jsonl`'s verdicts are assigned
by a documented, mechanical rule rather than a full independent re-fetch of every
record:
- `text_provenance: "webfetch_verbatim"` + `confidence: "high"` → `VERIFIED_EXACT`
  (matches v0's own definition: a direct fetch, not a paraphrase).
- `text_provenance: "websearch_synthesized_summary"` → `SOURCE_ONLY` (source
  confirmed to exist and be the right provision; exact text not independently
  re-fetched) — **not** included in `usable_evidence_verdicts` by default, the same
  treatment v0 gives its own `SOURCE_ONLY` records.

Each `evidence_audit_v1.jsonl` record's `audit_method` field states plainly whether
that specific record was one of the 8 independently re-fetched this session
(`"independently_refetched_and_spot_checked_this_session"`) or relies on the
researching agent's own build-time provenance
(`"build_time_provenance_only_not_independently_refetched"`). **A full, exhaustive
independent audit of all 82 records — the way v0 eventually got one — has not been
done.** This is the single most important caveat for anyone deciding whether v1 is
ready for a higher-stakes use than development/research.

## Known findings from this build (worth a future maintainer's attention)

- **`Section 417 in The Code of Criminal Procedure, 1973`** is a genuinely distinct
  provision ("Power to appoint place of imprisonment") — **not** the well-known
  "appeal in case of acquittal" Section 417, which was a **1898-Code** provision
  replaced by Section 378 in the 1973 Code. Independently cross-checked before
  recording; flagged here so a future citation for the *other* "Section 417" is not
  mistakenly matched against this record.
- **`Section 28 in The Income Tax Act, 1961`**: as of this build, the Income Tax Act,
  1961 itself is superseded (effective 2026-04-01) by the Income-tax Act, 2025 — newer
  information than v0's own 3 existing Income Tax Act 1961 records reflect (those are
  still stored as `historical_status: "in_force"`). Not corrected in v0 by this task
  (out of scope — v0 is never modified); flagged for a future pass.
- **`Section 106`/`Section 3` in The Indian Evidence Act, 1872** (v1) are marked
  `repealed_nationally_2024-07-01_superseded_by_BSA`, consistent with the 2024 BNS/BNSS/BSA
  transition documented in v0's own `README.md`. v0's own 2 existing Evidence Act
  records (§27, §114) are still stored as `in_force` — an apparent inconsistency
  worth reconciling in a future v0/v1 unification pass, not fixed here.
- **`Section 147`/`Section 148` in The Income Tax Act, 1961** (v1): both substituted
  by the Finance Act, 2021 (w.e.f. 2021-04-01) — the pre-2021 text (what most of this
  project's pre-2021 case law would actually be citing) is materially different and
  was not separately resolved; flagged in `historical_status`.
- **`Section 13` in The Prevention of Corruption Act, 1988** (v1): substituted by Act
  16 of 2018 — pre-2018 case law may cite the original 5-clause version, not the
  2-limb version recorded here; flagged in `historical_status`.

None of these are corpus errors — they are point-in-time / historical-versioning
caveats, flagged exactly as `README.md`'s own "Known limitations" section flags
equivalent issues for v0. No text was altered to work around them.

## Is v1 suitable as GOLD evaluation evidence?

**No — for the same reasons v0 is not**, plus v1's audit is narrower in coverage (§
above). Suitable for the same **development/research** purposes v0 is used for.

## 2026-08-27 independent audit addendum

An independent audit (separate from the build session above) re-fetched **41 of the 82
v1 `source_url`s directly** (50%, vs. the original 8/82 ≈ 10%) — including all 3
records marked `v1_supersedes_v0_record: true` and all 3 `SOURCE_ONLY` records — and
ran a full structural/programmatic pass over all 82 records (schema completeness,
duplicate-key/duplicate-`canonical_text`/duplicate-`source_url` checks, `act_norm`
consistency against `src/claim_parser.normalize_act`, `evidence_matcher` exact-index
collision analysis, and `audit_verdict`-assignment-rule consistency). See
`outputs/evidence_v1_independent_audit.md` for the full report. Result: **no
fabricated or wrong-provision content found**; every independently re-fetched record's
statutory text matched what this file already stored. Two genuine, narrow defects were
found and fixed in place (both logged inline on the affected records via a new
`independent_audit_note` field, and in `evidence_audit_v1.jsonl`'s `notes`):

1. **`Section 256 in The Income Tax Act, 1961`**: `canonical_text` was missing the
   "[Omitted by the National Tax Tribunal Act, 2005...]" bracket that this record's own
   `nyayarag_dataset_text_raw` already carried and that the live source page confirms —
   `historical_status` already correctly said "omitted", but `canonical_text` read as
   if the provision were still operative. Fixed by appending the verified bracket;
   `audit_verdict` unchanged (`VERIFIED_EXACT`).
2. **`Section 2 in The Income Tax Act, 1961`**: `text_provenance` was labeled
   `webfetch_verbatim` but the stored text is a paraphrased description of the
   section's ~48 definitions, not a verbatim quote (verbatim quotation was correctly
   judged impractical at build time; the *label* just didn't reflect that). Relabeled
   `webfetch_summarized_not_verbatim`; `audit_verdict` downgraded `VERIFIED_EXACT` →
   `SOURCE_ONLY` per this corpus's own pre-existing mechanical rule (the same rule
   already applied to every `websearch_synthesized_summary` record — not a new
   double standard).

**Net effect: the default usable pool is 136 records (was 137)** when
`use_evidence_v1: true`. This record was not used as evidence in any already-published
experiment in this project (confirmed by checking `final_gpu_validation_{A,B}.jsonl`'s
`evidence_id` values), so no prior committed or published result is invalidated by this
correction.
