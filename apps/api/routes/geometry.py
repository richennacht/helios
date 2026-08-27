from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from helios.contracts.models import RoofGeometryPrediction
from helios.ml.roof_geometry.geometry_engine import GeometryEngine, calculate_surface_area
from helios.ml.solar_output import estimate_annual_pv_yield_with_geometry

router = APIRouter(prefix="/geometry", tags=["geometry"])

WEIGHTS_PATH = Path(__file__).resolve().parents[3] / "helios" / "ml" / "roof_geometry" / "models" / "roof_geometry_resnet18.pt"
if not WEIGHTS_PATH.exists():
    WEIGHTS_PATH = Path(__file__).resolve().parents[3] / "helios_roof_geometry" / "models" / "roof_geometry_resnet18.pt"

_engine: Optional[GeometryEngine] = None


def get_engine() -> GeometryEngine:
    global _engine
    if _engine is None:
        _engine = GeometryEngine(model_weights_path=WEIGHTS_PATH if WEIGHTS_PATH.exists() else None)
    return _engine


class GeometryInferenceRequest(BaseModel):
    polygon_geojson: Dict[str, Any] = Field(..., description="GeoJSON polygon geometry or feature")
    pitch_deg: Optional[float] = Field(default=None, ge=0, le=90, description="Optional pitch angle override")
    azimuth_deg: Optional[float] = Field(default=None, ge=0, le=360, description="Optional azimuth angle override")
    crs: str = Field(default="EPSG:4326")


class GeometryInferenceResponse(BaseModel):
    pitch_deg: float
    azimuth_deg: float
    surface_area_sqm: float
    roof_type: str
    horizontal_area_sqm: float
    confidence: float
    area_gain_pct: float
    annual_yield_kwh: float
    estimated_capacity_kwp: float
    tilt_multiplier: float


@router.post("/predict", response_model=GeometryInferenceResponse)
def predict_roof_geometry(payload: GeometryInferenceRequest) -> GeometryInferenceResponse:
    """Predict 3D roof surface geometry and physics-informed solar yield."""
    engine = get_engine()
    try:
        pred = engine.predict(polygon_geojson=payload.polygon_geojson, default_crs=payload.crs)
        
        pitch = payload.pitch_deg if payload.pitch_deg is not None else pred["pitch_deg"]
        azimuth = payload.azimuth_deg if payload.azimuth_deg is not None else pred["azimuth_deg"]
        
        pv_calc = estimate_annual_pv_yield_with_geometry(
            horizontal_area_m2=pred["horizontal_area_sqm"],
            pitch_deg=pitch,
            azimuth_deg=azimuth,
        )
        
        return GeometryInferenceResponse(
            pitch_deg=pitch,
            azimuth_deg=azimuth,
            surface_area_sqm=pred["surface_area_sqm"],
            roof_type=pred["roof_type"],
            horizontal_area_sqm=pred["horizontal_area_sqm"],
            confidence=pred["confidence"],
            area_gain_pct=pv_calc["area_gain_pct"],
            annual_yield_kwh=pv_calc["annual_yield_kwh"],
            estimated_capacity_kwp=pv_calc["estimated_capacity_kwp"],
            tilt_multiplier=pv_calc["tilt_multiplier"],
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Geometry prediction failed: {str(exc)}") from exc
