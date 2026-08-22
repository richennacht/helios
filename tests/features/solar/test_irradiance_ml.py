"""Unit and integration tests for Solar Panel Output vs Irradiance Machine Learning models."""

from __future__ import annotations

import numpy as np
import pytest

from helios.features.solar.irradiance_ml import (
    PhysicalSTCModel,
    PhysicsInformedSolarRegressor,
    PolynomialRidgeSolarModel,
    SolarModuleSpecs,
    SolarObservation,
    VirtualPyranometerEstimator,
    compute_physical_stc_power,
    evaluate_solar_model,
    generate_solar_dataset,
)


@pytest.fixture
def standard_specs() -> SolarModuleSpecs:
    return SolarModuleSpecs(
        rated_power_stc_w=380.0,
        temp_coeff_pct_per_c=-0.38,
        noct_c=45.0,
        inverter_efficiency=0.96,
        annual_degradation_pct=0.70,
    )


def test_physical_stc_baseline_standard_conditions(standard_specs: SolarModuleSpecs) -> None:
    # Under STC: G = 1000 W/m2, T_cell = 25°C, shading=1.0, soiling=1.0, age=0
    obs_stc = SolarObservation(
        irradiance_w_m2=1000.0,
        ambient_temp_c=25.0,
        cell_temp_c=25.0,
        shading_factor=1.0,
        soiling_factor=1.0,
        panel_age_years=0.0,
    )
    p = compute_physical_stc_power(obs_stc, standard_specs)
    # Expected: 380 * (1000/1000) * 1.0 * 1.0 * 0.96 * 1.0 * 1.0 = 364.8 W AC
    assert p == pytest.approx(364.8)


def test_temperature_derating_monotonicity(standard_specs: SolarModuleSpecs) -> None:
    obs_25c = SolarObservation(irradiance_w_m2=1000.0, ambient_temp_c=25.0, cell_temp_c=25.0)
    obs_45c = SolarObservation(irradiance_w_m2=1000.0, ambient_temp_c=25.0, cell_temp_c=45.0)
    obs_65c = SolarObservation(irradiance_w_m2=1000.0, ambient_temp_c=25.0, cell_temp_c=65.0)

    p_25 = compute_physical_stc_power(obs_25c, standard_specs)
    p_45 = compute_physical_stc_power(obs_45c, standard_specs)
    p_65 = compute_physical_stc_power(obs_65c, standard_specs)

    # Power must strictly decrease with rising cell temperature
    assert p_25 > p_45 > p_65

    # 45°C is +20°C from STC -> 20 * -0.38% = -7.6% loss
    loss_ratio = (p_25 - p_45) / p_25
    assert loss_ratio == pytest.approx(0.076, abs=1e-3)


def test_darkness_and_full_shading_bounds(standard_specs: SolarModuleSpecs) -> None:
    obs_dark = SolarObservation(irradiance_w_m2=0.0, ambient_temp_c=20.0, cell_temp_c=20.0)
    obs_shaded = SolarObservation(irradiance_w_m2=800.0, ambient_temp_c=25.0, shading_factor=0.0)

    assert compute_physical_stc_power(obs_dark, standard_specs) == 0.0
    assert compute_physical_stc_power(obs_shaded, standard_specs) == 0.0


def test_effective_cell_temp_noct_fallback() -> None:
    # If cell_temp_c is None, use NOCT formula: T_cell = T_amb + ((NOCT - 20) / 800) * G
    obs = SolarObservation(irradiance_w_m2=800.0, ambient_temp_c=25.0, cell_temp_c=None)
    # NOCT = 45 -> (45 - 20) / 800 * 800 = 25 -> T_cell = 25 + 25 = 50.0°C
    assert obs.effective_cell_temp(noct_c=45.0) == pytest.approx(50.0)


def test_anern_guide_benchmark_points(standard_specs: SolarModuleSpecs) -> None:
    obs_stc = SolarObservation(
        irradiance_w_m2=1000.0,
        ambient_temp_c=25.0,
        cell_temp_c=25.0,
        soiling_factor=1.0,
    )
    obs_hot = SolarObservation(
        irradiance_w_m2=1000.0,
        ambient_temp_c=30.0,
        cell_temp_c=45.0,
        soiling_factor=1.0,
    )
    obs_mod = SolarObservation(
        irradiance_w_m2=800.0,
        ambient_temp_c=20.0,
        cell_temp_c=30.0,
        soiling_factor=1.0,
    )

    p_stc = compute_physical_stc_power(obs_stc, standard_specs)
    p_hot = compute_physical_stc_power(obs_hot, standard_specs)
    p_mod = compute_physical_stc_power(obs_mod, standard_specs)

    assert 350.0 <= p_stc <= 380.0
    assert 330.0 <= p_hot <= 365.0
    assert 270.0 <= p_mod <= 305.0


def test_polynomial_ridge_model_training_and_accuracy(standard_specs: SolarModuleSpecs) -> None:
    X, y, _ = generate_solar_dataset(n_samples=1000, specs=standard_specs, random_seed=42)
    split = 800
    X_train, y_train = X[:split], y[:split]
    X_test, y_test = X[split:], y[split:]

    model = PolynomialRidgeSolarModel(alpha=1.0)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    assert len(preds) == len(y_test)
    assert np.all(preds >= 0.0)

    metrics = evaluate_solar_model("Polynomial Ridge", model, X_test, y_test)
    assert metrics.r2_score > 0.95
    assert metrics.rmse_w < 18.0


def test_physics_informed_regressor_non_negativity_and_bounds(
    standard_specs: SolarModuleSpecs,
) -> None:
    X, y, _ = generate_solar_dataset(n_samples=800, specs=standard_specs, random_seed=42)
    split = 600
    X_train, y_train = X[:split], y[:split]
    X_test = X[split:]

    pi_model = PhysicsInformedSolarRegressor(
        specs=standard_specs,
        residual_model_type="ridge",
        random_state=42,
    )
    pi_model.fit(X_train, y_train)

    preds = pi_model.predict(X_test)
    assert np.all(preds >= 0.0)

    # Check that predictions for dark input are non-negative and zero/near zero
    dark_sample = np.array([[0.0, 20.0, 20.0, 1.0, 0.98, 0.0, 380.0, -0.38, 0.96]])
    dark_pred = pi_model.predict(dark_sample)
    assert dark_pred[0] == pytest.approx(0.0, abs=5.0)


def test_virtual_pyranometer_inverse_reconstruction(standard_specs: SolarModuleSpecs) -> None:
    _, _, observations = generate_solar_dataset(n_samples=800, specs=standard_specs, random_seed=42)
    train_obs = observations[:600]
    test_obs = observations[600:]

    estimator = VirtualPyranometerEstimator(specs=standard_specs)
    estimator.fit(train_obs)

    actual_g = []
    pred_g = []
    for obs in test_obs:
        if obs.measured_power_w is not None and obs.measured_power_w > 10.0:
            actual_g.append(obs.irradiance_w_m2)
            est = estimator.estimate_irradiance(
                measured_power_w=obs.measured_power_w,
                ambient_temp_c=obs.ambient_temp_c,
                cell_temp_c=obs.cell_temp_c,
                shading_factor=obs.shading_factor,
            )
            pred_g.append(est)

    errors = np.abs(np.array(actual_g) - np.array(pred_g))
    mae_g = np.mean(errors)
    assert mae_g < 35.0


def test_model_evaluation_metrics_and_bootstrap_intervals(standard_specs: SolarModuleSpecs) -> None:
    X, y, _ = generate_solar_dataset(n_samples=500, specs=standard_specs, random_seed=42)
    model = PhysicalSTCModel(specs=standard_specs)
    metrics = evaluate_solar_model("Physical Baseline", model, X, y, n_bootstrap=100)

    assert metrics.model_name == "Physical Baseline"
    assert metrics.sample_size == 500
    assert metrics.rmse_ci_95[0] <= metrics.rmse_w <= metrics.rmse_ci_95[1]
    assert metrics.mae_ci_95[0] <= metrics.mae_w <= metrics.mae_ci_95[1]
    assert "mae_low_irradiance (<300 W/m2)" in metrics.sliced_mae
    assert "mae_high_irradiance (>700 W/m2)" in metrics.sliced_mae
    assert "mae_hot_temp (>45 C)" in metrics.sliced_mae
