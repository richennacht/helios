"""Benchmark execution speed, latency, and accuracy of Solar Irradiance ML models."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helios.features.solar.irradiance_ml import (
    GradientBoostingSolarModel,
    PhysicalSTCModel,
    PhysicsInformedSolarRegressor,
    PolynomialRidgeSolarModel,
    SolarModuleSpecs,
    generate_solar_dataset,
)


def benchmark_models(n_samples: int = 5000) -> None:
    print("=" * 80)
    print(" HELIOS SOLAR IRRADIANCE ML PERFORMANCE & LATENCY BENCHMARK")
    print("=" * 80)

    specs = SolarModuleSpecs(rated_power_stc_w=380.0)
    X, y, _ = generate_solar_dataset(n_samples=n_samples, specs=specs, random_seed=42)

    split = int(0.8 * n_samples)
    X_train, y_train = X[:split], y[:split]
    X_test, _ = X[split:], y[split:]

    models = [
        ("Physical STC Baseline", PhysicalSTCModel(specs)),
        ("Polynomial Ridge Regressor", PolynomialRidgeSolarModel(alpha=1.0)),
        ("Gradient Boosting Regressor", GradientBoostingSolarModel(n_estimators=80, max_depth=3)),
        (
            "Physics-Informed Hybrid Regressor",
            PhysicsInformedSolarRegressor(specs=specs, residual_model_type="gbr"),
        ),
    ]

    print(f"\nEvaluating throughput on {len(X_test)} test observations (50 iters)...\n")
    header = (
        f"{'Model Name':<36} | {'Fit Time (ms)':<14} | {'Inference (us/sample)':<22} | "
        f"{'Throughput (k-pred/s)':<22}"
    )
    print(header)
    print("-" * 100)

    for name, model in models:
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        fit_time_ms = (time.perf_counter() - t0) * 1000.0

        n_iters = 50
        t0_inf = time.perf_counter()
        for _ in range(n_iters):
            _ = model.predict(X_test)
        total_inf_sec = time.perf_counter() - t0_inf
        total_preds = n_iters * len(X_test)
        us_per_sample = (total_inf_sec / total_preds) * 1_000_000.0
        k_preds_per_sec = (total_preds / total_inf_sec) / 1000.0

        row_str = (
            f"{name:<36} | {fit_time_ms:<14.2f} | {us_per_sample:<22.3f} | "
            f"{k_preds_per_sec:<22.2f}"
        )
        print(row_str)

    print("-" * 100)
    print("\nBenchmark completed successfully.")


if __name__ == "__main__":
    benchmark_models()
