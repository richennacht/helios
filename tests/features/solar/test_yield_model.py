# ruff: noqa: I001
import pytest

from helios.features.economics import EconomicsInput, calculate_economic_feature
from helios.features.solar import SolarAssumptions, SolarResource, calculate_solar_feature


ASSUMPTIONS = SolarAssumptions(
    version="kharghar-v1",
    usable_area_factor=0.70,
    area_per_kwp_m2=5.0,
    performance_ratio=0.86,
    inverter_efficiency=0.96,
)
RESOURCE = SolarResource(
    annual_poa_kwh_m2=1800,
    resource_period="2025 climatology",
    source_id="nasa-power-kharghar",
    source_checksum="fixture-checksum",
    solar_confidence=0.8,
)


def test_three_step_solar_hand_calculation() -> None:
    feature = calculate_solar_feature(
        candidate_id="KH-001",
        usable_area_m2=100,
        shading_factor=0.80,
        spatial_confidence=0.90,
        resource=RESOURCE,
        assumptions=ASSUMPTIONS,
    )

    # 100 * 0.70 / 5 = 14 kWp; 14 * 1800 * 0.8 * 0.86 * 0.96 = 16644.096 kWh
    assert feature.installable_capacity_kwp == 14.0
    assert feature.annual_yield_kwh == pytest.approx(16644.096)
    assert feature.loss_shading_fraction == pytest.approx(0.20)
    assert feature.solar_confidence == 0.8


def test_less_shading_cannot_increase_yield() -> None:
    common = {
        "candidate_id": "KH-001",
        "usable_area_m2": 100,
        "spatial_confidence": 0.9,
        "resource": RESOURCE,
        "assumptions": ASSUMPTIONS,
    }
    clear = calculate_solar_feature(shading_factor=0.90, **common)
    obstructed = calculate_solar_feature(shading_factor=0.50, **common)
    assert obstructed.annual_yield_kwh < clear.annual_yield_kwh


def test_missing_commercial_data_is_not_zero_filled() -> None:
    economic = calculate_economic_feature(
        installable_capacity_kwp=14,
        annual_yield_kwh=16644.096,
        economics=EconomicsInput(
            capex_inr_per_kwp=None,
            energy_value_inr_per_kwh=None,
            rent_inr_month=None,
            currency=None,
            source_id=None,
            source_date=None,
        ),
    )
    assert economic.estimated_cost_inr is None
    assert economic.annual_energy_value_inr is None
    assert economic.simple_payback_years is None


def test_registered_economic_values_calculate_payback() -> None:
    economic = calculate_economic_feature(
        installable_capacity_kwp=14,
        annual_yield_kwh=16644.096,
        economics=EconomicsInput(
            capex_inr_per_kwp=50_000,
            energy_value_inr_per_kwh=8,
            rent_inr_month=None,
            currency="INR",
            source_id="cost-fixture",
            source_date="2026-08-22",
        ),
    )
    assert economic.estimated_cost_inr == 700_000
    assert economic.annual_energy_value_inr == pytest.approx(133152.768)
    assert economic.simple_payback_years == pytest.approx(5.2571194014)
