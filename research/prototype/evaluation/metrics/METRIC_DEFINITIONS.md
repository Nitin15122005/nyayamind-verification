# Legitimate Natural-Data Metric Definitions (STEP 6)

Defined **before** running any inference, per this step's explicit requirement. Every
metric below is descriptive or paired-comparative. **None of them measures accuracy,
precision, recall, or F1 against an independent correctness label**, because no such
label exists for any natural-data record in this project.

## 1. Evidence coverage

**Formula**: `claims with usable evidence / total claims`
**Numerator**: count of claims where `evidence_match_method != "no_evidence"` (i.e. an
exact or fuzzy match against the usable evidence pool was found).
**Denominator**: total claims extracted from the generated text(s) in scope.
**Interpretation**: how often the retrieval stage supplied usable evidence for a claim.
**Does NOT prove**: that the evidence found is legally correct for the claim, or that a
claim with no evidence found is itself wrong — only that retrieval did or did not
surface a matching record in the corpus.

## 2. NO_EVIDENCE rate

**Formula**: `claims with evidence_match_method == "no_evidence" / total claims`
**Interpretation**: the complement of evidence coverage — how often retrieval could not
resolve a citation to any record in the pool.
**Does NOT prove**: an incorrect citation was made by the generator; the underlying
citation may be entirely accurate but simply outside this project's ~140-citation
corpus (a documented, known limitation — see `research/data/evidence/README.md`).

## 3. Verdict distribution

**Formula**: count of claims falling into each of `{ENTAILED, CONTRADICTED,
NOT_ENOUGH_INFORMATION, NO_EVIDENCE}` (the four actual production states — `UNKNOWN` is
not a state this codebase produces; `NOT_ENOUGH_INFORMATION` is the closest analog).
**Interpretation**: how the verifier's judgments are distributed across the evaluated
claims.
**Does NOT prove**: that ENTAILED claims are legally accurate or that CONTRADICTED
claims are legally wrong — only what the small NLI model's statistical judgment was,
exactly as `src/verifier.py`'s own disclaimer states ("NLI statistical confidence, not a
legal-correctness determination").

## 4. Confidence distribution

**Formula**: descriptive statistics (mean, median, quartiles) of the verifier's
`confidence` field, overall and broken out by verdict.
**Interpretation**: how decisively the model reached its verdicts.
**Does NOT prove**: correctness — a high-confidence verdict is a high-confidence
*model* judgment, not a validated fact.

## 5. Evidence retrieval behavior

**Formula**: per claim, whether a match was found (`match_method`: `exact`, `fuzzy`, or
`no_evidence`), and which specific evidence record (`evidence_id`) was retrieved.
**Interpretation**: describes retrieval mechanics — exact-key hits vs. fuzzy-fallback
hits vs. misses.
**Does NOT prove**: retrieval accuracy in a legal sense — only which retrieval path the
deterministic matcher took.

## 6. Claim parsing behavior

**Formula**: count of claims extracted per generated text; presence/absence of a
resolvable `citation_extracted`.
**Interpretation**: how many citation-bearing sentences the deterministic parser found.
**Does NOT prove**: that the parser correctly captured every citation a human would
identify — only what this specific regex-based extractor produced.

## 7. Contradiction detection counts (raw, not "accuracy")

**Formula**: raw count of claims with `verdict == CONTRADICTED`.
**Interpretation**: how many times, out of the claims evaluated, the verifier's
statistical judgment was CONTRADICTED.
**Explicitly NOT**: "contradiction accuracy," "contradiction recall," or any percentage
implying a known-correct denominator of *actually* contradictory claims — natural data
carries no such label. (Contradiction *recall* as a legitimate metric exists only for
GOLD-02, the synthetic stress set, where every record is contradictory by construction —
see STEP 4. That number must never be conflated with a natural-data count.)

## 8. Re-verification behavior (where available)

**Formula**: for the 209-paired dataset's historical correction attempts, and any fresh
re-verification performed in this step, the verdict before vs. after a premise-framing or
evidence-pool change.
**Interpretation**: whether re-verifying the same claim/evidence pair under a different
configuration setting changes the verifier's output.
**Does NOT prove**: which configuration was "more correct" — only that the outputs
differ, and how.

## 9. Correction behavior (descriptive only, historical data only)

Where existing historical correction outputs (e.g. `outputs/final_gpu_validation_corrections_detail.jsonl`)
are analyzed in this step, they are analyzed **descriptively** (status counts: shipped,
`correction_failed`, `correction_scope_violation`) — **no new Qwen correction is
generated in this step.**
**Does NOT prove**: that a shipped correction was legally accurate — only that it passed
the mechanical ENTAILED-only shipping gate.

## 10. Paired change categories (209-claim set)

**Formula**: for each of the 209 claim positions, aligned by ordinal position within the
same case (confirmed identical `claim_text` and `document_id` order between arms —
verified in `NATURAL_DATA_INVENTORY.md`), categorize the change between Arm A and Arm B
as: unchanged evidence status, evidence gained (NO_EVIDENCE→matched), evidence lost
(matched→NO_EVIDENCE), unchanged verdict, verdict changed (and to what).
**Interpretation**: a purely mechanical, paired description of what changed between two
configurations on identical underlying claims.
**Does NOT prove**: that a "gained evidence" or "changed verdict" claim is now correct —
only that the described mechanical state changed.

## 11. Paired statistical test (McNemar's, evidence-coverage binary event only)

Reproducing this project's own existing methodology (`outputs/final_gpu_validation.md`):
**binary event** = "did this claim receive usable evidence (yes/no)?", tested pairwise
between Arm A and Arm B on the same 209 claims. This is the exact test already used in
this project's history for this exact comparison — no new hypothesis is invented here.
**Interpretation**: whether the evidence-pool change (v0→v0+v1) produced a
statistically detectable shift in how often claims receive usable evidence.
**Does NOT prove**: legal correctness of the evidence found — only that the *rate* of
finding *some* usable evidence changed.

## Coverage/regression counts

Counts of claims moving from evidence→NO_EVIDENCE ("regression," in the narrow,
mechanical sense of losing a previously-available match) or NO_EVIDENCE→evidence
("coverage gain") between arms — reported as raw counts and rates, per item 10 above.

---

## Forbidden terminology in this step's artifacts (enforced in Phase 11)

"accuracy", "precision", "recall", "F1" (for natural data), "correctness",
"ground truth", "legal accuracy", "lawyer validated" — none of these may appear
attached to a natural-data number anywhere in this step's output unless an
independently established expected label exists for that exact record (which, for
natural data, it never does in this project).
