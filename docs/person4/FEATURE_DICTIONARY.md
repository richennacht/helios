# Person 4 frozen feature dictionary

- **Version:** `person4.features-v1`
- **Contract:** `person4.v1`
- **Status:** frozen for the isolated hackathon implementation

## Boundary decision

Person 2 owns construction of `physical_score` and `grid_score`. Person 3 owns
construction of `generation_score` and `economics_score`. Those four component scores
must already be normalized to `[0,1]`, where higher is always better. Person 4 validates
the range, applies stakeholder weights, calculates Pareto status, measures rank
acceptability and generates explanations.

Person 4 does not silently renormalize the four component scores. A future change to raw
feature normalization requires a new contract version and an approved P2/P3/P5 handoff.

## Fields

| Field | Owner | Unit/scale | Direction | Missing policy | Person 4 use |
|---|---|---|---|---|---|
| `generation_score` | P3 | normalized `[0,1]` | benefit | required | MCDA criterion |
| `physical_score` | P2 | normalized `[0,1]` | benefit | required | MCDA criterion |
| `grid_score` | P2 | normalized `[0,1]` | benefit | required | MCDA criterion |
| `economics_score` | P3 | normalized `[0,1]` | benefit | required | MCDA criterion |
| `usable_area_m2` | P2 | m² | benefit | required | hard filter and audit |
| `shading_factor` | P2 | retained fraction `[0,1]` | benefit | required | optional hard filter and caution |
| `grid_distance_m` | P2 | metres | cost | required | hard filter and audit |
| `annual_yield_kwh` | P3 | kWh/year | benefit | required | audit and explanation context |
| `estimated_cost_inr` | P3 | INR | cost | optional unless a budget requires it | budget filter and audit |
| `estimated_rent_inr_month` | P3 | INR/month | cost | optional with warning | audit and caution |
| `overall_confidence` | confidence owner | evidence `[0,1]` | evidence only | required | uncertainty width and warnings |
| criterion confidence | confidence owner | evidence `[0,1]` | evidence only | required | criterion perturbation width |

Confidence is never added to nominal utility. More complete evidence may narrow a rank
interval but cannot increase the nominal score.

## Frozen weight presets

| Preset | Generation | Physical | Grid | Economics |
|---|---:|---:|---:|---:|
| `balanced` | 0.35 | 0.30 | 0.20 | 0.15 |
| `energy_first` | 0.55 | 0.25 | 0.10 | 0.10 |
| `cost_first` | 0.20 | 0.20 | 0.15 | 0.45 |

Requests still carry explicit weights. Presets are reproducible starting values, not a
hidden mapping from scenario name to weights.

## Hard-filter semantics

Person 4 can independently enforce only constraints represented by the frozen inputs:

- minimum usable area;
- valid Point, Polygon or MultiPolygon exchange geometry;
- optional minimum retained shading factor;
- maximum grid-proximity screening distance;
- maximum budget;
- cost required when a budget is active, unless explicitly disabled.

Structural condition, legal suitability, hosting capacity, roof-grade shading and
temporal source acceptance remain upstream or platform responsibilities because this
contract does not contain evidence sufficient to decide them.
