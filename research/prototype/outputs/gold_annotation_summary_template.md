# Gold Annotation Summary — TEMPLATE (fill in after annotation completes)

This is a blank template. Every count below is a placeholder ("__") to be
filled in once human annotation of `gold_annotation.jsonl` is complete.
Do not fill this in before annotation starts.

## Coverage (known now, from the completed pipeline run)
- Total claims: 88
- Total cases: 29
- Claims with matched evidence: 38
- Claims without evidence (no_evidence): 50

## Citation validity (`citation_valid`) — fill in after annotation
| Value | Count | % of 88 |
|---|---|---|
| YES | __ | __ |
| NO | __ | __ |
| UNCERTAIN | __ | __ |

## Evidence entailment (`evidence_entails_claim`) — fill in after annotation
| Value | Count | % of 88 |
|---|---|---|
| ENTAILED | __ | __ |
| CONTRADICTED | __ | __ |
| NOT_ENOUGH_INFORMATION | __ | __ |
| UNCERTAIN | __ | __ |

## Evidence relevance (`evidence_relevance`) — fill in after annotation
| Value | Count | % of 88 |
|---|---|---|
| RELEVANT | __ | __ |
| NOT_RELEVANT | __ | __ |
| UNCERTAIN | __ | __ |

## Automated-vs-human agreement — fill in after annotation
Computed only over the 38 claims with matched evidence
(automated_verdict is one of ENTAILED/CONTRADICTED/NOT_ENOUGH_INFORMATION
for these; the 50 NO_EVIDENCE claims are excluded from
this comparison since automated_verdict is NO_EVIDENCE for those, a
different label space than evidence_entails_claim).

- Agreement definition: `annotation.evidence_entails_claim == automated_verdict`
  (UNCERTAIN human labels excluded from the denominator — decide before
  finalizing whether to treat UNCERTAIN as disagreement or exclude it, and
  state the choice here).
- Number of comparable claims (evidence matched, human label not UNCERTAIN): __
- Number of agreements: __
- Agreement rate: __%
- Confusion breakdown (human label x automated_verdict): __ (fill in a
  small table once counts are available)

## Notes
- These are preliminary counts pending full annotation; do not report them
  as final results until every row has a non-blank `annotation` block.
