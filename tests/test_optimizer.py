"""
Comprehensive Pytest Test Suite for Constraint-Aware Solar Panel Layout Optimizer
"""

import math
import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from layout_optimizer import (
    ConstraintRules,
    PanelLayoutOptimizer,
    PanelSpec,
    PlacementResult,
    SolarAccessMatrix,
    optimize_panel_placement,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def rectangular_roof():
    """A standard 30m x 20m commercial flat rooftop."""
    return box(0, 0, 30, 20)


@pytest.fixture
def standard_obstacles():
    """HVAC units and skylights."""
    return [
        box(5, 5, 8, 8),    # HVAC unit 1 (3m x 3m)
        box(18, 10, 21, 13), # HVAC unit 2 (3m x 3m)
        box(10, 14, 12, 16), # Skylight (2m x 2m)
    ]


@pytest.fixture
def gradient_solar_access():
    """A solar access matrix with high sun in center/South and heavy shade on North/West."""
    # 20 rows (Y) x 30 cols (X)
    y_coords, x_coords = np.mgrid[0:20:20j, 0:30:30j]
    # Center/South is 95%, North-West corner drops to 40%
    access = 0.95 - 0.50 * np.exp(-((x_coords - 5)**2 + (y_coords - 15)**2) / 50.0)
    return SolarAccessMatrix(data=access, bounds=(0, 0, 30, 20))


# ============================================================================
# Test Cases
# ============================================================================

class TestCorePlacementAndReturnTypes:
    """Validate API return types, coordinates array shape, and capacity calculations."""

    def test_return_structure_and_types(self, rectangular_roof, standard_obstacles):
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            obstacle_polygons=standard_obstacles,
            constraint_rules={"parapet_setback": 1.0, "obstacle_setback": 0.5, "reserved_space_ratio": 0.0},
            panel_spec={"length": 2.2, "width": 1.1, "rated_power_w": 550.0, "azimuth_deg": 180.0},
        )

        assert isinstance(result, PlacementResult)
        assert result.total_panel_count > 0
        assert isinstance(result.panel_coordinates, np.ndarray)
        assert result.panel_coordinates.shape == (result.total_panel_count, 4, 2)
        
        # Verify DC Capacity formula: N * 550W / 1000 = kWp
        expected_kwp = (result.total_panel_count * 550.0) / 1000.0
        assert math.isclose(result.installed_dc_capacity_kwp, expected_kwp, rel_tol=1e-5)

    def test_json_and_dict_serialization(self, rectangular_roof, standard_obstacles):
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            obstacle_polygons=standard_obstacles,
        )
        d = result.to_dict()
        assert "total_panel_count" in d
        assert "installed_dc_capacity_kwp" in d
        assert "panel_coordinates" in d
        assert len(d["panel_coordinates"]) == result.total_panel_count

        geojson = result.to_geojson()
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) > 0


class TestParapetSetbackConstraint:
    """Verify that all placed panels strictly respect the parapet setback."""

    def test_all_panels_strictly_inside_setback(self, rectangular_roof):
        parapet_setback = 1.5
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            constraint_rules=ConstraintRules(parapet_setback=parapet_setback, reserved_space_ratio=0.0),
        )

        inset_roof = rectangular_roof.buffer(-parapet_setback)
        assert result.total_panel_count > 0

        for panel_poly in result.panel_polygons:
            # Panel must be completely inside inset_roof
            assert inset_roof.contains(panel_poly)
            # Distance to outer perimeter must be at least setback
            dist = panel_poly.distance(rectangular_roof.exterior)
            assert dist >= parapet_setback - 1e-4, f"Panel violated parapet setback: dist={dist}"


class TestObstacleSetbackAndClearance:
    """Verify that panels strictly avoid obstacles and their buffers."""

    def test_no_obstacle_intersection(self, rectangular_roof, standard_obstacles):
        obstacle_setback = 0.8
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            obstacle_polygons=standard_obstacles,
            constraint_rules=ConstraintRules(obstacle_setback=obstacle_setback, reserved_space_ratio=0.0),
        )

        buffered_obstacles = unary_union([obs.buffer(obstacle_setback) for obs in standard_obstacles])

        for panel_poly in result.panel_polygons:
            for obs in standard_obstacles:
                # Direct intersection must be false
                assert not panel_poly.intersects(obs), "Panel intersects obstacle!"
            # Must be disjoint from buffered obstacle
            assert panel_poly.disjoint(buffered_obstacles) or panel_poly.touches(buffered_obstacles), \
                "Panel intersects obstacle setback buffer!"


class TestSolarAccessThresholding:
    """Verify that minimum 80% solar access threshold is strictly enforced."""

    def test_solar_access_filtering(self, rectangular_roof, gradient_solar_access):
        min_threshold = 0.80
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            solar_access_matrix=gradient_solar_access,
            constraint_rules=ConstraintRules(min_solar_access=min_threshold, reserved_space_ratio=0.0),
        )

        assert result.total_panel_count > 0
        for idx, panel_poly in enumerate(result.panel_polygons):
            score = gradient_solar_access.evaluate_polygon_solar_access(panel_poly)
            assert score >= min_threshold - 1e-4, f"Panel {idx} has solar access {score} < {min_threshold}"
            assert result.solar_access_scores[idx] >= min_threshold - 1e-4

    def test_fully_shaded_roof_yields_zero_panels(self, rectangular_roof):
        # 0.50 (50%) solar access everywhere
        low_access = SolarAccessMatrix(data=0.50)
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            solar_access_matrix=low_access,
            constraint_rules=ConstraintRules(min_solar_access=0.80),
        )
        assert result.total_panel_count == 0
        assert result.installed_dc_capacity_kwp == 0.0
        assert len(result.panel_coordinates) == 0


class TestMaintenanceAislesAndReservedSpace:
    """Verify maintenance aisles and reserved space policies."""

    def test_maintenance_aisles_created(self, rectangular_roof):
        aisle_w = 0.8
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            constraint_rules=ConstraintRules(
                maintenance_aisle_width=aisle_w,
                maintenance_aisle_frequency_rows=2,
                reserved_space_ratio=0.0,
            ),
        )

        assert result.total_panel_count > 0

    def test_reserved_space_ratio_reduction(self, rectangular_roof):
        # Unconstrained
        res_full = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            constraint_rules=ConstraintRules(reserved_space_ratio=0.0),
        )

        # With 15% reserved space
        res_reserved = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            constraint_rules=ConstraintRules(reserved_space_ratio=0.15),
        )

        expected_count = int(math.floor(res_full.total_panel_count * 0.85))
        assert res_reserved.total_panel_count == expected_count
        assert res_reserved.total_panel_count < res_full.total_panel_count


class TestIrregularRoofGeometries:
    """Test L-shaped, non-convex, and multi-polygon roof shapes."""

    def test_l_shaped_roof(self):
        # L-shaped polygon
        l_roof = Polygon([(0, 0), (25, 0), (25, 10), (10, 10), (10, 20), (0, 20)])
        result = optimize_panel_placement(
            roof_polygons=l_roof,
            constraint_rules=ConstraintRules(parapet_setback=1.0, reserved_space_ratio=0.0),
        )

        assert result.total_panel_count > 0
        inset = l_roof.buffer(-1.0)
        for poly in result.panel_polygons:
            assert inset.contains(poly)

    def test_multipolygon_input(self):
        # Two distinct roof sections
        section1 = box(0, 0, 15, 15)
        section2 = box(25, 0, 40, 15)
        multi_roof = MultiPolygon([section1, section2])

        result = optimize_panel_placement(
            roof_polygons=multi_roof,
            constraint_rules=ConstraintRules(parapet_setback=1.0, reserved_space_ratio=0.0),
        )

        assert result.total_panel_count > 0
        for poly in result.panel_polygons:
            assert multi_roof.contains(poly)


class TestOrientationsAndAzimuth:
    """Test landscape vs portrait and rotated azimuth angles."""

    def test_portrait_vs_landscape(self, rectangular_roof):
        res_portrait = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            panel_spec=PanelSpec(orientation="portrait"),
            constraint_rules=ConstraintRules(reserved_space_ratio=0.0),
        )
        res_landscape = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            panel_spec=PanelSpec(orientation="landscape"),
            constraint_rules=ConstraintRules(reserved_space_ratio=0.0),
        )

        assert res_portrait.total_panel_count > 0
        assert res_landscape.total_panel_count > 0

    def test_custom_azimuth_angle(self, rectangular_roof):
        # Azimuth 135° (South-East)
        result = optimize_panel_placement(
            roof_polygons=rectangular_roof,
            panel_spec=PanelSpec(azimuth_deg=135.0),
            constraint_rules=ConstraintRules(parapet_setback=1.0, reserved_space_ratio=0.0),
        )

        assert result.total_panel_count > 0
        for poly in result.panel_polygons:
            assert rectangular_roof.contains(poly)


class TestEdgeCases:
    """Test edge cases such as roofs too small for a panel or invalid shapes."""

    def test_roof_smaller_than_one_panel(self):
        tiny_roof = box(0, 0, 1.0, 1.0)
        result = optimize_panel_placement(roof_polygons=tiny_roof)
        assert result.total_panel_count == 0
        assert result.installed_dc_capacity_kwp == 0.0
        assert result.panel_coordinates.shape == (0, 4, 2)
