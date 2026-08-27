"""Convert a bounded OSM XML map extract into 3D-ready building GeoJSON."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    return float(match.group()) if match else None


def convert(source: Path, destination: Path) -> int:
    root = ET.parse(source).getroot()
    nodes = {
        element.attrib["id"]: (
            float(element.attrib["lon"]),
            float(element.attrib["lat"]),
        )
        for element in root.findall("node")
    }
    features: list[dict[str, object]] = []
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib.get("v", "") for tag in way.findall("tag")}
        if "building" not in tags:
            continue
        coordinates = [nodes[nd.attrib["ref"]] for nd in way.findall("nd") if nd.attrib["ref"] in nodes]
        if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
            continue
        height = number(tags.get("height"))
        levels = number(tags.get("building:levels"))
        if height is None and levels is not None:
            height = round(levels * 3.0, 2)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "osm_way_id": int(way.attrib["id"]),
                    "building_type": tags["building"],
                    "name": tags.get("name") or None,
                    "height_m": round(height, 2) if height is not None else None,
                    "height_source": "OSM height tag"
                    if tags.get("height")
                    else "OSM building:levels × 3 m"
                    if levels is not None
                    else "OSM height unavailable",
                    "building_levels": levels,
                    "source_dataset": "OpenStreetMap",
                    "source_license": "ODbL 1.0",
                    "source_extract": "https://api.openstreetmap.org/api/0.6/map?bbox=73.055,19.030,73.085,19.065",
                },
                "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            }
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "kharghar-osm-buildings-3d",
                "metadata": {
                    "description": "Bounded OSM building extract for exploratory 3D visualization",
                    "retrieved_from": "https://api.openstreetmap.org/api/0.6/map",
                    "retrieval_bbox": [73.055, 19.030, 73.085, 19.065],
                    "height_policy": "OSM height, then building levels × 3 m; missing values remain null",
                },
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return len(features)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(f"converted {convert(args.source, args.destination)} building polygons")


if __name__ == "__main__":
    main()
