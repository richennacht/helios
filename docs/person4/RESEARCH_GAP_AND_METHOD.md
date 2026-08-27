# Person 4 research gap and ranking method

Research snapshot: 2026-08-21

## Decision

The hackathon baseline remains deterministic weighted-sum MCDA. The research-backed
extension is **Confidence-Calibrated Rank Acceptability (CCRA-v1)**:

1. keep confidence out of the utility score so poor evidence cannot be disguised as a
   stakeholder preference;
2. use criterion-level confidence to size bounded feature perturbations;
3. perturb declared stakeholder weights within a versioned tolerance;
4. repeat the ranking with a fixed random seed;
5. report probability of rank 1, probability of remaining in the top K, expected rank,
   a 5th-95th percentile rank interval and nominal-top-K retention;
6. mark a candidate `stable`, `review_required` or `unstable` instead of forcing every
   candidate into a confident recommendation.

This is an experimental, SMAA-inspired prototype. It is not presented as a new theorem,
an exact implementation of the complete SMAA family, or proof that Helios improves field
outcomes. The uncertainty-width mapping must later be calibrated against observed P2/P3
errors.

## Why this is a defensible gap

Recent photovoltaic suitability literature still relies heavily on deterministic
GIS-MCDA overlays and expert weights. A 2026 meta-review found 33 reviewed PV studies with
sensitivity analysis and 36 without it; among studies that did test sensitivity, only a
limited subset used systematic uncertainty quantification. Rooftop-specific evidence also
shows that height/surface-model accuracy and simplifying roof-utilization rules materially
change estimated potential. Meanwhile, general decision-science methods already show how
to express uncertain rankings as rank acceptability rather than a single brittle order.

The gap Helios can test is therefore:

> Building-level Indian rooftop shortlisting rarely combines separately versioned
> spatial and techno-economic tables with criterion-level evidence confidence, stochastic
> weight/feature perturbation, top-K rank acceptability, deterministic explanations and an
> explicit review-required state in one reproducible open-data workflow.

That sentence is a synthesis/inference from the evidence below, not a claim that no prior
paper has ever combined any two of those elements.

## Evidence matrix

| Paper | What it establishes | Remaining opportunity for Person 4 |
|---|---|---|
| [A Systematic Meta-Review of Recent Photovoltaic Site Suitability Evolution (2026)](https://www.mdpi.com/1996-1073/19/14/3256) | Sensitivity analysis is still not standard in PV suitability research, and systematic uncertainty quantification remains limited. | Make stability a first-class output, not an appendix plot. |
| [Solar PV site selection using GIS-MCDM with spatial collinearity and sensitivity analyses (2026)](https://doi.org/10.1016/j.renene.2026.125873) | Spatial collinearity and weight sensitivity can materially improve the credibility of GIS-MCDM. | Extend robustness from suitability classes to building-level top-K probabilities and review states. |
| [Rethinking rooftop suitability for photovoltaic deployment at large scale (2026)](https://www.sciencedirect.com/science/article/pii/S2213138826000913) | Across 203 studies, utilization factors and threshold filters are major, context-sensitive uncertainty drivers. | Version every threshold/assumption and expose stability when those assumptions matter. |
| [Solar Potential Uncertainty in Building Rooftops as a Function of DSM Accuracy (2023)](https://doi.org/10.3390/rs15030567) | DSM choice and accuracy propagate into rooftop solar-potential estimates; the paper reports substantial differences and limited experimental validation in prior work. | Convert P2 confidence into visible rank uncertainty rather than treating the P2 score as exact. |
| [Sensitivity analysis approaches in MCDA: A systematic review (2023)](https://doi.org/10.1016/j.asoc.2023.110915) | Sensitivity analysis is needed to reveal ranking stability and preference changes, with many available techniques. | Report a reproducible, quantitative top-K stability bundle for every run. |
| [Multi-criteria framework for large-scale rooftop PV site selection using intuitionistic fuzzy sets (2021)](https://doi.org/10.1016/j.asoc.2021.107098) | Rooftop decisions contain uncertain, heterogeneous information, interacting criteria and expert disagreement. | Work at individual-rooftop level with traceable open-data confidence and labels, not only expert/fuzzy city alternatives. |
| [A hybrid ANN-AHP-GIS framework with uncertainty quantification for Southern India (2025)](https://doi.org/10.1016/j.ecmx.2025.101280) | Hybrid ranking and Monte Carlo uncertainty can improve robustness for 19 Southern Indian sites. | Test a transparent building-level approach where the demo does not depend on an ANN or a large training set. |
| [A double hierarchy fuzzy decision approach for solar farm ranking sites in India (2025)](https://doi.org/10.1016/j.eneco.2025.108993) | Expert hesitation, subjective bias and personalized rankings remain active Indian solar-siting problems. | Separate preferences from evidence confidence and publish both nominal and robust ranks. |
| [Fuzzy multi-criteria approach for rooftop PV site selection in Gujarat (2025)](https://doi.org/10.1038/s41598-025-21974-8) | Indian rooftop selection has limited prior work; defuzzification can introduce approximation error that needs validation. | Avoid hiding uncertainty in a single defuzzified number; return the observed rank distribution. |
| [Implementing stochastic multicriteria acceptability analysis (2007)](https://doi.org/10.1016/j.ejor.2005.12.037) | SMAA computes rank acceptability, central weights and confidence factors under uncertain measurements/preferences. | Adapt the rank-acceptability idea to the Helios P2/P3 contracts and top-K scouting decision. |
| [Modelling uncertainty in stochastic multicriteria acceptability analysis (2016)](https://research-repository.st-andrews.ac.uk/handle/10023/20847) | Probability distributions and quantiles can represent partial preference/measurement information effectively. | Start with bounded distributions, then calibrate them using observed feature errors. |
| [Towards Explainable TOPSIS (2023)](https://arxiv.org/abs/2306.07706) | Weight and aggregation effects can be made visible for MCDA users. | Keep every explanation tied to stored component contributions and stability statistics. |

## What CCRA-v1 adds to the repository

| Literature issue | Implemented response | Output evidence |
|---|---|---|
| Subjective weights | bounded weight perturbation and renormalization | random seed, tolerance and top-K retention |
| Inexact spatial/solar inputs | criterion confidence controls feature uncertainty width | score standard deviation and rank interval |
| False certainty from one ranking | repeated rank simulation | rank-acceptability distribution and top-K probability |
| Confidence double-counting | confidence is not a benefit criterion | unchanged nominal utility when only confidence changes |
| Hard-to-audit recommendations | deterministic contribution templates | component trace plus named cautions |
| Weak improvement claims | locked Person 6 labels and named manual baseline | Precision@K, Recall@K, nDCG@K and time delta |

## Assumptions that must remain visible

- `ccra-v1` uses a triangular distribution centered on each normalized feature.
- At zero confidence, the default half-width is 0.20; it shrinks linearly to zero at
  full confidence.
- Nominal weights are perturbed by up to 10 percent and renormalized.
- These defaults are demonstration assumptions, not learned calibration parameters.
- A candidate is `stable` only when its top-K probability and rank span pass the
  versioned thresholds in the request.
- A confidence score is evidence quality, not a reason to prefer a rooftop.

## Evaluation that can support a claim

Person 6 must lock blinded labels before seeing Helios rank. Person 4 then compares:

1. manual scouting order;
2. solar-generation-only order;
3. equal-weight MCDA;
4. balanced nominal MCDA;
5. CCRA-v1 robust order.

Report Precision@K, Recall@K, nDCG@K, shortlist time, labelled sample size and warnings.
Use “improved” only if a stored run beats the named baseline on the named metric. Until
then, say “designed to reduce brittle rankings and expose uncertainty.”
