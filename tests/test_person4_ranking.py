import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from helios.ranking.contracts import ExclusionReason, P5RankingRequest, WeightPreset
from helios.ranking.engine import rank_candidates
from helios.ranking.features import (
    CRITERIA,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_SPECS,
    weight_profile_for,
)
from helios.ranking.reasons import exclusion_reason_catalog

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
    assert bundle.input_versions == {
        "feature_dictionary": FEATURE_DICTIONARY_VERSION,
        "p2_features": "p2-kharghar-v1",
        "p3_assumptions": "solar-economics-2026-08-v1",
        "confidence": "confidence-v1",
    }


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


@pytest.mark.parametrize(
    ("table", "version_field", "message"),
    [
        ("p2_table", "feature_version", "one feature_version"),
        ("confidence_table", "confidence_version", "one confidence_version"),
    ],
)
def test_contract_rejects_mixed_input_versions(
    table: str, version_field: str, message: str
) -> None:
    data = _request_dict()
    data[table][0][version_field] = "drift-v2"

    with pytest.raises(ValidationError, match=message):
        P5RankingRequest.model_validate(data)


def test_validation_requires_explicit_blinding_status() -> None:
    data = _request_dict()
    data["validation"]["labels"][0].pop("blinded")

    with pytest.raises(ValidationError, match="blinded"):
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
    assert "pareto_optimal" in explanation.trace


def test_available_hard_exclusions_are_applied_before_ranking() -> None:
    data = _request_dict()
    data["scenario"].update(
        {
            "minimum_usable_area_m2": 40,
            "maximum_grid_distance_m": 300,
            "minimum_shading_factor": 0.80,
            "budget_inr": 1_000_000,
        }
    )
    data["p2_table"][0]["geometry"] = {"type": "Polygon", "coordinates": [[]]}
    data["p3_table"][4]["estimated_cost_inr"] = None

    bundle = rank_candidates(P5RankingRequest.model_validate(data))
    by_id = {row.candidate_id: row for row in bundle.ranked_candidates}

    assert "invalid_exchange_geometry" in by_id["roof-a"].exclusion_reasons
    assert "grid_distance_above_screening_limit" in by_id["roof-b"].exclusion_reasons
    assert "grid_distance_above_screening_limit" in by_id["roof-c"].exclusion_reasons
    assert "usable_area_below_minimum" in by_id["roof-d"].exclusion_reasons
    assert {
        "shading_factor_below_minimum",
        "grid_distance_above_screening_limit",
        "estimated_cost_missing_for_budget_filter",
    }.issubset(by_id["roof-e"].exclusion_reasons)
    assert all(row.rank is None for row in bundle.ranked_candidates)


def test_missing_cost_can_be_allowed_when_budget_policy_disables_requirement() -> None:
    data = _request_dict()
    data["scenario"]["require_cost_when_budgeted"] = False

    bundle = rank_candidates(P5RankingRequest.model_validate(data))
    roof_e = next(row for row in bundle.ranked_candidates if row.candidate_id == "roof-e")

    assert "estimated_cost_missing_for_budget_filter" not in roof_e.exclusion_reasons
    assert roof_e.eligible is True


def test_pareto_status_uses_all_four_benefit_criteria() -> None:
    data = _request_dict()
    for table in ("p2_table", "p3_table", "confidence_table"):
        data[table] = deepcopy(data[table][:3])
    data["validation"] = None
    data["scenario"]["top_k"] = 2
    scores = {
        "roof-a": {"generation": 0.8, "physical": 0.8, "grid": 0.8, "economics": 0.8},
        "roof-b": {"generation": 0.7, "physical": 0.7, "grid": 0.7, "economics": 0.7},
        "roof-c": {"generation": 0.9, "physical": 0.6, "grid": 0.6, "economics": 0.6},
    }
    for row in data["p2_table"]:
        row["physical_score"] = scores[row["candidate_id"]]["physical"]
        row["grid_score"] = scores[row["candidate_id"]]["grid"]
    for row in data["p3_table"]:
        row["generation_score"] = scores[row["candidate_id"]]["generation"]
        row["economics_score"] = scores[row["candidate_id"]]["economics"]

    bundle = rank_candidates(P5RankingRequest.model_validate(data))
    pareto = {row.candidate_id: row.pareto_optimal for row in bundle.ranked_candidates}

    assert pareto == {"roof-a": True, "roof-b": False, "roof-c": True}


def test_feature_dictionary_and_named_presets_are_frozen() -> None:
    criterion_fields = {f"{criterion}_score" for criterion in CRITERIA}

    assert criterion_fields.issubset(FEATURE_SPECS)
    for preset in WeightPreset:
        profile = weight_profile_for(preset)
        assert sum(profile.model_dump().values()) == pytest.approx(1.0)
    assert weight_profile_for("energy_first").generation > weight_profile_for("balanced").generation
    assert weight_profile_for("cost_first").economics > weight_profile_for("balanced").economics


def test_threshold_boundaries_are_inclusive() -> None:
    data = _request_dict()
    for table in ("p2_table", "p3_table", "confidence_table"):
        data[table] = deepcopy(data[table][:1])
    data["validation"] = None
    data["scenario"] = {
        "name": "boundary-test",
        "minimum_usable_area_m2": data["p2_table"][0]["usable_area_m2"],
        "maximum_grid_distance_m": data["p2_table"][0]["grid_distance_m"],
        "minimum_shading_factor": data["p2_table"][0]["shading_factor"],
        "budget_inr": data["p3_table"][0]["estimated_cost_inr"],
        "top_k": 1,
    }

    bundle = rank_candidates(P5RankingRequest.model_validate(data))

    assert bundle.ranked_candidates[0].eligible is True
    assert bundle.ranked_candidates[0].rank == 1


def test_output_contract_rejects_inconsistent_ranks() -> None:
    bundle = rank_candidates(P5RankingRequest.model_validate(_request_dict()))
    output = bundle.model_dump(mode="json")
    output["ranked_candidates"][1]["rank"] = 1

    with pytest.raises(ValidationError, match="unique and contiguous"):
        type(bundle).model_validate(output)


def test_exclusion_reason_catalog_is_complete() -> None:
    catalog = exclusion_reason_catalog()

    assert set(catalog) == {reason.value for reason in ExclusionReason}
    assert all(description.endswith(".") for description in catalog.values())
