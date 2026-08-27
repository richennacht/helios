import math

from fastapi.testclient import TestClient

from apps.api.main import app
from helios.contracts.models import RoofType
from helios.ml.roof_geometry import calculate_surface_area, simulate_geometry


def sample_polygon() -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [73.0685, 19.0450],
                [73.0690, 19.0450],
                [73.0690, 19.0455],
                [73.0685, 19.0455],
                [73.0685, 19.0450],
            ]
        ],
    }


def test_surface_area_uses_explicit_pitch() -> None:
    horizontal, flat = calculate_surface_area(sample_polygon(), 0)
    _, sloped = calculate_surface_area(sample_polygon(), 20)
    assert horizontal > 0
    assert flat == horizontal
    assert math.isclose(sloped / horizontal, 1 / math.cos(math.radians(20)), rel_tol=1e-6)


def test_simulation_has_no_invented_model_confidence() -> None:
    result = simulate_geometry(
        sample_polygon(),
        pitch_deg=18,
        azimuth_deg=180,
        roof_type=RoofType.GABLE,
        provenance="operator-entered test assumption",
    )
    assert result.decision_status == "simulation_only"
    assert result.confidence is None
    assert result.provenance == "operator-entered test assumption"


def test_geometry_simulation_api_is_explicit() -> None:
    response = TestClient(app).post(
        "/geometry/simulate",
        json={
            "polygon_geojson": sample_polygon(),
            "pitch_deg": 18,
            "azimuth_deg": 180,
            "roof_type": "gable",
            "provenance": "operator-entered test assumption",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision_status"] == "simulation_only"
    assert body["confidence"] is None
    assert body["surface_area_sqm"] > body["horizontal_area_sqm"]
    assert body["annual_yield_kwh"] > 0


def test_geometry_simulation_rejects_unclosed_polygon() -> None:
    polygon = sample_polygon()
    polygon["coordinates"][0][-1] = [73.0686, 19.0451]
    response = TestClient(app).post(
        "/geometry/simulate",
        json={
            "polygon_geojson": polygon,
            "pitch_deg": 18,
            "azimuth_deg": 180,
            "roof_type": "gable",
            "provenance": "operator-entered test assumption",
        },
    )
    assert response.status_code == 422
