from helios.pipeline.multimodal import rank_selected_aoi
from helios.ranking.contracts import P5RankingRequest


def test_multimodal_aoi_filters_p2_p3_and_confidence_before_person4():
    request = P5RankingRequest.model_validate(
        {
            "feature_dictionary_version": "person4.features-v1",
            "request_id": "aoi-test",
            "assumption_version": "mvp-1",
            "scenario": {"top_k": 2},
            "p2_table": [
                {"candidate_id": "inside", "geometry": {"type": "Polygon", "coordinates": [[[1,1],[2,1],[2,2],[1,1]]]}, "usable_area_m2": 100, "shading_factor": .9, "grid_distance_m": 100, "physical_score": .9, "grid_score": .9, "feature_version": "p2-v1"},
                {"candidate_id": "outside", "geometry": {"type": "Polygon", "coordinates": [[[3,3],[4,3],[4,4],[3,3]]]}, "usable_area_m2": 100, "shading_factor": .9, "grid_distance_m": 100, "physical_score": .9, "grid_score": .9, "feature_version": "p2-v1"},
            ],
            "p3_table": [{"candidate_id": x, "annual_yield_kwh": 1000, "estimated_cost_inr": 100000, "generation_score": .8, "economics_score": .8, "assumption_version": "mvp-1"} for x in ("inside", "outside")],
            "confidence_table": [{"candidate_id": x, "overall_confidence": .8, "criteria": {"generation": .8, "physical": .8, "grid": .8, "economics": .8}, "confidence_version": "c-v1"} for x in ("inside", "outside")],
        }
    )
    bundle = rank_selected_aoi(request, {"type": "Polygon", "coordinates": [[[0,0],[2.5,0],[2.5,2.5],[0,2.5],[0,0]]]})
    assert [row.candidate_id for row in bundle.ranked_candidates] == ["inside"]
