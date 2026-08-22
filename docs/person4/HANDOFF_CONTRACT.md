# Person 4 handoff contract

## Owned boundary

Person 4 owns:

- `helios/ranking/`
- `tests/test_person4_ranking.py`
- `data/fixtures/person4/`
- `docs/person4/`
- `scripts/run_person4.py`
- `scripts/export_person4_schemas.py`
- `scripts/benchmark_person4.py`

Person 4 does not edit P2/P3 feature calculations, P5 persistence/API wiring, GeoLibre,
or Person 6 labels. Contract changes are proposed here first and handed to Person 5.

## Inbound request

`P5RankingRequest` (`contract_version=person4.v1`) contains:

- required `feature_dictionary_version=person4.features-v1`;
- a P2 table with geometry, area, shading, distance and normalized physical/grid scores;
- a P3 table with yield, costs/rent and normalized generation/economic scores;
- a confidence table with overall and criterion-level confidence;
- one `assumption_version` that every P3 row must match;
- scenario, weight and robustness configuration from P5;
- an optional locked Person 6 validation set.

The exact feature semantics, missing policies and named weight presets are frozen in
[FEATURE_DICTIONARY.md](FEATURE_DICTIONARY.md) as `person4.features-v1`.

The request is rejected when candidate IDs differ across tables, IDs repeat, P3
assumptions drift, validation references unknown IDs, weights do not sum to one, or
`top_k` exceeds the candidate count.

## Outbound bundle

`RankingBundle` contains exactly four integration artifacts:

1. `ranked_candidates` - eligibility, nominal/robust/final rank, score, contributions,
   confidence and status;
2. `explanations` - deterministic positive reasons, cautions and a numeric trace;
3. `stability_report` - rank acceptability, top-K probabilities, rank intervals, score
   spread, seed and assumptions;
4. `evaluation_report` - label status, Helios/manual metrics, deltas and warnings.

The bundle also records aligned input versions. Each eligible ranked row contains
`pareto_optimal`; excluded rows use `null` because they do not enter preference analysis.

## Local run

```powershell
.\.venv\Scripts\python.exe scripts\run_person4.py `
  data\fixtures\person4\person4-request.json `
  --output output\person4\ranking-bundle.json
```

The output path is ignored by Git. Inspect the JSON, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_person4_ranking.py
.\.venv\Scripts\python.exe -m ruff check helios\ranking scripts\run_person4.py tests\test_person4_ranking.py
```

Run the reproducible scale benchmark separately:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_person4.py --candidates 5000 --iterations 100
```

## Integration rule for Person 5

Person 5 should call `rank_candidates(P5RankingRequest.model_validate(payload))` and
persist/serve the returned `RankingBundle`. Person 5 must not reimplement scoring,
stability, explanations or metrics in the API layer.

Machine-readable request and output schemas live in `docs/person4/schemas/`. Regenerate
them after an approved contract change with:

```powershell
.\.venv\Scripts\python.exe scripts\export_person4_schemas.py
```
