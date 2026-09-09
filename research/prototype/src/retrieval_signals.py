"""
Additive, opt-in retrieval SIGNAL layer for scoring candidate Act names
within evidence_matcher's existing fuzzy fallback path.

IMPORTANT SAFETY INVARIANT: this module never establishes legal evidence on
its own. It only supplies an alternative similarity SCORE for act-name
matching; evidence_matcher.match_evidence() still requires an exact
(provision_type, provision_number) match and applies the year-conflict veto
before any score from this module is even consulted. Semantic/lexical
similarity can raise or lower a match's confidence -- it can never override
citation identity. See evidence_matcher.py's module docstring and
match_evidence()'s `fuzzy_method` parameter.

This module also exposes suggest_candidates_*() functions used ONLY for
NO_EVIDENCE diagnostics (human review / audit_no_evidence_taxonomy) -- their
output is never consumed by the verifier and never auto-assigns evidence.

Two backends, both optional at import time (ImportError deferred to first
use, so the rest of the codebase works with neither installed):
  - "bm25": rank_bm25.BM25Okapi over the same act_significant_words()
    token bags claim_parser.py/evidence_matcher.py already use for Jaccard
    -- this changes only the SCORING function, not the vocabulary.
  - "embedding": sentence-transformers cosine similarity over raw act
    strings. Default model sentence-transformers/all-MiniLM-L6-v2 (22M
    params, ~90MB, CPU-friendly, general-purpose -- not legal-domain-tuned,
    but the corpus here is 22 unique, mostly-lexically-distinct Act names,
    where a small general model is adequate; see
    outputs/retrieval_signal_benchmark_report.md for the measured
    comparison against bm25/jaccard before choosing this default).

Both indexes are built once from the in-memory `all_usable` evidence list
already loaded by data_loader and cached for the process lifetime; nothing
is persisted to disk (rebuilding is near-instant at this corpus size --
tens of milliseconds for BM25, well under a second for embeddings on CPU).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .claim_parser import act_significant_words
from .data_loader import EvidenceRecord

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - exercised only when rank_bm25 absent
    BM25Okapi = None

try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers import util as _st_util
except ImportError:  # pragma: no cover - exercised only when sentence-transformers absent
    SentenceTransformer = None
    _st_util = None

DEFAULT_EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


class Bm25ActIndex:
    """BM25 index over the UNIQUE act_norm strings present in the usable
    evidence pool (not one entry per evidence record -- act names repeat
    across many provision numbers, and BM25's IDF statistics should reflect
    the vocabulary of distinct Acts, not be skewed by how many sections a
    given Act happens to have in the corpus)."""

    def __init__(self, all_usable: list[EvidenceRecord]):
        if BM25Okapi is None:
            raise ImportError(
                "rank_bm25 is not installed; pip install rank_bm25 to use fuzzy_method='bm25'"
            )
        self.unique_acts: list[str] = sorted({ev.act_norm for ev in all_usable})
        corpus_tokens = [sorted(act_significant_words(a)) for a in self.unique_acts]
        self._bm25 = BM25Okapi(corpus_tokens) if corpus_tokens else None

    def score_all(self, query_act_norm: str) -> dict[str, float]:
        """{act_norm: raw BM25 score} for every unique act in the pool.
        Higher is more similar; scale is corpus- and query-dependent (BM25
        scores are not bounded to [0, 1] and are only meaningful compared
        to each other for the SAME query)."""
        if self._bm25 is None:
            return {}
        query_tokens = sorted(act_significant_words(query_act_norm))
        if not query_tokens:
            return {a: 0.0 for a in self.unique_acts}
        raw_scores = self._bm25.get_scores(query_tokens)
        return dict(zip(self.unique_acts, raw_scores))


class EmbeddingActIndex:
    """Sentence-embedding cosine-similarity index over the unique act_norm
    strings in the usable evidence pool. Loads the model lazily (first call
    to score_all(), not __init__()) so constructing this object never
    triggers a model download/load until it's actually used."""

    def __init__(self, all_usable: list[EvidenceRecord], model_id: str = DEFAULT_EMBEDDING_MODEL_ID):
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers is not installed; "
                "pip install sentence-transformers to use fuzzy_method='embedding'"
            )
        self.unique_acts: list[str] = sorted({ev.act_norm for ev in all_usable})
        self.model_id = model_id
        self._model: Optional["SentenceTransformer"] = None
        self._corpus_embeddings = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(self.model_id, device="cpu")
            self._corpus_embeddings = (
                self._model.encode(self.unique_acts, convert_to_tensor=True, normalize_embeddings=True)
                if self.unique_acts
                else None
            )

    def score_all(self, query_act_norm: str) -> dict[str, float]:
        """{act_norm: cosine similarity in [-1, 1]} for every unique act."""
        self._ensure_loaded()
        if self._corpus_embeddings is None or not query_act_norm:
            return {a: 0.0 for a in self.unique_acts}
        query_emb = self._model.encode([query_act_norm], convert_to_tensor=True, normalize_embeddings=True)
        sims = _st_util.cos_sim(query_emb, self._corpus_embeddings)[0].tolist()
        return dict(zip(self.unique_acts, sims))


@dataclass
class ScoredMatch:
    evidence: Optional[EvidenceRecord]
    score: float  # method-specific normalization; never compared across methods
    method: str  # "bm25" | "embedding"


def best_match_among(
    query_act_norm: str,
    candidates: list[EvidenceRecord],
    index: "Bm25ActIndex | EmbeddingActIndex",
    method: str,
) -> ScoredMatch:
    """Given `candidates` already filtered by the caller to share
    provision_type + provision_number and to have passed the year-conflict
    veto (this function does NOT re-check legal identity -- that gate lives
    in evidence_matcher.match_evidence() and stays there), return the
    single best-scoring candidate.

    Score normalization -- deliberately NOT relative to the other
    candidates in this call (min-max-within-candidate-set was tried first
    and measured UNSAFE: with only one or two real candidates -- the norm
    at this corpus's size, since no duplicate (act, provision_number) pairs
    exist -- min-max normalization always maps the best of 1-2 candidates
    to a near-1.0 score regardless of its ABSOLUTE similarity to the query,
    so a threshold check against it can never reject a genuinely wrong Act;
    see outputs/retrieval_signal_benchmark_report.md's first run, which
    caught this as a 0% safety / 9-wrong-accept result before this fix):
      - "bm25": each candidate's raw score is divided by that SAME
        candidate's own self-score (index.score_all(candidate.act_norm) at
        candidate.act_norm) -- i.e. "what fraction of a perfect match to
        this candidate's own name did the query achieve", an absolute,
        per-candidate quality measure independent of what else happens to
        be in the candidate pool for this particular claim.
      - "embedding": raw cosine similarity, already an absolute, bounded
        [-1, 1] measure independent of the candidate pool -- unchanged.
    """
    if not candidates:
        return ScoredMatch(evidence=None, score=0.0, method=method)

    all_scores = index.score_all(query_act_norm)
    cand_scores = [(ev, all_scores.get(ev.act_norm, 0.0)) for ev in candidates]

    if method == "embedding":
        best_ev, best_raw = max(cand_scores, key=lambda t: t[1])
        return ScoredMatch(evidence=best_ev, score=best_raw, method=method)

    # bm25: normalize each candidate's score against its OWN self-score
    # (absolute, per-candidate -- never relative to sibling candidates).
    normalized = []
    for ev, raw in cand_scores:
        self_scores = index.score_all(ev.act_norm)
        self_score = self_scores.get(ev.act_norm, 0.0)
        norm = (raw / self_score) if self_score > 0 else 0.0
        normalized.append((ev, min(norm, 1.0)))
    best_ev, best_norm = max(normalized, key=lambda t: t[1])
    return ScoredMatch(evidence=best_ev, score=best_norm, method=method)


def suggest_candidates_bm25(
    query_act_norm: str,
    all_usable: list[EvidenceRecord],
    index: Bm25ActIndex,
    top_k: int = 5,
) -> list[tuple[EvidenceRecord, float]]:
    """DIAGNOSTIC ONLY -- for NO_EVIDENCE review / audit_no_evidence_taxonomy.
    Returns up to top_k evidence records (any provision_number) whose Act
    name is lexically closest to `query_act_norm`, for a human reviewer to
    look at. Never called by match_evidence() or apply_verification();
    never auto-assigns evidence to a claim."""
    all_scores = index.score_all(query_act_norm)
    ranked_acts = sorted(all_scores.items(), key=lambda t: t[1], reverse=True)[:top_k]
    act_rank = {act: i for i, (act, _) in enumerate(ranked_acts)}
    out = [
        (ev, all_scores.get(ev.act_norm, 0.0))
        for ev in all_usable
        if ev.act_norm in act_rank
    ]
    out.sort(key=lambda t: act_rank[t[0].act_norm])
    return out[:top_k]


def suggest_candidates_embedding(
    query_act_norm: str,
    all_usable: list[EvidenceRecord],
    index: EmbeddingActIndex,
    top_k: int = 5,
) -> list[tuple[EvidenceRecord, float]]:
    """DIAGNOSTIC ONLY -- see suggest_candidates_bm25()'s docstring; same
    contract, embedding backend."""
    all_scores = index.score_all(query_act_norm)
    ranked_acts = sorted(all_scores.items(), key=lambda t: t[1], reverse=True)[:top_k]
    act_rank = {act: i for i, (act, _) in enumerate(ranked_acts)}
    out = [
        (ev, all_scores.get(ev.act_norm, 0.0))
        for ev in all_usable
        if ev.act_norm in act_rank
    ]
    out.sort(key=lambda t: act_rank[t[0].act_norm])
    return out[:top_k]
