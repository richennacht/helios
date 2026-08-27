"""Clip public Google and Microsoft building partitions to a WGS84 envelope."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    west, south, east, north = bbox
    return west <= lon <= east and south <= lat <= north


def parse_polygon_wkt(value: str) -> dict[str, Any]:
    text = value.strip()
    polygon = re.fullmatch(r"POLYGON\s*\(\((.*)\)\)", text, flags=re.IGNORECASE)
    multipolygon = re.fullmatch(
        r"MULTIPOLYGON\s*\(\(\((.*)\)\)\)", text, flags=re.IGNORECASE
    )
    if not polygon and not multipolygon:
        raise ValueError(f"Unsupported Google v3 WKT geometry: {text[:40]}")

    def parse_ring(ring_text: str) -> list[list[float]]:
        ring = []
        for pair in ring_text.split(","):
            lon, lat = pair.strip().split()[:2]
            ring.append([float(lon), float(lat)])
        return ring

    if polygon:
        rings = [parse_ring(ring) for ring in re.split(r"\)\s*,\s*\(", polygon.group(1))]
        return {"type": "Polygon", "coordinates": rings}
    polygons = [
        [parse_ring(ring)] for ring in re.split(r"\)\)\s*,\s*\(\(", multipolygon.group(1))
    ]
    return {"type": "MultiPolygon", "coordinates": polygons}


def stable_id(source: str, geometry: dict[str, Any]) -> str:
    payload = json.dumps(geometry, separators=(",", ":"), sort_keys=True).encode()
    return f"{source}:{hashlib.sha256(payload).hexdigest()[:20]}"


def google_features(path: Path, bbox: tuple[float, float, float, float]) -> Iterable[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            lon, lat = float(row["longitude"]), float(row["latitude"])
            if not in_bbox(lon, lat, bbox):
                continue
            geometry = parse_polygon_wkt(row["geometry"])
            yield {
                "type": "Feature",
                "properties": {
                    "source_record_id": stable_id("google-open-buildings-v3", geometry),
                    "source_dataset": "Google Open Buildings",
                    "source_version": "v3",
                    "source_confidence": float(row["confidence"]),
                    "source_footprint_area_m2": float(row["area_in_meters"]),
                    "source_centroid_lon": lon,
                    "source_centroid_lat": lat,
                    "source_plus_code": row["full_plus_code"],
                    "height_m": None,
                    "height_source": "not present in Google Open Buildings v3 polygons",
                    "source_license": "CC BY 4.0",
                },
                "geometry": geometry,
            }


def microsoft_features(paths: list[Path], bbox: tuple[float, float, float, float]) -> Iterable[dict]:
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                feature = json.loads(line)
                ring = feature["geometry"]["coordinates"][0]
                lon = sum(point[0] for point in ring[:-1]) / max(1, len(ring) - 1)
                lat = sum(point[1] for point in ring[:-1]) / max(1, len(ring) - 1)
                if not in_bbox(lon, lat, bbox):
                    continue
                properties = feature.setdefault("properties", {})
                raw_height = properties.get("height")
                height = float(raw_height) if raw_height is not None and float(raw_height) > 0 else None
                properties.update(
                    {
                        "source_record_id": stable_id("microsoft-global-ml", feature["geometry"]),
                        "source_dataset": "Microsoft Global ML Building Footprints",
                        "source_version": "2026-08-13",
                        "source_confidence": properties.get("confidence")
                        if properties.get("confidence", -1) >= 0
                        else None,
                        "height_m": height,
                        "height_source": "Microsoft ML height"
                        if height is not None
                        else "height unavailable",
                        "source_license": "CDLA Permissive 2.0",
                    }
                )
                properties.pop("height", None)
                yield feature


def write_collection(features: Iterable[dict], destination: Path, metadata: dict) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8") as stream:
        stream.write('{"type":"FeatureCollection","metadata":')
        json.dump(metadata, stream, separators=(",", ":"))
        stream.write(',"features":[')
        for feature in features:
            if count:
                stream.write(",")
            json.dump(feature, stream, separators=(",", ":"))
            count += 1
        stream.write("]}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("google", "microsoft"), required=True)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    args = parser.parse_args()
    bbox = tuple(args.bbox)
    if args.source == "google":
        if len(args.input) != 1:
            parser.error("Google clipping accepts exactly one input tile")
        features = google_features(args.input[0], bbox)
        dataset = "Google Open Buildings v3"
    else:
        features = microsoft_features(args.input, bbox)
        dataset = "Microsoft Global ML Building Footprints 2026-08-13"
    count = write_collection(
        features,
        args.output,
        {
            "dataset": dataset,
            "clip_bbox_wgs84": bbox,
            "clip_note": "Acquisition envelope for Mumbai and Navi Mumbai; not a legal boundary",
        },
    )
    print(f"wrote {count} {dataset} features to {args.output}")


if __name__ == "__main__":
    main()
