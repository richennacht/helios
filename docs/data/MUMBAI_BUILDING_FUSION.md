# Mumbai and Navi Mumbai building fusion

The previous 15 Google records were a handoff fixture, not Open Buildings
coverage. The metro acquisition now uses the envelope
`72.75,18.85,73.25,19.35` and the source registry in
`data/manifests/mumbai-navi-mumbai-building-sources.json`.

The acquired footprint catalogues contain:

- Google Open Buildings v3: 1,627,685 detections;
- Microsoft Global ML Building Footprints: 466,651 detections;
- Overture Buildings: 1,061,226 records, including 20,640 published height
  values and 7,317 published floor counts.

Eight Google Temporal manifests (2016-2023) and four WSF3D metric rasters are
also acquired. Raw and metro-clipped artifacts live under ignored `data/raw`
and `data/processed` folders because the footprint extracts exceed 1.5 GB.
Only the reproducible adapters, registry, compact demo extracts, and tests
belong in Git.

## Queryable catalogue

`scripts/ingestion/build_building_catalog.py` builds a SQLite catalogue with an
RTree index. The local build contains **3,155,562 source observations**:

- Google Open Buildings v3: 1,627,685
- Microsoft Global ML Building Footprints: 466,651
- Overture Buildings: 1,061,226

The database is intentionally a generated, Git-ignored artifact. Rebuild it
with:

```powershell
py -3 -m scripts.ingestion.build_building_catalog `
  data/processed/buildings/mumbai-navi-mumbai-buildings.sqlite `
  --google data/processed/buildings/mumbai-navi-mumbai-google-v3.geojson `
  --microsoft data/processed/buildings/mumbai-navi-mumbai-microsoft-2026.geojson `
  --overture data/raw/buildings/mumbai-navi-mumbai-overture-2026-07-22.jsonl
```

Create a browser-sized fused view with `--query-bbox W S E N --output
view.geojson`. A validation query over `[73.04, 19.02, 73.10, 19.09]` read
47,987 observations and returned 26,369 building candidates; 16,520 candidates
had records from more than one source.

## Fusion rules

1. Keep each source record and its license/version before deduplication.
2. Match polygons spatially, never by row number. Require meaningful overlap;
   centroid proximity is only a candidate-index shortcut.
3. Average positive current-height measurements when independent sources refer
   to the same building. If only one source has height, retain that value.
4. Keep annual 2016-2023 heights as a time series. Only the selected/reference
   year participates in a current-height mean.
5. Do not count a fused catalogue and its named upstream inputs as independent
   votes. Preserve Overture/OpenBuildingMap/GlobalBuildingAtlas lineage.
6. A missing height remains null. No 6 m or floors-based value is silently
   inserted. A floors-times-storey-height estimate, if enabled later, must be a
   separately labelled model observation.

The downloaded WSF3D tile covers only the southeast part of the acquisition
envelope (east of roughly 73 E and south of roughly 19 N). It is registered as
partial coverage and is not silently applied to the uncovered metro area.

## Imagery inference adapter

Yes, a detector can create new boundaries from imagery. The recommended open
prototype is Raster Vision's published SpaceNet building segmentation model:
orthorectified high-resolution imagery is tiled, normalized, segmented into a
building-probability mask, polygonized, regularized, and written as another
source-labelled footprint layer. TorchGeo supplies CRS-aware SpaceNet datasets
and training infrastructure.

For a stronger footprint-plus-height research path, GlobalBuildingAtlas
publishes development code for satellite-image-to-building-footprint (`im2bf`)
and monocular building-height (`im2bh`/`infer_height`) pipelines. Its code and
height products have non-commercial restrictions, so they are an experimental
adapter—not a silently enabled production dependency.

Single-image height is a model estimate, not a measurement. Helios must store
the model/version, source imagery date and resolution, uncertainty, and
validation status. For Mumbai deployment, calibrate against local stereo/DSM,
LiDAR, surveyed heights, or a manually labelled validation sample before using
predicted height in ranking.
