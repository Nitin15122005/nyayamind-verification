#!/usr/bin/env python3
"""
Comprehensive analysis of NyayaMind research prototype evaluation outputs.
Reads from existing JSONL files — does NOT run any inference.
"""
import json
import os
from collections import Counter

BASE = os.path.join(os.path.dirname(__file__), "..", "outputs")

def load_jsonl(filename):
    path = os.path.join(BASE, filename)
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

# ============================================================
# PART 1: NATURAL TARGETED EVALUATION
# ============================================================
print("=" * 70)
print("PART 1: NATURAL TARGETED EVALUATION (run_natural_targeted.jsonl)")
print("=" * 70)

nat = load_jsonl("run_natural_targeted.jsonl")
print(f"Total documents evaluated: {len(nat)}")

for mode_key in ["mode_A", "mode_B", "mode_C"]:
    mode_label = mode_key[-1]
    total_claims = 0
    verdicts = Counter()
    evidence_methods = Counter()
    correction_statuses = Counter()
    reverif_verdicts = Counter()
    final_sources = Counter()

    for rec in nat:
        m = rec.get(mode_key, {})
        claims = m.get("claims", [])
        total_claims += len(claims)
        for c in claims:
            v = c.get("verdict")
            if v:
                verdicts[v] += 1
            em = c.get("evidence_match_method", "unknown")
            evidence_methods[em] += 1

        # Verification summary
        verif = m.get("verification", {})
        counts = verif.get("counts", {})
        
        # Correction
        corr = m.get("correction", {})
        status = corr.get("status", "unknown")
        correction_statuses[status] += 1
        
        if corr.get("reverification"):
            rv = corr["reverification"].get("verdict")
            if rv:
                reverif_verdicts[rv] += 1
        
        # Final field source
        ff = m.get("final_field", {})
        src = ff.get("source", "unknown")
        final_sources[src] += 1

    print(f"\n--- Mode {mode_label} ---")
    print(f"  Total claims: {total_claims}")
    print(f"  Verdicts: {dict(verdicts)}")
    print(f"  Evidence methods: {dict(evidence_methods)}")
    print(f"  Correction statuses: {dict(correction_statuses)}")
    if reverif_verdicts:
        print(f"  Re-verification verdicts: {dict(reverif_verdicts)}")
    print(f"  Final field sources: {dict(final_sources)}")

# Aggregate Mode B/C claim-level verdicts for comparison
print("\n--- Natural Evaluation: Claim-level Verdict Comparison (B vs C) ---")
for mode_key in ["mode_B", "mode_C"]:
    mode_label = mode_key[-1]
    verdicts = Counter()
    for rec in nat:
        m = rec.get(mode_key, {})
        for c in m.get("claims", []):
            v = c.get("verdict")
            if v:
                verdicts[v] += 1
    print(f"  Mode {mode_label}: {dict(verdicts)}")

# ============================================================
# PART 2: SYNTHETIC STRESS EVALUATION
# ============================================================
print("\n" + "=" * 70)
print("PART 2: SYNTHETIC STRESS EVALUATION (run_synthetic_stress.jsonl)")
print("=" * 70)

syn = load_jsonl("run_synthetic_stress.jsonl")
print(f"Total synthetic records: {len(syn)}")

# Mutation types
mutation_types = Counter()
for r in syn:
    mutation_types[r.get("transform_rule", "unknown")] += 1
print(f"Mutation types: {dict(mutation_types)}")

# Condition A: No verification
print("\n--- Condition A (No Verification) ---")
cA_verdicts = Counter()
cA_evidence = Counter()
for r in syn:
    cA = r.get("condition_A", {})
    for c in cA.get("claims", []):
        v = c.get("verdict")
        if v:
            cA_verdicts[v] += 1
        cA_evidence[c.get("evidence_match_method", "unknown")] += 1
print(f"  Verdicts: {dict(cA_verdicts)}")
print(f"  Evidence methods: {dict(cA_evidence)}")

# Condition B: Verification
print("\n--- Condition B (Verification) ---")
cB_c1_verdicts = Counter()
cB_c2_verdicts = Counter()
cB_all_verdicts = Counter()
for r in syn:
    cB = r.get("condition_B", {})
    for c in cB.get("claims", []):
        v = c.get("verdict")
        if v:
            cB_all_verdicts[v] += 1
        if c.get("claim_id") == "c1":
            cB_c1_verdicts[v] += 1
        elif c.get("claim_id") == "c2":
            cB_c2_verdicts[v] += 1

print(f"  All claims verdicts: {dict(cB_all_verdicts)}")
print(f"  Injected contradictions (c1) verdicts: {dict(cB_c1_verdicts)}")
print(f"  Unflagged true claims (c2) verdicts: {dict(cB_c2_verdicts)}")

# Detection recall
c1_total = sum(cB_c1_verdicts.values())
c1_contradicted = cB_c1_verdicts.get("CONTRADICTED", 0)
c1_no_evidence = cB_c1_verdicts.get("NO_EVIDENCE", 0)
c1_with_evidence = c1_total - c1_no_evidence
recall_overall = c1_contradicted / c1_total if c1_total > 0 else 0
recall_with_evidence = c1_contradicted / c1_with_evidence if c1_with_evidence > 0 else 0
print(f"\n  CONTRADICTED Detection Recall (overall): {c1_contradicted}/{c1_total} = {recall_overall:.2%}")
print(f"  CONTRADICTED Detection Recall (evidence found): {c1_contradicted}/{c1_with_evidence} = {recall_with_evidence:.2%}")

# False positive check on c2
c2_contradicted = cB_c2_verdicts.get("CONTRADICTED", 0)
c2_total = sum(cB_c2_verdicts.values())
print(f"  False positives on unflagged claims (c2): {c2_contradicted}/{c2_total}")

# ============================================================
# PART 3: SELECTIVE CORRECTION (Condition C) — Detailed
# ============================================================
print("\n" + "=" * 70)
print("PART 3: SELECTIVE CORRECTION ANALYSIS (Synthetic Condition C)")
print("=" * 70)

corr_statuses = Counter()
corr_sources = Counter()
reverif = Counter()
corr_triggered_count = 0
corr_attempt_total = 0
corrections_became_entailed = 0
corrections_remained_nei = 0
corrections_remained_contradicted = 0
correction_scope_violation = 0
unsafe_shipped = 0  # correction shipped but still CONTRADICTED on re-verification

for r in syn:
    cC = r.get("condition_C", {})
    source = cC.get("source", "unknown")
    corr_sources[source] += 1
    corr_obj = cC.get("correction", {})
    status = corr_obj.get("status", "unknown")
    corr_statuses[status] += 1
    attempts = corr_obj.get("attempts", 0)
    corr_attempt_total += attempts

    if corr_obj.get("triggered_for_claim_id"):
        corr_triggered_count += 1

    # Re-verification analysis
    rever = corr_obj.get("reverification")
    if rever and isinstance(rever, dict):
        rv = rever.get("verdict")
        reverif[rv] += 1
        if rv == "ENTAILED":
            corrections_became_entailed += 1
        elif rv == "NOT_ENOUGH_INFORMATION":
            corrections_remained_nei += 1
        elif rv == "CONTRADICTED":
            corrections_remained_contradicted += 1
            # If source is "corrected", this is an unsafe shipment
            if source == "corrected":
                unsafe_shipped += 1

    # Check for scope violation
    if status == "correction_scope_violation":
        correction_scope_violation += 1

# Also count correction_failed as "shipped original" which is still CONTRADICTED
# correction_failed means Qwen corrected but re-verification didn't get ENTAILED, 
# so original was kept (source = "correction_failed" means original shipped)
print(f"  Total CONTRADICTED claims (Mode B c1): {c1_contradicted}")
print(f"  Correction triggers (Mode C): {corr_triggered_count}")
print(f"  Total correction attempts: {corr_attempt_total}")
print(f"  Correction statuses: {dict(corr_statuses)}")
print(f"  Final text sources: {dict(corr_sources)}")
print(f"  Re-verification verdicts on rewritten claims: {dict(reverif)}")
print(f"  Corrections became ENTAILED: {corrections_became_entailed}")
print(f"  Corrections remained NEI: {corrections_remained_nei}")
print(f"  Corrections remained CONTRADICTED: {corrections_remained_contradicted}")
print(f"  Correction scope violations: {correction_scope_violation}")
print(f"  Unsafe corrections shipped (CONTRADICTED after correction): {unsafe_shipped}")

# Unflagged-claim preservation: check c2 verdicts in C
cC_c2_verdicts = Counter()
for r in syn:
    cC = r.get("condition_C", {})
    for c in cC.get("claims", []):
        if c.get("claim_id") == "c2":
            v = c.get("verdict")
            if v:
                cC_c2_verdicts[v] += 1
print(f"\n  Unflagged true claim (c2) preservation in C: {dict(cC_c2_verdicts)}")
c2_c_contradicted = cC_c2_verdicts.get("CONTRADICTED", 0)
print(f"  c2 false positive CONTRADICTED in C: {c2_c_contradicted}")

# ============================================================
# PART 4: NATURAL TARGETED — CORRECTION DETAIL
# ============================================================
print("\n" + "=" * 70)
print("PART 4: NATURAL TARGETED — CORRECTION DETAIL (Mode C)")
print("=" * 70)

nat_corr_statuses = Counter()
nat_corr_triggered = 0
nat_corr_attempts = 0
nat_reverif = Counter()
nat_final_sources = Counter()

for rec in nat:
    m = rec.get("mode_C", {})
    corr = m.get("correction", {})
    status = corr.get("status", "unknown")
    nat_corr_statuses[status] += 1
    attempts = corr.get("attempts", 0)
    nat_corr_attempts += attempts
    if corr.get("triggered_for_claim_id"):
        nat_corr_triggered += 1
    if corr.get("reverification") and isinstance(corr["reverification"], dict):
        rv = corr["reverification"].get("verdict")
        if rv:
            nat_reverif[rv] += 1
    ff = m.get("final_field", {})
    nat_final_sources[ff.get("source", "unknown")] += 1

print(f"  Total documents: {len(nat)}")
print(f"  Correction triggers: {nat_corr_triggered}")
print(f"  Total correction attempts: {nat_corr_attempts}")
print(f"  Correction statuses: {dict(nat_corr_statuses)}")
print(f"  Re-verification verdicts: {dict(nat_reverif)}")
print(f"  Final text sources: {dict(nat_final_sources)}")

# ============================================================
# PART 5: N=30 EVALUATION SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("PART 5: N=30 A/B/C EVALUATION (run_A/B/C_n30.jsonl)")
print("=" * 70)

for mode in ["A", "B", "C"]:
    fname = f"run_{mode}_n30.jsonl"
    try:
        recs = load_jsonl(fname)
        total_claims = 0
        verdicts = Counter()
        corr_st = Counter()
        for rec in recs:
            for c in rec.get("claims", []):
                total_claims += 1
                v = c.get("verdict")
                if v:
                    verdicts[v] += 1
            corr = rec.get("correction", {})
            corr_st[corr.get("status", "unknown")] += 1
        print(f"  Mode {mode}: {len(recs)} docs, {total_claims} claims")
        print(f"    Verdicts: {dict(verdicts)}")
        print(f"    Correction statuses: {dict(corr_st)}")
    except Exception as e:
        print(f"  Mode {mode}: Error loading — {e}")

# ============================================================
# PART 6: TIMING ANALYSIS (Natural Targeted)
# ============================================================
print("\n" + "=" * 70)
print("PART 6: TIMING ANALYSIS")
print("=" * 70)

timing_sums = {"A": 0, "B": 0, "C": 0}
timing_counts = {"A": 0, "B": 0, "C": 0}
for rec in nat:
    t = rec.get("timing", {})
    for mode in ["A", "B", "C"]:
        mt = t.get(mode, {})
        total = mt.get("total_seconds", 0)
        if total > 0:
            timing_sums[mode] += total
            timing_counts[mode] += 1

for mode in ["A", "B", "C"]:
    cnt = timing_counts[mode]
    avg = timing_sums[mode] / cnt if cnt > 0 else 0
    print(f"  Mode {mode}: avg {avg:.1f}s/doc over {cnt} docs, total {timing_sums[mode]:.0f}s")

print("\n✅ Analysis complete.")
