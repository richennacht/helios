"""Comprehensive test suite for Helios Roof-Plane & Geometry Engine."""

import json
import math
import numpy as np
import pytest
import shapely.geometry
import geopandas as gpd
import torch

from geometry_engine import calculate_surface_area, RoofGeometryNet, GeometryEngine, ROOF_CLASSES
from dataset import generate_synthetic_roof_patch, RoofGeometryDataset


def test_calculate_surface_area_flat():
    """Verify flat roof (0 deg pitch) yields exact horizontal area."""
    # 10m x 20m rectangular polygon in projected metric coords
    polygon = shapely.geometry.box(0, 0, 10, 20)  # Area = 200 m^2
    surface_area = calculate_surface_area(polygon, pitch_angle=0.0, default_crs="EPSG:32643")
    assert math.isclose(surface_area, 200.0, rel_tol=1e-5)


def test_calculate_surface_area_45_degrees():
    """Verify 45 deg pitch yields sqrt(2) * horizontal area."""
    polygon = shapely.geometry.box(0, 0, 10, 10)  # Area = 100 m^2
    surface_area = calculate_surface_area(polygon, pitch_angle=45.0, default_crs="EPSG:32643")
    expected = 100.0 / math.cos(math.radians(45.0))  # 100 * sqrt(2) ~= 141.421356
    assert math.isclose(surface_area, expected, rel_tol=1e-5)


def test_calculate_surface_area_pitch_clamping():
    """Verify pitch angles outside [0, 45] are safely clamped."""
    polygon = shapely.geometry.box(0, 0, 10, 10)
    area_neg = calculate_surface_area(polygon, pitch_angle=-10.0, default_crs="EPSG:32643")
    assert math.isclose(area_neg, 100.0, rel_tol=1e-5)
    
    area_over = calculate_surface_area(polygon, pitch_angle=60.0, default_crs="EPSG:32643")
    expected_45 = 100.0 / math.cos(math.radians(45.0))
    assert math.isclose(area_over, expected_45, rel_tol=1e-5)


def test_calculate_surface_area_various_inputs():
    """Verify handling of GeoJSON string, dict, Shapely shape, and GeoDataFrame."""
    geojson_dict = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
    }
    geojson_str = json.dumps(geojson_dict)
    shapely_geom = shapely.geometry.shape(geojson_dict)
    gdf = gpd.GeoDataFrame({"geometry": [shapely_geom]}, crs="EPSG:32643")
    
    area_dict = calculate_surface_area(geojson_dict, pitch_angle=30.0, default_crs="EPSG:32643")
    area_str = calculate_surface_area(geojson_str, pitch_angle=30.0, default_crs="EPSG:32643")
    area_shapely = calculate_surface_area(shapely_geom, pitch_angle=30.0, default_crs="EPSG:32643")
    area_gdf = calculate_surface_area(gdf, pitch_angle=30.0)
    
    expected = 100.0 / math.cos(math.radians(30.0))
    assert math.isclose(area_dict, expected, rel_tol=1e-4)
    assert math.isclose(area_str, expected, rel_tol=1e-4)
    assert math.isclose(area_shapely, expected, rel_tol=1e-4)
    assert math.isclose(area_gdf, expected, rel_tol=1e-4)


def test_geographic_wgs84_reprojection():
    """Verify WGS84 geographic polygon (e.g. Kharghar) is accurately reprojected to metric UTM."""
    # Approx 50m x 50m building in Kharghar (Navi Mumbai, ~19.045 N, 73.068 E)
    kharghar_polygon = {
        "type": "Polygon",
        "coordinates": [[
            [73.06850, 19.04500],
            [73.06897, 19.04500],
            [73.06897, 19.04545],
            [73.06850, 19.04545],
            [73.06850, 19.04500]
        ]]
    }
    # Calculate area with 20 deg pitch
    surface_area = calculate_surface_area(kharghar_polygon, pitch_angle=20.0, default_crs="EPSG:4326")
    assert surface_area > 1500.0  # Approx 2500 m^2 physical footprint
    assert surface_area < 3500.0


def test_roof_geometry_net_forward():
    """Verify PyTorch model forward pass, output shapes, and output ranges."""
    model = RoofGeometryNet(in_channels=4, num_classes=4)
    model.eval()
    
    batch = torch.randn(2, 4, 128, 128)
    with torch.no_grad():
        out = model(batch)
        
    assert "class_logits" in out
    assert "pitch_deg" in out
    assert "azimuth_sin_cos" in out
    
    assert out["class_logits"].shape == (2, 4)
    assert out["pitch_deg"].shape == (2,)
    assert out["azimuth_sin_cos"].shape == (2, 2)
    
    # Verify pitch angle is within [0, 45]
    pitch_vals = out["pitch_deg"].numpy()
    assert (pitch_vals >= 0.0).all() and (pitch_vals <= 45.0).all()
    
    # Verify azimuth vectors have unit norm
    az_norm = torch.norm(out["azimuth_sin_cos"], dim=-1).numpy()
    assert np.allclose(az_norm, 1.0, atol=1e-5)


def test_geometry_engine_json_schema():
    """Verify GeometryEngine returns JSON containing exact required keys."""
    engine = GeometryEngine()
    
    dsm, rgb = generate_synthetic_roof_patch("gable", pitch_deg=22.0, azimuth_deg=90.0)
    dsm_norm = (dsm - np.mean(dsm)) / (np.std(dsm) + 1e-5)
    composite = np.concatenate([np.transpose(rgb, (2, 0, 1)), np.expand_dims(dsm_norm, 0)], axis=0)
    
    polygon = shapely.geometry.box(0, 0, 15, 20)  # 300 m^2
    output = engine.predict(elevation_or_image_crop=composite, polygon_geojson=polygon, default_crs="EPSG:32643")
    
    # Required keys according to specification:
    # {'pitch_deg': float, 'azimuth_deg': float, 'surface_area_sqm': float}
    assert "pitch_deg" in output and isinstance(output["pitch_deg"], float)
    assert "azimuth_deg" in output and isinstance(output["azimuth_deg"], float)
    assert "surface_area_sqm" in output and isinstance(output["surface_area_sqm"], float)
    assert "roof_type" in output
    assert "horizontal_area_sqm" in output
    
    assert 0.0 <= output["pitch_deg"] <= 45.0
    assert 0.0 <= output["azimuth_deg"] <= 360.0
    assert output["surface_area_sqm"] >= 300.0  # Must be >= horizontal area
