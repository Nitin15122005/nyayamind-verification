# Case 7 — Labeled-framing improvement (same claim, same evidence, two framings)

**Document ID:** `1982_49` &nbsp;·&nbsp; **Claim ID:** `c1` &nbsp;·&nbsp; **Sources:** `research/prototype/outputs/natural_candidates_50_gpu_bare.jsonl` (bare) vs. `research/prototype/outputs/natural_candidates_50_gpu_labeled.jsonl` (labeled) — same batch, same generated text, same matched evidence; only the verifier's premise framing differs.

## Claim (identical in both runs)

> "The Industrial Disputes Act, 1947, specifically Section 25F requires that no
> workman who has been in continuous service for at least one year can be retrenched
> without satisfying certain pre-conditions, including providing notice,
> compensation, and an opportunity to be heard."

## Evidence (identical in both runs)

**Evidence ID:** `Section 25F in The Industrial Disputes Act, 1947`

> "No workman employed in any industry who has been in continuous service for not
> less than one year shall be retrenched until: (a) he has been given one month's
> notice in writing, or wages in lieu thereof; and (b) he has been paid retrenchment
> compensation equivalent to fifteen days' average pay for every completed year of
> continuous service."

## Bare framing (premise = evidence text alone)

| Field | Value |
|---|---|
| Verdict | NOT_ENOUGH_INFORMATION |
| Confidence | 0.888 |

## Labeled framing (premise = "Section 25F of the Industrial Disputes Act, 1947: <evidence text>")

| Field | Value |
|---|---|
| Verdict | **ENTAILED** |
| Confidence | 0.973 |

## Why it matters

Nothing about the underlying evidence or claim changed — only whether the verifier's
premise explicitly names the provision it's quoting. Under bare framing, the model
never sees that this text *is* "Section 25F," so a claim that explicitly attributes
its content to Section 25F is only weakly supported from the premise's point of view;
labeling the premise resolves that gap. This is one concrete instance of the
project-wide pattern behind the `premise_framing: "labeled"` production default (8x
more ENTAILED-per-matched-claim in the 100-case pooled labeled-vs-bare comparison —
see `reports/verifier_analysis.md`).

**What this does NOT establish:** that labeled framing is unconditionally better —
`FINAL_PRODUCTION_CONFIG.md` §1 records a genuine counter-signal on an older,
bundled-claim-heavy provisional-assumption-gold set where labeled framing agreed
*less* often than bare. This single case is one instance of the more common
direction, not proof the effect is universal.
