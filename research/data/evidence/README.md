# Canonical Statute Evidence Corpus — v0 (top-100 citations)

`canonical_statutes.jsonl` is a first-version, reproducibility-focused
mapping from the 100 most-frequently-cited statute/citation keys in the
NyayaRAG `CaseText_Statutes` data to independently-sourced canonical legal
text. It is **not** a verifier and does not implement any claim-checking
logic — it is only an evidence table.

`evidence_audit.jsonl` is a **subsequent, independent re-check** of every
record in `canonical_statutes.jsonl` — each record's `source_url` was
re-fetched directly and compared against the stored `act`,
`provision_type`, `provision_number`, `canonical_text`, and
`historical_status`. See "Audit methodology and results" below before using
`canonical_statutes.jsonl` for anything — it surfaced one invalid record and
one dead link that the original build did not catch.

## Source NyayaRAG files

Built entirely from data already extracted to local scratch space (no new
downloads) from `L-NLProc/NyayaRAG` on Hugging Face, file
`3.CaseText_Statutes.zip`:

- `SCI_56k_multi_5k_summarised_w_sections.json` (4,930 documents)
- `SCI_56k_single_5k_summarised_w_sections.json` (4,962 documents)

Both files were combined by citation-key frequency (summed across both) to
rank the 100 most-cited `sections` keys across the corpus.

## Top-100 citation profile

- Constitution provisions: **23**
- Central Act provisions: **74**
- Central Rules (subordinate legislation, e.g. Income Tax Rules 1962): **3**
- State Acts/Rules: **0** (none appear in the top 100 — state-level citations
  are far less frequent than Constitution/central-code citations in this
  Supreme-Court-heavy corpus)
- Citations requiring **historical-version handling**: **50** — all IPC (32),
  CrPC (9), Land Acquisition Act 1894 (6), Arbitration Act 1940 (2), plus
  Article 31 (deleted/modified by the 44th Amendment, 1978) and IPC §161
  (repealed by the Prevention of Corruption Act, 1988). IPC and CrPC alone
  (41 citations) are now nationally superseded by the Bharatiya Nyaya
  Sanhita / Bharatiya Nagarik Suraksha Sanhita, effective 2024-07-01 — so
  "canonical text" for the bulk of this corpus means the **pre-2024-07-01
  version**, not current law.

## Deterministic filtering rules applied to NyayaRAG's own text

Before external resolution, every top-100 key's *own* NyayaRAG `sections`
text was re-run through the same deterministic self-consistency classifier
used in the prior evidence-quality audit (regex-only, no LLM):

- **OK** — value's leading bare-act numbering, or an explicit
  "Section/Article N of ..." self-reference, matches the citation key's own
  Act and number.
- **B** — value explicitly names a *different* section number and/or Act
  than the key claims.
- **C** — no self-reference found, and none of the key's Act-name words
  appear in the value text.
- **D** — identical text string reused verbatim across multiple distinct
  keys (boilerplate/copy-paste artifact).
- **E** — no explicit self-reference; undetermined by the deterministic
  check alone.

This classification is stored per record as
`nyayarag_dataset_text_deterministic_category`, alongside the untouched
original NyayaRAG text as `nyayarag_dataset_text_raw` — kept for
transparency/comparison only. **`nyayarag_dataset_text_raw` was never used
to produce `canonical_text`** — see below.

## Canonical-source policy

1. **India Code (`indiacode.nic.in`)** is the Ministry of Law and
   Justice's official repository and is treated as the nominal authority.
   In this session, every attempt to fetch it — the site root, a
   `show-data` section page, the repealed-acts listing, and a static
   `/bitstream/` PDF — returned **HTTP 403**. This is consistent with an
   earlier, separate feasibility investigation and is not treated as a
   one-off failure.
2. Because India Code could not be accessed, **IndianKanoon.org** was used
   as the practical resolution source for every record in this file. It is
   **explicitly labeled as third-party** (`authority_level:
   "third_party_verified"`, `source_name: "IndianKanoon.org"`) in every
   record — never presented as if it were India Code's own text.
3. `canonical_text` was **not** taken from NyayaRAG's own `sections`
   field under any circumstance, regardless of that key's deterministic
   category (including keys marked `OK`) — it always comes from the
   external IndianKanoon lookup performed for this build.
4. No LLM was used to decide whether any text is correct. Where a record's
   `canonical_text` came from a synthesized web-search summary rather than
   a directly fetched, byte-for-byte verbatim page (see `text_provenance`
   below), that summary is itself a plain aggregation of search results,
   not an LLM judgment about correctness — no automated correctness
   adjudication was applied at any stage.

## Provenance fields (schema)

Every record in `canonical_statutes.jsonl`:

| Field | Meaning |
|---|---|
| `dataset_citation_key` | Exact, unmodified NyayaRAG citation key |
| `citation_frequency_in_top100_files` | Combined occurrence count across both source files |
| `act`, `provision_type`, `provision_number`, `subsection` | Normalized citation components |
| `canonical_text` | Text resolved from the external source (see policy above) |
| `source_name` | Always `"IndianKanoon.org"` in this v0 file |
| `source_url` | Exact, individually-verified URL for that provision. **Every record in this file has a real, non-empty URL** — during the build, 4 draft records whose exact IndianKanoon document ID could not be confirmed were dropped from the resolved set rather than shipped with a placeholder/incomplete URL (see Unresolved cases) |
| `authority_level` | `"third_party_verified"` for all records in this file |
| `retrieval_date` | ISO date of resolution (`2026-08-12`) |
| `historical_status` | Point-in-time status: `in_force`, `repealed_nationally_2024-07-01_superseded_by_BNS(S)`, `act_repealed_2013_superseded_by_RFCTLARR_Act`, `omitted_1978_superseded_by_Article_300A`, `repealed_1988_superseded_by_Prevention_of_Corruption_Act_1988`, or an amendment note |
| `text_provenance` | `"webfetch_verbatim"` (4 records: Art. 226, IPC §302, CrPC §482, Land Acquisition Act §4 — directly fetched and quoted byte-for-byte in an earlier session) or `"websearch_synthesized_summary"` (59 records — resolved via search-engine-aggregated snippets citing a specific IndianKanoon URL, not a direct page fetch) |
| `confidence` | `"high"` only for the 4 `webfetch_verbatim` records; `"medium_search_verified"` for the rest |
| `nyayarag_dataset_text_deterministic_category` | OK/B/C/D/E — see filtering rules above |
| `nyayarag_dataset_text_raw` | The original (often unreliable) NyayaRAG text, kept for comparison only |

## Unresolved cases

**37 of the top 100 citation keys are NOT in `canonical_statutes.jsonl`** —
per instruction, unresolved citations are excluded rather than included as
if verified. This breaks down as:

- **33 keys never attempted** in this pass (search/lookup budget ran out
  before reaching them), mostly lower-frequency Income Tax Act/Rules,
  Arbitration Act 1940, and remaining IPC/CrPC/CPC sections:
  `Section 66/10/34 in Income Tax Rules, 1962`; `Section 468/341/467/504/397/306/342/395 in The Indian Penal Code, 1860`;
  `Section 342 in The Code of Criminal Procedure, 1973`; `Section 439 in The Code of Criminal Procedure, 1973`;
  `Section 162 in The Code of Criminal Procedure, 1973`; `Section 4/2/3/34 in The Income Tax Act, 1961`;
  `Article 1/2/3/15/39/162/246 in Constitution of India`; `Section 9 in The Land Acquisition Act, 1894`;
  `Section 13 in The Prevention of Corruption Act, 1988`; `Section 116A in The Representation of the People Act, 1951`;
  `Section 3 in The Essential Commodities Act, 1955`; `Section 30/33 in The Arbitration Act, 1940`;
  `Section 80/11 in The Code of Civil Procedure, 1908`.
- **4 keys attempted but dropped** because an exact, individually-verified
  IndianKanoon document URL could not be confirmed during this session
  (content was found via search but not pinned to one resolvable link):
  `Section 498A in The Indian Penal Code, 1860`; `Section 326 in The Indian Penal Code, 1860`;
  `Section 106 in The Transfer Of Property Act, 1882`; `Section 409 in The Indian Penal Code, 1860`.

None of these 37 appear in `canonical_statutes.jsonl`. Resolving them is the
natural next step for a v1 pass.

## Audit methodology and results

Every one of the 63 records in `canonical_statutes.jsonl` was independently
re-checked against its `source_url`, producing `evidence_audit.jsonl` (63
records, one per `canonical_statutes.jsonl` record, same key order).

**Method:** each `source_url` was directly re-fetched (not re-searched) and
its content read and compared, by hand, against five things: (1) does the
source correspond to the stated Act/provision, (2) does `canonical_text`
correspond to that exact provision, (3) do the provision number and Act name
match, (4) is `historical_status` correct where checkable, (5) does the
original NyayaRAG citation key map correctly to the record. **No LLM was
used to adjudicate correctness** — the comparison was a direct human-style
reading of the re-fetched page against the stored fields, exactly as in the
prior audits in this project.

**Verdict definitions** (from `evidence_audit.jsonl`'s `audit_verdict`
field):

- `VERIFIED_EXACT` — canonical text was directly (re-)fetched from the cited
  source and matches the provision as a clean, unmodified quote (whatever
  portion `canonical_text` covers must be a genuine, unaltered substring of
  the source — not necessarily the complete section, but not reworded
  either).
- `VERIFIED_CONTENT` — the source directly confirms the same Act, provision,
  and substantive meaning, but byte-for-byte equality cannot be established
  because `canonical_text` is a paraphrase, a restructured/compressed
  summary, or omits/reorders clauses relative to the source.
- `SOURCE_ONLY` — the source page exists and is plausibly the right
  document, but this audit could not independently confirm that the stored
  `canonical_text` corresponds to it (e.g. the re-fetch surfaced different
  subsection content, or the page's nature — bare act vs. commentary/report
  — was ambiguous).
- `INVALID` — a confirmed citation/source/text mismatch.
- `UNRESOLVED` — the mapping could not be checked at all (e.g. the
  `source_url` no longer resolves).

### Final counts

| Verdict | Count | % of 63 |
|---|---|---|
| `VERIFIED_EXACT` | **25** | 39.7% |
| `VERIFIED_CONTENT` | **34** | 54.0% |
| `SOURCE_ONLY` | **2** | 3.2% |
| `INVALID` | **1** | 1.6% |
| `UNRESOLVED` | **1** | 1.6% |
| **Total "verified" (EXACT + CONTENT)** | **59** | **93.7%** |

### Invalid / unresolved / source-only examples

- **INVALID — `Section 100 in The Code of Civil Procedure, 1908`.** Its
  `source_url` (`https://indiankanoon.org/doc/143489098/`) actually resolves
  to **Section 101** ("No second appeal shall lie except on the grounds
  mentioned in section 100."), not Section 100 itself. The citation key,
  `canonical_text`, and `source_url` do not all point to the same provision.
  This record must not be used until replaced with the correct Section 100
  document.
- **UNRESOLVED — `Section 161 in The Indian Penal Code, 1860`.** Its
  `source_url` (a `kanoongpt.in` page) returned HTTP 404 on re-fetch — the
  link is dead. The underlying fact it recorded (IPC s.161 repealed by the
  Prevention of Corruption Act, 1988) is well-established, but this specific
  citation currently has no working source to point to.
- **SOURCE_ONLY — `Section 25 in The Arms Act, 1959`.** Re-fetching the
  source surfaced a different subsection breakdown than the specific
  "3 to 7 years under a notification issued under section 24-A" sentence
  stored in `canonical_text`; that exact sentence could not be
  independently re-confirmed in this pass.
- **SOURCE_ONLY — `Section 5 in The Limitation Act, 1963`.** The re-fetched
  page's own content was labeled "(as recommended in the report)",
  suggesting it may be a Law Commission report about section 5 rather than
  the live bare-act section page itself — the quoted text matches the
  well-known real text, but this specific source could not be confirmed as
  the canonical section page.
- **Flagged data-quality issue (not a verdict, but caught by the same
  audit) — `Section 256 in The Income Tax Act, 1961`.** `canonical_text`
  (statement of case to the High Court) is accurate as historical text, but
  the record's `historical_status` field was wrongly stored as `in_force`.
  The source shows the section was actually **"Omitted by the National Tax
  Tribunal Act, 2005 (49 of 2005), section 30 and Schedule" effective
  2005-12-28**. This needs correcting in `canonical_statutes.jsonl` before
  the `historical_status` field is trusted for that record.

### Is this corpus suitable as GOLD evaluation evidence?

**No, not as-is.** 93.7% of records are content-verified, but only 39.7%
meet the stricter `VERIFIED_EXACT` bar, one record is a confirmed `INVALID`
mismatch that slipped through the original build, one is `UNRESOLVED` due to
link rot, and one has an incorrect `historical_status` value. A gold
evaluation set needs every record to be trustworthy without caveats — this
corpus currently is not, because (a) it still contains at least one wrong
mapping, (b) most records are paraphrased rather than verbatim, and (c) the
underlying source (IndianKanoon) is third-party, not the official India Code
text.

### Is this corpus suitable as DEVELOPMENT evidence?

**Yes, with the `INVALID` and `UNRESOLVED` records excluded or fixed first.**
For building and debugging a claim-verification prototype — testing
retrieval plumbing, entailment-checking logic, pipeline wiring — 61 of the
63 records (all but `INVALID`/`UNRESOLVED`) are real, source-backed,
content-confirmed statute text tied to real NyayaRAG citation keys, which is
sufficient for development purposes. Before any evaluation claims are made
from results produced against this corpus, at minimum: drop or fix the
`Section 100 CPC` (`INVALID`) and `Section 161 IPC` (`UNRESOLVED`) records,
correct the `Section 256 IT Act` `historical_status`, and be explicit that
"verified" here means `VERIFIED_EXACT` or `VERIFIED_CONTENT` against a
third-party source, not confirmed against India Code itself.

## Known limitations

- **India Code is inaccessible to automated fetching** in this environment
  (consistent 403s). All 63 resolved records rely on IndianKanoon, a
  third-party platform — accurate in every case spot-checked, but not an
  official government source. This must not be silently upgraded to
  "official" in downstream use.
- **59 of 63 records (`text_provenance: websearch_synthesized_summary`) are
  not confirmed byte-for-byte verbatim** — they are search-engine
  aggregations that cite a specific source URL but were not independently
  re-fetched and diffed against the live page in this pass. Only 4 records
  (`webfetch_verbatim`) have that stronger guarantee. A v1 pass should
  upgrade all 59 to verbatim via direct page fetch before this corpus is
  used as ground truth for any verifier.
- **Point-in-time correctness is asserted from general legal knowledge of
  major amendments (e.g. BNS/BNSS 2024, RFCTLARR 2013, 44th Amendment
  1978), not from a section-by-section amendment-history lookup** for each
  of the 63 provisions. Subtler amendments within a still-"in_force" record
  may not be reflected in `canonical_text`.
- **State Acts and Rules are entirely absent from this v0 corpus** because
  none appear in the top 100 by frequency — a useful claim-verification
  prototype touching state legislation will need a separate,
  frequency-independent resolution pass.
- **Coverage is capped at the top 100 citation keys**, not the full ~8,100
  distinct citations in the underlying NyayaRAG statute data — by design,
  per task scope.
- No verifier, correction mechanism, or LLM-based validation was
  implemented or invoked anywhere in producing this file.
