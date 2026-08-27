"""Tests for the Helios Roof-Plane & Geometry Model and Engine."""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pytest
import shapely.geometry
import torch
from fastapi.testclient import TestClient

from helios.ml.roof_geometry.geometry_engine import (
    GeometryEngine,
    RoofGeometryNet,
    calculate_surface_area,
)
from helios.ml.solar_output import estimate_annual_pv_yield_with_geometry
from apps.api.main import app


@pytest.fixture
def sample_polygon_geojson():
    return {
        "type": "Polygon",
        "coordinates": [[
            [73.0685, 19.0450],
            [73.0690, 19.0450],
            [73.0690, 19.0455],
            [73.0685, 19.0455],
            [73.0685, 19.0450],
        ]]
    }


def test_calculate_surface_area_flat(sample_polygon_geojson):
    area_0 = calculate_surface_area(sample_polygon_geojson, pitch_angle=0.0)
    assert area_0 > 0
    # Kharghar ~50m x 55m approx 2700-3100 m2
    assert 2500 < area_0 < 3500


def test_calculate_surface_area_pitch_scaling(sample_polygon_geojson):
    pitch = 20.0
    area_0 = calculate_surface_area(sample_polygon_geojson, pitch_angle=0.0)
    area_20 = calculate_surface_area(sample_polygon_geojson, pitch_angle=pitch)
    
    expected_ratio = 1.0 / math.cos(math.radians(pitch))
    actual_ratio = area_20 / area_0
    
    assert math.isclose(actual_ratio, expected_ratio, rel_tol=1e-3)
    assert area_20 > area_0


def test_roof_geometry_net_architecture():
    model = RoofGeometryNet(in_channels=4, num_classes=4, pretrained=False)
    model.eval()
    
    dummy_input = torch.randn(2, 4, 128, 128)
    with torch.no_grad():
        out = model(dummy_input)
        
    assert "class_logits" in out
    assert "pitch_deg" in out
    assert "azimuth_sin_cos" in out
    
    assert out["class_logits"].shape == (2, 4)
    assert out["pitch_deg"].shape == (2,)
    assert out["azimuth_sin_cos"].shape == (2, 2)
    
    # Check pitch in [0, 45]
    assert (out["pitch_deg"] >= 0.0).all()
    assert (out["pitch_deg"] <= 45.0).all()


def test_geometry_engine_prediction(sample_polygon_geojson):
    engine = GeometryEngine()
    result = engine.predict(polygon_geojson=sample_polygon_geojson)
    
    required_keys = {
        "pitch_deg",
        "azimuth_deg",
        "surface_area_sqm",
        "roof_type",
        "horizontal_area_sqm",
        "confidence",
    }
    assert required_keys.issubset(result.keys())
    assert result["roof_type"] in ["flat", "gable", "hip", "single-slant"]
    assert 0 <= result["pitch_deg"] <= 45.0
    assert 0 <= result["azimuth_deg"] <= 360.0
    assert result["surface_area_sqm"] >= result["horizontal_area_sqm"]


def test_estimate_annual_pv_yield_with_geometry():
    horizontal_area = 1000.0
    pitch = 18.0
    azimuth = 180.0  # optimal south
    
    calc = estimate_annual_pv_yield_with_geometry(
        horizontal_area_m2=horizontal_area,
        pitch_deg=pitch,
        azimuth_deg=azimuth,
        irradiance_kwh_m2_year=1850.0,
    )
    
    assert calc["horizontal_area_m2"] == 1000.0
    assert calc["surface_area_m2"] > 1000.0
    assert calc["usable_area_m2"] == round(calc["surface_area_m2"] * 0.70, 2)
    assert calc["tilt_multiplier"] >= 1.0  # optimal south tilt gives boost
    assert calc["annual_yield_kwh"] > 0
    assert calc["area_gain_pct"] > 4.0


def test_api_geometry_predict_route(sample_polygon_geojson):
    client = TestClient(app)
    response = client.post(
        "/geometry/predict",
        json={"polygon_geojson": sample_polygon_geojson},
    )
    assert response.status_code == 200
    data = response.json()
    assert "surface_area_sqm" in data
    assert "annual_yield_kwh" in data
    assert "roof_type" in data
    assert "area_gain_pct" in data
