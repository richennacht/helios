# Repository ownership

| Person | Single responsibility | GitHub username | Owned implementation paths | Backup reviewer |
|---|---|---|---|---|
| 1 — data/GIS engineer | Kharghar data and GeoLibre base layers | `TBD` | `data/manifests`, `scripts/ingestion`, `apps/geolibre/base_project`, `docs/data` | Person 5 |
| 2 — spatial-feature engineer | geometry, height, terrain, access, grid and shading proxy | `TBD` | `helios/features/spatial`, `tests/features/spatial`, spatial fixtures/docs | Person 1 |
| 3 — solar/economics engineer | PV yield and early economics | `TBD` | `helios/features/solar`, `helios/features/economics`, corresponding tests/fixtures/docs | Person 2 |
| 4 — ranking/ML engineer | filters, MCDA, explanations and stability | `TBD` | `helios/ranking`, `helios/explanations`, `tests/ranking`, `docs/evaluation` | Person 5 |
| 5 — platform engineer | contracts, PostGIS, API, pipeline and CI | `TBD` | `helios/contracts`, `helios/pipeline`, `helios/storage`, `apps/api`, integration tests, CI/database config | Person 4 |
| 6 — validation/demo owner | labels, evidence and presentation | `TBD` | `docs/product`, `docs/demo`, validation fixtures/forms | Person 1 |

Root documentation and cross-workstream merge resolutions are integrator-owned. Do not add invented accounts. When the six GitHub usernames are available, populate this file and generate `.github/CODEOWNERS` from these boundaries.
