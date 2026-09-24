#!/usr/bin/env python3
"""Paired correction and safety analysis over the completed 2x2 run."""
from __future__ import annotations
import argparse, datetime, json
from pathlib import Path

def read_rows(path):
    return {x["document_id"]: x for x in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}

def summarize_side(rows):
    corrections=[r.get("correction") or {} for r in rows.values()]
    attempts=[c for c in corrections if int(c.get("attempts",0) or 0)>0]
    statuses={}
    for c in corrections: statuses[c.get("status","unknown")]=statuses.get(c.get("status","unknown"),0)+1
    def count_status(prefix): return sum(str(c.get("status","")).startswith(prefix) for c in corrections)
    return {"n_inputs":len(rows),"triggers":sum(bool(c.get("triggered_for_claim_id")) for c in corrections),"attempts":len(attempts),"accepted":sum(c.get("status")=="corrected" for c in corrections),"rejected_or_failed":sum(bool(int(c.get("attempts",0) or 0)) and c.get("status")!="corrected" for c in corrections),"status_counts":statuses,
      "scope_gate_rejections":count_status("correction_scope_violation"),"citation_identity_rejections":count_status("correction_unauthorized_addition"),"ordinal_gate_rejections":count_status("correction_ordinal_ambiguous"),"sibling_regressions":count_status("correction_sibling_regression"),"full_reverification_failures":sum(bool(c.get("reverification")) and c.get("status")!="corrected" for c in corrections),"unsafe_shipments":sum(c.get("status")=="corrected" and (c.get("reverification") or {}).get("verdict")!="ENTAILED" for c in corrections),"unsafe_shipments_per_attempt":sum(c.get("status")=="corrected" and (c.get("reverification") or {}).get("verdict")!="ENTAILED" for c in corrections)/len(attempts) if attempts else None,"negation_caveat_claims":sum(bool(c.get("negation_contradiction_caveat")) for r in rows.values() for c in r.get("claims",[]))}

def compare(run, left_name, right_name):
    l=read_rows(run/left_name/"predictions.jsonl"); r=read_rows(run/right_name/"predictions.jsonl")
    paired=[]
    for did in sorted(l.keys() & r.keys()):
        x,y=l[did],r[did]; cx=x.get("correction") or {}; cy=y.get("correction") or {}
        ax=int(cx.get("attempts",0) or 0)>0; ay=int(cy.get("attempts",0) or 0)>0
        common=ax and ay and cx.get("triggered_for_claim_id")==cy.get("triggered_for_claim_id")
        def target(row, corr):
            return next((c for c in row.get("claims",[]) if c.get("claim_id")==corr.get("triggered_for_claim_id")),None)
        left_claim=target(x,cx);right_claim=target(y,cy)
        paired.append({"document_id":did,"same_flagged_case_and_claim":common,"left_condition":left_name,"right_condition":right_name,
          "left_original_text":(x.get("generated_field") or {}).get("text"),"right_original_text":(y.get("generated_field") or {}).get("text"),
          "left_flagged_claim":left_claim,"right_flagged_claim":right_claim,"left_old_verdict":left_claim.get("verdict") if left_claim else None,"right_old_verdict":right_claim.get("verdict") if right_claim else None,
          "left_evidence":left_claim.get("evidence_text") if left_claim else None,"right_evidence":right_claim.get("evidence_text") if right_claim else None,
          "left_correction":cx,"right_correction":cy,"left_safety_gate_result":cx.get("status"),"right_safety_gate_result":cy.get("status"),
          "left_siblings":x.get("claims"),"right_siblings":y.get("claims"),"left_final_reverification":cx.get("reverification"),"right_final_reverification":cy.get("reverification"),
          "left_final":x.get("final_field"),"right_final":y.get("final_field"),"left_decision":cx.get("status"),"right_decision":cy.get("status")})
    common=[x for x in paired if x["same_flagged_case_and_claim"]]
    outcome={"left":summarize_side(l),"right":summarize_side(r),"n_paired_inputs":len(paired),"n_same_flagged_case_and_claim":len(common),
      "common_case_contradictions_resolved_by_left":sum(x["left_old_verdict"]=="CONTRADICTED" and x["left_decision"]=="corrected" and (x["left_final_reverification"] or {}).get("verdict")=="ENTAILED" for x in common),
      "common_case_contradictions_resolved_by_right":sum(x["right_old_verdict"]=="CONTRADICTED" and x["right_decision"]=="corrected" and (x["right_final_reverification"] or {}).get("verdict")=="ENTAILED" for x in common),
      "interpretation":"Natural data have no independent correctness labels; acceptance and re-verification are observable policy outcomes, not legal correctness."}
    return outcome,paired

def main():
    p=argparse.ArgumentParser();p.add_argument("--run-dir",required=True);a=p.parse_args();run=Path(a.run_dir).resolve()
    if "research_v2" not in run.parts or not run.is_dir():raise ValueError("run-dir must point to an existing research_v2 full-pipeline run")
    comparisons={"primary_stack":("baseline_baseline_C","v2_v2_C"),"same_deberta_verifier_generator_effect":("baseline_baseline_C","v2_baseline_C"),"same_modernbert_verifier_generator_effect":("baseline_v2_C","v2_v2_C")}
    result={};case_groups={}
    for name,(left,right) in comparisons.items():
        if not (run/left/"predictions.jsonl").exists() or not (run/right/"predictions.jsonl").exists(): continue
        result[name],case_groups[name]=compare(run,left,right)
    dest=Path(__file__).resolve().parents[1]/"results"/"paired"/"correction";dest.mkdir(parents=True,exist_ok=True);stamp=datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    (dest/f"{stamp}_cases.jsonl").write_text("".join(json.dumps({"comparison":name,**row},ensure_ascii=False)+"\n" for name,rows in case_groups.items() for row in rows),encoding="utf-8")
    (dest/f"{stamp}_summary.json").write_text(json.dumps({"pipeline_run":str(run),"comparisons":result},indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
