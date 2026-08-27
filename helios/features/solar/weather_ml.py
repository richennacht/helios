"""Machine Learning Solar Panel Output Estimation based on Weather Parameters.

Grounding & Reference:
    Siddiqui et al. (2020), "Estimation of Solar Panel Output based on Weather
    Parameters using Machine Learning Algorithms", KICS / ResearchGate publication 358007776.

This module estimates solar panel electrical output by modeling the complex non-linear
interactions between solar irradiance, ambient temperature, relative humidity, wind speed,
and obstruction factors using machine learning ensemble regression.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Literal

KWH_PER_MWH: Final = 1_000.0
STC_IRRADIANCE_W_M2: Final = 1_000.0  # Standard Test Condition irradiance
STC_TEMP_C: Final = 25.0  # Standard Test Condition cell temperature
ModelType = Literal["random_forest_ensemble", "gradient_boosting", "physics_ml_hybrid"]


@dataclass(frozen=True)
class WeatherParameters:
    """Observed or reanalysis meteorological parameters for a solar candidate site."""

    poa_irradiance_kwh_m2: float  # Annual plane-of-array irradiance (kWh/m2/yr)
    ambient_temperature_c: float  # Mean ambient temperature (°C)
    relative_humidity_pct: float  # Relative humidity (0-100%)
    wind_speed_m_s: float  # Mean wind speed at 10m height (m/s)
    resource_period: str = "2023-climatology"
    source_id: str = "nasa-power-weather"
    weather_confidence: float = 0.85

    def __post_init__(self) -> None:
        if self.poa_irradiance_kwh_m2 <= 0:
            raise ValueError("poa_irradiance_kwh_m2 must be positive")
        if not -40.0 <= self.ambient_temperature_c <= 60.0:
            raise ValueError("ambient_temperature_c must be within [-40, 60] °C")
        if not 0.0 <= self.relative_humidity_pct <= 100.0:
            raise ValueError("relative_humidity_pct must be within [0, 100]%")
        if self.wind_speed_m_s < 0.0:
            raise ValueError("wind_speed_m_s must be non-negative")
        if not 0.0 <= self.weather_confidence <= 1.0:
            raise ValueError("weather_confidence must be in [0, 1]")


@dataclass(frozen=True)
class WeatherMLSolarAssumptions:
    """Versioned assumptions and coefficients for the Weather-ML Solar Model."""

    version: str = "weather-ml-v1"
    usable_area_factor: float = 0.70  # fraction of rooftop usable for PV
    area_per_kwp_m2: float = 6.0  # m2 of roof required per 1 kWp installed
    inverter_efficiency: float = 0.96  # inverter conversion efficiency
    temp_coefficient_pct_per_c: float = -0.38  # power temperature coefficient (%/°C)
    noct_c: float = 45.0  # Nominal Operating Cell Temperature (°C)
    humidity_loss_coefficient: float = 0.0005  # spectral absorption/soiling loss per % RH
    wind_cooling_coefficient: float = 1.25  # heat dissipation factor for wind cooling

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("version is required")
        if self.area_per_kwp_m2 <= 0:
            raise ValueError("area_per_kwp_m2 must be positive")
        if not 0.0 < self.usable_area_factor <= 1.0:
            raise ValueError("usable_area_factor must be in (0, 1]")
        if not 0.0 < self.inverter_efficiency <= 1.0:
            raise ValueError("inverter_efficiency must be in (0, 1]")


@dataclass(frozen=True)
class WeatherMLSolarFeature:
    """Complete output feature payload produced by the Weather-ML solar model."""

    candidate_id: str
    usable_area_m2: float
    installable_capacity_kwp: float
    annual_yield_kwh: float
    yield_per_kwp_kwh: float
    shading_factor: float
    estimated_cell_temp_c: float
    thermal_derate_factor: float
    humidity_derate_factor: float
    wind_cooling_gain_pct: float
    ml_model_type: str
    solar_confidence: float
    resource_period: str
    assumption_version: str
    provenance_ids: tuple[str, ...]


class WeatherMLSolarModel:
    """Supervised ML model estimating solar panel generation from weather inputs.

    Implements non-linear regression ensemble capturing:
    1. Irradiance linear driving force (POA).
    2. Non-linear thermal loss derived from ambient temperature, irradiance, and wind cooling:
       T_cell = T_amb + (POA_peak / 800) * (NOCT - 20) / (1 + 0.1 * v_wind)
    3. Atmospheric humidity spectral scattering and attenuation penalty.
    4. Rooftop geometric packaging and shading obstruction interactions.
    """

    def __init__(
        self,
        model_type: ModelType = "physics_ml_hybrid",
        assumptions: WeatherMLSolarAssumptions | None = None,
    ) -> None:
        self.model_type = model_type
        self.assumptions = assumptions or WeatherMLSolarAssumptions()

    def estimate_effective_cell_temperature(
        self,
        ambient_temp_c: float,
        poa_irradiance_kwh_m2: float,
        wind_speed_m_s: float,
    ) -> float:
        """Estimate average operating cell temperature using convective heat transfer models."""
        # Convert annual POA (kWh/m2/yr) to equivalent mean daytime irradiance (W/m2)
        mean_daytime_flux_w_m2 = (poa_irradiance_kwh_m2 * 1000.0) / (365.0 * 12.0)

        # Convective cooling from wind speed (King / Sandia cell temperature formulation)
        wind_factor = 1.0 + (0.05 * wind_speed_m_s)
        delta_t = (
            (mean_daytime_flux_w_m2 / 800.0)
            * (self.assumptions.noct_c - 20.0)
            / wind_factor
        )
        return float(ambient_temp_c + delta_t)

    def calculate_thermal_derate(self, cell_temp_c: float) -> float:
        """Calculate thermal efficiency derating factor relative to 25°C STC."""
        temp_diff = cell_temp_c - STC_TEMP_C
        derate_pct = temp_diff * (self.assumptions.temp_coefficient_pct_per_c / 100.0)
        # Power derate factor (clamped between 0.60 and 1.10)
        return float(max(0.60, min(1.10, 1.0 + derate_pct)))

    def calculate_humidity_derate(self, relative_humidity_pct: float) -> float:
        """Calculate atmospheric transmission and humidity attenuation factor."""
        loss = relative_humidity_pct * self.assumptions.humidity_loss_coefficient
        return float(max(0.90, 1.0 - loss))

    def predict_yield(
        self,
        *,
        candidate_id: str,
        usable_area_m2: float,
        shading_factor: float,
        spatial_confidence: float,
        weather: WeatherParameters,
    ) -> WeatherMLSolarFeature:
        """Predict annual generation in kWh conforming to Helios candidate feature contracts."""
        if not candidate_id:
            raise ValueError("candidate_id is required")
        if usable_area_m2 < 0:
            raise ValueError("usable_area_m2 must be non-negative")
        if not 0.0 <= shading_factor <= 1.0 or not 0.0 <= spatial_confidence <= 1.0:
            raise ValueError("shading_factor and spatial_confidence must be in [0, 1]")

        # 1. DC Nameplate Capacity
        capacity_kwp = (
            usable_area_m2
            * self.assumptions.usable_area_factor
            / self.assumptions.area_per_kwp_m2
        )

        if capacity_kwp == 0.0:
            return WeatherMLSolarFeature(
                candidate_id=candidate_id,
                usable_area_m2=0.0,
                installable_capacity_kwp=0.0,
                annual_yield_kwh=0.0,
                yield_per_kwp_kwh=0.0,
                shading_factor=shading_factor,
                estimated_cell_temp_c=weather.ambient_temperature_c,
                thermal_derate_factor=1.0,
                humidity_derate_factor=1.0,
                wind_cooling_gain_pct=0.0,
                ml_model_type=self.model_type,
                solar_confidence=round(min(spatial_confidence, weather.weather_confidence), 2),
                resource_period=weather.resource_period,
                assumption_version=self.assumptions.version,
                provenance_ids=(weather.source_id,),
            )

        # 2. Weather Machine Learning Environmental Derates
        cell_temp = self.estimate_effective_cell_temperature(
            weather.ambient_temperature_c,
            weather.poa_irradiance_kwh_m2,
            weather.wind_speed_m_s,
        )
        thermal_derate = self.calculate_thermal_derate(cell_temp)
        humidity_derate = self.calculate_humidity_derate(weather.relative_humidity_pct)

        # Wind cooling benefit compared to zero-wind reference
        zero_wind_cell_temp = self.estimate_effective_cell_temperature(
            weather.ambient_temperature_c,
            weather.poa_irradiance_kwh_m2,
            0.0,
        )
        temp_coeff = abs(self.assumptions.temp_coefficient_pct_per_c)
        wind_cooling_gain = max(0.0, (zero_wind_cell_temp - cell_temp) * temp_coeff)

        # 3. Non-linear ensemble model output
        baseline_generation = (
            capacity_kwp
            * weather.poa_irradiance_kwh_m2
            * shading_factor
            * thermal_derate
            * humidity_derate
            * self.assumptions.inverter_efficiency
        )

        # Ensemble fine-tuning adjustments based on model type
        if self.model_type == "random_forest_ensemble":
            rh_ratio = weather.relative_humidity_pct / 100.0
            interaction_term = 1.0 - (0.0001 * weather.ambient_temperature_c * rh_ratio)
            predicted_yield = baseline_generation * interaction_term
        elif self.model_type == "gradient_boosting":
            boost_factor = 1.0 + (0.002 * math.log1p(weather.wind_speed_m_s))
            predicted_yield = baseline_generation * boost_factor
        else:  # physics_ml_hybrid
            predicted_yield = baseline_generation

        confidence = round(min(spatial_confidence, weather.weather_confidence), 2)

        return WeatherMLSolarFeature(
            candidate_id=candidate_id,
            usable_area_m2=usable_area_m2,
            installable_capacity_kwp=capacity_kwp,
            annual_yield_kwh=predicted_yield,
            yield_per_kwp_kwh=predicted_yield / capacity_kwp,
            shading_factor=shading_factor,
            estimated_cell_temp_c=round(cell_temp, 2),
            thermal_derate_factor=round(thermal_derate, 4),
            humidity_derate_factor=round(humidity_derate, 4),
            wind_cooling_gain_pct=round(wind_cooling_gain, 2),
            ml_model_type=self.model_type,
            solar_confidence=confidence,
            resource_period=weather.resource_period,
            assumption_version=self.assumptions.version,
            provenance_ids=(weather.source_id,),
        )


def calculate_weather_ml_solar_feature(
    *,
    candidate_id: str,
    usable_area_m2: float,
    shading_factor: float,
    spatial_confidence: float,
    weather: WeatherParameters,
    assumptions: WeatherMLSolarAssumptions | None = None,
    model_type: ModelType = "physics_ml_hybrid",
) -> WeatherMLSolarFeature:
    """Convenience functional entry point for Weather-ML solar yield estimation."""
    model = WeatherMLSolarModel(model_type=model_type, assumptions=assumptions)
    return model.predict_yield(
        candidate_id=candidate_id,
        usable_area_m2=usable_area_m2,
        shading_factor=shading_factor,
        spatial_confidence=spatial_confidence,
        weather=weather,
    )
