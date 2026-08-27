"""Attach context-only Copernicus DEM observations to candidate GeoJSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from helios.features.terrain import sample_terrain


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--dem", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", default="copernicus-dem-glo30-n19-e073")
    args = parser.parse_args()

    collection = json.loads(args.candidates.read_text(encoding="utf-8"))
    for feature in collection["features"]:
        properties = feature["properties"]
        longitude = float(properties["source_centroid_lon"])
        latitude = float(properties["source_centroid_lat"])
        observation = sample_terrain(args.dem, longitude, latitude)
        properties.update(
            {
                "terrain_elevation_m": observation.elevation_m,
                "terrain_slope_deg": observation.slope_deg,
                "terrain_aspect_deg": observation.aspect_deg,
                "terrain_local_relief_m": observation.local_relief_m,
                "terrain_source_resolution_m": observation.source_resolution_m,
                "terrain_sampling_method": observation.sampling_method,
                "terrain_semantic_role": observation.semantic_role,
                "terrain_source_id": args.source_id,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(collection['features'])} terrain-enriched candidates to {args.output}")


if __name__ == "__main__":
    main()
