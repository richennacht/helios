import json
from pathlib import Path

from helios.ranking.contracts import DecisionStatus, P5RankingRequest, RankingMode
from helios.ranking.engine import rank_candidates
from helios.ranking.ml_fuzzy_scheduler import (
    TriangularFuzzyNumber,
    rank_candidates_fuzzy_ml,
)

FIXTURE = Path("data/fixtures/person4/person4-request.json")


def _request_dict() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_triangular_fuzzy_number_operations() -> None:
    tfn1 = TriangularFuzzyNumber(0.2, 0.5, 0.8)
    tfn2 = TriangularFuzzyNumber(0.1, 0.3, 0.6)

    # GMIR defuzzification test: (l + 4m + u) / 6
    assert abs(tfn1.defuzzify() - (0.2 + 2.0 + 0.8) / 6.0) < 1e-5

    # Alpha cut interval at alpha=0.5
    low, high = tfn1.alpha_cut(0.5)
    assert abs(low - 0.35) < 1e-5
    assert abs(high - 0.65) < 1e-5

    # Fuzzy addition
    added = tfn1.add(tfn2)
    assert abs(added.l - 0.3) < 1e-5
    assert abs(added.m - 0.8) < 1e-5
    assert abs(added.u - 1.4) < 1e-5

    # Fuzzy scaling
    scaled = tfn1.scale(2.0)
    assert abs(scaled.l - 0.4) < 1e-5
    assert abs(scaled.m - 1.0) < 1e-5
    assert abs(scaled.u - 1.6) < 1e-5


def test_fuzzy_ml_scheduler_pipeline_integration() -> None:
    req_dict = _request_dict()
    req_dict["ranking_mode"] = RankingMode.FUZZY_ML_CHALLENGER
    request = P5RankingRequest.model_validate(req_dict)

    bundle = rank_candidates(request)

    assert bundle.ranking_mode == RankingMode.FUZZY_ML_CHALLENGER
    assert len(bundle.ranked_candidates) > 0

    # Verify candidate priority ranking & contributions
    top_candidate = bundle.ranked_candidates[0]
    assert top_candidate.nominal_rank == 1
    assert top_candidate.nominal_score is not None
    assert top_candidate.nominal_score > 0.0

    # Verify explanations contain fuzzy schedule metrics in trace
    top_explanation = next(
        e for e in bundle.explanations if e.candidate_id == top_candidate.candidate_id
    )
    assert "fuzzy_schedule_duration_days" in top_explanation.trace
    assert "Fuzzy ML Scheduler" in str(top_explanation.trace["summary"])

    # Verify excluded candidate is preserved
    excluded_candidate = next(c for c in bundle.ranked_candidates if not c.eligible)
    assert excluded_candidate.rank is None
    assert excluded_candidate.decision_status == DecisionStatus.EXCLUDED


def test_fuzzy_ml_scheduler_reproducibility() -> None:
    req_dict = _request_dict()
    req_dict["ranking_mode"] = RankingMode.FUZZY_ML_CHALLENGER
    request = P5RankingRequest.model_validate(req_dict)

    bundle_1 = rank_candidates_fuzzy_ml(request)
    bundle_2 = rank_candidates_fuzzy_ml(request)

    assert bundle_1.model_dump() == bundle_2.model_dump()
