# Case Inputs — Source

**This directory intentionally contains no copied data files.** The NyayaRAG source case
files are large (~27MB each) and already frozen at their original location — copying them
would violate this step's explicit instruction not to duplicate large datasets
unnecessarily.

## What this is

Real Indian Supreme Court case text (`case_text` / `summarized_text`) that would be fed
as `case_text` into `src/generator.py::StatuteGroundingGenerator.generate()` (stage 1,
generation) to produce a fresh statutory-grounding field. **This machine has no NVIDIA
GPU (see STEP 2's `ENVIRONMENT_REPRODUCIBILITY_RESULT.md`), so this input cannot
currently be run through generation here** — it is documented for completeness and for
any future GPU-capable environment, not because a fresh generation run is planned in this
step.

## Where it originates

| | |
|---|---|
| Source | `L-NLProc/NyayaRAG` on Hugging Face, `3.CaseText_Statutes.zip` |
| Files | `research/data/nyayarag/CaseText_Statutes/SCI_56k_multi_5k_summarised_w_sections.json` (4,930 records, 26.9 MB), `SCI_56k_single_5k_summarised_w_sections.json` (4,962 records, 27.7 MB) |
| Schema | one record: `{document_id, summarized_text, sections}` — `sections` is a dict of citation-key → NyayaRAG's own (unverified, never used as evidence) text |
| Provenance caveat | Populated by copying files already extracted in an earlier session's scratch space — **not reproducible from a clean checkout** without re-obtaining the zip from Hugging Face; no committed script downloads it automatically (`README.md` "Known limitations") |

## Which cases have already been selected from this pool (for reference, not fresh selection)

The natural-batch selection files (frozen, referenced — not copied here since they already
live at their own frozen paths) record which `document_id`s were previously drawn from
this pool: `outputs/natural_candidate_selected_ids_{30,50,50_batch2,50_final_validation}.json`
— confirmed disjoint by direct ID-set intersection in STEP 0. Their hashes are recorded in
`../MANIFEST.md`.

## Which component consumes it

`src/generator.py::StatuteGroundingGenerator.generate(case_text)` — only `case_text` (or
`summarized_text`) and the case's own citation **keys** are read; NyayaRAG's own
`sections` free-text values are never treated as evidence anywhere in this pipeline
(`src/data_loader.py` docstrings).

## Classification

**N/A / input corpus** — pre-generation raw case text, not a labeled dataset. Selecting a
disjoint new batch from it is possible via `scripts/select_natural_candidates.py`
(CPU-only, deterministic, no GPU) even on this machine; only the subsequent *generation*
step requires a GPU this machine does not have.

## What can legitimately be measured from it

Nothing directly — it is raw input. Selection scoring (`score_case`) can run and be
inspected here; no claim, verdict, or correction exists until generation runs, which is
blocked on this machine.
