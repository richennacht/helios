from pydantic import BaseModel, ConfigDict, Field


class WeatherObservation(BaseModel):
    """Weather inputs used by the paper-inspired output model."""

    model_config = ConfigDict(extra="forbid")

    temperature_c: float = Field(ge=-90, le=70)
    relative_humidity_pct: float = Field(ge=0, le=100)
    wind_speed_m_s: float = Field(ge=0)
    wind_direction_deg: float = Field(ge=0, le=360)
    dew_point_c: float = Field(ge=-100, le=70)
    rain_mm: float = Field(ge=0)
    rain_rate_mm_h: float = Field(ge=0)
    atmospheric_pressure_hpa: float = Field(gt=0)
    solar_irradiance_w_m2: float = Field(ge=0)


class SolarOutputPrediction(BaseModel):
    max_voltage_v: float = Field(ge=0)
    max_current_a: float = Field(ge=0)
    estimated_peak_power_w: float = Field(ge=0)
    model_name: str
    model_version: str


class RegressionMetrics(BaseModel):
    voltage_rmse: float = Field(ge=0)
    voltage_mae: float = Field(ge=0)
    current_rmse: float = Field(ge=0)
    current_mae: float = Field(ge=0)


class TrainingSummary(BaseModel):
    selected_model: str
    train_rows: int
    test_rows: int
    models: dict[str, RegressionMetrics]
