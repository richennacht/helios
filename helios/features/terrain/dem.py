"""Derive context-only terrain observations from a DEM.

Copernicus GLO-30 resolves terrain around a candidate, not an individual roof.
The outputs in this module must therefore never be labelled as roof tilt,
roof aspect, building height, or rooftop shading.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, degrees, pi
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TerrainObservation:
    elevation_m: float | None
    slope_deg: float | None
    aspect_deg: float | None
    local_relief_m: float | None
    source_resolution_m: float
    sampling_method: str
    semantic_role: str = "terrain_context_only"

    def as_properties(self) -> dict[str, Any]:
        return asdict(self)


def _meters_per_degree(latitude: float) -> tuple[float, float]:
    """Return practical WGS84 metre scales for a small local raster."""

    radians = latitude * pi / 180.0
    latitude_m = (
        111132.92
        - 559.82 * cos(2 * radians)
        + 1.175 * cos(4 * radians)
        - 0.0023 * cos(6 * radians)
    )
    longitude_m = (
        111412.84 * cos(radians)
        - 93.5 * cos(3 * radians)
        + 0.118 * cos(5 * radians)
    )
    return latitude_m, longitude_m


def sample_terrain(
    dem_path: str | Path,
    longitude: float,
    latitude: float,
    *,
    neighborhood_radius: int = 1,
) -> TerrainObservation:
    """Sample median elevation and a local plane from a DEM neighbourhood.

    A 3x3 neighbourhood is the default. It reduces single-cell DSM artefacts
    while retaining the local terrain signal available at GLO-30 resolution.
    """

    import numpy as np
    import rasterio
    from pyproj import Transformer
    from rasterio.windows import Window

    with rasterio.open(dem_path) as dataset:
        x, y = longitude, latitude
        if dataset.crs and dataset.crs.to_epsg() != 4326:
            transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
            x, y = transformer.transform(longitude, latitude)
        row, col = dataset.index(x, y)
        radius = neighborhood_radius
        window = Window(col - radius, row - radius, 2 * radius + 1, 2 * radius + 1)
        values = dataset.read(1, window=window, boundless=True, masked=True)
        array = values.filled(np.nan).astype(float)
        valid = np.isfinite(array)
        resolution_m = float(abs(dataset.res[0]))
        if dataset.crs and dataset.crs.is_geographic:
            latitude_m, longitude_m = _meters_per_degree(latitude)
            dy_m = abs(dataset.transform.e) * latitude_m
            dx_m = abs(dataset.transform.a) * longitude_m
            resolution_m = (dx_m + dy_m) / 2.0
        else:
            dx_m, dy_m = abs(dataset.transform.a), abs(dataset.transform.e)

        if not valid.any():
            return TerrainObservation(None, None, None, None, resolution_m, "3x3_median_plane")

        elevation = float(np.nanmedian(array))
        relief = float(np.nanmax(array) - np.nanmin(array))
        if array.shape != (3, 3) or valid.sum() < 6:
            return TerrainObservation(
                round(elevation, 2), None, None, round(relief, 2), resolution_m,
                "3x3_median_plane",
            )

        rows, cols = np.indices(array.shape)
        east_m = (cols - radius) * dx_m
        north_m = -(rows - radius) * dy_m
        design = np.column_stack((east_m[valid], north_m[valid], np.ones(valid.sum())))
        dz_deast, dz_dnorth, _ = np.linalg.lstsq(design, array[valid], rcond=None)[0]
        gradient = float(np.hypot(dz_deast, dz_dnorth))
        slope = degrees(float(np.arctan(gradient)))
        aspect = None
        if slope >= 0.1:
            # Compass bearing of steepest descent: 0=N, 90=E, 180=S, 270=W.
            aspect = (degrees(float(np.arctan2(-dz_deast, -dz_dnorth))) + 360.0) % 360.0
        return TerrainObservation(
            round(elevation, 2),
            round(slope, 2),
            round(aspect, 2) if aspect is not None else None,
            round(relief, 2),
            round(resolution_m, 2),
            "3x3_median_plane",
        )
