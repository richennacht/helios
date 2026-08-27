from math import sin

import pytest

from helios.ml.contracts import WeatherObservation
from helios.ml.solar_output import SolarOutputModel, train_and_evaluate


def _rows(count: int = 80) -> list[dict]:
    rows = []
    for index in range(count):
        irradiance = max(0.0, 800 * sin(index / 12))
        temperature = 18 + index * 0.05
        rows.append(
            {
                "temperature_c": temperature,
                "relative_humidity_pct": 60 - index * 0.1,
                "wind_speed_m_s": 2 + index % 4,
                "wind_direction_deg": (index * 17) % 360,
                "dew_point_c": 10,
                "rain_mm": 0,
                "rain_rate_mm_h": 0,
                "atmospheric_pressure_hpa": 1012,
                "solar_irradiance_w_m2": irradiance,
                "max_voltage_v": 20 + irradiance * 0.02 - temperature * 0.03,
                "max_current_a": 0.2 + irradiance * 0.01,
            }
        )
    return rows


def test_train_predict_and_round_trip(tmp_path) -> None:
    model, summary = train_and_evaluate(_rows())
    assert summary.train_rows == 64
    assert summary.test_rows == 16
    assert set(summary.models) == {"linear_regression", "ann_100x100"}

    weather_row = _rows()[30]
    observation = WeatherObservation.model_validate(
        {name: weather_row[name] for name in WeatherObservation.model_fields}
    )
    prediction = model.predict(observation)
    assert prediction.max_voltage_v > 0
    assert prediction.max_current_a > 0
    assert prediction.estimated_peak_power_w == pytest.approx(
        prediction.max_voltage_v * prediction.max_current_a
    )

    artifact = tmp_path / "solar-output.joblib"
    model.save(artifact)
    restored = SolarOutputModel.load(artifact)
    assert restored.predict(observation).max_voltage_v == pytest.approx(prediction.max_voltage_v)


def test_training_rejects_tiny_dataset() -> None:
    with pytest.raises(ValueError, match="At least 20"):
        train_and_evaluate(_rows(10))
