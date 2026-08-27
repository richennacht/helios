from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from helios.features.terrain import sample_terrain


def write_dem(path: Path, values: np.ndarray) -> tuple[float, float]:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32643",
        transform=from_origin(400000, 2100000, 30, 30),
    ) as dataset:
        dataset.write(values.astype("float32"), 1)
    inverse = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    return inverse.transform(400075, 2099925)


def test_flat_dem_has_no_meaningful_aspect(tmp_path: Path) -> None:
    path = tmp_path / "flat.tif"
    longitude, latitude = write_dem(path, np.full((5, 5), 100.0))
    observation = sample_terrain(path, longitude, latitude)
    assert observation.elevation_m == 100.0
    assert observation.slope_deg == 0.0
    assert observation.aspect_deg is None
    assert observation.semantic_role == "terrain_context_only"


def test_east_rising_plane_reports_west_facing_descent(tmp_path: Path) -> None:
    path = tmp_path / "plane.tif"
    values = np.tile(np.arange(5, dtype=float) * 3.0, (5, 1))
    longitude, latitude = write_dem(path, values)
    observation = sample_terrain(path, longitude, latitude)
    assert 5.0 < observation.slope_deg < 6.5
    assert observation.aspect_deg == 270.0
    assert observation.local_relief_m == 6.0
