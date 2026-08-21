import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from helios.ranking.contracts import P5RankingRequest
from helios.ranking.engine import rank_candidates

FIXTURE = Path("data/fixtures/person4/person4-request.json")


def _request_dict() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_person4_fixture_runs_end_to_end() -> None:
    request = P5RankingRequest.model_validate(_request_dict())
    bundle = rank_candidates(request)

    assert bundle.contract_version == "person4.v1"
    assert len(bundle.ranked_candidates) == 5
    assert bundle.ranked_candidates[-1].candidate_id == "roof-d"
    assert bundle.ranked_candidates[-1].eligible is False
    assert bundle.ranked_candidates[-1].rank is None
    assert bundle.stability_report.iterations == 1000
    assert bundle.evaluation_report.status == "completed"
    assert bundle.evaluation_report.helios is not None
    assert bundle.evaluation_report.manual_baseline is not None
    assert {row.method for row in bundle.evaluation_report.baselines} == {
        "solar_only",
        "equal_weight_mcda",
        "balanced_nominal_mcda",
    }
    assert bundle.evaluation_report.helios.precision_at_k == 0.5
    assert bundle.evaluation_report.manual_baseline.precision_at_k == 0


def test_rank_acceptability_is_seed_reproducible() -> None:
    request = P5RankingRequest.model_validate(_request_dict())

    first = rank_candidates(request)
    second = rank_candidates(request)

    assert first.model_dump() == second.model_dump()


def test_lower_confidence_produces_more_score_uncertainty() -> None:
    bundle = rank_candidates(P5RankingRequest.model_validate(_request_dict()))
    stability = {row.candidate_id: row for row in bundle.stability_report.candidates}

    assert stability["roof-c"].score_std > stability["roof-a"].score_std
    assert stability["roof-c"].rank_p95 - stability["roof-c"].rank_p05 >= 1


def test_confidence_changes_uncertainty_not_nominal_utility() -> None:
    data = _request_dict()
    request = P5RankingRequest.model_validate(data)
    first = rank_candidates(request)
    first_score = next(
        row.nominal_score for row in first.ranked_candidates if row.candidate_id == "roof-a"
    )

    data["confidence_table"][0]["overall_confidence"] = 0.1
    data["confidence_table"][0]["criteria"] = {
        "generation": 0.1,
        "physical": 0.1,
        "grid": 0.1,
        "economics": 0.1,
    }
    second = rank_candidates(P5RankingRequest.model_validate(data))
    second_score = next(
        row.nominal_score for row in second.ranked_candidates if row.candidate_id == "roof-a"
    )

    assert first_score == second_score


def test_contract_rejects_candidate_set_mismatch() -> None:
    data = _request_dict()
    data["confidence_table"].pop()

    with pytest.raises(ValidationError, match="identical candidate IDs"):
        P5RankingRequest.model_validate(data)


def test_contract_rejects_assumption_version_drift() -> None:
    data = _request_dict()
    data["p3_table"][0]["assumption_version"] = "unreviewed-v2"

    with pytest.raises(ValidationError, match="assumption_version"):
        P5RankingRequest.model_validate(data)


def test_nominal_ties_break_by_candidate_id() -> None:
    data = _request_dict()
    data["ranking_mode"] = "nominal_mcda"
    data["robustness"]["feature_perturbation_at_zero_confidence"] = 0
    data["robustness"]["weight_relative_tolerance"] = 0
    data["p2_table"] = deepcopy(data["p2_table"][:2])
    data["p3_table"] = deepcopy(data["p3_table"][:2])
    data["confidence_table"] = deepcopy(data["confidence_table"][:2])
    data["scenario"]["top_k"] = 1
    data["validation"] = None
    for table_name in ("p2_table", "p3_table", "confidence_table"):
        first = data[table_name][0]
        second = data[table_name][1]
        second.update({key: value for key, value in first.items() if key != "candidate_id"})

    bundle = rank_candidates(P5RankingRequest.model_validate(data))

    assert [row.candidate_id for row in bundle.ranked_candidates] == ["roof-a", "roof-b"]


def test_explanations_are_traceable_and_non_generative() -> None:
    bundle = rank_candidates(P5RankingRequest.model_validate(_request_dict()))
    explanation = next(row for row in bundle.explanations if row.candidate_id == "roof-a")

    assert len(explanation.positive_reasons) == 2
    assert "probability_top_k" in explanation.trace
    assert "decision_status" in explanation.trace
