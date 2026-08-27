# Person 4 performance evidence

## Reproducible benchmark

Command:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_person4.py --candidates 5000 --iterations 100
```

Observed on 2026-08-22 using Python 3.12.13 in the repository virtual environment:

| Candidates | CCRA iterations | Eligible | Elapsed | Candidate-simulations/second |
|---:|---:|---:|---:|---:|
| 5,000 | 100 | 5,000 | 5.563 seconds | 89,879 |

This is a single-machine engineering measurement, not a universal performance claim.
Repeat it on the final demonstration laptop. Use a cached higher-iteration result for the
demo if live execution exceeds the agreed time budget. Do not compare timings across code
versions without recording the commit and environment.

The benchmark covers contract construction, exclusions, MCDA, Pareto membership,
confidence-calibrated rank simulation, deterministic explanations and output validation.
It does not include P1-P3 ingestion, API/PostGIS persistence or GeoLibre rendering.
