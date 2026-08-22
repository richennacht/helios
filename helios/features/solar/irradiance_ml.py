"""Machine Learning models for Solar Panel Electrical Output vs. Irradiance Estimation.

Based on solar photovoltaic principles and empirical measurement guides:
- Photovoltaic power response to plane-of-array (POA) solar irradiance (W/m^2).
- Non-linear temperature derating (0.3% to 0.5% loss per °C above 25°C STC).
- Cell temperature dynamics from ambient temperature and irradiance (NOCT model).
- Low-irradiance non-linear efficiency drops (< 200 W/m^2).
- Inverter efficiency curves, shading obstruction, soiling, and degradation.
- Virtual Pyranometer inverse inference: reconstructing irradiance from panel output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from random import Random
from typing import Any, Final, Literal

import numpy as np

# Standard Test Conditions (STC)
STC_IRRADIANCE_W_M2: Final[float] = 1000.0
STC_TEMPERATURE_C: Final[float] = 25.0
DEFAULT_NOCT_C: Final[float] = 45.0
DEFAULT_TEMP_COEFF_PCT: Final[float] = -0.38
DEFAULT_INVERTER_EFFICIENCY: Final[float] = 0.96
DEFAULT_ANNUAL_DEGRADATION_PCT: Final[float] = 0.70


@dataclass(frozen=True)
class SolarModuleSpecs:
    """Photovoltaic panel specification parameters."""

    rated_power_stc_w: float = 380.0
    temp_coeff_pct_per_c: float = DEFAULT_TEMP_COEFF_PCT
    noct_c: float = DEFAULT_NOCT_C
    inverter_efficiency: float = DEFAULT_INVERTER_EFFICIENCY
    annual_degradation_pct: float = DEFAULT_ANNUAL_DEGRADATION_PCT
    module_area_m2: float = 1.95

    def __post_init__(self) -> None:
        if self.rated_power_stc_w <= 0:
            raise ValueError("rated_power_stc_w must be positive")
        if self.module_area_m2 <= 0:
            raise ValueError("module_area_m2 must be positive")
        if not (-1.5 <= self.temp_coeff_pct_per_c <= 0):
            raise ValueError("temp_coeff_pct_per_c must be in [-1.5, 0]")
        if not (0 < self.inverter_efficiency <= 1.0):
            raise ValueError("inverter_efficiency must be in (0, 1]")


DEFAULT_SPECS: Final[SolarModuleSpecs] = SolarModuleSpecs()


@dataclass(frozen=True)
class SolarObservation:
    """Environmental and electrical observation for a solar panel."""

    irradiance_w_m2: float
    ambient_temp_c: float
    cell_temp_c: float | None = None
    shading_factor: float = 1.0
    soiling_factor: float = 0.98
    panel_age_years: float = 0.0
    measured_power_w: float | None = None
    voltage_v: float | None = None
    current_a: float | None = None

    def effective_cell_temp(self, noct_c: float = DEFAULT_NOCT_C) -> float:
        """Return measured cell temperature or estimate it using the standard NOCT model."""
        if self.cell_temp_c is not None:
            return self.cell_temp_c
        # Standard NOCT formula: T_cell = T_amb + ((NOCT - 20) / 800) * G
        return self.ambient_temp_c + ((noct_c - 20.0) / 800.0) * max(0.0, self.irradiance_w_m2)


@dataclass(frozen=True)
class ModelEvaluationMetrics:
    """Model evaluation error metrics and confidence intervals."""

    model_name: str
    r2_score: float
    rmse_w: float
    mae_w: float
    mape_pct: float
    max_error_w: float
    rmse_ci_95: tuple[float, float]
    mae_ci_95: tuple[float, float]
    sample_size: int
    sliced_mae: dict[str, float] = field(default_factory=dict)


def compute_physical_stc_power(
    obs: SolarObservation,
    specs: SolarModuleSpecs | None = None,
) -> float:
    """Calculate deterministic physical baseline solar power output (Watts).

    P = P_stc * (G/1000) * [1 + (gamma/100)*(T_cell - 25)] * S * eta_inv * eta_soil * (1-d)^age
    """
    if specs is None:
        specs = DEFAULT_SPECS

    g = max(0.0, obs.irradiance_w_m2)
    if g <= 0.0 or obs.shading_factor <= 0.0:
        return 0.0

    cell_temp = obs.effective_cell_temp(specs.noct_c)
    temp_factor = 1.0 + (specs.temp_coeff_pct_per_c / 100.0) * (cell_temp - STC_TEMPERATURE_C)
    temp_factor = max(0.0, temp_factor)

    deg = (1.0 - (specs.annual_degradation_pct / 100.0)) ** max(0.0, obs.panel_age_years)

    power = (
        specs.rated_power_stc_w
        * (g / STC_IRRADIANCE_W_M2)
        * temp_factor
        * max(0.0, min(1.0, obs.shading_factor))
        * specs.inverter_efficiency
        * max(0.0, min(1.0, obs.soiling_factor))
        * deg
    )
    return float(max(0.0, power))


def generate_solar_dataset(
    n_samples: int = 2500,
    specs: SolarModuleSpecs | None = None,
    random_seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[SolarObservation]]:
    """Generate a realistic dataset of solar irradiance observations and actual outputs."""
    if specs is None:
        specs = DEFAULT_SPECS

    rng = Random(random_seed)

    observations: list[SolarObservation] = []
    features_list: list[list[float]] = []
    targets_list: list[float] = []

    for _ in range(n_samples):
        regime = rng.random()
        if regime < 0.15:
            g = rng.uniform(10.0, 200.0)
            amb_temp = rng.uniform(10.0, 25.0)
        elif regime < 0.50:
            g = rng.uniform(200.0, 650.0)
            amb_temp = rng.uniform(18.0, 32.0)
        else:
            g = rng.uniform(650.0, 1150.0)
            amb_temp = rng.uniform(22.0, 42.0)

        t_cell = amb_temp + ((specs.noct_c - 20.0) / 800.0) * g + rng.gauss(0.0, 1.2)
        shading = 1.0 if rng.random() > 0.20 else rng.uniform(0.4, 0.95)
        soiling = rng.uniform(0.94, 1.0)
        age = rng.uniform(0.0, 10.0)

        obs = SolarObservation(
            irradiance_w_m2=g,
            ambient_temp_c=amb_temp,
            cell_temp_c=t_cell,
            shading_factor=shading,
            soiling_factor=soiling,
            panel_age_years=age,
        )

        p_ideal = compute_physical_stc_power(obs, specs)

        # Real-world non-linear effects
        low_light_factor = 1.0
        if g < 250.0 and g > 0:
            low_light_factor = 1.0 - 0.12 * math.exp(-g / 80.0)

        p_dc = p_ideal * low_light_factor
        inv_load_ratio = p_dc / specs.rated_power_stc_w if specs.rated_power_stc_w else 0.0
        if inv_load_ratio < 0.10:
            inv_curve_factor = 0.88 + 1.2 * inv_load_ratio
        elif inv_load_ratio > 1.0:
            inv_curve_factor = 1.0 / inv_load_ratio
        else:
            inv_curve_factor = 1.0

        noise = rng.gauss(0.0, 1.8)
        actual_power = max(0.0, p_dc * inv_curve_factor + noise)

        obs_with_target = SolarObservation(
            irradiance_w_m2=g,
            ambient_temp_c=amb_temp,
            cell_temp_c=t_cell,
            shading_factor=shading,
            soiling_factor=soiling,
            panel_age_years=age,
            measured_power_w=round(actual_power, 2),
            voltage_v=round(35.0 - 0.12 * (t_cell - 25.0) + 0.005 * g, 2),
            current_a=round((actual_power / 35.0) if actual_power > 0 else 0.0, 2),
        )

        observations.append(obs_with_target)
        features_list.append([
            g,
            amb_temp,
            t_cell,
            shading,
            soiling,
            age,
            specs.rated_power_stc_w,
            specs.temp_coeff_pct_per_c,
            specs.inverter_efficiency,
        ])
        targets_list.append(actual_power)

    X = np.array(features_list, dtype=np.float64)
    y = np.array(targets_list, dtype=np.float64)
    return X, y, observations


class BaseSolarRegressor:
    """Base interface for Solar Irradiance ML and baseline models."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> BaseSolarRegressor:
        raise NotImplementedError

    def predict(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class PhysicalSTCModel(BaseSolarRegressor):
    """Pure physics-based single-diode STC benchmark model."""

    def __init__(self, specs: SolarModuleSpecs | None = None) -> None:
        self.specs = specs if specs is not None else DEFAULT_SPECS

    def fit(self, X: np.ndarray, y: np.ndarray) -> PhysicalSTCModel:
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        preds = []
        for row in X:
            obs = SolarObservation(
                irradiance_w_m2=row[0],
                ambient_temp_c=row[1],
                cell_temp_c=row[2],
                shading_factor=row[3],
                soiling_factor=row[4],
                panel_age_years=row[5],
            )
            p = compute_physical_stc_power(obs, self.specs)
            preds.append(p)
        return np.array(preds, dtype=np.float64)


class PolynomialRidgeSolarModel(BaseSolarRegressor):
    """L2-regularized Polynomial Ridge Regression with solar interaction features."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.weights: np.ndarray | None = None
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    def _transform_features(self, X: np.ndarray) -> np.ndarray:
        g = X[:, 0:1]
        t_cell = X[:, 2:3]
        shading = X[:, 3:4]
        soiling = X[:, 4:5]
        age = X[:, 5:6]

        g_norm = g / 1000.0
        temp_delta = (t_cell - 25.0) / 50.0

        features = [
            np.ones((X.shape[0], 1)),
            g_norm,
            temp_delta,
            shading,
            soiling,
            age / 10.0,
            g_norm * temp_delta,
            g_norm * shading,
            g_norm * soiling,
            g_norm ** 2,
            temp_delta ** 2,
        ]
        return np.hstack(features)

    def fit(self, X: np.ndarray, y: np.ndarray) -> PolynomialRidgeSolarModel:
        phi = self._transform_features(X)
        n_features = phi.shape[1]

        self.mean_ = np.mean(phi[:, 1:], axis=0)
        self.std_ = np.std(phi[:, 1:], axis=0)
        self.std_[self.std_ < 1e-8] = 1.0

        phi_scaled = np.copy(phi)
        phi_scaled[:, 1:] = (phi[:, 1:] - self.mean_) / self.std_

        reg_matrix = self.alpha * np.eye(n_features)
        reg_matrix[0, 0] = 0.0

        lhs = phi_scaled.T @ phi_scaled + reg_matrix
        rhs = phi_scaled.T @ y
        self.weights = np.linalg.solve(lhs, rhs)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.weights is None or self.mean_ is None or self.std_ is None:
            raise ValueError("Model must be fitted before predict")
        phi = self._transform_features(X)
        phi_scaled = np.copy(phi)
        phi_scaled[:, 1:] = (phi[:, 1:] - self.mean_) / self.std_
        preds = phi_scaled @ self.weights
        return np.clip(preds, a_min=0.0, a_max=None)


class GradientBoostingSolarModel(BaseSolarRegressor):
    """Ensemble Tree-based Gradient Boosting model for capturing non-linear PV behaviors."""

    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.1,
        max_depth: int = 4,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state
        self._model: Any = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> GradientBoostingSolarModel:
        try:
            from sklearn.ensemble import GradientBoostingRegressor

            self._model = GradientBoostingRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                random_state=self.random_state,
                loss="squared_error",
            )
            self._model.fit(X, y)
        except ImportError:
            poly = PolynomialRidgeSolarModel(alpha=0.5)
            poly.fit(X, y)
            self._model = poly
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise ValueError("Model must be fitted before predict")
        preds = self._model.predict(X)
        return np.clip(preds, a_min=0.0, a_max=None)


class PhysicsInformedSolarRegressor(BaseSolarRegressor):
    """Hybrid Physics-Informed ML Regressor.

    Combines physical single-diode STC prior with a trained gradient-boosted residual corrector:
        P_final = max(0, P_physical(X) + ML_residual(X))
    """

    def __init__(
        self,
        specs: SolarModuleSpecs | None = None,
        residual_model_type: Literal["ridge", "gbr"] = "gbr",
        random_state: int = 42,
    ) -> None:
        self.specs = specs if specs is not None else DEFAULT_SPECS
        self.residual_model_type = residual_model_type
        self.random_state = random_state
        self.physical_model = PhysicalSTCModel(self.specs)
        self.residual_model: BaseSolarRegressor | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> PhysicsInformedSolarRegressor:
        p_phys = self.physical_model.predict(X)
        residuals = y - p_phys

        if self.residual_model_type == "gbr":
            self.residual_model = GradientBoostingSolarModel(
                n_estimators=80,
                learning_rate=0.08,
                max_depth=3,
                random_state=self.random_state,
            )
        else:
            self.residual_model = PolynomialRidgeSolarModel(alpha=1.0)

        self.residual_model.fit(X, residuals)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.residual_model is None:
            raise ValueError("Model must be fitted before predict")
        p_phys = self.physical_model.predict(X)
        res_pred = self.residual_model.predict(X)
        y_final = p_phys + res_pred
        return np.clip(y_final, a_min=0.0, a_max=None)


class VirtualPyranometerEstimator:
    """Inverse Physics-Informed ML Model estimating incident Solar Irradiance (W/m^2)."""

    def __init__(self, specs: SolarModuleSpecs | None = None) -> None:
        self.specs = specs if specs is not None else DEFAULT_SPECS
        self._residual_model: Any = None

    def _physical_inverse_g(
        self,
        power_w: float,
        cell_temp_c: float,
        shading_factor: float,
        soiling_factor: float = 0.98,
        panel_age_years: float = 0.0,
    ) -> float:
        """Analytical inversion of physical STC equation."""
        if power_w <= 0.0 or shading_factor <= 0.0:
            return 0.0
        delta_t = cell_temp_c - STC_TEMPERATURE_C
        temp_derate = 1.0 + (self.specs.temp_coeff_pct_per_c / 100.0) * delta_t
        temp_derate = max(0.05, temp_derate)
        deg_factor = (
            (1.0 - (self.specs.annual_degradation_pct / 100.0)) ** max(0.0, panel_age_years)
        )
        denom = (
            self.specs.rated_power_stc_w
            * temp_derate
            * shading_factor
            * self.specs.inverter_efficiency
            * soiling_factor
            * deg_factor
        )
        if denom <= 0:
            return 0.0
        return (power_w / denom) * STC_IRRADIANCE_W_M2

    def fit(self, observations: list[SolarObservation]) -> VirtualPyranometerEstimator:
        """Fit inverse relationship using physical prior + ML residual."""
        feat_rows = []
        residuals = []

        for obs in observations:
            if obs.measured_power_w is None or obs.measured_power_w <= 0:
                continue
            t_cell = obs.effective_cell_temp(self.specs.noct_c)
            g_phys = self._physical_inverse_g(
                obs.measured_power_w,
                t_cell,
                obs.shading_factor,
                obs.soiling_factor,
                obs.panel_age_years,
            )
            g_true = obs.irradiance_w_m2
            res = g_true - g_phys

            p_norm = obs.measured_power_w / self.specs.rated_power_stc_w
            t_delta = (t_cell - 25.0) / 50.0
            feat_rows.append([p_norm, t_delta, obs.shading_factor, g_phys / 1000.0])
            residuals.append(res)

        if feat_rows:
            X_mat = np.array(feat_rows, dtype=np.float64)
            y_res = np.array(residuals, dtype=np.float64)
            try:
                from sklearn.ensemble import GradientBoostingRegressor

                self._residual_model = GradientBoostingRegressor(
                    n_estimators=50,
                    learning_rate=0.08,
                    max_depth=3,
                    random_state=42,
                )
                self._residual_model.fit(X_mat, y_res)
            except ImportError:
                self._residual_model = None

        return self

    def estimate_irradiance(
        self,
        measured_power_w: float,
        ambient_temp_c: float,
        cell_temp_c: float | None = None,
        shading_factor: float = 1.0,
        soiling_factor: float = 0.98,
        panel_age_years: float = 0.0,
    ) -> float:
        """Estimate solar irradiance in W/m^2 from measured electrical power and temperature."""
        if measured_power_w <= 0.0 or shading_factor <= 0.0:
            return 0.0

        t_cell = cell_temp_c if cell_temp_c is not None else (ambient_temp_c + 15.0)
        g_phys = self._physical_inverse_g(
            measured_power_w,
            t_cell,
            shading_factor,
            soiling_factor,
            panel_age_years,
        )

        if self._residual_model is not None:
            p_norm = measured_power_w / self.specs.rated_power_stc_w
            t_delta = (t_cell - 25.0) / 50.0
            X_q = np.array([[p_norm, t_delta, shading_factor, g_phys / 1000.0]])
            res_pred = self._residual_model.predict(X_q)[0]
            g_final = g_phys + res_pred
        else:
            g_final = g_phys

        return float(max(0.0, g_final))


def evaluate_solar_model(
    name: str,
    model: BaseSolarRegressor,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_bootstrap: int = 500,
    random_seed: int = 42,
) -> ModelEvaluationMetrics:
    """Evaluate a solar output prediction model with error metrics and bootstrap CIs."""
    y_pred = model.predict(X_test)
    n = len(y_test)

    errors = y_pred - y_test
    abs_errors = np.abs(errors)
    sq_errors = errors ** 2

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(sq_errors)))
    max_err = float(np.max(abs_errors))

    valid_mask = y_test > 5.0
    if np.any(valid_mask):
        mape = float(np.mean(np.abs(errors[valid_mask] / y_test[valid_mask])) * 100.0)
    else:
        mape = 0.0

    ss_tot = float(np.sum((y_test - np.mean(y_test)) ** 2))
    ss_res = float(np.sum(sq_errors))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    rng = np.random.default_rng(random_seed)
    boot_rmse: list[float] = []
    boot_mae: list[float] = []

    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        boot_mae.append(float(np.mean(np.abs(y_pred[idx] - y_test[idx]))))
        boot_rmse.append(float(np.sqrt(np.mean((y_pred[idx] - y_test[idx]) ** 2))))

    rmse_ci = (float(np.percentile(boot_rmse, 2.5)), float(np.percentile(boot_rmse, 97.5)))
    mae_ci = (float(np.percentile(boot_mae, 2.5)), float(np.percentile(boot_mae, 97.5)))

    g_vals = X_test[:, 0]
    t_cell_vals = X_test[:, 2]

    sliced: dict[str, float] = {}

    low_g = g_vals < 300.0
    mid_g = (g_vals >= 300.0) & (g_vals <= 700.0)
    high_g = g_vals > 700.0

    sliced["mae_low_irradiance (<300 W/m2)"] = (
        float(np.mean(abs_errors[low_g])) if np.any(low_g) else 0.0
    )
    sliced["mae_mid_irradiance (300-700 W/m2)"] = (
        float(np.mean(abs_errors[mid_g])) if np.any(mid_g) else 0.0
    )
    sliced["mae_high_irradiance (>700 W/m2)"] = (
        float(np.mean(abs_errors[high_g])) if np.any(high_g) else 0.0
    )

    cool_t = t_cell_vals < 25.0
    mod_t = (t_cell_vals >= 25.0) & (t_cell_vals <= 45.0)
    hot_t = t_cell_vals > 45.0

    sliced["mae_cool_temp (<25 C)"] = (
        float(np.mean(abs_errors[cool_t])) if np.any(cool_t) else 0.0
    )
    sliced["mae_mod_temp (25-45 C)"] = (
        float(np.mean(abs_errors[mod_t])) if np.any(mod_t) else 0.0
    )
    sliced["mae_hot_temp (>45 C)"] = (
        float(np.mean(abs_errors[hot_t])) if np.any(hot_t) else 0.0
    )

    return ModelEvaluationMetrics(
        model_name=name,
        r2_score=round(r2, 4),
        rmse_w=round(rmse, 3),
        mae_w=round(mae, 3),
        mape_pct=round(mape, 2),
        max_error_w=round(max_err, 3),
        rmse_ci_95=(round(rmse_ci[0], 3), round(rmse_ci[1], 3)),
        mae_ci_95=(round(mae_ci[0], 3), round(mae_ci[1], 3)),
        sample_size=n,
        sliced_mae=sliced,
    )
