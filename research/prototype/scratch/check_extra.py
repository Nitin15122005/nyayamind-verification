import json
recs = [json.loads(l) for l in open('research/prototype/outputs/run_synthetic_stress.jsonl','r',encoding='utf-8') if l.strip()]
extra_ids = ['s18','s20','s28','s35','s36','s37','s49','s55','s59']
for r in recs:
    if r['synthetic_claim_id'] in extra_ids:
        sid = r['synthetic_claim_id']
        # Check C claims for sub_reason
        c_claims = r.get('condition_C',{}).get('claims',[])
        c_c1 = [c for c in c_claims if c.get('claim_id')=='c1']
        if c_c1:
            c = c_c1[0]
            print(f"{sid}: C_c1 verdict={c['verdict']}, sub_reason={c.get('sub_reason')}, confidence={c.get('confidence')}")
        # Also check B claims
        b_claims = r.get('condition_B',{}).get('claims',[])
        b_c1 = [c for c in b_claims if c.get('claim_id')=='c1']
        if b_c1:
            c = b_c1[0]
            print(f"  B_c1 verdict={c['verdict']}, sub_reason={c.get('sub_reason')}, confidence={c.get('confidence')}")
