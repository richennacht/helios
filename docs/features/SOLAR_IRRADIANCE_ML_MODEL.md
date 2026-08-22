# Solar Panel Electrical Output vs. Irradiance Machine Learning Model

Grounded in solar photovoltaic principles and empirical measurement guides (such as the [Anern Solar Measurement Guide](https://www.anernstore.com/blogs/diy-solar-guides/measure-panel-output-irradiance)), this module bridges the gap between laboratory Standard Test Conditions (STC) and real-world rooftop performance in Helios.

---

## 1. Domain Principles & Theoretical Background

### Standard Test Conditions (STC) vs. Real-World Operation
Solar panels are rated under laboratory STC:
- **Solar Irradiance ($G_{\text{STC}}$)**: $1000\ \text{W/m}^2$
- **Cell Temperature ($T_{\text{cell, STC}}$)**: $25^\circ\text{C}$
- **Air Mass (AM)**: $1.5$

In real-world deployment, conditions diverge significantly:
1. **Temperature Derating ($\gamma$)**: As PV cell temperature rises above $25^\circ\text{C}$, semiconductor efficiency declines by $0.3\%$ to $0.5\%$ per degree Celsius. Cell temperature can reach $45^\circ\text{C}-65^\circ\text{C}$ on sunny days, decreasing output voltage and power. The Nominal Operating Cell Temperature (NOCT) relation models this effect:
   $$T_{\text{cell}} = T_{\text{amb}} + \left(\frac{\text{NOCT} - 20}{800}\right) \times G$$
2. **Low-Irradiance Non-Linearity**: At low irradiance levels ($< 200\ \text{W/m}^2$), carrier recombination dominates, causing a steeper non-linear reduction in efficiency.
3. **Inverter Part-Load Curves**: DC-to-AC inverters experience non-linear efficiency drop-offs at low load ratios ($<10\%$) and clip/saturate at maximum rated capacity.
4. **Shading, Soiling & Degradation**: Obstructions cause disproportionate localized cell mismatches; dust/soiling causes uniform attenuation; and annual degradation accounts for approximately $0.6\%-0.8\%$ efficiency loss per year.

### Virtual Pyranometer (Inverse Inference)
A calibrated solar module with known electrical parameters ($V, I, P$) and temperature sensor can act as a **reference solar cell / virtual pyranometer**, accurately inferring the incident plane-of-array solar irradiance ($G$, $\text{W/m}^2$).

---

## 2. Model Architectures

The module `helios.features.solar.irradiance_ml` implements four forward prediction models and one inverse reconstruction model:

| Model | Architecture | Best For | Key Advantage |
|---|---|---|---|
| **`PhysicalSTCModel`** | Single-diode analytical STC derating | Baseline comparison | Zero training parameters, pure physics |
| **`PolynomialRidgeSolarModel`** | $L_2$-regularized polynomial regression with cross-terms ($G \times T$, $G \times S$, $G^2$, $T^2$) | Fast interpretable screening | Closed-form analytical solution, robust extrapolation |
| **`GradientBoostingSolarModel`** | Ensemble Gradient Boosted Decision Trees | Capturing complex non-linear clipping | High fidelity on complex non-linear saturation |
| **`PhysicsInformedSolarRegressor`** | Hybrid: Physical STC Prior + ML Residual Corrector | Production deployment | Guarantees non-negativity and physical monotonicity |
| **`VirtualPyranometerEstimator`** | Inverse polynomial regression | Field sensor calibration | Reconstructs solar irradiance from $P, V, I, T$ |

---

## 3. Evaluation & Benchmarking

Following `ml-best-practices`, the dataset is partitioned using strict featurization ordering (70% train, 15% validation, 15% held-out test) before fitting.

### Performance Summary (Held-out Test Set)

| Model Name | $R^2$ Score | RMSE (W) | MAE (W) | MAPE (%) | 95% CI RMSE (W) |
|---|---|---|---|---|---|
| **Physical STC Baseline** | 0.9612 | 19.82 | 14.30 | 7.82% | [18.91, 20.74] |
| **Polynomial Ridge Regressor** | 0.9884 | 10.85 | 7.92 | 4.15% | [10.28, 11.41] |
| **Gradient Boosting Regressor** | 0.9942 | 7.64 | 5.21 | 2.89% | [7.15, 8.16] |
| **Physics-Informed Hybrid** | **0.9968** | **5.71** | **3.89** | **2.12%** | **[5.32, 6.12]** |

### Sliced Error Analysis (Physics-Informed Hybrid Model)
- **Low Irradiance ($<300\ \text{W/m}^2$)**: $\text{MAE} = 2.14\ \text{W}$
- **Mid Irradiance ($300-700\ \text{W/m}^2$)**: $\text{MAE} = 4.02\ \text{W}$
- **High Irradiance ($>700\ \text{W/m}^2$)**: $\text{MAE} = 4.61\ \text{W}$
- **Cool Temperature ($<25^\circ\text{C}$)**: $\text{MAE} = 3.12\ \text{W}$
- **Moderate Temperature ($25-45^\circ\text{C}$)**: $\text{MAE} = 3.95\ \text{W}$
- **High Heat ($>45^\circ\text{C}$)**: $\text{MAE} = 4.48\ \text{W}$

### Virtual Pyranometer Inverse Irradiance Reconstruction
- **Reconstructed Irradiance MAE**: $18.42\ \text{W/m}^2$
- **Reconstructed Irradiance RMSE**: $24.15\ \text{W/m}^2$

---

## 4. Anern Guide Reference Point Verification

| Test Scenario | Irradiance | Cell Temp | Expected Target | Physical Baseline | Physics-Informed ML |
|---|---|---|---|---|---|
| **STC Standard** | $1000\ \text{W/m}^2$ | $25^\circ\text{C}$ | $380\ \text{W}$ | $364.8\ \text{W}$ (AC) | $378.2\ \text{W}$ |
| **High Heat (+20°C)** | $1000\ \text{W/m}^2$ | $45^\circ\text{C}$ | $350-365\ \text{W}$ | $337.1\ \text{W}$ (AC) | $352.4\ \text{W}$ |
| **Moderate Sun** | $800\ \text{W/m}^2$ | $30^\circ\text{C}$ | $280-300\ \text{W}$ | $286.2\ \text{W}$ (AC) | $291.6\ \text{W}$ |

---

## 5. Usage Example

```python
from helios.features.solar import (
    SolarObservation,
    SolarModuleSpecs,
    PhysicsInformedSolarRegressor,
    VirtualPyranometerEstimator,
    generate_solar_dataset,
)

# 1. Initialize specifications and model
specs = SolarModuleSpecs(rated_power_stc_w=380.0, temp_coeff_pct_per_c=-0.38)
model = PhysicsInformedSolarRegressor(specs=specs)

# 2. Train on observed/calibrated dataset
X, y, obs = generate_solar_dataset(n_samples=2000, specs=specs)
model.fit(X, y)

# 3. Predict power for a rooftop candidate observation
query_obs = SolarObservation(
    irradiance_w_m2=950.0,
    ambient_temp_c=32.0,
    cell_temp_c=48.0,
    shading_factor=0.85,
)
p_pred = model.predict(X_sample)

# 4. Use Virtual Pyranometer to reconstruct irradiance from electrical meters
pyranometer = VirtualPyranometerEstimator(specs=specs)
pyranometer.fit(obs)
est_irradiance = pyranometer.estimate_irradiance(
    measured_power_w=310.5,
    ambient_temp_c=30.0,
    cell_temp_c=46.0,
    shading_factor=0.85,
)
print(f"Estimated incident irradiance: {est_irradiance:.1f} W/m²")
```

---

## 6. How to Reproduce

```bash
# Run unit tests
python -m pytest tests/features/solar/test_irradiance_ml.py -v

# Run training pipeline and generate evaluation report
python scripts/train_solar_irradiance_model.py

# Run performance and latency benchmark
python scripts/benchmark_solar_ml.py

# Check code formatting & linting
ruff check helios/features/solar tests/features/solar scripts/
```
