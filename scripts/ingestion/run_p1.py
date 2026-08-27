"""Acquire only Person 1-owned OSM context layers for Kharghar.

Building candidates come from Google Open Buildings via ``build_p1_fixture.py``.
This command does not generate solar, economic, spatial-feature or ranking data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

WEST, SOUTH, EAST, NORTH = 73.045, 19.010, 73.090, 19.075


def fetch_osm_features(ox: object, tags: dict[str, object]) -> object:
    try:
        return ox.features_from_bbox((WEST, SOUTH, EAST, NORTH), tags=tags)
    except TypeError:
        return ox.features_from_bbox(NORTH, SOUTH, EAST, WEST, tags=tags)


def preserve_osm_identity(frame: object) -> object:
    frame = frame.reset_index()
    if {"element", "id"}.issubset(frame.columns):
        frame["source_id"] = frame["element"].astype(str) + "/" + frame["id"].astype(str)
    elif {"element_type", "osmid"}.issubset(frame.columns):
        frame["source_id"] = (
            frame["element_type"].astype(str) + "/" + frame["osmid"].astype(str)
        )
    else:
        raise ValueError("OSMnx result does not expose a preservable element identifier")
    frame["source_dataset"] = "OpenStreetMap"
    frame["source_snapshot_date"] = "2026-08-22"
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    import geopandas as gpd
    import osmnx as ox
    from shapely.geometry import box

    args.output_dir.mkdir(parents=True, exist_ok=True)
    aoi = gpd.GeoDataFrame(
        {"aoi_id": ["kharghar-v1"]},
        geometry=[box(WEST, SOUTH, EAST, NORTH)],
        crs="EPSG:4326",
    )
    aoi.to_file(args.output_dir / "kharghar_aoi.geojson", driver="GeoJSON")

    roads = fetch_osm_features(ox, {"highway": True})
    roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])].copy()
    roads = preserve_osm_identity(roads).to_crs(epsg=4326)
    road_columns = [
        column
        for column in [
            "source_id",
            "source_dataset",
            "source_snapshot_date",
            "name",
            "highway",
            "geometry",
        ]
        if column in roads.columns
    ]
    roads[road_columns].to_file(args.output_dir / "kharghar_roads.geojson", driver="GeoJSON")

    power_tags = {
        "power": ["substation", "transformer", "line", "minor_line", "plant", "cable"]
    }
    power = preserve_osm_identity(fetch_osm_features(ox, power_tags)).to_crs(epsg=4326)
    power_columns = [
        column
        for column in [
            "source_id",
            "source_dataset",
            "source_snapshot_date",
            "name",
            "power",
            "geometry",
        ]
        if column in power.columns
    ]
    power[power_columns].to_file(args.output_dir / "kharghar_power.geojson", driver="GeoJSON")
    print(f"Wrote AOI, {len(roads)} roads and {len(power)} power features to {args.output_dir}")


if __name__ == "__main__":
    main()
