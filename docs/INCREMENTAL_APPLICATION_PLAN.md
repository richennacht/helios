# Incremental application plan

This is the implementation plan for the shared Helios application. It replaces a feature-by-feature demo with one small working path that can grow safely.

## Slice 1: visible map and AOI

1. Person 1 keeps the GeoLibre viewer loading from a clean clone and adds rectangle and free-form polygon drawing.
2. The UI displays the selected shape, its area, coordinate system and a clear reset button.
3. The UI sends the shape as GeoJSON. No factor is allowed to read the map’s internal state directly.
4. Person 5 adds AOI validation: valid geometry, reasonable size, supported CRS and a useful error message.
5. Person 6 checks the same three shapes from the browser and records screenshots and timings.

**Done means:** a teammate can open the hosted preview, draw a shape, reload it from the run payload, and see the same shape again.

## Slice 2: one real candidate factor

1. Person 2 clips the checked-in building source to the AOI and emits stable `candidate_id` values.
2. Person 2 adds height/roof/terrain fields using the factor contract.
3. Person 5 exposes `POST /analysis-runs` and a GeoJSON result endpoint.
4. Person 4 ranks the candidates with one transparent baseline score and returns reason codes.
5. Person 1 colours candidates by score and opens a popup with the value, confidence and source.

**Done means:** one drawn Kharghar polygon produces a visible candidate layer and a ranked table without hand-editing a file.

## Slice 3: add factors one at a time

For each new dataset, the owner must provide a registry entry (format, CRS, date, licence, coverage and download URL), an AOI adapter, a factor output using the common schema, a fixture and missing-data case, and a short browser demonstration.

The factor is then enabled in the run request. Existing runs remain reproducible because the request stores factor IDs, dataset versions and assumptions.

## Run contract

```json
{
  "aoi": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}},
  "factor_ids": ["building_height", "terrain", "solar_resource"],
  "dataset_ids": ["osm_buildings_kharghar", "copernicus_glo30"],
  "assumption_version": "mvp-1"
}
```

Every factor result contains `candidate_id`, `value`, `unit`, `confidence`, `source`, `dataset_version` and `warnings`. The final response contains candidates, rank, component scores, exclusions, explanations and a run manifest.

## Vercel preview

The root `vercel.json` maps `/` to the static Kharghar viewer. Vercel can deploy this repository without a build command. The preview is for visual review of the application shell and experimental 3D layer; the Python API remains a separate service until it is hosted.
