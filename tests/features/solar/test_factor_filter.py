import pytest

from helios.features.economics.batch_handoff import (
    EconomicsFactors,
    P3Input,
    build_p3_batch,
)
from helios.features.solar.factor_filter import (
    EnvironmentalFactors,
    PvFactorAssumptions,
)

ASSUMPTIONS = PvFactorAssumptions(
    version="solar-economics-2026-08-v2",
    area_per_kwp_m2=5.0,
    performance_ratio_excluding_inverter=0.86,
    inverter_efficiency=0.96,
    temperature_coefficient_per_c=-0.004,
    nominal_operating_cell_temperature_c=45.0,
)


def valid_input(candidate_id: str, poa: float = 1800.0) -> P3Input:
    return P3Input(
        candidate_id=candidate_id,
        usable_area_m2=100.0,
        factors=EnvironmentalFactors(
            annual_poa_kwh_m2=poa,
            mean_air_temperature_c=28.0,
            mean_wind_speed_m_s=2.5,
            shading_factor=0.8,
            soiling_loss_fraction=0.03,
            resource_period="2025 calendar year",
            source_id="nasa-power-kharghar",
            source_checksum="sha256:fixture",
            source_date="2026-08-27",
            generation_confidence=0.8,
        ),
        economics=EconomicsFactors(
            capex_inr_per_kwp=50000.0,
            energy_value_inr_per_kwh=8.0,
            rent_inr_month=None,
            economics_confidence=0.7,
            currency="INR",
            source_id="registered-cost-v1",
            source_date="2026-08-27",
        ),
    )


def test_batch_emits_exact_person4_p3_schema_and_evidence() -> None:
    result = build_p3_batch([valid_input("roof-a"), valid_input("roof-b", 1700)], ASSUMPTIONS)

    from helios.ranking.contracts import P3CandidateRow as P4CandidateRow

    assert len(result.rows) == 2
    P4CandidateRow.model_validate(result.rows[0].__dict__)
    assert result.evidence[0].source_checksum == "sha256:fixture"
    assert result.evidence[0].economics_confidence == 0.7


def test_missing_rent_provenance_is_rejected() -> None:
    item = valid_input("roof-a")
    object.__setattr__(item, "economics", EconomicsFactors(
        capex_inr_per_kwp=None, energy_value_inr_per_kwh=None, rent_inr_month=1000.0,
        economics_confidence=0.5, currency=None, source_id=None, source_date=None,
    ))
    result = build_p3_batch([item], ASSUMPTIONS)
    assert result.rows == ()
    assert "economics_provenance_missing" in result.rejected["roof-a"]


def test_invalid_weather_factor_is_filtered() -> None:
    item = valid_input("roof-a")
    object.__setattr__(item, "factors", EnvironmentalFactors(
        annual_poa_kwh_m2=1800, mean_air_temperature_c=28, mean_wind_speed_m_s=-1,
        shading_factor=0.8, soiling_loss_fraction=0.03, resource_period="2025",
        source_id="solar", source_checksum="x", source_date="2026-08-27",
        generation_confidence=0.8,
    ))
    result = build_p3_batch([item], ASSUMPTIONS)
    assert "mean_wind_speed_m_s_out_of_range" in result.rejected["roof-a"]


def test_usable_area_is_not_reduced_twice() -> None:
    item = valid_input("roof-a")
    result = build_p3_batch([item], ASSUMPTIONS)
    assert result.rows[0].estimated_cost_inr == pytest.approx(1_000_000.0)
