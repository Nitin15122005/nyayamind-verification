# DIAGRAM INDEX

All 14 diagrams are **structural**: they carry no performance numbers. Every stage name,
function reference and gate name comes from the audited source at HEAD `fb4e98f` or the
original codebase at root commit `0e37525`.

| diagram | title | arm | what it shows | source of truth |
|---|---|---|---|---|
| `diagrams/01_original_architecture/D01_original_architecture.png` | ORIGINAL NyayaMind architecture | ORIGINAL | End-to-end stages of the original codebase, and what it lacked | `git show 0e37525:research/prototype/src/{pipeline,claim_parser,evidence_matcher,verifier,corrector}.py` |
| `diagrams/02_latest_architecture/D02_latest_architecture.png` | LATEST NyayaMind architecture | LATEST | End-to-end stages at HEAD with new/changed components marked | `research/prototype/src/ @ fb4e98f; config/prototype.yaml` |
| `diagrams/03_side_by_side/D03_original_vs_latest_side_by_side.png` | ORIGINAL vs LATEST side by side | BOTH | Stage-for-stage comparison with changed components highlighted and the unchanged-models banner | `0e37525 and fb4e98f source; config/prototype.yaml` |
| `diagrams/04_end_to_end_pipeline/D04_complete_latest_pipeline.png` | Complete LATEST pipeline | LATEST | All 26 stages in execution order with function references | `research/prototype/src/pipeline.py, claim_parser.py, evidence_matcher.py, verifier.py, corrector.py @ fb4e98f` |
| `diagrams/05_claim_parsing/D05_claim_parsing_flow.png` | Claim parsing flow | BOTH | Stages 3-7 with the ORIGINAL limitation beside each step | `claim_parser.py:466/597/379/814/970/1050 @ fb4e98f; 0e37525:claim_parser.py` |
| `diagrams/06_evidence_retrieval/D06_evidence_retrieval_flow.png` | Evidence retrieval flow | BOTH | The match ladder, the year-conflict veto, the Jaccard threshold, and both pool sizes | `evidence_matcher.py:48/59/69/121/170 @ fb4e98f` |
| `diagrams/07_nli_verification/D07_nli_verification_flow.png` | NLI verification flow | BOTH | Premise construction bare vs labeled (literal template), hypothesis selection, threshold downgrade | `verifier.py:78/178/218-222; pipeline.py:55/401-412 @ fb4e98f` |
| `diagrams/08_verdict/D08_verdict_assignment.png` | Verdict assignment | BOTH | Four verdicts, the confidence downgrade, and the negation caveat | `verifier.py:218-222; pipeline.py:160/419 @ fb4e98f` |
| `diagrams/09_correction_reverification/D09_correction_and_reverification.png` | Correction and re-verification | LATEST | Trigger → rewrite → gate chain → re-verify → ship or reject | `pipeline.py:714-730/462/769-790/806-873/878-932/601/945; corrector.py:43 @ fb4e98f` |
| `diagrams/10_safety/D10_safety_gate_chain.png` | Safety gate chain | BOTH | Every gate, when it was added, and whether it existed at ORIGINAL | `pipeline.py:133-153/601/769-790/806-873/160/419/1151; evidence_matcher.py:48 — commits 0e37525/100e263/adf54aa/8cf8fa9` |
| `diagrams/11_final_answer/D11_final_answer_assembly.png` | Final answer assembly | BOTH | How final_field is produced and what final_field.source records | `pipeline.py:1401-1508 @ fb4e98f` |
| `diagrams/12_data_flow/D12_data_flow.png` | Data flow | LATEST | Inputs, pipeline, outputs, and the read-only guarantees | `config/prototype.yaml paths; data_loader.py docstring @ fb4e98f` |
| `diagrams/13_new_components/D13_new_components.png` | New components at LATEST | LATEST | Everything added since ORIGINAL, grouped by subsystem, with production status | `config/prototype.yaml live values; src/ @ fb4e98f; change inventory` |
| `diagrams/14_flaw_fix_behavior/D14_flaw_fix_behavior.png` | Flaw → Fix → Latest behaviour | BOTH | The six best-evidenced changes, with honest evidence strength per row | `V2 metrics + change inventory; src/ @ fb4e98f` |

## Colour conventions (consistent across the whole package)

| colour | meaning |
|---|---|
| grey `#8C8C8C` | ORIGINAL NyayaMind |
| blue `#2A6099` | LATEST NyayaMind |
| green `#3F8F4F` | component new or changed since ORIGINAL / production status |
| red `#C44E52` | fail-closed safety gate |
| amber `#DDA63A` | EXPERIMENTAL, built but OFF in production |
| light grey `#9E9E9E` | EVALUATED AND REJECTED |
