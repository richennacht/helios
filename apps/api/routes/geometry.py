from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from helios.contracts.models import RoofGeometryPrediction, RoofType
from helios.ml.roof_geometry import simulate_geometry
from helios.ml.solar_output import estimate_annual_pv_yield_with_geometry

router = APIRouter(prefix="/geometry", tags=["geometry"])


class GeometrySimulationRequest(BaseModel):
    polygon_geojson: dict[str, Any]
    pitch_deg: float = Field(ge=0, le=45)
    azimuth_deg: float = Field(ge=0, le=360)
    roof_type: RoofType
    provenance: str = Field(min_length=3)


class GeometrySimulationResponse(RoofGeometryPrediction):
    area_gain_pct: float
    annual_yield_kwh: float
    estimated_capacity_kwp: float
    orientation_factor: float


@router.post("/simulate", response_model=GeometrySimulationResponse)
def simulate_roof_geometry(payload: GeometrySimulationRequest) -> GeometrySimulationResponse:
    try:
        prediction = simulate_geometry(
            payload.polygon_geojson,
            pitch_deg=payload.pitch_deg,
            azimuth_deg=payload.azimuth_deg,
            roof_type=payload.roof_type,
            provenance=payload.provenance,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    pv = estimate_annual_pv_yield_with_geometry(
        horizontal_area_m2=prediction.horizontal_area_sqm,
        pitch_deg=prediction.pitch_deg,
        azimuth_deg=prediction.azimuth_deg,
    )
    return GeometrySimulationResponse(
        **prediction.model_dump(),
        area_gain_pct=pv["area_gain_pct"],
        annual_yield_kwh=pv["annual_yield_kwh"],
        estimated_capacity_kwp=pv["estimated_capacity_kwp"],
        orientation_factor=pv["orientation_factor"],
    )
