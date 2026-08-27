"""Create a reproducible acquisition plan for a regional Helios AOI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bbox", nargs=4, type=float, required=True,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
    )
    parser.add_argument("--aoi-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    west, south, east, north = args.bbox
    # Copernicus DEM COGs are named by their integer 1-degree southwest tile.
    dem_tiles = [
        {
            "lat": lat,
            "lon": lon,
            "url": f"https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM/Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM.tif",
        }
        for lat in range(int(south), int(north) + 1)
        for lon in range(int(west), int(east) + 1)
    ]
    plan = {
        "aoi_id": args.aoi_id,
        "bbox_wgs84": [west, south, east, north],
        "copernicus_dem_tiles": dem_tiles,
        "building_geometry": {
            "provider": "Google Open Buildings v3",
            "citation_url": "https://sites.research.google/gr/open-buildings/",
            "action": (
                "enumerate intersecting S2 level-4 shards, download outside Git, "
                "filter by approved boundary"
            ),
        },
        "solar_resource": {
            "provider": "Global Solar Atlas",
            "citation_url": "https://globalsolaratlas.info/download/india",
            "action": "export Maharashtra-only raster/tiles after confirming account terms",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(dem_tiles)} Copernicus tile entries to {args.output}")


if __name__ == "__main__":
    main()
