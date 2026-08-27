# "Respectively" Atomic-Claim Diagnosis (Phase 1)

**Prototype v0 · NyayaMind statutory-grounding verification layer**
Generated 2026-08-26. Concise diagnosis per the task brief, produced before the Phase 2
GPU natural evaluation. Full implementation: `src/claim_parser.py`
(`Claim.assertion_spans`, `_assign_respectively_spans`), `src/pipeline.py`
(`_scope_violation(..., use_assertion_spans=True)`, `atomic_scope_check: "assertion_spans"`).

---

## 1. Representation chosen

**A list of independently-required VERBATIM fragments (`assertion_spans`), not a
synthetic combined sentence.** For a "respectively" claim (e.g. citation 149 in
*"...sections 302, 149, 323, and 34 of the IPC, 1860, which respectively deal with
murder, criminal conspiracy, voluntarily causing hurt, and abetting..."*), instead of
building one coherent hypothesis string, the claim gets:

```
assertion_spans = ["149", "criminal conspiracy"]
```

— the citation's own bare provision number (protects against a sibling's number being
silently altered) and its own paired description item, positionally matched to the Nth
citation in the Nth description slot (the only correct reading of "respectively"). The
scope check (`atomic_scope_check: "assertion_spans"`) requires **all** fragments in the
list to still be present as substrings of the corrected text — not concatenated,
compared as one string, or reordered.

Every other bundled-sentence pattern from the prior phase (semicolon clause, "while"
clause, parenthetical gloss) still produces a single-fragment `assertion_spans =
[assertion_text]`, so this is a pure superset — no existing claim's representation
changed.

## 2. Why this does not fabricate text

Every element of `assertion_spans` is obtained by **progressively slicing the original
sentence string** — never by concatenating two spans together, reordering words, or
generating new text. The number fragment is a `re.search` match on the sentence itself;
the description fragment comes from splitting a substring of the sentence
(`_respectively_items_zone` → `_split_list_items`, both operating on Python string slices)
— transitively, every output item is provably a contiguous substring of the model's own
generated text. A dedicated test asserts this directly:

```python
for c in claims:
    for fragment in c.assertion_spans:
        assert fragment in s          # s = the original sentence
```

The alternative considered and **rejected**: building one recombined sentence like
"Section 149 of the IPC deals with criminal conspiracy" by joining the citation mention
and its description together. This was rejected in the prior phase and remains rejected
here — joining two disjoint spans with invented connective words ("of the IPC deals
with...") is exactly the kind of synthesis this project has never done anywhere, for
premises or for claims.

## 3. Previously blocked cases it can now safely separate

**Proven correct in isolation** (10 new regression tests, `test_respectively_claims.py`
+ 4 in `test_pipeline_mock.py`): a scope violation legacy checking would reject — editing
only the flagged citation's own description in a "respectively" sentence — now ships
under `assertion_spans` mode, including an explicit end-to-end test on the flagship
`1991_110` sentence (4 citations, one shared sentence; correcting citation 149's own
description ships while citations 302/323/34's content stays required and verified
byte-identical).

**On the 6 real cases from the n=50 GPU experiment: 0/6 additionally unblocked**
(`outputs/atomic_scope_check_replay_v2.md`). Diagnosed precisely for the two
"respectively"-pattern cases specifically:

- `2009_431`/c2 (target: citation 324): the real edit Qwen made changed **citation 300's
  own number** ("300"→"302"), not the target's content at all. A genuine, correct scope
  violation — the corrector touched a sibling citation, not the flagged one.
- `1991_110`/c2 (target: citation 149, the flagship mislabeling): the real edit removed
  "non-cognizable" from **citation 34's own description**, leaving 149's actual
  mislabeling ("criminal conspiracy") completely untouched. Also a genuine, correct
  scope violation — and notably, even if it had shipped, it would not have fixed the
  problem that triggered the correction in the first place.

**This is not a limitation of the representation — it is the representation correctly
identifying that, in both real cases available to test it against, Qwen's own edit
did not respect the citation boundary it was asked to respect.** The mechanism
discriminates precisely between "edit confined to the flagged citation" (ships) and
"edit touched a different citation" (still blocked), exactly as designed; it happens
that neither of the two real respectively-pattern attempts in this project's history is
the former.

## 4. What remains intentionally unsupported

- **Ambiguous respectively constructions fail closed by design and are tested**:
  more than one `respectively` in a sentence, no `which` anchor to locate the item list,
  more than one `which`, an item count that doesn't exactly match the citation count
  (both directions — too few or too many), an empty items zone, and a sentence already
  resolved by an earlier mechanism (semicolon/while/parenthetical) — all leave
  `assertion_spans` at its safe default rather than guess.
- **Verification hypothesis precision is out of scope, deliberately, still.** Exactly as
  in the prior phase, `assertion_spans`/`assertion_text` are never wired into
  `apply_verification`'s hypothesis — that remains `claim_text` (the full sentence) for
  every claim, respectively-pattern or not. This mechanism only ever affects the
  post-correction scope-violation check.
- **No semantic content matching.** Items are paired to citations by position only,
  never by guessing which description "sounds like" which provision — the only
  linguistically correct reading of "respectively," and the only one that cannot
  silently mismatch.

## 5. Test suite impact

145 → 163 tests (+18: 14 in the new `tests/test_respectively_claims.py`, 4 new
`assertion_spans` end-to-end tests in `tests/test_pipeline_mock.py`, including the
flagship case). All passing; zero regressions on the 145 pre-existing tests.
`run_mvp.py --check` passes.
