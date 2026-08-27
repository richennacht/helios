# Helios six-person atomic execution plan

## 1. Operating model

The team has five technically sound contributors and one non-technical contributor. Work is split by **data transformation boundary**, not by vague topics. Every person owns one input-to-output stage, one branch and one set of repository paths. Two people must never edit the same implementation files during the hackathon.

The fixed demonstration AOI is **Kharghar**. Helios remains a scouting-priority system for roughly 1,000–5,000 buildings, not a structural, legal or grid-interconnection approval system.

### Data-access correction — 2026-08-22

GOBS state files are request-only through the official contact route; the dashboard is not a raw-download API. The build therefore uses Google Open Buildings v3 polygons and Open Buildings Temporal v1 heights as its reproducible baseline. GOBS is optional enrichment if a file arrives and its terms permit use. Nobody waits for it. The exact source hierarchy, joins, proposed actions and per-person acceptance tests are in [GOBS access finding and executable fallback](data/GOBS_ACCESS_AND_FALLBACK.md).

## 2. Frozen handoff artifacts

These files are the interfaces between people. Real outputs may remain outside Git when large, but every branch must include a small fixture with the same schema.

| Artifact | Producer | Consumer | Minimum content |
|---|---|---|---|
| `source_manifest.json` | P1 | everyone | source, URL, license, version, retrieval time, CRS, date range and limitations |
| `candidate_buildings.geojson` | P1 | P2/P5 | `candidate_id`, polygon, source IDs and basic source attributes |
| `spatial_features.parquet` | P2 | P3/P4/P5 | area, fused height, roof elevation, terrain, access/grid distances, shading proxy and confidence |
| `solar_economic_features.parquet` | P3 | P4/P5 | yield, usable capacity, loss assumptions, capex/rent/payback proxies and confidence |
| `ranked_candidates.geojson` | P4 | P5/P6 | eligibility, components, total score, rank, stability and reason codes |
| `analysis_run.json` | P5 | P6 | run metadata, warnings, weights, candidates and provenance |
| `validation_labels.csv` | P6 | P4 | `candidate_id`, decision, reason codes, reviewer and review time |

Person 5 owns the schemas in `helios/contracts/`. Anyone needing a change opens an issue containing an example; they do not directly change the contract during parallel work.

---

## 3. Person 1 — Kharghar data and GIS engineer

### Single responsibility

Acquire, clean, document and package all external input data. Person 1 does **not** calculate suitability features, solar yield or candidate scores.

### Owned paths

- `data/manifests/`
- `data/sample/source_layers/`
- `scripts/ingestion/`
- `apps/geolibre/base_project/`
- `docs/data/`

### Step-by-step procedure

#### Step 1: freeze the AOI

Create one Kharghar boundary polygon, assign an AOI version such as `kharghar-v1`, and record its CRS, bounding box, area and acquisition source. Save the exchange copy as EPSG:4326 and choose one suitable projected CRS for distance/area calculations.

#### Step 2: register sources before downloading

Create a manifest record for every planned source. Use Google Open Buildings v3 for candidate polygons, Open Buildings Temporal v1 for baseline height, OpenStreetMap for roads and mapped power infrastructure, Copernicus GLO-30 for terrain context, and the selected solar/weather and economic proxy sources. Submit the GOBS Maharashtra state-file request and record its status as optional enrichment. Record licenses and temporal coverage before use.

#### Step 3: acquire building candidates

Clip Google Open Buildings v3 polygons to `kharghar-v1` and sample Temporal v1 height to them. Preserve source identifiers and source confidence. Create a stable Helios `candidate_id` for every polygon; never use row number as identity. If a GOBS file arrives, audit a small spatial match before enriching the batch; never join by row order.

#### Step 4: validate building data

Repair invalid polygons, remove exact duplicates, flag implausible areas/heights and quantify missingness. Do not invent missing height values. Preserve raw values, source availability, sampling/join method, match distance and source confidence. Keep requested bulk GOBS data outside Git unless redistribution is explicitly permitted.

#### Step 5: acquire contextual layers

Download or derive OSM roads and mapped power features for the AOI plus a buffer. Clip Copernicus terrain to the same buffer. Acquire the solar/weather and rent/cost inputs required by Person 3, but do not model them.

#### Step 6: harmonize coordinates and time metadata

Keep original CRS metadata, create projected working copies, and produce EPSG:4326 exchange files. Attach source dates and validity ranges; do not mix snapshots without a warning.

#### Step 7: build the GeoLibre base project

Load AOI, buildings, roads, power and terrain as read-only layers. Use relative paths, visible attribution and separate styles. Do not add ranking expressions—the ranked layer belongs downstream.

#### Step 8: publish the handoff fixture

Commit a redistributable 10–20-building sample, manifests and an import command. Store full datasets outside Git. The sample must contain the same fields as the full data.

#### Step 9: prove the handoff

Open the sample on a different checkout/path, confirm geometry validity and produce a data-quality summary: candidate count, missing heights, invalid features, date mismatches and source coverage.

### Completion signal

Person 2 can load `candidate_buildings.geojson` and all required context layers without contacting Person 1 or manually renaming fields.

### Explicit exclusions

No roof suitability calculations, shading equations, PV modelling, ranking, API work or presentation claims.

---

## 4. Person 2 — spatial roof-feature engineer

### Single responsibility

Transform canonical GIS layers into comparable physical and proximity features for each building. Person 2 never downloads production datasets and never computes energy or money metrics.

### Owned paths

- `helios/features/spatial/`
- `tests/features/spatial/`
- `data/sample/features/spatial/`
- `docs/features/SPATIAL_FEATURES.md`

### Step-by-step procedure

#### Step 1: begin from the fixture

Load Person 1's sample or the contract fixture supplied by Person 5. Verify `candidate_id`, geometry, CRS and required source IDs. Fail clearly if any are missing.

#### Step 2: compute footprint geometry

Calculate polygon area, perimeter, compactness and any simple orientation measure in the projected CRS. Retain source area separately so differences are auditable.

#### Step 3: fuse height evidence

Implement documented height handling for one source, multiple sources or no height. Temporal v1 is the baseline observation; an audited GOBS match may be added as optional evidence. Output the fused value, contributing sources, disagreement range and height confidence. Missing evidence remains null with low confidence.

#### Step 4: add terrain context

Sample terrain elevation at or around each building, then calculate approximate roof elevation as terrain plus fused building height. Add local terrain slope/context only at the resolution the DEM can support.

#### Step 5: calculate accessibility

Compute projected distance from each building to the nearest mapped road. Return both the distance and the matched source feature ID.

#### Step 6: calculate grid-proximity proxy

Compute projected distance to the nearest mapped power/substation feature. Name it `grid_distance_m` and explicitly label it as a proximity proxy—not hosting capacity.

#### Step 7: calculate a shading proxy

Use the available height/terrain neighbourhood to create a coarse obstruction factor with a confidence flag. Do not call it a measured shade study. If data resolution is insufficient, return a neutral or missing value plus a limitation code.

#### Step 8: validate physical sanity

Test units, non-negative distances, valid ranges, determinism and behaviour for missing height/road/grid data. Visually spot-check at least five buildings in GeoLibre.

#### Step 9: publish one row per candidate

Write `spatial_features.parquet` keyed only by `candidate_id`, plus a small CSV/JSON fixture and a schema document. Never copy source polygons into ad hoc columns.

### Completion signal

Person 3 and Person 4 can join the file by `candidate_id`, understand every unit and reproduce the same values from the sample.

### Explicit exclusions

No data scraping, irradiance/PV calculations, capex/rent modelling, weighting, ranking, database or UI work.

---

## 5. Person 3 — solar and techno-economic engineer

### Single responsibility

Convert spatial features plus registered solar/weather/cost inputs into physics-informed generation and early-economic features. Person 3 does not rank buildings.

### Owned paths

- `helios/features/solar/`
- `helios/features/economics/`
- `tests/features/solar/`
- `tests/features/economics/`
- `data/sample/features/solar_economics/`
- `docs/features/SOLAR_ECONOMICS.md`

### Step-by-step procedure

#### Step 1: lock modelling assumptions

Document module efficiency, performance ratio, usable-area factor, system losses, degradation treatment, reference period, cost basis and currency date. Use one assumption set for the entire AOI.

#### Step 2: load only registered inputs

Consume Person 1's cited irradiance/weather/economic inputs and Person 2's area, height and shading-proxy fields. Reject unregistered manual numbers.

Do not require GOBS floor or land-use attributes. When they are absent, preserve nulls and propagate the reduced confidence or sensitivity rather than changing the model formula silently.

#### Step 3: determine usable PV capacity

Convert usable roof area into an estimated installable `kWp` using the declared packing/area assumption. Preserve the intermediate value and its confidence.

#### Step 4: model annual solar yield

Use pvlib or an equivalent physics-informed calculation to estimate annual generation. Apply shading only as a documented proxy loss. Record resource period, model version and loss components.

#### Step 5: estimate cost and rent proxies

Calculate indicative capex and, where source data allows, roof rent. Keep unavailable rent null; never replace it with zero. Normalize dates/currency before comparison.

#### Step 6: derive interpretable economics

Calculate simple annual energy value, yield-to-cost and indicative payback. Do not claim a bankable return, tariff guarantee or legal lease feasibility.

#### Step 7: propagate confidence

Combine source quality, temporal match, spatial resolution and missingness into separate solar and economics confidence fields. Keep the method deterministic.

#### Step 8: benchmark calculations

Hand-check at least three candidate calculations and compare expected yield per kWp against a reasonable Kharghar range. Investigate implausible outputs instead of clipping silently.

#### Step 9: publish the handoff

Write one `solar_economic_features.parquet` row per `candidate_id`, include units/provenance, and publish a small fixture plus a command that recreates it.

### Completion signal

Person 4 can rank the fixture without knowing pvlib, rent-source formats or any hidden spreadsheet formula.

### Explicit exclusions

No source acquisition, GIS distance processing, rank weights, ML training, API persistence or presentation design.

---

## 6. Person 4 — ranking, confidence and ML engineer

### Single responsibility

Turn standardized candidate features into eligibility decisions and explainable rankings, then measure ranking robustness. This person may be the project lead working on ML.

### Owned paths

- `helios/ranking/`
- `helios/explanations/`
- `tests/test_ranking.py`
- `tests/ranking/`
- `docs/evaluation/`

### Step-by-step procedure

#### Step 1: define ranking inputs

Read only the contract fields emitted by Persons 2 and 3. Create a feature dictionary with directionality, units, missing-value policy and confidence treatment.

#### Step 2: implement hard exclusions

Apply minimum usable area, maximum screening distance, budget and required-data constraints before scoring. Excluded candidates receive reason codes and no rank.

#### Step 3: normalize within the run

Implement a documented, deterministic normalization method. Fit it on the eligible candidates in the same AOI/run and persist its parameters.

#### Step 4: implement scenario MCDA

Provide balanced, energy-first and cost-first weight sets that sum to one. Calculate component contributions and the final score exactly once in `helios/ranking/`.

#### Step 5: generate deterministic explanations

Select the strongest positive factors and meaningful cautions from component values and confidence. Do not use an LLM for ranking or factual explanations.

#### Step 6: measure rank stability

Perturb uncertain inputs and allowed weight ranges, then calculate top-K overlap and rank intervals. Add a source-availability scenario that masks all GOBS-derived fields and compare it with any enriched run. Mark unstable candidates instead of hiding variation, and never reward candidates simply for having more observed fields.

#### Step 7: evaluate baselines

Once Person 6 supplies reviewed labels, calculate Precision@K, Recall@K and nDCG for manual, solar-only, equal-weight and balanced baselines.

#### Step 8: attempt the optional challenger

Only if labels are sufficient, train a lightweight ranker or tree model behind the same interface. Keep it out of the demo path unless held-out metrics improve and explanations remain defensible.

#### Step 9: publish the handoff

Return ranked candidate records with eligibility, components, total score, rank, stability and reason codes. Include tests proving deterministic output and exclusion behaviour.

### Completion signal

Person 5 can call one ranking interface with fixture features and receive contract-valid results without importing notebooks or model-training code.

### Explicit exclusions

No GIS collection, physical/solar feature generation, database routing, dashboard styling, field review or slide claims.

---

## 7. Person 5 — platform and integration engineer

### Single responsibility

Own the stable contracts and move artifacts through FastAPI/PostGIS into GeoJSON. Person 5 wires modules together but does not rewrite their scientific logic.

### Owned paths

- `helios/contracts/`
- `helios/pipeline/`
- `helios/storage/`
- `apps/api/`
- `tests/test_api.py`
- `tests/integration/`
- `docker-compose.yml`
- `.github/workflows/`
- database migrations and configuration

### Step-by-step procedure

#### Step 1: freeze contract v1

Publish example request, source manifest, feature and result objects before parallel development. Add contract-validation tests. After freezing, accept changes only through a reviewed schema proposal.

#### Step 2: build fixture-first adapters

Create loader interfaces for P1, P2, P3 and P4 outputs using sample files. Each loader validates IDs, units, required columns and provenance; it never silently renames fields. Keep the public Open Buildings baseline mandatory and the GOBS loader optional. Absence of GOBS emits a source-capability warning rather than failing the run.

#### Step 3: design PostGIS persistence

Create tables and migrations for sources, candidates, feature versions, analysis runs and ranked results. Store geometry with explicit SRID and retain original run inputs.

#### Step 4: implement staged orchestration

Represent the run as clear stages: validate request → load sources → join features → filter/rank → persist → emit result. Return stage-specific errors with run and source context.

#### Step 5: complete API endpoints

Keep create, fetch, rerank and GeoJSON routes compatible with `docs/api/API_CONTRACT.md`. Add run status and warnings without changing scientific values.

#### Step 6: create the fusion join

Join P2 and P3 feature tables strictly on `candidate_id`, verify one-to-one cardinality and report missing or duplicate IDs. Pass the validated frame to P4 without recomputing features.

#### Step 7: connect GeoLibre delivery

Return EPSG:4326 GeoJSON with eligibility, rank, component scores, confidence, reasons and provenance IDs. Do not embed map-specific ranking expressions.

#### Step 8: automate quality gates

Run lint, unit, contract and end-to-end fixture tests in CI. A branch cannot enter `integration` if its artifact fails the consumer's loader.

#### Step 9: package the demo runtime

Provide one command to start the API/database and one command or request to load the cached demonstration run. Verify from a clean clone.

### Completion signal

Person 6 can run the demonstration and retrieve a candidate explanation without a developer manually editing the database or JSON.

### Explicit exclusions

No dataset research, spatial equations, PV/economic equations, ranking design, manual labels or presentation claims.

---

## 8. Person 6 — validation, evidence and demo owner (non-technical)

### Single responsibility

Own human review, evidence traceability and the final demonstration. This role is intentionally operational and requires no production coding.

### Owned paths

- `docs/product/`
- `docs/demo/`
- `data/sample/validation/`
- validation form content in `apps/geolibre/field_forms/`

### Step-by-step procedure

#### Step 1: learn the decision boundary

Read the short product statement and limitations. Be able to explain that Helios prioritizes inspection; it does not approve structural safety, leases or grid connection.

#### Step 2: define the review rubric

Use three labels: `inspect`, `uncertain`, `reject`. For each, define plain-language reason codes such as insufficient visible roof area, severe obstruction, poor access or data uncertainty.

#### Step 3: prepare the blind review sheet

Create `validation_labels.csv` with candidate ID, reviewer, decision, reason codes, review time and notes. Hide Helios rank while initial labels are assigned to reduce bias.

#### Step 4: run the traditional baseline

Using the same AOI and a fixed time limit, manually identify promising buildings using the team's old scouting method. Record time taken and selected IDs; do not change the method after seeing Helios results.

#### Step 5: review the Helios shortlist

After labels and baseline are locked, inspect the Helios top-K in GeoLibre. Record disagreements, obvious data failures and candidates that need field verification.

#### Step 6: maintain the evidence ledger

For every number intended for slides, record the source run ID, metric, sample size and file or link. Mark each run `fallback-only` or `GOBS-enriched`, and record the GOBS request status separately. If evidence is absent, change “improves” to “designed to improve.” Never describe the request-only GOBS state file as a direct public download.

#### Step 7: write the demo script

Prepare a 3–5 minute sequence: select Kharghar → show sources and warnings → display ranking → open one candidate → change scenario → compare baseline → state limitations.

#### Step 8: prepare visual proof

Capture approved screenshots of the AOI, ranked layer, candidate explanation, scenario change and evaluation result. Check spelling, units and consistency with the live system.

#### Step 9: rehearse and record failure notes

Run the script twice from the cached demo. Write one-line fallbacks for internet, API or model failure and note which teammate answers each technical question.

### Completion signal

The team can present only defensible claims, reproduce the demo order and show a fair comparison with traditional scouting.

### Explicit exclusions

No editing Python, database schemas, rank weights, source data, scientific assumptions or production configuration.

---

## 9. How Codex will combine the work

Codex acts as merge integrator, not a seventh feature owner.

1. **Freeze:** verify P5 contract fixtures on `integration` before any feature merge.
2. **Inspect:** for each branch, compare changed paths with that person's ownership boundary. Reject collisions or unrelated edits.
3. **Validate producer:** run that person's unit tests and regenerate the small handoff fixture.
4. **Validate consumer:** run the next person's loader against the fixture; a producer is not complete until the consumer succeeds.
5. **Merge in order:** P1 data metadata → P2 spatial engine → P3 solar/economics → P4 ranking → P5 runtime wiring → P6 evidence.
6. **Run one-candidate gate:** pass one real Kharghar candidate through all modules and display it in GeoLibre.
7. **Scale gate:** only after the one-candidate path passes, run the batch AOI.
8. **Freeze demo:** after Day 3 feature freeze, accept only reproducibility, correctness or demo-blocking fixes.

Codex will not resolve a scientific disagreement by averaging two implementations. The owner of the affected stage must provide the corrected artifact and evidence.

## 10. Three-day synchronization points

### Day 1, Hour 0–2: contract freeze

P5 publishes schemas and fixtures. P1 submits the GOBS request and starts the Open Buildings v3 plus Temporal v1 public fallback immediately. P2–P4 build against fixtures without waiting for GOBS. P6 prepares the rubric, baseline sheet and source-access claim wording.

### Day 1, Hour 6: first artifact review

Each technical person demonstrates their fixture-to-output command. P6 demonstrates a completed dummy review row. No slides are built yet.

### Day 1, Hour 12: one-real-candidate gate

The same `candidate_id` must exist in P1 data, P2 features, P3 features, P4 result, P5 API and P6 review sheet.

### Day 2, Hour 8: batch and validation gate

Run the frozen Kharghar batch, collect top-K labels and compare at least the manual and solar-only baselines. If GOBS enrichment is available, also record fallback-only versus enriched top-K overlap; otherwise report the fallback-only run without delay.

### Day 2 end: feature-freeze candidate

GeoLibre renders the shortlist; reranking works; source warnings and explanations are visible; quantitative evidence is stored.

### Day 3 midday: hard feature freeze

Only defect fixes. P6 owns rehearsal; P5 owns runtime reliability; P1–P4 remain available for their subsystem only.

## 11. Non-collision rules

1. A person edits only owned paths. Root `README.md`, shared workflow docs and cross-cutting configuration are integrator-owned unless explicitly assigned.
2. P1 supplies data; P2 and P3 never add hidden downloads to feature code.
3. P2 supplies spatial features; P3 never recalculates geometry or grid distance.
4. P3 supplies energy and economics; P4 never embeds PV or rent formulas in ranking.
5. P4 supplies ranking; P5 never creates alternate weights or scores inside API routes.
6. P5 supplies contracts and runtime; others request schema changes rather than modifying them.
7. P6 supplies labels and claims; technical owners never alter human labels to improve metrics.
8. Every artifact is keyed by stable `candidate_id`; handoffs never depend on row order.
