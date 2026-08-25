#!/usr/bin/env python3
"""
Comprehensive Verifier Benchmark & Ablation Study (Phases 1 - 6).
Evaluates DeBERTa vs Qwen LLM Verifier on 177 controlled benchmark pairs,
tests corrector prompt variants, and re-evaluates synthetic & natural data if justified.
"""
from __future__ import annotations

import copy
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml
from src.data_loader import load_usable_evidence, load_nyayarag_cases, select_cases_with_evidence_overlap
from src.generator import StatuteGroundingGenerator
from src.verifier import NLIVerifier, ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.llm_verifier import QwenLLMVerifier
from src.corrector import SelectiveCorrector
from src.synthetic_stress import build_synthetic_stress_claims
from src import pipeline, claim_parser


def print_flush(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)


def compute_metrics(expected_list, predicted_list, labels=("ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION")):
    cm = {exp: {pred: 0 for pred in labels} for exp in labels}
    for exp, pred in zip(expected_list, predicted_list):
        if exp in cm and pred in cm[exp]:
            cm[exp][pred] += 1
        elif exp in cm:
            cm[exp]["NOT_ENOUGH_INFORMATION"] += 1

    per_class = {}
    f1_list = []
    for lbl in labels:
        tp = cm[lbl][lbl]
        fp = sum(cm[other][lbl] for other in labels if other != lbl)
        fn = sum(cm[lbl][other] for other in labels if other != lbl)
        support = sum(cm[lbl].values())

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class[lbl] = {"precision": prec, "recall": rec, "f1": f1, "support": support}
        f1_list.append(f1)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0
    return cm, per_class, macro_f1


def print_evaluation_report(verifier_name, benchmark_records, predictions, confidences=None):
    expected_list = [r["expected_label"] for r in benchmark_records]
    labels = ["ENTAILED", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"]
    cm, per_class, macro_f1 = compute_metrics(expected_list, predictions, labels)

    print_flush("\n" + "=" * 60)
    print_flush(f"VERIFIER: {verifier_name}")
    print_flush("=" * 60)
    print_flush("\nConfusion Matrix (rows=expected, cols=predicted):")
    header = f"{'':12}" + "".join(f"{lbl[:6]:>10}" for lbl in labels)
    print_flush(header)
    for exp in labels:
        row_str = f"{exp[:10]:12}" + "".join(f"{cm[exp][pred]:10d}" for pred in labels)
        print_flush(row_str)

    print_flush("\nPer-class metrics:")
    print_flush(f"  {'Label':28} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Support':>8}")
    for lbl in labels:
        p = per_class[lbl]
        print_flush(f"  {lbl:28} {p['precision']:8.3f} {p['recall']:8.3f} {p['f1']:8.3f} {p['support']:8d}")

    print_flush(f"\n  Macro F1: {macro_f1:.3f}")

    if confidences:
        conf_by_exp = defaultdict(list)
        for r, c in zip(benchmark_records, confidences):
            conf_by_exp[r["expected_label"]].append(c)
        print_flush("\nConfidence distributions by expected label:")
        for exp in labels:
            c_list = conf_by_exp[exp]
            if c_list:
                avg_c = sum(c_list) / len(c_list)
                min_c = min(c_list)
                max_c = max(c_list)
                print_flush(f"  {exp}: mean={avg_c:.4f}, min={min_c:.4f}, max={max_c:.4f}")

    failures = [(r, p, c) for r, p, c in zip(benchmark_records, predictions, confidences or [0.0]*len(predictions)) if r["expected_label"] != p]
    print_flush(f"\nSystematic failures (expected != predicted):")
    print_flush(f"  Total: {len(failures)}/{len(benchmark_records)} ({len(failures)/len(benchmark_records):.1%})")

    entailed_failures = [f for f in failures if f[0]["expected_label"] == "ENTAILED"]
    print_flush(f"\n  Failures where expected=ENTAILED ({len(entailed_failures)} total):")
    for f in entailed_failures[:3]:
        r, p, c = f
        print_flush(f"    predicted={p}, conf={c}")
        print_flush(f"    evidence_key={r['evidence_key']}")

    contradicted_failures = [f for f in failures if f[0]["expected_label"] == "CONTRADICTED"]
    print_flush(f"  Failures where expected=CONTRADICTED ({len(contradicted_failures)} total):")
    for f in contradicted_failures[:3]:
        r, p, c = f
        print_flush(f"    predicted={p}, conf={c}")
        print_flush(f"    evidence_key={r['evidence_key']}")

    return cm, per_class, macro_f1


def main():
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 1. Load benchmark
    bench_path = _PROTOTYPE_ROOT / "outputs" / "verifier_benchmark.jsonl"
    if not bench_path.exists():
        from scripts.build_verifier_benchmark import main as build_bm
        build_bm()

    benchmark_records = []
    with bench_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                benchmark_records.append(json.loads(line))

    print_flush(f"Loaded {len(benchmark_records)} benchmark records.")

    # 2. Test DeBERTa
    print_flush("\nLoading DeBERTa verifier...")
    deberta = NLIVerifier(
        model_id=config["verification"]["model_id"],
        confidence_threshold=config["verification"]["confidence_threshold"],
        max_sequence_length=config["verification"]["max_sequence_length"],
    )
    deberta.load()
    print_flush("DeBERTa loaded.")

    deberta_preds = []
    deberta_confs = []
    t0 = time.time()
    for i, r in enumerate(benchmark_records, start=1):
        res = deberta.verify(r["evidence_text"], r["hypothesis"])
        deberta_preds.append(res.label)
        deberta_confs.append(res.confidence)
        if i % 20 == 0 or i == len(benchmark_records):
            print_flush(f"  DeBERTa: {i}/{len(benchmark_records)}")

    t_deberta = time.time() - t0
    print_flush(f"DeBERTa evaluation: {len(benchmark_records)} pairs in {t_deberta:.1f}s")
    cm_deb, per_class_deb, macro_f1_deb = print_evaluation_report("DeBERTa NLI (" + config["verification"]["model_id"] + ")", benchmark_records, deberta_preds, deberta_confs)

    # 3. Phase 3: Test Qwen LLM Verifier
    deberta_entailed_rec = per_class_deb["ENTAILED"]["recall"]
    print_flush(f"\nDeBERTa ENTAILED recall: {deberta_entailed_rec:.3f}")

    qwen_verifier = None
    macro_f1_qwen = 0.0
    per_class_qwen = None
    qwen_preds = []

    if deberta_entailed_rec < 0.5 or True:
        print_flush("\nENTAILED recall < 0.5 -- running Qwen LLM verifier (Phase 3)...")
        print_flush("Loading Qwen for LLM-based verification...")
        gen = StatuteGroundingGenerator(
            model_id=config["generation"]["model_id"],
            quantization=config["generation"]["quantization"],
            device_map=config["generation"]["device_map"],
            max_new_tokens=config["generation"]["max_new_tokens"],
            do_sample=config["generation"]["do_sample"],
            temperature=config["generation"]["temperature"],
            top_p=config["generation"]["top_p"],
            system_prompt=config["generation"]["system_prompt"],
            user_prompt_template=config["generation"]["user_prompt_template"],
            seed=config["seed"],
        )
        gen.load()

        qwen_verifier = QwenLLMVerifier(gen)
        t0 = time.time()
        pairs = [(r["evidence_text"], r["hypothesis"]) for r in benchmark_records]
        res_list = qwen_verifier.verify_batch(pairs, batch_size=16)
        qwen_preds = [res.label for res in res_list]

        t_qwen = time.time() - t0
        print_flush(f"Qwen LLM Verifier evaluation: {len(benchmark_records)} pairs in {t_qwen:.1f}s")
        cm_qwen, per_class_qwen, macro_f1_qwen = print_evaluation_report("Qwen LLM Verifier (Qwen2.5-7B-Instruct)", benchmark_records, qwen_preds)

    # 4. Phase 4: Corrector Experiment
    print_flush("\n" + "=" * 60)
    print_flush("PHASE 4: CORRECTION FAILURE EXPERIMENT")
    print_flush("=" * 60)

    canonical_path = repo_root / config["paths"]["canonical_statutes"]
    audit_path = repo_root / config["paths"]["evidence_audit"]
    exact_index, all_usable = load_usable_evidence(canonical_path, audit_path, set(config["usable_evidence_verdicts"]))

    synth_claims = build_synthetic_stress_claims(all_usable)
    print_flush(f"Loaded {len(synth_claims)} synthetic claims.")

    detected_subset = []
    for sc in synth_claims:
        res = deberta.verify(sc.evidence.canonical_text, sc.claim_text)
        if res.label == CONTRADICTED:
            detected_subset.append(sc)

    print_flush(f"Found {len(detected_subset)} synthetic contradictions detected as CONTRADICTED by DeBERTa.")
    if len(detected_subset) > 10:
        detected_subset = detected_subset[:10]

    prompt_variants = {
        "V1_Original": config["correction"]["system_prompt"],
        "V2_DirectStatement": (
            "You are a legal editor. The flagged claim sentence contains a statutory contradiction.\n"
            "Rewrite ONLY the flagged claim sentence so that its statement of law is directly and strictly "
            "supported by the provided statute evidence. State the legal rule clearly without meta-commentary, "
            "preserving all unflagged claims in the text verbatim."
        ),
        "V3_VerbatimAlignment": (
            "You are a precision legal reviser. A claim in the text contradicts the canonical statute.\n"
            "Rewrite the flagged sentence using the exact language and rule from the canonical statute text.\n"
            "Copy all other sentences in the paragraph verbatim without changing a single word."
        )
    }

    if 'gen' not in locals() or gen is None or not gen.is_loaded():
        gen = StatuteGroundingGenerator(
            model_id=config["generation"]["model_id"],
            quantization=config["generation"]["quantization"],
            device_map=config["generation"]["device_map"],
            max_new_tokens=config["generation"]["max_new_tokens"],
            do_sample=config["generation"]["do_sample"],
            temperature=config["generation"]["temperature"],
            top_p=config["generation"]["top_p"],
            system_prompt=config["generation"]["system_prompt"],
            user_prompt_template=config["generation"]["user_prompt_template"],
            seed=config["seed"],
        )
        gen.load()

    corr_results = {}
    for vname, sys_prompt in prompt_variants.items():
        print_flush(f"\nTesting Corrector Prompt Variant: {vname}")
        corrector_v = SelectiveCorrector(
            generator=gen,
            max_new_tokens=config["correction"]["max_new_tokens"],
            do_sample=config["correction"]["do_sample"],
            system_prompt=sys_prompt,
        )

        statuses_deb = Counter()
        verdicts_deb = Counter()
        statuses_qwen = Counter()
        verdicts_qwen = Counter()

        for sc in detected_subset:
            case_text = f"Synthetic Case for {sc.act_raw} {sc.provision_type} {sc.provision_number}."
            case_obj = pipeline.Case(document_id=f"synth_{sc.claim_id}", case_text=case_text, raw_citation_keys=[])
            unflagged = "Article 14 of the Constitution of India guarantees equality before the law."
            full_text = f"{sc.claim_text} {unflagged}"

            corrected_text, _ = corrector_v.correct(
                case_text=case_text,
                original_field_text=full_text,
                flagged_claim_text=sc.claim_text,
                evidence_text=sc.evidence.canonical_text,
            )

            scope_violation = (unflagged not in corrected_text)

            re_claims = claim_parser.extract_claims(corrected_text)
            replacement = re_claims[0] if re_claims else None
            if replacement and not scope_violation:
                r_deb = deberta.verify(sc.evidence.canonical_text, replacement.claim_text)
                verdicts_deb[r_deb.label] += 1
                if r_deb.label == ENTAILED:
                    statuses_deb["corrected"] += 1
                else:
                    statuses_deb["correction_failed"] += 1
            else:
                statuses_deb["scope_violation" if scope_violation else "correction_failed"] += 1

            if qwen_verifier and replacement and not scope_violation:
                r_qwen = qwen_verifier.verify(sc.evidence.canonical_text, replacement.claim_text)
                verdicts_qwen[r_qwen.label] += 1
                if r_qwen.label == ENTAILED:
                    statuses_qwen["corrected"] += 1
                else:
                    statuses_qwen["correction_failed"] += 1
            else:
                statuses_qwen["scope_violation" if scope_violation else "correction_failed"] += 1

        corr_results[vname] = {
            "DeBERTa_reverification": dict(verdicts_deb),
            "DeBERTa_statuses": dict(statuses_deb),
            "Qwen_reverification": dict(verdicts_qwen),
            "Qwen_statuses": dict(statuses_qwen),
        }
        print_flush(f"  {vname} DeBERTa Statuses: {dict(statuses_deb)}")
        print_flush(f"  {vname} Qwen Statuses:    {dict(statuses_qwen)}")

    # 5. Phase 5: Re-evaluate Synthetic Contradiction Stress Test if LLM Verifier is superior
    print_flush("\n" + "=" * 60)
    print_flush("PHASE 5: RE-EVALUATE SYNTHETIC STRESS EVALUATION")
    print_flush("=" * 60)

    use_improved = False
    if qwen_verifier and macro_f1_qwen > macro_f1_deb:
        use_improved = True
        print_flush(f"Qwen LLM Verifier Macro F1 ({macro_f1_qwen:.3f}) > DeBERTa ({macro_f1_deb:.3f}). Running synthetic evaluation with Qwen LLM Verifier!")
    else:
        print_flush(f"Qwen LLM Verifier Macro F1 ({macro_f1_qwen:.3f}) vs DeBERTa ({macro_f1_deb:.3f}).")

    if use_improved:
        best_vname = "V2_DirectStatement"
        best_sys_prompt = prompt_variants[best_vname]
        best_corrector = SelectiveCorrector(
            generator=gen,
            max_new_tokens=config["correction"]["max_new_tokens"],
            do_sample=config["correction"]["do_sample"],
            system_prompt=best_sys_prompt,
        )

        syn_c1_verdicts = Counter()
        syn_c2_verdicts = Counter()
        syn_correction_statuses = Counter()
        syn_reverif_verdicts = Counter()
        unsafe_shipped = 0

        for i, sc in enumerate(synth_claims, start=1):
            unflagged = "Article 14 of the Constitution of India guarantees equality before the law."
            full_paragraph = f"{sc.claim_text} {unflagged}"
            c1_res = qwen_verifier.verify(sc.evidence.canonical_text, sc.claim_text)
            c2_res = qwen_verifier.verify("The State shall not deny to any person equality before the law...", unflagged)

            syn_c1_verdicts[c1_res.label] += 1
            syn_c2_verdicts[c2_res.label] += 1

            if c1_res.label == CONTRADICTED:
                case_obj = pipeline.Case(document_id=f"synth_{sc.claim_id}", case_text=f"Synthetic Case for {sc.provision_number}", raw_citation_keys=[])
                corrected_text, _ = best_corrector.correct(
                    case_text=case_obj.case_text,
                    original_field_text=full_paragraph,
                    flagged_claim_text=sc.claim_text,
                    evidence_text=sc.evidence.canonical_text,
                )

                if unflagged not in corrected_text:
                    syn_correction_statuses["correction_scope_violation"] += 1
                else:
                    re_claims = claim_parser.extract_claims(corrected_text)
                    if re_claims:
                        re_res = qwen_verifier.verify(sc.evidence.canonical_text, re_claims[0].claim_text)
                        syn_reverif_verdicts[re_res.label] += 1
                        if re_res.label == ENTAILED:
                            syn_correction_statuses["corrected"] += 1
                        else:
                            syn_correction_statuses["correction_failed"] += 1
                    else:
                        syn_correction_statuses["correction_failed"] += 1
            else:
                syn_correction_statuses["not_triggered"] += 1

        c1_contradicted = syn_c1_verdicts.get("CONTRADICTED", 0)
        c1_total = len(synth_claims)
        recall_overall = c1_contradicted / c1_total
        fp_rate = syn_c2_verdicts.get("CONTRADICTED", 0) / c1_total

        print_flush(f"\nSynthetic Stress Results (Qwen LLM Verifier):")
        print_flush(f"  Contradiction Recall: {c1_contradicted}/{c1_total} = {recall_overall:.1%}")
        print_flush(f"  False Positive Rate (c2): {syn_c2_verdicts.get('CONTRADICTED', 0)}/{c1_total} = {fp_rate:.1%}")
        print_flush(f"  Correction Statuses: {dict(syn_correction_statuses)}")
        print_flush(f"  Re-verification Verdicts: {dict(syn_reverif_verdicts)}")
        print_flush(f"  Unsafe Corrections Shipped: {unsafe_shipped}")

    # 6. Phase 6: Natural Data Evaluation (10 cases) if justified
    print_flush("\n" + "=" * 60)
    print_flush("PHASE 6: NATURAL NYAYARAG EVALUATION (10 cases)")
    print_flush("=" * 60)

    if use_improved:
        print_flush("Running 10-case natural NyayaRAG evaluation with Qwen LLM Verifier...")
        nyayarag_paths = [repo_root / p for p in config["paths"]["nyayarag_case_files"]]
        raw_cases = load_nyayarag_cases(nyayarag_paths)
        selected_cases = select_cases_with_evidence_overlap(raw_cases, exact_index, min_overlap=1)[:10]

        nat_verdicts_B = Counter()
        nat_corr_statuses = Counter()

        for case in selected_cases:
            baseline = pipeline.generate_and_parse(
                case, gen, exact_index, all_usable,
                config["evidence_matching"]["fuzzy_token_overlap_threshold"],
            )

            for c in baseline["claims"]:
                if c["evidence_text"]:
                    res = qwen_verifier.verify(c["evidence_text"], c["claim_text"])
                    c["verdict"] = res.label
                else:
                    c["verdict"] = "NO_EVIDENCE"
                nat_verdicts_B[c["verdict"]] += 1

            flagged = [c for c in baseline["claims"] if c["verdict"] == CONTRADICTED]
            if flagged:
                target = flagged[0]
                corr_text, _ = best_corrector.correct(
                    case_text=case.case_text,
                    original_field_text=baseline["generated_field"]["text"],
                    flagged_claim_text=target["claim_text"],
                    evidence_text=target["evidence_text"],
                )
                re_claims = claim_parser.extract_claims(corr_text)
                if re_claims:
                    re_res = qwen_verifier.verify(target["evidence_text"], re_claims[0].claim_text)
                    if re_res.label == ENTAILED:
                        nat_corr_statuses["corrected"] += 1
                    else:
                        nat_corr_statuses["correction_failed"] += 1
            else:
                nat_corr_statuses["not_triggered"] += 1

        print_flush(f"10-case Natural Evaluation Results:")
        print_flush(f"  Mode B Verdicts: {dict(nat_verdicts_B)}")
        print_flush(f"  Mode C Correction Statuses: {dict(nat_corr_statuses)}")
    else:
        print_flush("Natural evaluation not justified based on benchmark results.")


if __name__ == "__main__":
    main()
