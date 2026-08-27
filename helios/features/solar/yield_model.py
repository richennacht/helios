"""Pure, deterministic annual solar-yield calculations for Person 3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

KWH_PER_MWH: Final = 1_000.0


@dataclass(frozen=True)
class SolarAssumptions:
    """Versioned screening assumptions; all fraction values are retained factors."""

    version: str
    usable_area_factor: float
    area_per_kwp_m2: float
    performance_ratio: float
    inverter_efficiency: float

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("assumption version is required")
        if self.area_per_kwp_m2 <= 0:
            raise ValueError("area_per_kwp_m2 must be positive")
        for name in ("usable_area_factor", "performance_ratio", "inverter_efficiency"):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")


@dataclass(frozen=True)
class SolarResource:
    """Registered annual plane-of-array resource, prepared upstream from a cached source."""

    annual_poa_kwh_m2: float
    resource_period: str
    source_id: str
    source_checksum: str
    solar_confidence: float

    def __post_init__(self) -> None:
        if self.annual_poa_kwh_m2 <= 0:
            raise ValueError("annual_poa_kwh_m2 must be positive")
        if not self.resource_period or not self.source_id or not self.source_checksum:
            raise ValueError("solar resource period and provenance are required")
        if not 0 <= self.solar_confidence <= 1:
            raise ValueError("solar_confidence must be in [0, 1]")


@dataclass(frozen=True)
class SolarFeature:
    candidate_id: str
    usable_area_m2: float
    installable_capacity_kwp: float
    annual_yield_kwh: float
    yield_per_kwp_kwh: float
    shading_factor: float
    loss_shading_fraction: float
    loss_performance_fraction: float
    loss_inverter_fraction: float
    solar_confidence: float
    resource_period: str
    assumption_version: str
    provenance_ids: tuple[str, ...]


def calculate_solar_feature(
    *,
    candidate_id: str,
    usable_area_m2: float,
    shading_factor: float,
    spatial_confidence: float,
    resource: SolarResource,
    assumptions: SolarAssumptions,
) -> SolarFeature:
    """Return a transparent annual screening estimate from registered resource data.

    annual_yield_kwh = installable_capacity_kwp * annual_poa_kwh_m2
        * shading_factor * performance_ratio * inverter_efficiency

    The resource must be derived and cached by an upstream source adapter; this
    function makes no network calls and never changes spatial inputs.
    """
    if not candidate_id:
        raise ValueError("candidate_id is required")
    if usable_area_m2 < 0:
        raise ValueError("usable_area_m2 must be non-negative")
    if not 0 <= shading_factor <= 1 or not 0 <= spatial_confidence <= 1:
        raise ValueError("shading_factor and spatial_confidence must be in [0, 1]")

    capacity_kwp = usable_area_m2 * assumptions.usable_area_factor / assumptions.area_per_kwp_m2
    yield_kwh = (
        capacity_kwp
        * resource.annual_poa_kwh_m2
        * shading_factor
        * assumptions.performance_ratio
        * assumptions.inverter_efficiency
    )
    confidence = round(min(spatial_confidence, resource.solar_confidence), 2)
    return SolarFeature(
        candidate_id=candidate_id,
        usable_area_m2=usable_area_m2,
        installable_capacity_kwp=capacity_kwp,
        annual_yield_kwh=yield_kwh,
        yield_per_kwp_kwh=yield_kwh / capacity_kwp if capacity_kwp else 0.0,
        shading_factor=shading_factor,
        loss_shading_fraction=1 - shading_factor,
        loss_performance_fraction=1 - assumptions.performance_ratio,
        loss_inverter_fraction=1 - assumptions.inverter_efficiency,
        solar_confidence=confidence,
        resource_period=resource.resource_period,
        assumption_version=assumptions.version,
        provenance_ids=(resource.source_id,),
    )
