# ML challenger promote/no-promote report

Use this template only after Person 6 supplies locked labels and a held-out split is
possible. Until then, the decision is **not evaluated** and deterministic MCDA remains
the production path.

## Experiment identity

- challenger name/version:
- training-data version:
- label-set version:
- feature-dictionary version:
- random seed:
- training candidate count:
- held-out candidate count:
- leakage checks performed:

## Frozen comparison

| Item | Production baseline | Challenger |
|---|---|---|
| Input features | | |
| Hard exclusions | identical | identical |
| Evaluation K | | |
| Precision@K | | |
| Recall@K | | |
| nDCG@K | | |
| Rank stability | | |
| Runtime | | |
| Explanation method | deterministic trace | |

## Promotion gates

- [ ] Labels were locked before rank inspection.
- [ ] Candidate IDs and exclusions are identical between methods.
- [ ] Evaluation is held out from training and tuning.
- [ ] Challenger improves a named primary metric by the predeclared margin.
- [ ] Improvement is not caused by leakage or a changed candidate population.
- [ ] Explanations remain traceable to stored inputs.
- [ ] Runtime and artifact size fit the demonstration budget.
- [ ] Failure falls back to deterministic MCDA without changing the contract.

## Decision

Choose exactly one:

- **PROMOTE:** all gates pass; record reviewer and commit/model artifact.
- **DO NOT PROMOTE:** one or more gates fail; retain deterministic MCDA.
- **NOT EVALUATED:** labels or held-out evidence are insufficient.

Decision:

Evidence:

Reviewer and date:
