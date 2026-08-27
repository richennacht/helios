import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from helios.contracts.models import AnalysisRequest, AnalysisRun, RerankRequest
from helios.pipeline.multimodal import rank_selected_aoi
from helios.pipeline.service import AnalysisService
from helios.ranking.contracts import P5RankingRequest, RankingBundle

router = APIRouter(prefix="/analysis-runs", tags=["analysis"])
service = AnalysisService()
FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "fixtures"
    / "person4"
    / "person4-request.json"
)


def _load_default_ranking_request() -> P5RankingRequest:
    """Load the checked-in, provenance-controlled demo request.

    The API owns this default so clients do not need to know internal P2/P3
    table layouts. Production deployments can replace this loader with a
    database-backed regional feature provider without changing the route.
    """
    with FIXTURE_PATH.open(encoding="utf-8") as stream:
        return P5RankingRequest.model_validate(json.load(stream))


@router.post("/multimodal", response_model=RankingBundle)
def run_multimodal_aoi(payload: dict[str, Any]) -> RankingBundle:
    """Run the selected AOI through the aligned P2/P3/Person 4 pipeline."""
    try:
        request = (
            P5RankingRequest.model_validate(payload["ranking_request"])
            if payload.get("ranking_request") is not None
            else _load_default_ranking_request()
        )
        return rank_selected_aoi(request, payload["aoi"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("", response_model=AnalysisRun, status_code=status.HTTP_201_CREATED)
def create_analysis_run(request: AnalysisRequest) -> AnalysisRun:
    try:
        return service.create(request)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@router.get("/{run_id}", response_model=AnalysisRun)
def get_analysis_run(run_id: str) -> AnalysisRun:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run


@router.post("/{run_id}/rerank", response_model=AnalysisRun)
def rerank_analysis(run_id: str, request: RerankRequest) -> AnalysisRun:
    run = service.rerank(run_id, request)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run


@router.get("/{run_id}/candidates.geojson")
def candidate_geojson(run_id: str) -> dict:
    feature_collection = service.as_geojson(run_id)
    if feature_collection is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return feature_collection
