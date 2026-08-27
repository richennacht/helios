# Helios 4-Minute Demonstration Script

**Target Duration:** 3.5 to 4.0 minutes (Maximum 240 seconds)
**Lead Presenter:** Person 6 (Validation, Evidence, and Demo Owner)
**Technical Backing:** Team REverb (Persons 1â€“5)
**Live AOI:** Kharghar Region (`kharghar-v1`), Navi Mumbai
**Run Mode:** Local Cached Run / Live FastAPI + GeoLibre

---

## Presentation Flow Overview

```text
[0:00 - 0:30] 1. Problem & Product Positioning (30s)
[0:30 - 1:00] 2. Kharghar AOI, Provenance & Data Warnings (30s)
[1:00 - 1:30] 3. Pipeline Execution & Ranked Shortlist (30s)
[1:30 - 2:15] 4. Explainable Candidate Detail & Stability (45s)
[2:15 - 2:45] 5. Scenario Reranking (30s)
[2:45 - 3:20] 6. Evaluation vs. Manual Scouting Baseline (35s)
[3:20 - 3:45] 7. Limitations & Screening Boundary (25s)
[3:45 - 4:00] 8. Summary & Technical Q&A Hand-off (15s)
```

---

## Detailed Cue-by-Cue Script

### Section 1: Problem & Product Positioning (0:00 â€“ 0:30 | 30s)
- **Speaker:** Person 6
- **Screen:** Title Slide / Helios Overview
- **Spoken Track:**
  > *"Commercial rooftop solar deployment in India suffers from high preliminary customer acquisition and inspection costs. Today, project developers manually pan across satellite maps, guessing which roofs have adequate area, solar yield, and structural viability before dispatching field engineers.*
  >
  > *Helios solves this discovery bottleneck. It transforms raw regional geospatial and solar datasets into an explainable, uncertainty-aware shortlist of candidate rooftops to inspect first."*
- **Fallback Note:** If slides fail, speak directly to the problem and transition straight to the map.

---

### Section 2: Kharghar AOI, Provenance & Data Warnings (0:30 â€“ 1:00 | 30s)
- **Speaker:** Person 6
- **Screen:** GeoLibre Base Map showing `kharghar-v1` AOI polygon, road network, power grid, and building footprints.
- **Spoken Track:**
  > *"Here is our demonstration area: Kharghar, Navi Mumbai (`kharghar-v1`).*
  >
  > *Helios strictly enforces data provenance. Every input layerâ€”from Google Open Buildings v3 footprints and 2023 Temporal v1 heights to Copernicus GLO-30 terrain and OpenStreetMap power linesâ€”is registered in a signed manifest with versioning and licenses.*
  >
  > *Notice our transparent source capability banner: because GOBS state files require official request-only processing, Helios seamlessly operates on an audited Open Buildings public fallback without stalling the pipeline."*
- **Click Track:** Hover over source manifest / capability warning badge in UI.
- **Fallback Note:** If network tiles lag, switch to cached local GeoJSON layers in GeoLibre.

---

### Section 3: Pipeline Execution & Ranked Shortlist (1:00 â€“ 1:30 | 30s)
- **Speaker:** Person 6
- **Screen:** GeoLibre / API showing candidate layers and hard-filter exclusions.
- **Spoken Track:**
  > *"When we trigger an analysis run for Kharghar under our balanced scenario, Helios executes in stages:*
  > 1. *It applies hard constraints: buildings with usable area under $40\text{ m}^2$ or excessive grid distances are immediately excluded with clear reason codes.*
  > 2. *It calculates physical geometry, pvlib solar yields, grid proximity, and early cost proxies.*
  > 3. *It normalizes criteria within the run and performs Multi-Criteria Decision Analysis (MCDA).*
  >
  > *In seconds, the system returns a prioritized shortlist ready for field dispatch."*
- **Click Track:** Display filtered vs. eligible candidates on map.

---

### Section 4: Explainable Candidate Detail & Stability (1:30 â€“ 2:15 | 45s)
- **Speaker:** Person 6
- **Screen:** Candidate Detail Panel for `roof-a` (Rank 1) and `roof-b` (Rank 2).
- **Spoken Track:**
  > *"Helios rejects black-box scoring. Opening our top-ranked candidate (`roof-a`), the analyst sees an exact breakdown:*
  > - *Normalized generation contribution: $0.322$, physical area score: $0.270$, grid score: $0.172$, and economics: $0.120$, giving a nominal score of $0.884$.*
  > - *Deterministic reason codes confirm 'strong modeled annual-generation potential' and 'strong usable-roof and coarse-shading profile'.*
  >
  > *Crucially, we run Confidence-Calibrated Rank Acceptability (CCRA-v1) across 1,000 Monte Carlo perturbations. `roof-a` demonstrates 100% top-2 probabilityâ€”it is rock solid.*
  >
  > *By contrast, `roof-b` achieves 70.8% top-2 retention and is automatically flagged as 'review required'. Helios tells the surveyor when to trust the rank and when to look closer."*
- **Click Track:** Toggle explanation panel for `roof-a`, then show caution flag on `roof-b`.

---

### Section 5: Scenario Reranking (2:15 â€“ 2:45 | 30s)
- **Speaker:** Person 6
- **Screen:** Scenario Preset Selector (`balanced` $\rightarrow$ `energy_first` $\rightarrow$ `cost_first`).
- **Spoken Track:**
  > *"Different developers have different strategies. An EPC contractor focused purely on kilowatt-hour generation can switch to the 'Energy-First' preset.*
  >
  > *Helios instantly recalculates the MCDA weights without recomputing underlying spatial geometry or pvlib physics. The shortlist updates dynamically, maintaining full mathematical trace and explanation consistency."*
- **Click Track:** Select `energy_first` preset; show updated rank order.

---

### Section 6: Evaluation vs. Manual Scouting Baseline (2:45 â€“ 3:20 | 35s)
- **Speaker:** Person 6
- **Screen:** Evaluation Comparison Table / Chart.
- **Spoken Track:**
  > *"We validated Helios against a controlled manual scouting baseline (`manual-scout-v1`), where a human GIS analyst scouted the same Kharghar region with a 28-minute time budget:*
  >
  > - *Time to shortlist dropped from 28.0 minutes to 4.0 minutesâ€”a **7x speedup**.*
  > - *Ranking quality measured by nDCG@2 jumped from **0.3066 to 0.8066** (+0.5000).*
  > - *Precision@2 increased from **0.0 to 0.50**, because manual visual scouting fell into a false-positive trap on a large but heavily shaded roof (`roof-e`), while Helios correctly filtered it.*
  >
  > *Every number shown here is traceable in our locked evidence ledger."*
- **Click Track:** Highlight baseline comparison metrics.

---

### Section 7: Limitations & Screening Boundary (3:20 â€“ 3:45 | 25s)
- **Speaker:** Person 6
- **Screen:** Product Boundary and Safeguards Slide.
- **Spoken Track:**
  > *"We emphasize what Helios is and what it is not:*
  >
  > *Helios is an inspection prioritization engine. It does **NOT** replace on-site structural load testing, detailed millimeter shadow modeling, electrical single-line diagram design, utility grid interconnection approvals, or commercial lease execution.*
  >
  > *It optimizes where surveyors spend their field hours."*

---

### Section 8: Summary & Technical Hand-off (3:45 â€“ 4:00 | 15s)
- **Speaker:** Person 6
- **Screen:** Architecture Summary / Team Contact Slide.
- **Spoken Track:**
  > *"In summary, Helios delivers reproducible data provenance, physics-informed screening, transparent deterministic rankings, and proven scouting acceleration.*
  >
  > *I will now open the floor to the jury, and invite our subsystem leadsâ€”Persons 1 through 5â€”to address specialized technical questions."*
- **Action:** Transition to Judge Q&A.

---

## Contingency and Fallback Reference

| Scenario | Trigger | Presenter Action |
|---|---|---|
| **Live API Timeout** | API does not return in 3 seconds | *"Let's switch to our cached Kharghar run bundle..."* Load pre-generated `data/fixtures/person4/person4-request.json` output. |
| **GeoLibre Tile Failure** | Satellite imagery fails to load | Rely on vector building polygon outlines and Copernicus DEM hillshade. |
| **Missing Metric Question** | Judge asks for an unmeasured statistic | *"That metric was not part of our frozen evaluation sample; we report only audited evidence."* |
