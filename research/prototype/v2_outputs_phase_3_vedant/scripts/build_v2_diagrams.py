#!/usr/bin/env python3
"""
V2 architecture and flow diagrams (14 PNGs).

These are STRUCTURAL diagrams: they carry no performance numbers. Every stage name,
function reference and gate name is taken from the audited source at HEAD `fb4e98f`
and from the original codebase at root commit `0e37525`.

Invariants:
  - ORIGINAL is always grey (C_ORIGINAL); LATEST is always blue (C_LATEST).
  - A component that is EXPERIMENTAL or REJECTED is never drawn as production.
  - Nothing is invented: if it is on a diagram, it exists in the source.

Emits diagrams/diagram_index.json describing each one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

_V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v2_style import C_ORIGINAL, C_LATEST, C_INTERMEDIATE, save, plt  # noqa: E402

D = _V2 / "diagrams"
INDEX: list[dict] = []

# palette
NEW = "#3F8F4F"        # component that did not exist at ORIGINAL
GATE = "#C44E52"       # safety gate
EXPERIMENTAL = "#DDA63A"
REJECTED = "#9E9E9E"
INK = "#1A1A1A"
MUTED = "#5A5A5A"


def idx(fname, title, shows, truth, arm):
    INDEX.append({
        "diagram_file": f"diagrams/{fname}",
        "title": title,
        "what_it_shows": shows,
        "source_of_truth": truth,
        "original_or_latest_or_both": arm,
    })


def canvas(w=13.0, h=8.6):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.grid(False)
    return fig, ax


def box(ax, x, y, w, h, text, fc="#FFFFFF", ec=C_LATEST, lw=1.6, fs=9.0,
        tc=INK, bold=False, alpha=1.0, style="round,pad=0.35"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=lw,
                                edgecolor=ec, facecolor=fc, alpha=alpha, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=3, linespacing=1.35,
            fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, color=MUTED, lw=1.5, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=13, linewidth=lw, color=color,
                                 linestyle=ls, zorder=1,
                                 shrinkA=2, shrinkB=2))


def title(ax, main, sub=""):
    ax.text(50, 98, main, ha="center", va="top", fontsize=15, fontweight="bold", color=INK)
    if sub:
        ax.text(50, 93.6, sub, ha="center", va="top", fontsize=9.6, color=MUTED, linespacing=1.4)


def note(ax, text, y=1.5, fs=8.2):
    ax.text(50, y, text, ha="center", va="bottom", fontsize=fs, color=MUTED, linespacing=1.45)


def legend(ax, items, x=1, y=88, fs=8.4):
    handles = [mpatches.Patch(facecolor=c, edgecolor=c, label=l) for l, c in items]
    lg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(x / 100, y / 100),
                   fontsize=fs, frameon=False, handlelength=1.1, ncol=len(items))
    return lg


# ---------------------------------------------------------------- D01 / D02
def linear_stack(ax, stages, x, w, y_top, y_bot, ec, fc="#FFFFFF", fs=8.6, gap=1.6):
    n = len(stages)
    h = (y_top - y_bot - gap * (n - 1)) / n
    ys = []
    for i, s in enumerate(stages):
        y = y_top - h - i * (h + gap)
        ys.append(y)
        if isinstance(s, tuple):
            label, col = s
        else:
            label, col = s, ec
        box(ax, x, y, w, h, label, fc=fc, ec=col, fs=fs)
        if i:
            arrow(ax, x + w / 2, ys[i - 1], x + w / 2, y + h, color=MUTED, lw=1.3)
    return ys, h


ORIG_STAGES = [
    "Case text (NyayaRAG)",
    "Generate Statutory Grounding\nQwen2.5-7B-Instruct · 4-bit NF4 · greedy",
    "Sentence split\nclaim_parser.split_sentences",
    "Citation extraction\none Claim per citation\nClaim = {claim_id, claim_text, citation_extracted}",
    "Evidence match  (v0 pool: 59 usable records)\nexact → exact-ignoring-subsection → Jaccard ≥ 0.8",
    "NLI verification  DeBERTa-v3-base-mnli-fever-anli\npremise = RAW statute text (unlabelled)\nhypothesis = FULL claim sentence",
    "Verdict + confidence < 0.70 → NEI\nENTAILED / CONTRADICTED / NEI / NO_EVIDENCE",
    "Selective correction\nwhole-paragraph Qwen rewrite · first flagged claim · 1 attempt",
    ("SINGLE SAFETY GATE\nfull-sentence scope check  (pipeline.py:133-153)", GATE),
    "Re-verify (1 pass, bare premise, full sentence)\nship only if ENTAILED",
    "final_field",
]

LATEST_STAGES = [
    "Case text (NyayaRAG)",
    "Generate Statutory Grounding\nQwen2.5-7B-Instruct · 4-bit NF4 · greedy  (UNCHANGED)",
    ("Sentence split + Art./Arts. re-merge\nclaim_parser.py:466", NEW),
    ("Citation extraction → assertion narrowing → 'respectively' spans\n→ field-wide act inheritance   (claim_parser.py:597/814/970/1050)", NEW),
    ("Evidence match  (v1 merged pool: 136 usable records)\nexact → loose-subsection → Jaccard ≥ 0.8  + YEAR-CONFLICT VETO", NEW),
    ("NLI verification  DeBERTa-v3-base-mnli-fever-anli  (UNCHANGED MODEL)\npremise = \"<Type> <N> of <Act>: <text>\"  (labeled)\nhypothesis = narrow assertion_text when available", NEW),
    "Verdict + confidence < 0.70 → NEI\n+ negation caveat flag  (pipeline.py:160/419)",
    "Selective correction — LEGACY whole-paragraph rewrite\n(assertion-aware splice path built but OFF)",
    ("SAFETY GATE CHAIN (fail-closed)\nscope · unauthorized citation · ordinal integrity · sibling regression", GATE),
    "Re-match + re-verify with narrow hypothesis\nship ONLY if status=='corrected' AND re-verify ENTAILED",
    "final_field  (+ final_field.source records why)",
]


def d01():
    fig, ax = canvas(11.0, 9.4)
    title(ax, "D01 · ORIGINAL NyayaMind architecture",
          "Root commit 0e37525 · 2026-08-13 · the system before any modification")
    linear_stack(ax, ORIG_STAGES, 12, 76, 89, 8, ec=C_ORIGINAL, fc="#F5F5F5", fs=8.4)
    note(ax, "Exactly ONE safety gate. No assertion spans, no acronym/alias normalisation, no Art./Arts. handling,\n"
             "no year-conflict veto, no citation-injection guard, no ordinal-integrity guard, no sibling-regression net.\n"
             "Measured behaviour on 30 real cases: 38/88 claims resolved to evidence, every verdict NEI, correction triggered 0/30.",
         y=1.0)
    p = save(fig, D / "01_original_architecture" / "D01_original_architecture.png")
    idx("01_original_architecture/D01_original_architecture.png",
        "ORIGINAL NyayaMind architecture",
        "End-to-end stages of the original codebase, and what it lacked",
        "git show 0e37525:research/prototype/src/{pipeline,claim_parser,evidence_matcher,verifier,corrector}.py",
        "ORIGINAL")


def d02():
    fig, ax = canvas(11.6, 9.8)
    title(ax, "D02 · LATEST NyayaMind architecture",
          "HEAD fb4e98f · 2026-09-12 · production configuration")
    linear_stack(ax, LATEST_STAGES, 9, 82, 89, 8, ec=C_LATEST, fc="#FFFFFF", fs=8.3)
    legend(ax, [("new or changed since ORIGINAL", NEW), ("fail-closed safety gate", GATE)], x=8, y=92.5)
    note(ax, "The MODELS ARE UNCHANGED from ORIGINAL — same Qwen2.5-7B-Instruct (one instance reused for generation and correction)\n"
             "and the same DeBERTa-v3-base-mnli-fever-anli. Every difference is a pipeline or configuration change.\n"
             "correction.assertion_aware = false, so the LEGACY correction path is the live one.",
         y=1.0)
    p = save(fig, D / "02_latest_architecture" / "D02_latest_architecture.png")
    idx("02_latest_architecture/D02_latest_architecture.png",
        "LATEST NyayaMind architecture",
        "End-to-end stages at HEAD with new/changed components marked",
        "research/prototype/src/ @ fb4e98f; config/prototype.yaml",
        "LATEST")


def d03():
    fig, ax = canvas(15.0, 10.0)
    title(ax, "D03 · ORIGINAL vs LATEST, stage for stage")
    box(ax, 6, 89.8, 88, 4.8,
        "THE MODELS NEVER CHANGED  —  generation + correction: Qwen/Qwen2.5-7B-Instruct (4-bit NF4, greedy, one instance reused)\n"
        "verification: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli.   Every difference below is a pipeline or configuration change.",
        fc="#EEF3F8", ec=C_LATEST, fs=8.3, bold=False)
    ax.text(25, 86.8, "ORIGINAL  ·  0e37525", ha="center", fontsize=11.5, fontweight="bold", color=C_ORIGINAL)
    ax.text(75, 86.8, "LATEST  ·  fb4e98f", ha="center", fontsize=11.5, fontweight="bold", color=C_LATEST)

    pairs = [
        ("Generation\nQwen2.5-7B 4-bit greedy", "Generation\nQwen2.5-7B 4-bit greedy", False),
        ("Sentence split\n(no abbreviation awareness)", "Sentence split\n+ Art./Arts. re-merge", True),
        ("Citation extraction\nClaim = id, text, citation", "Citation extraction + assertion_text\n+ assertion_spans + 'respectively'", True),
        ("Act normalisation\nno acronym/alias handling", "Act normalisation\nIPC / CrPC / CPC aliases, act-bleed fix", True),
        ("Evidence pool\n59 usable records · 10 Acts", "Evidence pool\n136 usable records · 22 Acts", True),
        ("Retrieval\nexact → loose → Jaccard ≥ 0.8", "Retrieval\nsame ladder + YEAR-CONFLICT VETO", True),
        ("NLI premise\nraw statute text (bare)", "NLI premise\n\"<Type> <N> of <Act>: <text>\" (labeled)", True),
        ("NLI hypothesis\nfull claim sentence", "NLI hypothesis\nnarrow assertion_text when available", True),
        ("Verdict\n4 verdicts, <0.70 → NEI", "Verdict\nsame + negation caveat flag", True),
        ("Correction\nwhole-paragraph rewrite", "Correction\nwhole-paragraph rewrite (LEGACY, live)", False),
        ("Safety gates\nONE: full-sentence scope check", "Safety gates\nscope(span) · citation · ordinal · sibling", True),
        ("Re-verification\n1 pass, bare, full sentence", "Re-verification\n1 pass, labeled, narrow hypothesis", True),
    ]
    y0, h, gap = 78.8, 5.3, 1.05
    for i, (l, r, changed) in enumerate(pairs):
        y = y0 - i * (h + gap)
        box(ax, 3, y, 44, h, l, fc="#F5F5F5", ec=C_ORIGINAL, fs=8.0)
        box(ax, 53, y, 44, h, r, fc="#FFFFFF", ec=(NEW if changed else C_LATEST),
            lw=2.0 if changed else 1.4, fs=8.0)
        arrow(ax, 47.4, y + h / 2, 52.6, y + h / 2,
              color=(NEW if changed else "#C8C8C8"), lw=1.7 if changed else 1.1)
    note(ax, "Green outline = changed between ORIGINAL and LATEST.  Generation and the legacy correction mechanism are unchanged.",
         y=0.8, fs=8.6)
    p = save(fig, D / "03_side_by_side" / "D03_original_vs_latest_side_by_side.png")
    idx("03_side_by_side/D03_original_vs_latest_side_by_side.png",
        "ORIGINAL vs LATEST side by side",
        "Stage-for-stage comparison with changed components highlighted and the unchanged-models banner",
        "0e37525 and fb4e98f source; config/prototype.yaml",
        "BOTH")


def d04():
    fig, ax = canvas(15.4, 9.6)
    title(ax, "D04 · Complete LATEST pipeline", "HEAD fb4e98f · execution order with real function references")
    cols = [
        ("SETUP", [
            "0a  Evidence load → 136 records\ndata_loader.py:127",
            "0b  Model load\ngenerator.py:65 · verifier.py:131\ncorrector.py:31 (reuses Qwen)",
            "1  Case entry / mode gate\npipeline.py:1359 run_case",
            "2  Generation (greedy, seeded, 200 tok)\ngenerator.py:123",
        ], C_LATEST),
        ("PARSE", [
            "3  Sentence split + Art./Arts. re-merge\nclaim_parser.py:466",
            "4  Citation extraction\nclaim_parser.py:597",
            "5  Assertion narrowing (4 ordered passes)\nclaim_parser.py:814",
            "6  'Respectively' spans\nclaim_parser.py:970",
            "7  Field-wide act inheritance\nclaim_parser.py:1050 (never invents)",
        ], NEW),
        ("RETRIEVE + VERIFY", [
            "8  Match: exact → loose → fuzzy\nevidence_matcher.py:69",
            "8a  Year-conflict veto\nevidence_matcher.py:48 / :121",
            "8b  Jaccard |A∩B|/|A∪B| ≥ 0.8\nevidence_matcher.py:59",
            "9  NO_EVIDENCE taxonomy (diagnostic)\nevidence_matcher.py:170",
            "10  Premise (labeled)\npipeline.py:55 → verifier.py:78",
            "11  Hypothesis selection\npipeline.py:401-412",
            "12  NLI verify + truncation probe\nverifier.py:178",
            "13  Verdict, <0.70 → NEI\nverifier.py:218-222",
            "14  Negation caveat flag\npipeline.py:160 / :419",
        ], C_LATEST),
        ("CORRECT + GATE + SHIP", [
            "15  Dispatch → LEGACY path\npipeline.py:1394-1400",
            "16  Trigger: first flagged claim only\npipeline.py:96 / :714-730",
            "17  Whole-paragraph rewrite (220 tok)\ncorrector.py:43",
            "18  GATE scope violation\npipeline.py:462 / :423",
            "19  GATE unauthorized citation\npipeline.py:769-790",
            "20-21  Ordinal lookup + GATE\npipeline.py:806-873",
            "22-23  Re-match + re-verify (narrow)\npipeline.py:878-932",
            "24  GATE sibling regression\npipeline.py:601 / :945",
            "25-26  final_field + record\npipeline.py:1401-1508",
        ], C_LATEST),
    ]
    xs = [2.0, 26.0, 50.0, 74.0]
    w = 22.5
    for (name, items, col), x in zip(cols, xs):
        head_col = GATE if name.startswith("CORRECT") else col
        ax.text(x + w / 2, 89.0, name, ha="center", fontsize=10.5, fontweight="bold", color=head_col)
        n = len(items)
        top, bot, gap = 86.5, 7.0, 1.0
        h = (top - bot - gap * (n - 1)) / n
        for i, t in enumerate(items):
            y = top - h - i * (h + gap)
            ec = GATE if t.strip().startswith(("18", "19", "20", "24")) else col
            box(ax, x, y, w, h, t, ec=ec, fs=7.1,
                fc="#FDF3F3" if ec == GATE else "#FFFFFF")
            if i:
                arrow(ax, x + w / 2, y + h + gap, x + w / 2, y + h, color="#BBBBBB", lw=1.0)
    for x in xs[:-1]:
        arrow(ax, x + w + 0.3, 46, x + w + 3.2, 46, color=MUTED, lw=1.8)
    note(ax, "Corrected text ships in exactly ONE case: status=='corrected', which requires passing EVERY gate AND re-verifying ENTAILED.\n"
             "Every rejection ships the ORIGINAL text with the reason recorded in final_field.source. All gates are fail-closed.",
         y=1.2, fs=8.4)
    p = save(fig, D / "04_end_to_end_pipeline" / "D04_complete_latest_pipeline.png")
    idx("04_end_to_end_pipeline/D04_complete_latest_pipeline.png",
        "Complete LATEST pipeline",
        "All 26 stages in execution order with function references",
        "research/prototype/src/pipeline.py, claim_parser.py, evidence_matcher.py, verifier.py, corrector.py @ fb4e98f",
        "LATEST")


def d05():
    fig, ax = canvas(13.4, 8.4)
    title(ax, "D05 · Claim parsing flow (stages 3-7)", "claim_parser.py @ fb4e98f · what ORIGINAL could not do")
    steps = [
        ("3  split_sentences  (claim_parser.py:466)\nabbreviation-aware: 'Art.' / 'Arts.' no longer end a sentence", NEW,
         "ORIGINAL: no abbreviation awareness →\na 4-Article paragraph could extract 0 claims"),
        ("4  extract_citations  (claim_parser.py:597)\nCITATION_REGEX:76 · BARE:99 · plurals + number lists", NEW,
         "ORIGINAL: singular, single-number only"),
        ("normalize_act  (claim_parser.py:379)\nIPC / CrPC / CPC aliases · act-bleed fix · trailing-abbrev strip", NEW,
         "ORIGINAL: no acronym or alias handling;\nrun-on sentences merged two Acts into one"),
        ("5  _assign_assertion_texts  (claim_parser.py:814)\n4 ordered passes → verbatim per-citation clause", NEW,
         "ORIGINAL: field did not exist"),
        ("6  _assign_respectively_spans  (claim_parser.py:970)", NEW,
         "ORIGINAL: field did not exist"),
        ("7  field-wide act inheritance  (claim_parser.py:1050)\nunambiguous only — never invents an Act", C_LATEST,
         "ORIGINAL: sentence-level only"),
    ]
    top, h, gap = 84.0, 9.6, 2.4
    for i, (main, col, orig) in enumerate(steps):
        y = top - h - i * (h + gap)
        box(ax, 3, y, 56, h, main, ec=col, fs=8.2, lw=1.8)
        box(ax, 62, y + 0.9, 35, h - 1.8, orig, ec=C_ORIGINAL, fc="#F5F5F5", fs=7.6)
        if i:
            arrow(ax, 31, y + h + gap, 31, y + h, color=MUTED, lw=1.3)
    ax.text(31, 88.5, "LATEST", ha="center", fontsize=11, fontweight="bold", color=C_LATEST)
    ax.text(79.5, 88.5, "ORIGINAL (0e37525)", ha="center", fontsize=11, fontweight="bold", color=C_ORIGINAL)
    note(ax, "Output: Claim objects. At ORIGINAL a Claim carried only {claim_id, claim_text, citation_extracted};\n"
             "assertion_text and assertion_spans are verbatim substrings of the model's own text — never synthesized.", y=1.0)
    p = save(fig, D / "05_claim_parsing" / "D05_claim_parsing_flow.png")
    idx("05_claim_parsing/D05_claim_parsing_flow.png", "Claim parsing flow",
        "Stages 3-7 with the ORIGINAL limitation beside each step",
        "claim_parser.py:466/597/379/814/970/1050 @ fb4e98f; 0e37525:claim_parser.py",
        "BOTH")


def d06():
    fig, ax = canvas(13.0, 8.6)
    title(ax, "D06 · Evidence retrieval flow", "evidence_matcher.py @ fb4e98f")
    box(ax, 34, 80, 32, 7, "ExtractedCitation\n(provision_type, number, subsection, act_norm)", ec=C_LATEST, fs=8.4)
    box(ax, 34, 68, 32, 6.5, "1 · exact_normalized\nindex lookup on the full key", ec=C_LATEST, fs=8.4)
    box(ax, 34, 57, 32, 6.5, "2 · exact, subsection ignored\n'25F(1)' ↔ '25F'", ec=C_LATEST, fs=8.4)
    box(ax, 30, 45, 40, 7.0, "8a · YEAR-CONFLICT VETO  (evidence_matcher.py:48, applied :121)\ncandidate rejected if the cited year contradicts the record", ec=NEW, lw=2.0, fs=8.2, fc="#F1F8F2")
    box(ax, 30, 33, 40, 7.0, "8b · fuzzy Jaccard  |A∩B| / |A∪B|  ≥ 0.8\nover act_significant_words (evidence_matcher.py:59)", ec=C_LATEST, fs=8.4)
    box(ax, 8, 20, 30, 6.5, "MATCH → EvidenceRecord\nbecomes the NLI premise", ec=NEW, fs=8.6, fc="#F1F8F2")
    box(ax, 62, 20, 30, 6.5, "NO_EVIDENCE  (first-class outcome)\n+ taxonomy, evidence_matcher.py:170", ec=REJECTED, fs=8.2, fc="#F5F5F5")
    for y1, y2 in ((80, 74.5), (68, 63.5), (57, 52.0), (45, 40.0)):
        arrow(ax, 50, y1, 50, y2)
    arrow(ax, 44, 33, 23, 26.5)
    arrow(ax, 56, 33, 77, 26.5)
    box(ax, 3, 60, 26, 16, "EVIDENCE POOL\n\nORIGINAL: 59 usable records\n10 distinct Acts\n(v0 only)\n\nLATEST: 136 usable records\n22 distinct Acts\n(v0 + audited v1 supplement)",
        ec=C_ORIGINAL, fc="#F7F9FB", fs=8.4)
    box(ax, 71, 60, 26, 16, "REJECTED ALTERNATIVES\n\nBM25 · sentence embeddings\nbuilt, benchmarked, NOT used\n\nBoth accept every real match but\nare less safe on adversarial\nnear-miss Act names",
        ec=REJECTED, fc="#F5F5F5", fs=8.0)
    note(ax, "The year-conflict veto is UNCONDITIONAL — it is not controlled by any config lever, and it can change which record is retrieved,\n"
             "hence the premise, hence the verdict. Separately: evidence_matching.fuzzy_method is never read by any call site,\n"
             "so BM25/embedding are unreachable from production regardless of the config value.", y=1.0)
    p = save(fig, D / "06_evidence_retrieval" / "D06_evidence_retrieval_flow.png")
    idx("06_evidence_retrieval/D06_evidence_retrieval_flow.png", "Evidence retrieval flow",
        "The match ladder, the year-conflict veto, the Jaccard threshold, and both pool sizes",
        "evidence_matcher.py:48/59/69/121/170 @ fb4e98f",
        "BOTH")


def d07():
    fig, ax = canvas(13.4, 8.4)
    title(ax, "D07 · NLI verification flow", "verifier.py / pipeline.py @ fb4e98f · the premise-framing change in full")
    box(ax, 4, 72, 40, 12,
        "ORIGINAL  ·  premise_framing = bare\n\npremise = evidence_text\n(raw statute text, unlabelled)\n\nhypothesis = full claim_text sentence",
        ec=C_ORIGINAL, fc="#F5F5F5", fs=8.6)
    box(ax, 56, 72, 40, 12,
        "LATEST  ·  premise_framing = labeled\n\npremise = f\"{provision_type} {provision_number}\n of {act}: {evidence_text}\"   (verifier.py:78)\n\nhypothesis = assertion_text when available",
        ec=NEW, lw=2.0, fc="#F1F8F2", fs=8.4)
    box(ax, 22, 56, 56, 9.5,
        "The label comes from the MATCHED EVIDENCE RECORD — never from the claim's own (possibly wrong) citation.\n"
        "No legal content is invented; the statute text is passed through untouched.",
        ec=C_LATEST, fc="#EEF3F8", fs=8.4)
    box(ax, 30, 42, 40, 8.0, "NLIVerifier.verify  (verifier.py:178)\nDeBERTa-v3-base-mnli-fever-anli  ·  max_len 512\n+ truncation probe (detects, never prevents)", ec=C_LATEST, fs=8.3)
    box(ax, 30, 29, 40, 7.5, "argmax softmax → entailment / neutral / contradiction\nmapped to ENTAILED / NEI / CONTRADICTED", ec=C_LATEST, fs=8.4)
    box(ax, 30, 17, 40, 7.0, "confidence < 0.70 → NOT_ENOUGH_INFORMATION\nsub_reason = 'low_confidence'   (verifier.py:218-222)", ec=C_LATEST, fs=8.4)
    arrow(ax, 24, 72, 40, 51.5); arrow(ax, 76, 72, 60, 51.5)
    arrow(ax, 50, 56, 50, 50); arrow(ax, 50, 42, 50, 36.5); arrow(ax, 50, 29, 50, 24)
    note(ax, "WHY the bare premise failed: generated claims are overwhelmingly attributed ('According to Section 302 of the IPC, ...').\n"
             "A bare premise contains the rule but never names Section 302, so that half of the hypothesis is genuinely unsupported\n"
             "and a well-behaved NLI model must answer neutral. Labeled framing restores the identifier the claim is about.", y=1.0)
    p = save(fig, D / "07_nli_verification" / "D07_nli_verification_flow.png")
    idx("07_nli_verification/D07_nli_verification_flow.png", "NLI verification flow",
        "Premise construction bare vs labeled (literal template), hypothesis selection, threshold downgrade",
        "verifier.py:78/178/218-222; pipeline.py:55/401-412 @ fb4e98f",
        "BOTH")


def d08():
    fig, ax = canvas(12.6, 7.8)
    title(ax, "D08 · Verdict assignment", "verifier.py / pipeline.py @ fb4e98f")
    box(ax, 36, 80, 28, 6.5, "Claim", ec=C_LATEST, fs=9)
    box(ax, 36, 68, 28, 7.0, "Has matched evidence?", ec=C_LATEST, fs=8.8)
    box(ax, 72, 55, 25, 7.0, "NO_EVIDENCE\nverifier never called", ec=REJECTED, fc="#F5F5F5", fs=8.4)
    box(ax, 32, 55, 36, 7.0, "NLI argmax + confidence", ec=C_LATEST, fs=8.8)
    verdicts = [
        ("ENTAILED", "#3F8F4F", 4),
        ("CONTRADICTED", "#C44E52", 27),
        ("NOT_ENOUGH_\nINFORMATION", "#DDA63A", 50),
    ]
    for label, col, x in verdicts:
        box(ax, x, 36, 21, 8.0, label, ec=col, fc="#FFFFFF", fs=8.6, bold=True, tc=col)
    box(ax, 27, 21, 46, 7.5, "confidence < 0.70  →  downgraded to NOT_ENOUGH_INFORMATION\nsub_reason = 'low_confidence'", ec=C_LATEST, fs=8.4)
    box(ax, 22, 8, 56, 7.5, "NEGATION CAVEAT (LATEST only, unconditional)  pipeline.py:160 / :419\na negation-marked CONTRADICTED claim is flagged and excluded from the correction trigger", ec=NEW, fc="#F1F8F2", fs=8.2, lw=1.9)
    arrow(ax, 50, 80, 50, 75); arrow(ax, 50, 68, 50, 62)
    arrow(ax, 64, 71.5, 84, 62)
    for _, _, x in verdicts:
        arrow(ax, 50, 55, x + 10.5, 44)
    arrow(ax, 50, 36, 50, 28.5); arrow(ax, 50, 21, 50, 15.5)
    note(ax, "Four verdicts. NO_EVIDENCE is a first-class outcome, not an error — an NLI verdict without a premise would be meaningless.\n"
             "ORIGINAL had the same four verdicts and the same 0.70 downgrade rule; only the negation caveat is new.", y=1.0)
    p = save(fig, D / "08_verdict" / "D08_verdict_assignment.png")
    idx("08_verdict/D08_verdict_assignment.png", "Verdict assignment",
        "Four verdicts, the confidence downgrade, and the negation caveat",
        "verifier.py:218-222; pipeline.py:160/419 @ fb4e98f", "BOTH")


def d09():
    fig, ax = canvas(13.2, 8.8)
    title(ax, "D09 · Correction and re-verification", "pipeline.py / corrector.py @ fb4e98f · the LEGACY path (assertion_aware = false)")
    steps = [
        ("16  TRIGGER  (pipeline.py:714-730)\nCONTRADICTED, or NEI with sub_reason='low_confidence'\nfirst flagged claim only · max 1 attempt · never NO_EVIDENCE", C_LATEST),
        ("17  LLM whole-paragraph rewrite  (corrector.py:43)\nsame Qwen instance · 220 tokens · greedy\n'change ONLY the flagged sentence'", C_LATEST),
        ("18  GATE · scope violation  (pipeline.py:462/423)", GATE),
        ("19  GATE · unauthorized citation addition  (pipeline.py:769-790)", GATE),
        ("20-21  ordinal lookup + GATE · ordinal integrity  (pipeline.py:806-873)", GATE),
        ("22-23  re-parse, re-match, RE-VERIFY  (pipeline.py:878-932)\nnarrow_reverification_hypothesis = true", C_LATEST),
        ("24  GATE · sibling regression  (pipeline.py:601/945)", GATE),
    ]
    top, h, gap = 84, 8.2, 2.0
    for i, (t, col) in enumerate(steps):
        y = top - h - i * (h + gap)
        box(ax, 6, y, 60, h, t, ec=col, fs=8.1, lw=1.9 if col == GATE else 1.5,
            fc="#FDF3F3" if col == GATE else "#FFFFFF")
        if i:
            arrow(ax, 36, y + h + gap, 36, y + h, color=MUTED, lw=1.3)
        if col == GATE:
            arrow(ax, 66, y + h / 2, 72, y + h / 2, color=GATE, lw=1.5)
            box(ax, 72, y + 0.6, 25, h - 1.2, "REJECT →\nship ORIGINAL text\nreason in final_field.source",
                ec=GATE, fc="#FDF3F3", fs=7.4)
    y_last = top - h - (len(steps) - 1) * (h + gap)
    box(ax, 6, y_last - 11, 60, 7.5,
        "SHIP  ·  status == 'corrected'\nrequires ALL gates passed AND re-verification == ENTAILED",
        ec=NEW, fc="#F1F8F2", fs=8.6, lw=2.0, bold=True)
    arrow(ax, 36, y_last, 36, y_last - 3.5, color=NEW, lw=1.8)
    note(ax, "Every gate is FAIL-CLOSED: on any doubt the ORIGINAL text ships unchanged. The assertion-aware splice path is fully built\n"
             "and adds three further fail-closed statuses, but correction.assertion_aware = false, so it is DORMANT in production.", y=1.0)
    p = save(fig, D / "09_correction_reverification" / "D09_correction_and_reverification.png")
    idx("09_correction_reverification/D09_correction_and_reverification.png",
        "Correction and re-verification",
        "Trigger → rewrite → gate chain → re-verify → ship or reject",
        "pipeline.py:714-730/462/769-790/806-873/878-932/601/945; corrector.py:43 @ fb4e98f", "LATEST")


def d10():
    fig, ax = canvas(13.6, 8.4)
    title(ax, "D10 · Safety gate chain", "Which gates existed at ORIGINAL, and when each was added")
    gates = [
        ("Full-sentence scope check\npipeline.py:133-153 → :462", "0e37525", True,
         "every unflagged claim must reappear verbatim"),
        ("Sibling regression net\npipeline.py:601 / :945", "100e263 · 2026-08-27", False,
         "an untouched sibling claim must not get worse\n(INACTIVE unless atomic_scope_check is truthy)"),
        ("Unauthorized citation addition\npipeline.py:769-790", "adf54aa · 2026-09-09", False,
         "the corrector may not introduce a new citation"),
        ("Ordinal integrity\npipeline.py:806-873", "adf54aa · 2026-09-09", False,
         "reordered same-citation siblings cannot fake\na safety confirmation"),
        ("Negation gate\npipeline.py:160 / :419 / :713-716", "adf54aa · 2026-09-09", False,
         "unconditional — not lever-controllable"),
        ("Year-conflict veto\nevidence_matcher.py:48 / :121", "adf54aa · 2026-09-09", False,
         "unconditional — retrieval-side"),
        ("Structural span validation\npipeline.py:1151", "8cf8fa9 · 2026-09-12", False,
         "assertion-aware path only (currently dormant)"),
    ]
    top, h, gap = 82, 9.0, 1.8
    for i, (name, when, at_orig, what) in enumerate(gates):
        y = top - h - i * (h + gap)
        col = C_ORIGINAL if at_orig else GATE
        box(ax, 3, y, 34, h, name, ec=col, fs=8.0,
            fc="#F5F5F5" if at_orig else "#FDF3F3", lw=1.8)
        box(ax, 39, y + 0.8, 20, h - 1.6,
            ("PRESENT at\nORIGINAL" if at_orig else f"ADDED\n{when}"),
            ec=col, fc="#FFFFFF", fs=7.8, bold=at_orig)
        box(ax, 61, y + 0.8, 36, h - 1.6, what, ec="#D8D8D8", fc="#FFFFFF", fs=7.6)
    note(ax, "ORIGINAL had exactly ONE gate. All gates are FAIL-CLOSED: on any doubt the original text ships unchanged.\n"
             "Most of these gates were discovered adversarially and are covered by REGRESSION TESTS, not by data-batch measurement —\n"
             "so 'zero unsafe shipped corrections' is a zero-event outcome over a small denominator, not a proof of safety.", y=1.0)
    p = save(fig, D / "10_safety" / "D10_safety_gate_chain.png")
    idx("10_safety/D10_safety_gate_chain.png", "Safety gate chain",
        "Every gate, when it was added, and whether it existed at ORIGINAL",
        "pipeline.py:133-153/601/769-790/806-873/160/419/1151; evidence_matcher.py:48 — commits 0e37525/100e263/adf54aa/8cf8fa9",
        "BOTH")


def d11():
    fig, ax = canvas(12.6, 7.6)
    title(ax, "D11 · Final answer assembly", "pipeline.py:1401-1508 @ fb4e98f")
    box(ax, 33, 80, 34, 7.0, "correction terminal status", ec=C_LATEST, fs=9)
    outcomes = [
        ("corrected", NEW, "CORRECTED text ships\nall gates passed AND re-verified ENTAILED", 4),
        ("correction_scope_violation\ncorrection_unauthorized_addition\ncorrection_ordinal_ambiguous", GATE,
         "ORIGINAL text ships\nblocked by a safety gate", 36),
        ("correction_failed\nnot_triggered", REJECTED, "ORIGINAL text ships\nno valid edit, or nothing flagged", 68),
    ]
    for label, col, what, x in outcomes:
        box(ax, x, 56, 28, 12.0, label, ec=col, fs=7.8,
            fc="#F1F8F2" if col == NEW else ("#FDF3F3" if col == GATE else "#F5F5F5"))
        box(ax, x, 38, 28, 10.0, what, ec="#D8D8D8", fc="#FFFFFF", fs=7.8)
        arrow(ax, 50, 80, x + 14, 68.5)
        arrow(ax, x + 14, 56, x + 14, 48.5)
    box(ax, 22, 20, 56, 9.5,
        "final_field = { text, source }\n\nfinal_field.source records WHICH of the outcomes above applied —\nso every record states why its text is what it is",
        ec=C_LATEST, fc="#EEF3F8", fs=8.4)
    for _, _, _, x in outcomes:
        arrow(ax, x + 14, 38, 50, 29.8)
    note(ax, "The assembly RULE never changed between ORIGINAL and LATEST — anything not fully verified ships the original text.\n"
             "Only the vocabulary grew: 4 → 9 distinct final_field.source labels.", y=1.5)
    p = save(fig, D / "11_final_answer" / "D11_final_answer_assembly.png")
    idx("11_final_answer/D11_final_answer_assembly.png", "Final answer assembly",
        "How final_field is produced and what final_field.source records",
        "pipeline.py:1401-1508 @ fb4e98f", "BOTH")


def d12():
    fig, ax = canvas(13.4, 8.0)
    title(ax, "D12 · Data flow", "Read-only inputs, the pipeline, and what it writes")
    box(ax, 3, 66, 26, 13, "NyayaRAG CaseText_Statutes\nSCI_56k_multi / single 5k\n\nREAD-ONLY\nonly document_id, summarized_text\nand section KEYS are read", ec=C_ORIGINAL, fc="#F7F9FB", fs=7.8)
    box(ax, 3, 46, 26, 15, "canonical_statutes.jsonl  (63 rec)\nevidence_audit.jsonl\n→ 59 usable\n\ncanonical_statutes_v1.jsonl (82 rec)\nevidence_audit_v1.jsonl\n→ merged total 136 usable\n\nREAD-ONLY", ec=NEW, fc="#F1F8F2", fs=7.6)
    box(ax, 37, 56, 26, 22, "PIPELINE\n\ngenerate → parse →\nmatch → verify →\nverdict → correct →\ngate → re-verify →\nassemble", ec=C_LATEST, fs=9.0, bold=True)
    box(ax, 71, 66, 26, 12, "outputs/*.jsonl\nper-case records\n(claims, evidence, verdicts,\ncorrection, final_field)", ec=C_LATEST, fs=8.0)
    box(ax, 71, 50, 26, 12, "outputs/*.json + *.md\nexperiment metrics\nand reports", ec=C_LATEST, fs=8.0)
    box(ax, 37, 32, 26, 10, "MODELS  (never written to)\nQwen2.5-7B-Instruct 4-bit\nDeBERTa-v3-base-mnli-fever-anli", ec=C_INTERMEDIATE, fc="#F7F9FB", fs=7.8)
    arrow(ax, 29, 72, 37, 70); arrow(ax, 29, 53, 37, 62)
    arrow(ax, 63, 70, 71, 72); arrow(ax, 63, 62, 71, 56)
    arrow(ax, 50, 42, 50, 56, style="-", lw=1.2, ls=":")
    box(ax, 12, 12, 76, 11,
        "NEVER WRITTEN TO BY THE PIPELINE:  research/data/evidence/*  ·  research/data/nyayarag/*  ·  baseline/LegalSeg\n"
        "NyayaRAG's own free-text `sections` VALUES are never read into anything that could reach the verifier —\n"
        "evidence text always comes from canonical_statutes.jsonl, which is audited.",
        ec=GATE, fc="#FDF3F3", fs=8.0)
    p = save(fig, D / "12_data_flow" / "D12_data_flow.png")
    idx("12_data_flow/D12_data_flow.png", "Data flow",
        "Inputs, pipeline, outputs, and the read-only guarantees",
        "config/prototype.yaml paths; data_loader.py docstring @ fb4e98f", "LATEST")


def d13():
    fig, ax = canvas(13.6, 8.6)
    title(ax, "D13 · Components that exist at LATEST but not at ORIGINAL",
          "Grouped by subsystem, with production status")
    groups = [
        ("PARSER", [
            ("assertion_text / assertion_spans", "PRODUCTION"),
            ("Art. / Arts. abbreviation handling", "PRODUCTION"),
            ("acronym + alias normalisation (IPC/CrPC/CPC)", "PRODUCTION"),
            ("act-bleed fix (run-on multi-Act sentences)", "PRODUCTION"),
            ("'respectively' span assignment", "PRODUCTION"),
        ]),
        ("RETRIEVAL", [
            ("v1 evidence supplement → 136 records", "PRODUCTION"),
            ("year-conflict veto", "PRODUCTION"),
            ("NO_EVIDENCE taxonomy (diagnostic)", "PRODUCTION"),
            ("BM25 act matching", "EVALUATED_AND_REJECTED"),
            ("sentence-embedding act matching", "EVALUATED_AND_REJECTED"),
        ]),
        ("VERIFICATION", [
            ("labeled premise framing", "PRODUCTION"),
            ("narrow_primary_hypothesis", "PRODUCTION"),
            ("truncation detection probe", "PRODUCTION"),
            ("negation caveat flag", "PRODUCTION"),
            ("assertion_span_primary_hypothesis", "EXPERIMENTAL — OFF"),
        ]),
        ("CORRECTION + SAFETY", [
            ("atomic_scope_check = assertion_spans", "PRODUCTION"),
            ("narrow_reverification_hypothesis", "PRODUCTION"),
            ("unauthorized-citation guard", "PRODUCTION"),
            ("ordinal-integrity guard", "PRODUCTION"),
            ("sibling-regression net", "PRODUCTION"),
            ("correction.assertion_aware (splice)", "EXPERIMENTAL — OFF"),
        ]),
    ]
    colmap = {"PRODUCTION": NEW, "EXPERIMENTAL — OFF": EXPERIMENTAL,
              "EVALUATED_AND_REJECTED": REJECTED}
    xs = [2.0, 26.0, 50.0, 74.0]
    w = 22.5
    for (name, items), x in zip(groups, xs):
        ax.text(x + w / 2, 86.5, name, ha="center", fontsize=10.5, fontweight="bold", color=C_LATEST)
        top, h, gap = 83.0, 9.2, 1.6
        for i, (label, status) in enumerate(items):
            y = top - h - i * (h + gap)
            col = colmap[status]
            box(ax, x, y, w, h, f"{label}\n\n[{status}]", ec=col, fs=7.2,
                fc={"PRODUCTION": "#F1F8F2", "EXPERIMENTAL — OFF": "#FEF8EC",
                    "EVALUATED_AND_REJECTED": "#F5F5F5"}[status])
    legend(ax, [("production", NEW), ("experimental — OFF", EXPERIMENTAL),
                ("evaluated and rejected", REJECTED)], x=26, y=92)
    note(ax, "NEVER describe an amber or grey component as production behaviour. Two mechanisms are fully built, benchmarked and\n"
             "deliberately OFF; two retrieval alternatives were built, benchmarked and actively REJECTED on safety grounds.", y=1.2)
    p = save(fig, D / "13_new_components" / "D13_new_components.png")
    idx("13_new_components/D13_new_components.png", "New components at LATEST",
        "Everything added since ORIGINAL, grouped by subsystem, with production status",
        "config/prototype.yaml live values; src/ @ fb4e98f; change inventory", "LATEST")


def d14():
    fig, ax = canvas(15.0, 9.2)
    title(ax, "D14 · Flaw → Fix → Latest behaviour", "The six best-evidenced changes")
    rows = [
        ("Bare NLI premise never named\nthe provision, so attributed\nclaims could not be entailed",
         "premise_framing\nbare → labeled",
         "premise = \"<Type> <N> of\n<Act>: <text>\", labelled from\nthe MATCHED record",
         "GOLD-01 n=420: macro F1\n0.749→0.968  (99/100 of the\ngain is in attributed conditions)"),
        ("Evidence pool too small:\n57% of claims resolved\nto nothing",
         "use_evidence_v1\nfalse → true",
         "136 usable records\nacross 22 Acts",
         "n=209 paired: coverage\n63.2%→70.3%, 15 gained,\n0 lost  (HISTORICAL)"),
        ("Parser could not normalise\nIndian citation forms\n(IPC/CrPC/CPC, Art./Arts.)",
         "acronym + alias normalisation,\nabbreviation-aware splitting",
         "one clean act_norm per\ncitation; exact matches\nreplace fuzzy ones",
         "n=30 docs: claims resolving\nto evidence 38→57,\n+10/−0 docs, p=0.0020"),
        ("Corrector could flip a negation\nand call it a fix",
         "negation gate\n(unconditional)",
         "negation-marked CONTRADICTED\nclaims are flagged and never\nenter the correction trigger",
         "Regression tests only —\nNO data-batch measurement"),
        ("Reordered same-citation siblings\ncould ship a verdict never\ncomputed against the real edit",
         "ordinal-integrity guard\n(unconditional)",
         "ordinal position is resolved\nand verified; ambiguity\nfails closed",
         "Regression tests only —\nNO data-batch measurement"),
        ("A differently-dated Act could\nmatch the wrong record",
         "year-conflict veto\n(unconditional)",
         "candidate rejected when the\ncited year contradicts\nthe record",
         "Regression tests only —\nNO data-batch measurement"),
    ]
    heads = ["FLAW at ORIGINAL", "MODIFICATION", "LATEST BEHAVIOUR", "EVIDENCE"]
    xs = [2.0, 26.5, 49.0, 73.0]
    ws = [23.0, 21.0, 22.5, 25.0]
    cols = [C_ORIGINAL, C_INTERMEDIATE, C_LATEST, NEW]
    for hname, x, w, c in zip(heads, xs, ws, cols):
        ax.text(x + w / 2, 88.0, hname, ha="center", fontsize=10.2, fontweight="bold", color=c)
    top, h, gap = 85.0, 12.0, 1.8
    for i, cells in enumerate(rows):
        y = top - h - i * (h + gap)
        for j, (txt, x, w, c) in enumerate(zip(cells, xs, ws, cols)):
            weak = (j == 3 and "Regression tests only" in txt)
            box(ax, x, y, w, h, txt, ec=(EXPERIMENTAL if weak else c), fs=7.2,
                fc={0: "#F5F5F5", 1: "#F7F9FB", 2: "#FFFFFF",
                    3: ("#FEF8EC" if weak else "#F1F8F2")}[j])
            if j < 3:
                arrow(ax, x + w + 0.3, y + h / 2, xs[j + 1] - 0.3, y + h / 2,
                      color="#C8C8C8", lw=1.2)
    note(ax, "Amber evidence cells mark changes whose only evidence is a REGRESSION TEST: the test proves the failure is blocked, but nothing\n"
             "measures how often it occurred in real data. They are included because omitting them would overstate how well the safety\n"
             "architecture is evidenced. Grade measures how well a change is EVIDENCED — never effect size, never quality.", y=1.0)
    p = save(fig, D / "14_flaw_fix_behavior" / "D14_flaw_fix_behavior.png")
    idx("14_flaw_fix_behavior/D14_flaw_fix_behavior.png", "Flaw → Fix → Latest behaviour",
        "The six best-evidenced changes, with honest evidence strength per row",
        "V2 metrics + change inventory; src/ @ fb4e98f", "BOTH")


def main() -> int:
    print("building V2 diagrams...")
    for fn in (d01, d02, d03, d04, d05, d06, d07, d08, d09, d10, d11, d12, d13, d14):
        fn()
    p = D / "diagram_index.json"
    p.write_text(json.dumps(INDEX, indent=2), encoding="utf-8")
    print(f"\n{len(INDEX)} diagrams written; index -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
