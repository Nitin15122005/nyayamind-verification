#!/usr/bin/env python3
"""
V2 FRESH RERUN — GOLD-01 controlled verifier benchmark, ORIGINAL vs LATEST.

WHAT THIS MEASURES
------------------
The single `verification.premise_framing` lever, which is the difference
between the ORIGINAL NyayaMind verifier configuration (`bare`) and the
LATEST production configuration (`labeled`). Everything else is held fixed:
same 420 gold items, same NLI checkpoint, same confidence threshold (0.70),
same max_sequence_length (512), same device (cpu), same code path
(`src.verifier.NLIVerifier` / `src.verifier.format_premise` at HEAD).

This is a SINGLE-LEVER ablation, not a joint multi-lever original-vs-latest
comparison. Label it as such wherever it is reported.

WHY IT IS LEGITIMATELY RERUNNABLE ON THIS MACHINE
-------------------------------------------------
It uses only `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, which is cached
locally and runs on CPU. No Qwen generation/correction is involved, so the
absence of a GPU does not affect it. Inference is greedy argmax over a
softmax — there is no sampling, so no random seed is required and the run is
deterministic given the same weights and stack.

GOLD LABELS
-----------
`expected_label` in the benchmark JSONL is produced by deterministic
construction rules over canonical statute text (see
`outputs/controlled_verifier_benchmark_meta.json`:
"gold_label_source": "construction rule (never a model prediction)"),
so accuracy / precision / recall / F1 / confusion matrix are legitimate
terms for this dataset. Evidence grade: GOLD.

STATISTICS
----------
- McNemar exact (binomial) test on the paired per-item correctness vectors.
  Paired because both arms score the identical 420 items.
- Wilson score 95% CI for each arm's accuracy.
- Bootstrap 95% CI (10,000 resamples, fixed seed 20260918) for macro F1 and
  for the paired macro-F1 delta.

OUTPUTS (all under v2_outputs_phase_3_vedant/metrics/)
------------------------------------------------------
- gold01_v2_predictions_bare.jsonl
- gold01_v2_predictions_labeled.jsonl
- gold01_v2_metrics.json

Run:  python v2_outputs_phase_3_vedant/scripts/rerun_gold01_verifier_original_vs_latest.py
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
_PROTOTYPE_ROOT = _V2_ROOT.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml  # noqa: E402

from src.verifier import (  # noqa: E402
    NLIVerifier,
    format_premise,
    ENTAILED,
    CONTRADICTED,
    NOT_ENOUGH_INFORMATION,
)

LABELS = (ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION)

BENCHMARK_PATH = _PROTOTYPE_ROOT / "outputs" / "controlled_verifier_benchmark.jsonl"
CONFIG_PATH = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
METRICS_DIR = _V2_ROOT / "metrics"

# Recorded in the historical GOLD-01 run metadata; we re-check it so that a
# silently-changed dataset can never masquerade as a reproduction.
EXPECTED_DATASET_SHA256 = (
    "962de21ee373bcfb685193902767c1c2c4f10acf592b08f561159503b4287f99"
)

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260918


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_benchmark(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_metrics(expected: list[str], predicted: list[str]) -> dict:
    cm = {e: {p: 0 for p in LABELS} for e in LABELS}
    for e, p in zip(expected, predicted):
        cm[e][p] += 1

    per_class = {}
    f1s = []
    for lbl in LABELS:
        tp = cm[lbl][lbl]
        fp = sum(cm[o][lbl] for o in LABELS if o != lbl)
        fn = sum(cm[lbl][o] for o in LABELS if o != lbl)
        support = sum(cm[lbl].values())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_class[lbl] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        f1s.append(f1)

    correct = sum(1 for e, p in zip(expected, predicted) if e == p)
    return {
        "n_items": len(expected),
        "accuracy": correct / len(expected) if expected else 0.0,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
        "confusion_matrix": cm,
        "per_class": per_class,
    }


def macro_f1_from_pairs(pairs: list[tuple[str, str]]) -> float:
    """Macro F1 over an arbitrary (possibly resampled) list of (expected, predicted)."""
    cm = {e: {p: 0 for p in LABELS} for e in LABELS}
    for e, p in pairs:
        cm[e][p] += 1
    f1s = []
    for lbl in LABELS:
        tp = cm[lbl][lbl]
        fp = sum(cm[o][lbl] for o in LABELS if o != lbl)
        fn = sum(cm[lbl][o] for o in LABELS if o != lbl)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    return sum(f1s) / len(f1s)


def wilson_ci(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval — appropriate for a proportion, unlike the normal
    approximation which misbehaves near 0 and 1 (labeled accuracy is ~0.97)."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(correct_a: list[bool], correct_b: list[bool]) -> dict:
    """Exact (binomial) McNemar test on paired correctness.

    b = items A got right and B got wrong; c = items B got right and A wrong.
    Exact two-sided binomial test on b vs (b+c), p=0.5. Used instead of the
    chi-square approximation because it is valid at any discordant count.
    """
    b = sum(1 for a, bb in zip(correct_a, correct_b) if a and not bb)
    c = sum(1 for a, bb in zip(correct_a, correct_b) if (not a) and bb)
    n = b + c
    if n == 0:
        return {"b_only_A_correct": 0, "c_only_B_correct": 0,
                "n_discordant": 0, "p_value": 1.0,
                "test": "McNemar exact binomial (two-sided)",
                "note": "no discordant pairs"}
    k = min(b, c)
    # two-sided exact binomial
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    p = min(1.0, 2.0 * tail)
    return {
        "b_only_A_correct": b,
        "c_only_B_correct": c,
        "n_discordant": n,
        "p_value": p,
        "test": "McNemar exact binomial (two-sided)",
    }


def bootstrap_macro_f1(expected, pred_a, pred_b, resamples, seed):
    """Paired bootstrap over items: resample item indices once per replicate and
    recompute BOTH arms on the same resample, so the delta CI is paired."""
    rng = random.Random(seed)
    n = len(expected)
    idx_range = range(n)
    a_vals, b_vals, d_vals = [], [], []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in idx_range]
        pa = [(expected[i], pred_a[i]) for i in idx]
        pb = [(expected[i], pred_b[i]) for i in idx]
        fa = macro_f1_from_pairs(pa)
        fb = macro_f1_from_pairs(pb)
        a_vals.append(fa)
        b_vals.append(fb)
        d_vals.append(fb - fa)

    def pct(vals, q):
        s = sorted(vals)
        k = (len(s) - 1) * q
        lo, hi = math.floor(k), math.ceil(k)
        if lo == hi:
            return s[int(k)]
        return s[lo] * (hi - k) + s[hi] * (k - lo)

    return {
        "resamples": resamples,
        "seed": seed,
        "bare_macro_f1_ci95": [pct(a_vals, 0.025), pct(a_vals, 0.975)],
        "labeled_macro_f1_ci95": [pct(b_vals, 0.025), pct(b_vals, 0.975)],
        "delta_macro_f1_ci95_paired": [pct(d_vals, 0.025), pct(d_vals, 0.975)],
    }


def run_framing(verifier: NLIVerifier, records: list[dict], framing: str) -> tuple[list[str], list[dict], float]:
    preds, rows = [], []
    t0 = time.time()
    for rec in records:
        premise = format_premise(
            rec["evidence_text"],
            framing=framing,
            provision_type=rec.get("provision_type"),
            provision_number=rec.get("provision_number"),
            act=rec.get("act_name"),
        )
        res = verifier.verify(premise, rec["hypothesis"])
        preds.append(res.label)
        rows.append({
            "benchmark_id": rec["benchmark_id"],
            "condition": rec["condition"],
            "evidence_key": rec["evidence_key"],
            "expected_label": rec["expected_label"],
            "predicted_label": res.label,
            "confidence": res.confidence,
            "sub_reason": res.sub_reason,
            "raw_scores": res.raw_scores,
            "input_truncated": res.input_truncated,
            "premise_framing": framing,
        })
    return preds, rows, time.time() - t0


def main() -> int:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    actual_sha = sha256_of(BENCHMARK_PATH)
    if actual_sha != EXPECTED_DATASET_SHA256:
        print(f"ABORT: dataset sha256 mismatch.\n  expected {EXPECTED_DATASET_SHA256}\n  actual   {actual_sha}")
        return 1
    print(f"dataset sha256 OK: {actual_sha}")

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    vcfg = cfg["verification"]
    model_id = vcfg["model_id"]
    threshold = vcfg["confidence_threshold"]
    max_len = vcfg["max_sequence_length"]
    production_framing = vcfg["premise_framing"]
    print(f"config: model={model_id} threshold={threshold} max_len={max_len} production_framing={production_framing}")

    records = load_benchmark(BENCHMARK_PATH)
    print(f"loaded {len(records)} benchmark items")

    verifier = NLIVerifier(
        model_id=model_id,
        confidence_threshold=threshold,
        max_sequence_length=max_len,
        device="cpu",  # explicit opt-in, as src/verifier.py requires
    )
    t_load = time.time()
    verifier.load()
    load_seconds = time.time() - t_load
    print(f"model loaded on cpu in {load_seconds:.1f}s")

    expected = [r["expected_label"] for r in records]

    print("running framing=bare (ORIGINAL) ...")
    pred_bare, rows_bare, secs_bare = run_framing(verifier, records, "bare")
    print(f"  done in {secs_bare:.1f}s")

    print("running framing=labeled (LATEST) ...")
    pred_labeled, rows_labeled, secs_labeled = run_framing(verifier, records, "labeled")
    print(f"  done in {secs_labeled:.1f}s")

    m_bare = compute_metrics(expected, pred_bare)
    m_labeled = compute_metrics(expected, pred_labeled)

    correct_bare = [e == p for e, p in zip(expected, pred_bare)]
    correct_labeled = [e == p for e, p in zip(expected, pred_labeled)]
    mcnemar = mcnemar_exact(correct_bare, correct_labeled)

    n = len(records)
    ci_bare = wilson_ci(sum(correct_bare), n)
    ci_labeled = wilson_ci(sum(correct_labeled), n)

    print(f"bootstrapping macro F1 ({BOOTSTRAP_RESAMPLES} resamples) ...")
    boot = bootstrap_macro_f1(expected, pred_bare, pred_labeled, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED)

    n_truncated = sum(1 for r in rows_bare + rows_labeled if r["input_truncated"])

    out = {
        "artifact_id": "GOLD01-V2-FRESH",
        "benchmark_tag": "GOLD-01_controlled_verifier_benchmark",
        "comparison": "ORIGINAL (premise_framing=bare) vs LATEST (premise_framing=labeled)",
        "comparison_scope": (
            "SINGLE-LEVER ablation of verification.premise_framing. NOT a joint "
            "multi-lever original-vs-latest system comparison. All other settings "
            "held at HEAD production values."
        ),
        "original_arm": {"name": "NyayaMind v0 verifier config", "premise_framing": "bare"},
        "latest_arm": {"name": "NyayaMind production verifier config", "premise_framing": "labeled"},
        "evidence_grade": "GOLD",
        "gold_label_source": "deterministic construction rule (never a model prediction)",
        "n_items": n,
        "dataset_path": str(BENCHMARK_PATH.relative_to(_PROTOTYPE_ROOT)),
        "dataset_sha256": actual_sha,
        "verifier_model": model_id,
        "confidence_threshold": threshold,
        "max_sequence_length": max_len,
        "device": "cpu",
        "deterministic": True,
        "seed_required": False,
        "seed_note": "greedy argmax over softmax; no sampling, so no inference seed exists. Bootstrap CI uses seed 20260918.",
        "n_inference_failures": 0,
        "n_inputs_truncated": n_truncated,
        "model_load_seconds": load_seconds,
        "results_by_framing": {
            "bare": {**m_bare, "elapsed_seconds": secs_bare,
                     "accuracy_ci95_wilson": list(ci_bare)},
            "labeled": {**m_labeled, "elapsed_seconds": secs_labeled,
                        "accuracy_ci95_wilson": list(ci_labeled)},
        },
        "deltas": {
            "accuracy": m_labeled["accuracy"] - m_bare["accuracy"],
            "macro_f1": m_labeled["macro_f1"] - m_bare["macro_f1"],
            "per_class_f1": {
                lbl: m_labeled["per_class"][lbl]["f1"] - m_bare["per_class"][lbl]["f1"]
                for lbl in LABELS
            },
            "per_class_recall": {
                lbl: m_labeled["per_class"][lbl]["recall"] - m_bare["per_class"][lbl]["recall"]
                for lbl in LABELS
            },
            "per_class_precision": {
                lbl: m_labeled["per_class"][lbl]["precision"] - m_bare["per_class"][lbl]["precision"]
                for lbl in LABELS
            },
        },
        "statistics": {"mcnemar_accuracy": mcnemar, "bootstrap_macro_f1": boot},
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": __import__("torch").__version__,
            "transformers": __import__("transformers").__version__,
            "cuda_available": __import__("torch").cuda.is_available(),
        },
        "environment_note": (
            "This rerun executed on a DIFFERENT software stack than the historical "
            "GOLD-01 run (historical: Python 3.11.9 / torch 2.2.2+cu121; here: see "
            "`environment`). Any difference from the historical numbers is therefore a "
            "cross-stack reproduction difference, not a system change."
        ),
        "historical_comparison_reference": (
            "research/prototype/evaluation/actual_outputs/gold_benchmark_runs/"
            "gold01_controlled/gold01_metrics.json"
        ),
        "generated_by": "v2_outputs_phase_3_vedant/scripts/rerun_gold01_verifier_original_vs_latest.py",
    }

    (METRICS_DIR / "gold01_v2_metrics.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    for name, rows in (("bare", rows_bare), ("labeled", rows_labeled)):
        with (METRICS_DIR / f"gold01_v2_predictions_{name}.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    print("\n=== RESULT ===")
    print(f"  bare    (ORIGINAL): accuracy {m_bare['accuracy']:.4f}  macro F1 {m_bare['macro_f1']:.4f}")
    print(f"  labeled (LATEST)  : accuracy {m_labeled['accuracy']:.4f}  macro F1 {m_labeled['macro_f1']:.4f}")
    print(f"  delta macro F1    : {out['deltas']['macro_f1']:+.4f}")
    print(f"  McNemar exact p   : {mcnemar['p_value']:.3e}  (b={mcnemar['b_only_A_correct']}, c={mcnemar['c_only_B_correct']})")
    print(f"  truncated inputs  : {n_truncated}")
    print(f"  wrote {METRICS_DIR / 'gold01_v2_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
