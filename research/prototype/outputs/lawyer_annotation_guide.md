# Instructions for the Lawyer — Statutory Claim Annotation

_See root `README.md` § "Project Author Statement — 2026-09-03" for a subsequent status update from the project author. This does not change the instructions below._

## Why we need this

We built a small AI tool that reads a court case and writes a short
paragraph naming the laws (sections, articles, etc.) it thinks apply to
that case. We then automatically split that paragraph into individual
claims — one claim per law cited — and tried to find the actual text of
that law to check against.

Before we can trust the tool, we need a human legal expert to check its
work. **Your review is the real answer key ("gold standard") for this
project.** Everything produced before this — including a file called
`assumption_annotation.jsonl` — was only a provisional placeholder created
by an AI while waiting for you, and none of it should influence your
judgment. Please form your own opinion from the case PDF and your own
legal knowledge, not from anything the AI decided.

## What you're looking at

Open `lawyer_annotation.jsonl` in a text/JSON viewer. It contains 88 rows.
Each row is **one claim** — one sentence from the AI's output, naming one
specific law citation. The fields in each row:

| Field | What it means |
|---|---|
| `document_id` | Which court case this claim came from |
| `claim_text` | The actual sentence the AI wrote, naming a law |
| `extracted_citation` | The specific section/article the AI thinks this sentence is about (type, number, and act name) |
| `matched_evidence_text` | The text of that law our system found, or blank (`null`) if it found nothing |
| `automated_verdict`, `automated_confidence` | What our AI's checker decided on its own — **ignore these until after you've made up your own mind** (see below) |
| `lawyer_annotation` | **This is what you fill in.** Four blank fields, described below |

If you have the original PDF of the case, please use it as your main
reference. Where the PDF isn't available, use `document_id` to look up the
case and your own knowledge of the cited law.

## What to fill in, one row at a time

For each row, fill in these four fields inside `lawyer_annotation`:

### 1. `citation_valid` — write `YES`, `NO`, or `UNCERTAIN`

Question: **Is this a real, correctly-identified law citation?**
Look at `claim_text` and `extracted_citation` together.

- `YES` — Yes, this is a genuine section/article of a real law, correctly
  named (right number, right act).
- `NO` — No — the citation is wrong, garbled, made up, or doesn't actually
  match what the sentence says (for example: the wrong act was attached,
  or a number that isn't really a section number).
- `UNCERTAIN` — You genuinely can't tell from the sentence alone.

### 2. `evidence_entails_claim` — write `ENTAILED`, `CONTRADICTED`, `NOT_ENOUGH_INFORMATION`, or `UNCERTAIN`

Question: **Does the law's actual text (`matched_evidence_text`) support
what the claim sentence says about it?**

- `ENTAILED` — Yes, the law's text confirms what the claim says.
- `CONTRADICTED` — No, the law's text says something different from, or
  opposite to, what the claim says.
- `NOT_ENOUGH_INFORMATION` — The law's text is on the right topic but
  doesn't clearly confirm or deny the specific thing the claim says — OR
  `matched_evidence_text` is blank (nothing to compare against).
- `UNCERTAIN` — You've read both carefully and still can't decide (should
  be rare).

**Please base this only on `matched_evidence_text`** — not on your general
knowledge of what the law actually says elsewhere, and not on the outcome
of the case. We are specifically testing whether the *text our system
found* backs up the claim, since that's the piece our tool controls.

### 3. `evidence_relevance` — write `RELEVANT`, `NOT_RELEVANT`, or `UNCERTAIN`

Question: **Is `matched_evidence_text` actually about the same
section/article named in the claim, or did our system attach the wrong
law by mistake?**

This is different from question 2. A claim can have the *wrong* evidence
attached (`NOT_RELEVANT`) even if that wrong evidence happens to look like
it supports the claim by coincidence — and the *right* evidence can still
be attached (`RELEVANT`) even if it doesn't fully support the claim.

- `RELEVANT` — Yes, this is genuinely the section/article the claim cites.
- `NOT_RELEVANT` — No, this text is about a different section or law
  entirely.
- If `matched_evidence_text` is blank, write `UNCERTAIN` and note "no
  evidence found" in your notes (there's nothing to judge).

### 4. `annotator_notes` — free text, optional

Use this box for anything you want to flag: something that seemed clearly
wrong, something ambiguous you had to make a judgment call on, or any
other comment for our team. Leave it blank if you have nothing to add.

## Please do NOT do this

- **Do not look at `automated_verdict` or `automated_confidence` before
  deciding your own answer.** Form your opinion first from `claim_text`
  and `matched_evidence_text`. You may look at them afterward if you want
  to note a disagreement, but don't let them anchor your judgment.
- **Do not use or reference `assumption_annotation.jsonl`.** That file was
  a provisional AI guess made before your review — it is not a reference
  answer, and copying from it would defeat the purpose of your review.
- **Do not edit** `claim_text`, `extracted_citation`, or
  `matched_evidence_text` — those are locked as the system's actual
  output. If something there is wrong, say so in `annotator_notes` instead
  of changing it.
- **Do not skip a row** just because `matched_evidence_text` is blank —
  `citation_valid` can still usually be answered from `claim_text` alone.

## One last reminder

**This file, once you've filled it in, becomes the real gold standard for
this project.** Every other annotation we've produced so far — automated
verdicts and the placeholder assumption labels — will be compared against
your answers, not the other way around. Thank you.
