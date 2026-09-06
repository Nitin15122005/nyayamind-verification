# Live Demo Suite

A presentation-quality demonstration of the NyayaMind pipeline, built on
`research/prototype/src/*` — unmodified, unmocked. This is **not** an
experimental testing workspace (that's `../components/`, `../ablation/`,
`../metrics/`, etc.); it exists purely to let a reviewer *watch the real
system run* against real data, one pipeline stage at a time, with clean,
explained output.

No file under `src/`, `tests/`, `config/`, `research/data/`, or
`research/prototype/outputs/` is modified by anything in this directory.
Every script here is read-only against those paths.

## Directory structure

```
live_demo/
├── README.md                          — this file
├── run_demo.py                        — original combined walkthrough (3 full
│                                          real cases, stages 1–7 end to end)
├── demo_run_log.txt                   — a real, current sample run of run_demo.py
├── common/                            — shared code every demo below imports
│   ├── pipeline_helpers.py            — path setup, config/pool/verifier loaders,
│   │                                     FakeGenerator/ScriptedCorrector
│   └── formatting.py                  — consistent terminal output (banners,
│                                          stage tags, the grouped claim view)
├── 01_claim_parser_demo.py            — A: Claim Parser
├── 02_evidence_retrieval_demo.py      — B: Evidence Retrieval
├── 03_nli_verification_demo.py        — C: NLI Verification
├── 04_verdict_application_demo.py     — D: Verdict Application
├── 05_scope_safety_demo.py            — E: Scope / Safety Check
├── 06_correction_reverification_demo.py — F: Correction + Re-verification
└── 07_full_pipeline/                  — G: Full Pipeline, one script per outcome
    ├── entailed_outcome.py
    ├── contradicted_outcome.py
    ├── nei_outcome.py
    └── no_evidence_outcome.py
```

Every script above is independently runnable and self-contained (its own
`main()`, its own module docstring naming exactly what's live vs. replayed).
None depends on another having run first.

## Why claims repeat — read this first

Every demo that prints a document's claims (01, 04, 06, and all of
`07_full_pipeline/`) uses a shared grouped view
(`common/formatting.py::claim_overview`) instead of a flat, truncated
per-claim list. That fix exists because of a real, investigated question:
**why do claims for "Section 302" or "Section 304" sometimes look
repeated?**

Answer, confirmed by reading `src/claim_parser.py::extract_claims`'s own
docstring and reproducing it live (see `01_claim_parser_demo.py`):

> "A sentence naming several provisions of the same act ... becomes one
> Claim PER provision — each with the same `claim_text` (the original
> sentence, preserved verbatim) but its own `citation_extracted`, so each
> provision gets its own independent evidence lookup and verification."

This is **legitimate atomic decomposition, not duplicate parsing, and not a
demo bug in the underlying logic** — confirmed directly from the source, not
assumed. What *was* a demo-presentation problem (in the original
`run_demo.py`, before this redesign): printing only a truncated `claim_text`
preview per claim made two independent claims that share one sentence look
like accidental duplicates, with no explanation. `claim_overview()` fixes
that presentation, without touching any production code, by showing:

1. **Unique source sentences**, and how many atomic claims/citations each
   produced (so "2 claims, same sentence" reads as "one sentence, two
   citations," not as noise).
2. A **claim → citation → evidence → verdict** table — one row per claim,
   each with its own distinguishing citation/evidence/verdict, not just the
   shared sentence preview.
3. **Evidence cited by more than one claim** in the document, grouped
   explicitly — e.g. `run_demo.py`'s real CASE 1997_1306 has "Section 304"
   cited by claims c2, c3, c7, and c8 (two different sentences, each
   bundling several citations); the grouped view states this as one fact
   instead of four separately-printed, unexplained-looking repeats.

`01_claim_parser_demo.py` demonstrates and resolves this directly using the
real repeated-claims case (document `2011_625`) and a harder, real
multi-Act sentence, with a byte-for-byte self-check against an
already-audited expected result.

## Running the demos

All commands below are run from the repository root:

```
research/.venv/Scripts/python.exe research/prototype/evaluation/live_demo/<script>.py
```

| # | Script | GPU needed? | What it shows |
|---|---|---|---|
| — | `run_demo.py` | No (auto CPU/GPU) | Original combined walkthrough: 3 real cases end to end (NO_EVIDENCE, CONTRADICTED→shipped, ENTAILED-after-correction), stages 1–7 |
| A | `01_claim_parser_demo.py` | No (no model) | Claim extraction, citation/statute info, and the "why claims repeat" explanation, live + self-checked |
| B | `02_evidence_retrieval_demo.py` | No (no model) | Exact match, NO_EVIDENCE, and (static) same-number/different-Act disambiguation |
| C | `03_nli_verification_demo.py` | No (auto CPU/GPU) | ENTAILED, CONTRADICTED, and NEI, each a genuine live verifier call |
| D | `04_verdict_application_demo.py` | No (auto CPU/GPU) | The real evidence/no-evidence ROUTING logic (`apply_verification`) |
| E | `05_scope_safety_demo.py` | No (no model) | The real `_scope_violation()` gate in isolation: one safe case, one rejected case |
| F | `06_correction_reverification_demo.py` | No (auto CPU/GPU) | Full `run_case()` correction lifecycle: SHIPPED vs REJECTED, side by side |
| G | `07_full_pipeline/entailed_outcome.py` | No (auto CPU/GPU) | Full pipeline (Mode B), ending in ENTAILED |
| G | `07_full_pipeline/contradicted_outcome.py` | No (auto CPU/GPU) | Full pipeline (Mode B), ending in CONTRADICTED |
| G | `07_full_pipeline/nei_outcome.py` | No (auto CPU/GPU) | Full pipeline (Mode B), ending in a genuine NOT_ENOUGH_INFORMATION |
| G | `07_full_pipeline/no_evidence_outcome.py` | No (auto CPU/GPU) | Full pipeline (Mode B), ending in NO_EVIDENCE |

**No script in this directory requires a GPU.** The only genuinely
GPU-bound stages in the real pipeline are text *generation* and *correction
rewriting* (both Qwen2.5-7B-Instruct calls) — every demo above substitutes
those with either (a) a real, already-committed generated/corrected text
read verbatim from `research/prototype/outputs/*.jsonl` (`REPLAYED`,
labeled as such in the stage header), or (b) `common.pipeline_helpers`'s
`FakeGenerator`/`ScriptedCorrector` (`SCRIPTED`) — the exact same
substitution pattern `tests/test_correction_path_real_integration.py`
already uses to exercise `src.pipeline.run_case()`'s real logic without a
GPU. Every other stage (claim parsing, evidence retrieval, NLI verification,
the scope gate, re-verification) is executed live. The NLI verifier itself
(~184M parameters) auto-detects CUDA and falls back to CPU
(`"cuda" if torch.cuda.is_available() else "cpu"` — the exact pattern the
project's own real test fixture uses); on CPU it typically takes a few
seconds to load and run.

## LIVE vs REPLAYED vs SCRIPTED vs STATIC — what these tags mean

Every stage header in every demo carries one of four tags
(`common/formatting.py`):

- **LIVE** — real, unmodified `src/*` code, executed just now, on this run.
- **REPLAYED (from committed output, not re-run)** — a real value read
  verbatim from an already-committed `research/prototype/outputs/*.jsonl`
  file at runtime, not recomputed. Used for the generation stage in
  `run_demo.py`, `04_verdict_application_demo.py`, and every script in
  `07_full_pipeline/` (each loads a real record via
  `pipeline_helpers.load_record()` and feeds its real generated text through
  `FakeGenerator`), plus the correction-text stage in `run_demo.py`.
- **SCRIPTED SUBSTITUTE** — the `FakeGenerator`/`ScriptedCorrector` pattern:
  real, verbatim text (copied from a real committed record or the project's
  own real integration test), supplied directly instead of invoking the 7B
  model, so the REAL surrounding pipeline logic (`run_case()`, the scope
  gate, re-verification) can still execute live. Used in `05`, `06`, and
  all of `07_full_pipeline/`.
- **STATIC (curated real record, read only)** — an already-audited real
  result read from `../components/*/demo_examples.json`, shown for
  reference/context but not recomputed against this demo's own live state
  (used sparingly — currently only one illustration in
  `02_evidence_retrieval_demo.py`, where the recorded result was produced
  against a different, test-only evidence pool).

Nothing in this suite invents a citation, an evidence text, a verdict, or a
confidence value. Every number either comes from a live model/function call
made during that run, or is read character-for-character from a real,
already-committed file.

## Self-checks

Several demos (`01`, `02`) compare their own live output against an
already-recorded, previously-audited expected result
(`../components/*/demo_examples.json`) and print `PASS`/`MISMATCH`
explicitly, rather than silently trusting either source. As of this
redesign, every self-check passes.

## Relationship to `../components/`

`../components/0N_*/` holds this project's per-pipeline-stage *test
inventory and evidence* (which real `tests/` files exercise each stage,
plus curated `demo_examples.json` fixtures) — the audit trail. This
directory (`live_demo/`) is the *presentation layer* built on top of some
of that same real data: several demos here read a `demo_examples.json` file
directly (always labeled `STATIC` when doing so, or used as a live
self-check target) rather than duplicating its content by hand.

## Known limitations

- **`03_nli_verification_demo.py`, `04_verdict_application_demo.py`,
  `06_correction_reverification_demo.py`, and every script in
  `07_full_pipeline/`** load the real ~184M-parameter DeBERTa verifier.
  This is fast on either CPU or GPU, but is not "instant" — expect the
  first `verifier.load()` in a given process to take a few seconds
  (longer on a cold Hugging Face cache, since the checkpoint may need to
  download once).
- **Confidence values are live and will vary slightly** run to run and
  machine to machine (float precision, hardware, `transformers`/`torch`
  versions) — expect agreement to ~3-4 decimal places with the historical
  reference values cited in each demo's docstring, not bit-for-bit
  identity. The verdict *label* (ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION)
  is what each demo actually asserts on; if a live run's label ever
  disagreed with what a demo expects, the script reports that mismatch
  honestly instead of forcing/hiding it (see `07_full_pipeline/entailed_outcome.py`
  and `contradicted_outcome.py` in particular, which pick their target
  claim by live verdict, not by a hardcoded index, for exactly this
  reason).
- **This suite demonstrates code paths and real model behavior, not legal
  correctness.** Every verifier verdict is a small public NLI model's
  statistical judgment against a third-party-sourced, ~140-provision
  evidence corpus — never a lawyer-verified determination (see
  `common/formatting.py::NLI_DISCLAIMER`, printed by every demo that calls
  the verifier).
- **Mode C's correction step is never run live end-to-end with a real 7B
  model here** — that would require a GPU and would not be reproducible
  across reviewers' machines. `05`, `06`, and `07_full_pipeline/` instead
  run the REAL correction/scope-check/re-verification *logic*
  (`src.pipeline.run_case()`/`_scope_violation()`, unmodified) against
  real, verbatim text with only the two GPU-only generation calls
  substituted — the same technique the project's own real integration test
  suite already relies on for the identical reason.
