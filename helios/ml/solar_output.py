"""Train and serve the solar-output challenger described by Siddiqui et al.

The paper predicts maximum PV voltage and current from weather and solar
measurements using linear regression and a two-layer ANN. This implementation
keeps only features available at inference time, encodes wind direction as a
circular value, and uses a chronological holdout to avoid future leakage.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import cos, pi, sin
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from helios.ml.contracts import (
    RegressionMetrics,
    SolarOutputPrediction,
    TrainingSummary,
    WeatherObservation,
)

MODEL_VERSION = "paper-siddiqui-2020-v1"
TARGET_COLUMNS = ("max_voltage_v", "max_current_a")
FEATURE_COLUMNS = (
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_m_s",
    "wind_direction_sin",
    "wind_direction_cos",
    "dew_point_c",
    "rain_mm",
    "rain_rate_mm_h",
    "atmospheric_pressure_hpa",
    "solar_irradiance_w_m2",
)


def _features(observation: WeatherObservation) -> list[float]:
    angle = observation.wind_direction_deg * pi / 180
    return [
        observation.temperature_c,
        observation.relative_humidity_pct,
        observation.wind_speed_m_s,
        sin(angle),
        cos(angle),
        observation.dew_point_c,
        observation.rain_mm,
        observation.rain_rate_mm_h,
        observation.atmospheric_pressure_hpa,
        observation.solar_irradiance_w_m2,
    ]


def _row(row: Mapping[str, Any]) -> tuple[list[float], list[float]]:
    weather = {name: row[name] for name in WeatherObservation.model_fields}
    observation = WeatherObservation.model_validate(weather)
    targets = [float(row[column]) for column in TARGET_COLUMNS]
    if any(value < 0 for value in targets):
        raise ValueError("Solar output targets must be non-negative")
    return _features(observation), targets


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> RegressionMetrics:
    return RegressionMetrics(
        voltage_rmse=float(mean_squared_error(actual[:, 0], predicted[:, 0]) ** 0.5),
        voltage_mae=float(mean_absolute_error(actual[:, 0], predicted[:, 0])),
        current_rmse=float(mean_squared_error(actual[:, 1], predicted[:, 1]) ** 0.5),
        current_mae=float(mean_absolute_error(actual[:, 1], predicted[:, 1])),
    )


@dataclass
class SolarOutputModel:
    estimator: Any
    model_name: str
    trained_at: str

    def predict(self, observation: WeatherObservation) -> SolarOutputPrediction:
        voltage, current = self.estimator.predict([_features(observation)])[0]
        voltage = max(0.0, float(voltage))
        current = max(0.0, float(current))
        return SolarOutputPrediction(
            max_voltage_v=voltage,
            max_current_a=current,
            estimated_peak_power_w=voltage * current,
            model_name=self.model_name,
            model_version=MODEL_VERSION,
        )

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "estimator": self.estimator,
                "model_name": self.model_name,
                "model_version": MODEL_VERSION,
                "trained_at": self.trained_at,
                "feature_columns": FEATURE_COLUMNS,
            },
            destination,
        )

    @classmethod
    def load(cls, path: str | Path) -> SolarOutputModel:
        artifact = joblib.load(path)
        if artifact.get("model_version") != MODEL_VERSION:
            raise ValueError("Unsupported solar-output model version")
        if tuple(artifact.get("feature_columns", ())) != FEATURE_COLUMNS:
            raise ValueError("Solar-output artifact has an incompatible feature schema")
        return cls(
            estimator=artifact["estimator"],
            model_name=artifact["model_name"],
            trained_at=artifact["trained_at"],
        )


def train_and_evaluate(
    rows: Iterable[Mapping[str, Any]], *, test_fraction: float = 0.2, random_state: int = 42
) -> tuple[SolarOutputModel, TrainingSummary]:
    """Train LR and the paper's 100x100 ANN, returning the best holdout model.

    Rows must already be in chronological order. The last ``test_fraction`` is
    held out, reflecting the time-dependent production use case.
    """
    if not 0.05 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.05 and 0.5")
    materialized = list(rows)
    if len(materialized) < 20:
        raise ValueError("At least 20 chronological observations are required")
    parsed = [_row(row) for row in materialized]
    x = np.asarray([item[0] for item in parsed], dtype=float)
    y = np.asarray([item[1] for item in parsed], dtype=float)
    split = int(len(parsed) * (1 - test_fraction))
    x_train, x_test = x[:split], x[split:]
    y_train, y_test = y[:split], y[split:]

    estimators = {
        "linear_regression": make_pipeline(StandardScaler(), LinearRegression()),
        "ann_100x100": make_pipeline(
            StandardScaler(),
            MLPRegressor(
                hidden_layer_sizes=(100, 100),
                learning_rate_init=0.01,
                tol=1e-4,
                max_iter=300,
                random_state=random_state,
                early_stopping=True,
            ),
        ),
    }
    results: dict[str, RegressionMetrics] = {}
    for name, estimator in estimators.items():
        estimator.fit(x_train, y_train)
        results[name] = _metrics(y_test, estimator.predict(x_test))
    selected_name = min(
        results,
        key=lambda name: results[name].voltage_rmse + results[name].current_rmse,
    )
    selected = estimators[selected_name]
    selected.fit(x, y)
    model = SolarOutputModel(
        estimator=selected,
        model_name=selected_name,
        trained_at=datetime.now(UTC).isoformat(),
    )
    return model, TrainingSummary(
        selected_model=selected_name,
        train_rows=len(x_train),
        test_rows=len(x_test),
        models=results,
    )


def estimate_annual_pv_yield_with_geometry(
    *,
    horizontal_area_m2: float,
    pitch_deg: float,
    azimuth_deg: float,
    irradiance_kwh_m2_year: float = 1701.2009,
    module_density_kwp_m2: float = 0.20,
    performance_ratio: float = 0.80,
    usable_fraction: float = 0.70,
) -> dict[str, float]:
    """Run a labelled screening simulation using explicit roof-plane inputs."""
    pitch = max(0.0, min(float(pitch_deg), 45.0))
    azimuth = float(azimuth_deg) % 360
    surface_area = horizontal_area_m2 / max(cos(pitch * pi / 180), 1e-6)
    usable_area = surface_area * usable_fraction
    azimuth_delta = abs(((azimuth - 180 + 180) % 360) - 180)
    orientation_factor = 1.0 - 0.30 * (azimuth_delta / 180)
    capacity_kwp = usable_area * module_density_kwp_m2
    annual_yield = capacity_kwp * irradiance_kwh_m2_year * performance_ratio * orientation_factor
    return {
        "horizontal_area_m2": round(horizontal_area_m2, 2),
        "surface_area_m2": round(surface_area, 2),
        "usable_area_m2": round(usable_area, 2),
        "estimated_capacity_kwp": round(capacity_kwp, 2),
        "annual_yield_kwh": round(annual_yield, 2),
        "orientation_factor": round(orientation_factor, 4),
        "area_gain_pct": round((surface_area / max(horizontal_area_m2, 1e-6) - 1) * 100, 2),
    }
