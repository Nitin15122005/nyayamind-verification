# T04_verifier_confusion_matrices

Both confusion matrices in long format, GOLD-01 n=420. Same 420 items in both arms.

| arm | premise_framing | gold_label | predicted_label | count | cell_type |
|---|---|---|---|---|---|
| ORIGINAL | bare | ENTAILED | ENTAILED | 92 | correct |
| ORIGINAL | bare | ENTAILED | CONTRADICTED | 0 | error |
| ORIGINAL | bare | ENTAILED | NOT_ENOUGH_INFORMATION | 92 | error |
| ORIGINAL | bare | CONTRADICTED | ENTAILED | 2 | error |
| ORIGINAL | bare | CONTRADICTED | CONTRADICTED | 103 | correct |
| ORIGINAL | bare | CONTRADICTED | NOT_ENOUGH_INFORMATION | 13 | error |
| ORIGINAL | bare | NOT_ENOUGH_INFORMATION | ENTAILED | 0 | error |
| ORIGINAL | bare | NOT_ENOUGH_INFORMATION | CONTRADICTED | 5 | error |
| ORIGINAL | bare | NOT_ENOUGH_INFORMATION | NOT_ENOUGH_INFORMATION | 113 | correct |
| LATEST | labeled | ENTAILED | ENTAILED | 184 | correct |
| LATEST | labeled | ENTAILED | CONTRADICTED | 0 | error |
| LATEST | labeled | ENTAILED | NOT_ENOUGH_INFORMATION | 0 | error |
| LATEST | labeled | CONTRADICTED | ENTAILED | 5 | error |
| LATEST | labeled | CONTRADICTED | CONTRADICTED | 110 | correct |
| LATEST | labeled | CONTRADICTED | NOT_ENOUGH_INFORMATION | 3 | error |
| LATEST | labeled | NOT_ENOUGH_INFORMATION | ENTAILED | 0 | error |
| LATEST | labeled | NOT_ENOUGH_INFORMATION | CONTRADICTED | 4 | error |
| LATEST | labeled | NOT_ENOUGH_INFORMATION | NOT_ENOUGH_INFORMATION | 114 | correct |
