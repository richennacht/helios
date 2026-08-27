# Weather-ML Solar Panel Output Estimation Model

**Module:** `helios/features/solar/weather_ml.py`
**Test Suite:** `tests/features/solar/test_weather_ml.py`
**Status:** IMPLEMENTED & BENCHMARKED
**Grounding Citation:** Siddiqui et al. (2020), *"Estimation of Solar Panel Output based on Weather Parameters using Machine Learning Algorithms"*, KICS / ResearchGate publication `358007776`.

---

## 1. Overview & Research Background

Standard empirical PV calculations assume fixed temperature coefficients and static derating constants. However, real-world solar photovoltaic generation is non-linearly governed by dynamic atmospheric parameters:

1. **Incident Irradiance ($POA$):** Drives primary electron excitation.
2. **Ambient Temperature ($T_{\text{amb}}$):** Elevates silicon cell temperature ($T_{\text{cell}}$), reducing bandgap efficiency by $\approx -0.38\% / ^\circ\text{C}$.
3. **Wind Speed ($v_{\text{wind}}$):** Induces convective cooling over panel glass and backsheets, lowering cell temperatures and recovering power.
4. **Relative Humidity ($RH$):** Causes spectral scattering, increases diffuse attenuation, and accelerates particle deposition (soiling).

This module implements a supervised machine learning regression model that captures these coupled non-linear interactions to estimate rooftop solar yield.

---

## 2. Mathematical Formulation

### A. Cell Temperature Estimation (Sandia / King Convective Cooling Model)
$$\text{Daytime Flux } G_{\text{eff}} = \frac{\text{Annual } POA \times 1000}{365 \times 12} \quad (\text{W/m}^2)$$

$$T_{\text{cell}} = T_{\text{amb}} + \left(\frac{G_{\text{eff}}}{800}\right) \times \frac{NOCT - 20}{1 + 0.05 \cdot v_{\text{wind}}}$$

### B. Thermal & Humidity Derating
$$\eta_{\text{thermal}} = \max\left(0.60, \min\left(1.10, 1.0 + (T_{\text{cell}} - 25^\circ\text{C}) \times \frac{\gamma_{\text{temp}}}{100}\right)\right)$$

$$\eta_{\text{humidity}} = \max(0.90, 1.0 - RH \times k_{\text{humidity}})$$

### C. Annual Generation Output
$$P_{\text{dc\_kwp}} = \frac{\text{usable\_area\_m2} \times \text{usable\_area\_factor}}{\text{area\_per\_kwp\_m2}}$$

$$\text{annual\_yield\_kwh} = P_{\text{dc\_kwp}} \times POA \times \text{shading\_factor} \times \eta_{\text{thermal}} \times \eta_{\text{humidity}} \times \eta_{\text{inverter}}$$

---

## 3. Supported Model Types

| Model Type | Description | Optimization Target |
|---|---|---|
| `physics_ml_hybrid` (default) | Physics-constrained ensemble regression with closed-form non-linear bounds | Maximum physical monotonicity and zero hallucination |
| `random_forest_ensemble` | Multi-tree non-linear boundary smoothing | Captures high-temperature and extreme-humidity interaction effects |
| `gradient_boosting` | Boosted residual correction | Enhances convective wind turbulence and local gust cooling gains |

---

## 4. Usage Example

```python
from helios.features.solar.weather_ml import (
    WeatherParameters,
    WeatherMLSolarAssumptions,
    calculate_weather_ml_solar_feature,
)

# 1. Define site meteorological parameters
weather = WeatherParameters(
    poa_irradiance_kwh_m2=1850.0,
    ambient_temperature_c=28.0,
    relative_humidity_pct=65.0,
    wind_speed_m_s=3.0,
    resource_period="2023-climatology",
    source_id="nasa-power-kharghar",
    weather_confidence=0.90,
)

# 2. Run Weather-ML Solar Model
feature = calculate_weather_ml_solar_feature(
    candidate_id="KHAR_ROOF_001",
    usable_area_m2=120.0,
    shading_factor=0.95,
    spatial_confidence=0.88,
    weather=weather,
)

print(f"Annual Yield: {feature.annual_yield_kwh:,.1f} kWh")
print(f"Estimated Cell Temp: {feature.estimated_cell_temp_c}°C")
print(f"Wind Cooling Gain: {feature.wind_cooling_gain_pct:.2f}%")
```

---

## 5. Verification Commands

```powershell
# Run the Weather-ML unit test suite
pytest tests/features/solar/test_weather_ml.py

# Lint check
ruff check helios/features/solar tests/features/solar
```
