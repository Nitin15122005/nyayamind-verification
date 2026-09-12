#!/usr/bin/env python3
"""Phase 3 (Vedant) — STEP 3: system-flow diagrams for the mentor package.

Every box, model id, function name, config key and outcome label below was read
out of the repository's own source (research/prototype/src/*.py,
research/prototype/scripts/run_mvp.py, config/prototype.yaml) or its frozen
records (research/baseline/BASELINE.md, archive/.../comparison_config.json).
No stage is invented; where a capability does not exist in a system, the diagram
says so instead of drawing it.

Rendered twice, like the figures:
  diagrams/<name>.png             — publication density
  ppt_assets/diagrams/<name>.png  — 16:9 landscape, presentation type sizes
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # noqa: E402

PPT = False
MANIFEST: list[dict] = []
DPI = 200
PPT_SIZE = (13.333, 7.5)

# palette
BG_INPUT = "#E8EEF4"
BG_SHARED = "#DCE4EC"
BG_GEN = "#CBD9E8"
BG_PARSE = "#D7E4D3"
BG_EVID = "#E7E0CF"
BG_VERIFY = "#E4D9EC"
BG_CORRECT = "#F2DFD2"
BG_SAFETY = "#F6D6D6"
BG_OUTPUT = "#DDE9DD"
BG_NEW = "#FFF6D8"          # functionality the modified system adds
EDGE = "#3A3A3A"
NEW_EDGE = "#C48A00"


def S(pub: float, ppt: float) -> float:
    return ppt if PPT else pub


def new_canvas(w: float, h: float, xlim=(0, 100), ylim=(0, 100)):
    size = PPT_SIZE if PPT else (w, h)
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=BG_SHARED, ec=EDGE, fs=None, weight="normal",
        lw=1.2, style="round,pad=0.25", ls="solid", wrap=None, tc="#111111"):
    """Draw one labelled node. (x, y) is the box centre, in axis units."""
    fs = fs or S(7.6, 10.5)
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=style,
                                facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls,
                                mutation_scale=1.0, zorder=2))
    label = textwrap.fill(text, wrap) if wrap else text
    ax.text(x, y, label, ha="center", va="center", fontsize=fs, fontweight=weight,
            zorder=3, color=tc, linespacing=1.35)
    return (x, y, w, h)


def arrow(ax, p1, p2, label=None, color=EDGE, lw=1.4, ls="-", fs=None,
          label_dx=0.0, label_dy=0.0, rad=0.0):
    fs = fs or S(6.6, 9.2)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=S(12, 16),
                                 color=color, lw=lw, linestyle=ls, zorder=1,
                                 connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=1.5, shrinkB=2.5))
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + label_dx, (p1[1] + p2[1]) / 2 + label_dy
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color=color,
                zorder=4, bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                                    edgecolor="none", alpha=0.88))


def below(b):
    return (b[0], b[1] - b[3] / 2)


def above(b):
    return (b[0], b[1] + b[3] / 2)


def left(b):
    return (b[0] - b[2] / 2, b[1])


def right(b):
    return (b[0] + b[2] / 2, b[1])


def titleblock(fig, title, subtitle):
    fig.suptitle(title, fontsize=S(13, 19), fontweight="bold", y=0.982)
    fig.text(0.5, 0.932, subtitle, ha="center", va="top", fontsize=S(8.2, 12),
             color="#333333")


def footer(fig, source: str, note: str):
    width = 150 if PPT else 180
    txt = "\n".join(["\n".join(textwrap.wrap(s, width)) for s in
                     (f"Source: {source}", f"Note: {note}")])
    fig.text(0.012, 0.012, txt, ha="left", va="bottom", fontsize=S(6.6, 9.2),
             color="#444444")


def save(fig, name):
    out = (C.OUT_PPT_DIA if PPT else C.OUT_DIAGRAMS) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def register(did, name, title, purpose, source, designation, note):
    if PPT:
        return
    MANIFEST.append({
        "artifact_id": did,
        "artifact_type": "diagram",
        "filename": f"diagrams/{name}",
        "ppt_variant": f"ppt_assets/diagrams/{name}",
        "title": title,
        "purpose": purpose,
        "metric_contract_csv": "n/a (structural diagram, no plotted metric)",
        "source_artifact": source,
        "dataset": "n/a (source code / configuration)",
        "n": "n/a",
        "system_model_names": designation,
        "baseline_or_modified": designation,
        "fresh_or_historical": "FRESH (read from source at build time)",
        "evidence_grade": "n/a (structural)",
        "caveat": note,
        "generation_script": "Output_phase_3_vedant/scripts/generate_diagrams.py",
    })


GEN = C.GENERATION_MODEL
VER = C.VERIFICATION_MODEL
COR = C.CORRECTION_MODEL
SRC_ALL = ("research/prototype/src/{pipeline,generator,claim_parser,evidence_matcher,"
           "verifier,corrector,data_loader}.py; research/prototype/config/prototype.yaml")


def new_badge(ax, x, y, text="ADDED IN THE MODIFIED SYSTEM"):
    ax.text(x, y, text, ha="center", va="center", fontsize=S(6.2, 8.6),
            fontweight="bold", color="#8A6100",
            bbox=dict(boxstyle="round,pad=0.28", facecolor=BG_NEW, edgecolor=NEW_EDGE, lw=1.0))


# ==========================================================================
# D01 — baseline architecture
# ==========================================================================
def d01():
    fig, ax = new_canvas(10.5, 7.4)
    x = 50
    b0 = box(ax, x, 92, 62, 9, "NyayaRAG case text (summarized_text)\n"
                               "data_loader.load_nyayarag_cases() → "
                               "select_cases_with_evidence_overlap(min_overlap=1)",
             fc=BG_INPUT, fs=S(7.2, 10))
    b1 = box(ax, x, 78, 62, 9.5,
             f"[1] Generate statutory_grounding field\n{GEN} · 4-bit {C.QUANT} · greedy "
             "(do_sample=false) · max_new_tokens=200", fc=BG_GEN, fs=S(7.2, 10))
    b2 = box(ax, x, 64, 62, 9.5,
             "[2] Extract citation-bearing claims\nclaim_parser.extract_claims() — "
             "deterministic regex, no LLM", fc=BG_PARSE, fs=S(7.2, 10))
    b3 = box(ax, x, 50, 62, 10.5,
             "[3] Match each claim to canonical evidence\n"
             "evidence_matcher.match_evidence() — exact key, then fuzzy (overlap ≥ 0.8)\n"
             "evidence pool v0 only: 59 usable records (use_evidence_v1 = false)",
             fc=BG_EVID, fs=S(7.0, 9.6))
    b4 = box(ax, x, 35, 62, 10.5,
             "[4] Verify each claim (modes B and C)\n"
             f"{VER} · confidence_threshold = 0.70\n"
             "premise_framing = \"bare\" — premise is the statute text ALONE",
             fc=BG_VERIFY, fs=S(7.0, 9.6))
    b5 = box(ax, x, 20.5, 62, 9.5,
             "[5–7] Selective correction, scope gate, re-verification (mode C)\n"
             f"{COR} · scope check = full-sentence byte-for-byte (atomic_scope_check = false)\n"
             "re-verification hypothesis = the full bundled sentence",
             fc=BG_CORRECT, fs=S(7.0, 9.6))
    b6 = box(ax, x, 7, 62, 8,
             "final_field.source ∈ {original, corrected, correction_failed,\n"
             "correction_scope_violation}", fc=BG_OUTPUT, fs=S(7.2, 10))
    for a, b in ((b0, b1), (b1, b2), (b2, b3), (b3, b4), (b4, b5), (b5, b6)):
        arrow(ax, below(a), above(b))
    ax.text(90.5, 35, "sibling-regression\nre-verification\nis INACTIVE\n(it only arms when\n"
                    "an atomic scope-check\nmode is enabled)", ha="center", va="center",
            fontsize=S(6.6, 9), color="#8A2020",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#FBEAEA", edgecolor="#C08080"))
    titleblock(fig, "Baseline architecture — NyayaMind v0 (pre-2026-08-27 production configuration)",
               "The configuration under which every output committed before 2026-08-27 was "
               "produced; still reproducible byte-for-byte from the current code")
    footer(fig, SRC_ALL + "; research/prototype/archive/2026-08-27_presentation/final_comparison/"
                          "comparison_config.json (\"ORIGINAL\")",
           "Baseline and modified run the SAME pipeline code — they differ only in configuration "
           "values, except for the separately-measured claim-parser fix (commit 223eb9d).")
    save(fig, "D01_baseline_architecture_nyayamind_v0.png")
    register("D01", "D01_baseline_architecture_nyayamind_v0.png",
             "Baseline architecture — NyayaMind v0 (pre-2026-08-27 production configuration)",
             "Establish exactly what the baseline system is before any comparison",
             "config/prototype.yaml; comparison_config.json (ORIGINAL); src/*.py",
             "Baseline: NyayaMind v0", "Configuration A/B, not a code fork.")


# ==========================================================================
# D02 — modified architecture
# ==========================================================================
def d02():
    fig, ax = new_canvas(10.5, 7.6)
    x = 44
    b0 = box(ax, x, 93, 66, 8, "NyayaRAG case text (summarized_text)\n"
                               "data_loader.load_nyayarag_cases() → "
                               "select_cases_with_evidence_overlap(min_overlap=1)",
             fc=BG_INPUT, fs=S(7.0, 9.6))
    b1 = box(ax, x, 80.5, 66, 9,
             f"[1] Generate statutory_grounding field\n{GEN} · 4-bit {C.QUANT} · greedy · "
             "max_new_tokens=200  (UNCHANGED)", fc=BG_GEN, fs=S(7.0, 9.6))
    b2 = box(ax, x, 68, 66, 9,
             "[2] Extract citation-bearing claims\nclaim_parser.extract_claims() + "
             "assertion_text / assertion_spans sub-spans", fc=BG_PARSE, fs=S(7.0, 9.6))
    b3 = box(ax, x, 55, 66, 9.5,
             "[3] Match each claim to canonical evidence\nevidence_matcher.match_evidence()\n"
             "evidence pool v0+v1: 136 usable records (use_evidence_v1 = true)",
             fc=BG_EVID, fs=S(7.0, 9.6))
    b4 = box(ax, x, 42, 66, 9.5,
             f"[4] Verify each claim\n{VER} · confidence_threshold = 0.70 (UNCHANGED)\n"
             "premise_framing = \"labeled\" — \"Section N of Act: <statute text>\"",
             fc=BG_VERIFY, fs=S(7.0, 9.6))
    b5 = box(ax, x, 29.5, 66, 8.5,
             f"[5] Regenerate ONLY the first flagged sentence\ncorrector.SelectiveCorrector."
             f"correct() · {COR} (UNCHANGED)", fc=BG_CORRECT, fs=S(7.0, 9.6))
    b6 = box(ax, x, 18, 66, 8.5,
             "[6] Scope + safety gate\npipeline._scope_violation(atomic_scope_check="
             "\"assertion_spans\")\n+ _reverify_sibling_regressions() + _citation_identity()",
             fc=BG_SAFETY, fs=S(7.0, 9.6))
    b7 = box(ax, x, 7, 66, 8,
             "[7] Re-verify · narrow_reverification_hypothesis = true → final_field.source ∈\n"
             "{original, corrected, correction_failed, correction_scope_violation, "
             "correction_sibling_regression}", fc=BG_OUTPUT, fs=S(6.6, 9.2))
    for a, b in ((b0, b1), (b1, b2), (b2, b3), (b3, b4), (b4, b5), (b5, b6), (b6, b7)):
        arrow(ax, below(a), above(b))

    for y, txt in ((68, "assertion_spans:\nper-citation verbatim\nfragments"),
                   (55, "+77 usable evidence\nrecords vs baseline"),
                   (42, "provision label\nprepended to the premise"),
                   (18, "sibling-regression net\narms with the relaxed\nscope check"),
                   (7, "narrower, non-fabricated\nre-verification hypothesis")):
        ax.add_patch(FancyBboxPatch((80.5, y - 4.4), 19, 8.8, boxstyle="round,pad=0.2",
                                    facecolor=BG_NEW, edgecolor=NEW_EDGE, lw=1.1, zorder=2))
        ax.text(90, y, txt, ha="center", va="center", fontsize=S(6.3, 8.7), zorder=3,
                color="#5C4400")
        arrow(ax, (80.5, y), (77.2, y), color=NEW_EDGE, lw=1.1)
    new_badge(ax, 90, 89, "ADDED / CHANGED vs BASELINE")
    titleblock(fig, "Modified architecture — NyayaMind 2026-08-27 shipped production configuration",
               f"Same models as the baseline ({GEN} + {VER}); four configuration levers changed, "
               "plus two always-on gates the relaxed scope check arms")
    footer(fig, "research/prototype/config/prototype.yaml; FINAL_PRODUCTION_CONFIG.md; " + SRC_ALL,
           "Highlighted panels mark where the modified system adds or changes functionality. "
           "Generation model, correction model, prompts, seed and confidence threshold are "
           "identical to the baseline.")
    save(fig, "D02_modified_architecture_nyayamind_production.png")
    register("D02", "D02_modified_architecture_nyayamind_production.png",
             "Modified architecture — NyayaMind 2026-08-27 shipped production configuration",
             "Show exactly where the modified system adds functionality",
             "config/prototype.yaml; FINAL_PRODUCTION_CONFIG.md; src/*.py",
             "Modified: NyayaMind production", "Highlighted panels are the added/changed parts.")


# ==========================================================================
# D03 — side by side
# ==========================================================================
def d03():
    fig, ax = new_canvas(12.5, 7.4)
    rows = [
        ("Case input", "NyayaRAG summarized_text — identical", "NyayaRAG summarized_text — identical",
         BG_INPUT, False),
        ("Generation", f"{GEN}\n4-bit {C.QUANT} · greedy · 200 new tokens",
         f"{GEN}\n4-bit {C.QUANT} · greedy · 200 new tokens", BG_GEN, False),
        ("Claim parsing", "claim_parser.extract_claims()\nclaim_text only",
         "claim_parser.extract_claims()\n+ assertion_text / assertion_spans", BG_PARSE, True),
        ("Evidence retrieval", "evidence pool v0\n59 usable records",
         "evidence pool v0 + v1\n136 usable records", BG_EVID, True),
        ("NLI verification", f"{VER}\npremise_framing = \"bare\"",
         f"{VER}\npremise_framing = \"labeled\"", BG_VERIFY, True),
        ("Verdict application", "threshold 0.70 · ENTAILED / CONTRADICTED /\n"
                                "NOT_ENOUGH_INFORMATION / NO_EVIDENCE",
         "threshold 0.70 · same four verdict states\n(UNCHANGED)", BG_VERIFY, False),
        ("Selective correction", f"{COR}\nfirst flagged claim only",
         f"{COR}\nfirst flagged claim only (UNCHANGED)", BG_CORRECT, False),
        ("Scope / safety gate", "full-sentence byte-for-byte rule\nsibling-regression net inactive",
         "assertion_spans per-citation fragments\n+ sibling-regression re-verification active",
         BG_SAFETY, True),
        ("Re-verification", "hypothesis = full bundled sentence",
         "hypothesis = narrower assertion_text\nwhen a safe split exists", BG_CORRECT, True),
        ("Final assembly", "final_field.source ∈ 4 states", "final_field.source ∈ 5 states\n"
                                                            "(+ correction_sibling_regression)",
         BG_OUTPUT, True),
    ]
    top, rowh, gap = 85.0, 7.2, 1.1
    ax.text(33, 94.5, "Baseline: NyayaMind v0\n(pre-2026-08-27)", ha="center", va="center",
            fontsize=S(9, 12.5), fontweight="bold", color="#555555")
    ax.text(71, 94.5, "Modified: NyayaMind production\n(2026-08-27, shipped)", ha="center",
            va="center", fontsize=S(9, 12.5), fontweight="bold", color=C.C_MODIFIED)
    for i, (stage, a, b, fc, changed) in enumerate(rows):
        y = top - i * (rowh + gap)
        ax.text(1.5, y, stage, ha="left", va="center", fontsize=S(7.4, 10.2),
                fontweight="bold", color="#222222")
        box(ax, 33, y, 29, rowh, a, fc=fc, fs=S(6.5, 9.0))
        box(ax, 71, y, 29, rowh, b, fc=BG_NEW if changed else fc,
            ec=NEW_EDGE if changed else EDGE, lw=1.7 if changed else 1.2, fs=S(6.5, 9.0))
        if changed:
            ax.text(87.0, y, "CHANGED", ha="left", va="center", fontsize=S(6.2, 8.6),
                    fontweight="bold", color="#8A6100")
        else:
            ax.text(87.0, y, "identical", ha="left", va="center", fontsize=S(6.2, 8.6),
                    color="#777777")
        arrow(ax, (48, y), (56, y), color=NEW_EDGE if changed else "#AAAAAA", lw=1.1)
    titleblock(fig, "Baseline vs modified NyayaMind — stage-by-stage component comparison",
               "Both systems execute the identical pipeline code in research/prototype/src/; "
               "six of ten stages differ only by a configuration value")
    footer(fig, "research/prototype/config/prototype.yaml; comparison_config.json; " + SRC_ALL,
           "The generation model, correction model, prompts, decoding parameters, seed and "
           "confidence threshold are byte-identical between the two systems.")
    save(fig, "D03_baseline_vs_modified_side_by_side.png")
    register("D03", "D03_baseline_vs_modified_side_by_side.png",
             "Baseline vs modified NyayaMind — stage-by-stage component comparison",
             "The single slide that answers 'what actually changed?'",
             "config/prototype.yaml; comparison_config.json; src/*.py",
             "Baseline vs Modified", "Configuration differences only, plus the parser fix.")


# ==========================================================================
# D04 — complete pipeline
# ==========================================================================
def d04():
    fig, ax = new_canvas(12.5, 7.0)
    y = 76
    stages = [
        (11, "[1] Generation",
         "Qwen2.5-7B-Instruct\n4-bit nf4, greedy\nStatuteGroundingGenerator\n.generate()", BG_GEN),
        (29, "[2] Claim parsing",
         "claim_parser\n.extract_claims()\ndeterministic regex\n(no model call)", BG_PARSE),
        (47, "[3] Evidence retrieval",
         "evidence_matcher\n.match_evidence()\nexact → fuzzy → none\npool v0+v1 (136)", BG_EVID),
        (65, "[4] NLI verification",
         "DeBERTa-v3-base-\nmnli-fever-anli\nformat_premise(labeled)\nNLIVerifier.verify()",
         BG_VERIFY),
        (85, "[5] Selective correction",
         "Qwen2.5-7B-Instruct\nSelectiveCorrector\n.correct()\nfirst flagged claim only",
         BG_CORRECT),
    ]
    boxes = []
    for cx, title, body, fc in stages:
        box(ax, cx, y + 13, 17, 6.5, title, fc="#FFFFFF", fs=S(7.4, 10.2), weight="bold")
        boxes.append(box(ax, cx, y, 17, 17, body, fc=fc, fs=S(6.6, 9.1)))
    for a, b in zip(boxes, boxes[1:]):
        arrow(ax, right(a), left(b))

    g1 = box(ax, 85, 46, 22, 13, "[6] Scope gate\npipeline._scope_violation()\n"
                                 'atomic_scope_check =\n"assertion_spans"',
             fc=BG_SAFETY, fs=S(6.5, 9.0))
    g2 = box(ax, 55, 46, 24, 13, "[6b] Sibling-regression\nre-verification\n"
                                 "_reverify_sibling_regressions()", fc=BG_SAFETY, fs=S(6.5, 9.0))
    g3 = box(ax, 24, 46, 22, 13, "[7] Re-verify the replacement\n"
                                 "narrow_reverification_\nhypothesis = true",
             fc=BG_CORRECT, fs=S(6.5, 9.0))
    box(ax, 38, 17, 62, 14,
        "Final assembly — pipeline.run_case()\nfinal_field.source ∈ {original · corrected · "
        "correction_failed ·\ncorrection_scope_violation · correction_sibling_regression}\n"
        "+ reproducibility block (seed, model ids, quantization, library versions)",
        fc=BG_OUTPUT, fs=S(6.6, 9.1))
    box(ax, 85, 17, 22, 14, "Any gate failing →\nthe ORIGINAL text\nships unchanged",
        fc="#FBEAEA", ec="#B04040", fs=S(6.6, 9.1))
    arrow(ax, below(boxes[4]), above(g1))
    arrow(ax, left(g1), right(g2), "in scope", label_dy=2.8)
    arrow(ax, left(g2), right(g3), "no sibling\nregression", label_dy=3.2)
    arrow(ax, below(g3), (24, 24.5), "ENTAILED", label_dy=0.4)
    arrow(ax, below(g1), (85, 24.5), color="#B04040", lw=1.1, ls="--")
    arrow(ax, (g2[0] + 6, g2[1] - g2[3] / 2), (78, 24.5), color="#B04040", lw=1.1, ls="--")
    arrow(ax, (g3[0] + 6, g3[1] - g3[3] / 2), (72, 24.5), color="#B04040", lw=1.1, ls="--",
          rad=-0.2)
    titleblock(fig, "Complete NyayaMind pipeline — seven stages, production configuration",
               f"Generator {GEN} (4-bit {C.QUANT}) and verifier {VER}; a correction ships only if "
               "it clears the scope gate, the sibling-regression net and an ENTAILED re-verification")
    footer(fig, "research/prototype/src/pipeline.py (run_case, apply_verification, "
                "apply_selective_correction, _scope_violation, _reverify_sibling_regressions); " + SRC_ALL,
           "Modes A / B / C decide how far a case travels: A stops after stage 3, B adds stage 4 "
           "as a diagnostic only, C runs stages 5-7. Box labels use short model names; the full "
           "model ids are given in the subtitle above.")
    save(fig, "D04_complete_pipeline.png")
    register("D04", "D04_complete_pipeline.png",
             "Complete NyayaMind pipeline -- seven stages, production configuration",
             "One-slide view of the whole system",
             "src/pipeline.py; src/*.py", "Modified: NyayaMind production",
             "Stage numbering follows the repository README's own architecture block.")


# ==========================================================================
# D05..D11 — per-stage diagrams
# ==========================================================================
def stage_canvas(title, subtitle):
    fig, ax = new_canvas(11.0, 6.4)
    titleblock(fig, title, subtitle)
    return fig, ax


def d05():
    fig, ax = stage_canvas(
        "Stage 2 — Claim parsing (deterministic, no model call)",
        "claim_parser.extract_claims(): one Claim per CITATION, not per sentence, so each "
        "provision gets its own independent evidence lookup and verdict")
    a = box(ax, 15, 78, 24, 13, "Generated\nstatutory_grounding\nparagraph\n(3–6 sentences)",
            fc=BG_GEN, fs=S(7.2, 10))
    b = box(ax, 45, 78, 24, 13, "split_sentences()\nregex on sentence\nboundaries", fc=BG_PARSE)
    c = box(ax, 78, 78, 26, 13, "extract_citations()\n(Section|Article|Order|Rule|\n"
                                "Regulation|Clause|Schedule)\n+ number + act name",
            fc=BG_PARSE, fs=S(6.8, 9.4))
    d = box(ax, 30, 50, 42, 15,
            "_trim_act_name() · normalize_act()\nacronym and full-form act resolution "
            "(IPC → \"indian penal code 1860\")", fc=BG_PARSE, fs=S(7.0, 9.6))
    e = box(ax, 78, 50, 30, 15,
            "_assign_assertion_texts()\n_assign_respectively_spans()\nverbatim per-citation "
            "sub-spans", fc=BG_NEW, ec=NEW_EDGE, lw=1.7, fs=S(7.0, 9.6))
    f = box(ax, 50, 20, 66, 15,
            "Claim(claim_id, claim_text, citation_extracted,\n"
            "assertion_text, assertion_spans)\n"
            "One sentence naming several provisions becomes one Claim PER provision — "
            "they share claim_text but carry different citations",
            fc=BG_OUTPUT, fs=S(6.9, 9.4))
    arrow(ax, right(a), left(b)); arrow(ax, right(b), left(c))
    arrow(ax, below(c), above(e)); arrow(ax, left(c), right(d), rad=-0.15)
    arrow(ax, below(d), (35, 27.5)); arrow(ax, below(e), (72, 27.5))
    new_badge(ax, 78, 66, "assertion_spans: added in the modified system")
    footer(fig, "research/prototype/src/claim_parser.py (extract_claims, extract_citations, "
                "_trim_act_name, normalize_act, _assign_assertion_texts, _assign_respectively_spans)",
           "assertion_text and assertion_spans are always contiguous substrings of the model's own "
           "generated text — the parser never synthesizes wording. The baseline computes them too "
           "but no gate reads them.")
    save(fig, "D05_stage_claim_parsing.png")
    register("D05", "D05_stage_claim_parsing.png", "Stage 2 — Claim parsing",
             "Explain atomic claim decomposition and why claims can share a sentence",
             "src/claim_parser.py", "Shared stage; assertion_spans used only by the modified system",
             "Deterministic regex, no LLM involved at this stage.")


def d06():
    fig, ax = stage_canvas(
        "Stage 3 — Evidence retrieval (deterministic, no model call)",
        "evidence_matcher.match_evidence(): exact normalized key first, subsection-loose retry, "
        "then a fuzzy act-name fallback; NO_EVIDENCE is a first-class outcome")
    a = box(ax, 16, 80, 26, 12, "ExtractedCitation\n(provision_type, number,\nsubsection, act_norm)",
            fc=BG_PARSE, fs=S(7.0, 9.6))
    pool = box(ax, 16, 50, 26, 20,
               "Usable evidence pool\ndata_loader.load_usable_evidence_from_config()\n\n"
               "Baseline: v0 only → 59 records\nModified: v0 + v1 → 136 records\n\n"
               "Only VERIFIED_EXACT /\nVERIFIED_CONTENT are usable",
               fc=BG_EVID, fs=S(6.6, 9.1))
    s1 = box(ax, 55, 82, 30, 11, "1. exact_normalized\n(type, number, subsection, act_norm)",
             fc=BG_EVID, fs=S(6.9, 9.5))
    s2 = box(ax, 55, 63, 30, 11, "2. exact match, subsection ignored\n(\"Section 25F(1)\" → "
                                 "\"Section 25F\")", fc=BG_EVID, fs=S(6.9, 9.5))
    s3 = box(ax, 55, 44, 30, 12, "3. fuzzy fallback\nsame type + number, act-name token\n"
                                 "overlap ≥ 0.8 (fuzzy_token_overlap_threshold)",
             fc=BG_EVID, fs=S(6.7, 9.2))
    s4 = box(ax, 55, 24, 30, 10, "4. NO_EVIDENCE\nthe verifier is never called",
             fc="#E4E4E4", fs=S(6.9, 9.5))
    hit = box(ax, 88, 63, 20, 26, "MatchResult(matched=True)\nEvidenceRecord\n\n"
                                  "canonical_text →\nthe NLI premise\n\n"
                                  "provision_type / number / act →\nthe \"labeled\" premise prefix",
              fc=BG_OUTPUT, fs=S(6.6, 9.1))
    arrow(ax, below(a), above(pool), "", rad=0)
    arrow(ax, right(a), left(s1))
    for u, v, lbl in ((s1, s2, "miss"), (s2, s3, "miss"), (s3, s4, "miss")):
        arrow(ax, below(u), above(v), lbl)
    for s in (s1, s2, s3):
        arrow(ax, right(s), left(hit), "hit", color="#2A6F2A", rad=0.12)
    arrow(ax, right(pool), (40, 50), color="#777777", lw=1.1)
    footer(fig, "research/prototype/src/evidence_matcher.py; research/prototype/src/data_loader.py; "
                "research/data/evidence/{canonical_statutes,canonical_statutes_v1}.jsonl",
           "A NO_EVIDENCE outcome means the citation was not found in this ~140-provision corpus. "
           "It is NOT evidence that the citation was wrong.")
    save(fig, "D06_stage_evidence_retrieval.png")
    register("D06", "D06_stage_evidence_retrieval.png", "Stage 3 — Evidence retrieval",
             "Show the deterministic match cascade and where the pool size matters",
             "src/evidence_matcher.py; src/data_loader.py",
             "Shared stage; evidence pool size differs between systems",
             "NO_EVIDENCE reflects a corpus limit, not a detected citation error.")


def d07():
    fig, ax = stage_canvas(
        "Stage 4 — NLI verification",
        f"{VER} scores one (premise, hypothesis) pair per evidence-matched claim; "
        "the premise construction is the single lever that differs between the systems")
    prem_b = box(ax, 21, 80, 36, 13, "BASELINE premise — format_premise(\"bare\")\n"
                                     "\"Whoever commits murder shall be\npunished …\"",
                 fc=BG_SHARED, fs=S(6.7, 9.2))
    prem_m = box(ax, 21, 62, 36, 13, "MODIFIED premise — format_premise(\"labeled\")\n"
                                     "\"Section 302 of The Indian Penal Code, 1860:\n"
                                     "Whoever commits murder …\"",
                 fc=BG_NEW, ec=NEW_EDGE, lw=1.7, fs=S(6.7, 9.2))
    hyp = box(ax, 21, 43, 36, 12, "Hypothesis — the extracted claim_text\n"
                                  "\"According to Section 302 of the IPC, …\"",
              fc=BG_PARSE, fs=S(6.7, 9.2))
    model = box(ax, 55, 62, 20, 20, "NLIVerifier.verify()\nDeBERTa-v3-base-\nmnli-fever-anli\n\n"
                                    "fp16 · max_seq_len 512\nCUDA by default;\nCPU is an explicit "
                                    "opt-in", fc=BG_VERIFY, fs=S(6.4, 8.9))
    thr = box(ax, 84, 62, 26, 20,
              "softmax → argmax\n\nentailment → ENTAILED\ncontradiction → CONTRADICTED\n"
              "neutral → NOT_ENOUGH_INFORMATION\n\nconfidence < 0.70 → downgrade to\n"
              "NOT_ENOUGH_INFORMATION with\nsub_reason = \"low_confidence\"",
              fc=BG_VERIFY, fs=S(6.1, 8.5))
    note = box(ax, 50, 15, 84, 13,
               "Why the labeled premise matters: a generated claim is almost always ATTRIBUTED "
               "(\"According to Section 302 …\").\nA bare premise never names Section 302, so half "
               "the hypothesis is genuinely unsupported and a well-behaved NLI model\nmust answer "
               "neutral. On GOLD-01 this is worth 92 of the 112 baseline errors.",
               fc="#F4F4F4", fs=S(6.8, 9.3))
    for p in (prem_b, prem_m, hyp):
        arrow(ax, right(p), left(model), rad=0.05)
    arrow(ax, right(model), left(thr))
    arrow(ax, below(model), above(note), color="#777777", lw=1.0)
    footer(fig, "research/prototype/src/verifier.py (format_premise, NLIVerifier.verify); "
                "research/prototype/src/pipeline.py (apply_verification, _premise_for_claim)",
           "The verifier reports a small public NLI model's statistical confidence, NOT legal "
           "correctness — src/verifier.py attaches that disclaimer to every VerificationResult.")
    save(fig, "D07_stage_nli_verification.png")
    register("D07", "D07_stage_nli_verification.png", "Stage 4 — NLI verification",
             "Explain the premise-framing lever, the project's largest measured effect",
             "src/verifier.py; src/pipeline.py", "Baseline vs Modified premise framing",
             "NLI confidence is not a legal-correctness determination.")


def d08():
    fig, ax = stage_canvas(
        "Stage 4b — Verdict application and correction triggering",
        "pipeline.apply_verification() writes one verdict per claim; "
        "_should_trigger_correction() decides which verdicts are worth a correction attempt")
    start = box(ax, 15, 80, 24, 11, "Claim record\nwith matched evidence", fc=BG_PARSE)
    v = box(ax, 45, 80, 26, 11, "NLIVerifier.verify()\nverdict + confidence", fc=BG_VERIFY)
    outcomes = [
        (12, "ENTAILED", "trigger: NO\nverdict recorded", "#DDEBDD"),
        (35, "CONTRADICTED", "trigger: YES\n(regardless of confidence)", "#F6D6D6"),
        (58, "NOT_ENOUGH_INFORMATION\nsub_reason = \"low_confidence\"",
         "trigger: YES\n(the sub-threshold downgrade)", "#F6E3D6"),
        (83, "NOT_ENOUGH_INFORMATION\n(genuine high-confidence neutral)",
         "trigger: NO\na legitimate verdict in itself", "#EDEDED"),
    ]
    for cx, label, action, fc in outcomes:
        b = box(ax, cx, 50, 21, 14, label, fc=fc, fs=S(6.5, 9.0))
        box(ax, cx, 28, 21, 11, action, fc="#FFFFFF", fs=S(6.5, 9.0))
        arrow(ax, below(v), above(b), rad=0.08)
        arrow(ax, below(b), (cx, 33.5))
    box(ax, 50, 11, 80, 9,
        "NO_EVIDENCE claims never reach the verifier and never trigger a correction.\n"
        "In mode C only the FIRST triggering claim in a field drives the single correction attempt "
        "(a documented v0 simplification).", fc="#F4F4F4", fs=S(6.8, 9.3))
    arrow(ax, right(start), left(v))
    footer(fig, "research/prototype/src/pipeline.py (apply_verification, "
                "_should_trigger_correction); research/prototype/src/verifier.py",
           "Verdict states and trigger rules are identical in the baseline and modified systems — "
           "only which verdict a claim receives changes, because the premise changes.")
    save(fig, "D08_stage_verdict_application.png")
    register("D08", "D08_stage_verdict_application.png",
             "Stage 4b — Verdict application and correction triggering",
             "Show which verdicts do and do not cause a correction attempt",
             "src/pipeline.py", "Shared stage (identical rules in both systems)",
             "First-flagged-claim-only correction is a documented v0 simplification.")


def d09():
    fig, ax = stage_canvas(
        "Stages 5 and 7 — Selective correction and re-verification",
        "The corrector rewrites ONE sentence and must copy every other sentence verbatim; "
        "the replacement is then re-verified against its own evidence")
    a = box(ax, 16, 82, 28, 12, "First flagged claim\n+ full original paragraph\n+ matched statute text",
            fc=BG_VERIFY, fs=S(6.9, 9.5))
    b = box(ax, 52, 82, 32, 12, f"SelectiveCorrector.correct()\n{COR}\ngreedy · "
                                "max_new_tokens=220 · max_attempts = 1",
            fc=BG_CORRECT, fs=S(6.7, 9.2))
    c = box(ax, 86, 82, 22, 12, "Regenerated full\nparagraph", fc=BG_CORRECT, fs=S(6.9, 9.5))
    d = box(ax, 86, 58, 22, 13, "Scope + safety gates\n(see diagram D10)", fc=BG_SAFETY,
            fs=S(6.9, 9.5))
    e = box(ax, 52, 58, 32, 13, "Re-parse the corrected text\n_citation_identity() + ordinal "
                                "position\n→ the SAME citation slot", fc=BG_PARSE, fs=S(6.7, 9.2))
    f = box(ax, 16, 58, 28, 13, "Re-match evidence\nevidence_matcher.match_evidence()",
            fc=BG_EVID, fs=S(6.9, 9.5))
    g = box(ax, 16, 34, 28, 14, "Re-verify with the SAME\npremise framing that flagged it\n"
                                "hypothesis = assertion_text when\nnarrow_reverification_"
                                "hypothesis = true", fc=BG_NEW, ec=NEW_EDGE, lw=1.7, fs=S(6.5, 9.0))
    ship = box(ax, 52, 34, 26, 14, "verdict == ENTAILED ?", fc="#FFFFFF", fs=S(7.4, 10.2),
               weight="bold")
    ok = box(ax, 52, 12, 26, 11, "status = \"corrected\"\nfinal_field.source = \"corrected\"",
             fc=BG_OUTPUT, fs=S(6.9, 9.5))
    no = box(ax, 86, 34, 22, 11, "status = \"correction_failed\"\nthe ORIGINAL text ships",
             fc="#FBEAEA", fs=S(6.9, 9.5))
    arrow(ax, right(a), left(b)); arrow(ax, right(b), left(c))
    arrow(ax, below(c), above(d)); arrow(ax, left(d), right(e), "in scope")
    arrow(ax, left(e), right(f)); arrow(ax, below(f), above(g))
    arrow(ax, right(g), left(ship)); arrow(ax, below(ship), above(ok), "yes", color="#2A6F2A")
    arrow(ax, right(ship), left(no), "no", color="#8A2020")
    new_badge(ax, 16, 22, "narrow re-verification hypothesis: modified system only")
    footer(fig, "research/prototype/src/corrector.py; research/prototype/src/pipeline.py "
                "(apply_selective_correction, _citation_identity)",
           "Citation-identity preservation (ordinal matching among same-citation claims) is core "
           "pipeline logic in BOTH systems and was never a configuration toggle.")
    save(fig, "D09_stage_correction_and_reverification.png")
    register("D09", "D09_stage_correction_and_reverification.png",
             "Stages 5 and 7 — Selective correction and re-verification",
             "Show the ENTAILED-only shipping gate and the narrow-hypothesis change",
             "src/corrector.py; src/pipeline.py", "Baseline vs Modified re-verification hypothesis",
             "Only the first flagged claim is ever corrected, once.")


def d10():
    fig, ax = stage_canvas(
        "Stage 6 — Scope and safety gate (programmatic, not prompt-only)",
        "Three independent checks, each of which can only REJECT a correction — none can approve "
        "one that the ENTAILED re-verification gate would refuse")
    src = box(ax, 15, 84, 26, 11, "Regenerated paragraph\nfrom SelectiveCorrector", fc=BG_CORRECT,
              fs=S(6.9, 9.5))
    g1 = box(ax, 50, 84, 34, 12, "Check 1 — scope violation\npipeline._scope_violation()",
             fc=BG_SAFETY, fs=S(7.2, 10))
    base = box(ax, 27, 62, 34, 16, "BASELINE rule (atomic_scope_check = false)\n"
                                   "every unflagged claim's FULL claim_text must\n"
                                   "reappear byte-for-byte in the corrected text",
               fc=BG_SHARED, fs=S(6.6, 9.1))
    mod = box(ax, 71, 62, 38, 16, "MODIFIED rule (atomic_scope_check = \"assertion_spans\")\n"
                                  "each unflagged claim's own verbatim assertion_spans\n"
                                  "must ALL survive; falls back to the full sentence\n"
                                  "whenever no safe split pattern applies",
              fc=BG_NEW, ec=NEW_EDGE, lw=1.7, fs=S(6.5, 9.0))
    g2 = box(ax, 50, 38, 44, 13, "Check 2 — sibling regression\n_reverify_sibling_regressions(): "
                                 "re-parse and genuinely re-verify\nevery sibling claim against "
                                 "its own evidence", fc=BG_NEW, ec=NEW_EDGE, lw=1.7, fs=S(6.6, 9.1))
    g3 = box(ax, 50, 20, 44, 11, "Check 3 — citation identity\n_citation_identity() ordinal "
                                 "matching — always on in BOTH systems", fc=BG_SAFETY,
             fs=S(6.6, 9.1))
    rej = box(ax, 89, 29, 20, 20, "Any check failing →\nnever ship\n\n"
                                  "correction_scope_violation\ncorrection_sibling_regression\n"
                                  "correction_failed\n\nthe ORIGINAL text is\nreturned unchanged",
              fc="#FBEAEA", ec="#B04040", fs=S(6.4, 8.9))
    arrow(ax, right(src), left(g1))
    arrow(ax, below(g1), above(base), rad=0.1); arrow(ax, below(g1), above(mod), rad=-0.1)
    arrow(ax, below(base), above(g2), rad=-0.1); arrow(ax, below(mod), above(g2), rad=0.1)
    arrow(ax, below(g2), above(g3))
    arrow(ax, right(g2), left(rej), color="#8A2020", rad=0.1)
    arrow(ax, right(g3), left(rej), color="#8A2020", rad=-0.1)
    ax.text(14, 38, "The sibling-regression net\nexists specifically to cover\nthe gap the relaxed "
                    "scope\ncheck opens. It arms\nautomatically whenever\natomic_scope_check is "
                    "truthy\nand cannot be disabled\nseparately.",
            ha="center", va="center", fontsize=S(6.4, 8.9), color="#5C4400",
            bbox=dict(boxstyle="round,pad=0.35", facecolor=BG_NEW, edgecolor=NEW_EDGE))
    footer(fig, "research/prototype/src/pipeline.py (_scope_violation, "
                "_reverify_sibling_regressions, _citation_identity); FINAL_PRODUCTION_CONFIG.md §3, §6, §7",
           "Observed across the full tested correction history: 0 unsafe corrections shipped in "
           "122 attempts, 18 scope-gate rejections and 37 re-verification rejections on the 56 "
           "natural attempts.")
    save(fig, "D10_stage_scope_and_safety_gate.png")
    register("D10", "D10_stage_scope_and_safety_gate.png",
             "Stage 6 — Scope and safety gate",
             "Show that the safety layer is programmatic and reject-only",
             "src/pipeline.py; FINAL_PRODUCTION_CONFIG.md",
             "Baseline vs Modified scope rule", "Gates can only reject, never approve.")


def d11():
    fig, ax = stage_canvas(
        "Final answer assembly — pipeline.run_case()",
        "Exactly one of five terminal states is recorded per case, together with the full "
        "reproducibility block that makes the run auditable")
    src = box(ax, 50, 92, 74, 9, "Correction summary + claim records + evidence summary + "
                                 "verification summary", fc=BG_CORRECT, fs=S(6.9, 9.5))
    states = [
        (78, "not_triggered", "final_field.source = \"original\"  —  no claim triggered correction",
         BG_OUTPUT),
        (66, "corrected", "final_field.source = \"corrected\"  —  the ONLY state that ships "
                          "regenerated text", "#CBE6CB"),
        (54, "correction_failed",
         "final_field.source = \"correction_failed\"  —  original text kept", "#FBEAEA"),
        (42, "correction_scope_violation",
         "final_field.source = \"correction_scope_violation\"  —  original text kept", "#FBEAEA"),
        (30, "correction_sibling_regression",
         "final_field.source = \"correction_sibling_regression\"  —  original text kept\n"
         "(reachable only in the modified system)", "#FFF0E0"),
    ]
    spine_x = 6.0
    ax.plot([spine_x, spine_x], [states[-1][0], 87.0], color=EDGE, lw=1.3, zorder=1)
    ax.plot([spine_x, 50], [87.0, 87.0], color=EDGE, lw=1.3, zorder=1)
    for y, status, body, fc in states:
        s = box(ax, 29, y, 36, 9.5, f"status = \"{status}\"", fc="#FFFFFF", fs=S(6.6, 9.1),
                weight="bold")
        o = box(ax, 73, y, 48, 9.5, body, fc=fc, fs=S(6.2, 8.6))
        arrow(ax, (spine_x, y), left(s))
        arrow(ax, right(s), left(o))
    box(ax, 50, 17, 92, 10,
        "reproducibility block written on every record: mode · seed 42 · generation_model · "
        f"verification_model · quantization (4-bit {C.QUANT}) ·\nconfidence_threshold · "
        "premise_framing · UTC timestamp · installed torch / transformers / accelerate / "
        "bitsandbytes / peft versions", fc=BG_INPUT, fs=S(6.6, 9.1))
    box(ax, 50, 6, 92, 7,
        "Every VerificationResult also carries the standing disclaimer: "
        "\"NLI statistical confidence, not a legal-correctness determination.\"",
        fc="#F4F4F4", fs=S(6.6, 9.1))
    footer(fig, "research/prototype/src/pipeline.py (run_case); research/prototype/src/verifier.py",
           "The baseline can reach four of these five states; correction_sibling_regression is "
           "only reachable once an atomic scope-check mode arms the sibling-regression net.")
    save(fig, "D11_final_answer_assembly.png")
    register("D11", "D11_final_answer_assembly.png", "Final answer assembly — pipeline.run_case()",
             "Show the five terminal states and the reproducibility record",
             "src/pipeline.py", "Baseline reaches 4 states; Modified reaches 5",
             "Only 'corrected' ever ships regenerated text.")


# ==========================================================================
# D12 — full data flow
# ==========================================================================
def d12():
    fig, ax = new_canvas(13.0, 6.6)
    lanes = [
        (86, "INPUT", BG_INPUT, [
            ("NyayaRAG\nCaseText_Statutes\n(SCI 56k summaries)", 21),
            ("canonical_statutes.jsonl\n+ canonical_statutes_v1.jsonl\n+ their audit files", 44),
            ("config/prototype.yaml\n(seed 42, thresholds,\nmodel ids, framing)", 66),
            ("scripts/run_mvp.py\n--mode {A,B,C}\ncapped at 5 cases", 88),
        ]),
    ]
    for y, lane, fc, items in lanes:
        ax.text(2, y, lane, ha="left", va="center", fontsize=S(7.6, 10.4), fontweight="bold",
                rotation=0, color="#444444")
        for text, cx in items:
            box(ax, cx, y, 21, 12, text, fc=fc, fs=S(6.2, 8.6))

    mid = [
        (62, "PIPELINE", [
            ("generate_and_parse()\ngeneration → claims →\nevidence match", 24, BG_GEN),
            ("apply_verification()\nper-claim verdicts\n(modes B and C)", 53, BG_VERIFY),
            ("apply_selective_correction()\ncorrect → scope gate →\nre-verify (mode C)", 83, BG_CORRECT),
        ]),
    ]
    for y, lane, items in mid:
        ax.text(2, y, lane, ha="left", va="center", fontsize=S(7.6, 10.4), fontweight="bold",
                color="#444444")
        for text, cx, fc in items:
            box(ax, cx, y, 25, 13, text, fc=fc, fs=S(6.2, 8.6))

    ax.text(2, 34, "OUTPUT", ha="left", va="center", fontsize=S(7.6, 10.4), fontweight="bold",
            color="#444444")
    o1 = box(ax, 24, 34, 30, 14, "One JSONL record per case\ndocument_id · generated_field · "
                                 "claims[] ·\nevidence · verification · correction ·\nfinal_field · "
                                 "reproducibility", fc=BG_OUTPUT, fs=S(6.2, 8.6))
    o2 = box(ax, 60, 34, 26, 14, "research/prototype/outputs/\n(read-only in this package)",
             fc=BG_OUTPUT, fs=S(6.6, 9.1))
    o3 = box(ax, 88, 34, 22, 14, "evaluation/ workspace\nmetrics · figures · reports",
             fc=BG_OUTPUT, fs=S(6.6, 9.1))
    arrow(ax, right(o1), left(o2)); arrow(ax, right(o2), left(o3))

    ax.text(2, 12, "THIS PACKAGE", ha="left", va="center", fontsize=S(7.6, 10.4),
            fontweight="bold", color="#444444")
    p1 = box(ax, 30, 12, 34, 12, "Output_phase_3_vedant/metrics/*.csv\nlocked figure-data "
                                 "contracts extracted\nfrom the artifacts above (read-only)",
             fc=BG_NEW, ec=NEW_EDGE, fs=S(6.4, 8.8))
    p2 = box(ax, 74, 12, 34, 12, "figures/ · diagrams/ · tables/ · ppt_assets/\nrendered only from "
                                 "those locked CSVs", fc=BG_NEW, ec=NEW_EDGE, fs=S(6.4, 8.8))
    arrow(ax, right(p1), left(p2))
    for cx, tx in ((21, 24), (44, 24), (66, 53), (88, 83)):
        arrow(ax, (cx, 80), (tx, 68.5), color="#888888", lw=1.0)
    for cx, tx in ((24, 24), (53, 60), (83, 88)):
        arrow(ax, (cx, 55.5), (tx, 41), color="#888888", lw=1.0)
    arrow(ax, (60, 27), (40, 18), color=NEW_EDGE, lw=1.2)
    titleblock(fig, "Full data flow — case input to mentor-facing artifact",
               "Everything below the OUTPUT lane is read-only in this package: no experiment is "
               "re-run and no existing artifact is modified")
    footer(fig, "research/prototype/scripts/run_mvp.py; research/prototype/src/pipeline.py; "
                "research/prototype/evaluation/; Output_phase_3_vedant/scripts/",
           "The evaluation workspace and this package only ever READ src/, config/, outputs/ and "
           "research/data/; they write nothing back into them.")
    save(fig, "D12_full_data_flow.png")
    register("D12", "D12_full_data_flow.png", "Full data flow — case input to mentor-facing artifact",
             "Trace provenance end to end, including this package's own read-only position",
             "scripts/run_mvp.py; src/pipeline.py; evaluation/", "Both systems",
             "This package writes only into Output_phase_3_vedant/.")


# ==========================================================================
# D13 — modes A / B / C
# ==========================================================================
def d13():
    fig, ax = new_canvas(11.5, 6.0)
    stages = ["Generate\nstatutory_grounding", "Extract claims", "Match evidence",
              "Verify claims", "Correct + gate\n+ re-verify"]
    modes = [
        ("Mode A — generation only", [True, True, True, False, False],
         "final_field.source = \"original\"; verification_model = null"),
        ("Mode B — generation + verification (diagnostic)", [True, True, True, True, False],
         "verdicts recorded, but final_field is ALWAYS the original text"),
        ("Mode C — generation + verification + selective correction",
         [True, True, True, True, True],
         "the only mode that can ship regenerated text"),
    ]
    for i, (name, active, note) in enumerate(modes):
        y = 78 - i * 26
        ax.text(2, y + 11, name, ha="left", va="center", fontsize=S(8, 11),
                fontweight="bold", color="#222222")
        prev = None
        for j, (st, on) in enumerate(zip(stages, active)):
            cx = 13 + j * 19
            b = box(ax, cx, y, 17, 12, st,
                    fc=(BG_GEN, BG_PARSE, BG_EVID, BG_VERIFY, BG_CORRECT)[j] if on else "#F0F0F0",
                    ec=EDGE if on else "#BBBBBB",
                    tc="#111111" if on else "#999999",
                    ls="solid" if on else "dashed", fs=S(6.6, 9.1))
            if prev is not None:
                arrow(ax, right(prev), left(b), color=EDGE if on else "#CCCCCC",
                      lw=1.3 if on else 0.9, ls="-" if on else "--")
            prev = b
        ax.text(13, y - 9.5, note, ha="left", va="center", fontsize=S(6.5, 9),
                color="#555555", style="italic")
    titleblock(fig, "Pipeline modes A / B / C — how far one case travels",
               "All three modes share the identical generation, claim-extraction and "
               "evidence-matching stage, so A vs B vs C is a paired comparison, not three "
               "different generations")
    footer(fig, "research/prototype/src/pipeline.py (MODES, run_case); "
                "research/prototype/scripts/run_mvp.py",
           "Mode is orthogonal to the baseline/modified distinction: both systems support all "
           "three modes, and every comparison in this package holds the mode fixed.")
    save(fig, "D13_pipeline_modes_a_b_c.png")
    register("D13", "D13_pipeline_modes_a_b_c.png", "Pipeline modes A / B / C",
             "Prevent the common confusion between modes and system configurations",
             "src/pipeline.py; scripts/run_mvp.py", "Both systems",
             "Mode is orthogonal to the baseline/modified configuration difference.")


# ==========================================================================
# D14 — out-of-scope reference baseline
# ==========================================================================
def d14():
    fig, ax = new_canvas(11.5, 6.0)
    a = box(ax, 26, 76, 44, 20,
            f"RhetoricLLaMA reproduction (research/baseline/)\n\nBase model: {C.RHETORIC_BASE_MODEL}"
            f"\nLoRA adapter: {C.RHETORIC_ADAPTER}\n4-bit nf4 · max_new_tokens=100\n\n"
            "TASK: sentence-level rhetorical-role classification\n(labels 0–6: Facts, Issue, "
            "Arguments, Reasoning, Decision …)", fc="#EDEDED", fs=S(6.5, 9.0))
    b = box(ax, 74, 76, 44, 20,
            f"NyayaMind statutory-claim verification\n\nGenerator: {GEN}\nVerifier: {VER}\n"
            "4-bit nf4 · max_new_tokens=200\n\nTASK: does each cited provision actually say what\n"
            "the generated summary claims it says?", fc=BG_VERIFY, fs=S(6.5, 9.0))
    ax.plot([50, 50], [58, 90], color="#B04040", lw=2.0, linestyle="--")
    ax.text(50, 52, "DIFFERENT TASK · DIFFERENT DATASET · DIFFERENT OUTPUT SPACE",
            ha="center", va="center", fontsize=S(7.6, 10.4), fontweight="bold", color="#B04040")
    box(ax, 50, 33, 90, 17,
        "Why RhetoricLLaMA is NOT the quantitative baseline in this package\n\n"
        "• It classifies rhetorical roles of sentences; NyayaMind verifies statutory claims against "
        "canonical statute text — there is no shared metric.\n"
        "• Only a ONE-ROW smoke test was ever executed (research/baseline/BASELINE.md); no "
        "dataset-wide run, no training, no output verification.\n"
        "• comparison_config.json marks it \"explicitly_out_of_scope\" for exactly this reason.\n"
        "• Its role in this project is real but narrow: NyayaMind inherits its pinned "
        "quantization / library versions (accelerate==0.29.3) from that reproduction.",
        fc="#FBEAEA", ec="#B04040", fs=S(6.4, 8.9))
    box(ax, 50, 11, 90, 9,
        "The quantitative baseline used throughout this package is instead NyayaMind's OWN "
        "pre-2026-08-27 production configuration —\nsame task, same data, same code, "
        "different configuration. See diagrams D01 and D03.", fc=BG_OUTPUT, fs=S(6.7, 9.2))
    titleframe = ("Reference baseline context — RhetoricLLaMA / LegalSeg is a different task, "
                  "not a metric baseline")
    titleblock(fig, titleframe,
               "Recorded here so the distinction is explicit for reviewers, not to make a "
               "performance comparison")
    footer(fig, "research/baseline/BASELINE.md; research/baseline/README.md; "
                "research/prototype/archive/2026-08-27_presentation/final_comparison/"
                "comparison_config.json (explicitly_out_of_scope)",
           "NO accuracy, F1 or any other quantitative comparison against RhetoricLLaMA is made "
           "anywhere in this package, because no comparable measurement exists.")
    save(fig, "D14_reference_baseline_rhetoricllama_out_of_scope.png")
    register("D14", "D14_reference_baseline_rhetoricllama_out_of_scope.png",
             "Reference baseline context — RhetoricLLaMA / LegalSeg is a different task",
             "Pre-empt the natural mentor question 'why not compare against the LegalSeg baseline?'",
             "research/baseline/BASELINE.md; comparison_config.json",
             "Out-of-scope reference (not compared)",
             "No quantitative comparison is made; only a one-row smoke test was ever run.")


DIAGRAMS = [d01, d02, d03, d04, d05, d06, d07, d08, d09, d10, d11, d12, d13, d14]


def main():
    global PPT
    for mode in (False, True):
        PPT = mode
        plt.rcParams.update({"figure.dpi": DPI, "savefig.dpi": DPI,
                             "font.size": 13.5 if mode else 9.5})
        print(f"\nRendering {'PPT (16:9)' if mode else 'publication'} diagrams ...")
        for fn in DIAGRAMS:
            fn()
            print(f"  {fn.__name__} ok")
    C.write_csv(C.BUILD_STATE / "diagrams.csv", list(MANIFEST[0].keys()), MANIFEST)
    print(f"\n{len(MANIFEST)} diagrams rendered in both variants.")


if __name__ == "__main__":
    main()
