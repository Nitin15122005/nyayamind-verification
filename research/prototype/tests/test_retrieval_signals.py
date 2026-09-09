"""
Tests for src/retrieval_signals.py (BM25 / embedding act-name scoring) and
its wiring into evidence_matcher.match_evidence() via `fuzzy_method`.

Safety-critical property under test: regardless of which fuzzy_method is
selected, a claim can NEVER match evidence under a different
(provision_type, provision_number) than it cited, and NEVER match evidence
whose Act states an explicit, disjoint year from the claim's own citation.
These gates are structural (candidates are filtered before any
bm25/embedding score is even computed) — the tests here confirm that
structural guarantee holds for the new code paths too, not just jaccard.
"""
from pathlib import Path

import pytest

from src.claim_parser import ExtractedCitation, normalize_act
from src.data_loader import EvidenceRecord
from src.evidence_matcher import match_evidence

pytest.importorskip("rank_bm25")
pytest.importorskip("sentence_transformers")

from src.retrieval_signals import (  # noqa: E402
    Bm25ActIndex,
    EmbeddingActIndex,
    best_match_among,
    suggest_candidates_bm25,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CANONICAL_PATH = REPO_ROOT / "research/data/evidence/canonical_statutes.jsonl"
AUDIT_PATH = REPO_ROOT / "research/data/evidence/evidence_audit.jsonl"


def _mk_record(act_raw: str, provision_type: str, provision_number: str) -> EvidenceRecord:
    return EvidenceRecord(
        dataset_citation_key=f"{provision_type}_{provision_number}_{act_raw}",
        act=act_raw,
        provision_type=provision_type,
        provision_number=provision_number,
        subsection=None,
        canonical_text="irrelevant text for these tests",
        source_url="https://example.invalid",
        audit_verdict="VERIFIED_EXACT",
        act_norm=normalize_act(act_raw),
    )


@pytest.fixture
def confusable_pool() -> list[EvidenceRecord]:
    """Deliberately adversarial: two Acts sharing the same provision number
    with very similar names, exactly the shape a wrong-Act bug would slip
    through on. Includes several unrelated decoy acts so BM25's IDF
    statistics aren't computed over a degenerate 2-document corpus (a
    term appearing in 100% of a tiny corpus gets a near-zero/negative BM25
    IDF weight, which is a real BM25 property but not representative of
    the real ~22-act corpus this index is actually built over in
    production -- see Bm25ActIndex, which always indexes ALL unique acts
    in the usable evidence pool, never just a query's own candidate set)."""
    return [
        _mk_record("The Code of Civil Procedure, 1908", "Section", "100"),
        _mk_record("The Code of Criminal Procedure, 1973", "Section", "100"),
        _mk_record("The Indian Penal Code, 1860", "Section", "302"),
        _mk_record("The Indian Evidence Act, 1872", "Section", "25"),
        _mk_record("The Arbitration Act, 1940", "Section", "34"),
        _mk_record("The Arbitration and Conciliation Act, 1996", "Section", "34"),
        _mk_record("The Prevention of Corruption Act, 1988", "Section", "7"),
    ]


class TestBm25ActIndex:
    def test_exact_name_scores_highest(self, confusable_pool):
        index = Bm25ActIndex(confusable_pool)
        scores = index.score_all(normalize_act("The Code of Civil Procedure, 1908"))
        civil = normalize_act("The Code of Civil Procedure, 1908")
        criminal = normalize_act("The Code of Criminal Procedure, 1973")
        assert scores[civil] > scores[criminal]

    def test_civil_vs_criminal_disambiguation_on_small_fixture(self, confusable_pool):
        # NOTE: this small (7-act) fixture does NOT reproduce the wrong-accept
        # failure measured on the real 22-act corpus (see
        # TestRealCorpusSafety below and
        # outputs/retrieval_signal_benchmark_report.md) -- BM25's IDF
        # statistics are corpus-composition-dependent, so a small synthetic
        # pool is not a reliable stand-in for the real safety check. This
        # test only guards against a regression on THIS fixture; it is not
        # evidence that bm25 is safe in production.
        index = Bm25ActIndex(confusable_pool)
        candidates = [r for r in confusable_pool if r.provision_number == "100"]
        result = best_match_among(normalize_act("Criminal Procedure Code"), candidates, index, "bm25")
        assert result.evidence.act_norm == normalize_act("The Code of Criminal Procedure, 1973")

    def test_wrong_provision_number_never_in_candidate_pool(self, confusable_pool):
        # best_match_among only ever sees candidates the CALLER already
        # filtered by provision_number -- confirm a caller who (correctly)
        # filters to provision_number=100 never receives a provision_number
        # != 100 record even if it scored higher lexically.
        other_number = _mk_record("The Code of Civil Procedure, 1908", "Section", "151")
        index = Bm25ActIndex(confusable_pool + [other_number])
        candidates = [r for r in confusable_pool if r.provision_number == "100"]
        result = best_match_among(normalize_act("Civil Procedure Code"), candidates, index, "bm25")
        assert result.evidence.provision_number == "100"


class TestEmbeddingActIndex:
    def test_exact_name_scores_highest(self, confusable_pool):
        index = EmbeddingActIndex(confusable_pool)
        scores = index.score_all(normalize_act("The Code of Civil Procedure, 1908"))
        civil = normalize_act("The Code of Civil Procedure, 1908")
        criminal = normalize_act("The Code of Criminal Procedure, 1973")
        assert scores[civil] >= scores[criminal]

    def test_civil_vs_criminal_never_wrong_accepted_at_production_threshold(self, confusable_pool):
        """The single most realistic wrong-Act trap in the real corpus
        (Civil Procedure vs Criminal Procedure Code, same provision number
        space). A claim explicitly citing "Criminal Procedure Code" must
        never resolve to the Civil Procedure evidence record."""
        index = EmbeddingActIndex(confusable_pool)
        candidates = [r for r in confusable_pool if r.provision_number == "100"]
        result = best_match_among(normalize_act("Criminal Procedure Code"), candidates, index, "embedding")
        assert result.evidence.act_norm == normalize_act("The Code of Criminal Procedure, 1973")


class TestMatchEvidenceFuzzyMethodDispatch:
    def test_bm25_dispatch_requires_index(self, confusable_pool):
        citation = ExtractedCitation(
            provision_type="Section", provision_number="100", subsection=None,
            act_raw="Civil Procedure Code", act_norm=normalize_act("Civil Procedure Code"),
        )
        exact_index = {}
        with pytest.raises(ValueError):
            match_evidence(citation, exact_index, confusable_pool, fuzzy_method="bm25", fuzzy_act_index=None)

    def test_bm25_dispatch_matches_correct_act(self, confusable_pool):
        index = Bm25ActIndex(confusable_pool)
        citation = ExtractedCitation(
            provision_type="Section", provision_number="100", subsection=None,
            act_raw="Civil Procedure Code", act_norm=normalize_act("Civil Procedure Code"),
        )
        exact_index = {}
        result = match_evidence(
            citation, exact_index, confusable_pool,
            fuzzy_method="bm25", fuzzy_act_index=index, fuzzy_bm25_threshold=0.5,
        )
        assert result.matched is True
        assert result.evidence.act_norm == normalize_act("The Code of Civil Procedure, 1908")

    def test_embedding_dispatch_never_cross_matches_civil_and_criminal(self, confusable_pool):
        index = EmbeddingActIndex(confusable_pool)
        citation = ExtractedCitation(
            provision_type="Section", provision_number="100", subsection=None,
            act_raw="Criminal Procedure Code", act_norm=normalize_act("Criminal Procedure Code"),
        )
        exact_index = {}
        result = match_evidence(
            citation, exact_index, confusable_pool,
            fuzzy_method="embedding", fuzzy_act_index=index, fuzzy_embedding_threshold=0.55,
        )
        if result.matched:
            assert result.evidence.act_norm == normalize_act("The Code of Criminal Procedure, 1973")

    def test_jaccard_remains_default_and_unaffected_by_new_params(self, confusable_pool):
        citation = ExtractedCitation(
            provision_type="Section", provision_number="100", subsection=None,
            act_raw="Civil Procedure Code", act_norm=normalize_act("Civil Procedure Code"),
        )
        exact_index = {}
        result = match_evidence(citation, exact_index, confusable_pool)
        assert result.matched is True
        assert result.match_method == "fuzzy"
        assert result.evidence.act_norm == normalize_act("The Code of Civil Procedure, 1908")

    def test_unknown_fuzzy_method_raises(self, confusable_pool):
        citation = ExtractedCitation(
            provision_type="Section", provision_number="100", subsection=None,
            act_raw="Civil Procedure Code", act_norm=normalize_act("Civil Procedure Code"),
        )
        with pytest.raises(ValueError):
            match_evidence(citation, {}, confusable_pool, fuzzy_method="not_a_real_method")


@pytest.mark.skipif(not CANONICAL_PATH.exists(), reason="real evidence corpus not present in this checkout")
class TestRealCorpusSafety:
    """Real-data safety net: build the actual production indexes over the
    real 136-record evidence pool and confirm bm25/embedding never
    wrong-accept the corpus's known confusable Act pairs (mirrors
    scripts/benchmark_retrieval_signals.py's should-NOT-match cases, kept
    here as a fast pytest regression rather than relying solely on the
    standalone benchmark script being run)."""

    @pytest.fixture(scope="class")
    def real_pool(self):
        # Load with the v1 supplement, matching production
        # (config/prototype.yaml's use_evidence_v1: true) -- this is the
        # actual 136-record pool the benchmark script measured against.
        from src.data_loader import load_usable_evidence
        canonical_v1 = REPO_ROOT / "research/data/evidence/canonical_statutes_v1.jsonl"
        audit_v1 = REPO_ROOT / "research/data/evidence/evidence_audit_v1.jsonl"
        extra = {}
        if canonical_v1.exists() and audit_v1.exists():
            extra = {"extra_canonical_path": canonical_v1, "extra_audit_path": audit_v1}
        _, all_usable = load_usable_evidence(
            CANONICAL_PATH, AUDIT_PATH, {"VERIFIED_EXACT", "VERIFIED_CONTENT"}, **extra,
        )
        return all_usable

    def test_jaccard_is_the_only_fully_safe_method_at_production_thresholds(self, real_pool):
        """Authoritative safety regression, using the EXACT same
        candidate-pool-construction and pre-registered adversarial cases as
        scripts/benchmark_retrieval_signals.py (imported directly, not
        reimplemented, so the two can never silently drift apart). This
        replaces an earlier version of this test that built an unrealistic
        2-candidates-sharing-a-provision-number scenario -- that never
        actually occurs in this corpus (no duplicate (act,
        provision_number) pairs exist) and passed vacuously without
        exercising the real single-candidate absolute-threshold decision
        match_evidence() actually makes.

        Confirms the measured, current state of the world (see
        outputs/retrieval_signal_benchmark_report.md for the full
        threshold-sweep analysis this asserts a snapshot of): jaccard is
        the only one of the three methods with ZERO wrong-Act matches at
        its production threshold. bm25 and embedding are NOT currently
        safe at their evaluated thresholds -- this is documented,
        known, and exactly why config/prototype.yaml keeps
        fuzzy_method: "jaccard" as the production default.
        """
        import sys
        sys.path.insert(0, str(REPO_ROOT / "research" / "prototype" / "scripts"))
        from benchmark_retrieval_signals import evaluate_all, SHOULD_MATCH, SHOULD_NOT_MATCH

        from src.retrieval_signals import EmbeddingActIndex

        bm25_index = Bm25ActIndex(real_pool)
        embedding_index = EmbeddingActIndex(real_pool)
        thresholds = {"jaccard": 0.8, "bm25": 0.5, "embedding": 0.55}
        results = evaluate_all(
            ["jaccard", "bm25", "embedding"], real_pool, thresholds,
            indexes={"bm25": bm25_index, "embedding": embedding_index},
        )

        def correct_reject_rate(method):
            sn = [r for r in results if r["method"] == method and r["kind"] == "should_not_match"]
            if not sn:
                pytest.skip("no should_not_match cases resolvable against this checkout's corpus")
            return sum(1 for r in sn if r["correct"]) / len(sn)

        assert correct_reject_rate("jaccard") == 1.0, (
            "jaccard must remain 100% safe (zero wrong-Act matches) -- any regression here "
            "is a real safety bug, not a known/accepted limitation."
        )
        # Documented, known, NOT a passing safety property -- asserted here
        # (rather than silently ignored) so a change that improves either
        # method gets noticed and considered for promotion, and so nobody
        # mistakes their absence from this test as "presumed safe".
        assert correct_reject_rate("bm25") < 1.0
        assert correct_reject_rate("embedding") < 1.0

    def test_suggest_candidates_bm25_is_diagnostic_only_never_raises(self, real_pool):
        index = Bm25ActIndex(real_pool)
        out = suggest_candidates_bm25(normalize_act("Evidence Act"), real_pool, index, top_k=3)
        assert isinstance(out, list)
        assert len(out) <= 3
