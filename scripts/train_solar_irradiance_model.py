"""Train and evaluate Machine Learning models for Solar Panel Output vs Irradiance.

Adheres strictly to ml-best-practices:
- Strict Featurization Ordering (train/val/test split before fitting).
- Physical STC benchmark comparison.
- Multi-model evaluation (Physical STC, Polynomial Ridge, Gradient Boosting, Physics-Informed).
- 95% Bootstrap Confidence Intervals and Sliced Error Analysis.
- Inverse Virtual Pyranometer training and validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from helios.features.solar.irradiance_ml import (
    GradientBoostingSolarModel,
    PhysicalSTCModel,
    PhysicsInformedSolarRegressor,
    PolynomialRidgeSolarModel,
    SolarModuleSpecs,
    VirtualPyranometerEstimator,
    evaluate_solar_model,
    generate_solar_dataset,
)


def run_training_pipeline(
    n_samples: int = 3000,
    random_seed: int = 42,
    output_report_path: Path | None = None,
) -> dict:
    print("=" * 80)
    print(" HELIOS SOLAR IRRADIANCE & ELECTRICAL OUTPUT ML TRAINING PIPELINE")
    print(" Grounded in Anern Solar Measurement Guide Principles")
    print("=" * 80)

    specs = SolarModuleSpecs(
        rated_power_stc_w=380.0,
        temp_coeff_pct_per_c=-0.38,
        noct_c=45.0,
        inverter_efficiency=0.96,
        annual_degradation_pct=0.70,
        module_area_m2=1.95,
    )

    print(f"\n[1] Generating dataset with {n_samples} environmental & electrical observations...")
    X, y, observations = generate_solar_dataset(
        n_samples=n_samples, specs=specs, random_seed=random_seed
    )

    # 1. Strict Train / Validation / Test Splitting BEFORE any fitting
    n_total = len(y)
    n_train = int(0.70 * n_total)
    n_val = int(0.15 * n_total)

    rng = np.random.default_rng(random_seed)
    indices = rng.permutation(n_total)

    train_idx = indices[:n_train]
    val_idx = indices[n_train : n_train + n_val]
    test_idx = indices[n_train + n_val :]

    X_train, y_train = X[train_idx], y[train_idx]
    _X_val = X[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    train_obs = [observations[i] for i in train_idx]
    test_obs = [observations[i] for i in test_idx]

    print(f"    - Training set:   {len(X_train)} samples")
    print(f"    - Validation set: {len(_X_val)} samples")
    print(f"    - Held-out test:  {len(X_test)} samples")

    # 2. Train Models
    print("\n[2] Training Solar Output Regressors...")

    print("    - Fitting Model 1: Physical STC Baseline...")
    phys_model = PhysicalSTCModel(specs=specs)
    phys_model.fit(X_train, y_train)

    print("    - Fitting Model 2: Polynomial Ridge Regressor (L2 alpha=1.0)...")
    ridge_model = PolynomialRidgeSolarModel(alpha=1.0)
    ridge_model.fit(X_train, y_train)

    print("    - Fitting Model 3: Gradient Boosting Solar Regressor...")
    gbr_model = GradientBoostingSolarModel(
        n_estimators=100, learning_rate=0.08, max_depth=4, random_state=random_seed
    )
    gbr_model.fit(X_train, y_train)

    print("    - Fitting Model 4: Physics-Informed Hybrid Regressor (STC prior + ML residual)...")
    pi_model = PhysicsInformedSolarRegressor(
        specs=specs, residual_model_type="gbr", random_state=random_seed
    )
    pi_model.fit(X_train, y_train)

    # 3. Comprehensive Evaluation on Held-Out Test Set
    print("\n[3] Evaluating Models on Held-out Test Data (95% Bootstrap CIs)...")
    models = [
        ("Physical STC Baseline", phys_model),
        ("Polynomial Ridge Regressor", ridge_model),
        ("Gradient Boosting Regressor", gbr_model),
        ("Physics-Informed Hybrid Regressor", pi_model),
    ]

    metrics_list = []
    for name, model in models:
        metrics = evaluate_solar_model(
            name, model, X_test, y_test, n_bootstrap=500, random_seed=random_seed
        )
        metrics_list.append(metrics)

    # Print summary table
    print("\n" + "-" * 100)
    header = (
        f"{'Model Name':<34} | {'R2':<6} | {'RMSE(W)':<8} | {'MAE(W)':<7} | "
        f"{'MAPE%':<6} | {'95% CI RMSE (W)':<18}"
    )
    print(header)
    print("-" * 100)
    for m in metrics_list:
        ci_str = f"[{m.rmse_ci_95[0]:.2f}, {m.rmse_ci_95[1]:.2f}]"
        row_str = (
            f"{m.model_name:<34} | {m.r2_score:<6.4f} | {m.rmse_w:<8.2f} | "
            f"{m.mae_w:<7.2f} | {m.mape_pct:<6.2f} | {ci_str:<18}"
        )
        print(row_str)
    print("-" * 100)

    # Sliced Error Analysis
    print("\n[4] Sliced Error Analysis (MAE in Watts across Environmental Regimes):")
    best_model_metrics = metrics_list[-1]
    print(f"    Breakdown for '{best_model_metrics.model_name}':")
    for slice_name, slice_mae in best_model_metrics.sliced_mae.items():
        print(f"      * {slice_name:<38}: {slice_mae:.2f} W")

    # 4. Train and Validate Virtual Pyranometer (Inverse ML Model)
    print("\n[5] Training Virtual Pyranometer (Inverse Irradiance Estimator)...")
    pyranometer = VirtualPyranometerEstimator(specs=specs)
    pyranometer.fit(train_obs)

    test_actual_g = [obs.irradiance_w_m2 for obs in test_obs if obs.measured_power_w is not None]
    test_pred_g = [
        pyranometer.estimate_irradiance(
            measured_power_w=obs.measured_power_w or 0.0,
            ambient_temp_c=obs.ambient_temp_c,
            cell_temp_c=obs.cell_temp_c,
            shading_factor=obs.shading_factor,
        )
        for obs in test_obs
        if obs.measured_power_w is not None
    ]

    g_errors = np.abs(np.array(test_actual_g) - np.array(test_pred_g))
    pyr_mae = float(np.mean(g_errors))
    pyr_rmse = float(np.sqrt(np.mean(g_errors ** 2)))
    print(f"    - Virtual Pyranometer Reconstructed Irradiance MAE:  {pyr_mae:.2f} W/m2")
    print(f"    - Virtual Pyranometer Reconstructed Irradiance RMSE: {pyr_rmse:.2f} W/m2")

    # 5. Anern Guide Benchmark Verification Points
    print("\n[6] Verification Against Anern DIY Solar Guide Benchmark Points:")
    benchmark_points = [
        ("STC Standard (1000 W/m2 @ 25C cell)", 1000.0, 25.0, 25.0, 1.0, "380 W expected"),
        ("High Heat (1000 W/m2 @ 45C cell)", 1000.0, 32.0, 45.0, 1.0, "350 - 365 W expected"),
        ("Moderate Sun (800 W/m2 @ 30C cell)", 800.0, 25.0, 30.0, 1.0, "280 - 300 W expected"),
    ]

    for label, g_val, amb_t, cell_t, shade, exp_note in benchmark_points:
        X_bench = np.array([[
            g_val,
            amb_t,
            cell_t,
            shade,
            0.98,
            0.0,
            specs.rated_power_stc_w,
            specs.temp_coeff_pct_per_c,
            specs.inverter_efficiency,
        ]])
        p_phys = phys_model.predict(X_bench)[0]
        p_pi = pi_model.predict(X_bench)[0]
        est_g = pyranometer.estimate_irradiance(p_pi, amb_t, cell_t, shade)
        print(f"    * {label}:")
        print(f"        Expected:       {exp_note}")
        print(f"        Physical STC:   {p_phys:.2f} W")
        print(f"        Physics-Inf ML: {p_pi:.2f} W")
        print(f"        Inverse Pyr:    {est_g:.1f} W/m2 (target: {g_val:.1f} W/m2)")

    report = {
        "status": "completed",
        "sample_size": n_samples,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "models": [
            {
                "model_name": m.model_name,
                "r2_score": m.r2_score,
                "rmse_w": m.rmse_w,
                "mae_w": m.mae_w,
                "mape_pct": m.mape_pct,
                "rmse_ci_95": list(m.rmse_ci_95),
                "mae_ci_95": list(m.mae_ci_95),
                "sliced_mae": m.sliced_mae,
            }
            for m in metrics_list
        ],
        "virtual_pyranometer": {
            "mae_w_m2": round(pyr_mae, 2),
            "rmse_w_m2": round(pyr_rmse, 2),
        },
    }

    if output_report_path:
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        output_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n[7] Saved evaluation report to: {output_report_path}")

    print("\n" + "=" * 80)
    print(" TRAINING & EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Solar Output vs Irradiance ML models")
    parser.add_argument("--samples", type=int, default=3000, help="Number of simulation samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/solar_irradiance_ml_evaluation.json"),
        help="Path to save evaluation JSON report",
    )
    args = parser.parse_args()
    run_training_pipeline(
        n_samples=args.samples,
        random_seed=args.seed,
        output_report_path=args.output,
    )
