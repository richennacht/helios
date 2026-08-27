import pytest

from helios.features.solar.resource_breakdown import (
    SolarResourceBreakdown,
    effective_irradiance_score,
)


def test_irradiance_is_decomposed_and_bounded():
    resource = SolarResourceBreakdown(
        ghi_kwh_m2_year=1800,
        dni_kwh_m2_year=1200,
        dhi_kwh_m2_year=600,
        seasonal_variability_fraction=0.2,
        temperature_loss_fraction=0.08,
        weather_confidence=0.9,
        source_ids=("nasa-power", "niwe"),
    )
    assert 0 < effective_irradiance_score(resource) <= 1


def test_irradiance_rejects_invalid_ghi():
    with pytest.raises(ValueError):
        SolarResourceBreakdown(0, None, None, None, None, 1, ("nasa-power",))
