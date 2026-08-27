"""Build and query a spatially indexed, multi-source building catalogue.

The catalogue stores source observations rather than prematurely flattening
them.  Query results cluster likely representations of the same building and
average independent height observations, passing through a sole observation
and leaving missing height as null.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from scripts.geo.merge_building_datasets import fuse_height_observations


SOURCE_GROUPS = {
    "google-open-buildings-v3": "google-open-buildings",
    "microsoft-global-ml-buildings-2026-08-13": "microsoft-global-ml",
    # Overture records preserve upstream lineage. The group is refined per row.
    "overture-buildings-2026-07-22": "overture",
}


def stream_geojson_features(path: Path, chunk_size: int = 1 << 20) -> Iterator[dict[str, Any]]:
    """Yield FeatureCollection features without loading the whole file."""
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as stream:
        buffer = ""
        while '"features"' not in buffer:
            block = stream.read(chunk_size)
            if not block:
                raise ValueError(f"No features array in {path}")
            buffer += block
        buffer = buffer.split('"features"', 1)[1]
        while "[" not in buffer:
            block = stream.read(chunk_size)
            if not block:
                raise ValueError(f"No features array in {path}")
            buffer += block
        buffer = buffer.split("[", 1)[1]
        while True:
            buffer = buffer.lstrip(" \r\n\t,")
            if buffer.startswith("]"):
                return
            try:
                feature, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                block = stream.read(chunk_size)
                if not block:
                    raise
                buffer += block
                continue
            yield feature
            buffer = buffer[end:]


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def geometry_stats(geometry: dict[str, Any]) -> tuple[float, float, float, float, float, float]:
    coordinates = geometry.get("coordinates") or []
    kind = geometry.get("type")
    rings = [coordinates[0]] if kind == "Polygon" and coordinates else []
    if kind == "MultiPolygon":
        rings = [polygon[0] for polygon in coordinates if polygon]
    points = [point for ring in rings for point in ring]
    if not points:
        raise ValueError(f"Unsupported or empty geometry: {kind}")
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    # Mean vertices is deliberately cheap and deterministic; matching also uses bbox overlap.
    return min(xs), min(ys), max(xs), max(ys), sum(xs) / len(xs), sum(ys) / len(ys)


def _positive(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _overture_group(feature: dict[str, Any]) -> str:
    datasets = sorted(
        str(source.get("dataset") or "unknown").lower()
        for source in feature.get("sources") or []
    )
    # This prevents an Overture copy of OSM/Microsoft from becoming an extra vote.
    return "upstream:" + "+".join(datasets)


def normalise_feature(feature: dict[str, Any], source_id: str) -> dict[str, Any]:
    geometry = feature["geometry"]
    minx, miny, maxx, maxy, lon, lat = geometry_stats(geometry)
    properties = feature.get("properties") or feature
    record_id = properties.get("source_record_id") or feature.get("id")
    return {
        "source_id": source_id,
        "source_record_id": str(record_id),
        "independence_group": _overture_group(feature)
        if source_id.startswith("overture-")
        else SOURCE_GROUPS[source_id],
        "height_m": next(
            (
                value
                for candidate in (
                    properties.get("height_m"),
                    properties.get("height"),
                    feature.get("height"),
                )
                if (value := _positive(candidate)) is not None
            ),
            None,
        ),
        "year": properties.get("year"),
        "minx": minx,
        "miny": miny,
        "maxx": maxx,
        "maxy": maxy,
        "centroid_lon": lon,
        "centroid_lat": lat,
        "geometry": geometry,
        "properties": properties,
    }


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_record_id TEXT NOT NULL,
            independence_group TEXT NOT NULL,
            height_m REAL,
            year INTEGER,
            centroid_lon REAL NOT NULL,
            centroid_lat REAL NOT NULL,
            geometry_json TEXT NOT NULL,
            properties_json TEXT NOT NULL,
            UNIQUE(source_id, source_record_id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS observation_bounds USING rtree(
            id, minx, maxx, miny, maxy
        );
        CREATE INDEX IF NOT EXISTS observations_source ON observations(source_id);
        """
    )


def ingest(
    connection: sqlite3.Connection,
    source_id: str,
    features: Iterable[dict[str, Any]],
    batch_size: int = 10_000,
) -> int:
    rows: list[dict[str, Any]] = []
    inserted = 0

    def flush() -> None:
        nonlocal inserted
        for row in rows:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO observations
                (source_id, source_record_id, independence_group, height_m, year,
                 centroid_lon, centroid_lat, geometry_json, properties_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["source_id"], row["source_record_id"], row["independence_group"],
                    row["height_m"], row["year"], row["centroid_lon"], row["centroid_lat"],
                    json.dumps(row["geometry"], separators=(",", ":")),
                    json.dumps(row["properties"], separators=(",", ":")),
                ),
            )
            if cursor.rowcount:
                observation_id = cursor.lastrowid
                connection.execute(
                    "INSERT INTO observation_bounds VALUES (?, ?, ?, ?, ?)",
                    (observation_id, row["minx"], row["maxx"], row["miny"], row["maxy"]),
                )
                inserted += 1
        connection.commit()
        rows.clear()

    for feature in features:
        rows.append(normalise_feature(feature, source_id))
        if len(rows) >= batch_size:
            flush()
    if rows:
        flush()
    return inserted


def _metres_between(a: sqlite3.Row, b: sqlite3.Row) -> float:
    lat = math.radians((a["centroid_lat"] + b["centroid_lat"]) / 2)
    dx = (a["centroid_lon"] - b["centroid_lon"]) * 111_320 * math.cos(lat)
    dy = (a["centroid_lat"] - b["centroid_lat"]) * 110_540
    return math.hypot(dx, dy)


def _overlap_ratio(a: sqlite3.Row, b: sqlite3.Row) -> float:
    overlap_x = max(0.0, min(a["maxx"], b["maxx"]) - max(a["minx"], b["minx"]))
    overlap_y = max(0.0, min(a["maxy"], b["maxy"]) - max(a["miny"], b["miny"]))
    intersection = overlap_x * overlap_y
    area_a = max(1e-15, (a["maxx"] - a["minx"]) * (a["maxy"] - a["miny"]))
    area_b = max(1e-15, (b["maxx"] - b["minx"]) * (b["maxy"] - b["miny"]))
    return intersection / min(area_a, area_b)


def query_fused(
    connection: sqlite3.Connection,
    bbox: tuple[float, float, float, float],
    match_distance_m: float = 12.0,
) -> dict[str, Any]:
    """Return a fused GeoJSON view for a small viewport/AOI."""
    connection.row_factory = sqlite3.Row
    west, south, east, north = bbox
    rows = connection.execute(
        """SELECT o.*, b.minx, b.maxx, b.miny, b.maxy
        FROM observation_bounds b JOIN observations o ON o.id=b.id
        WHERE b.maxx>=? AND b.minx<=? AND b.maxy>=? AND b.miny<=?
        ORDER BY CASE o.source_id
          WHEN 'google-open-buildings-v3' THEN 0
          WHEN 'microsoft-global-ml-buildings-2026-08-13' THEN 1 ELSE 2 END, o.id""",
        (west, east, south, north),
    ).fetchall()
    clusters: list[list[sqlite3.Row]] = []
    cluster_buckets: dict[tuple[int, int], list[int]] = {}
    cell_degrees = match_distance_m / 100_000
    for row in rows:
        key = (int(row["centroid_lon"] / cell_degrees), int(row["centroid_lat"] / cell_degrees))
        candidate_indices = {
            index
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for index in cluster_buckets.get((key[0] + dx, key[1] + dy), [])
        }
        match_index = next(
            (
                index
                for index in candidate_indices
                if all(item["source_id"] != row["source_id"] for item in clusters[index])
                and _metres_between(clusters[index][0], row) <= match_distance_m
                and _overlap_ratio(clusters[index][0], row) >= 0.35
            ),
            None,
        )
        if match_index is None:
            match_index = len(clusters)
            clusters.append([row])
            cluster_buckets.setdefault(key, []).append(match_index)
        else:
            clusters[match_index].append(row)
    features = []
    for cluster in clusters:
        representative = cluster[0]
        height_observations = [
            {
                "source_id": row["source_id"],
                "independence_group": row["independence_group"],
                "height_m": row["height_m"],
                "year": row["year"],
            }
            for row in cluster
            if row["height_m"] is not None
        ]
        height, height_sources = fuse_height_observations(height_observations)
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(representative["geometry_json"]),
                "properties": {
                    "building_id": f"helios:{representative['id']}",
                    "height_m": height,
                    "height_observations": height_observations,
                    "height_observation_sources": height_sources,
                    "source_datasets": [row["source_id"] for row in cluster],
                    "source_record_ids": [row["source_record_id"] for row in cluster],
                    "synthetic_height": False,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "metadata": {
            "bbox_wgs84": bbox,
            "observation_count": len(rows),
            "building_count": len(features),
            "height_policy": "mean of independent positive observations; sole value passes through; missing remains null",
        },
        "features": features,
    }


def enrich_with_height_raster(
    collection: dict[str, Any], raster_path: Path, source_id: str
) -> dict[str, Any]:
    """Fuse a georeferenced height raster into a queried collection.

    Raster support stays optional so catalogue construction requires only the
    standard library. The project virtual environment supplies rasterio.
    """
    import rasterio
    from rasterio.warp import transform

    features = collection.get("features") or []
    with rasterio.open(raster_path) as dataset:
        centres = [geometry_stats(feature["geometry"])[-2:] for feature in features]
        xs, ys = transform("EPSG:4326", dataset.crs, [p[0] for p in centres], [p[1] for p in centres])
        samples = dataset.sample(zip(xs, ys), indexes=1, masked=True)
        enriched = 0
        for feature, sample in zip(features, samples):
            raster_height = None if sample.mask[0] else _positive(sample[0])
            properties = feature["properties"]
            vector_height = _positive(properties.get("height_m"))
            observations = list(properties.get("height_observations") or [])
            if raster_height is not None:
                observations.append({"source_id": source_id, "height_m": raster_height})
                enriched += 1
            height, sources = fuse_height_observations(observations)
            properties["vector_height_m"] = vector_height
            properties["context_height_m"] = round(raster_height, 2) if raster_height else None
            properties["height_m"] = height
            properties["height_observation_sources"] = sources
            properties["height_observations"] = observations
            properties["height_quality"] = (
                "multi-source mean" if len(sources) > 1 else
                "source observation" if sources else "unavailable"
            )
    collection.setdefault("metadata", {})["height_raster"] = {
        "source_id": source_id,
        "path": str(raster_path),
        "resolution_note": "area-average raster context sampled at footprint centroid",
        "enriched_building_count": enriched,
    }
    return collection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--google", type=Path)
    parser.add_argument("--microsoft", type=Path)
    parser.add_argument("--overture", type=Path)
    parser.add_argument("--query-bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--height-raster", type=Path)
    parser.add_argument("--height-raster-source", default="wsf3d-v02-building-height")
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    create_schema(connection)
    inputs = (
        ("google-open-buildings-v3", args.google, stream_geojson_features),
        ("microsoft-global-ml-buildings-2026-08-13", args.microsoft, stream_geojson_features),
        ("overture-buildings-2026-07-22", args.overture, iter_jsonl),
    )
    for source_id, path, reader in inputs:
        if path:
            print(f"{source_id}: inserted {ingest(connection, source_id, reader(path))}")
    if args.query_bbox:
        result = query_fused(connection, tuple(args.query_bbox))
        if args.height_raster:
            result = enrich_with_height_raster(result, args.height_raster, args.height_raster_source)
        payload = json.dumps(result, separators=(",", ":"))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload)


if __name__ == "__main__":
    main()
