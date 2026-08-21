# Six-person delivery workflow

This page is the short operating agreement. The complete person-by-person procedure is in [SIX_PERSON_EXECUTION_PLAN.md](SIX_PERSON_EXECUTION_PLAN.md).

## Single-responsibility split

| Person | One owned subsystem | Consumes | Produces |
|---|---|---|---|
| 1 — data/GIS engineer | Kharghar source acquisition and canonical GIS layers | AOI and source list | versioned buildings, terrain, roads, power, solar/weather and economic input layers plus manifests |
| 2 — spatial-feature engineer | roof, height, terrain, access and grid-proximity features | Person 1 canonical layers | one spatial-feature row per `candidate_id` |
| 3 — solar/economics engineer | solar-yield and early techno-economic features | Person 1 inputs + Person 2 spatial features | one solar/economic-feature row per `candidate_id` |
| 4 — ranking/ML engineer | filters, normalization, MCDA, confidence and rank stability | fused feature rows | ranked candidates, component scores and reason codes |
| 5 — platform engineer | contracts, PostGIS, API, orchestration and CI | outputs from Persons 1–4 | versioned analysis run and GeoJSON API |
| 6 — validation/demo owner (non-technical) | reviewed labels, evidence ledger and presentation | API/GeoLibre output | validation sheet, baseline timings, demo script and claim evidence |

No person may silently take over another person's transformation. If an upstream output is unavailable, use the checked-in fixture with the same schema.

## Source-availability rule

The GOBS dashboard is not a direct raw-data download. GOBS state files are request-only and therefore optional enrichment. Person 1 builds the baseline from Google Open Buildings v3 polygons and Open Buildings Temporal v1 heights; Persons 2–5 must keep the pipeline executable without GOBS; Person 6 identifies each result as fallback-only or enriched. See [the verified finding, actions and six-person differences](data/GOBS_ACCESS_AND_FALLBACK.md).

## Shared integration rule

1. Person 5 freezes the v1 contracts and sample fixtures before parallel work begins.
2. Each person works only on the owned paths listed in the execution plan.
3. Each branch must produce a contract-valid artifact that the next stage can load without manual editing.
4. Pull requests target `integration`; `main` stays demo-stable.
5. Codex combines work in dependency order: P5 contracts → P1 → P2 → P3 → P4 → P5 runtime wiring → P6 evidence.
6. One real Kharghar candidate must pass all six stages before anyone scales the AOI.

## Branches

- Person 1: `feature/p1-kharghar-data`
- Person 2: `feature/p2-spatial-features`
- Person 3: `feature/p3-solar-economics`
- Person 4: `feature/p4-ranking-stability`
- Person 5: `feature/p5-platform-integration`
- Person 6: `docs/p6-validation-demo`

## Handoff chain

```text
P1 canonical data
      ↓
P2 spatial features
      ↓
P3 solar/economic features
      ↓
P4 ranking result
      ↓
P5 API + PostGIS + GeoJSON
      ↓
P6 reviewed evidence + demo
```

Person 5 may integrate artifacts but does not alter their scientific calculations. Codex resolves cross-branch wiring and rejects schema-breaking handoffs rather than guessing intent.
