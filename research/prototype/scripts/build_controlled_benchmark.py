#!/usr/bin/env python3
"""
CONTROLLED_VERIFIER_BENCHMARK (v2) — built ONLY from the 59 usable canonical
statute records. No LLM is used anywhere in construction: every hypothesis is
a deterministic, auditable transformation of canonical text, so the gold label
comes from the construction rule and never from any model's prediction.

Why v2 exists (v1 = scripts/build_verifier_benchmark.py, kept for provenance):
  v1's ENTAILED condition was the canonical text copied VERBATIM behind an
  attribution prefix, so it never tested paraphrase at all — which is the exact
  phenomenon under investigation. v1's NEI condition was one hard-coded English
  sentence repeated for all 59 records (one effective data point, not 59), its
  CONTRADICTED rewrites produced ungrammatical output ("has no power or
  authoritys"), and item ids used Python's salted `hash()`, so they changed on
  every interpreter run and the file was not reproducible.

Design — a 2x2 factorial on the ENTAILED side:

                       bare (no attribution)   attributed ("According to S.X of Act, ...")
  verbatim text        E1_verbatim             E2_verbatim_attributed
  paraphrased text     E3_paraphrase_bare      E4_paraphrase_attributed

That is the instrument for the research question. If DeBERTa entails E1 but not
E2, the blocker is the ATTRIBUTION PREFIX (a premise-side framing problem). If
it entails E1 but not E3, the blocker is PARAPHRASE (a genuine domain problem).
The two factors are independently attributable only because they are crossed.

CONTRADICTED mirrors the attribution factor (C1 bare / C2 attributed) so that
contradiction detection can be compared at matched framing.

NEI conditions:
  N1_other_provision  — the VERBATIM canonical text of a DIFFERENT provision in
                        the same corpus, checked against this record's evidence.
                        Grounded entirely in audited canonical text: no legal
                        fact is invented. Guaranteed non-entailed, and (unlike
                        v1) 59 distinct items rather than one repeated string.
  N2_procedural_add   — canonical rule PLUS an extraneous procedural condition
                        that the evidence does not state. Neutral by construction.

Every emitted item carries the rules that fired, so construction is auditable
against the canonical text. Items whose transformation could not be applied
grammatically are DROPPED and reported, never silently degraded.

Output: research/prototype/outputs/controlled_verifier_benchmark.jsonl
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

_PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROTOTYPE_ROOT.parent.parent))
sys.path.insert(0, str(_PROTOTYPE_ROOT))

import yaml

from src.data_loader import EvidenceRecord, load_usable_evidence

BENCHMARK_TAG = "CONTROLLED_VERIFIER_BENCHMARK"
BENCHMARK_VERSION = "v2"

ENTAILED = "ENTAILED"
CONTRADICTED = "CONTRADICTED"
NOT_ENOUGH_INFORMATION = "NOT_ENOUGH_INFORMATION"


# --------------------------------------------------------------------------
# Meaning-PRESERVING lexical paraphrase (legal register).
#
# Every pair here is a register swap, not a change of legal effect: the
# rewritten rule binds exactly the same conduct with exactly the same
# consequence. Deliberately conservative — nothing touches a bare modal
# ("shall"/"may"), a quantifier, a numeral, or a penalty amount, because those
# carry the operative content. ALL matching rules fire (not first-match), and
# the ones that fired are recorded on the item.
# --------------------------------------------------------------------------
_PARAPHRASE_RULES: list[tuple[str, str, str]] = [
    # -- offence/penalty register (IPC-style) --
    ("whoever_to_any_person_who", r"\bWhoever\b", "Any person who"),
    ("whoever_lc_to_any_person_who", r"\bwhoever\b", "any person who"),
    ("punished_with_to_liable_to_punishment_of", r"\bshall be punished with\b", "is liable to punishment of"),
    ("also_liable_fine_to_also_liable_a_fine", r"\bshall also be liable to fine\b", "is also liable to a fine"),
    ("shall_also_be_liable_to_is_also_liable_to", r"\bshall also be liable to\b", "is also liable to"),
    ("shall_be_liable_to_is_liable", r"\bshall be liable\b", "is liable"),
    ("imprisonment_for_life_to_life_imprisonment", r"\bimprisonment for life\b", "life imprisonment"),
    ("may_extend_to_to_may_go_up_to", r"\bmay extend to\b", "may go up to"),
    ("punishable_with_to_carrying_punishment_of", r"\bpunishable with\b", "carrying a punishment of"),
    # -- powers / duties (Constitution, CrPC, CPC style) --
    ("shall_have_power_to_is_empowered", r"\bshall have power\b", "is empowered"),
    ("shall_have_powers_to_is_empowered", r"\bshall have powers\b", "is empowered"),
    ("shall_be_deemed_to_be_to_is_to_be_regarded_as", r"\bshall be deemed to be\b", "is to be regarded as"),
    ("shall_not_to_is_not_to", r"\bshall not\b", "is not to"),
    ("notwithstanding_to_despite", r"\bNotwithstanding anything contained in\b", "Despite anything stated in"),
    ("subject_to_provisions_of_to_subject_to_what_is_provided_in",
     r"\bsubject to the provisions of\b", "subject to what is provided in"),
    ("in_accordance_with_to_in_conformity_with", r"\bin accordance with\b", "in conformity with"),
    ("in_relation_to_to_with_respect_to", r"\bin relation to\b", "with respect to"),
    ("by_reason_of_to_because_of", r"\bby reason of\b", "because of"),
    ("for_the_purposes_of_to_for_the_purpose_of", r"\bfor the purposes of\b", "for the purpose of"),
    ("as_the_case_may_be_to_whichever_applies", r"\bas the case may be\b", "whichever applies"),
    ("not_less_than_to_at_least", r"\bnot less than\b", "at least"),
    ("not_exceeding_to_no_more_than", r"\bnot exceeding\b", "no more than"),
    ("in_the_opinion_of_to_in_the_view_of", r"\bin the opinion of\b", "in the view of"),
    ("it_appears_to_to_it_seems_to", r"\bit appears to\b", "it seems to"),
    ("aggrieved_by_to_adversely_affected_by", r"\baggrieved by\b", "adversely affected by"),
    ("unless_context_otherwise_requires_to_except_where",
     r"\bunless the context otherwise requires\b", "except where the context requires otherwise"),
    ("in_furtherance_of_to_in_pursuance_of", r"\bin furtherance of\b", "in pursuance of"),
    ("every_to_each", r"\bEvery\b", "Each"),
    ("no_person_to_no_individual", r"\bNo person\b", "No individual"),
    ("each_of_such_persons_to_every_one_of_those_persons",
     r"\beach of such persons\b", "every one of those persons"),
    ("the_said_to_that", r"\bthe said\b", "that"),
    ("at_any_time_to_at_any_point", r"\bat any time\b", "at any point"),
]


def apply_paraphrase(text: str) -> tuple[str, list[str]]:
    """Apply every meaning-preserving substitution that matches.

    Returns (paraphrased_text, fired_rule_names). An empty rule list means the
    record has no safe paraphrase available and the caller must drop the
    paraphrase conditions for it rather than emit the text unchanged (an
    unchanged 'paraphrase' would silently duplicate E1/E2 and corrupt the
    factorial).
    """
    fired: list[str] = []
    out = text
    for name, pattern, repl in _PARAPHRASE_RULES:
        new = re.sub(pattern, repl, out)
        if new != out:
            fired.append(name)
            out = new
    return out, fired


# --------------------------------------------------------------------------
# Meaning-REVERSING negation, first-match wins.
#
# Order matters: the "shall not" -> "shall" rule MUST be tried first, otherwise
# a later bare-"shall" rule turns "shall not" into "shall not not" (this is the
# concrete bug v1 shipped). Each rule flips the operative modal in exactly one
# direction so the result is a clean contradiction, not word salad.
# --------------------------------------------------------------------------
_NEGATION_RULES: list[tuple[str, str, str]] = [
    ("prohibition_lifted", r"\bshall not\b", "shall"),
    ("punishment_negated", r"\bshall be punished with\b", "shall not be punished with"),
    ("power_negated", r"\bshall have\b", "shall not have"),
    ("obligation_negated_shall_be", r"\bshall be\b", "shall not be"),
    ("obligation_negated_shall", r"\bshall\b", "shall not"),
    ("permission_negated_may", r"\bmay\b", "may not"),
    ("entitlement_negated_is_entitled", r"\bis entitled\b", "is not entitled"),
    ("liability_negated_is_liable", r"\bis liable\b", "is not liable"),
    # Definition sections carry their operative content in the inclusion verb
    # rather than a modal, so flipping inclusion is the real contradiction.
    ("definition_inverted_includes", r"\bincludes\b", "excludes"),
    ("classification_negated_is_murder", r"\bis murder\b", "is not murder"),
]

# Applied only alongside punishment_negated, so a penalty clause is not left
# asserting the opposite direction of the sentence's main verb.
_SECONDARY_NEGATIONS: list[tuple[str, str, str]] = [
    ("secondary_fine_negated", r"\bshall also be liable to fine\b", "shall not be liable to any fine"),
]


def apply_negation(text: str) -> tuple[str, list[str]]:
    """Flip the operative modal. Returns (negated_text, fired_rule_names)."""
    for name, pattern, repl in _NEGATION_RULES:
        new, n = re.subn(pattern, repl, text, count=1)
        if n:
            fired = [name]
            if name == "punishment_negated":
                for sname, spattern, srepl in _SECONDARY_NEGATIONS:
                    new2, n2 = re.subn(spattern, srepl, new)
                    if n2:
                        fired.append(sname)
                        new = new2
            return new, fired
    # Last resort for texts with no operative modal or inclusion verb to flip
    # (omitted articles, pure definition stubs). Sentential negation is a real
    # contradiction and stays grammatical; it is tagged separately so its items
    # can be isolated in analysis rather than being mistaken for a lexical flip.
    if text:
        return f"It is not the case that {_lower_first(_strip_final_period(text))}.", ["sentential_negation_fallback"]
    return text, []


def cite(rec: EvidenceRecord) -> str:
    sub = f"({rec.subsection})" if rec.subsection else ""
    return f"{rec.provision_type} {rec.provision_number}{sub} of {rec.act}"


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _strip_final_period(text: str) -> str:
    return text[:-1] if text.endswith(".") else text


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _stable_id(key: str) -> str:
    """Content-addressed id. Python's hash() is salted per process (v1 used it),
    so ids changed on every run and the benchmark file was not reproducible."""
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def _pair_for_nei(records: list[EvidenceRecord], i: int) -> EvidenceRecord | None:
    """Pick a DIFFERENT provision to serve as a neutral hypothesis.

    Walks coprime strides so the pairing is deterministic and self-pairing is
    impossible, and rejects any candidate whose text overlaps this record's too
    much — a near-duplicate provision could be genuinely entailed or genuinely
    contradictory, which would make the NEI gold label wrong.
    """
    n = len(records)
    for stride in (17, 23, 29, 31, 37, 41, 43, 47, 53):
        cand = records[(i + stride) % n]
        if cand.dataset_citation_key == records[i].dataset_citation_key:
            continue
        if _jaccard(cand.canonical_text, records[i].canonical_text) < 0.35:
            return cand
    return None


def build_controlled_benchmark(records: list[EvidenceRecord]) -> tuple[list[dict], list[dict]]:
    """Returns (items, dropped) — `dropped` records every condition that could
    not be constructed and why, so coverage gaps are visible instead of silent."""
    items: list[dict] = []
    dropped: list[dict] = []

    for i, rec in enumerate(records):
        base = _stable_id(rec.dataset_citation_key)
        text = rec.canonical_text.strip()
        c = cite(rec)

        common = {
            "benchmark_tag": BENCHMARK_TAG,
            "benchmark_version": BENCHMARK_VERSION,
            "evidence_key": rec.dataset_citation_key,
            "evidence_text": text,
            "provision_type": rec.provision_type,
            "provision_number": rec.provision_number,
            "act_name": rec.act,
            "audit_verdict": rec.audit_verdict,
        }

        def emit(cond: str, hypothesis: str, label: str, rules: list[str],
                 attribution: bool, paraphrase: bool) -> None:
            items.append({
                "benchmark_id": f"cb_{base}_{cond}",
                **common,
                "condition": cond,
                "hypothesis": hypothesis,
                "expected_label": label,
                "construction_rules": rules,
                "factor_attribution": attribution,
                "factor_paraphrase": paraphrase,
            })

        # ---- ENTAILED 2x2 ------------------------------------------------
        emit("E1_verbatim", text, ENTAILED, ["verbatim_canonical"], False, False)
        emit("E2_verbatim_attributed", f"According to {c}, {_lower_first(text)}",
             ENTAILED, ["verbatim_canonical", "attribution_prefix"], True, False)

        para, para_rules = apply_paraphrase(text)
        if para_rules and para != text:
            emit("E3_paraphrase_bare", para, ENTAILED, para_rules, False, True)
            emit("E4_paraphrase_attributed", f"According to {c}, {_lower_first(para)}",
                 ENTAILED, para_rules + ["attribution_prefix"], True, True)
        else:
            dropped.append({
                "evidence_key": rec.dataset_citation_key,
                "conditions": ["E3_paraphrase_bare", "E4_paraphrase_attributed"],
                "reason": "no meaning-preserving paraphrase rule matched this text",
            })

        # ---- CONTRADICTED ------------------------------------------------
        neg, neg_rules = apply_negation(text)
        if neg_rules and neg != text:
            emit("C1_negated_bare", neg, CONTRADICTED, neg_rules, False, False)
            emit("C2_negated_attributed", f"According to {c}, {_lower_first(neg)}",
                 CONTRADICTED, neg_rules + ["attribution_prefix"], True, False)
        else:
            dropped.append({
                "evidence_key": rec.dataset_citation_key,
                "conditions": ["C1_negated_bare", "C2_negated_attributed"],
                "reason": "no operative modal available to negate grammatically",
            })

        # ---- NOT_ENOUGH_INFORMATION --------------------------------------
        other = _pair_for_nei(records, i)
        if other is not None:
            emit("N1_other_provision", other.canonical_text.strip(),
                 NOT_ENOUGH_INFORMATION,
                 [f"verbatim_canonical_of_other_provision:{other.dataset_citation_key}"],
                 False, False)
        else:
            dropped.append({
                "evidence_key": rec.dataset_citation_key,
                "conditions": ["N1_other_provision"],
                "reason": "no sufficiently dissimilar provision available for neutral pairing",
            })

        emit("N2_procedural_addition",
             f"{_strip_final_period(text)}, and the affected party must additionally file a "
             f"written notice with the appropriate authority within thirty days before this "
             f"provision may be invoked.",
             NOT_ENOUGH_INFORMATION, ["canonical_plus_extraneous_procedural_condition"],
             False, False)

    return items, dropped


def validate(items: list[dict]) -> list[str]:
    """Algorithmic checks that each hypothesis really is tied to canonical text
    and that no transformation produced a degenerate artifact. Any violation is
    a construction bug: the caller refuses to write the file."""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for it in items:
        bid, cond, hyp, ev = it["benchmark_id"], it["condition"], it["hypothesis"], it["evidence_text"]

        if bid in seen_ids:
            errors.append(f"{bid}: duplicate benchmark_id")
        seen_ids.add(bid)

        if re.search(r"\bnot not\b", hyp):
            errors.append(f"{bid}: double-negation artifact")
        if re.search(r"\b(\w+)s\b(?<=authoritys)", hyp):
            errors.append(f"{bid}: malformed pluralisation artifact")
        if not hyp.strip():
            errors.append(f"{bid}: empty hypothesis")

        # Hypotheses derived from THIS record's text must stay lexically anchored
        # to it. N1 is exempt by design: it is another provision's text.
        #
        # Measure the anchoring on the DERIVED RULE TEXT, with the attribution
        # prefix stripped. The prefix contributes ~10 tokens ("according to
        # section 302 of the indian penal code 1860") that are absent from the
        # evidence by construction, so scoring the raw hypothesis would penalise
        # an item purely for exhibiting the factor under test — and would do so
        # hardest on E4, the condition closest to real generated text.
        if cond != "N1_other_provision":
            rule_text = re.sub(r"^According to .*?, ", "", hyp) if it["factor_attribution"] else hyp
            tie = _jaccard(rule_text, ev)
            if tie < 0.35:
                errors.append(f"{bid}: hypothesis not lexically tied to canonical text "
                              f"(jaccard={tie:.2f})")

        if cond.startswith(("E3", "E4")) and hyp == ev:
            errors.append(f"{bid}: paraphrase identical to source")
        if cond.startswith("C") and _strip_final_period(hyp) == _strip_final_period(ev):
            errors.append(f"{bid}: contradiction identical to source")
        if cond == "N1_other_provision" and hyp == ev:
            errors.append(f"{bid}: neutral pairing selected the same provision")

        # The attribution factor must be observable in the text, and absent when
        # the item claims to be bare — otherwise the factorial is not measuring
        # what it says it measures.
        has_prefix = hyp.startswith("According to ")
        if it["factor_attribution"] != has_prefix:
            errors.append(f"{bid}: factor_attribution={it['factor_attribution']} "
                          f"but prefix present={has_prefix}")

    return errors


def main() -> int:
    repo_root = _PROTOTYPE_ROOT.parent.parent
    config_path = _PROTOTYPE_ROOT / "config" / "prototype.yaml"
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    _, usable = load_usable_evidence(
        repo_root / config["paths"]["canonical_statutes"],
        repo_root / config["paths"]["evidence_audit"],
        set(config["usable_evidence_verdicts"]),
    )
    # Stable ordering so the pairing stride and the file are reproducible
    # regardless of how the loader happened to order records.
    usable = sorted(usable, key=lambda r: r.dataset_citation_key)

    items, dropped = build_controlled_benchmark(usable)

    errors = validate(items)
    if errors:
        print(f"CONSTRUCTION VALIDATION FAILED ({len(errors)} errors):")
        for e in errors[:25]:
            print("  -", e)
        return 1

    out_path = _PROTOTYPE_ROOT / "outputs" / "controlled_verifier_benchmark.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    meta_path = _PROTOTYPE_ROOT / "outputs" / "controlled_verifier_benchmark_meta.json"
    by_cond: dict[str, int] = {}
    by_label: dict[str, int] = {}
    for it in items:
        by_cond[it["condition"]] = by_cond.get(it["condition"], 0) + 1
        by_label[it["expected_label"]] = by_label.get(it["expected_label"], 0) + 1

    meta = {
        "benchmark_tag": BENCHMARK_TAG,
        "benchmark_version": BENCHMARK_VERSION,
        "construction": "deterministic rule-based transformation of canonical statute text; no LLM used",
        "gold_label_source": "construction rule (never a model prediction)",
        "source_evidence_records": len(usable),
        "usable_evidence_verdicts": sorted(config["usable_evidence_verdicts"]),
        "total_items": len(items),
        "items_by_condition": by_cond,
        "items_by_expected_label": by_label,
        "dropped_conditions": dropped,
        "paraphrase_rules": [n for n, _, _ in _PARAPHRASE_RULES],
        "negation_rules": [n for n, _, _ in _NEGATION_RULES],
        "validation": f"passed ({len(items)} items, 0 errors)",
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Built {len(items)} controlled benchmark items from {len(usable)} evidence records.")
    print(f"  by condition: {json.dumps(by_cond, indent=2)}")
    print(f"  by label:     {json.dumps(by_label, indent=2)}")
    print(f"  dropped:      {len(dropped)}")
    for d in dropped:
        print(f"    - {d['evidence_key']}: {d['conditions']} ({d['reason']})")
    print(f"Wrote {out_path}")
    print(f"Wrote {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
