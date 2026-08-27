# GOBS access finding and executable fallback

## Verified finding

**Access status verified 2026-08-22.** The GOBS dashboard is an aggregate exploration interface. It does not expose a direct raw-data download button or a stable public `.csv.gz` URL. State-level files are requested through the official [GOBS contact form](https://gobs.aeee.in/contact) by choosing **Require State Files for Download**, or by contacting `gobs@aeee.in`.

The GOBS [About page](https://gobs.aeee.in/about) describes compressed state CSV files with fields including location, footprint confidence, area, perimeter, height, estimated floor count, land use, total built-up area, prediction flags and administrative labels. Its public data dictionary does not promise polygon geometry. The dashboard and downloadable file may also differ because the dashboard applies AEEE visualization assumptions.

This is an access constraint, not a reason to scrape the dashboard or pause development.

## Accepted source hierarchy

| Need | Primary hackathon source | Optional enrichment | Required output metadata |
|---|---|---|---|
| building polygons | [Google Open Buildings v3](https://sites.research.google/gr/open-buildings/) | other licensed local or OSM footprints | source ID, polygon confidence, retrieval/version and license |
| building height | [Google Open Buildings Temporal v1](https://sites.research.google/gr/open-buildings/temporal/) sampled to each polygon | GOBS height, estimated floors and prediction confidence | source, sampling rule, missingness and confidence |
| land-use/context | OpenStreetMap and other approved public layers | GOBS land-use field | source date, matched feature and match confidence |
| GOBS attributes | none required | requested Maharashtra state file | request date, received version, terms and spatial-match method |

Google Open Buildings v3 is the immediate candidate-geometry source. Google Open Buildings Temporal v1 is the immediate height source. A GOBS state file, if received in time and permitted by its terms, enriches those candidates; it never becomes a runtime prerequisite.

## Join and provenance rules

1. Never join a GOBS CSV to Open Buildings polygons by row order.
2. Prefer a documented spatial join using coordinates/centroids and administrative fields; use plus codes only when their precision is compatible.
3. Emit `source_ids`, `source_availability`, `spatial_match_method`, `spatial_match_distance_m` and `match_confidence` for every enrichment.
4. Preserve conflicting source observations. Person 2 may fuse them only through a documented rule that returns disagreement and confidence.
5. Keep GOBS-derived bulk data outside Git until its access and redistribution terms are confirmed. Commit only a manifest and a tiny sample when redistribution is explicitly allowed.
6. Do not reverse-engineer Firebase calls, scrape dashboard aggregates as building records or present dashboard values as the raw downloadable dataset.

## Proposed actions

### P0 — start immediately

1. Person 1 submits one Maharashtra request through the GOBS contact form and records the request timestamp and purpose in a manifest note.
2. Person 1 downloads/clips Google Open Buildings v3 polygons for `kharghar-v1` and samples Temporal v1 building height for those polygons.
3. Person 5 keeps GOBS fields nullable and adds source-capability warnings so the same pipeline accepts fallback-only and GOBS-enriched runs.
4. Persons 2–4 continue from fixtures and public fallback data; nobody waits for a GOBS response.
5. Person 6 changes all demo language from “GOBS data downloaded” to “public Open Buildings baseline, optionally enriched by requested GOBS attributes.”

### P1 — before the batch gate

1. Publish a fallback-only data-quality report: polygon count, confidence distribution, height coverage, spatial resolution and missingness.
2. Run one candidate end to end with source availability visible in the API and GeoLibre explanation.
3. If GOBS arrives, spatially match a small audited sample first; measure match rate and disagreement before enriching the batch.
4. Person 4 evaluates top-K overlap and rank stability with the GOBS-dependent fields masked, so the demo result is not fragile to their absence.

### P2 — only if time remains

1. Compare fallback-only and GOBS-enriched runs using identical assumptions and candidates.
2. Keep an enrichment only when it improves a recorded validation metric, data coverage or explanation quality.
3. Report the result as an ablation, not as proof that GOBS is universally superior.

## Six-person impact

| Person | Important difference | New acceptance test |
|---|---|---|
| **1 — data/GIS** | GOBS becomes a request-and-enrichment task. Candidate polygons come from Open Buildings v3 now; heights come from Temporal v1. | A clean checkout can reproduce a 10–20 candidate fallback fixture without a GOBS file. |
| **2 — spatial features** | Height fusion must accept one source, multiple sources or no height. GOBS floor/height fields are optional evidence, not required columns. | The same command succeeds for fallback-only and enriched fixtures and reports disagreement/confidence. |
| **3 — solar/economics** | Solar modelling consumes area, height/shading and their confidence; it must not assume GOBS land use or floors exist. | Yield output remains valid with nullable enrichment fields and sensitivity reflects lower spatial confidence. |
| **4 — ranking/ML** | Source availability and missingness become explicit uncertainty scenarios. Rankings must not reward a candidate merely for having more source coverage. | Report top-K overlap/rank stability with GOBS-derived fields present versus masked; abstain when confidence is inadequate. |
| **5 — platform** | Build capability-aware adapters: mandatory public baseline plus optional GOBS loader. No dashboard scraping or hidden network dependency. | API exposes source/version/warnings and runs identically when the optional GOBS adapter is disabled. |
| **6 — validation/demo** | Track the GOBS request and police claims. Demonstrate provenance and the fallback rather than promising unavailable data. | Evidence ledger identifies whether each run is fallback-only or enriched and never labels a request-only file as publicly downloadable. |

## Decision consequence

This finding reduces delivery risk while creating a stronger research/evaluation angle: Helios can quantify how source availability changes confidence and rank stability. The demonstrable improvement remains faster, reproducible regional scouting versus manual inspection—not mere access to one dataset.
