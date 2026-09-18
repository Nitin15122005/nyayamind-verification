# T11_safety_gates

Every safety gate, when it was added, and whether the ORIGINAL system had it. ORIGINAL had exactly ONE.

| gate | source reference | present at ORIGINAL | commit added | fail-closed | what it blocks |
|---|---|---|---|---|---|
| Full-sentence scope check | pipeline.py:133-153 -> :462 | YES | 0e37525 | YES | every unflagged claim must reappear verbatim in the rewrite |
| Sibling regression net | pipeline.py:601 / :945 | NO | 100e263 (2026-08-27) | YES | an untouched sibling claim must not regress; INACTIVE unless atomic_scope_check is truthy |
| Unauthorized citation addition | pipeline.py:769-790 | NO | adf54aa (2026-09-09) | YES | the corrector may not introduce a citation that was not there |
| Ordinal integrity | pipeline.py:806-873 | NO | adf54aa (2026-09-09) | YES | reordered same-citation siblings cannot ship a verdict never computed against the real edit |
| Negation gate | pipeline.py:160 / :419 / :713-716 | NO | adf54aa (2026-09-09) | YES | negation-marked CONTRADICTED claims never enter the correction trigger; UNCONDITIONAL |
| Year-conflict veto | evidence_matcher.py:48 / :121 | NO | adf54aa (2026-09-09) | YES | retrieval-side: rejects a candidate whose year contradicts the citation; UNCONDITIONAL |
| Structural span validation | pipeline.py:1151 | NO | 8cf8fa9 (2026-09-12) | YES | assertion-aware path only - currently DORMANT (assertion_aware=false) |

## Notes

- All gates are FAIL-CLOSED: on any doubt the ORIGINAL text ships unchanged.
- Most of these gates were discovered adversarially and are covered by REGRESSION TESTS rather than by data-batch measurement - see T12.
- The negation gate, year-conflict veto, injection guard and ordinal guard are UNCONDITIONAL and not controllable by any config lever. This is why the configuration baseline is strictly more gated than the real pre-2026-09-09 system (discrepancy C-1).
