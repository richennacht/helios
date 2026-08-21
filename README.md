# Helios

Helios is a regional solar-site discovery and scouting platform. It converts a selected area of interest into an explainable, uncertainty-aware shortlist of rooftop candidates worth inspecting first.

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
- [GOBS access finding and public fallback](docs/data/GOBS_ACCESS_AND_FALLBACK.md)
- [Temporal alignment](docs/data/TEMPORAL_ALIGNMENT.md)
- [Ranking and validation](docs/evaluation/RANKING_VALIDATION.md)
- [GeoLibre contract](apps/geolibre/README.md)
- [API contract](docs/api/API_CONTRACT.md)
- [Hackathon runbook](docs/HACKATHON_RUNBOOK.md)
- [Contributing](CONTRIBUTING.md)

## License status

No open-source license has been selected yet. Until the team explicitly chooses one, treat this repository as private team work.
