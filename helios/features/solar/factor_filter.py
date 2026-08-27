"""Research-informed, deterministic PV factor screening for Person 3.

This layer has no network access. Person 1 supplies registered/cached weather and
irradiance; Person 2 supplies usable roof area and the shading proxy.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class EnvironmentalFactors:
    """Annual resource and weather factors from one registered source period."""

    annual_poa_kwh_m2: float
    mean_air_temperature_c: float
    mean_wind_speed_m_s: float
    shading_factor: float
    soiling_loss_fraction: float
    resource_period: str
    source_id: str
    source_checksum: str
    source_date: str
    generation_confidence: float

    def validation_errors(self) -> tuple[str, ...]:
        failures: list[str] = []
        bounded = {
            "shading_factor": self.shading_factor,
            "soiling_loss_fraction": self.soiling_loss_fraction,
            "generation_confidence": self.generation_confidence,
        }
        if not isfinite(self.annual_poa_kwh_m2) or self.annual_poa_kwh_m2 <= 0:
            failures.append("annual_poa_kwh_m2_invalid")
        if (
            not isfinite(self.mean_air_temperature_c)
            or not -40 <= self.mean_air_temperature_c <= 70
        ):
            failures.append("mean_air_temperature_c_out_of_range")
        if not isfinite(self.mean_wind_speed_m_s) or not 0 <= self.mean_wind_speed_m_s <= 60:
            failures.append("mean_wind_speed_m_s_out_of_range")
        for name, value in bounded.items():
            if not isfinite(value) or not 0 <= value <= 1:
                failures.append(f"{name}_out_of_range")
        if not all((self.resource_period, self.source_id, self.source_checksum, self.source_date)):
            failures.append("solar_provenance_missing")
        return tuple(failures)


@dataclass(frozen=True)
class PvFactorAssumptions:
    """Explicit annual screening assumptions.

    usable_area_m2 is already usable roof area from Person 2, so it is not
    multiplied by a packing/usable-area fraction again. Performance ratio
    excludes inverter, shading, soiling and degradation losses, which are each
    applied exactly once below.
    """

    version: str
    area_per_kwp_m2: float
    performance_ratio_excluding_inverter: float
    inverter_efficiency: float
    temperature_coefficient_per_c: float
    nominal_operating_cell_temperature_c: float
    annual_degradation_rate: float = 0.0
    reference_year: int = 1

    def __post_init__(self) -> None:
        if not self.version or self.area_per_kwp_m2 <= 0 or self.reference_year < 1:
            raise ValueError("version, positive area_per_kwp_m2, and reference_year are required")
        for name in (
            "performance_ratio_excluding_inverter",
            "inverter_efficiency",
            "annual_degradation_rate",
        ):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not -0.02 <= self.temperature_coefficient_per_c <= 0:
            raise ValueError("temperature_coefficient_per_c must be in [-0.02, 0]")


@dataclass(frozen=True)
class SolarScreeningResult:
    annual_yield_kwh: float
    installable_capacity_kwp: float
    cell_temperature_c: float
    temperature_factor: float
    loss_shading_fraction: float
    loss_soiling_fraction: float
    loss_performance_fraction: float
    loss_inverter_fraction: float
    loss_degradation_fraction: float


def calculate_solar_screening(
    *, usable_area_m2: float, factors: EnvironmentalFactors, assumptions: PvFactorAssumptions
) -> SolarScreeningResult:
    """Calculate annual yield after rejecting invalid registered factor inputs."""
    if usable_area_m2 < 0:
        raise ValueError("usable_area_m2 must be non-negative")
    if failures := factors.validation_errors():
        raise ValueError(f"invalid environmental factors: {', '.join(failures)}")

    cell_temp = factors.mean_air_temperature_c + (
        factors.annual_poa_kwh_m2 / 8760
    ) * (assumptions.nominal_operating_cell_temperature_c - 20) / 800 / (
        1 + 0.05 * factors.mean_wind_speed_m_s
    )
    temperature_factor = max(
        0.0, 1 + assumptions.temperature_coefficient_per_c * (cell_temp - 25)
    )
    capacity_kwp = usable_area_m2 / assumptions.area_per_kwp_m2
    degradation_factor = (1 - assumptions.annual_degradation_rate) ** (
        assumptions.reference_year - 1
    )
    annual_yield = (
        capacity_kwp * factors.annual_poa_kwh_m2 * factors.shading_factor
        * (1 - factors.soiling_loss_fraction)
        * assumptions.performance_ratio_excluding_inverter
        * assumptions.inverter_efficiency * temperature_factor * degradation_factor
    )
    return SolarScreeningResult(
        annual_yield_kwh=annual_yield,
        installable_capacity_kwp=capacity_kwp,
        cell_temperature_c=cell_temp,
        temperature_factor=temperature_factor,
        loss_shading_fraction=1 - factors.shading_factor,
        loss_soiling_fraction=factors.soiling_loss_fraction,
        loss_performance_fraction=1 - assumptions.performance_ratio_excluding_inverter,
        loss_inverter_fraction=1 - assumptions.inverter_efficiency,
        loss_degradation_fraction=1 - degradation_factor,
    )
