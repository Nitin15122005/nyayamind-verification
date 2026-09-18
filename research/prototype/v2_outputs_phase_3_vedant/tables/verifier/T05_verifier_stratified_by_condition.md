# T05_verifier_stratified_by_condition

**THE REQUIRED CAVEAT TABLE.** GOLD-01 split by benchmark construction condition. ATTRIBUTED conditions are those whose hypothesis names the provision while the ORIGINAL bare premise omits it by construction.

| stratum | n | ORIGINAL accuracy | LATEST accuracy | delta | items fixed | items broken | sign test p | verdict |
|---|---|---|---|---|---|---|---|---|
| ALL_420 | 420 | 0.7333 | 0.9714 | 0.2381 | 100 | 0 | 1.578e-30 | significant |
| ATTRIBUTED_conditions | 151 | 0.3179 | 0.9735 | 0.6556 | 99 | 0 | 3.155e-30 | significant |
| NON_ATTRIBUTED_conditions | 269 | 0.9665 | 0.9703 | 0.0037 | 1 | 0 | 1 | NOT SIGNIFICANT |
|   C1_negated_bare | 59 | 0.9322 | 0.9322 | 0.0000 | 0 | 0 | 1 | NOT SIGNIFICANT |
|   C2_negated_attributed [ATTRIBUTED] | 59 | 0.8136 | 0.9322 | 0.1186 | 7 | 0 | 0.01562 | significant |
|   E1_verbatim | 59 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 | 1 | NOT SIGNIFICANT |
|   E2_verbatim_attributed [ATTRIBUTED] | 59 | 0.0000 | 1.0000 | 1.0000 | 59 | 0 | 3.469e-18 | significant |
|   E3_paraphrase_bare | 33 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 | 1 | NOT SIGNIFICANT |
|   E4_paraphrase_attributed [ATTRIBUTED] | 33 | 0.0000 | 1.0000 | 1.0000 | 33 | 0 | 2.328e-10 | significant |
|   N1_other_provision | 59 | 0.9153 | 0.9322 | 0.0169 | 1 | 0 | 1 | NOT SIGNIFICANT |
|   N2_procedural_addition | 59 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 | 1 | NOT SIGNIFICANT |

## Notes

- 99.0% of every item the LATEST framing fixes on GOLD-01 lies in the attributed conditions, where the ORIGINAL bare premise was constructed to omit the very identifier the hypothesis asserts. On the 269 non-attributed items the two arms are near-identical (accuracy 0.9665 -> 0.9703, sign test p=1.0000). The headline macro F1 0.749 -> 0.968 must therefore always be reported WITH this stratification. It is strong evidence that labeled framing removes a premise/hypothesis mismatch; it is NOT evidence of a general +0.22 macro-F1 improvement in legal reasoning.
- It still matters: real generated statutory claims ARE overwhelmingly attributed, so the attributed conditions are the realistic ones. The caveat constrains the SIZE and GENERALITY of the number, not whether the change was worth making.
