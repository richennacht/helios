"""Explainable solar-resource components used by the regional scorer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolarResourceBreakdown:
    """Separate irradiance into auditable components instead of one opaque value."""

    ghi_kwh_m2_year: float
    dni_kwh_m2_year: float | None
    dhi_kwh_m2_year: float | None
    seasonal_variability_fraction: float | None
    temperature_loss_fraction: float | None
    weather_confidence: float
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.ghi_kwh_m2_year <= 0:
            raise ValueError("GHI must be positive")
        for name in ("dni_kwh_m2_year", "dhi_kwh_m2_year"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
        for name in ("seasonal_variability_fraction", "temperature_loss_fraction"):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not 0 <= self.weather_confidence <= 1:
            raise ValueError("weather_confidence must be in [0, 1]")
        if not self.source_ids:
            raise ValueError("at least one solar source is required")


def effective_irradiance_score(resource: SolarResourceBreakdown) -> float:
    """Return a bounded benefit score with explicit weather/season penalties."""
    score = resource.ghi_kwh_m2_year / 2_200.0
    if resource.dni_kwh_m2_year is not None:
        score *= 0.7 + 0.3 * min(resource.dni_kwh_m2_year / resource.ghi_kwh_m2_year, 1.0)
    if resource.seasonal_variability_fraction is not None:
        score *= 1.0 - 0.25 * resource.seasonal_variability_fraction
    if resource.temperature_loss_fraction is not None:
        score *= 1.0 - resource.temperature_loss_fraction
    return round(max(0.0, min(score, 1.0)) * resource.weather_confidence, 6)
