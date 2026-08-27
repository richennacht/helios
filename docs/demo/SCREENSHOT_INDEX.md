# Visual Proof and Screenshot Catalog

**Owner:** Person 6 (Validation, Evidence, and Demo Owner)
**Status:** INDEXED AND CONSISTENCY AUDITED
**Date:** 2026-08-22

---

## 1. Visual Proof Catalog

| Asset ID | Target Slide / Section | Caption | Source Run / Fixture | Features / Candidate IDs Shown | Displayed Units | Visual Status |
|---|---|---|---|---|---|---|
| `img-01-aoi-base` | Slide 2 (AOI & Sources) | *"Kharghar AOI (`kharghar-v1`) with Open Buildings v3 Footprints, OSM Roads & Power Grid"* | `data/manifests/kharghar-v1.json` | `kharghar-v1` polygon, OSM roads, power lines, DEM | EPSG:4326, meters | Verified |
| `img-02-geolibre-base` | Slide 2 (GeoLibre Client) | *"GeoLibre Base Project with 5 Registered Attribution Layers"* | `apps/geolibre/base_project/` | Base map, hillshade, candidate outlines | Meters, mÂ² | Verified |
| `img-03-ranking-shortlist` | Slide 3 (MCDA Shortlist) | *"Helios Prioritized Rooftop Shortlist with Multi-Tier Confidence Badges"* | `data/fixtures/person4/person4-request.json` | `roof-a` (Rank 1), `roof-b` (Rank 2), `roof-c` (Rank 3), `roof-d` (Excluded) | Normalized (0â€“1), Rank 1..N | Verified |
| `img-04-candidate-explain` | Slide 4 (Explainability) | *"Candidate Detail Panel for `roof-a`: 5 Component Contributions & Deterministic Reasons"* | `scripts/run_person4.py` | `roof-a` (Score $0.884$, Yield $27,000\text{ kWh}$, Area $180\text{ m}^2$) | kWh/yr, mÂ², INR, m | Verified |
| `img-05-stability-report` | Slide 4 (CCRA-v1 Stability) | *"Confidence-Calibrated Rank Acceptability: 100% Stability for `roof-a` vs. Review Flag for `roof-b`"* | `ccra-v1` (1,000 iterations) | `roof-a` ($1.00$), `roof-b` ($0.708$), `roof-c` ($0.292$) | Probability (0â€“1), Rank Span | Verified |
| `img-06-scenario-rerank` | Slide 5 (Dynamic Reranking) | *"Instant Scenario Rerank: Transition from Balanced to Energy-First Weight Preset"* | API `/runs/{id}/rerank` | `roof-a`, `roof-b`, `roof-c` under $w_{\text{gen}}=0.50$ | Weights $\sum w = 1.0$ | Verified |
| `img-07-baseline-eval` | Slide 5 (Baseline Comparison) | *"Helios vs. Manual Scouting Baseline (`manual-scout-v1`): 7x Speedup and +0.5000 nDCG Gain"* | `evaluation_report` | Manual ($28\text{ min}$) vs. Helios ($4\text{ min}$), Prec@2, nDCG@2 | Minutes, nDCG (0â€“1) | Verified |
| `img-08-product-boundary` | Slide 6 (Screening Boundary) | *"Helios Product Boundary: Inspection Prioritization vs. EPC / Structural Approval"* | `README.md` & `docs/architecture/` | Screening pipeline vs. Field engineering gates | Text / Architecture Diagram | Verified |

---

## 2. Visual Proof Consistency Checklist

Before any screenshot or diagram is added to presentation slides, Person 6 must verify:

- [x] **Candidate ID Integrity:** Candidate IDs (`roof-a`, `roof-b`, etc., and `KHAR_...`) match the frozen fixtures exactly.
- [x] **Unit Consistency:** Area is in $\text{m}^2$, annual generation in $\text{kWh}$, grid distance in meters ($\text{m}$), and financial values in $\text{INR}$ (â‚¹).
- [x] **Mathematical Trace:** Component contributions in screenshot detail panels sum exactly to the displayed nominal score ($\sum c_i = \text{nominal\_score}$).
- [x] **No Hallucinated Ranks:** Excluded candidates (e.g., `roof-d`) display reason code `usable_area_below_minimum` with NO rank number.
- [x] **Privacy and Credentials:** No API keys, database connection strings, internal server paths, or private personal surveyor identifiers are visible.
- [x] **Disclaimer Visibility:** The screening disclaimer (*"Helios is a screening tool; not an EPC/structural approval"*) is legible on all overview screens.
