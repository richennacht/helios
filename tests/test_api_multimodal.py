from fastapi.testclient import TestClient

from apps.api.main import app


def test_multimodal_route_loads_server_owned_fixture_and_filters_point_candidates():
    client = TestClient(app)
    response = client.post(
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
    assert body["contract_version"] == "person4.v1"
    assert body["ranked_candidates"]
    assert body["stability_report"]["method_version"] == "ccra-v1"


def test_multimodal_route_rejects_missing_aoi():
    response = TestClient(app).post("/analysis-runs/multimodal", json={})
    assert response.status_code == 422
