"""Transparent screening economics for Person 3 solar features."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EconomicsInput:
    capex_inr_per_kwp: float | None
    energy_value_inr_per_kwh: float | None
    rent_inr_month: float | None
    currency: str | None
    source_id: str | None
    source_date: str | None

    def __post_init__(self) -> None:
        for name in ("capex_inr_per_kwp", "energy_value_inr_per_kwh", "rent_inr_month"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative when supplied")
        if (self.capex_inr_per_kwp is not None or self.energy_value_inr_per_kwh is not None) and (
            not self.currency or not self.source_id or not self.source_date
        ):
            raise ValueError(
                "registered economics must include currency, source_id and source_date"
            )


@dataclass(frozen=True)
class EconomicFeature:
    estimated_cost_inr: float | None
    estimated_rent_inr_month: float | None
    annual_energy_value_inr: float | None
    simple_payback_years: float | None
    economics_confidence: float
    provenance_ids: tuple[str, ...]


def calculate_access_cost_feature(
    *, road_distance_m: float | None, grid_distance_m: float | None,
    repairability_score: float | None, base_capex_inr: float | None,
) -> dict[str, float | None]:
    """Estimate logistics/access additions from OSM context without hiding missing data."""
    for name, value in (("road_distance_m", road_distance_m), ("grid_distance_m", grid_distance_m)):
        if value is not None and value < 0:
            raise ValueError(f"{name} must be non-negative")
    if repairability_score is not None and not 0 <= repairability_score <= 1:
        raise ValueError("repairability_score must be in [0, 1]")
    if base_capex_inr is not None and base_capex_inr < 0:
        raise ValueError("base_capex_inr must be non-negative")
    logistics = (
        (road_distance_m or 0) * 12.0 + (grid_distance_m or 0) * 4.0
        if road_distance_m is not None and grid_distance_m is not None else None
    )
    repairability_adder = (
        (1.0 - repairability_score) * (base_capex_inr or 0) * 0.08
        if repairability_score is not None and base_capex_inr is not None else None
    )
    total = (
        (base_capex_inr or 0) + (logistics or 0) + (repairability_adder or 0)
        if (
            base_capex_inr is not None
            and logistics is not None
            and repairability_adder is not None
        )
        else None
    )
    return {
        "logistics_cost_inr": logistics,
        "repairability_adder_inr": repairability_adder,
        "estimated_total_cost_inr": total,
    }


def calculate_economic_feature(
    *, installable_capacity_kwp: float, annual_yield_kwh: float, economics: EconomicsInput
) -> EconomicFeature:
    """Calculate screening-only economics without replacing unavailable inputs with zero."""
    if installable_capacity_kwp < 0 or annual_yield_kwh < 0:
        raise ValueError("capacity and annual yield must be non-negative")

    cost = (
        installable_capacity_kwp * economics.capex_inr_per_kwp
        if economics.capex_inr_per_kwp is not None
        else None
    )
    value = (
        annual_yield_kwh * economics.energy_value_inr_per_kwh
        if economics.energy_value_inr_per_kwh is not None
        else None
    )
    payback = (
        cost / value if cost is not None and value is not None and value > 0 else None
    )
    confidence = (
        1.0
        if cost is not None and value is not None
        else 0.5
        if value is not None
        else 0.0
    )
    return EconomicFeature(
        estimated_cost_inr=cost,
        estimated_rent_inr_month=economics.rent_inr_month,
        annual_energy_value_inr=value,
        simple_payback_years=payback,
        economics_confidence=confidence,
        provenance_ids=(economics.source_id,) if economics.source_id else (),
    )
