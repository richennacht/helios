"""P3 batch handoff adapter with explicit factor and economics provenance."""

from __future__ import annotations

from dataclasses import dataclass

from helios.features.solar.factor_filter import (
    EnvironmentalFactors,
    PvFactorAssumptions,
    calculate_solar_screening,
)


@dataclass(frozen=True)
class EconomicsFactors:
    capex_inr_per_kwp: float | None
    energy_value_inr_per_kwh: float | None
    rent_inr_month: float | None
    economics_confidence: float
    currency: str | None
    source_id: str | None
    source_date: str | None

    def validation_errors(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not 0 <= self.economics_confidence <= 1:
            errors.append("economics_confidence_out_of_range")
        if any(value is not None for value in (
            self.capex_inr_per_kwp, self.energy_value_inr_per_kwh, self.rent_inr_month
        )) and not all((self.currency, self.source_id, self.source_date)):
            errors.append("economics_provenance_missing")
        for name in ("capex_inr_per_kwp", "energy_value_inr_per_kwh", "rent_inr_month"):
            if (value := getattr(self, name)) is not None and value < 0:
                errors.append(f"{name}_negative")
        return tuple(errors)


@dataclass(frozen=True)
class P3Input:
    candidate_id: str
    usable_area_m2: float
    factors: EnvironmentalFactors
    economics: EconomicsFactors


@dataclass(frozen=True)
class P3CandidateRow:
    """Exact Person 4 P3-row schema; extra provenance stays in P3EvidenceRow."""

    candidate_id: str
    annual_yield_kwh: float
    estimated_cost_inr: float | None
    estimated_rent_inr_month: float | None
    generation_score: float
    economics_score: float
    assumption_version: str


@dataclass(frozen=True)
class P3EvidenceRow:
    candidate_id: str
    source_id: str
    source_checksum: str
    source_date: str
    resource_period: str
    currency: str | None
    economics_source_id: str | None
    economics_source_date: str | None
    generation_confidence: float
    economics_confidence: float


@dataclass(frozen=True)
class P3BatchResult:
    rows: tuple[P3CandidateRow, ...]
    evidence: tuple[P3EvidenceRow, ...]
    rejected: dict[str, tuple[str, ...]]


def _normalise(values: list[float], higher_is_better: bool = True) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if low == high:
        return [1.0] * len(values)
    raw = [(value - low) / (high - low) for value in values]
    return raw if higher_is_better else [1 - value for value in raw]


def build_p3_batch(inputs: list[P3Input], assumptions: PvFactorAssumptions) -> P3BatchResult:
    """Filter invalid factor/provenance records and emit P4 rows plus evidence."""
    accepted: list[tuple[P3Input, object]] = []
    rejected: dict[str, tuple[str, ...]] = {}
    for item in inputs:
        errors = item.factors.validation_errors() + item.economics.validation_errors()
        if not item.candidate_id:
            errors += ("candidate_id_missing",)
        if errors:
            rejected[item.candidate_id or "<missing>"] = errors
            continue
        accepted.append((item, calculate_solar_screening(
            usable_area_m2=item.usable_area_m2, factors=item.factors, assumptions=assumptions
        )))

    yields = [result.annual_yield_kwh for _, result in accepted]
    costs = [
        result.installable_capacity_kwp * item.economics.capex_inr_per_kwp
        if item.economics.capex_inr_per_kwp is not None else None
        for item, result in accepted
    ]
    values = [
        result.annual_yield_kwh * item.economics.energy_value_inr_per_kwh
        if item.economics.energy_value_inr_per_kwh is not None else None
        for item, result in accepted
    ]
    paybacks = [
        cost / value if cost is not None and value is not None and value > 0 else None
        for cost, value in zip(costs, values, strict=True)
    ]
    generation_scores = _normalise(yields)
    known_paybacks = [value for value in paybacks if value is not None]
    economics_by_payback = dict(zip(
        known_paybacks, _normalise(known_paybacks, higher_is_better=False), strict=True
    ))

    rows: list[P3CandidateRow] = []
    evidence: list[P3EvidenceRow] = []
    for (item, result), score, cost, payback in zip(
        accepted, generation_scores, costs, paybacks, strict=True
    ):
        rows.append(P3CandidateRow(
            candidate_id=item.candidate_id, annual_yield_kwh=result.annual_yield_kwh,
            estimated_cost_inr=cost, estimated_rent_inr_month=item.economics.rent_inr_month,
            generation_score=score, economics_score=economics_by_payback.get(payback, 0.0),
            assumption_version=assumptions.version,
        ))
        evidence.append(P3EvidenceRow(
            candidate_id=item.candidate_id, source_id=item.factors.source_id,
            source_checksum=item.factors.source_checksum, source_date=item.factors.source_date,
            resource_period=item.factors.resource_period, currency=item.economics.currency,
            economics_source_id=item.economics.source_id,
            economics_source_date=item.economics.source_date,
            generation_confidence=item.factors.generation_confidence,
            economics_confidence=item.economics.economics_confidence,
        ))
    return P3BatchResult(tuple(rows), tuple(evidence), rejected)
