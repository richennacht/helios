from scripts.geo.merge_building_datasets import fuse_height_observations, merge_collections


def _feature(height, coordinates, **properties):
    return {
        "type": "Feature",
        "properties": {"height_m": height, **properties},
        "geometry": {"type": "Polygon", "coordinates": [coordinates]},
    }


SQUARE = [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]


def test_averages_heights_when_both_sources_have_data():
    osm = {"features": [_feature(10, SQUARE)]}
    google = {
        "features": [
            _feature(None, SQUARE, source_centroid_lon=1, source_centroid_lat=1, temporal_height_m=20)
        ]
    }
    result = merge_collections(osm, google)
    properties = result["features"][0]["properties"]
    assert properties["height_m"] == 15
    assert properties["osm_height_m"] == 10
    assert properties["google_temporal_height_m"] == 20


def test_uses_only_available_height_and_never_invents_a_fallback():
    osm = {"features": [_feature(None, SQUARE)]}
    google = {
        "features": [
            _feature(None, SQUARE, source_centroid_lon=1, source_centroid_lat=1, temporal_height_m=12)
        ]
    }
    result = merge_collections(osm, google)
    assert result["features"][0]["properties"]["height_m"] == 12
    assert result["metadata"]["synthetic_height_fallback"] is False


def test_keeps_missing_height_null_when_no_source_has_data():
    result = merge_collections({"features": [_feature(None, SQUARE)]}, {"features": []})
    assert result["features"][0]["properties"]["height_m"] is None


def test_discards_legacy_synthetic_osm_fallback():
    osm = {
        "features": [
            _feature(6, SQUARE, height_source="display fallback; OSM height unavailable")
        ]
    }
    result = merge_collections(osm, {"features": []})
    properties = result["features"][0]["properties"]
    assert properties["osm_height_m"] is None
    assert properties["height_m"] is None


def test_generic_height_fusion_averages_all_independent_available_sources():
    height, sources = fuse_height_observations(
        [
            {
                "source_id": "google-2023",
                "height_m": 12,
                "year": 2023,
                "independence_group": "google",
            },
            {"source_id": "microsoft", "height_m": None},
            {"source_id": "overture", "height_m": 18},
            {
                "source_id": "fused-copy-of-google",
                "height_m": 30,
                "independence_group": "google",
            },
            {"source_id": "google-copy", "height_m": 10, "independence_group": "google"},
            {"source_id": "google-2022", "height_m": 100, "year": 2022},
        ],
        reference_year=2023,
    )
    assert height == 15
    assert sources == ["google-2023", "overture"]
