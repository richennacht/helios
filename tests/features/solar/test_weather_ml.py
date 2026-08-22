"""Unit tests for the Weather-ML Solar Output Estimation Model."""

import pytest

from helios.features.solar.weather_ml import (
    WeatherMLSolarAssumptions,
    WeatherMLSolarModel,
    WeatherParameters,
    calculate_weather_ml_solar_feature,
)


@pytest.fixture
def baseline_weather() -> WeatherParameters:
    return WeatherParameters(
        poa_irradiance_kwh_m2=1850.0,
        ambient_temperature_c=28.0,
        relative_humidity_pct=65.0,
        wind_speed_m_s=3.0,
        resource_period="2023-climatology",
        source_id="nasa-power-kharghar",
        weather_confidence=0.90,
    )


@pytest.fixture
def baseline_assumptions() -> WeatherMLSolarAssumptions:
    return WeatherMLSolarAssumptions(
        version="weather-ml-2026-v1",
        usable_area_factor=0.70,
        area_per_kwp_m2=6.0,
        inverter_efficiency=0.96,
        temp_coefficient_pct_per_c=-0.38,
        noct_c=45.0,
    )


def test_weather_ml_basic_calculation(baseline_weather, baseline_assumptions):
    feature = calculate_weather_ml_solar_feature(
        candidate_id="KHAR_TEST_001",
        usable_area_m2=120.0,
        shading_factor=0.95,
        spatial_confidence=0.88,
        weather=baseline_weather,
        assumptions=baseline_assumptions,
    )

    expected_kwp = 120.0 * 0.70 / 6.0  # 14.0 kWp
    assert feature.candidate_id == "KHAR_TEST_001"
    assert feature.usable_area_m2 == 120.0
    assert pytest.approx(feature.installable_capacity_kwp) == expected_kwp
    assert feature.annual_yield_kwh > 15_000.0
    assert feature.yield_per_kwp_kwh > 1_000.0
    assert 0.80 <= feature.thermal_derate_factor <= 1.05
    assert 0.90 <= feature.humidity_derate_factor <= 1.0
    assert feature.solar_confidence == 0.88
    assert feature.assumption_version == "weather-ml-2026-v1"


def test_weather_ml_irradiance_monotonicity(baseline_assumptions):
    model = WeatherMLSolarModel(assumptions=baseline_assumptions)

    low_sun = WeatherParameters(
        poa_irradiance_kwh_m2=1200.0,
        ambient_temperature_c=25.0,
        relative_humidity_pct=50.0,
        wind_speed_m_s=2.0,
    )
    high_sun = WeatherParameters(
        poa_irradiance_kwh_m2=2000.0,
        ambient_temperature_c=25.0,
        relative_humidity_pct=50.0,
        wind_speed_m_s=2.0,
    )

    feat_low = model.predict_yield(
        candidate_id="roof-1",
        usable_area_m2=100.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=low_sun,
    )
    feat_high = model.predict_yield(
        candidate_id="roof-1",
        usable_area_m2=100.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=high_sun,
    )

    assert feat_high.annual_yield_kwh > feat_low.annual_yield_kwh


def test_weather_ml_temperature_sensitivity(baseline_assumptions):
    model = WeatherMLSolarModel(assumptions=baseline_assumptions)

    cool_weather = WeatherParameters(
        poa_irradiance_kwh_m2=1800.0,
        ambient_temperature_c=15.0,
        relative_humidity_pct=50.0,
        wind_speed_m_s=2.0,
    )
    hot_weather = WeatherParameters(
        poa_irradiance_kwh_m2=1800.0,
        ambient_temperature_c=42.0,
        relative_humidity_pct=50.0,
        wind_speed_m_s=2.0,
    )

    feat_cool = model.predict_yield(
        candidate_id="roof-1",
        usable_area_m2=100.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=cool_weather,
    )
    feat_hot = model.predict_yield(
        candidate_id="roof-1",
        usable_area_m2=100.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=hot_weather,
    )

    # Cooler temperatures yield higher efficiency and lower cell temp
    assert feat_cool.estimated_cell_temp_c < feat_hot.estimated_cell_temp_c
    assert feat_cool.thermal_derate_factor > feat_hot.thermal_derate_factor
    assert feat_cool.annual_yield_kwh > feat_hot.annual_yield_kwh


def test_weather_ml_wind_cooling_benefit(baseline_assumptions):
    model = WeatherMLSolarModel(assumptions=baseline_assumptions)

    calm_wind = WeatherParameters(
        poa_irradiance_kwh_m2=1800.0,
        ambient_temperature_c=35.0,
        relative_humidity_pct=50.0,
        wind_speed_m_s=0.5,
    )
    strong_wind = WeatherParameters(
        poa_irradiance_kwh_m2=1800.0,
        ambient_temperature_c=35.0,
        relative_humidity_pct=50.0,
        wind_speed_m_s=8.0,
    )

    feat_calm = model.predict_yield(
        candidate_id="roof-1",
        usable_area_m2=100.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=calm_wind,
    )
    feat_wind = model.predict_yield(
        candidate_id="roof-1",
        usable_area_m2=100.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=strong_wind,
    )

    # Strong wind cools cells and increases generation
    assert feat_wind.estimated_cell_temp_c < feat_calm.estimated_cell_temp_c
    assert feat_wind.annual_yield_kwh > feat_calm.annual_yield_kwh
    assert feat_wind.wind_cooling_gain_pct > feat_calm.wind_cooling_gain_pct


def test_weather_ml_zero_usable_area(baseline_weather, baseline_assumptions):
    feature = calculate_weather_ml_solar_feature(
        candidate_id="KHAR_EMPTY",
        usable_area_m2=0.0,
        shading_factor=1.0,
        spatial_confidence=0.9,
        weather=baseline_weather,
        assumptions=baseline_assumptions,
    )
    assert feature.installable_capacity_kwp == 0.0
    assert feature.annual_yield_kwh == 0.0
    assert feature.yield_per_kwp_kwh == 0.0


def test_weather_ml_invalid_inputs(baseline_weather):
    model = WeatherMLSolarModel()

    with pytest.raises(ValueError, match="candidate_id is required"):
        model.predict_yield(
            candidate_id="",
            usable_area_m2=100.0,
            shading_factor=1.0,
            spatial_confidence=0.9,
            weather=baseline_weather,
        )

    with pytest.raises(ValueError, match="usable_area_m2 must be non-negative"):
        model.predict_yield(
            candidate_id="roof-1",
            usable_area_m2=-10.0,
            shading_factor=1.0,
            spatial_confidence=0.9,
            weather=baseline_weather,
        )

    with pytest.raises(ValueError, match="shading_factor and spatial_confidence"):
        model.predict_yield(
            candidate_id="roof-1",
            usable_area_m2=100.0,
            shading_factor=1.5,
            spatial_confidence=0.9,
            weather=baseline_weather,
        )


def test_weather_ml_model_types(baseline_weather, baseline_assumptions):
    for m_type in ("random_forest_ensemble", "gradient_boosting", "physics_ml_hybrid"):
        feat = calculate_weather_ml_solar_feature(
            candidate_id="roof-test",
            usable_area_m2=100.0,
            shading_factor=0.9,
            spatial_confidence=0.85,
            weather=baseline_weather,
            assumptions=baseline_assumptions,
            model_type=m_type,
        )
        assert feat.annual_yield_kwh > 0.0
        assert feat.ml_model_type == m_type
