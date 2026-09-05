# Evidence Corpus — Input Source

**This directory intentionally contains no copied data files.** The evidence corpus is
already clean, small, frozen, and directly usable at its original location — copying it
would create a second source of truth for no benefit, contrary to this step's instruction
to prefer referencing over copying wherever the original is already suitable.

## What this is

The statute/citation evidence corpus consumed by `src/evidence_matcher.py::match_evidence`
(stage 3, evidence retrieval) — never generated text, never a claim, never a verdict.

## Where it originates

| | |
|---|---|
| v0 | `research/data/evidence/canonical_statutes.jsonl` + `evidence_audit.jsonl` — 63 raw / 59 usable records |
| v1 | `research/data/evidence/canonical_statutes_v1.jsonl` + `evidence_audit_v1.jsonl` — 82 + 82 records |
| Merged (production) | v0+v1 via `src/data_loader.py::load_usable_evidence_from_config`, `use_evidence_v1: true` — **136 usable records**, live-verified in STEP 1/2 |

## What one record represents

One statute/citation key's independently-sourced canonical text (IndianKanoon.org,
third-party — India Code returned HTTP 403 on every attempt), plus a separately-keyed
audit-verdict record. Full schema in `../README.md` §1-3.

## Which component consumes it

`src/evidence_matcher.py::match_evidence` (exact-key lookup, then fuzzy act-token-overlap
fallback) against the pool returned by `src/data_loader.py::load_usable_evidence[_from_config]`.

## Classification

**N/A / input corpus** — not GOLD, BEHAVIOR, METRIC-ONLY, or PROVISIONAL. It is a
retrieval corpus, not a labeled test set: `audit_verdict` labels the evidence record's own
trustworthiness (was this citation's text correctly sourced?), not any claim's entailment
status. See `MANIFEST.md` row IN-01/IN-02/IN-03 for this same classification.

## What can legitimately be measured from it

Coverage (what fraction of real claims resolve to a match vs. `NO_EVIDENCE`), and
comparative coverage between v0-only and v0+v1 pools (McNemar χ²=13.07, p≈0.0003, +7.1pp,
n=209 — see `../../comparisons/metric_based/`). **Not** a source of verifier ground truth
by itself.

## What must NOT be claimed

That this corpus is official/government-sourced (it is third-party, IndianKanoon-derived,
explicitly not India Code text), or that it is complete (top-100/top-143 citation keys by
frequency only, not the full ~8,100 distinct NyayaRAG citations).

## Reference, not copy

| | |
|---|---|
| Reference path | `research/data/evidence/` (all 4 files) |
| Frozen? | Yes |
| SHA-256 | recorded in `../README.md` §1-2 and `../MANIFEST.md` |
| Byte-identical to source? | N/A — not copied, referenced in place |
| Why referenced rather than copied | Already frozen, already read-only by design (`config/prototype.yaml`'s own comment: "Evidence files are READ-ONLY inputs. Never write to these."), small, and copying would create a second, driftable source of truth for the same data |
