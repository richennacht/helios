# Helios

Helios is a regional solar-site discovery and scouting platform. It converts a selected area of interest into an explainable, uncertainty-aware shortlist of rooftop candidates worth inspecting first.

The application is being built as an incremental, visible product: the map and a small working analysis come first; new datasets and scoring factors are added one at a time through stable contracts. This keeps every change demonstrable in the browser and prevents a half-integrated collection of models from becoming the product.

The hackathon MVP is deliberately narrow: evaluate 1,000-5,000 buildings in one compact region, calculate comparable technical and early-economic features, rank the candidates, and visualize the results in GeoLibre.

## What Helios does

```text
Region + scenario + reference window
  -> source adapters
  -> temporal/provenance checks
  -> candidate discovery
  -> geometry and shading features
  -> solar-yield features
  -> grid-proximity and economic features
  -> hard filters
  -> MCDA / Pareto / rank stability
  -> GeoLibre-ready shortlist
```

Helios is a screening tool. It does not replace structural inspection, utility interconnection studies, legal approval, or detailed EPC design.

## Repository status

This baseline establishes the shared contracts and collaboration surface for Team REverb. It includes:

- FastAPI application skeleton;
- versioned Pydantic contracts;
- deterministic ranking and explanations;
- staged pipeline interfaces;
- source provenance and temporal-consistency models;
- GeoLibre delivery conventions;
- Docker/PostGIS development setup;
- unit and API tests;
- GitHub Actions CI;
- issue and pull-request templates;
- six-person atomic ownership and three-day integration plan.

The current product direction is the **AOI analysis workspace**. A user draws a rectangle or free-form polygon on the map, chooses the factors to run, and receives only the buildings and scores that fall inside that shape. The first slice uses the Kharghar viewer and real public building/terrain inputs; later slices add solar, grid and economic factors without changing the drawing workflow.

## Run the visible application

The quickest local preview is the checked-in GeoLibre/MapLibre viewer:

```powershell
cd apps/geolibre/experimental/kharghar-3d
python -m http.server 8765
```

Open <http://localhost:8765/>. This is a visual sandbox, not yet the official ranking API. It is the first shared surface for checking map behaviour, data provenance and 3D presentation.

The intended hosted preview is the Vercel deployment of this repository. Vercel serves the same viewer at `/`, so a commit on the shared integration branch becomes the team’s visible source of truth. The deployment is deliberately static at this stage; the FastAPI service remains a separate local/container service until the analysis endpoint is ready for hosting.

## Product workflow (current target)

```text
draw rectangle or polygon
  -> validate AOI (closed, valid, supported size/CRS)
  -> load registered datasets for that AOI
  -> discover building candidates
  -> run enabled factor plug-ins
  -> apply hard exclusions
  -> rank with confidence and missing-data warnings
  -> show coloured candidates, table, explanations and provenance
```

An analysis run is reproducible: it records the AOI GeoJSON, enabled factor IDs, dataset versions, assumptions and timestamp. Adding a factor must not silently change an earlier run.

### Factor plug-in contract

Each factor is an independent calculator. It receives a candidate and the selected AOI context and returns a value, unit, confidence, source/version and warnings. The ranking layer combines these standardized results; it does not know how a height raster, irradiance series or rent CSV was produced. Missing data is reported as missing, never quietly replaced with zero.

Initial factor order:

1. footprint and candidate discovery;
2. building height, roof area and terrain;
3. solar resource and usable roof estimate;
4. grid/access proximity proxies;
5. early economics and scenario ranking;
6. uncertainty, stability and human validation.

## New team allocation for the main application

Ownership is now by module, not by a list of loosely connected features. Each person can work independently against the shared contracts and produce a visible result.

| Owner | Single responsibility | Visible result |
|---|---|---|
| Person 1 | AOI map shell, drawing tools and source-layer loading | Drawn rectangle/polygon and visible footprints |
| Person 2 | Spatial factor plug-ins (height, terrain, roof geometry) | Per-building spatial attributes and coloured layer |
| Person 3 | Solar and early-economic factor plug-ins | Solar/yield/economic fields in the candidate table |
| Person 4 | Ranking, explanations, confidence and stability | Ordered shortlist, reason codes and uncertainty panel |
| Person 5 | API, dataset registry and run orchestration | One run contract connecting UI, factors and output GeoJSON |
| Person 6 | Validation, evidence and demo acceptance | Reproducible demo script, checks, screenshots and claim ledger |

The handoff rule is simple: a person publishes their module through the contract and a small fixture; they do not edit another owner’s module to make an integration pass. Person 5 wires modules together only after the fixture and contract checks pass. Person 6 verifies the result from the browser and records what is actually demonstrated.

See [the incremental execution plan](docs/INCREMENTAL_APPLICATION_PLAN.md) for the step-by-step build order and handoff criteria.

## Quick start

### Prerequisites

- Python 3.11+
- Git
- Docker Desktop (optional, for PostGIS)

### Local API

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn apps.api.main:app --reload
```

Open:

- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

### PostGIS

```bash
docker compose up -d db
```

Copy `.env.example` to `.env` before using the database-backed implementation.

### Tests

```bash
pytest
ruff check .
```

## First integration target

By the first integration checkpoint, one real candidate must move through the complete interface:

1. valid candidate geometry and source manifest;
2. physical, solar, grid-proximity and economic features;
3. hard-filter decision;
4. balanced score and rank explanation;
5. GeoJSON returned by the API;
6. candidate displayed in GeoLibre.

Do not scale to thousands of candidates until this single-candidate path works.

## Team ownership

| Workstream | Owner |
|---|---|
| Kharghar source data and GeoLibre base layers | Person 1 / data-GIS engineer |
| Spatial roof, height, terrain and proximity features | Person 2 / spatial-feature engineer |
| Solar yield and early techno-economics | Person 3 / solar-economics engineer |
| Ranking, explanations, uncertainty and optional ML | Person 4 / ranking-ML engineer |
| FastAPI, PostGIS, contracts and pipeline integration | Person 5 / platform engineer |
| Human validation, evidence ledger and demonstration | Person 6 / non-technical validation-demo owner |

See the [six-person execution plan](docs/SIX_PERSON_EXECUTION_PLAN.md) for the complete step-by-step procedure, owned paths, handoffs and non-collision rules.

### Person 4 ranking workstream

The isolated Person 4 implementation accepts separate P2, P3 and confidence tables,
enforces assumption/version alignment, and returns ranked candidates, deterministic
explanations, a confidence-calibrated stability report and an optional label-based
evaluation report.

```powershell
.\.venv\Scripts\python.exe scripts\run_person4.py `
  data\fixtures\person4\person4-request.json `
  --output output\person4\ranking-bundle.json
```

Read the [Person 4 handoff contract](docs/person4/HANDOFF_CONTRACT.md),
[research gap and method](docs/person4/RESEARCH_GAP_AND_METHOD.md) and
[AI working brief](docs/person4/AI_WORKING_BRIEF.md) before changing ranking behavior.
The [frozen feature dictionary](docs/person4/FEATURE_DICTIONARY.md) defines field
direction, units, missing policies and named weight presets.

## Core engineering rules

1. The contracts in `helios/contracts/` are the team boundary.
2. Raw modalities do not need to live in one place; adapters emit standardized features.
3. Every dataset and model must have a citation, version and validity period.
4. Incompatible temporal inputs are rejected or visibly flagged.
5. Public grid data is a proximity proxy, not hosting capacity.
6. Coarse shading is labelled as a proxy, not a measured value.
7. ML is an optional challenger for the MVP, not an architectural dependency.
8. Excluded candidates never enter a ranking.
9. Every top candidate must have component scores, confidence and reason codes.
10. Quantitative presentation claims must trace to recorded validation results.
11. Request-only sources are optional enrichment; the cached demo must run from a lawful, reproducible public baseline.

## Documentation map

- [System architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Architecture decisions](docs/architecture/decisions/)
- [Team workflow](docs/TEAM_WORKFLOW.md)
- [Six-person step-by-step execution plan](docs/SIX_PERSON_EXECUTION_PLAN.md)
- [Data and citations](docs/data/DATA_AND_PROVENANCE.md)
- [Maharashtra regional acquisition manifest](data/manifests/maharashtra-v1.json)
- [GOBS access finding and public fallback](docs/data/GOBS_ACCESS_AND_FALLBACK.md)
- [Mumbai and Navi Mumbai multi-source building fusion](docs/data/MUMBAI_BUILDING_FUSION.md)
- [Mumbai and Navi Mumbai building-source registry](data/manifests/mumbai-navi-mumbai-building-sources.json)
- [Temporal alignment](docs/data/TEMPORAL_ALIGNMENT.md)
- [Ranking and validation](docs/evaluation/RANKING_VALIDATION.md)
- [Solar-output ML challenger](docs/ml/SOLAR_OUTPUT_MODEL.md)
- [GeoLibre contract](apps/geolibre/README.md)
- [API contract](docs/api/API_CONTRACT.md)
- [Hackathon runbook](docs/HACKATHON_RUNBOOK.md)
- [Contributing](CONTRIBUTING.md)

### Planning the Maharashtra data expansion

Kharghar remains the small, reproducible demo AOI. Maharashtra-wide acquisition is staged outside Git because the source files are large. Generate the Copernicus tile and Global Solar Atlas acquisition plan with:

```powershell
python scripts/ingestion/plan_regional_sources.py --aoi-id maharashtra-v1 --bbox 72.6 15.5 80.9 22.1 --output tmp/maharashtra-source-plan.json
```

The planning bbox is not a legal/state boundary. Before scoring statewide candidates, supply an approved Maharashtra administrative boundary, clip all layers to it, record checksums, and add the resulting source manifests.

## License status

No open-source license has been selected yet. Until the team explicitly chooses one, treat this repository as private team work.

## Backend analysis endpoint

The FastAPI service now owns the default Person 4 analysis request instead of requiring the browser to assemble internal P2/P3/confidence tables. Start it from the repository root with:

```powershell
uvicorn apps.api.main:app --reload
```

Run a selected polygon against the server-owned, provenance-controlled Kharghar fixture:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis-runs/multimodal -Method Post -ContentType 'application/json' -Body (@{aoi=@{type='Polygon';coordinates=@(@(@(73.05,19.03),@(73.09,19.03),@(73.09,19.07),@(73.05,19.07),@(73.05,19.03)))}} | ConvertTo-Json -Depth 10
```

The response is the versioned `person4.v1` `RankingBundle`, including ranked candidates, explanations, confidence-calibrated stability, and evaluation output. A client may still provide an explicit `ranking_request` for a production data adapter, but the public route no longer requires knowledge of internal table layout.
