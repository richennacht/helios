# Person 4 AI working brief

## Starter prompt

Paste this into a fresh AI task from the repository root:

```text
You are assisting Person 4, the Helios Ranking, Confidence and ML Engineer.
Read helios/ranking/AGENTS.md, docs/person4/HANDOFF_CONTRACT.md and
docs/person4/RESEARCH_GAP_AND_METHOD.md before proposing changes.

Owned paths: helios/ranking/, tests/test_person4_ranking.py,
data/fixtures/person4/, docs/person4/, scripts/run_person4.py,
scripts/export_person4_schemas.py and scripts/benchmark_person4.py.
Do not change P2/P3 calculations, API/PostGIS/GeoLibre code or validation labels.

The required inbound boundary is P2 table + P3 table + confidence table +
assumption_version + P5 request configuration + optional locked Person 6 labels.
The required output is ranked candidates + deterministic explanations + stability
report + evaluation report.

MCDA is the production baseline. CCRA-v1 is the experimental robust extension.
The frozen feature dictionary is person4.features-v1. P2/P3 own component-score
construction; do not silently renormalize their scores in Person 4.
Confidence controls uncertainty width; it must not be added to the utility score.
Do not introduce ML unless a held-out labelled comparison justifies it.

For this task, first list the exact files you will change. Make one bounded change,
show the diff, run the narrow tests and report assumptions and limitations. Never
invent results, citations, labels, feature values or calibration constants.
```

## Safe AI loop for every change

1. Give the AI only the relevant contract, failing test and target file.
2. Require it to state the files it plans to modify before editing.
3. Ask for one behavior and one test at a time.
4. Read the diff; reject hidden score terms, magic thresholds and runtime prose generation.
5. Run the exact narrow test locally.
6. Inspect the fixture output for score/rank/explanation consistency.
7. Commit only after the evidence exists.

## Useful prompts

### Contract audit

```text
Audit P5RankingRequest for version drift, duplicate IDs, mismatched candidate sets,
unknown validation IDs and accidental extra fields. Return missing invariants first;
do not edit until I approve the list.
```

### Stability audit

```text
Check CCRA-v1 for seed reproducibility, bounded values, normalized weights, stable
tie-breaking and confidence double-counting. Add a hand-worked test for each defect.
Do not change the mathematical assumptions without updating the method version.
```

### Explanation audit

```text
For one fixture candidate, prove every explanation phrase is selected from stored
component contributions, source fields or stability statistics. Remove any phrase
that requires a generative inference at runtime.
```

### Evaluation audit

```text
Recalculate Precision@K, Recall@K and nDCG@K by hand for the fixture. Verify labels
are filtered without changing their order or values. Flag any claim that lacks a
named baseline, K, sample size and stored metric.
```

## Commit message

```text
feat(ranking): add confidence-calibrated rank acceptability
```
