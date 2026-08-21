# Data and provenance policy

## Minimum manifest

Every external dataset must have a `SourceManifest` before its features can enter a scored run. The manifest records provider, direct citation URL, license, retrieval timestamp, version, temporal type/validity, spatial resolution and limitations. Copy `data/manifests/example-source-manifest.json` for new sources.

## Candidate public sources

These are candidates, not automatically approved dependencies. Confirm the AOI coverage, current terms and download path when implementing an adapter.

| Factor | Candidate source | Intended use | Caution |
|---|---|---|---|
| building geometry | Google Open Buildings v3 | immediate public polygon baseline | retain polygon confidence/version; validate AOI coverage and license obligations |
| building height | Google Open Buildings Temporal v1 | height raster sampled to candidate polygons | raster-derived estimate; preserve sampling method, resolution and missingness |
| building enrichment | GOBS state file requested from AEEE | optional height, floors, land-use and confidence attributes | request-only as verified 2026-08-22; not a runtime dependency; data dictionary does not promise polygons |
| building geometry | OpenStreetMap / local open GIS portals | footprints and access context | completeness varies; retain OSM timestamp and attribution |
| solar resource | NASA POWER | meteorology and solar resource time series | resolution is coarse for individual roofs |
| solar resource | Global Solar Atlas | long-term regional solar context | confirm permitted export/use for chosen workflow |
| elevation | Copernicus DEM or NASADEM/SRTM | terrain/elevation proxy | not a roof-surface model; resolution limits shading claims |
| weather reanalysis | ERA5/ERA5-Land | historical consistency and uncertainty tests | latency and spatial scale require documentation |
| grid context | OpenStreetMap and openly published utility layers | distance-to-grid proxy | does not provide hosting capacity or interconnection approval |
| costs/rent | official benchmark costs, open property listings or local surveys | early economic screening | time-sensitive, biased and often incomplete; show provenance/confidence |

## Storage zones

- `data/manifests/`: small, reviewable metadata committed to Git.
- `data/sample/`: tiny redistributable fixtures only.
- `data/raw/`: ignored; immutable downloads with checksums.
- `data/processed/`: ignored; reproducible derivatives.
- PostGIS: candidate geometries, feature tables and analysis runs.

## Rules

1. Never commit credentials, restricted imagery, personal data or bulk source rasters.
2. Keep the original CRS and checksum in ingestion metadata; use EPSG:4326 only for exchange.
3. Record units at the boundary and convert once.
4. Missing observations stay missing and reduce confidence; they are not silently changed to zero.
5. Every presentation claim links to a run ID, source manifests and validation output.
6. Record whether access is direct, request-only or credentialed. A request-only source cannot be a mandatory hackathon dependency.
7. Optional enrichment must use a documented spatial match and carry match confidence; never join independent files by row order.
8. Do not commit or redistribute requested bulk data until its terms permit it.

The accepted GOBS source hierarchy, fallback and owner actions are defined in [GOBS access finding and executable fallback](GOBS_ACCESS_AND_FALLBACK.md) and [ADR 0004](../architecture/decisions/0004-gobs-is-optional-enrichment.md).
