import json
from collections import Counter

filepath = "research/prototype/outputs/run_synthetic_stress.jsonl"

records = []
with open(filepath, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print(f"Total synthetic evaluation records: {len(records)}")

# 1. Total claims, injected contradictions
total_claims = 0
injected_contradictions = 0
mutation_types = Counter()

# Condition B (Verification) metrics
verdicts_B = Counter()
evidence_matches = Counter()

# Condition C (Selective Correction) metrics
correction_statuses = Counter()
reverification_verdicts = Counter()

for r in records:
    mutation_types[r.get("mutation_type", "unknown")] += 1
    
    # Injected claim details
    orig_text = r.get("original_synthetic_text", "")
    # Condition B
    cB = r.get("condition_B", {})
    claims_B = cB.get("claims", [])
    for c in claims_B:
        total_claims += 1
        verdict = c.get("verdict")
        verdicts_B[verdict] += 1
        match_method = c.get("evidence_match_method")
        evidence_matches[match_method] += 1
        # The first claim c1 is the mutated synthetic claim
        if c.get("claim_id") == "c1":
            injected_contradictions += 1

    # Condition C
    cC = r.get("condition_C", {})
    source_C = cC.get("source", "")
    corr_obj = cC.get("correction", {})
    status = corr_obj.get("status", "not_triggered" if source_C == "uncorrected" else "unknown")
    correction_statuses[status] += 1
    
    if "reverification" in corr_obj and corr_obj["reverification"]:
        rever = corr_obj["reverification"]
        reverification_verdicts[rever.get("verdict")] += 1

print("\n--- SYNTHETIC STRESS EVALUATION METRICS ---")
print(f"Total synthetic claims processed: {total_claims}")
print(f"Total injected statutory contradictions (c1): {injected_contradictions}")
print(f"Mutation types distribution: {dict(mutation_types)}")
print(f"\nCondition B Verdicts across all claims: {dict(verdicts_B)}")
print(f"Evidence Match Methods: {dict(evidence_matches)}")

# Detection recall for c1 injected contradictions
c1_verdicts = Counter()
for r in records:
    claims_B = r.get("condition_B", {}).get("claims", [])
    for c in claims_B:
        if c.get("claim_id") == "c1":
            c1_verdicts[c.get("verdict")] += 1

print(f"\nVerifier Verdicts on Injected Contradictions (c1): {dict(c1_verdicts)}")
contradicted_count = c1_verdicts.get("CONTRADICTED", 0)
nei_count = c1_verdicts.get("NOT_ENOUGH_INFORMATION", 0)
no_ev_count = c1_verdicts.get("NO_EVIDENCE", 0)
entailed_count = c1_verdicts.get("ENTAILED", 0)

recall_overall = contradicted_count / injected_contradictions if injected_contradictions > 0 else 0
recall_where_evidence_matched = contradicted_count / (injected_contradictions - no_ev_count) if (injected_contradictions - no_ev_count) > 0 else 0

print(f"CONTRADICTED Detection Recall (Overall 59): {contradicted_count}/{injected_contradictions} ({recall_overall:.2%})")
print(f"CONTRADICTED Detection Recall (Where Evidence Exists): {contradicted_count}/{injected_contradictions - no_ev_count} ({recall_where_evidence_matched:.2%})")

# Unflagged claim (c2) False Positives
c2_verdicts = Counter()
for r in records:
    claims_B = r.get("condition_B", {}).get("claims", [])
    for c in claims_B:
        if c.get("claim_id") == "c2":
            c2_verdicts[c.get("verdict")] += 1

print(f"\nVerifier Verdicts on Unflagged True Claims (c2): {dict(c2_verdicts)}")

print(f"\nCondition C Correction Statuses: {dict(correction_statuses)}")
print(f"Re-verification Verdicts on Rewritten Claims: {dict(reverification_verdicts)}")
