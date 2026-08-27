"""Clip a public Copernicus DEM COG to the frozen Kharghar AOI."""

from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_SOURCE = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_N19_00_E073_00_DEM/"
    "Copernicus_DSM_COG_10_N19_00_E073_00_DEM.tif"
)
DEFAULT_BBOX = (73.045, 19.010, 73.090, 19.075)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX)
    args = parser.parse_args()

    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open(args.source) as source:
        window = from_bounds(*args.bbox, transform=source.transform).round_offsets().round_lengths()
        data = source.read(window=window)
        profile = source.profile.copy()
        profile.update(
            height=data.shape[1],
            width=data.shape[2],
            transform=source.window_transform(window),
            compress="deflate",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(args.output, "w", **profile) as destination:
            destination.write(data)
            destination.update_tags(
                source_url=args.source,
                aoi_id="kharghar-v1",
                processing="window clip only; elevations unmodified",
            )
    print(f"Wrote Copernicus DEM clip to {args.output}")


if __name__ == "__main__":
    main()
