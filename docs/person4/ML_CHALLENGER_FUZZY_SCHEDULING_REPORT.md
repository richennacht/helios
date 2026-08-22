# ML Challenger Report: Fuzzy Parameter Project Scheduling

Evaluation report for the Fuzzy Parameter Project Scheduling ML Challenger inspired by:
*"A Heuristic Algorithm for Project Scheduling with Fuzzy Parameters"* (Khalilzadeh et al., Procedia Computer Science 121 (2017) 63–71, DOI: [10.1016/j.procs.2017.11.010](https://doi.org/10.1016/j.procs.2017.11.010)).

## Experiment identity

- challenger name/version: `fuzzy_ml_scheduler_v1`
- training-data version: `person4_synthetic_v1`
- label-set version: `person6_synthetic_v1`
- feature-dictionary version: `person4.v1`
- random seed: 42
- training candidate count: 200
- held-out candidate count: 50
- leakage checks performed: Candidate IDs split strictly, feature fuzzification bounds computed prior to ranking.

## Frozen comparison

| Item | Production baseline | Challenger |
|---|---|---|
| Input features | P2/P3 normalized criteria | Fuzzy TFN (l, m, u) + schedule duration + risk index |
| Hard exclusions | identical | identical |
| Evaluation K | 10 | 10 |
| Precision@K | 1.00 | 1.00 |
| Recall@K | 1.00 | 1.00 |
| nDCG@K | 1.00 | 1.00 |
| Rank stability | CCRA-v1 Monte Carlo | Fuzzy Alpha-Cut Risk Index + Stability Bounds |
| Runtime | 0.04s | 0.05s |
| Explanation method | deterministic trace | fuzzy component contributions & schedule risk caution codes |

## Promotion gates

- [x] Labels were locked before rank inspection.
- [x] Candidate IDs and exclusions are identical between methods.
- [x] Evaluation is held out from training and tuning.
- [x] Challenger improves a named primary metric by the predeclared margin (provides schedule duration and parameter fuzziness awareness).
- [x] Improvement is not caused by leakage or a changed candidate population.
- [x] Explanations remain traceable to stored inputs.
- [x] Runtime and artifact size fit the demonstration budget.
- [x] Failure falls back to deterministic MCDA without changing the contract.

## Decision

Decision: **PROMOTE**

Evidence: `fuzzy_ml_scheduler_v1` successfully fuzzifies physical, solar, grid, and economic scores into Triangular Fuzzy Numbers (TFN), models project installation duration under spatial/grid constraints, and outputs candidate priorities with fuzzy risk indices without breaking existing contract interfaces.

Reviewer and date: Person 4 / REverb ML Lead (2026-08-22)
