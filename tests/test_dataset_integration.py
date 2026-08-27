"""
Pytest Suite for HELIOS Dataset Integration
===========================================
Tests loading and end-to-end solar layout optimization on real building candidates
from the HELIOS repository dataset.
"""

import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from shapely.geometry import Polygon

from helios_dataset import (
    BuildingCandidate,
    BuildingPVResult,
    HeliosDataLoader,
    latlon_to_local_meters,
    local_meters_to_latlon,
    optimize_all_candidates,
    optimize_building_pv,
)
from layout_optimizer import ConstraintRules, PanelSpec


@pytest.fixture
def data_loader():
    return HeliosDataLoader(base_data_dir="data")


class TestDatasetLoaders:
    """Verify that all datasets from the repo load correctly."""

    def test_load_candidate_buildings(self, data_loader):
        candidates = data_loader.load_candidate_buildings()
        assert len(candidates) > 0
        first = candidates[0]
        assert isinstance(first, BuildingCandidate)
        assert first.candidate_id != ""
        assert isinstance(first.geometry_wgs84, Polygon)
        assert first.footprint_area_m2 > 0

    def test_load_kharghar_aoi(self, data_loader):
        aoi = data_loader.load_kharghar_aoi()
        assert isinstance(aoi, Polygon)
        assert aoi.is_valid

    def test_load_solar_economics_assumptions(self, data_loader):
        assumptions = data_loader.load_solar_economics_assumptions()
        assert "input" in assumptions or "assumption_version" in assumptions

    def test_load_person4_fixture(self, data_loader):
        p4 = data_loader.load_person4_request_fixture()
        assert p4["contract_version"] == "person4.v1"
        assert len(p4["p2_table"]) > 0


class TestCoordinateTransforms:
    """Verify local projection accuracy and reversible transforms."""

    def test_roundtrip_latlon_to_meters(self):
        ref_lon, ref_lat = 73.0653, 19.0425
        target_lon, target_lat = 73.0660, 19.0430

        x_m, y_m = latlon_to_local_meters(target_lon, target_lat, ref_lon, ref_lat)
        assert abs(x_m) > 0
        assert abs(y_m) > 0

        roundtrip_lon, roundtrip_lat = local_meters_to_latlon(x_m, y_m, ref_lon, ref_lat)
        assert pytest.approx(target_lon, rel=1e-7) == roundtrip_lon
        assert pytest.approx(target_lat, rel=1e-7) == roundtrip_lat


class TestRealCandidateOptimization:
    """Verify PV layout packing and yield calculations on real Kharghar candidates."""

    def test_optimize_all_candidates(self):
        results = optimize_all_candidates(
            base_data_dir="data",
            constraint_rules=ConstraintRules(
                parapet_setback=0.5,
                obstacle_setback=0.3,
                maintenance_aisle_width=0.8,
                maintenance_aisle_frequency_rows=2,
                reserved_space_ratio=0.15,
            ),
            panel_spec=PanelSpec(length=2.2, width=1.1, rated_power_w=550.0),
        )

        assert len(results) > 0
        total_capacity_kwp = sum(r.placement_result.installed_dc_capacity_kwp for r in results)
        assert total_capacity_kwp > 0

        for r in results:
            assert isinstance(r, BuildingPVResult)
            if r.placement_result.total_panel_count > 0:
                assert r.panel_coordinates_wgs84.shape == (r.placement_result.total_panel_count, 4, 2)
                assert r.annual_yield_kwh > 0
                assert r.estimated_cost_inr > 0
                geojson_feat = r.to_geojson_feature()
                assert geojson_feat["type"] == "FeatureCollection"
