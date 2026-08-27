from datetime import date

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_full_analysis_pipeline_and_geojson_flow(sample_request: dict) -> None:
    # 1. Create analysis run
    response = client.post("/analysis-runs", json=sample_request)
    assert response.status_code == 201
    run_data = response.json()
    assert "run_id" in run_data
    assert run_data["status"] == "completed"
    assert run_data["contract_version"] == "v1"
    assert len(run_data["candidates"]) == 1
    
    candidate = run_data["candidates"][0]
    assert candidate["candidate_id"] == "roof-a"
    assert candidate["eligible"] is True
    assert candidate["rank"] == 1
    assert candidate["total_score"] is not None
    assert "positive_reasons" in candidate
    assert "caution_reasons" in candidate

    run_id = run_data["run_id"]

    # 2. Get analysis run by ID
    get_res = client.get(f"/analysis-runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["run_id"] == run_id

    # 3. Rerank analysis run
    new_weights = {
        "weights": {
            "generation": 0.50,
            "physical": 0.20,
            "grid": 0.10,
            "economics": 0.10,
            "confidence": 0.10,
        }
    }
    rerank_res = client.post(f"/analysis-runs/{run_id}/rerank", json=new_weights)
    assert rerank_res.status_code == 200
    reranked_data = rerank_res.json()
    assert reranked_data["weights"]["generation"] == 0.50

    # 4. Retrieve candidates GeoJSON
    geojson_res = client.get(f"/analysis-runs/{run_id}/candidates.geojson")
    assert geojson_res.status_code == 200
    geojson = geojson_res.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1
    feature = geojson["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"] == {"type": "Point", "coordinates": [72.805, 19.105]}
    props = feature["properties"]
    assert props["run_id"] == run_id
    assert props["candidate_id"] == "roof-a"
    assert props["eligible"] is True
    assert props["rank"] == 1
    assert props["confidence"] == 0.81


def test_missing_run_id_returns_404() -> None:
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    
    get_res = client.get(f"/analysis-runs/{non_existent_id}")
    assert get_res.status_code == 404
    assert get_res.json()["detail"] == "Analysis run not found"

    rerank_payload = {
        "weights": {
            "generation": 0.20,
            "physical": 0.20,
            "grid": 0.20,
            "economics": 0.20,
            "confidence": 0.20,
        }
    }
    rerank_res = client.post(f"/analysis-runs/{non_existent_id}/rerank", json=rerank_payload)
    assert rerank_res.status_code == 404

    geojson_res = client.get(f"/analysis-runs/{non_existent_id}/candidates.geojson")
    assert geojson_res.status_code == 404


def test_invalid_weights_rejected_422(sample_request: dict) -> None:
    invalid_request = sample_request.copy()
    invalid_request["weights"] = {
        "generation": 0.5,
        "physical": 0.5,
        "grid": 0.5,
        "economics": 0.5,
        "confidence": 0.5,
    }
    response = client.post("/analysis-runs", json=invalid_request)
    assert response.status_code == 422


def test_duplicate_candidate_ids_rejected_400(sample_request: dict) -> None:
    dup_request = sample_request.copy()
    dup_request["candidates"] = [
        sample_request["candidates"][0],
        sample_request["candidates"][0],
    ]
    response = client.post("/analysis-runs", json=dup_request)
    assert response.status_code == 400
    assert "Duplicate candidate_id" in response.json()["detail"]


def test_temporal_warnings_generated(sample_request: dict) -> None:
    temporal_request = sample_request.copy()
    temporal_request["sources"] = [
        {
            "source_id": "nasa-power-snapshot",
            "title": "NASA POWER Weather",
            "provider": "NASA",
            "citation_url": "https://power.larc.nasa.gov",
            "license_name": "Open Data",
            "retrieved_at": "2026-08-01T00:00:00Z",
            "version": "1.0",
            "temporal_type": "snapshot",
            "valid_from": date(2020, 1, 1).isoformat(),
            "valid_to": date(2025, 12, 31).isoformat(),
        }
    ]
    response = client.post("/analysis-runs", json=temporal_request)
    assert response.status_code == 201
    run_data = response.json()
    assert len(run_data["temporal_warnings"]) == 1
    assert "reference date exceeds validity" in run_data["temporal_warnings"][0]
