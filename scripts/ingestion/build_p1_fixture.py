"""Build the Person 1 candidate fixture from Google Open Buildings v3.

The input is one official ``*_buildings.csv.gz`` shard. Temporal rasters are
optional because downloading them is a separate, comparatively large step. If
they are omitted, height observations remain null rather than being invented.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Any, BinaryIO, TextIO
from urllib.request import urlopen

from helios.ingestion.identity import candidate_id, source_record_digest

DEFAULT_BBOX = (73.045, 19.010, 73.090, 19.075)


def open_gzip_csv(source: str, stack: ExitStack) -> TextIO:
    """Open a local path or HTTPS URL as a decoded gzip CSV stream."""
    if source.startswith(("https://", "http://")):
        binary: BinaryIO = stack.enter_context(urlopen(source))  # noqa: S310
    else:
        binary = stack.enter_context(Path(source).open("rb"))
    compressed = stack.enter_context(gzip.GzipFile(fileobj=binary))
    return stack.enter_context(
        __import__("io").TextIOWrapper(compressed, encoding="utf-8", newline="")
    )


def temporal_sample(
    longitude: float,
    latitude: float,
    datasets: list[Any],
    transformer: Any,
) -> tuple[float | None, float | None, str | None]:
    """Sample height and uncalibrated presence at a building centroid."""
    if not datasets:
        return None, None, None
    x, y = transformer.transform(longitude, latitude)
    for dataset in datasets:
        inside_x = dataset.bounds.left <= x <= dataset.bounds.right
        inside_y = dataset.bounds.bottom <= y <= dataset.bounds.top
        if inside_x and inside_y:
            height, presence = next(dataset.sample([(x, y)], indexes=[2, 3]))
            if dataset.nodata is not None and height == dataset.nodata:
                return None, None, dataset.name
            height_value = float(height)
            presence_value = float(presence)
            if height_value <= 0 or not 0 <= presence_value <= 1:
                return None, presence_value if 0 <= presence_value <= 1 else None, dataset.name
            return round(height_value, 2), round(presence_value, 4), dataset.name
    return None, None, None


def build_fixture(args: argparse.Namespace) -> dict[str, Any]:
    """Clip, validate, enrich and deterministically order a small fixture."""
    from shapely import from_wkt
    from shapely.geometry import mapping

    datasets: list[Any] = []
    raster_stack = ExitStack()
    transformer = None
    if args.temporal_raster:
        os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
        import rasterio
        from pyproj import Transformer

        datasets = [raster_stack.enter_context(rasterio.open(uri)) for uri in args.temporal_raster]
        transformer = Transformer.from_crs("EPSG:4326", datasets[0].crs, always_xy=True)

    west, south, east, north = args.bbox
    features: dict[str, dict[str, Any]] = {}
    with ExitStack() as source_stack:
        reader = csv.DictReader(open_gzip_csv(args.buildings, source_stack))
        required = {
            "latitude",
            "longitude",
            "area_in_meters",
            "confidence",
            "geometry",
            "full_plus_code",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"Google Open Buildings columns missing: {missing}")

        for row in reader:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
            if not (west <= longitude <= east and south <= latitude <= north):
                continue
            geometry = from_wkt(row["geometry"])
            if geometry.is_empty or not geometry.is_valid:
                continue
            digest = source_record_digest(args.source_tile, row["full_plus_code"], row["geometry"])
            helios_id = candidate_id(args.source_tile, row["full_plus_code"], row["geometry"])
            height, presence, temporal_uri = temporal_sample(
                longitude,
                latitude,
                datasets,
                transformer,
            )
            properties = {
                "candidate_id": helios_id,
                "aoi_id": "kharghar-v1",
                "source_dataset": "Google Open Buildings",
                "source_version": "v3",
                "source_tile_token": args.source_tile,
                "source_record_key": f"gobv3:{args.source_tile}:sha256:{digest}",
                "source_record_key_method": "sha256(tile|plus_code|normalized_source_wkt)",
                "source_plus_code": row["full_plus_code"],
                "source_confidence": round(float(row["confidence"]), 4),
                "source_centroid_lat": latitude,
                "source_centroid_lon": longitude,
                "source_footprint_area_m2": round(float(row["area_in_meters"]), 4),
                "geometry_valid": True,
                "temporal_height_m": height,
                "temporal_presence_score": presence,
                "temporal_year": 2023 if temporal_uri else None,
                "temporal_sampling_method": "centroid_nearest_pixel" if temporal_uri else None,
                "temporal_source_uri": temporal_uri,
                "temporal_effective_resolution_m": 4.0 if temporal_uri else None,
                "gobs_enrichment_status": "not_requested_file_available",
            }
            features[helios_id] = {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geometry),
            }
            if len(features) >= args.limit:
                break

    raster_stack.close()
    selected = [features[key] for key in sorted(features)[: args.limit]]
    if len(selected) < args.limit:
        raise ValueError(f"Only {len(selected)} valid buildings found; expected {args.limit}")
    return {
        "type": "FeatureCollection",
        "name": "candidate_buildings",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": selected,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--buildings", required=True, help="Local path or HTTPS URL to v3 CSV.gz")
    parser.add_argument("--source-tile", default="3bf")
    parser.add_argument("--temporal-raster", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixture = build_fixture(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(fixture['features'])} candidates to {args.output}")


if __name__ == "__main__":
    main()
