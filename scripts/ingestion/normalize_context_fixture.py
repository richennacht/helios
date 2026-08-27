"""Publish a small context fixture with explicit, stable source identity."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IDENTITY_FIELDS = {
    "source_id",
    "source_id_method",
    "source_dataset",
    "source_snapshot_date",
}


def normalize_layer(input_path: Path, output_path: Path, name: str, limit: int) -> None:
    collection = json.loads(input_path.read_text(encoding="utf-8"))
    for feature in collection["features"]:
        source_properties = {
            key: value
            for key, value in feature["properties"].items()
            if key not in IDENTITY_FIELDS
        }
        canonical = json.dumps(
            {"geometry": feature["geometry"], "properties": source_properties},
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        props = feature["properties"]
        props["source_id"] = f"osm-surrogate:{name}:sha256:{digest}"
        props["source_id_method"] = "sha256(canonical_geometry_and_preserved_tags)"
        props["source_dataset"] = "OpenStreetMap"
        props["source_snapshot_date"] = "2026-08-22"
    collection["features"].sort(key=lambda item: item["properties"]["source_id"])
    collection["features"] = collection["features"][:limit]
    output_path.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/sample/source_layers"))
    parser.add_argument("--roads-limit", type=int, default=25)
    parser.add_argument("--power-limit", type=int, default=20)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    normalize_layer(
        args.input_dir / "kharghar_roads.geojson",
        args.output_dir / "sample_kharghar_roads.geojson",
        "roads",
        args.roads_limit,
    )
    normalize_layer(
        args.input_dir / "kharghar_power.geojson",
        args.output_dir / "sample_kharghar_power.geojson",
        "power",
        args.power_limit,
    )
    print("Published small road and power fixtures with explicit source identity")


if __name__ == "__main__":
    main()
