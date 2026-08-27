from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class TemporalType(StrEnum):
    STATIC = "static"
    SNAPSHOT = "snapshot"
    RANGE = "range"
    CLIMATOLOGY = "climatology"


class SourceManifest(BaseModel):
    source_id: str = Field(min_length=1)
    title: str
    provider: str
    citation_url: str
    license_name: str
    license_url: str | None = None
    retrieved_at: datetime
    version: str
    temporal_type: TemporalType
    valid_from: date | None = None
    valid_to: date | None = None
    spatial_resolution_m: float | None = Field(default=None, gt=0)
    notes: str | None = None


class Scenario(BaseModel):
    name: str = "balanced"
    budget_inr: float | None = Field(default=None, gt=0)
    minimum_usable_area_m2: float = Field(default=40, ge=0)
    maximum_grid_distance_m: float | None = Field(default=2000, gt=0)
    preferred_system_kwp: float | None = Field(default=None, gt=0)


class WeightSet(BaseModel):
    generation: float = Field(default=0.30, ge=0)
    physical: float = Field(default=0.25, ge=0)
    grid: float = Field(default=0.20, ge=0)
    economics: float = Field(default=0.20, ge=0)
    confidence: float = Field(default=0.05, ge=0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "WeightSet":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-6:
            raise ValueError("Ranking weights must sum to 1.0")
        return self


class ScoreInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation: float = Field(ge=0, le=1)
    physical: float = Field(ge=0, le=1)
    grid: float = Field(ge=0, le=1)
    economics: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class CandidateMetrics(BaseModel):
    annual_yield_kwh: float = Field(ge=0)
    usable_area_m2: float = Field(ge=0)
    shading_factor: float = Field(ge=0, le=1)
    grid_distance_m: float = Field(ge=0)
    estimated_cost_inr: float | None = Field(default=None, ge=0)
    estimated_rent_inr_month: float | None = Field(default=None, ge=0)
    provenance_ids: list[str] = Field(default_factory=list)


class CandidateInput(BaseModel):
    candidate_id: str
    name: str | None = None
    geometry: dict[str, Any]
    metrics: CandidateMetrics
    normalized: ScoreInputs


class AnalysisRequest(BaseModel):
    contract_version: str = "v1"
    region_name: str
    aoi_geojson: dict[str, Any]
    reference_date: date
    scenario: Scenario = Field(default_factory=Scenario)
    weights: WeightSet = Field(default_factory=WeightSet)
    sources: list[SourceManifest] = Field(default_factory=list)
    candidates: list[CandidateInput] = Field(min_length=1)


class RerankRequest(BaseModel):
    weights: WeightSet


class CandidateResult(BaseModel):
    candidate_id: str
    name: str | None
    geometry: dict[str, Any]
    metrics: CandidateMetrics
    normalized: ScoreInputs
    eligible: bool
    exclusion_reasons: list[str]
    component_scores: dict[str, float]
    total_score: float | None
    rank: int | None
    positive_reasons: list[str]
    caution_reasons: list[str]


class AnalysisRun(BaseModel):
    run_id: str
    contract_version: str = "v1"
    status: RunStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    region_name: str
    reference_date: date
    scenario: Scenario
    weights: WeightSet
    source_ids: list[str]
    temporal_warnings: list[str]
    candidates: list[CandidateResult]
