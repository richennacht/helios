import json
from pathlib import Path

PROFILE_PATH = (
    Path(__file__).parents[1]
    / "apps"
    / "geolibre"
    / "experimental"
    / "kharghar-3d"
    / "data"
    / "government_economic_profiles.json"
)


def _profiles() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_kharghar_has_a_provenance_complete_government_profile() -> None:
    payload = _profiles()
    profile = payload["profiles"][0]
    west, south, east, north = profile["coverage_bbox"]

    assert payload["schema_version"] == "helios.government-economic-profile.v1"
    assert payload["currency"] == "INR"
    assert west <= 73.0697 <= east
    assert south <= 19.0468 <= north
    for dataset in (profile["capex"], profile["energy_value"]):
        assert dataset["source_agency"]
        assert dataset["source_document"]
        assert dataset["source_date"]
        assert dataset["source_url"].startswith("https://")
        assert 0 < dataset["confidence"] <= 1


def test_mnre_and_cea_capacity_bands_are_explicit_and_ordered() -> None:
    profile = _profiles()["profiles"][0]

    assert [band["value"] for band in profile["capex"]["bands"]] == [54, 48, 45]
    assert [band["value"] for band in profile["energy_value"]["bands"]] == [
        9.69,
        14.18,
        16.55,
    ]
    for dataset in (profile["capex"], profile["energy_value"]):
        minimums = [band["min_kw_exclusive"] for band in dataset["bands"]]
        assert minimums == sorted(minimums)


def test_viewer_exposes_discounted_cashflow_economic_ranking() -> None:
    viewer = PROFILE_PATH.parent.parent.joinpath("index.html").read_text(encoding="utf-8")

    assert "Run economic ranking analysis" in viewer
    assert "discountedNetCashflow" in viewer
    assert "profitabilityIndex" in viewer
    assert "degradationPct" in viewer
    assert "data-economic-index" in viewer
    assert "focusRankingBuilding(row.feature, button)" in viewer
