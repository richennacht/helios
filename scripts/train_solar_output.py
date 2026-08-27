"""Train the optional solar-output challenger from a timestamped CSV."""

import argparse
import json
from pathlib import Path

import pandas as pd

from helios.ml.solar_output import TARGET_COLUMNS, train_and_evaluate

WEATHER_COLUMNS = [
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_m_s",
    "wind_direction_deg",
    "dew_point_c",
    "rain_mm",
    "rain_rate_mm_h",
    "atmospheric_pressure_hpa",
    "solar_irradiance_w_m2",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--timestamp-column", default="timestamp")
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()

    frame = pd.read_csv(args.csv, parse_dates=[args.timestamp_column])
    required = [args.timestamp_column, *WEATHER_COLUMNS, *TARGET_COLUMNS]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing CSV columns: {', '.join(missing)}")
    frame = frame[required].sort_values(args.timestamp_column).set_index(args.timestamp_column)
    hourly = frame.resample("1h").mean().dropna()
    model, summary = train_and_evaluate(hourly.to_dict(orient="records"))
    model.save(args.artifact)
    report = json.dumps(summary.model_dump(mode="json"), indent=2)
    if args.metrics:
        args.metrics.parent.mkdir(parents=True, exist_ok=True)
        args.metrics.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
