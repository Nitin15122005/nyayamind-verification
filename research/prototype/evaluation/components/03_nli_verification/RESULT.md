# RESULT — 03 Verifier / NLI Verification (STEP 5)

**Also see** `README.md` (STEP 3's stage-first mapping).
**The complete 420-record GOLD-01 expected-vs-actual benchmark is the STEP 4 artifact**
(`../../comparisons/expected_vs_actual/`) and is **not duplicated here** — this RESULT.md
covers component-level unit tests plus one representative case, per STEP 5's explicit
instruction.

## Execution

`research/.venv/Scripts/python.exe -m pytest test_controlled_benchmark.py test_premise_framing_production.py -v`

**48 executed, 48 passed, 0 failed, 0 skipped.** (Raw log removed in PASS 1 cleanup, see
`../01_claim_parser/RESULT.md`'s note.) No Qwen involved anywhere in this group.

## Model / checkpoint

`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, `device="cpu"` (no NVIDIA GPU on this
machine — STEP 2), `confidence_threshold=0.70`, read unmodified from
`config/prototype.yaml`. Same model/config STEP 4 used.

## Representative input → actual output (one real case, not the full 420)

Source: `demo_examples.json` in this directory — the real `NLIVerifier.verify()` call
inside a real `run_case()` execution (same fixtures as
`tests/test_correction_path_real_integration.py::test_corrupted_claim_reaches_contradicted_against_real_evidence`).

| | |
|---|---|
| Premise framing | production default (`labeled`) |
| Premise (real canonical evidence, Section 302 IPC) | "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine." |
| Hypothesis (deliberately corrupted claim) | "The offense of murder under Section 302 of the Indian Penal Code, 1860 is punishable only by a fine and never by death or imprisonment." |
| **Actual verdict** | **CONTRADICTED** |
| Actual confidence | above `confidence_threshold=0.70` (exact value in the JSON) |
| Expected behavior | a genuinely contradictory hypothesis against real evidence must be judged CONTRADICTED above threshold |

**Result: PASS.** This is a **Category A-adjacent** result in the sense that the
"expected" answer here (CONTRADICTED) follows from the hypothesis being a deliberately,
verifiably false restatement of the real evidence text — it is a software-behavior
assertion pinned by an existing test, not drawn from the 420-item construction-derived
GOLD benchmark. The full statistical accuracy claim against true GOLD labels remains
exclusively STEP 4's territory.

## Where the full 420-item GOLD-01 result lives

`../../comparisons/expected_vs_actual/gold01_expected_vs_actual.csv`,
`EXPECTED_VS_ACTUAL_REPORT.md`, `HISTORICAL_CROSSCHECK.md` (STEP 4). Not reproduced here.
