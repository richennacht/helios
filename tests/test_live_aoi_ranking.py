from fastapi.testclient import TestClient

from apps.api.main import app


def test_local_geolibre_origin_can_call_registered_aoi_ranking_route():
    client = TestClient(app)
    response = client.options(
        "/analysis-runs/multimodal",
        headers={
            "Origin": "http://127.0.0.1:8765",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8765"


def test_registered_aoi_route_returns_explainable_ranking_bundle():
    response = TestClient(app).post(
        "/analysis-runs/multimodal",
        json={
            "aoi": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [73.05, 19.03],
                        [73.09, 19.03],
                        [73.09, 19.07],
                        [73.05, 19.07],
                        [73.05, 19.03],
                    ]
                ],
            }
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    candidate = body["ranked_candidates"][0]
    assert body["assumption_version"]
    assert body["input_versions"]
    assert candidate["overall_confidence"] >= 0
    assert "component_contributions" in candidate
