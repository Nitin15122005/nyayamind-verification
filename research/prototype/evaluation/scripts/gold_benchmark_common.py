"""Shared metric-calculation helper for STEP 4's GOLD-01/GOLD-02 evaluation runners.

WHY THIS FILE EXISTS (a documented blocker, not a stylistic choice):

`research/prototype/scripts/run_controlled_benchmark.py` — the project's own existing
GOLD-01 evaluation script — CANNOT be imported under this project's own pinned canonical
Python 3.11.9 (`research/.venv/`). It raises:

    SyntaxError: f-string expression part cannot include a backslash

at its `fmt_confusion()` function (`f"  {'gold \\ pred':<16}"` — a Python 3.12+-only
relaxed f-string grammar feature, PEP 701). Verified directly: the file fails
`py_compile` under Python 3.11.9 and succeeds under Python 3.14. This is independently
corroborated by the historical results themselves: `outputs/controlled_benchmark_deberta_metrics.json`'s
own recorded `environment` field shows `{"python": "3.13.1", "torch": "2.13.0+cpu",
"transformers": "5.15.1"}` — the historical GOLD-01 results were never produced under
this project's documented Python 3.11.9 / torch==2.2.2+cu121 pin at all, but under an
entirely different, undocumented environment. This is a genuine, pre-existing project
reproducibility gap that STEP 4 did not introduce and is not authorized to fix (fixing
`run_controlled_benchmark.py` would mean modifying a file outside `evaluation/`).

The actual model-loading/inference code — `src/verifier.py::NLIVerifier`, `format_premise`
— imports and runs perfectly under the pinned 3.11.9 environment; only this one
presentation-layer script fails to parse, due to a syntax-portability issue in its own
console-formatting code, unrelated to any model or verification logic.

RESOLUTION: STEP 4 calls the real, unmodified `NLIVerifier`/`format_premise` directly —
exactly the same functions `run_controlled_benchmark.py` itself calls internally — and
reimplements ONLY the generic confusion-matrix / precision / recall / F1 arithmetic below,
using the identical tp/fp/fn-based formula `run_controlled_benchmark.py::compute_metrics`
uses (verified by reading that file's source directly, even though it cannot be imported
in this environment). This is not a duplicate reimplementation of anything
model/verifier/inference-related — it is the same standard, unambiguous scoring formula,
written fresh only because the existing file containing it happens not to parse here.

GOLD-02's existing evaluation script, `scripts/compare_premise_framing_synthetic.py`,
has no such issue and IS imported directly and reused as-is by `run_gold02_evaluation.py`.
"""

from __future__ import annotations

ENTAILED = "ENTAILED"
CONTRADICTED = "CONTRADICTED"
NOT_ENOUGH_INFORMATION = "NOT_ENOUGH_INFORMATION"
LABELS = [ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION]


def compute_metrics(expected: list[str], predicted: list[str]) -> tuple[dict, dict, float]:
    """Identical formula to scripts/run_controlled_benchmark.py::compute_metrics
    (that file's own source was read directly; this is not a guess at the formula),
    EXTENDED to tolerate predicted values outside the 3 verifier labels -- specifically
    NO_EVIDENCE, which is a real, legitimate outcome of the full retrieve-then-verify
    path (build_baseline + apply_verification) used for GOLD-02: it means the claim
    parser/evidence matcher never handed this claim to the verifier at all, which is a
    distinct failure mode from the verifier answering incorrectly and must not be
    silently coerced into one of the 3 verifier labels or dropped from the accounting.
    `expected` values are always assumed to be within LABELS (true for both GOLD-01 and
    GOLD-02 as constructed)."""
    pred_columns = list(LABELS)
    for p in predicted:
        if p not in pred_columns:
            pred_columns.append(p)

    cm = {e: {p: 0 for p in pred_columns} for e in LABELS}
    for e, p in zip(expected, predicted):
        cm[e][p] += 1

    per_class = {}
    f1s = []
    for lbl in LABELS:
        tp = cm[lbl][lbl]
        fp = sum(cm[o][lbl] for o in LABELS if o != lbl)
        fn = sum(cm[lbl][o] for o in LABELS if o != lbl)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[lbl] = {
            "precision": prec, "recall": rec, "f1": f1,
            "support": sum(cm[lbl].values()), "tp": tp, "fp": fp, "fn": fn,
        }
        f1s.append(f1)
    macro_f1 = sum(f1s) / len(f1s)
    return cm, per_class, macro_f1


def confusion_matrix_rows(cm: dict) -> list[str]:
    short = {ENTAILED: "ENT", CONTRADICTED: "CON", NOT_ENOUGH_INFORMATION: "NEI",
             "NO_EVIDENCE": "N_EV"}
    pred_columns = list(next(iter(cm.values())).keys()) if cm else list(LABELS)

    def col_label(c: str) -> str:
        return short.get(c, c[:7])

    out = ["Confusion matrix (rows = expected/gold, cols = predicted/actual; "
           "N_EV = NO_EVIDENCE, never reached the verifier):",
           "  " + f"{'gold vs pred':<16}" + "".join(f"{col_label(c):>7}" for c in pred_columns) + f"{'total':>8}"]
    for e in LABELS:
        if e not in cm:
            continue
        row_total = sum(cm[e].values())
        out.append("  " + f"{short.get(e, e):<16}" + "".join(f"{cm[e][c]:>7}" for c in pred_columns) + f"{row_total:>8}")
    return out
