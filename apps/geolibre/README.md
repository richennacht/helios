# GeoLibre workspace contract

GeoLibre is the collection, inspection and visualization surface for Helios. The API remains the source of ranking logic. The application is incremental: the user draws an area of interest first, then the server runs only the enabled, versioned factors inside that area.

## User flow

1. Open the shared preview or local viewer.
2. Draw a rectangle or custom polygon around the region to inspect.
3. Review or reset the boundary.
4. Choose factors and start an analysis run.
5. Inspect the candidate layer, ranked table, explanations, confidence and data warnings.

The map sends the selected shape to the API as GeoJSON. It must never invent a candidate outside that shape or hide missing data.

## MVP setup

1. Start the API and create a run from `data/sample/analysis-request.json`.
2. Add `http://localhost:8000/analysis-runs/{run_id}/candidates.geojson` as a GeoJSON/HTTP layer, or save the response locally.
3. Style eligible candidates by `rank` or `total_score` and excluded candidates separately.
4. Configure popups for component confidence, positive reasons and cautions.
5. Keep source layers read-only; use a separate validation layer/form for reviewer labels.

## Required visual layers

- AOI boundary;
- source building footprints;
- eligible candidates graduated by score;
- excluded candidates with reason codes;
- grid asset/proximity context labelled as proxy;
- optional elevation/shading proxy;
- field/expert validation points.

## Portability

Store relative paths, project CRS and attribution in the project. Do not commit local caches, credentials or restricted layers. A future checked-in `.qgz`/GeoLibre project must open after cloning into a different directory.

## Shared preview

The experimental Kharghar scene is the current visible shell and is served at `/` by the root Vercel configuration. It is useful for checking map, terrain and building presentation while the versioned analysis-run API is built.
