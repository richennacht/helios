"""Frozen Person 4 feature dictionary and named preference presets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from helios.ranking.contracts import WeightPreset, WeightProfile

FEATURE_DICTIONARY_VERSION = "person4.features-v1"
CRITERIA = ("generation", "physical", "grid", "economics")


class FeatureDirection(StrEnum):
    BENEFIT = "benefit"
    COST = "cost"
    EVIDENCE_ONLY = "evidence_only"


class MissingPolicy(StrEnum):
    REQUIRED = "required"
    OPTIONAL_WARNING = "optional_warning"


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    owner: str
    unit: str
    direction: FeatureDirection
    missing_policy: MissingPolicy
    role: str


FEATURE_SPECS = {
    "generation_score": FeatureSpec(
        "generation_score", "P3", "normalized_0_1", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "mcda_criterion",
    ),
    "physical_score": FeatureSpec(
        "physical_score", "P2", "normalized_0_1", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "mcda_criterion",
    ),
    "grid_score": FeatureSpec(
        "grid_score", "P2", "normalized_0_1", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "mcda_criterion",
    ),
    "economics_score": FeatureSpec(
        "economics_score", "P3", "normalized_0_1", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "mcda_criterion",
    ),
    "usable_area_m2": FeatureSpec(
        "usable_area_m2", "P2", "m2", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "hard_filter_and_audit",
    ),
    "shading_factor": FeatureSpec(
        "shading_factor", "P2", "retained_fraction_0_1", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "hard_filter_and_audit",
    ),
    "grid_distance_m": FeatureSpec(
        "grid_distance_m", "P2", "m", FeatureDirection.COST,
        MissingPolicy.REQUIRED, "hard_filter_and_audit",
    ),
    "annual_yield_kwh": FeatureSpec(
        "annual_yield_kwh", "P3", "kWh_per_year", FeatureDirection.BENEFIT,
        MissingPolicy.REQUIRED, "audit",
    ),
    "estimated_cost_inr": FeatureSpec(
        "estimated_cost_inr", "P3", "INR", FeatureDirection.COST,
        MissingPolicy.OPTIONAL_WARNING, "hard_filter_and_audit",
    ),
    "estimated_rent_inr_month": FeatureSpec(
        "estimated_rent_inr_month", "P3", "INR_per_month", FeatureDirection.COST,
        MissingPolicy.OPTIONAL_WARNING, "audit",
    ),
    "overall_confidence": FeatureSpec(
        "overall_confidence", "confidence", "evidence_0_1",
        FeatureDirection.EVIDENCE_ONLY, MissingPolicy.REQUIRED, "uncertainty_only",
    ),
}


WEIGHT_PRESETS = {
    WeightPreset.BALANCED: WeightProfile(
        generation=0.35, physical=0.30, grid=0.20, economics=0.15
    ),
    WeightPreset.ENERGY_FIRST: WeightProfile(
        generation=0.55, physical=0.25, grid=0.10, economics=0.10
    ),
    WeightPreset.COST_FIRST: WeightProfile(
        generation=0.20, physical=0.20, grid=0.15, economics=0.45
    ),
}


def weight_profile_for(preset: WeightPreset | str) -> WeightProfile:
    """Return a defensive copy of a frozen named preference profile."""

    selected = WeightPreset(preset)
    return WEIGHT_PRESETS[selected].model_copy(deep=True)
