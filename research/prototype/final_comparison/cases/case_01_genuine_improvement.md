# Case 1 — Genuine improvement: ORIGINAL misses, CURRENT confirms ENTAILED

**Selection criterion**: from the 15 verdict flips in `final_validation_bare_vs_labeled_cpu_metrics.json`,
one single-citation, non-bundled claim, picked for narrative clarity (not the most favorable
confidence gap in the list).

**Source**: `outputs/final_validation_bare_vs_labeled_cpu_metrics.json` → `flips[9]`
(`document_id="2002_731"`, `claim_id="c4"`). Verification-only CPU re-check of an
already-matched natural claim — no new Qwen generation.

| | ORIGINAL (`premise_framing: bare`) | CURRENT (`premise_framing: labeled`) |
|---|---|---|
| Claim text | "Article 14 mandates that the state shall not deny to any person equality before the law or the equal protection of the laws within the territory of India." | *(identical — same generated claim, same evidence)* |
| Evidence | `Article 14 in Constitution of India` | *(identical)* |
| Verdict | **NOT_ENOUGH_INFORMATION** | **ENTAILED** |
| Confidence | 0.9951 | 0.9962 |

## What changed and why

Under `bare` framing, the NLI premise is the statute text alone. The claim explicitly
attributes its content to "Article 14" — a bare premise never says the words "Article 14",
so the model correctly reads the claim as talking about something the premise doesn't
confirm it's *about*, and returns NEI even though the substantive content matches. Under
`labeled` framing, the premise becomes `"Article 14 of Constitution of India: <statute
text>"`, which now matches the claim's own attribution — the model resolves to ENTAILED at
very high confidence (0.996).

## What this case does and does not show

- **Does show**: labeled framing recovers a correct ENTAILED verdict on a real, unmodified
  natural claim that bare framing could not reach, at high confidence, with no evidence
  change and no generation change — a clean, isolated framing effect.
- **Does not show**: that the claim's legal content is *actually* correct — no lawyer has
  reviewed it. It shows the automated verifier's own behavior changed, not a validated
  accuracy gain.

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author._

## Reproduce

```
python -c "
import json
d = json.load(open('research/prototype/outputs/final_validation_bare_vs_labeled_cpu_metrics.json', encoding='utf-8'))
print([f for f in d['flips'] if f['document_id']=='2002_731' and f['claim_id']=='c4'])
"
```
