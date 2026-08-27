# Solar-output challenger

This optional model adapts Siddiqui et al., *Estimation of Solar Panel Output
based on Weather Parameters using Machine Learning Algorithms* (KICS Summer
2020). The paper compares linear regression with a two-hidden-layer ANN to
predict maximum panel voltage and current from hourly solar and weather data.

The implementation lives behind `helios.ml.SolarOutputModel` and does not alter
the deterministic MCDA ranking path. A downstream solar-yield adapter can load
the versioned artifact and use its voltage/current estimate as an additional
feature only after it passes local validation.

## CSV contract

The trainer expects a `timestamp` plus:

- `temperature_c`, `relative_humidity_pct`, `wind_speed_m_s`;
- `wind_direction_deg`, `dew_point_c`, `rain_mm`, `rain_rate_mm_h`;
- `atmospheric_pressure_hpa`, `solar_irradiance_w_m2`;
- targets `max_voltage_v` and `max_current_a`.

Input samples are sorted and averaged to hourly observations, matching the
paper. Wind direction is encoded with sine/cosine components. Unlike the paper's
reported random ratios, validation uses the final 20% of observations as a
chronological holdout to reduce future leakage.

## Training

```bash
python -m pip install -e ".[dev,ml]"
python scripts/train_solar_output.py data.csv artifacts/solar-output.joblib \
  --metrics artifacts/solar-output-metrics.json
```

Both linear regression and a `(100, 100)` ANN are evaluated with RMSE and MAE.
The model with the lowest combined voltage/current RMSE is retrained on all rows
and stored with its feature schema and model version.

Artifacts and source datasets must not be committed. Record the dataset URL,
license, checksum, date range and local validation metrics in a source manifest.
Only load trusted joblib artifacts because joblib deserialization can execute
code.

## Integration boundary

```python
from helios.ml import SolarOutputModel
from helios.ml.contracts import WeatherObservation

model = SolarOutputModel.load("artifacts/solar-output.joblib")
prediction = model.predict(WeatherObservation(...))
```

The calculated `estimated_peak_power_w` is `max_voltage_v * max_current_a`. It
is a model estimate, not annual energy yield. Do not replace
`CandidateMetrics.annual_yield_kwh` with it without a separately validated
temporal aggregation and PV-system model.

## Limitations

- The paper's Croft Close UK dataset is not redistributed here.
- Performance claims from the paper do not transfer to a new geography.
- Irradiance must be forecast or measured at inference time.
- Promotion into ranking remains governed by ADR 0003 and requires held-out
  improvement plus provenance and uncertainty reporting.
